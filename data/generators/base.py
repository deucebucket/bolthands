"""
Base synthetic data generator for BoltHands training data.

Generates multi-turn ChatML conversations with tool calls by:
1. Loading tool schemas for a domain
2. Selecting a random scenario template
3. Generating a realistic conversation (template-based or LLM-powered)
4. Outputting as ChatML-formatted text
"""

import json
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

SCHEMAS_DIR = Path(__file__).parent.parent / "schemas"

SYSTEM_PROMPT_TEMPLATE = """You are BoltHands, an all-purpose AI assistant. You manage home infrastructure, generate media, and handle any task thrown at you.

You have access to the following tools:

<tools>
{tools}
</tools>

When you need to use a tool, respond with:
<tool_call>
{{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
</tool_call>

You can call multiple tools in one response. After receiving tool results, summarize the outcome naturally."""


@dataclass
class Message:
    role: str
    content: str


@dataclass
class Scenario:
    """A scenario template for generating training data."""

    domain: str
    category: str
    difficulty: str  # easy, medium, hard
    user_prompts: list[str]
    expected_tools: list[str]
    description: str = ""

    def random_prompt(self) -> str:
        return random.choice(self.user_prompts)


@dataclass
class ToolCall:
    name: str
    arguments: dict

    def to_xml(self) -> str:
        return f'<tool_call>\n{json.dumps({"name": self.name, "arguments": self.arguments})}\n</tool_call>'


@dataclass
class ToolResponse:
    name: str
    content: dict

    def to_xml(self) -> str:
        return f'<tool_response>\n{json.dumps({"name": self.name, "content": self.content})}\n</tool_response>'


@dataclass
class GeneratedExample:
    messages: list[Message]
    domain: str
    category: str
    difficulty: str
    tools_used: list[str] = field(default_factory=list)

    def to_chatml(self, tools_json: str) -> str:
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(tools=tools_json)
        parts = [f"<|im_start|>system\n{system_prompt}\n<|im_end|>"]
        for msg in self.messages:
            parts.append(f"<|im_start|>{msg.role}\n{msg.content}\n<|im_end|>")
        return "\n".join(parts)

    def to_dict(self, tools_json: str) -> dict:
        return {
            "text": self.to_chatml(tools_json),
            "domain": self.domain,
            "category": self.category,
            "difficulty": self.difficulty,
            "tools_used": self.tools_used,
        }


class BaseGenerator(ABC):
    """Base class for domain-specific synthetic data generators."""

    domain: str = ""
    schema_files: list[str] = []

    def __init__(self, llm_url: Optional[str] = None):
        self.tools = self._load_schemas()
        self.tools_json = json.dumps(self.tools, indent=2)
        self.llm_url = llm_url
        self.scenarios = self._build_scenarios()

    def _load_schemas(self) -> list[dict]:
        tools = []
        for schema_file in self.schema_files:
            path = SCHEMAS_DIR / schema_file
            if path.exists():
                with open(path) as f:
                    tools.extend(json.load(f))
            else:
                logger.warning(f"Schema file not found: {path}")
        return tools

    @abstractmethod
    def _build_scenarios(self) -> list[Scenario]:
        """Return list of scenario templates for this domain."""
        ...

    @abstractmethod
    def generate_example(self, scenario: Scenario) -> GeneratedExample:
        """Generate a single training example from a scenario.

        Subclasses implement this with either template-based generation
        (deterministic, fast) or LLM-powered generation (diverse, slower).
        """
        ...

    def generate_batch(self, count: int) -> list[GeneratedExample]:
        """Generate a batch of examples, sampling evenly across scenarios."""
        examples = []
        for i in range(count):
            scenario = self.scenarios[i % len(self.scenarios)]
            try:
                example = self.generate_example(scenario)
                examples.append(example)
            except Exception:
                logger.exception(f"Failed to generate example for {scenario.category}")
        return examples

    def generate_to_jsonl(self, count: int, output_path: Path) -> int:
        """Generate examples and write to JSONL file. Returns count written."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        examples = self.generate_batch(count)
        written = 0
        with open(output_path, "w") as f:
            for ex in examples:
                f.write(json.dumps(ex.to_dict(self.tools_json)) + "\n")
                written += 1
        logger.info(f"Wrote {written} examples to {output_path}")
        return written

    def _llm_generate(self, prompt: str, system: str = "") -> str:
        """Call the LLM to generate text. Requires llm_url to be set."""
        if not self.llm_url:
            raise ValueError("LLM URL not configured — use template-based generation or set llm_url")

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{self.llm_url}/v1/chat/completions",
                json={
                    "model": "bolthands",
                    "messages": messages,
                    "temperature": 0.8,
                    "max_tokens": 4096,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    def _make_assistant_with_tool(self, reasoning: str, tool_call: ToolCall) -> Message:
        """Create an assistant message with reasoning + tool call."""
        content = reasoning.strip()
        if content:
            content += "\n\n"
        content += tool_call.to_xml()
        return Message(role="assistant", content=content)

    def _make_tool_response(self, response: ToolResponse) -> Message:
        """Create a tool response message."""
        return Message(role="tool", content=response.to_xml())

    def _make_assistant_summary(self, text: str) -> Message:
        """Create a plain assistant message (no tool call)."""
        return Message(role="assistant", content=text)

    def _make_user(self, text: str) -> Message:
        return Message(role="user", content=text)
