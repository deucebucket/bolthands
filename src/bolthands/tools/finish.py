"""Finish tool — signals that the agent has completed its task."""

from __future__ import annotations

from typing import Any

SCHEMA = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Signal that the task is complete.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "Summary of what was accomplished.",
                },
            },
            "required": ["message"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> None:
    # The controller handles finish — we just return None.
    return None
