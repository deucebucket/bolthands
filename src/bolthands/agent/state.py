"""Agent state machine models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel


class AgentState(str, Enum):
    """Possible states of the agent."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"
    ERROR = "error"


class AgentStatus(BaseModel):
    """Current status of an agent run."""

    task_id: str
    state: AgentState
    iteration: int
    max_iterations: int
    last_action_type: str | None = None
    error_message: str | None = None
