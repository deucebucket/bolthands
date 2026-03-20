"""Docker sandbox container management."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

import docker
from docker.models.containers import Container

logger = logging.getLogger(__name__)


class SandboxContainer:
    """Manages a Docker container used as an isolated sandbox for tool execution.

    The container is created with a workspace volume mounted at /workspace,
    host networking, and configurable memory limits. All Docker SDK calls
    are wrapped in asyncio.to_thread() since the SDK is synchronous.

    Usage as an async context manager:
        async with SandboxContainer(image, workspace_dir) as sandbox:
            # container is created and started
            ...
        # container is stopped and removed
    """

    def __init__(
        self,
        image: str,
        workspace_dir: str,
        memory_limit: str = "4g",
    ) -> None:
        self.image = image
        self.workspace_dir = workspace_dir
        self.memory_limit = memory_limit
        self._container: Optional[Container] = None
        self._client: Optional[docker.DockerClient] = None

    async def create(self) -> None:
        """Create the Docker container (does not start it)."""
        self._client = await asyncio.to_thread(docker.from_env)
        self._container = await asyncio.to_thread(
            self._client.containers.create,
            self.image,
            working_dir="/workspace",
            volumes={
                self.workspace_dir: {"bind": "/workspace", "mode": "rw"},
            },
            network_mode="host",
            mem_limit=self.memory_limit,
            detach=True,
            tty=True,
            stdin_open=True,
        )
        logger.info(
            "Created container %s from image %s",
            self._container.short_id,
            self.image,
        )

    async def start(self) -> None:
        """Start the container."""
        if self._container is None:
            raise RuntimeError("Container not created. Call create() first.")
        await asyncio.to_thread(self._container.start)
        logger.info("Started container %s", self._container.short_id)

    async def stop(self) -> None:
        """Stop the container."""
        if self._container is None:
            return
        await asyncio.to_thread(self._container.stop)
        logger.info("Stopped container %s", self._container.short_id)

    async def remove(self, force: bool = True) -> None:
        """Remove the container."""
        if self._container is None:
            return
        await asyncio.to_thread(self._container.remove, force=force)
        logger.info("Removed container %s", self._container.short_id)
        self._container = None

    async def is_running(self) -> bool:
        """Check whether the container is currently running."""
        if self._container is None:
            return False
        await asyncio.to_thread(self._container.reload)
        return self._container.status == "running"

    async def __aenter__(self) -> SandboxContainer:
        await self.create()
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.stop()
        await self.remove(force=True)
