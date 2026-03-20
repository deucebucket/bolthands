"""File editing tool using string replacement."""

from __future__ import annotations

import base64
import shlex
from typing import Any

from bolthands.events.observations import FileEditObservation

SCHEMA = {
    "type": "function",
    "function": {
        "name": "edit_file",
        "description": "Edit a file by replacing the first occurrence of old_str with new_str.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Absolute or relative path to the file.",
                },
                "old_str": {
                    "type": "string",
                    "description": "The exact string to find and replace.",
                },
                "new_str": {
                    "type": "string",
                    "description": "The replacement string.",
                },
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
}


def schema() -> dict:
    return SCHEMA


async def execute(args: dict[str, Any], executor: Any) -> FileEditObservation:
    path = args["path"]
    old_str = args["old_str"]
    new_str = args["new_str"]

    # Read the file
    stdout, stderr, exit_code = await executor.run(f"cat {shlex.quote(path)}", 30)

    if exit_code != 0:
        return FileEditObservation(
            path=path, success=False, error=f"Failed to read file: {stderr}"
        )

    content = stdout

    # Check that old_str exists in the file
    if old_str not in content:
        return FileEditObservation(
            path=path,
            success=False,
            error=f"old_str not found in {path}",
        )

    # Replace first occurrence
    new_content = content.replace(old_str, new_str, 1)

    # Write back using base64 encoding to safely pass arbitrary content
    encoded = base64.b64encode(new_content.encode()).decode()
    write_cmd = f"echo '{encoded}' | base64 -d > {shlex.quote(path)}"
    stdout, stderr, exit_code = await executor.run(write_cmd, 30)

    if exit_code != 0:
        return FileEditObservation(
            path=path, success=False, error=f"Failed to write file: {stderr}"
        )

    return FileEditObservation(path=path, success=True)
