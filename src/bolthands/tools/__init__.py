"""Tool registry and tool implementations for the BoltHands agent."""

from __future__ import annotations

from bolthands.tools import (
    bash,
    edit_file,
    finish,
    read_file,
    search_files,
    think,
    write_file,
)
from bolthands.tools.registry import ToolRegistry

_TOOL_MODULES = [
    ("execute_bash", bash),
    ("read_file", read_file),
    ("write_file", write_file),
    ("edit_file", edit_file),
    ("search_files", search_files),
    ("think", think),
    ("finish", finish),
]


def create_registry() -> ToolRegistry:
    """Create a ToolRegistry with all built-in tools registered."""
    registry = ToolRegistry()
    for name, module in _TOOL_MODULES:
        registry.register(name, module.schema, module.execute)
    return registry


__all__ = ["ToolRegistry", "create_registry"]
