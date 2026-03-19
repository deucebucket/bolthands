#!/usr/bin/env python3
"""
BoltHands 9B — Regression Testing

Compares output quality between the base model and fine-tuned model on
general capabilities: chat, code generation, and instruction following.
Ensures fine-tuning hasn't degraded non-tool-calling abilities.

Usage:
    python -m eval.regression \
        --base-endpoint http://localhost:8080/v1 \
        --tuned-endpoint http://localhost:8081/v1

    # Single model mode (just check outputs):
    python -m eval.regression --tuned-endpoint http://localhost:8080/v1
"""

import json
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parent.parent
console = Console()


def load_fixtures(path: Path) -> list[dict]:
    """Load evaluation fixtures from a JSONL file."""
    fixtures = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


def send_chat(
    client: httpx.Client,
    endpoint: str,
    prompt: str,
    system_prompt: str | None,
    model: str,
) -> str:
    """Send a chat completion request (no tools) and return the response text."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    resp = client.post(f"{endpoint}/chat/completions", json=payload)
    resp.raise_for_status()
    data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        return "<no response>"

    return choices[0].get("message", {}).get("content", "<empty>")


def check_quality(response: str, scenario: dict) -> tuple[bool, str]:
    """Basic quality checks on a response."""
    category = scenario.get("category", "chat")
    checks = scenario.get("quality_checks", [])

    if not response or response in ("<no response>", "<empty>"):
        return False, "empty response"

    # Check minimum length
    if len(response.strip()) < 20:
        return False, "response too short"

    # Check for required keywords/patterns
    for check in checks:
        check_type = check.get("type", "")
        if check_type == "contains":
            keyword = check["value"]
            if keyword.lower() not in response.lower():
                return False, f"missing expected content: '{keyword}'"
        elif check_type == "not_contains":
            keyword = check["value"]
            if keyword.lower() in response.lower():
                return False, f"contains unexpected content: '{keyword}'"
        elif check_type == "min_length":
            if len(response) < check["value"]:
                return False, f"response shorter than {check['value']} chars"

    # Category-specific checks
    if category == "code":
        code_indicators = [
            "```", "def ", "function ", "class ", "import ",
            "return ", "const ", "let ", "var ",
        ]
        if not any(indicator in response for indicator in code_indicators):
            return False, "code response lacks code content"

    return True, "ok"


@click.command()
@click.option(
    "--base-endpoint",
    default=None,
    help="Base model API endpoint (optional, for comparison)",
)
@click.option(
    "--tuned-endpoint",
    required=True,
    help="Fine-tuned model API endpoint",
)
@click.option(
    "--fixtures",
    "fixtures_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to JSONL fixtures file (default: eval/fixtures/regression.jsonl)",
)
@click.option(
    "--base-model",
    default="qwen3.5-9b",
    help="Base model name for API requests",
)
@click.option(
    "--tuned-model",
    default="bolthands-9b",
    help="Fine-tuned model name for API requests",
)
@click.option(
    "--show-outputs",
    is_flag=True,
    default=False,
    help="Show full model outputs side-by-side",
)
def main(
    base_endpoint: str | None,
    tuned_endpoint: str,
    fixtures_path: str | None,
    base_model: str,
    tuned_model: str,
    show_outputs: bool,
):
    """Run regression tests comparing base and fine-tuned models."""
    tuned_endpoint = tuned_endpoint.rstrip("/")
    if base_endpoint:
        base_endpoint = base_endpoint.rstrip("/")

    if fixtures_path is None:
        fixtures_path = PROJECT_ROOT / "eval" / "fixtures" / "regression.jsonl"
    else:
        fixtures_path = Path(fixtures_path)

    fixtures = load_fixtures(fixtures_path)
    console.print(f"Loaded [bold]{len(fixtures)}[/bold] regression scenarios")
    console.print(f"Fine-tuned endpoint: [cyan]{tuned_endpoint}[/cyan]")
    if base_endpoint:
        console.print(f"Base endpoint: [cyan]{base_endpoint}[/cyan]")
    else:
        console.print("[yellow]No base endpoint -- running single-model mode[/yellow]")
    console.print()

    comparison_mode = base_endpoint is not None
    results = []

    with httpx.Client(timeout=60.0) as client:
        for i, scenario in enumerate(fixtures, 1):
            prompt = scenario["prompt"]
            category = scenario.get("category", "chat")
            system_prompt = scenario.get("system_prompt")

            console.print(
                f"[{i}/{len(fixtures)}] [{category}] "
                f"{prompt[:70]}..."
            )

            # Get fine-tuned response
            try:
                tuned_response = send_chat(
                    client, tuned_endpoint, prompt, system_prompt, tuned_model
                )
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                tuned_response = f"<error: {e}>"

            tuned_ok, tuned_reason = check_quality(tuned_response, scenario)

            # Get base response if comparison mode
            base_response = None
            base_ok = None
            base_reason = None
            if comparison_mode:
                try:
                    base_response = send_chat(
                        client, base_endpoint, prompt, system_prompt, base_model
                    )
                except (httpx.HTTPStatusError, httpx.RequestError) as e:
                    base_response = f"<error: {e}>"
                base_ok, base_reason = check_quality(base_response, scenario)

            result = {
                "prompt": prompt,
                "category": category,
                "tuned_response": tuned_response,
                "tuned_passed": tuned_ok,
                "tuned_reason": tuned_reason,
                "base_response": base_response,
                "base_passed": base_ok,
                "base_reason": base_reason,
            }
            results.append(result)

            # Print inline result
            status = (
                "[green]PASS[/green]"
                if tuned_ok
                else f"[red]FAIL[/red] - {tuned_reason}"
            )
            if comparison_mode and base_ok is not None:
                base_status = (
                    "[green]PASS[/green]" if base_ok else "[red]FAIL[/red]"
                )
                console.print(f"  Tuned: {status} | Base: {base_status}")
            else:
                console.print(f"  {status}")

            # Show outputs if requested
            if show_outputs:
                console.print(
                    Panel(
                        tuned_response[:500],
                        title=f"[cyan]Fine-tuned ({tuned_model})[/cyan]",
                        width=100,
                    )
                )
                if base_response:
                    console.print(
                        Panel(
                            base_response[:500],
                            title=f"[yellow]Base ({base_model})[/yellow]",
                            width=100,
                        )
                    )

    # Summary table
    console.print()
    table = Table(title="Regression Test Results")
    table.add_column("Category", style="cyan")
    table.add_column("Prompt", max_width=40)
    table.add_column("Tuned", justify="center")
    if comparison_mode:
        table.add_column("Base", justify="center")
        table.add_column("Regression?", justify="center")

    for r in results:
        tuned_status = (
            "[green]PASS[/green]" if r["tuned_passed"] else "[red]FAIL[/red]"
        )
        row = [r["category"], r["prompt"][:40], tuned_status]

        if comparison_mode:
            base_status = (
                "[green]PASS[/green]"
                if r["base_passed"]
                else "[red]FAIL[/red]"
            )
            regression = (
                r["base_passed"] is True and r["tuned_passed"] is False
            )
            reg_status = (
                "[red]YES[/red]" if regression else "[green]no[/green]"
            )
            row.extend([base_status, reg_status])

        table.add_row(*row)

    console.print(table)

    # Overall stats
    tuned_passed = sum(1 for r in results if r["tuned_passed"])
    total = len(results)
    tuned_pct = (tuned_passed / total * 100) if total > 0 else 0

    console.print()
    console.print(
        f"[bold]Fine-tuned: {tuned_passed}/{total} ({tuned_pct:.1f}%)[/bold]"
    )

    if comparison_mode:
        base_passed = sum(1 for r in results if r["base_passed"])
        base_pct = (base_passed / total * 100) if total > 0 else 0
        regressions = sum(
            1
            for r in results
            if r["base_passed"] and not r["tuned_passed"]
        )
        console.print(
            f"[bold]Base: {base_passed}/{total} ({base_pct:.1f}%)[/bold]"
        )

        if regressions > 0:
            console.print(
                f"[bold red]Regressions detected: {regressions}[/bold red]"
            )
        else:
            console.print("[bold green]No regressions detected.[/bold green]")

    # Per-category breakdown
    categories = sorted(set(r["category"] for r in results))
    if len(categories) > 1:
        console.print()
        console.print("[bold]Per-category breakdown (fine-tuned):[/bold]")
        for cat in categories:
            cat_results = [r for r in results if r["category"] == cat]
            cat_passed = sum(1 for r in cat_results if r["tuned_passed"])
            cat_total = len(cat_results)
            cat_pct = (
                (cat_passed / cat_total * 100) if cat_total > 0 else 0
            )
            console.print(
                f"  {cat}: {cat_passed}/{cat_total} ({cat_pct:.1f}%)"
            )

    sys.exit(0 if tuned_pct >= 80.0 else 1)


if __name__ == "__main__":
    main()
