from __future__ import annotations

"""DOM parsing helpers.

Pure functions for testability. These don't call the network.
"""
import re
from typing import Optional

from bs4 import BeautifulSoup


PRODUCT_ID_REGEX = re.compile(r"(?:/item/|item/)(\d{10,})")


def parse_product_id(url: str) -> Optional[str]:
    """Extract product ID from common AliExpress URL formats."""
    m = PRODUCT_ID_REGEX.search(url)
    return m.group(1) if m else None


def parse_text(soup: BeautifulSoup, selector: str) -> Optional[str]:
    el = soup.select_one(selector)
    if not el:
        return None
    text = el.get_text(" ", strip=True)
    return text or None


def detect_antibot(html: str) -> bool:
    html_lower = html.lower()
    indicators = [
        "captcha",
        "verify you are human",
        "cloudflare",
        "attention required",
        "unusual traffic",
    ]
    return any(ind in html_lower for ind in indicators)
