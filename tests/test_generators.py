"""Tests for synthetic data generators."""

import json
import re
from pathlib import Path
from unittest.mock import patch

from data.generators.base import (
    BaseGenerator,
    GeneratedExample,
    Message,
    Scenario,
    ToolCall,
    ToolResponse,
    SCHEMAS_DIR,
)
from data.generators.systemd import SystemdGenerator
from data.generators.flipper import FlipperGenerator
from data.generators.dashboard import DashboardGenerator


TOOL_CALL_RE = re.compile(r"<tool_call>\s*({.*?})\s*</tool_call>", re.DOTALL)
TOOL_RESPONSE_RE = re.compile(r"<tool_response>\s*({.*?})\s*</tool_response>", re.DOTALL)


class TestBaseClasses:
    def test_tool_call_xml(self):
        tc = ToolCall("bash", {"command": "ls"})
        xml = tc.to_xml()
        assert "<tool_call>" in xml
        assert '"name": "bash"' in xml
        assert '"command": "ls"' in xml

    def test_tool_response_xml(self):
        tr = ToolResponse("bash", {"output": "hello"})
        xml = tr.to_xml()
        assert "<tool_response>" in xml
        assert '"name": "bash"' in xml

    def test_generated_example_to_chatml(self):
        ex = GeneratedExample(
            messages=[
                Message("user", "Hello"),
                Message("assistant", "Hi there"),
            ],
            domain="test",
            category="greeting",
            difficulty="easy",
        )
        chatml = ex.to_chatml("[]")
        assert "<|im_start|>system" in chatml
        assert "<|im_start|>user\nHello\n<|im_end|>" in chatml
        assert "<|im_start|>assistant\nHi there\n<|im_end|>" in chatml

    def test_generated_example_to_dict(self):
        ex = GeneratedExample(
            messages=[Message("user", "Hello")],
            domain="test",
            category="greeting",
            difficulty="easy",
            tools_used=["bash"],
        )
        d = ex.to_dict("[]")
        assert "text" in d
        assert d["domain"] == "test"
        assert d["tools_used"] == ["bash"]


def _validate_generated_example(example: GeneratedExample, tools_json: str = "[]"):
    """Common validation for all generated examples."""
    chatml = example.to_chatml(tools_json)

    # Must have system, user, and assistant messages
    assert "<|im_start|>system" in chatml
    assert "<|im_start|>user" in chatml
    assert "<|im_start|>assistant" in chatml

    # All tool calls must be valid JSON
    tool_calls = TOOL_CALL_RE.findall(chatml)
    for tc_json in tool_calls:
        parsed = json.loads(tc_json)
        assert "name" in parsed
        assert "arguments" in parsed

    # All tool responses must be valid JSON
    tool_responses = TOOL_RESPONSE_RE.findall(chatml)
    for tr_json in tool_responses:
        parsed = json.loads(tr_json)

    # Metadata must be set
    assert example.domain
    assert example.category
    assert example.difficulty in ("easy", "medium", "hard")


class TestSystemdGenerator:
    def setup_method(self):
        self.gen = SystemdGenerator()

    def test_has_scenarios(self):
        assert len(self.gen.scenarios) > 0

    def test_generate_all_scenarios(self):
        for scenario in self.gen.scenarios:
            example = self.gen.generate_example(scenario)
            _validate_generated_example(example)

    def test_generate_batch(self):
        examples = self.gen.generate_batch(10)
        assert len(examples) == 10
        for ex in examples:
            _validate_generated_example(ex)

    def test_generate_to_jsonl(self, tmp_path):
        output = tmp_path / "systemd.jsonl"
        count = self.gen.generate_to_jsonl(5, output)
        assert count == 5
        assert output.exists()
        with open(output) as f:
            lines = f.readlines()
        assert len(lines) == 5
        for line in lines:
            data = json.loads(line)
            assert "text" in data
            assert data["domain"] == "systemd"


class TestFlipperGenerator:
    def setup_method(self):
        self.gen = FlipperGenerator()

    def test_has_scenarios(self):
        assert len(self.gen.scenarios) > 0

    def test_generate_all_scenarios(self):
        for scenario in self.gen.scenarios:
            example = self.gen.generate_example(scenario)
            _validate_generated_example(example)

    def test_generate_batch(self):
        examples = self.gen.generate_batch(10)
        assert len(examples) == 10


class TestDashboardGenerator:
    def setup_method(self):
        self.gen = DashboardGenerator()

    def test_has_scenarios(self):
        assert len(self.gen.scenarios) > 0

    def test_generate_all_scenarios(self):
        for scenario in self.gen.scenarios:
            example = self.gen.generate_example(scenario)
            _validate_generated_example(example)

    def test_vram_management_multi_step(self):
        """VRAM management should produce multi-tool conversations."""
        vram_scenario = [s for s in self.gen.scenarios if s.category == "vram_management"][0]
        example = self.gen.generate_example(vram_scenario)
        chatml = example.to_chatml("[]")
        tool_calls = TOOL_CALL_RE.findall(chatml)
        assert len(tool_calls) >= 2, "VRAM management should use multiple tools"
