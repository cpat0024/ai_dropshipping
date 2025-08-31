from __future__ import annotations

import asyncio
import types

import pytest

from aliexpress_scraper.parsers import parse_product_id


@pytest.mark.asyncio
async def test_smoke_no_network(monkeypatch):
    """Non-invasive smoke test: exercises retryable coroutine with backoff without hitting network."""

    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise RuntimeError("transient")
        return "ok"

    # Simple manual backoff loop to avoid depending on decorators for test stability
    retries = 3
    delay = 0.01
    for _ in range(retries):
        try:
            res = await flaky()
            assert res == "ok"
            break
        except RuntimeError:
            await asyncio.sleep(delay)
            delay *= 2
    else:
        pytest.fail("flaky did not succeed")

    # Also check parser helper
    assert parse_product_id("https://www.aliexpress.com/item/1005001234567890.html") == "1005001234567890"
