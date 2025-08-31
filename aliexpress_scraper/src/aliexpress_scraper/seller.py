from __future__ import annotations

"""Seller/store page scraping logic."""
from typing import List, Optional

from playwright.async_api import Page, Error as PWError

from .exceptions import AntiBotDetected
from .models import Seller
from .parsers import detect_antibot
from .utils import random_sleep


async def scrape_seller(page: Page, seller_name: str, seller_url: str) -> Optional[Seller]:
    delay = 0.8
    for attempt in range(3):
        try:
            await page.goto(seller_url, wait_until="domcontentloaded")
            break
        except PWError:
            if attempt == 2:
                raise
            import asyncio as _asyncio

            await _asyncio.sleep(delay)
            delay *= 1.8
    html = await page.content()
    if detect_antibot(html):
        raise AntiBotDetected("Anti-bot page detected on seller")

    rating = await _float_sel(page, [".store-rating-score", "span.score"])
    followers = await _int_sel(page, [".store-followers", "span.follow-num"])  # type: ignore[assignment]
    location = await _text_sel(page, [".store-location", "span.store-loc", "[data-role='store-location']"])  # type: ignore[assignment]

    badges: List[str] = await page.eval_on_selector_all(
        ".store-badges .badge, .store-badges img[alt]",
        "els => Array.from(els).map(e => e.alt || e.textContent.trim()).filter(Boolean)",
    )

    years_on_platform = await _int_sel(page, [".store-years", "span.years"])
    total_reviews = await _int_sel(page, [".store-reviews-total", "span.total-reviews"])  # type: ignore[assignment]

    await random_sleep(0.3, 1.0)

    return Seller(
        seller_name=seller_name,
        seller_url=seller_url,
        seller_rating=rating,
        num_followers=followers,
        store_location=location,
        seller_badges=badges or [],
        years_on_platform=years_on_platform,
        total_reviews=total_reviews,
    )


async def _text_sel(page: Page, sels: list[str]) -> Optional[str]:
    for sel in sels:
        el = await page.query_selector(sel)
        if el:
            t = (await el.inner_text()).strip()
            if t:
                return t
    return None


async def _int_sel(page: Page, sels: list[str]) -> Optional[int]:
    t = await _text_sel(page, sels)
    if not t:
        return None
    digits = "".join(ch for ch in t if ch.isdigit())
    return int(digits) if digits else None


async def _float_sel(page: Page, sels: list[str]) -> Optional[float]:
    t = await _text_sel(page, sels)
    if not t:
        return None
    t = t.replace(",", ".")
    num = "".join(ch for ch in t if (ch.isdigit() or ch == "."))
    try:
        return float(num)
    except Exception:
        return None
