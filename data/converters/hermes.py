"""Converter for NousResearch/hermes-function-calling-v1.

Input format: ShareGPT with "conversations" array.
Roles: "system", "human", "gpt", "tool"
Tool calls in gpt messages already use <tool_call> tags (Hermes format).
Tool responses in tool messages already use <tool_response> tags.

This is the closest to our target format -- mostly pass-through with role normalization.
"""

import logging

from .base import BaseConverter, normalize_role, to_chatml

logger = logging.getLogger(__name__)

# HuggingFace dataset identifier
DATASET_NAME = "NousResearch/hermes-function-calling-v1"


class HermesConverter(BaseConverter):
    """Convert Hermes function-calling-v1 to ChatML.

    This dataset already uses Hermes-style <tool_call> and <tool_response> tags,
    so we only need to normalize roles and reformat to ChatML tokens.
    """

    name = "hermes"

    def convert(self, example: dict) -> dict | None:
        conversations = example.get("conversations")
        if not conversations:
            logger.warning("Example missing 'conversations' field, skipping")
            return None

        messages = []
        for turn in conversations:
            role_key = turn.get("from", turn.get("role", ""))
            content = turn.get("value", turn.get("content", ""))

            if not role_key:
                logger.warning("Turn missing role, skipping example")
                return None

            role = normalize_role(role_key)

            if content is None:
                content = ""

            messages.append({"role": role, "content": content})

        if not messages:
            return None

        # Validate: must have at least a user and assistant turn
        roles_present = {m["role"] for m in messages}
        if "user" not in roles_present or "assistant" not in roles_present:
            logger.warning("Example missing user or assistant turn, skipping")
            return None

        return {"text": to_chatml(messages)}

    @classmethod
    def convert_dataset(
        cls,
        dataset_name_or_path: str = DATASET_NAME,
        output_path: str = "data/output/hermes.jsonl",
        max_examples: int | None = None,
        split: str = "train",
    ) -> int:
        return super().convert_dataset(
            dataset_name_or_path, output_path, max_examples, split
        )
