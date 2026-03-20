"""Response parser that extracts tool calls from LLM responses.

Handles both native OpenAI tool_calls format and inline <tool_call> XML tags
(used by Qwen/ChatML models).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from bolthands.events.actions import (
    Action,
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    FinishAction,
    SearchFilesAction,
    ThinkAction,
)

logger = logging.getLogger(__name__)

# Mapping from tool name to Action class
_TOOL_ACTION_MAP: dict[str, type] = {
    "execute_bash": CmdRunAction,
    "read_file": FileReadAction,
    "write_file": FileWriteAction,
    "edit_file": FileEditAction,
    "search_files": SearchFilesAction,
    "think": ThinkAction,
    "finish": FinishAction,
}

# Regex to extract JSON from <tool_call>...</tool_call> tags
_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL
)


def parse_response(message: dict) -> Action | None:
    """Parse an LLM response message into an Action.

    Supports two formats:
    1. Native tool_calls array (OpenAI function calling)
    2. Inline <tool_call> XML tags (Qwen ChatML format)

    Args:
        message: The assistant message dict from the chat completion response.

    Returns:
        An Action instance, or None if the response is plain text or unparseable.
    """
    # Format 1: Native tool_calls
    tool_calls = message.get("tool_calls")
    if tool_calls and len(tool_calls) > 0:
        return _parse_native_tool_call(tool_calls[0])

    # Format 2: Inline <tool_call> XML tags in content
    content = message.get("content", "")
    if content and "<tool_call>" in content:
        return _parse_inline_tool_call(content)

    # Plain text response — no action
    return None


def _parse_native_tool_call(tool_call: dict) -> Action | None:
    """Parse a native OpenAI-format tool call into an Action."""
    try:
        function = tool_call.get("function", {})
        name = function.get("name", "")
        arguments = function.get("arguments", "{}")

        # Arguments may be a string (JSON) or already a dict
        if isinstance(arguments, str):
            args = json.loads(arguments)
        else:
            args = arguments

        return _build_action(name, args)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse native tool call: %s", exc)
        return None


def _parse_inline_tool_call(content: str) -> Action | None:
    """Parse an inline <tool_call> XML tag into an Action."""
    match = _TOOL_CALL_RE.search(content)
    if not match:
        return None

    try:
        data = json.loads(match.group(1))
        name = data.get("name", "")
        args = data.get("arguments", {})
        if isinstance(args, str):
            args = json.loads(args)
        return _build_action(name, args)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse inline tool call: %s", exc)
        return None


def _build_action(name: str, args: dict[str, Any]) -> Action | None:
    """Map a tool name and arguments to an Action instance."""
    action_cls = _TOOL_ACTION_MAP.get(name)
    if action_cls is None:
        logger.warning("Unknown tool name: %r", name)
        return None

    try:
        return action_cls(**args)
    except Exception as exc:
        logger.warning("Failed to build action %r with args %r: %s", name, args, exc)
        return None
