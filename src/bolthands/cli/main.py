"""CLI entry point for BoltHands."""

import asyncio
import time

import click
from rich.console import Console
from rich.panel import Panel

from bolthands.agent import AgentController, AgentState
from bolthands.config import BoltHandsConfig
from bolthands.llm import LLMClient
from bolthands.tools import create_registry

console = Console()


@click.group()
def main():
    """BoltHands - Autonomous Coding Agent"""
    pass


@main.command()
@click.option("--port", default=8000, help="Server port")
@click.option("--host", default="0.0.0.0", help="Server host")
def serve(port, host):
    """Start the BoltHands API server."""
    import uvicorn

    from bolthands.server.app import app

    console.print(f"[bold green]Starting BoltHands server on {host}:{port}[/]")
    uvicorn.run(app, host=host, port=port)


@main.command()
@click.argument("task")
@click.option("--image", default=None, help="Docker image")
@click.option("--llm-url", default=None, help="LLM server URL")
@click.option("--max-iterations", default=None, type=int, help="Max iterations")
def run(task, image, llm_url, max_iterations):
    """Run a coding task autonomously."""
    config = BoltHandsConfig()
    if llm_url:
        config.llm_url = llm_url
    if max_iterations:
        config.max_iterations = max_iterations

    llm = LLMClient(base_url=config.llm_url)
    registry = create_registry()
    controller = AgentController(
        config=config,
        llm_client=llm,
        tool_registry=registry,
        sandbox_image=image,
    )

    events = []

    def on_event(event):
        events.append(event)
        event_type = event.get("type", "")
        iteration = event.get("iteration", "?")
        data = event.get("data", {})

        if event_type == "action":
            tool = data.get("tool", "unknown")
            obs = data.get("observation", {})
            exit_code = obs.get("exit_code")
            if exit_code is not None and exit_code != 0:
                console.print(
                    f"  [red][{iteration}] {tool} -> exit code {exit_code}[/]"
                )
            else:
                console.print(f"  [green][{iteration}] {tool} -> ok[/]")
        elif event_type == "think":
            thought = data.get("thought", "")
            preview = thought[:120].replace("\n", " ")
            console.print(f"  [yellow][{iteration}] think: {preview}[/]")
        elif event_type == "finish":
            message = data.get("message", "")
            console.print(f"  [blue][{iteration}] finish: {message}[/]")
        else:
            console.print(f"  [dim][{iteration}] {event_type}[/]")

    controller.on_event = on_event

    console.print(Panel(f"[bold]Task:[/] {task}", title="BoltHands"))
    start = time.time()
    status = asyncio.run(controller.run(task))
    elapsed = time.time() - start

    color = "green" if status.state == AgentState.FINISHED else "red"
    console.print(
        Panel(
            f"State: [{color}]{status.state.value}[/]\n"
            f"Iterations: {status.iteration}/{status.max_iterations}\n"
            f"Time: {elapsed:.1f}s",
            title="Result",
        )
    )
