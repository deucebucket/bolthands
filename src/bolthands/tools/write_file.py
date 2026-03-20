"""File writing tool."""

from __future__ import annotations

import base64
import shlex
from typing import Any

from bolthands.events.observations import FileWriteObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "write_file",
        "description": "Write content to a file, creating it if it does not exist.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file.",
                },
            },
            "required": ["path", "content"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> FileWriteObservation:
    path = args["path"]
    content = args["content"]

    # Use base64 encoding to safely pass arbitrary content through the shell
    encoded = base64.b64encode(content.encode()).decode()
    command = f"echo '{encoded}' | base64 -d > {shlex.quote(path)}"

    stdout, stderr, exit_code = await executor.run(command, 30)

    if exit_code != 0:
        return FileWriteObservation(path=path, success=False, error=stderr)

    return FileWriteObservation(path=path, success=True)
