"""Converter for glaiveai/glaive-function-calling-v2.

Input format:
    {
        "system": str,      # System prompt (usually includes function definitions)
        "chat": str          # Formatted string with USER/ASSISTANT/FUNCTION RESPONSE markers
    }

Chat string format example:
    USER: What's the weather?
    ASSISTANT: <functioncall> {"name": "get_weather", "arguments": {"city": "NYC"}}
    FUNCTION RESPONSE: {"temperature": 72, "condition": "sunny"}
    ASSISTANT: The weather in NYC is 72F and sunny.

We need to:
1. Parse the chat string into turns
2. Convert <functioncall> to <tool_call> tags
3. Convert FUNCTION RESPONSE to <tool_response> tags
"""

import json
import logging
import re

from .base import (
    BaseConverter,
    to_chatml,
    wrap_tool_call,
    wrap_tool_response,
)

logger = logging.getLogger(__name__)

DATASET_NAME = "glaiveai/glaive-function-calling-v2"

# Regex to split chat into turns. Matches USER:, ASSISTANT:, FUNCTION RESPONSE:
_TURN_PATTERN = re.compile(
    r"(USER|ASSISTANT|FUNCTION RESPONSE)\s*:\s*", re.IGNORECASE
)

# Regex to extract functioncall content
_FUNCTIONCALL_PATTERN = re.compile(
    r"<functioncall>\s*(\{.*?\})\s*(?:</functioncall>)?",
    re.DOTALL,
)


def _parse_chat(chat: str) -> list[dict[str, str]] | None:
    """Parse the Glaive chat string into a list of {role, content} dicts."""
    if not chat or not isinstance(chat, str):
        return None

    # Split by turn markers, keeping the markers
    parts = _TURN_PATTERN.split(chat.strip())

    # parts[0] is text before first marker (usually empty)
    # Then alternating: marker, content, marker, content, ...
    turns = []
    i = 1  # skip leading text
    while i < len(parts) - 1:
        marker = parts[i].strip().upper()
        content = parts[i + 1].strip()
        i += 2

        if marker == "USER":
            turns.append({"role": "user", "content": content})
        elif marker == "ASSISTANT":
            turns.append({"role": "assistant", "content": content})
        elif marker == "FUNCTION RESPONSE":
            turns.append({"role": "tool", "content": content})

    return turns if turns else None


def _convert_functioncall(content: str) -> str:
    """Convert <functioncall> format to <tool_call> format."""
    match = _FUNCTIONCALL_PATTERN.search(content)
    if not match:
        return content

    try:
        call_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        logger.warning("Could not parse functioncall JSON: %s", match.group(1)[:100])
        return content

    name = call_data.get("name", "")
    arguments = call_data.get("arguments", {})

    if not name:
        return content

    # Replace the <functioncall> with <tool_call>, preserving any surrounding text
    prefix = content[: match.start()].strip()
    suffix = content[match.end() :].strip()
    tool_call = wrap_tool_call(name, arguments)

    parts = [p for p in [prefix, tool_call, suffix] if p]
    return "\n".join(parts)


def _convert_function_response(content: str, prev_call_name: str = "") -> str:
    """Convert a function response string to <tool_response> format."""
    # Try to parse the content as JSON
    try:
        parsed = json.loads(content.strip())
        return wrap_tool_response(prev_call_name or "function", parsed)
    except (json.JSONDecodeError, TypeError):
        # If not valid JSON, wrap as-is
        return wrap_tool_response(prev_call_name or "function", content.strip())


class GlaiveConverter(BaseConverter):
    """Convert Glaive function-calling-v2 to ChatML.

    Parses the chat string format and converts functioncall/response tags
    to Hermes-style tool_call/tool_response tags.
    """

    name = "glaive"

    def convert(self, example: dict) -> dict | None:
        system_prompt = example.get("system", "")
        chat = example.get("chat", "")

        if not chat:
            logger.warning("Example missing 'chat' field, skipping")
            return None

        turns = _parse_chat(chat)
        if not turns:
            logger.warning("Could not parse any turns from chat, skipping")
            return None

        messages = []

        # Add system message if present
        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})

        # Track the last tool call name for pairing with responses
        last_call_name = ""

        for turn in turns:
            role = turn["role"]
            content = turn["content"]

            if role == "assistant":
                # Check for functioncall and convert
                if "<functioncall>" in content.lower():
                    content = _convert_functioncall(content)
                    # Extract the name for pairing with response
                    match = _FUNCTIONCALL_PATTERN.search(turn["content"])
                    if match:
                        try:
                            call_data = json.loads(match.group(1))
                            last_call_name = call_data.get("name", "")
                        except (json.JSONDecodeError, TypeError):
                            pass

            elif role == "tool":
                content = _convert_function_response(content, last_call_name)
                last_call_name = ""

            messages.append({"role": role, "content": content})

        # Validate: need at least user + assistant
        roles_present = {m["role"] for m in messages}
        if "user" not in roles_present or "assistant" not in roles_present:
            logger.warning("Missing user or assistant turn, skipping")
            return None

        return {"text": to_chatml(messages)}

    @classmethod
    def convert_dataset(
        cls,
        dataset_name_or_path: str = DATASET_NAME,
        output_path: str = "data/output/glaive.jsonl",
        max_examples: int | None = None,
        split: str = "train",
    ) -> int:
        return super().convert_dataset(
            dataset_name_or_path, output_path, max_examples, split
        )
