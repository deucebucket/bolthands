"""Converter for Salesforce/xlam-function-calling-60k.

Input format:
    {
        "query": str,           # The user's question/request
        "tools": str,           # JSON string of tool definitions array
        "answers": str          # JSON string of function call answers array
    }

Each answer in "answers" looks like:
    {"name": "func_name", "arguments": {"arg1": "val1", ...}}

This dataset only has calls, not responses. We generate synthetic tool responses
to create complete multi-turn conversations.
"""

import json
import logging

from .base import (
    SYSTEM_PROMPT,
    BaseConverter,
    to_chatml,
    wrap_tool_call,
    wrap_tool_response,
)

logger = logging.getLogger(__name__)

DATASET_NAME = "Salesforce/xlam-function-calling-60k"


def _generate_synthetic_response(name: str, arguments: dict) -> dict:
    """Generate a plausible synthetic tool response for training.

    Since xlam only provides tool calls without responses, we create
    minimal but structurally valid responses so the model learns the
    call-response pattern.
    """
    return {"status": "success", "result": f"{name} executed successfully"}


def _parse_json_field(raw: str, field_name: str) -> list | None:
    """Safely parse a JSON string field, returning None on failure."""
    if not raw or not isinstance(raw, str):
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return parsed
        # Some examples wrap in an extra layer
        if isinstance(parsed, dict):
            return [parsed]
        return None
    except (json.JSONDecodeError, TypeError):
        logger.warning("Failed to parse '%s' field as JSON", field_name)
        return None


class XlamConverter(BaseConverter):
    """Convert Salesforce xLAM function-calling-60k to ChatML.

    Produces: system (with tools) -> user (query) -> assistant (tool_call)
    -> tool (synthetic response) -> assistant (summary).
    """

    name = "xlam"

    def convert(self, example: dict) -> dict | None:
        query = example.get("query", "")
        if not query:
            logger.warning("Example missing 'query', skipping")
            return None

        # Parse tools
        tools_raw = example.get("tools", "[]")
        tools = _parse_json_field(tools_raw, "tools")
        if tools is None:
            logger.warning("Could not parse tools, skipping")
            return None

        # Parse answers (the tool calls)
        answers_raw = example.get("answers", "[]")
        answers = _parse_json_field(answers_raw, "answers")
        if not answers:
            logger.warning("No valid answers found, skipping")
            return None

        # Build tool definitions for system prompt
        tools_json = json.dumps(tools, ensure_ascii=False)
        system_content = SYSTEM_PROMPT.format(tools=tools_json)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        # Build assistant message with tool calls
        tool_call_parts = []
        for answer in answers:
            name = answer.get("name", "")
            arguments = answer.get("arguments", {})
            if not name:
                continue
            tool_call_parts.append(wrap_tool_call(name, arguments))

        if not tool_call_parts:
            logger.warning("No valid tool calls extracted, skipping")
            return None

        assistant_content = "\n".join(tool_call_parts)
        messages.append({"role": "assistant", "content": assistant_content})

        # Generate synthetic tool responses
        response_parts = []
        for answer in answers:
            name = answer.get("name", "")
            arguments = answer.get("arguments", {})
            if not name:
                continue
            synthetic = _generate_synthetic_response(name, arguments)
            response_parts.append(wrap_tool_response(name, synthetic))

        tool_response_content = "\n".join(response_parts)
        messages.append({"role": "tool", "content": tool_response_content})

        # Final assistant summary
        tool_names = [a.get("name", "unknown") for a in answers if a.get("name")]
        summary = f"I've completed the requested operation using {', '.join(tool_names)}."
        messages.append({"role": "assistant", "content": summary})

        return {"text": to_chatml(messages)}

    @classmethod
    def convert_dataset(
        cls,
        dataset_name_or_path: str = DATASET_NAME,
        output_path: str = "data/output/xlam.jsonl",
        max_examples: int | None = None,
        split: str = "train",
    ) -> int:
        return super().convert_dataset(
            dataset_name_or_path, output_path, max_examples, split
        )
