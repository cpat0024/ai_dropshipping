from __future__ import annotations

"""Search and discovery on AliExpress."""
import asyncio
from typing import List, Tuple
from urllib.parse import quote_plus

from playwright.async_api import Page, Error as PWError

from .exceptions import AntiBotDetected
from .logger import get_logger
from .parsers import detect_antibot
from .utils import random_sleep

SEARCH_URL_TMPL = (
    "https://www.aliexpress.com/wholesale?SearchText={query}&SortType=default&page={page}"
)


async def discover_sellers(
    page: Page,
    query: str,
    *,
    limit: int = 20,
    max_suppliers: int = 5,
) -> List[Tuple[str, str, List[str]]]:
    """Return list of (seller_name, seller_url, product_urls[]) up to max_suppliers.

    Scans search pages until `limit` items processed.
    """
    logger = get_logger()
    sellers: list[Tuple[str, str, list[str]]] = []
    seen_sellers: set[str] = set()

    processed = 0
    page_num = 1
    while processed < limit and len(sellers) < max_suppliers:
        # Retry navigation a few times with simple backoff
        nav_retries = 3
        delay = 0.8
        for attempt in range(nav_retries):
            try:
                await page.goto(
                    SEARCH_URL_TMPL.format(query=quote_plus(query), page=page_num),
                    wait_until="domcontentloaded",
                )
                break
            except PWError:
                if attempt == nav_retries - 1:
                    raise
                await asyncio.sleep(delay)
                delay *= 1.8
        html = await page.content()
        if detect_antibot(html):
            raise AntiBotDetected("Anti-bot page detected during search")

        # Playwright-first selectors; fallback to attribute scraping.
        items = await page.query_selector_all('[data-widget-cid] article, .manhattan--container--1lP57Ag')
        if not items:
            # Try a simpler selector
            items = await page.query_selector_all("a[href*='/item/']")

        for item in items:
            if processed >= limit:
                break
            # Extract product URL
            href = await item.get_attribute("href")
            if not href:
                link = await item.query_selector("a[href*='/item/']")
                href = await link.get_attribute("href") if link else None
            if not href:
                continue

            # Extract seller link if present
            seller_link = await item.query_selector("a[href*='/store/']")
            seller_url = await seller_link.get_attribute("href") if seller_link else None
            seller_name = await seller_link.inner_text() if seller_link else "Unknown Seller"
            if not seller_url:
                # Fallback: skip if we can't find a seller link
                continue

            key = seller_url.split("?")[0]
            if key not in seen_sellers:
                seen_sellers.add(key)
                sellers.append((seller_name.strip(), key, [href]))
            else:
                # Append product to existing seller entry
                for i, (sn, su, urls) in enumerate(sellers):
                    if su == key and href not in urls:
                        urls.append(href)
                        sellers[i] = (sn, su, urls)
                        break
            processed += 1
        page_num += 1
        await random_sleep(0.5, 1.2)

    return sellers[:max_suppliers]
