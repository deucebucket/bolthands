"""Tests for the agent controller and state machine."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bolthands.agent.controller import AgentController
from bolthands.agent.state import AgentState, AgentStatus
from bolthands.config import BoltHandsConfig
from bolthands.events.observations import CmdOutputObservation, ThinkObservation
from bolthands.tools import create_registry


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------

class MockLLMClient:
    """LLM client that returns predefined responses in sequence."""

    def __init__(self, responses: list[dict]):
        self.responses = list(responses)
        self.call_count = 0

    async def chat(self, messages, tools=None, temperature=0.1):
        if self.call_count >= len(self.responses):
            # Safety: return a finish if we run out of responses
            return _finish_response("out of responses")
        resp = self.responses[self.call_count]
        self.call_count += 1
        if isinstance(resp, Exception):
            raise resp
        return resp


class MockExecutor:
    """Executor that returns predefined outputs in sequence."""

    def __init__(self, outputs: list[tuple[str, str, int]]):
        self.outputs = list(outputs)
        self.call_count = 0

    async def run(self, command: str, timeout: int = 30) -> tuple[str, str, int]:
        if self.call_count >= len(self.outputs):
            return ("", "", 0)
        out = self.outputs[self.call_count]
        self.call_count += 1
        return out


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _tool_call_response(
    name: str, arguments: dict, content: str = ""
) -> dict:
    """Build a mock LLM response with a native tool call."""
    return {
        "role": "assistant",
        "content": content,
        "tool_calls": [
            {
                "id": "call_mock",
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments),
                },
            }
        ],
    }


def _finish_response(message: str = "Done") -> dict:
    return _tool_call_response("finish", {"message": message})


def _bash_response(command: str, content: str = "") -> dict:
    return _tool_call_response("execute_bash", {"command": command}, content)


def _think_response(thought: str) -> dict:
    return _tool_call_response("think", {"thought": thought})


def _plain_text_response(text: str) -> dict:
    return {"role": "assistant", "content": text}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def config():
    return BoltHandsConfig(max_iterations=10, stuck_threshold=3)


@pytest.fixture
def registry():
    return create_registry()


def _make_controller(
    config: BoltHandsConfig,
    llm_client: MockLLMClient,
    registry,
    executor: MockExecutor | None = None,
) -> AgentController:
    """Create a controller with sandbox mocked out."""
    controller = AgentController(
        config=config,
        llm_client=llm_client,
        tool_registry=registry,
    )
    # Inject mock executor so real Docker is never used
    if executor is not None:
        controller._executor = executor
    return controller


# Patch sandbox to avoid Docker calls
_SANDBOX_PATCH_CREATE = "bolthands.agent.controller.SandboxContainer.create"
_SANDBOX_PATCH_START = "bolthands.agent.controller.SandboxContainer.start"
_SANDBOX_PATCH_STOP = "bolthands.agent.controller.SandboxContainer.stop"
_SANDBOX_PATCH_REMOVE = "bolthands.agent.controller.SandboxContainer.remove"


_SESSION_PATCH_START = "bolthands.agent.controller.SessionManager.start_session"
_SESSION_PATCH_END = "bolthands.agent.controller.SessionManager.end_session"
_WORKSPACE_PATCH_INIT = "bolthands.agent.controller.WorkspaceMemory"


@pytest.fixture
def mock_sandbox():
    """Patch all sandbox Docker methods and session/workspace calls to be no-ops."""
    with (
        patch(_SANDBOX_PATCH_CREATE, new_callable=AsyncMock) as m_create,
        patch(_SANDBOX_PATCH_START, new_callable=AsyncMock) as m_start,
        patch(_SANDBOX_PATCH_STOP, new_callable=AsyncMock) as m_stop,
        patch(_SANDBOX_PATCH_REMOVE, new_callable=AsyncMock) as m_remove,
        patch(_SESSION_PATCH_START, new_callable=AsyncMock, return_value=None),
        patch(_SESSION_PATCH_END, new_callable=AsyncMock),
    ):
        yield {
            "create": m_create,
            "start": m_start,
            "stop": m_stop,
            "remove": m_remove,
        }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAgentState:
    """Tests for AgentState and AgentStatus models."""

    def test_state_values(self):
        assert AgentState.IDLE == "idle"
        assert AgentState.RUNNING == "running"
        assert AgentState.PAUSED == "paused"
        assert AgentState.FINISHED == "finished"
        assert AgentState.ERROR == "error"

    def test_status_defaults(self):
        status = AgentStatus(
            task_id="test-123",
            state=AgentState.IDLE,
            iteration=0,
            max_iterations=25,
        )
        assert status.last_action_type is None
        assert status.error_message is None

    def test_status_with_error(self):
        status = AgentStatus(
            task_id="test-123",
            state=AgentState.ERROR,
            iteration=5,
            max_iterations=25,
            error_message="something broke",
        )
        assert status.error_message == "something broke"


class TestAgentController:
    """Tests for the AgentController main loop."""

    @pytest.mark.asyncio
    async def test_single_step_finish(self, config, registry, mock_sandbox):
        """LLM returns finish action -> state=FINISHED, iteration=1."""
        llm = MockLLMClient([_finish_response("Task complete")])
        controller = _make_controller(config, llm, registry)

        status = await controller.run("Do something")

        assert status.state == AgentState.FINISHED
        assert status.iteration == 1
        assert status.last_action_type == "finish"

    @pytest.mark.asyncio
    async def test_multi_step(self, config, registry, mock_sandbox):
        """LLM returns bash action -> result -> finish -> state=FINISHED."""
        llm = MockLLMClient([
            _bash_response("echo hello"),
            _finish_response("Done"),
        ])
        executor = MockExecutor([("hello\n", "", 0)])
        controller = _make_controller(config, llm, registry, executor)

        # Patch tool execution to use our mock executor
        original_execute = registry.execute

        async def mock_execute(name, args, exec_):
            return await original_execute(name, args, executor)

        registry.execute = mock_execute

        status = await controller.run("Run a command")

        assert status.state == AgentState.FINISHED
        assert status.iteration == 2
        assert llm.call_count == 2

    @pytest.mark.asyncio
    async def test_error_recovery(self, config, registry, mock_sandbox):
        """LLM returns bash -> fails -> bash again -> succeeds -> finish."""
        llm = MockLLMClient([
            _bash_response("bad_command"),
            _bash_response("good_command"),
            _finish_response("Fixed it"),
        ])
        executor = MockExecutor([
            ("", "command not found", 1),
            ("success", "", 0),
        ])
        controller = _make_controller(config, llm, registry, executor)

        original_execute = registry.execute

        async def mock_execute(name, args, exec_):
            return await original_execute(name, args, executor)

        registry.execute = mock_execute

        status = await controller.run("Run commands")

        assert status.state == AgentState.FINISHED
        assert status.iteration == 3
        assert llm.call_count == 3

    @pytest.mark.asyncio
    async def test_max_iterations(self, config, registry, mock_sandbox):
        """LLM keeps returning bash, never finishes -> ERROR after max_iterations."""
        config.max_iterations = 3
        responses = [_bash_response(f"echo {i}") for i in range(10)]
        llm = MockLLMClient(responses)
        executor = MockExecutor([("output", "", 0)] * 10)
        controller = _make_controller(config, llm, registry, executor)

        original_execute = registry.execute

        async def mock_execute(name, args, exec_):
            return await original_execute(name, args, executor)

        registry.execute = mock_execute

        status = await controller.run("Infinite task")

        assert status.state == AgentState.ERROR
        assert status.error_message == "Max iterations reached"
        assert status.iteration == 3

    @pytest.mark.asyncio
    async def test_stuck_detection(self, config, registry, mock_sandbox):
        """LLM returns same bash("ls") 3 times -> ERROR "stuck"."""
        config.stuck_threshold = 3
        responses = [_bash_response("ls")] * 5
        llm = MockLLMClient(responses)
        executor = MockExecutor([("file1\nfile2", "", 0)] * 5)
        controller = _make_controller(config, llm, registry, executor)

        original_execute = registry.execute

        async def mock_execute(name, args, exec_):
            return await original_execute(name, args, executor)

        registry.execute = mock_execute

        status = await controller.run("List files")

        assert status.state == AgentState.ERROR
        assert "stuck" in status.error_message.lower()

    @pytest.mark.asyncio
    async def test_think_action(self, config, registry, mock_sandbox):
        """LLM returns think -> no executor call -> continues to next LLM call."""
        llm = MockLLMClient([
            _think_response("Let me analyze this..."),
            _finish_response("Done thinking"),
        ])
        executor = MockExecutor([])
        controller = _make_controller(config, llm, registry, executor)

        status = await controller.run("Think about it")

        assert status.state == AgentState.FINISHED
        assert status.iteration == 2
        # Executor should not have been called
        assert executor.call_count == 0

    @pytest.mark.asyncio
    async def test_history_truncation(self, config, registry, mock_sandbox):
        """Run enough iterations that history > 50, verify oldest pairs dropped."""
        config.max_iterations = 30
        responses = [_bash_response(f"echo {i}") for i in range(28)]
        responses.append(_finish_response("Done"))
        llm = MockLLMClient(responses)
        executor = MockExecutor([("output", "", 0)] * 28)
        controller = _make_controller(config, llm, registry, executor)

        original_execute = registry.execute

        async def mock_execute(name, args, exec_):
            return await original_execute(name, args, executor)

        registry.execute = mock_execute

        status = await controller.run("Run many commands")

        assert status.state == AgentState.FINISHED
        # History should have been truncated to <= 50
        assert len(controller._history) <= 50
        # First two messages should still be system + user
        assert controller._history[0]["role"] == "system"
        assert controller._history[1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_cancel(self, config, registry, mock_sandbox):
        """Call cancel -> state=ERROR "Cancelled"."""
        llm = MockLLMClient([])
        controller = _make_controller(config, llm, registry)

        # Set state to RUNNING to simulate a running agent
        controller.status.state = AgentState.RUNNING

        await controller.cancel()

        assert controller.status.state == AgentState.ERROR
        assert controller.status.error_message == "Cancelled"

    @pytest.mark.asyncio
    async def test_llm_connect_error(self, config, registry, mock_sandbox):
        """Mock LLM raises ConnectError -> state=ERROR."""
        llm = MockLLMClient([httpx.ConnectError("Connection refused")])
        controller = _make_controller(config, llm, registry)

        status = await controller.run("Try to connect")

        assert status.state == AgentState.ERROR
        assert "not reachable" in status.error_message.lower()

    @pytest.mark.asyncio
    async def test_llm_other_error(self, config, registry, mock_sandbox):
        """Mock LLM raises generic exception -> state=ERROR with message."""
        llm = MockLLMClient([RuntimeError("Something unexpected")])
        controller = _make_controller(config, llm, registry)

        status = await controller.run("Fail")

        assert status.state == AgentState.ERROR
        assert "Something unexpected" in status.error_message

    @pytest.mark.asyncio
    async def test_plain_text_response(self, config, registry, mock_sandbox):
        """LLM returns plain text (no tool call) -> added to history, loop continues."""
        llm = MockLLMClient([
            _plain_text_response("I'm thinking about how to solve this..."),
            _finish_response("Done"),
        ])
        controller = _make_controller(config, llm, registry)

        status = await controller.run("Solve it")

        assert status.state == AgentState.FINISHED
        assert llm.call_count == 2

    @pytest.mark.asyncio
    async def test_event_emission(self, config, registry, mock_sandbox):
        """Verify events are emitted with correct envelope structure."""
        llm = MockLLMClient([_finish_response("Done")])
        controller = _make_controller(config, llm, registry)

        events = []
        controller.on_event = lambda e: events.append(e)

        status = await controller.run("Emit events")

        assert status.state == AgentState.FINISHED
        assert len(events) >= 1
        event = events[0]
        assert "type" in event
        assert "timestamp" in event
        assert "iteration" in event
        assert "data" in event

    @pytest.mark.asyncio
    async def test_sandbox_cleanup_on_error(self, config, registry, mock_sandbox):
        """Verify sandbox is stopped and removed even on error."""
        llm = MockLLMClient([httpx.ConnectError("fail")])
        controller = _make_controller(config, llm, registry)

        await controller.run("Fail and cleanup")

        mock_sandbox["stop"].assert_called_once()
        mock_sandbox["remove"].assert_called_once()

    @pytest.mark.asyncio
    async def test_sandbox_cleanup_on_success(self, config, registry, mock_sandbox):
        """Verify sandbox is stopped and removed on success."""
        llm = MockLLMClient([_finish_response("Done")])
        controller = _make_controller(config, llm, registry)

        await controller.run("Succeed and cleanup")

        mock_sandbox["stop"].assert_called_once()
        mock_sandbox["remove"].assert_called_once()

    @pytest.mark.asyncio
    async def test_initial_state_is_idle(self, config, registry):
        """Controller starts in IDLE state."""
        llm = MockLLMClient([])
        controller = _make_controller(config, llm, registry)
        assert controller.status.state == AgentState.IDLE

    @pytest.mark.asyncio
    async def test_task_id_is_uuid(self, config, registry):
        """Controller generates a UUID task_id."""
        import uuid
        llm = MockLLMClient([])
        controller = _make_controller(config, llm, registry)
        # Should not raise
        uuid.UUID(controller.task_id)

    @pytest.mark.asyncio
    async def test_context_compaction(self, config, registry, mock_sandbox):
        """When monitor returns YELLOW, compactor.compact is called."""
        from bolthands.context.monitor import CompactionLevel

        llm = MockLLMClient([_finish_response("Done")])
        controller = _make_controller(config, llm, registry)

        # Mock the monitor to return YELLOW so compaction triggers
        controller.monitor.check_budget = MagicMock(return_value=CompactionLevel.YELLOW)
        controller.compactor.compact = AsyncMock(side_effect=lambda msgs, level: msgs)

        status = await controller.run("Test compaction")

        assert status.state == AgentState.FINISHED
        controller.monitor.check_budget.assert_called()
        controller.compactor.compact.assert_called_once()
        # Verify the level passed to compact was YELLOW
        call_args = controller.compactor.compact.call_args
        assert call_args[0][1] == CompactionLevel.YELLOW

    @pytest.mark.asyncio
    async def test_session_resume(self, config, registry, mock_sandbox):
        """When workspace has existing state, resume prompt is prepended to task."""
        llm = MockLLMClient([_finish_response("Done")])
        controller = _make_controller(config, llm, registry)

        saved_state = {"status": "finished", "summary": "Previous work"}

        with (
            patch(
                "bolthands.agent.controller.SessionManager.start_session",
                new_callable=AsyncMock,
                return_value=saved_state,
            ),
            patch(
                "bolthands.agent.controller.SessionManager.end_session",
                new_callable=AsyncMock,
            ),
            patch(
                "bolthands.agent.controller.SessionManager.build_resume_prompt",
                return_value="Resuming from previous session.",
            ) as mock_resume,
        ):
            status = await controller.run("Continue working")

            assert status.state == AgentState.FINISHED
            mock_resume.assert_called_once_with(saved_state)
            # The user message should contain both resume prompt and original task
            user_msg = controller._history[1]["content"]
            assert "Resuming from previous session." in user_msg
            assert "Continue working" in user_msg
