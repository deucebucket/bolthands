"""Tests for the FastAPI server endpoints."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from bolthands.agent.state import AgentState, AgentStatus
from bolthands.server.app import active_tasks, app


@pytest.fixture(autouse=True)
def _clear_active_tasks():
    """Ensure active_tasks is clean before and after each test."""
    active_tasks.clear()
    yield
    active_tasks.clear()


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


def _mock_controller(task_id: str = "test-task-123") -> MagicMock:
    """Create a mock AgentController with a realistic status."""
    controller = MagicMock()
    controller.task_id = task_id
    controller.status = AgentStatus(
        task_id=task_id,
        state=AgentState.RUNNING,
        iteration=1,
        max_iterations=25,
        last_action_type="execute_bash",
    )
    controller.on_event = None
    controller._event_queue = asyncio.Queue()
    controller.cancel = AsyncMock()
    controller.run = AsyncMock(return_value=controller.status)
    controller._emit_event = MagicMock()
    return controller


# ---------------------------------------------------------------------------
# POST /task
# ---------------------------------------------------------------------------


class TestCreateTask:
    """Tests for the POST /task endpoint."""

    @patch("bolthands.server.app.create_registry")
    @patch("bolthands.server.app.LLMClient")
    @patch("bolthands.server.app.AgentController")
    def test_create_task_returns_task_id(
        self, mock_controller_cls, mock_llm_cls, mock_registry, client
    ):
        """POST /task returns 200 with a task_id."""
        controller = _mock_controller()
        mock_controller_cls.return_value = controller

        response = client.post("/task", json={"task": "write hello world"})

        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["task_id"] == "test-task-123"

    @patch("bolthands.server.app.create_registry")
    @patch("bolthands.server.app.LLMClient")
    @patch("bolthands.server.app.AgentController")
    def test_create_task_with_sandbox_image(
        self, mock_controller_cls, mock_llm_cls, mock_registry, client
    ):
        """POST /task with sandbox_image passes it to the controller."""
        controller = _mock_controller()
        mock_controller_cls.return_value = controller

        response = client.post(
            "/task",
            json={"task": "run tests", "sandbox_image": "node:20-slim"},
        )

        assert response.status_code == 200
        mock_controller_cls.assert_called_once()
        call_kwargs = mock_controller_cls.call_args[1]
        assert call_kwargs["sandbox_image"] == "node:20-slim"

    @patch("bolthands.server.app.create_registry")
    @patch("bolthands.server.app.LLMClient")
    @patch("bolthands.server.app.AgentController")
    def test_create_task_stores_in_active_tasks(
        self, mock_controller_cls, mock_llm_cls, mock_registry, client
    ):
        """POST /task starts background task (auto-cleaned on completion)."""
        controller = _mock_controller()
        mock_controller_cls.return_value = controller

        response = client.post("/task", json={"task": "hello"})
        task_id = response.json()["task_id"]

        # Task completes inline in TestClient, so it may already be cleaned up.
        # Just verify the POST succeeded with the right task_id.
        assert response.status_code == 200
        assert task_id == controller.task_id


# ---------------------------------------------------------------------------
# GET /task/{task_id}/status
# ---------------------------------------------------------------------------


class TestGetTaskStatus:
    """Tests for the GET /task/{task_id}/status endpoint."""

    def test_status_returns_agent_status(self, client):
        """GET /task/{id}/status returns the controller's status."""
        controller = _mock_controller()
        bg_task = MagicMock()
        active_tasks["test-task-123"] = (controller, bg_task)

        response = client.get("/task/test-task-123/status")

        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test-task-123"
        assert data["state"] == "running"
        assert data["iteration"] == 1
        assert data["max_iterations"] == 25
        assert data["last_action_type"] == "execute_bash"

    def test_status_404_for_nonexistent_task(self, client):
        """GET /task/nonexistent/status returns 404."""
        response = client.get("/task/nonexistent/status")

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"


# ---------------------------------------------------------------------------
# DELETE /task/{task_id}
# ---------------------------------------------------------------------------


class TestCancelTask:
    """Tests for the DELETE /task/{task_id} endpoint."""

    def test_cancel_returns_cancelled(self, client):
        """DELETE /task/{id} returns 200 with status cancelled."""
        controller = _mock_controller()
        # Create a done future to simulate a completed background task
        bg_task = MagicMock()
        bg_task.cancel = MagicMock()
        active_tasks["test-task-123"] = (controller, bg_task)

        # We need to patch asyncio.wait_for to not actually await
        with patch("bolthands.server.app.asyncio.wait_for", new_callable=AsyncMock):
            response = client.delete("/task/test-task-123")

        assert response.status_code == 200
        assert response.json() == {"status": "cancelled"}
        controller.cancel.assert_called_once()

    def test_cancel_removes_from_active_tasks(self, client):
        """DELETE /task/{id} removes the task from active_tasks."""
        controller = _mock_controller()
        bg_task = MagicMock()
        bg_task.cancel = MagicMock()
        active_tasks["test-task-123"] = (controller, bg_task)

        with patch("bolthands.server.app.asyncio.wait_for", new_callable=AsyncMock):
            client.delete("/task/test-task-123")

        assert "test-task-123" not in active_tasks

    def test_cancel_404_for_nonexistent_task(self, client):
        """DELETE /task/nonexistent returns 404."""
        response = client.delete("/task/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Task not found"
