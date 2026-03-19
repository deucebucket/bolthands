"""HuggingFace dataset format converters for BoltHands training pipeline.

Each converter transforms a specific HF dataset format into unified
Qwen 3.5 ChatML with Hermes-style <tool_call>/<tool_response> tags.

Output format: JSONL with {"text": "<|im_start|>role\\ncontent\\n<|im_end|>\\n..."} per line.
"""

from .base import (
    SYSTEM_PROMPT,
    BaseConverter,
    normalize_role,
    to_chatml,
    wrap_tool_call,
    wrap_tool_response,
)
from .glaive import GlaiveConverter
from .hermes import HermesConverter
from .nemotron import NemotronConverter
from .xlam import XlamConverter

__all__ = [
    # Base utilities
    "BaseConverter",
    "SYSTEM_PROMPT",
    "normalize_role",
    "to_chatml",
    "wrap_tool_call",
    "wrap_tool_response",
    # Converters
    "HermesConverter",
    "XlamConverter",
    "GlaiveConverter",
    "NemotronConverter",
]

# Registry for lookup by name
CONVERTERS = {
    "hermes": HermesConverter,
    "xlam": XlamConverter,
    "glaive": GlaiveConverter,
    "nemotron": NemotronConverter,
}
