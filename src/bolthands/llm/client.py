"""LLM client for communicating with llama.cpp or any OpenAI-compatible server."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """Async client for OpenAI-compatible chat completion endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        timeout: float = 120,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))

    async def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        temperature: float = 0.1,
    ) -> dict:
        """Send a chat completion request and return the assistant message.

        Args:
            messages: List of chat messages in OpenAI format.
            tools: Optional list of tool schemas in OpenAI function calling format.
            temperature: Sampling temperature.

        Returns:
            The first choice's message dict from the response.

        Raises:
            httpx.ConnectError: If the server is unreachable (no retry).
            httpx.HTTPStatusError: If retries are exhausted on server errors.
            httpx.TimeoutException: If retries are exhausted on timeouts.
        """
        payload: dict[str, Any] = {
            "model": "bolthands",
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 4096,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        backoff_delays = [2, 4, 8]
        last_exception: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]

            except httpx.ConnectError:
                # Server unreachable — don't retry
                raise

            except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
                # Only retry on timeout or 500/502/503
                if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code not in (
                    500, 502, 503
                ):
                    raise

                last_exception = exc
                if attempt < self.max_retries - 1:
                    delay = backoff_delays[min(attempt, len(backoff_delays) - 1)]
                    logger.warning(
                        "LLM request failed (attempt %d/%d), retrying in %ds: %s",
                        attempt + 1,
                        self.max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted
        raise last_exception  # type: ignore[misc]

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        await self.client.aclose()
