"""File reading tool."""

from __future__ import annotations

import shlex
from typing import Any

from bolthands.events.observations import CmdOutputObservation, FileContentObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read the contents of a file.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum number of lines to read. Reads entire file if omitted.",
                },
            },
            "required": ["path"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> FileContentObservation:
    path = args["path"]
    max_lines = args.get("max_lines")

    if max_lines is not None:
        command = f"head -n {int(max_lines)} {shlex.quote(path)}"
    else:
        command = f"cat {shlex.quote(path)}"

    stdout, stderr, exit_code = await executor.run(command, 30)

    if exit_code != 0:
        return FileContentObservation(path=path, content=stderr, exists=False)

    return FileContentObservation(path=path, content=stdout, exists=True)
