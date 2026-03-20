"""Bash command execution tool."""

from __future__ import annotations

from typing import Any

from bolthands.events.observations import CmdOutputObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "execute_bash",
        "description": "Execute a bash command in the sandbox environment.",
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30).",
                    "default": 30,
                },
            },
            "required": ["command"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> CmdOutputObservation:
    command = args["command"]
    timeout = args.get("timeout", 30)
    stdout, stderr, exit_code = await executor.run(command, timeout)
    return CmdOutputObservation(stdout=stdout, stderr=stderr, exit_code=exit_code)
