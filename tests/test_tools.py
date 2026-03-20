"""Tests for the BoltHands tool registry and tool implementations."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from bolthands.events.observations import (
    CmdOutputObservation,
    FileContentObservation,
    FileEditObservation,
    FileWriteObservation,
    SearchResultObservation,
    ThinkObservation,
)
from bolthands.tools import create_registry
from bolthands.tools.registry import ToolRegistry


@pytest.fixture
def registry() -> ToolRegistry:
    return create_registry()


@pytest.fixture
def executor() -> AsyncMock:
    mock = AsyncMock()
    mock.run = AsyncMock(return_value=("", "", 0))
    return mock


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_contains_all_tools(self, registry: ToolRegistry) -> None:
        expected = [
            "execute_bash",
            "read_file",
            "write_file",
            "edit_file",
            "search_files",
            "think",
            "finish",
        ]
        for name in expected:
            assert name in registry

    def test_len(self, registry: ToolRegistry) -> None:
        assert len(registry) == 7

    def test_schemas_returns_7_items(self, registry: ToolRegistry) -> None:
        schemas = registry.schemas()
        assert len(schemas) == 7

    def test_get_unknown_tool_raises(self, registry: ToolRegistry) -> None:
        with pytest.raises(KeyError, match="Unknown tool"):
            registry.get("nonexistent")

    async def test_execute_unknown_tool_raises(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        with pytest.raises(KeyError, match="Unknown tool"):
            await registry.execute("nonexistent", {}, executor)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------


class TestSchemas:
    def test_each_schema_has_required_fields(self, registry: ToolRegistry) -> None:
        for tool_schema in registry.schemas():
            assert tool_schema["type"] == "function"
            func = tool_schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
            assert "properties" in func["parameters"]


# ---------------------------------------------------------------------------
# Tool execution tests
# ---------------------------------------------------------------------------


class TestBash:
    async def test_returns_cmd_output(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("hello\n", "", 0)
        result = await registry.execute("execute_bash", {"command": "echo hello"}, executor)
        assert isinstance(result, CmdOutputObservation)
        assert result.stdout == "hello\n"
        assert result.exit_code == 0

    async def test_passes_timeout(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "", 0)
        await registry.execute("execute_bash", {"command": "sleep 5", "timeout": 60}, executor)
        executor.run.assert_called_once_with("sleep 5", 60)

    async def test_default_timeout(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "", 0)
        await registry.execute("execute_bash", {"command": "ls"}, executor)
        executor.run.assert_called_once_with("ls", 30)


class TestReadFile:
    async def test_returns_file_content(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("file contents\n", "", 0)
        result = await registry.execute("read_file", {"path": "/tmp/test.txt"}, executor)
        assert isinstance(result, FileContentObservation)
        assert result.exists is True
        assert result.content == "file contents\n"

    async def test_file_not_found(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "No such file", 1)
        result = await registry.execute("read_file", {"path": "/tmp/missing.txt"}, executor)
        assert isinstance(result, FileContentObservation)
        assert result.exists is False

    async def test_max_lines(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("line1\nline2\n", "", 0)
        await registry.execute("read_file", {"path": "/tmp/test.txt", "max_lines": 2}, executor)
        cmd = executor.run.call_args[0][0]
        assert "head -n 2" in cmd


class TestWriteFile:
    async def test_returns_write_observation(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "", 0)
        result = await registry.execute(
            "write_file", {"path": "/tmp/out.txt", "content": "hello"}, executor
        )
        assert isinstance(result, FileWriteObservation)
        assert result.success is True
        assert result.path == "/tmp/out.txt"

    async def test_write_failure(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "Permission denied", 1)
        result = await registry.execute(
            "write_file", {"path": "/read-only/out.txt", "content": "x"}, executor
        )
        assert isinstance(result, FileWriteObservation)
        assert result.success is False
        assert "Permission denied" in result.error


class TestEditFile:
    async def test_replaces_old_with_new(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        # First call reads, second call writes
        executor.run.side_effect = [
            ("hello world\n", "", 0),  # cat read
            ("", "", 0),  # cat > write
        ]
        result = await registry.execute(
            "edit_file",
            {"path": "/tmp/f.txt", "old_str": "hello", "new_str": "goodbye"},
            executor,
        )
        assert isinstance(result, FileEditObservation)
        assert result.success is True

        # Verify the written content contains the replacement
        write_cmd = executor.run.call_args_list[1][0][0]
        assert "goodbye world" in write_cmd

    async def test_old_str_not_found(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("hello world\n", "", 0)
        result = await registry.execute(
            "edit_file",
            {"path": "/tmp/f.txt", "old_str": "missing", "new_str": "x"},
            executor,
        )
        assert isinstance(result, FileEditObservation)
        assert result.success is False
        assert "not found" in result.error

    async def test_read_failure(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "No such file", 1)
        result = await registry.execute(
            "edit_file",
            {"path": "/tmp/missing.txt", "old_str": "a", "new_str": "b"},
            executor,
        )
        assert isinstance(result, FileEditObservation)
        assert result.success is False


class TestSearchFiles:
    async def test_returns_matches(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("file.py:1:match1\nfile.py:5:match2\n", "", 0)
        result = await registry.execute(
            "search_files", {"pattern": "match"}, executor
        )
        assert isinstance(result, SearchResultObservation)
        assert len(result.matches) == 2
        assert result.total_count == 2

    async def test_no_matches(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        executor.run.return_value = ("", "", 1)
        result = await registry.execute(
            "search_files", {"pattern": "nonexistent"}, executor
        )
        assert isinstance(result, SearchResultObservation)
        assert result.matches == []
        assert result.total_count == 0


class TestThink:
    async def test_returns_thought(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        result = await registry.execute(
            "think", {"thought": "I need to check the logs"}, executor
        )
        assert isinstance(result, ThinkObservation)
        assert result.thought == "I need to check the logs"

    async def test_does_not_call_executor(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        await registry.execute("think", {"thought": "reasoning"}, executor)
        executor.run.assert_not_called()


class TestFinish:
    async def test_returns_none(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        result = await registry.execute(
            "finish", {"message": "Task complete"}, executor
        )
        assert result is None

    async def test_does_not_call_executor(self, registry: ToolRegistry, executor: AsyncMock) -> None:
        await registry.execute("finish", {"message": "done"}, executor)
        executor.run.assert_not_called()
