#!/usr/bin/env python3
"""
BoltHands 9B — Tool Accuracy Evaluation

Tests whether the model produces valid tool calls with correct tool names
and valid arguments per schema.

Usage:
    python -m eval.tool_accuracy --endpoint http://localhost:8080/v1
    python -m eval.tool_accuracy --endpoint http://localhost:8080/v1 --fixtures eval/fixtures/tool_accuracy.jsonl
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
    tools = []
    for name, func in schemas.items():
        tools.append({
            "type": "function",
            "function": {
                "name": func["name"],
                "description": func["description"],
                "parameters": func["parameters"],
            },
        })
    return tools


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
                    "Use the provided tools to fulfill user requests. "
                    "Always respond with tool calls when a tool is appropriate."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 1024,
    }
    resp = client.post(f"{endpoint}/chat/completions", json=payload)
    resp.raise_for_status()
    return resp.json()


def validate_tool_call(
    tool_call: dict,
    expected_tools: list[str],
    schemas: dict[str, dict],
) -> tuple[bool, str]:
    """Validate a single tool call against expected tools and schemas."""
    func = tool_call.get("function", {})
    name = func.get("name", "")
    args_str = func.get("arguments", "{}")

    # Check tool name
    if name not in expected_tools:
        return False, f"unexpected tool '{name}' (expected one of {expected_tools})"

    # Check if tool exists in schema
    if name not in schemas:
        return False, f"tool '{name}' not found in schemas"

    # Validate arguments are valid JSON
    try:
        args = json.loads(args_str) if isinstance(args_str, str) else args_str
    except json.JSONDecodeError:
        return False, f"invalid JSON arguments for '{name}'"

    # Validate required parameters
    schema_params = schemas[name].get("parameters", {})
    required = schema_params.get("required", [])
    properties = schema_params.get("properties", {})

    for req_param in required:
        if req_param not in args:
            return False, f"missing required param '{req_param}' for '{name}'"

    # Validate no unknown parameters
    for param_name in args:
        if param_name not in properties:
            return False, f"unknown param '{param_name}' for '{name}'"

    # Validate enum values
    for param_name, param_value in args.items():
        if param_name in properties:
            prop_schema = properties[param_name]
            if "enum" in prop_schema and param_value not in prop_schema["enum"]:
                return False, (
                    f"invalid value '{param_value}' for '{param_name}' "
                    f"(expected one of {prop_schema['enum']})"
                )

    return True, "ok"


def evaluate_scenario(
    client: httpx.Client,
    endpoint: str,
    scenario: dict,
    tools: list[dict],
    schemas: dict[str, dict],
    model: str,
) -> dict:
    """Evaluate a single scenario and return results."""
    prompt = scenario["prompt"]
    expected_tools = scenario["expected_tools"]

    result = {
        "prompt": prompt,
        "expected_tools": expected_tools,
        "domain": scenario.get("domain", "unknown"),
        "difficulty": scenario.get("difficulty", "unknown"),
        "passed": False,
        "reason": "",
        "tool_calls": [],
    }

    try:
        response = send_request(client, endpoint, prompt, tools, model)
    except httpx.HTTPStatusError as e:
        result["reason"] = f"HTTP error: {e.response.status_code}"
        return result
    except httpx.RequestError as e:
        result["reason"] = f"Request error: {e}"
        return result

    # Extract tool calls from response
    choices = response.get("choices", [])
    if not choices:
        result["reason"] = "no choices in response"
        return result

    message = choices[0].get("message", {})
    tool_calls = message.get("tool_calls", [])

    if not tool_calls:
        result["reason"] = "no tool calls produced"
        return result

    result["tool_calls"] = tool_calls

    # Validate each tool call
    called_names = []
    for tc in tool_calls:
        valid, reason = validate_tool_call(tc, expected_tools, schemas)
        if not valid:
            result["reason"] = reason
            return result
        called_names.append(tc["function"]["name"])

    # Check that at least one expected tool was called
    if not any(name in expected_tools for name in called_names):
        result["reason"] = (
            f"none of expected tools {expected_tools} were called "
            f"(got {called_names})"
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
    help="Path to JSONL fixtures file (default: eval/fixtures/tool_accuracy.jsonl)",
)
@click.option(
    "--model",
    default="bolthands-9b",
    help="Model name to send in API requests",
)
def main(endpoint: str, fixtures_path: str | None, model: str):
    """Evaluate tool-calling accuracy of a BoltHands model."""
    endpoint = endpoint.rstrip("/")

    if fixtures_path is None:
        fixtures_path = PROJECT_ROOT / "eval" / "fixtures" / "tool_accuracy.jsonl"
    else:
        fixtures_path = Path(fixtures_path)

    schemas = load_schemas()
    console.print(f"Loaded [bold]{len(schemas)}[/bold] tool schemas")

    fixtures = load_fixtures(fixtures_path)
    console.print(f"Loaded [bold]{len(fixtures)}[/bold] evaluation scenarios")
    console.print(f"Endpoint: [cyan]{endpoint}[/cyan]")
    console.print(f"Model: [cyan]{model}[/cyan]")
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
                console.print("[green]PASS[/green]")
            else:
                console.print(f"[red]FAIL[/red] - {result['reason']}")

    # Summary table
    console.print()
    table = Table(title="Tool Accuracy Results")
    table.add_column("Domain", style="cyan")
    table.add_column("Difficulty", style="magenta")
    table.add_column("Prompt", max_width=50)
    table.add_column("Result", justify="center")
    table.add_column("Reason")

    for r in results:
        status = "[green]PASS[/green]" if r["passed"] else "[red]FAIL[/red]"
        table.add_row(
            r["domain"],
            r["difficulty"],
            r["prompt"][:50],
            status,
            r["reason"] if not r["passed"] else "",
        )

    console.print(table)

    # Overall stats
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    pct = (passed / total * 100) if total > 0 else 0

    console.print()
    console.print(f"[bold]Overall: {passed}/{total} ({pct:.1f}%)[/bold]")

    # Per-domain breakdown
    domains = sorted(set(r["domain"] for r in results))
    if len(domains) > 1:
        console.print()
        console.print("[bold]Per-domain breakdown:[/bold]")
        for domain in domains:
            domain_results = [r for r in results if r["domain"] == domain]
            domain_passed = sum(1 for r in domain_results if r["passed"])
            domain_total = len(domain_results)
            domain_pct = (domain_passed / domain_total * 100) if domain_total > 0 else 0
            console.print(f"  {domain}: {domain_passed}/{domain_total} ({domain_pct:.1f}%)")

    sys.exit(0 if pct >= 80.0 else 1)


if __name__ == "__main__":
    main()
