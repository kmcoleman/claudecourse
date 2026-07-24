"""Mandatory live-API green light: proves ANTHROPIC_API_KEY + billing work.
One real Claude call. Marked `api` so `pytest -m "not api"` skips it for CI.

Note: the Agent SDK does NOT auto-load .env; the key must be in the environment
(the bootstrap exports it, or use `python-dotenv`/`set` before running)."""
import asyncio
import os

import pytest

from claude_agent_sdk import query


def _collect_text() -> str:
    async def run():
        chunks = []
        async for message in query(prompt="Reply with the exact word: READY"):
            content = getattr(message, "content", None)
            if content:
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        chunks.append(text)
        return "".join(chunks)
    return asyncio.run(run())


@pytest.mark.api
def test_claude_api_responds():
    assert os.environ.get("ANTHROPIC_API_KEY"), \
        "ANTHROPIC_API_KEY not set — copy .env.example to .env and add your key, " \
        "then export it into the environment before running the API check."
    out = _collect_text()
    assert out.strip(), "no text returned from Claude — check key, billing, and network"
