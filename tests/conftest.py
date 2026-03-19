"""Shared test fixtures for BoltHands tests."""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def schemas_dir(tmp_path):
    """Create a temp schemas directory with a minimal test schema."""
    schemas = tmp_path / "schemas"
    schemas.mkdir()

    core_schema = [
        {
            "type": "function",
            "function": {
                "name": "bash",
                "description": "Execute a bash command",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "The bash command"}
                    },
                    "required": ["command"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "file_read",
                "description": "Read a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"}
                    },
                    "required": ["path"],
                },
            },
        },
    ]
    with open(schemas / "core.json", "w") as f:
        json.dump(core_schema, f)

    return schemas


@pytest.fixture
def sample_chatml():
    """A valid ChatML training example."""
    return {
        "text": (
            "<|im_start|>system\nYou are BoltHands.\n<tools>[]\n</tools>\n<|im_end|>\n"
            "<|im_start|>user\nList files in /tmp\n<|im_end|>\n"
            '<|im_start|>assistant\nLet me check.\n\n<tool_call>\n{"name": "bash", "arguments": {"command": "ls /tmp"}}\n</tool_call>\n<|im_end|>\n'
            '<|im_start|>tool\n<tool_response>\n{"name": "bash", "content": {"output": "file1.txt\\nfile2.txt"}}\n</tool_response>\n<|im_end|>\n'
            "<|im_start|>assistant\nFound 2 files: file1.txt and file2.txt.\n<|im_end|>"
        )
    }


@pytest.fixture
def sample_chatml_bad_json():
    """A ChatML example with invalid JSON in tool call."""
    return {
        "text": (
            "<|im_start|>system\nYou are BoltHands.\n<|im_end|>\n"
            "<|im_start|>user\nDo something\n<|im_end|>\n"
            '<|im_start|>assistant\n<tool_call>\n{bad json here}\n</tool_call>\n<|im_end|>'
        )
    }


@pytest.fixture
def sample_chatml_missing_arg():
    """A ChatML example with a missing required argument."""
    return {
        "text": (
            "<|im_start|>system\nYou are BoltHands.\n<|im_end|>\n"
            "<|im_start|>user\nRead a file\n<|im_end|>\n"
            '<|im_start|>assistant\n<tool_call>\n{"name": "file_read", "arguments": {}}\n</tool_call>\n<|im_end|>\n'
            '<|im_start|>tool\n<tool_response>\n{"name": "file_read", "content": {}}\n</tool_response>\n<|im_end|>'
        )
    }


@pytest.fixture
def sample_hermes_data():
    """Sample NousResearch/hermes-function-calling-v1 format."""
    return {
        "conversations": [
            {"from": "system", "value": "You are a helpful assistant with tools."},
            {"from": "human", "value": "What's the weather?"},
            {
                "from": "gpt",
                "value": '<tool_call>\n{"name": "get_weather", "arguments": {"city": "Paris"}}\n</tool_call>',
            },
            {
                "from": "tool",
                "value": '<tool_response>\n{"temperature": 22}\n</tool_response>',
            },
            {"from": "gpt", "value": "It's 22 degrees in Paris."},
        ]
    }


@pytest.fixture
def sample_xlam_data():
    """Sample Salesforce/xlam-function-calling-60k format."""
    return {
        "query": "What's the stock price of AAPL?",
        "tools": json.dumps([
            {
                "name": "get_stock_price",
                "description": "Get stock price",
                "parameters": {
                    "type": "object",
                    "properties": {"symbol": {"type": "string"}},
                    "required": ["symbol"],
                },
            }
        ]),
        "answers": json.dumps([
            {"name": "get_stock_price", "arguments": {"symbol": "AAPL"}}
        ]),
    }


@pytest.fixture
def sample_glaive_data():
    """Sample glaiveai/glaive-function-calling-v2 format."""
    return {
        "system": "You are a helpful assistant with access to functions.",
        "chat": (
            "USER: What's 2+2?\n"
            "ASSISTANT: <functioncall> {\"name\": \"calculate\", \"arguments\": {\"expression\": \"2+2\"}} </functioncall>\n"
            "FUNCTION RESPONSE: {\"result\": 4}\n"
            "ASSISTANT: The answer is 4."
        ),
    }


@pytest.fixture
def tmp_jsonl(tmp_path):
    """Create a temp JSONL file with sample data."""

    def _write(examples: list[dict], filename: str = "test.jsonl") -> Path:
        path = tmp_path / filename
        with open(path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex) + "\n")
        return path

    return _write
