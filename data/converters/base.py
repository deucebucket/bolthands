"""Base converter for HuggingFace datasets to Qwen 3.5 ChatML format."""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Role normalization map: source role -> ChatML role
ROLE_MAP = {
    "system": "system",
    "user": "user",
    "human": "user",
    "assistant": "assistant",
    "gpt": "assistant",
    "model": "assistant",
    "tool": "tool",
    "function": "tool",
    "function_response": "tool",
    "observation": "tool",
}

SYSTEM_PROMPT = (
    "You are a capable AI assistant with access to the following tools:\n"
    "<tools>\n{tools}\n</tools>\n\n"
    "When you need to use a tool, write your tool call inside <tool_call> tags like this:\n"
    "<tool_call>\n"
    '{{\"name\": \"tool_name\", \"arguments\": {{\"arg1\": \"value1\"}}}}\n'
    "</tool_call>\n\n"
    "Tool results will be provided inside <tool_response> tags."
)


def normalize_role(role: str) -> str:
    """Normalize a role string to one of: system, user, assistant, tool."""
    normalized = ROLE_MAP.get(role.lower().strip())
    if normalized is None:
        logger.warning("Unknown role '%s', defaulting to 'user'", role)
        return "user"
    return normalized


def to_chatml(messages: list[dict[str, str]]) -> str:
    """Convert a list of {role, content} messages to a ChatML formatted string.

    ChatML format:
        <|im_start|>{role}
        {content}
        <|im_end|>
    """
    parts = []
    for msg in messages:
        role = normalize_role(msg.get("role", msg.get("from", "user")))
        content = msg.get("content", msg.get("value", ""))
        if content is None:
            content = ""
        parts.append(f"<|im_start|>{role}\n{content}\n<|im_end|>")
    return "\n".join(parts) + "\n"


def wrap_tool_call(name: str, arguments: dict | str) -> str:
    """Wrap a function call in <tool_call> tags (Hermes format).

    Args:
        name: The tool/function name.
        arguments: The arguments dict or JSON string.

    Returns:
        String with <tool_call>...</tool_call> wrapping.
    """
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except (json.JSONDecodeError, TypeError):
            pass
    payload = json.dumps({"name": name, "arguments": arguments}, ensure_ascii=False)
    return f"<tool_call>\n{payload}\n</tool_call>"


def wrap_tool_response(name: str, content: Any) -> str:
    """Wrap a tool response in <tool_response> tags (Hermes format).

    Args:
        name: The tool/function name that produced this response.
        content: The response content (dict, str, etc.).

    Returns:
        String with <tool_response>...</tool_response> wrapping.
    """
    if isinstance(content, str):
        try:
            content = json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass
    payload = json.dumps({"name": name, "content": content}, ensure_ascii=False)
    return f"<tool_response>\n{payload}\n</tool_response>"


class BaseConverter:
    """Base class for dataset format converters.

    Subclasses must implement `convert(example)` which takes a single dataset
    row and returns {"text": chatml_string} or None to skip.
    """

    name: str = "base"

    def convert(self, example: dict) -> dict | None:
        """Convert a single dataset example to {"text": chatml_string}.

        Returns None to skip malformed examples.
        """
        raise NotImplementedError

    @classmethod
    def convert_dataset(
        cls,
        dataset_name_or_path: str,
        output_path: str | Path,
        max_examples: int | None = None,
        split: str = "train",
    ) -> int:
        """Load a HuggingFace dataset and convert it to JSONL.

        Args:
            dataset_name_or_path: HF dataset name or local path.
            output_path: Path to write the output JSONL file.
            max_examples: Maximum number of examples to convert (None = all).
            split: Dataset split to use.

        Returns:
            Number of examples successfully converted.
        """
        from datasets import load_dataset

        logger.info(
            "Loading dataset '%s' (split=%s, max=%s)",
            dataset_name_or_path,
            split,
            max_examples,
        )
        ds = load_dataset(dataset_name_or_path, split=split)

        if max_examples is not None:
            ds = ds.shuffle(seed=42).select(range(min(max_examples, len(ds))))

        converter = cls()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        converted = 0
        skipped = 0

        with open(output_path, "w", encoding="utf-8") as f:
            for i, example in enumerate(ds):
                try:
                    result = converter.convert(example)
                    if result is not None and result.get("text"):
                        f.write(json.dumps(result, ensure_ascii=False) + "\n")
                        converted += 1
                    else:
                        skipped += 1
                except Exception:
                    logger.warning(
                        "Error converting example %d, skipping", i, exc_info=True
                    )
                    skipped += 1

        logger.info(
            "Wrote %d examples to %s (%d skipped)", converted, output_path, skipped
        )
        return converted
