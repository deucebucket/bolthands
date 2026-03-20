"""System prompt builder for the BoltHands agent."""

from __future__ import annotations

_BASE_PROMPT = """\
You are BoltHands, an autonomous coding agent running inside a Docker container. \
You solve programming tasks by reading files, running commands, editing code, \
and iterating on errors until the task is complete.

Core behaviors:
- Always read files before modifying them
- Test changes after making them
- When errors occur, analyze the error and try a different approach
- Use the think tool to reason about complex problems
- Call finish when the task is complete
"""


def build_system_prompt(
    tool_schemas: list[dict],
    workspace_info: str = "",
) -> str:
    """Build the system prompt for the agent.

    Tools are passed separately via the API's tools parameter, so they are
    NOT embedded in the prompt text.

    Args:
        tool_schemas: List of tool schemas (reserved for future use,
            not embedded in prompt).
        workspace_info: Optional description of the current workspace state.

    Returns:
        The assembled system prompt string.
    """
    parts = [_BASE_PROMPT]

    if workspace_info:
        parts.append(f"\n{workspace_info}\n")

    return "".join(parts)
