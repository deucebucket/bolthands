"""FastAPI application with WebSocket streaming for the BoltHands agent."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from bolthands.agent import AgentController, AgentStatus
from bolthands.config import BoltHandsConfig
from bolthands.llm import LLMClient
from bolthands.tools import create_registry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class TaskRequest(BaseModel):
    """Body for POST /task."""

    task: str
    sandbox_image: str | None = None


class TaskResponse(BaseModel):
    """Response for POST /task."""

    task_id: str


class CancelResponse(BaseModel):
    """Response for DELETE /task/{task_id}."""

    status: str


# ---------------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------------

active_tasks: dict[str, tuple[AgentController, asyncio.Task]] = {}  # type: ignore[type-arg]

# ---------------------------------------------------------------------------
# Lifespan (replaces deprecated on_event)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    """Manage startup / shutdown."""
    yield
    # Shutdown: cancel all active tasks
    for task_id, (controller, bg_task) in list(active_tasks.items()):
        try:
            await controller.cancel()
            bg_task.cancel()
            try:
                await asyncio.wait_for(bg_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass
        except Exception as exc:
            logger.warning("Error cleaning up task %s: %s", task_id, exc)
    active_tasks.clear()


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

config = BoltHandsConfig()
app = FastAPI(title="BoltHands Agent", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/task", response_model=TaskResponse)
async def create_task(request: TaskRequest) -> TaskResponse:
    """Create a new agent task and start it in the background."""
    llm = LLMClient(base_url=config.llm_url)
    registry = create_registry()
    controller = AgentController(
        config=config,
        llm_client=llm,
        tool_registry=registry,
        sandbox_image=request.sandbox_image,
    )

    # Wire up event queue for WebSocket consumers
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()

    def _on_event_callback(envelope: dict) -> None:
        try:
            queue.put_nowait(envelope)
        except asyncio.QueueFull:
            logger.warning("Event queue full for task %s", controller.task_id)

    controller.on_event = _on_event_callback

    # Store queue on controller for WebSocket access
    controller._event_queue = queue  # type: ignore[attr-defined]

    async def _run_and_cleanup(task_id: str, ctrl: AgentController, task_text: str):
        try:
            await ctrl.run(task_text)
        finally:
            active_tasks.pop(task_id, None)

    bg_task = asyncio.create_task(
        _run_and_cleanup(controller.task_id, controller, request.task)
    )
    active_tasks[controller.task_id] = (controller, bg_task)

    return TaskResponse(task_id=controller.task_id)


@app.get("/task/{task_id}/status", response_model=AgentStatus)
async def get_task_status(task_id: str) -> AgentStatus:
    """Return the current status of a task."""
    entry = active_tasks.get(task_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Task not found")
    controller, _ = entry
    return controller.status


@app.delete("/task/{task_id}", response_model=CancelResponse)
async def cancel_task(task_id: str) -> CancelResponse:
    """Cancel a running task."""
    entry = active_tasks.get(task_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Task not found")
    controller, bg_task = entry

    await controller.cancel()
    bg_task.cancel()
    try:
        await asyncio.wait_for(bg_task, timeout=5.0)
    except (asyncio.CancelledError, asyncio.TimeoutError):
        pass

    active_tasks.pop(task_id, None)
    return CancelResponse(status="cancelled")


@app.websocket("/ws/{task_id}")
async def websocket_stream(websocket: WebSocket, task_id: str) -> None:
    """Stream task events to a WebSocket client."""
    entry = active_tasks.get(task_id)
    if entry is None:
        await websocket.close(code=4004, reason="Task not found")
        return

    controller, bg_task = entry
    queue: asyncio.Queue[dict[str, Any]] = getattr(controller, "_event_queue", None)  # type: ignore[assignment]
    if queue is None:
        await websocket.close(code=4004, reason="No event queue")
        return

    await websocket.accept()

    try:
        while True:
            # Wait for either an event or the task to finish
            get_event = asyncio.create_task(queue.get())
            done, pending = await asyncio.wait(
                {get_event, bg_task},
                return_when=asyncio.FIRST_COMPLETED,
            )

            if get_event in done:
                event = get_event.result()
                await websocket.send_json(event)
            else:
                get_event.cancel()

            # If background task is done, drain remaining events and close
            if bg_task in done:
                # Drain any remaining events in the queue
                while not queue.empty():
                    try:
                        event = queue.get_nowait()
                        await websocket.send_json(event)
                    except asyncio.QueueEmpty:
                        break
                # Send final status
                await websocket.send_json({
                    "type": "done",
                    "status": controller.status.model_dump(),
                })
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected for task %s", task_id)
    except Exception as exc:
        logger.exception("WebSocket error for task %s: %s", task_id, exc)
    finally:
        await websocket.close()
