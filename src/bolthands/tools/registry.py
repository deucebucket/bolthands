"""Tool registry for the BoltHands agent.

Manages registration and dispatch of all available tools.
Each tool provides an OpenAI function calling schema and an async execute function.
"""

from __future__ import annotations

from typing import Any, Callable

from bolthands.events.observations import Observation


class ToolRegistry:
    """Registry that maps tool names to their schema and execute functions."""

    def __init__(self) -> None:
        self._tools: dict[str, tuple[Callable[[], dict], Callable]] = {}

    def register(
        self,
        name: str,
        schema_fn: Callable[[], dict],
        execute_fn: Callable,
    ) -> None:
        """Register a tool by name with its schema and execute functions."""
        self._tools[name] = (schema_fn, execute_fn)

    def schemas(self) -> list[dict]:
        """Return OpenAI function calling schemas for all registered tools."""
        return [schema_fn() for schema_fn, _ in self._tools.values()]

    def get(self, name: str) -> tuple[Callable[[], dict], Callable]:
        """Get the (schema_fn, execute_fn) tuple for a tool by name.

        Raises:
            KeyError: If the tool name is not registered.
        """
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name!r}")
        return self._tools[name]

    async def execute(
        self, name: str, args: dict[str, Any], executor: Any
    ) -> Observation | None:
        """Execute a tool by name with the given arguments.

        Args:
            name: The registered tool name.
            args: Arguments to pass to the tool's execute function.
            executor: Sandbox executor that provides run(command, timeout).

        Returns:
            An Observation from the tool, or None for finish.

        Raises:
            KeyError: If the tool name is not registered.
        """
        _, execute_fn = self.get(name)
        return await execute_fn(args, executor)

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
