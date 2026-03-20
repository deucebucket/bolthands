"""Tests for the context management module."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from bolthands.context.monitor import ContextMonitor, CompactionLevel
from bolthands.context.compactor import Compactor
from bolthands.context.workspace import WorkspaceMemory
from bolthands.context.session import SessionManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_messages(count: int, content_len: int = 100, role: str = "user") -> list[dict]:
    """Create a list of messages with known content length."""
    return [
        {"role": role, "content": "x" * content_len}
        for _ in range(count)
    ]


def make_executor(state_json: str | None = None):
    """Create a mock executor that optionally returns state JSON on cat."""
    executor = AsyncMock()

    async def run_side_effect(cmd: str):
        if "cat /workspace/context/state.json" in cmd:
            return state_json or ""
        return ""

    executor.run.side_effect = run_side_effect
    return executor


def make_llm_client(response: str = "Summary of conversation."):
    """Create a mock LLM client."""
    client = AsyncMock()
    client.generate.return_value = response
    return client


# ---------------------------------------------------------------------------
# Monitor tests
# ---------------------------------------------------------------------------

class TestContextMonitor:
    def test_count_tokens(self):
        """Verify token approximation: len(content)/4 + 10 per message."""
        monitor = ContextMonitor()
        # 100 chars => 100/4 + 10 = 35 tokens per message
        messages = make_messages(2, content_len=100)
        count = monitor.count_tokens(messages)
        assert count == 70  # 35 * 2

    def test_check_budget_green(self):
        """Under 60% utilization => GREEN."""
        monitor = ContextMonitor(max_context=1000)
        # Need tokens < 600. Each msg with 100 chars = 35 tokens.
        # 10 messages = 350 tokens = 35% utilization
        messages = make_messages(10, content_len=100)
        assert monitor.check_budget(messages) == CompactionLevel.GREEN

    def test_check_budget_yellow(self):
        """60-75% utilization => YELLOW."""
        monitor = ContextMonitor(max_context=1000)
        # Need tokens in [600, 750). Each msg = 35 tokens.
        # 18 messages = 630 tokens = 63%
        messages = make_messages(18, content_len=100)
        assert monitor.check_budget(messages) == CompactionLevel.YELLOW

    def test_check_budget_orange(self):
        """75-85% utilization => ORANGE."""
        monitor = ContextMonitor(max_context=1000)
        # 22 messages = 770 tokens = 77%
        messages = make_messages(22, content_len=100)
        assert monitor.check_budget(messages) == CompactionLevel.ORANGE

    def test_check_budget_red(self):
        """Over 85% utilization => RED."""
        monitor = ContextMonitor(max_context=1000)
        # 25 messages = 875 tokens = 87.5%
        messages = make_messages(25, content_len=100)
        assert monitor.check_budget(messages) == CompactionLevel.RED


# ---------------------------------------------------------------------------
# Compactor tests
# ---------------------------------------------------------------------------

class TestCompactor:
    def test_tier1_mask(self):
        """Old tool messages get masked, recent ones kept intact."""
        llm = make_llm_client()
        compactor = Compactor(llm)

        messages = []
        for i in range(15):
            messages.append({"role": "user", "content": f"question {i}"})
            messages.append({"role": "tool", "content": f"long output line {i}\nmore data"})

        result = compactor.tier1_mask(messages, keep_recent=10)

        # Messages before cutoff (index < 20) with role=tool should be masked
        # Total 30 messages, keep_recent=10 => cutoff at index 20
        for i in range(20):
            msg = result[i]
            if msg["role"] == "tool":
                assert "[Output masked, was" in msg["content"]

        # Recent messages (index >= 20) should be untouched
        for i in range(20, 30):
            assert result[i] == messages[i]

    def test_tier1_mask_preserves_system(self):
        """System messages are never masked."""
        llm = make_llm_client()
        compactor = Compactor(llm)

        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            *[{"role": "tool", "content": f"output {i}"} for i in range(15)],
        ]

        result = compactor.tier1_mask(messages, keep_recent=5)

        # System message at index 0 should be preserved
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_tier2_summarize(self):
        """LLM called with summarization prompt, oldest messages replaced."""
        llm = make_llm_client("This is the summary.")
        compactor = Compactor(llm)

        messages = [
            {"role": "system", "content": "System prompt"},
        ]
        # Add 30 user/assistant pairs (60 messages)
        for i in range(30):
            messages.append({"role": "user", "content": f"user msg {i}"})
            messages.append({"role": "assistant", "content": f"assistant msg {i}"})

        result = await compactor.tier2_summarize(messages)

        # LLM should have been called
        llm.generate.assert_called_once()
        prompt_arg = llm.generate.call_args[0][0]
        assert "Summarize this conversation history" in prompt_arg

        # Result should have: system + summary + last 20 messages
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "System prompt"
        assert result[1]["role"] == "system"
        assert "[Conversation summary]" in result[1]["content"]
        assert "This is the summary." in result[1]["content"]
        # 1 system + 1 summary + 20 recent = 22
        assert len(result) == 22

    @pytest.mark.asyncio
    async def test_compact_green_noop(self):
        """GREEN level returns messages unchanged."""
        llm = make_llm_client()
        compactor = Compactor(llm)
        messages = make_messages(5)
        result = await compactor.compact(messages, CompactionLevel.GREEN)
        assert result == messages

    @pytest.mark.asyncio
    async def test_compact_yellow_masks(self):
        """YELLOW applies tier1 masking only."""
        llm = make_llm_client()
        compactor = Compactor(llm)

        messages = []
        for i in range(15):
            messages.append({"role": "user", "content": f"question {i}"})
            messages.append({"role": "tool", "content": f"output {i}\nextra"})

        result = await compactor.compact(messages, CompactionLevel.YELLOW)

        # LLM should NOT have been called (tier1 only)
        llm.generate.assert_not_called()

        # Old tool messages should be masked
        masked_count = sum(
            1 for m in result if "[Output masked, was" in m.get("content", "")
        )
        assert masked_count > 0


# ---------------------------------------------------------------------------
# Workspace tests
# ---------------------------------------------------------------------------

class TestWorkspaceMemory:
    @pytest.mark.asyncio
    async def test_save_load_state(self):
        """Save then load returns same data."""
        state_data = {"step": 3, "phase": "coding", "files": ["main.py"]}
        stored = {}

        async def run_side_effect(cmd: str):
            if cmd.startswith("cat > /workspace/context/state.json"):
                # Extract the JSON between the heredoc markers
                lines = cmd.split("\n")
                json_lines = lines[1:-1]  # skip first and last (heredoc markers)
                stored["json"] = "\n".join(json_lines)
                return ""
            elif "cat /workspace/context/state.json" in cmd:
                return stored.get("json", "")
            return ""

        executor = AsyncMock()
        executor.run.side_effect = run_side_effect

        workspace = WorkspaceMemory(executor)
        await workspace.save_state(state_data)
        result = await workspace.load_state()

        assert result == state_data


# ---------------------------------------------------------------------------
# Session tests
# ---------------------------------------------------------------------------

class TestSessionManager:
    @pytest.mark.asyncio
    async def test_session_fresh_start(self):
        """No state.json => returns None, creates workspace."""
        executor = make_executor(state_json="")
        workspace = WorkspaceMemory(executor)
        session = SessionManager(workspace)

        result = await session.start_session()

        assert result is None
        # init_workspace should have been called (mkdir)
        calls = [str(c) for c in executor.run.call_args_list]
        assert any("mkdir" in c for c in calls)

    @pytest.mark.asyncio
    async def test_session_resume(self):
        """state.json exists => returns state dict."""
        state = {"step": 5, "phase": "testing"}
        executor = make_executor(state_json=json.dumps(state))
        workspace = WorkspaceMemory(executor)
        session = SessionManager(workspace)

        result = await session.start_session()

        assert result == state
