from __future__ import annotations

"""Main orchestrator for the scraper.

Exposes a `Scraper` class used by CLI and programmatic API.
"""
import asyncio
from pathlib import Path
from typing import List

from .browser_manager import BrowserManager
from .config import Config
from .exceptions import AntiBotDetected, RobotsDisallowed, ScraperError
from .logger import get_logger
from .models import Product, ScrapeResult, Seller
from .output import download_images
from .product import scrape_product
from .search import discover_sellers
from .seller import scrape_seller
from .utils import check_robots_txt, exponential_backoff_retry, random_sleep


class Scraper:
    """Scraper orchestrates search, seller, and product scraping."""

    def __init__(self, config: Config) -> None:
        self.cfg = config
        self.logger = get_logger(debug=config.debug)
        self._bm: BrowserManager | None = None
        self._sem = asyncio.Semaphore(self.cfg.concurrency)

    async def __aenter__(self) -> "Scraper":
        self._bm = BrowserManager(
            headless=self.cfg.headless,
            proxy=self.cfg.proxy,
            timeout=self.cfg.timeout,
            ua_list_path=self.cfg.user_agent_list,
            debug=self.cfg.debug,
        )
        await self._bm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[override]
        if self._bm:
            await self._bm.__aexit__(exc_type, exc, tb)

    async def run(self) -> ScrapeResult:
        assert self._bm is not None
        page = await self._bm.new_page()

        # Respect robots if requested
        if self.cfg.respect_robots:
            start_url = "https://www.aliexpress.com/wholesale?SearchText=test"
            if not check_robots_txt(start_url):
                raise RobotsDisallowed("Robots.txt disallows scraping search page")

        try:
            sellers_info = await discover_sellers(
                page,
                self.cfg.query,
                limit=self.cfg.limit,
                max_suppliers=self.cfg.max_suppliers,
            )
        except AntiBotDetected as e:
            if self.cfg.abort_on_antibot:
                raise
            self.logger.warning("Anti-bot detected during search: %s (continuing with none)", e)
            sellers_info = []

        result = ScrapeResult(query=self.cfg.query)

        async def handle_seller(seller_name: str, seller_url: str, product_urls: List[str]) -> None:
            await random_sleep(0.2, 0.8)
            p = await self._bm.new_page()  # type: ignore[union-attr]
            async with self._sem:
                seller = await scrape_seller(p, seller_name, seller_url)
            if not seller:
                return

            # Limit products per seller
            urls = product_urls[: self.cfg.max_products_per_seller]

            async def handle_product(url: str) -> Product | None:
                await random_sleep(0.2, 0.8)
                pg = await self._bm.new_page()  # type: ignore[union-attr]
                async with self._sem:
                    prod = await scrape_product(pg, url)
                return prod

            prods = await asyncio.gather(*[handle_product(u) for u in urls], return_exceptions=True)
            for pr in prods:
                if isinstance(pr, Exception):
                    self.logger.warning("Product scrape failed: %s", pr)
                elif pr:
                    seller.products.append(pr)

            result.suppliers.append(seller)

        async def safe_handle_seller(n: str, u: str, ps: list[str]):
            try:
                await handle_seller(n, u, ps)
            except AntiBotDetected as e:
                if self.cfg.abort_on_antibot:
                    raise
                self.logger.warning("Anti-bot detected for seller %s: %s (skipping)", u, e)

        await asyncio.gather(*(safe_handle_seller(n, u, ps) for (n, u, ps) in sellers_info), return_exceptions=False)

        if self.cfg.download_images:
            download_images(Path("images"), result.suppliers)

        return result
