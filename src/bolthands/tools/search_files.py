"""File search tool using grep."""

from __future__ import annotations

import shlex
from typing import Any

from bolthands.events.observations import SearchResultObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "Search for a pattern in files using grep.",
        "parameters": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "The regex pattern to search for.",
                },
                "path": {
                    "type": "string",
                    "description": "Directory to search in (default '.').",
                    "default": ".",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default 20).",
                    "default": 20,
                },
            },
            "required": ["pattern"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(
    args: dict[str, Any], executor: Any
) -> SearchResultObservation:
    pattern = args["pattern"]
    path = args.get("path", ".")
    max_results = args.get("max_results", 20)

    command = f"grep -rn {shlex.quote(pattern)} {shlex.quote(path)} | head -n {int(max_results)}"
    stdout, stderr, exit_code = await executor.run(command, 30)

    # grep returns exit_code 1 when no matches found — that's not an error
    if exit_code not in (0, 1):
        return SearchResultObservation(matches=[], total_count=0)

    matches = [line for line in stdout.strip().split("\n") if line]
    return SearchResultObservation(matches=matches, total_count=len(matches))
