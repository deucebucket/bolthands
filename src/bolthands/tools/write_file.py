"""File writing tool."""

from __future__ import annotations

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

    # Use heredoc to write content, avoiding quoting issues
    delimiter = "BOLTHANDS_EOF"
    command = f"cat > {path!r} << '{delimiter}'\n{content}\n{delimiter}"

    stdout, stderr, exit_code = await executor.run(command, 30)

    if exit_code != 0:
        return FileWriteObservation(path=path, success=False, error=stderr)

    return FileWriteObservation(path=path, success=True)
