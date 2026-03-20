"""Agent controller — the main loop that coordinates LLM, tools, and sandbox."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from bolthands.agent.state import AgentState, AgentStatus
from bolthands.config import BoltHandsConfig
from bolthands.events.actions import FinishAction, ThinkAction
from bolthands.llm import LLMClient, build_system_prompt, parse_response
from bolthands.sandbox import SandboxContainer, SandboxExecutor
from bolthands.tools import ToolRegistry

logger = logging.getLogger(__name__)


class AgentController:
    """Orchestrates the agent loop: LLM decisions -> tool execution -> observation.

    The controller manages the full lifecycle of a task: creating a sandbox,
    running the agent loop, and cleaning up resources.
    """

    def __init__(
        self,
        config: BoltHandsConfig,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        sandbox_image: str | None = None,
        workspace_dir: str | None = None,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.sandbox_image = sandbox_image or config.sandbox_image
        self.workspace_dir = workspace_dir or "/tmp/bolthands-workspace"

        self.task_id: str = str(uuid.uuid4())
        self.status = AgentStatus(
            task_id=self.task_id,
            state=AgentState.IDLE,
            iteration=0,
            max_iterations=config.max_iterations,
        )
        self.on_event: Callable[[dict], None] | None = None

        self._history: list[dict[str, Any]] = []
        self._sandbox: SandboxContainer | None = None
        self._executor: SandboxExecutor | None = None
        self._call_counter: int = 0

    async def run(self, task: str) -> AgentStatus:
        """Execute the main agent loop for the given task.

        Args:
            task: The user's task description.

        Returns:
            The final AgentStatus after the loop completes or errors.
        """
        try:
            # 1. Create and start sandbox
            self._sandbox = SandboxContainer(
                image=self.sandbox_image,
                workspace_dir=self.workspace_dir,
                memory_limit=self.config.sandbox_memory,
            )
            await self._sandbox.create()
            await self._sandbox.start()
            self._executor = SandboxExecutor(
                self._sandbox,
                max_output_length=self.config.max_output_length,
            )

            # 2. Build system prompt
            system_prompt = build_system_prompt(self.tool_registry.schemas())

            # 3. Initialize history
            self._history = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            # 4. Set state to RUNNING
            self.status.state = AgentState.RUNNING
            self.status.iteration = 0

            # 5. Main loop
            while (
                self.status.state == AgentState.RUNNING
                and self.status.iteration < self.status.max_iterations
            ):
                # a. Check stuck detection
                if self._is_stuck():
                    self.status.state = AgentState.ERROR
                    self.status.error_message = "Agent is stuck: repeating the same action"
                    break

                # b. Call LLM
                try:
                    response = await self.llm_client.chat(
                        self._history,
                        tools=self.tool_registry.schemas(),
                        temperature=0.1,
                    )
                except httpx.ConnectError:
                    self.status.state = AgentState.ERROR
                    self.status.error_message = "LLM server not reachable"
                    break
                except Exception as exc:
                    self.status.state = AgentState.ERROR
                    self.status.error_message = str(exc)
                    break

                # c. Parse response
                action = parse_response(response)

                # d. Plain text — no action
                if action is None:
                    content = response.get("content", "")
                    self._history.append({"role": "assistant", "content": content})
                    self.status.iteration += 1
                    continue

                # e. FinishAction
                if isinstance(action, FinishAction):
                    self.status.state = AgentState.FINISHED
                    self.status.last_action_type = "finish"
                    self._emit_event("finish", {"message": action.message})
                    self.status.iteration += 1
                    break

                # f. ThinkAction
                if isinstance(action, ThinkAction):
                    self._call_counter += 1
                    call_id = f"call_{self._call_counter}"
                    self._history.append({
                        "role": "assistant",
                        "content": action.thought,
                        "tool_calls": [{
                            "id": call_id,
                            "type": "function",
                            "function": {
                                "name": "think",
                                "arguments": json.dumps({"thought": action.thought}),
                            },
                        }],
                    })
                    self._history.append({
                        "role": "tool",
                        "tool_call_id": call_id,
                        "content": json.dumps({"type": "think_result", "thought": action.thought}),
                    })
                    self.status.last_action_type = "think"
                    self._emit_event("think", {"thought": action.thought})
                    self.status.iteration += 1
                    continue

                # g. Execute action via tool registry
                action_name = action.type
                # Map action type to tool name
                tool_name = _ACTION_TYPE_TO_TOOL.get(action_name, action_name)
                args = action.model_dump(exclude={"type"})

                observation = await self.tool_registry.execute(
                    tool_name, args, self._executor
                )

                # h. Truncate observation output
                obs_data = observation.model_dump() if observation else {}
                obs_json = json.dumps(obs_data)
                if len(obs_json) > self.config.max_output_length:
                    obs_json = obs_json[: self.config.max_output_length] + "..."

                # i. Append assistant message (with tool call) + tool response
                self._call_counter += 1
                call_id = f"call_{self._call_counter}"
                thought_text = response.get("content", "") or ""
                self._history.append({
                    "role": "assistant",
                    "content": thought_text,
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(args),
                        },
                    }],
                })
                self._history.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": obs_json,
                })

                self.status.last_action_type = action_name

                # j. Emit event
                self._emit_event("action", {
                    "tool": tool_name,
                    "args": args,
                    "observation": obs_data,
                })

                # Truncate history if needed
                self._truncate_history()

                # k. Increment iteration
                self.status.iteration += 1

            # 6. Max iterations exceeded
            if (
                self.status.state == AgentState.RUNNING
                and self.status.iteration >= self.status.max_iterations
            ):
                self.status.state = AgentState.ERROR
                self.status.error_message = "Max iterations reached"

        except Exception as exc:
            self.status.state = AgentState.ERROR
            self.status.error_message = str(exc)
            logger.exception("Agent loop failed: %s", exc)

        finally:
            # 7. Clean up sandbox
            await self._cleanup_sandbox()

        # 8. Return status
        return self.status

    async def cancel(self) -> None:
        """Cancel the running agent, setting state to ERROR."""
        self.status.state = AgentState.ERROR
        self.status.error_message = "Cancelled"
        await self._cleanup_sandbox()

    def _is_stuck(self) -> bool:
        """Check if the last N actions are identical (same tool + args)."""
        threshold = self.config.stuck_threshold
        # Collect recent tool calls from history
        tool_calls = []
        for msg in self._history:
            if msg.get("role") == "assistant" and msg.get("tool_calls"):
                tc = msg["tool_calls"][0]
                func = tc.get("function", {})
                key = (func.get("name", ""), func.get("arguments", ""))
                tool_calls.append(key)

        if len(tool_calls) < threshold:
            return False

        last_n = tool_calls[-threshold:]
        return all(call == last_n[0] for call in last_n)

    def _truncate_history(self) -> None:
        """If history exceeds 50 messages, remove oldest action+observation pairs.

        Keeps the first 2 messages (system prompt + user task).
        """
        max_history = 50
        while len(self._history) > max_history:
            # Remove the 3rd and 4th messages (first action+observation pair after system+user)
            if len(self._history) > 4:
                del self._history[2:4]
            else:
                break

    def _emit_event(self, event_type: str, data: dict) -> None:
        """Build and emit a WebSocket event envelope."""
        envelope = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iteration": self.status.iteration,
            "data": data,
        }
        if self.on_event is not None:
            self.on_event(envelope)

    async def _cleanup_sandbox(self) -> None:
        """Stop and remove the sandbox container."""
        if self._sandbox is not None:
            try:
                await self._sandbox.stop()
                await self._sandbox.remove(force=True)
            except Exception as exc:
                logger.warning("Failed to clean up sandbox: %s", exc)
            self._sandbox = None
            self._executor = None


# Mapping from action type field to tool registry name
_ACTION_TYPE_TO_TOOL: dict[str, str] = {
    "cmd_run": "execute_bash",
    "file_read": "read_file",
    "file_write": "write_file",
    "file_edit": "edit_file",
    "search_files": "search_files",
    "think": "think",
    "finish": "finish",
}
