from __future__ import annotations

"""Product-level scraping and parsing."""
import asyncio
from typing import Optional

from playwright.async_api import Page, Error as PWError

from .exceptions import AntiBotDetected
from .models import Product
from .parsers import detect_antibot, parse_product_id
from .utils import random_sleep


async def scrape_product(page: Page, url: str) -> Optional[Product]:
    # Retry navigation
    delay = 0.8
    for attempt in range(3):
        try:
            await page.goto(url, wait_until="domcontentloaded")
            break
        except PWError:
            if attempt == 2:
                raise
            await asyncio.sleep(delay)
            delay *= 1.8
    html = await page.content()
    if detect_antibot(html):
        raise AntiBotDetected("Anti-bot page detected on product")

    pid = parse_product_id(url) or ""

    # Try grabbing title and price with common selectors
    title = await _first_text(page, ["h1.product-title-text", "h1", "title"]) or ""
    price = await _first_text(page, [
        ".product-price-value",
        "span#j-sku-price",
        "span#j-sku-price2",
        "meta[itemprop='price']",
    ])
    currency = await page.get_attribute("meta[itemprop='priceCurrency']", "content")

    # Best-effort counts
    rating = await _first_number(page, ["span.product-reviewer-satisfaction", "span.overview-rating-average"])  # type: ignore[assignment]
    num_ratings = await _first_int(page, ["span.product-reviewer-reviews", "span#j-cnt-review"])  # type: ignore[assignment]
    num_orders = await _first_int(page, ["span.product-reviewer-sold", "span#j-order-num"])  # type: ignore[assignment]

    imgs = await page.eval_on_selector_all(
        "img",
        "els => Array.from(els).map(e => e.src).filter(s => s && s.startsWith('http'))",
    )

    p = Product(
        product_title=title,
        product_url=url,
        product_id=pid,
        price=price,
        currency=currency,
        rating=rating,
        num_ratings=num_ratings,
        num_orders=num_orders,
        image_urls=imgs or [],
    )
    await random_sleep(0.3, 1.0)
    return p


async def _first_text(page: Page, selectors: list[str]) -> Optional[str]:
    for sel in selectors:
        el = await page.query_selector(sel)
        if el:
            # Some price selectors use content attribute
            content = await el.get_attribute("content")
            if content:
                return content
            text = (await el.inner_text()).strip()
            if text:
                return text
    return None


async def _first_int(page: Page, selectors: list[str]) -> Optional[int]:
    t = await _first_text(page, selectors)
    if not t:
        return None
    digits = "".join(ch for ch in t if ch.isdigit())
    return int(digits) if digits else None


async def _first_number(page: Page, selectors: list[str]) -> Optional[float]:
    t = await _first_text(page, selectors)
    if not t:
        return None
    t = t.replace(",", ".")
    num = "".join(ch for ch in t if (ch.isdigit() or ch == "."))
    try:
        return float(num)
    except Exception:
        return None
