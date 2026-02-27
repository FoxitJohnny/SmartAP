"""
Lightweight ChatAgent replacement.

The ``agent-framework-azure-ai`` pre-release package frequently changes its
public API between versions.  Rather than pinning to a specific nightly build,
this module provides a thin wrapper around the ``openai`` ``AsyncOpenAI`` client
that exposes the same ``.chat()`` / ``.run_stream()`` interface our agents use.

If the real ``ChatAgent`` is available it will be re-exported; otherwise the
local fallback is used transparently.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response wrappers (match the shapes our agents expect)
# ---------------------------------------------------------------------------

@dataclass
class ChatResponse:
    """Wrapper returned by ``ChatAgent.chat()``."""
    content: str


@dataclass
class StreamChunk:
    """Wrapper yielded by ``ChatAgent.run_stream()``."""
    text: Optional[str] = None


# ---------------------------------------------------------------------------
# ChatAgent – local fallback
# ---------------------------------------------------------------------------

class _ChatAgentLocal:
    """
    Minimal ChatAgent that delegates to ``AsyncOpenAI``.

    Constructor signature intentionally mirrors the original so existing call
    sites only need an import change.
    """

    def __init__(
        self,
        *,
        async_client: AsyncOpenAI,
        model_id: str,
        name: str = "",
        instructions: str = "",
    ) -> None:
        self._client = async_client
        self._model = model_id
        self.name = name
        self.instructions = instructions

    # -- non-streaming -------------------------------------------------
    async def chat(self, prompt: str) -> ChatResponse:
        """Send a single user message and return the assistant reply."""
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": prompt},
            ],
        )
        content = response.choices[0].message.content or ""
        return ChatResponse(content=content)

    # -- streaming -----------------------------------------------------
    async def run_stream(self, prompt: str) -> AsyncIterator[StreamChunk]:
        """Stream assistant reply chunk-by-chunk."""
        stream = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": prompt},
            ],
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield StreamChunk(text=delta.content)


# ---------------------------------------------------------------------------
# Public re-export – prefer the real one, fall back to local
# ---------------------------------------------------------------------------

try:
    from agent_framework import ChatAgent  # type: ignore[import-untyped]

    logger.debug("Using ChatAgent from agent_framework")
except ImportError:
    ChatAgent = _ChatAgentLocal  # type: ignore[misc,assignment]
    logger.info(
        "agent_framework.ChatAgent not available – using local fallback"
    )

__all__ = ["ChatAgent"]
