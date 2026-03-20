"""Think tool — lets the agent reason without taking action."""

from __future__ import annotations

from typing import Any

from bolthands.events.observations import ThinkObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "think",
        "description": "Record a thought or reasoning step. Does not execute anything.",
        "parameters": {
            "type": "object",
            "properties": {
                "thought": {
                    "type": "string",
                    "description": "The thought or reasoning to record.",
                },
            },
            "required": ["thought"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> ThinkObservation:
    return ThinkObservation(thought=args["thought"])
