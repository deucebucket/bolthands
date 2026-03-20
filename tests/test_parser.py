"""Tests for the LLM response parser."""

import json

import pytest

from bolthands.events.actions import (
    CmdRunAction,
    FileEditAction,
    FileReadAction,
    FileWriteAction,
    FinishAction,
    SearchFilesAction,
    ThinkAction,
)
from bolthands.llm.parser import parse_response


# --- Native tool_calls format ---


class TestNativeToolCalls:
    """Test parsing of OpenAI-native tool_calls format."""

    def test_parse_cmd_run(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_1",
                    "type": "function",
                    "function": {
                        "name": "execute_bash",
                        "arguments": json.dumps(
                            {"command": "ls -la", "timeout": 10}
                        ),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, CmdRunAction)
        assert action.command == "ls -la"
        assert action.timeout == 10

    def test_parse_read_file(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_2",
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": json.dumps({"path": "/workspace/main.py"}),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, FileReadAction)
        assert action.path == "/workspace/main.py"

    def test_parse_write_file(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_3",
                    "type": "function",
                    "function": {
                        "name": "write_file",
                        "arguments": json.dumps(
                            {"path": "/workspace/out.py", "content": "print('hi')"}
                        ),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, FileWriteAction)
        assert action.path == "/workspace/out.py"
        assert action.content == "print('hi')"

    def test_parse_edit_file(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_4",
                    "type": "function",
                    "function": {
                        "name": "edit_file",
                        "arguments": json.dumps(
                            {
                                "path": "/workspace/app.py",
                                "old_str": "foo",
                                "new_str": "bar",
                            }
                        ),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, FileEditAction)
        assert action.old_str == "foo"
        assert action.new_str == "bar"

    def test_parse_search_files(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_5",
                    "type": "function",
                    "function": {
                        "name": "search_files",
                        "arguments": json.dumps(
                            {"pattern": "def main", "path": "/workspace"}
                        ),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, SearchFilesAction)
        assert action.pattern == "def main"

    def test_parse_think(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_6",
                    "type": "function",
                    "function": {
                        "name": "think",
                        "arguments": json.dumps(
                            {"thought": "I need to check the imports"}
                        ),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, ThinkAction)
        assert action.thought == "I need to check the imports"

    def test_parse_finish(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_7",
                    "type": "function",
                    "function": {
                        "name": "finish",
                        "arguments": json.dumps({"message": "Task complete"}),
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, FinishAction)
        assert action.message == "Task complete"

    def test_multiple_tool_calls_extracts_first(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_a",
                    "type": "function",
                    "function": {
                        "name": "execute_bash",
                        "arguments": json.dumps({"command": "first"}),
                    },
                },
                {
                    "id": "call_b",
                    "type": "function",
                    "function": {
                        "name": "execute_bash",
                        "arguments": json.dumps({"command": "second"}),
                    },
                },
            ],
        }
        action = parse_response(message)
        assert isinstance(action, CmdRunAction)
        assert action.command == "first"


# --- Inline <tool_call> XML format ---


class TestInlineToolCall:
    """Test parsing of inline <tool_call> XML format (Qwen ChatML)."""

    def test_parse_inline_cmd_run(self):
        tool_data = json.dumps(
            {"name": "execute_bash", "arguments": {"command": "pwd"}}
        )
        message = {
            "role": "assistant",
            "content": f"Let me check the directory.\n<tool_call>\n{tool_data}\n</tool_call>",
        }
        action = parse_response(message)
        assert isinstance(action, CmdRunAction)
        assert action.command == "pwd"

    def test_parse_inline_finish(self):
        tool_data = json.dumps(
            {"name": "finish", "arguments": {"message": "Done!"}}
        )
        message = {
            "role": "assistant",
            "content": f"<tool_call>{tool_data}</tool_call>",
        }
        action = parse_response(message)
        assert isinstance(action, FinishAction)
        assert action.message == "Done!"


# --- Edge cases ---


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_plain_text_returns_none(self):
        message = {
            "role": "assistant",
            "content": "Here is my analysis of the code.",
        }
        assert parse_response(message) is None

    def test_empty_content_returns_none(self):
        message = {"role": "assistant", "content": ""}
        assert parse_response(message) is None

    def test_no_content_returns_none(self):
        message = {"role": "assistant"}
        assert parse_response(message) is None

    def test_malformed_json_in_native_tool_call(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_bad",
                    "type": "function",
                    "function": {
                        "name": "execute_bash",
                        "arguments": "{invalid json!!!",
                    },
                }
            ],
        }
        assert parse_response(message) is None

    def test_malformed_json_in_inline_tool_call(self):
        message = {
            "role": "assistant",
            "content": "<tool_call>not valid json</tool_call>",
        }
        assert parse_response(message) is None

    def test_unknown_tool_name_returns_none(self):
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_unk",
                    "type": "function",
                    "function": {
                        "name": "nonexistent_tool",
                        "arguments": json.dumps({"foo": "bar"}),
                    },
                }
            ],
        }
        assert parse_response(message) is None

    def test_empty_tool_calls_array(self):
        message = {
            "role": "assistant",
            "content": "Some text",
            "tool_calls": [],
        }
        assert parse_response(message) is None

    def test_arguments_as_dict(self):
        """Some servers return arguments as a dict instead of JSON string."""
        message = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call_dict",
                    "type": "function",
                    "function": {
                        "name": "execute_bash",
                        "arguments": {"command": "echo hello"},
                    },
                }
            ],
        }
        action = parse_response(message)
        assert isinstance(action, CmdRunAction)
        assert action.command == "echo hello"
