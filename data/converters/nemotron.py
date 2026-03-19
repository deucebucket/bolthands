"""Converter for nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1.

Input format: Multi-turn trajectory with OpenAI-style messages.
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "...", "tool_calls": [
                {"function": {"name": "func", "arguments": "{...}"}, "id": "call_xxx", "type": "function"}
            ]},
            {"role": "tool", "content": "...", "tool_call_id": "call_xxx", "name": "func"},
            {"role": "assistant", "content": "final answer"}
        ],
        "tools": [...]  # Optional tool definitions
    }

Converts OpenAI-style tool_calls to Hermes-style <tool_call> tags.
"""

import json
import logging

from .base import (
    BaseConverter,
    to_chatml,
    wrap_tool_call,
    wrap_tool_response,
)

logger = logging.getLogger(__name__)

DATASET_NAME = "nvidia/Nemotron-RL-Agentic-Function-Calling-Pivot-v1"


def _extract_tool_calls(assistant_msg: dict) -> list[tuple[str, dict]]:
    """Extract (name, arguments) pairs from an OpenAI-style assistant message."""
    tool_calls = assistant_msg.get("tool_calls", [])
    if not tool_calls:
        return []

    results = []
    for tc in tool_calls:
        func = tc.get("function", {})
        name = func.get("name", "")
        args_raw = func.get("arguments", "{}")

        if not name:
            continue

        if isinstance(args_raw, str):
            try:
                arguments = json.loads(args_raw)
            except (json.JSONDecodeError, TypeError):
                arguments = {"raw": args_raw}
        elif isinstance(args_raw, dict):
            arguments = args_raw
        else:
            arguments = {}

        results.append((name, arguments))

    return results


class NemotronConverter(BaseConverter):
    """Convert Nemotron agentic function-calling trajectories to ChatML.

    Handles multi-turn trajectories where assistant messages contain
    OpenAI-style tool_calls arrays, converting them to Hermes-style
    <tool_call> tags inline.
    """

    name = "nemotron"

    def convert(self, example: dict) -> dict | None:
        raw_messages = example.get("messages")
        if not raw_messages:
            logger.warning("Example missing 'messages' field, skipping")
            return None

        if not isinstance(raw_messages, list):
            logger.warning("'messages' is not a list, skipping")
            return None

        # Build a map of tool_call_id -> name for matching tool responses
        call_id_to_name: dict[str, str] = {}

        # First pass: collect tool_call_id -> name mappings
        for msg in raw_messages:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    tc_id = tc.get("id", "")
                    func_name = tc.get("function", {}).get("name", "")
                    if tc_id and func_name:
                        call_id_to_name[tc_id] = func_name

        # Second pass: convert messages
        messages = []
        for msg in raw_messages:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""

            if role == "system":
                messages.append({"role": "system", "content": content})

            elif role == "user":
                messages.append({"role": "user", "content": content})

            elif role == "assistant":
                tool_calls = _extract_tool_calls(msg)
                if tool_calls:
                    # Build content with tool call tags
                    parts = []
                    if content.strip():
                        parts.append(content.strip())
                    for name, arguments in tool_calls:
                        parts.append(wrap_tool_call(name, arguments))
                    messages.append({
                        "role": "assistant",
                        "content": "\n".join(parts),
                    })
                else:
                    messages.append({"role": "assistant", "content": content})

            elif role == "tool":
                # Match tool response to its call via tool_call_id
                tc_id = msg.get("tool_call_id", "")
                name = msg.get("name", "") or call_id_to_name.get(tc_id, "tool")

                # Parse content as JSON if possible
                try:
                    parsed_content = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    parsed_content = content

                response = wrap_tool_response(name, parsed_content)
                messages.append({"role": "tool", "content": response})

            else:
                logger.warning("Unknown role '%s', treating as user", role)
                messages.append({"role": "user", "content": content})

        if not messages:
            return None

        # Validate
        roles_present = {m["role"] for m in messages}
        if "assistant" not in roles_present:
            logger.warning("No assistant messages found, skipping")
            return None

        return {"text": to_chatml(messages)}

    @classmethod
    def convert_dataset(
        cls,
        dataset_name_or_path: str = DATASET_NAME,
        output_path: str = "data/output/nemotron.jsonl",
        max_examples: int | None = None,
        split: str = "train",
    ) -> int:
        return super().convert_dataset(
            dataset_name_or_path, output_path, max_examples, split
        )
