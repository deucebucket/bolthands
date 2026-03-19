"""Tests for the training data validator."""

import json
from pathlib import Path
from unittest.mock import patch

from data.validator import Validator, ValidationResult


class TestValidateExample:
    def setup_method(self):
        # Patch schemas dir to avoid needing real schema files
        self.validator = Validator()

    def test_valid_example(self, sample_chatml):
        result = self.validator.validate_example(sample_chatml)
        assert result.valid
        assert len(result.errors) == 0

    def test_empty_text(self):
        result = self.validator.validate_example({"text": ""})
        assert not result.valid
        assert "Empty text field" in result.errors

    def test_missing_chatml_tags(self):
        result = self.validator.validate_example({"text": "plain text without tags"})
        assert not result.valid
        assert "missing_chatml_tags" in result.errors

    def test_missing_user_message(self):
        result = self.validator.validate_example({
            "text": "<|im_start|>system\nHello\n<|im_end|>\n<|im_start|>assistant\nHi\n<|im_end|>"
        })
        assert not result.valid
        assert "missing_user_message" in result.errors

    def test_missing_assistant_message(self):
        result = self.validator.validate_example({
            "text": "<|im_start|>system\nHello\n<|im_end|>\n<|im_start|>user\nHi\n<|im_end|>"
        })
        assert not result.valid
        assert "missing_assistant_message" in result.errors

    def test_invalid_tool_call_json(self, sample_chatml_bad_json):
        result = self.validator.validate_example(sample_chatml_bad_json)
        assert not result.valid
        assert "invalid_tool_call_json" in result.errors

    def test_missing_required_arg(self, sample_chatml_missing_arg, schemas_dir):
        # Use validator with real schemas
        with patch("data.validator.SCHEMAS_DIR", schemas_dir):
            v = Validator()
            result = v.validate_example(sample_chatml_missing_arg)
            assert not result.valid
            assert any("missing_required_arg" in e for e in result.errors)

    def test_unknown_tool(self, schemas_dir):
        with patch("data.validator.SCHEMAS_DIR", schemas_dir):
            v = Validator()
            example = {
                "text": (
                    "<|im_start|>system\nTest\n<|im_end|>\n"
                    "<|im_start|>user\nDo thing\n<|im_end|>\n"
                    '<|im_start|>assistant\n<tool_call>\n{"name": "nonexistent_tool", "arguments": {}}\n</tool_call>\n<|im_end|>\n'
                    '<|im_start|>tool\n<tool_response>\n{"name": "nonexistent_tool", "content": {}}\n</tool_response>\n<|im_end|>'
                )
            }
            result = v.validate_example(example)
            assert not result.valid
            assert any("unknown_tool" in e for e in result.errors)


class TestDeduplication:
    def test_duplicate_detection(self):
        v = Validator()
        ex1 = {"text": "<|im_start|>user\nHello world\n<|im_end|>"}
        ex2 = {"text": "<|im_start|>user\nHello world\n<|im_end|>"}
        ex3 = {"text": "<|im_start|>user\nDifferent message\n<|im_end|>"}

        assert not v.is_duplicate(ex1)
        assert v.is_duplicate(ex2)  # duplicate
        assert not v.is_duplicate(ex3)  # different

    def test_reset_clears_state(self):
        v = Validator()
        ex = {"text": "<|im_start|>user\nHello\n<|im_end|>"}
        assert not v.is_duplicate(ex)
        assert v.is_duplicate(ex)
        v.reset()
        assert not v.is_duplicate(ex)  # should be new again


class TestValidateFile:
    def test_validate_file_writes_valid_only(self, tmp_path, sample_chatml, sample_chatml_bad_json):
        input_path = tmp_path / "input.jsonl"
        output_path = tmp_path / "output.jsonl"

        with open(input_path, "w") as f:
            f.write(json.dumps(sample_chatml) + "\n")
            f.write(json.dumps(sample_chatml_bad_json) + "\n")
            f.write(json.dumps(sample_chatml) + "\n")  # duplicate

        v = Validator()
        report = v.validate_file(input_path, output_path)

        assert report.total == 3
        assert report.valid == 1  # only first valid one
        assert report.invalid == 1
        assert report.duplicates_removed == 1

        # Output should have only the valid, non-duplicate example
        with open(output_path) as f:
            lines = f.readlines()
        assert len(lines) == 1
