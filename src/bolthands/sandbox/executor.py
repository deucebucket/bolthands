"""Command execution inside a Docker sandbox container."""

from __future__ import annotations

import asyncio
import logging

from bolthands.sandbox.container import SandboxContainer

logger = logging.getLogger(__name__)


class SandboxExecutor:
    """Runs commands inside a SandboxContainer and returns their output.

    All Docker SDK calls are wrapped in asyncio.to_thread() to avoid
    blocking the event loop. Output is decoded from bytes and truncated
    to *max_output_length* characters.
    """

    def __init__(
        self,
        container: SandboxContainer,
        max_output_length: int = 10000,
    ) -> None:
        self.container = container
        self.max_output_length = max_output_length

    async def run(
        self,
        command: str,
        timeout: int = 30,
    ) -> tuple[str, str, int]:
        """Execute *command* inside the sandbox via ``bash -c``.

        Returns:
            A tuple of ``(stdout, stderr, exit_code)``.
            On timeout the return value is ``("", "Command timed out", 1)``.
        """
        if self.container._container is None:
            raise RuntimeError("Container not available. Is the sandbox running?")

        try:
            exit_code, output = await asyncio.wait_for(
                asyncio.to_thread(
                    self.container._container.exec_run,
                    ["bash", "-c", command],
                    demux=True,
                ),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("Command timed out after %ds: %s", timeout, command)
            return ("", "Command timed out", 1)

        stdout = (output[0] or b"").decode("utf-8", errors="replace")
        stderr = (output[1] or b"").decode("utf-8", errors="replace")

        if len(stdout) > self.max_output_length:
            stdout = stdout[: self.max_output_length] + "\n... [truncated]"
        if len(stderr) > self.max_output_length:
            stderr = stderr[: self.max_output_length] + "\n... [truncated]"

        logger.debug(
            "Command exited with %d: %s",
            exit_code,
            command[:100],
        )
        return (stdout, stderr, exit_code)
