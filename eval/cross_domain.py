#!/usr/bin/env python3
"""
BoltHands 9B — Cross-Domain Evaluation

Tests whether the model can use tools from multiple domains in a single
conversation turn (e.g., checking Sonarr queue AND Plex now playing).

Usage:
    python -m eval.cross_domain --endpoint http://localhost:8080/v1
"""

import json
import sys
from pathlib import Path

import click
import httpx
from rich.console import Console
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parent.parent
console = Console()


def load_schemas() -> dict[str, dict]:
    """Load all tool schemas from data/schemas/ and index by tool name."""
    schemas_dir = PROJECT_ROOT / "data" / "schemas"
    tools = {}
    for schema_file in schemas_dir.glob("*.json"):
        with open(schema_file) as f:
            schema_list = json.load(f)
        for tool_def in schema_list:
            name = tool_def["function"]["name"]
            tools[name] = tool_def["function"]
    return tools


def load_fixtures(path: Path) -> list[dict]:
    """Load evaluation fixtures from a JSONL file."""
    fixtures = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                fixtures.append(json.loads(line))
    return fixtures


def build_tool_list(schemas: dict[str, dict]) -> list[dict]:
    """Convert internal schemas to OpenAI-compatible tool format."""
    return [
        {
            "type": "function",
            "function": {
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"],
            },
        }
        for func in schemas.values()
    ]


def get_domain(tool_name: str) -> str:
    """Extract the domain prefix from a tool name."""
    if "." in tool_name:
        return tool_name.split(".")[0]
    return "core"


def send_request(
    client: httpx.Client,
    endpoint: str,
    prompt: str,
    tools: list[dict],
    model: str,
) -> dict:
    """Send a chat completion request with tools."""
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are BoltHands, a home automation assistant. "
                    "You manage Windows PCs, Plex, Sonarr, Radarr, and more. "
                    "When a user request involves multiple systems, call all "
                    "relevant tools. Use parallel tool calls when possible."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 2048,
    }
    resp = client.post(f"{endpoint}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()


def evaluate_scenario(
    client: httpx.Client,
    endpoint: str,
    scenario: dict,
    tools: list[dict],
    schemas: dict[str, dict],
    model: str,
) -> dict:
    """Evaluate a cross-domain scenario."""
    prompt = scenario["prompt"]
    expected_tools = scenario["expected_tools"]
    expected_domains = set(scenario.get("expected_domains", []))

    # If expected_domains not explicitly set, infer from expected_tools
    if not expected_domains:
        expected_domains = {get_domain(t) for t in expected_tools}

    result = {
        "prompt": prompt,
        "expected_tools": expected_tools,
        "expected_domains": sorted(expected_domains),
        "difficulty": scenario.get("difficulty", "unknown"),
        "passed": False,
        "multi_domain": False,
        "domains_hit": [],
        "tools_called": [],
        "reason": "",
    }

    try:
        response = send_request(client, endpoint, prompt, tools, model)
    except httpx.HTTPStatusError as e:
        result["reason"] = f"HTTP error: {e.response.status_code}"
        return result
    except httpx.RequestError as e:
        result["reason"] = f"Request error: {e}"
        return result

    choices = response.get("choices", [])
    if not choices:
        result["reason"] = "no choices in response"
        return result

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        result["reason"] = "no tool calls produced"
        return result

    # Collect called tool names and their domains
    called_names = []
    called_domains = set()
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        called_names.append(name)
        called_domains.add(get_domain(name))

        # Validate JSON arguments
        args_str = func.get("arguments", "{}")
        try:
            json.loads(args_str) if isinstance(args_str, str) else args_str
        except json.JSONDecodeError:
            result["reason"] = f"invalid JSON arguments for '{name}'"
            return result

    result["tools_called"] = called_names
    result["domains_hit"] = sorted(called_domains)
    result["multi_domain"] = len(called_domains) >= 2

    # Check that we hit the expected domains
    missing_domains = expected_domains - called_domains
    if missing_domains:
        result["reason"] = (
            f"missing domains: {sorted(missing_domains)} "
            f"(hit: {sorted(called_domains)})"
        )
        return result

    # Check that expected tools were called
    missing_tools = set(expected_tools) - set(called_names)
    if missing_tools:
        result["reason"] = (
            f"missing tools: {sorted(missing_tools)} "
            f"(called: {called_names})"
        )
        return result

    result["passed"] = True
    result["reason"] = "ok"
    return result


@click.command()
@click.option(
    "--endpoint",
    required=True,
    help="OpenAI-compatible API endpoint (e.g., http://localhost:8080/v1)",
)
@click.option(
    "--fixtures",
    "fixtures_path",
    default=None,
    type=click.Path(exists=True),
    help="Path to JSONL fixtures file (default: eval/fixtures/cross_domain.jsonl)",
)
@click.option(
    "--model",
    default="bolthands-9b",
    help="Model name to send in API requests",
)
def main(endpoint: str, fixtures_path: str | None, model: str):
    """Evaluate cross-domain tool-calling accuracy."""
    endpoint = endpoint.rstrip("/")

    if fixtures_path is None:
        fixtures_path = PROJECT_ROOT / "eval" / "fixtures" / "cross_domain.jsonl"
    else:
        fixtures_path = Path(fixtures_path)

    schemas = load_schemas()
    console.print(f"Loaded [bold]{len(schemas)}[/bold] tool schemas")

    fixtures = load_fixtures(fixtures_path)
    console.print(f"Loaded [bold]{len(fixtures)}[/bold] cross-domain scenarios")
    console.print(f"Endpoint: [cyan]{endpoint}[/cyan]")
    console.print()

    tools = build_tool_list(schemas)
    results = []

    with httpx.Client(timeout=60.0) as client:
        for i, scenario in enumerate(fixtures, 1):
            console.print(f"[{i}/{len(fixtures)}] {scenario['prompt'][:80]}...", end=" ")
            result = evaluate_scenario(
                client, endpoint, scenario, tools, schemas, model
            )
            results.append(result)

            if result["passed"]:
                console.print(
                    f"[green]PASS[/green] "
                    f"(domains: {', '.join(result['domains_hit'])})"
                )
            else:
                console.print(f"[red]FAIL[/red] - {result['reason']}")

    # Summary table
    console.print()
    table = Table(title="Cross-Domain Evaluation Results")
    table.add_column("Prompt", max_width=45)
    table.add_column("Expected Domains", style="cyan")
    table.add_column("Domains Hit", style="magenta")
    table.add_column("Multi-Domain", justify="center")
    table.add_column("Result", justify="center")
    table.add_column("Reason")

    for r in results:
        status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
        multi = "[green]YES[/green]" if r["multi_domain"] else "[red]NO[/red]"
        table.add_row(
            r["prompt"][:45],
            ", ".join(r["expected_domains"]),
            ", ".join(r["domains_hit"]),
            multi,
            status,
            r["reason"] if not r["passed"] else "",
        )

    console.print(table)

    # Overall stats
    passed = sum(1 for r in results if r["passed"])
    multi = sum(1 for r in results if r["multi_domain"])
    total = len(results)
    pct = (passed / total * 100) if total > 0 else 0

    console.print()
    console.print(f"[bold]Overall: {passed}/{total} ({pct:.1f}%)[/bold]")
    console.print(f"[bold]Multi-domain tool use: {multi}/{total}[/bold]")

    sys.exit(0 if pct >= 80.0 else 1)


if __name__ == "__main__":
    main()
