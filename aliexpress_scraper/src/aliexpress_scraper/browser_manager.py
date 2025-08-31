from __future__ import annotations

"""Async Playwright browser/context manager with UA rotation and proxy support."""
import asyncio
import json
import random
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator, Optional

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from .logger import get_logger

DEFAULT_UAS = [
    # A small, diverse UA set; can be replaced via --user-agent-list
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
]


class BrowserManager:
    """High-level manager to own Playwright lifecycle and contexts.

    Usage:
        async with BrowserManager(headless=True, proxy=None, timeout=30, ua_list_path=None) as bm:
            page = await bm.new_page()
    """

    def __init__(
        self,
        *,
        headless: bool = True,
        proxy: Optional[str] = None,
        timeout: float = 30.0,
        ua_list_path: Optional[Path] = None,
        debug: bool = False,
    ) -> None:
        self.headless = headless
        self.proxy = proxy
        self.timeout = timeout
        self.ua_list_path = ua_list_path
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._logger = get_logger(debug=debug)
        self._uas = self._load_ua_list()

    def _load_ua_list(self) -> list[str]:
        if self.ua_list_path and self.ua_list_path.exists():
            try:
                content = self.ua_list_path.read_text(encoding="utf-8")
                if self.ua_list_path.suffix.lower() == ".json":
                    data = json.loads(content)
                    if isinstance(data, list):
                        return [str(x) for x in data if isinstance(x, (str, int, float))]
                return [line.strip() for line in content.splitlines() if line.strip()]
            except Exception as e:
                self._logger.warning("Failed to load UA list from %s: %s", self.ua_list_path, e)
        return DEFAULT_UAS[:]

    async def __aenter__(self) -> "BrowserManager":
        self._playwright = await async_playwright().start()
        launch_kwargs = {"headless": self.headless}
        if self.proxy:
            launch_kwargs["proxy"] = {"server": self.proxy}
        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._playwright:
                await self._playwright.stop()

    async def new_context(self) -> BrowserContext:
        assert self._browser is not None
        ua = random.choice(self._uas)
        ctx = await self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 900},
            java_script_enabled=True,
        )
        ctx.set_default_timeout(self.timeout * 1000)
        return ctx

    async def new_page(self) -> Page:
        ctx = await self.new_context()
        page = await ctx.new_page()
        return page
