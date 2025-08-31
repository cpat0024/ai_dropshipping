from __future__ import annotations

"""Configuration for AliExpress scraper.

Defines the Config dataclass with sensible defaults and CLI-controlled options.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .utils import slugify


@dataclass
class Config:
    """Scraper configuration.

    Attributes:
        query: Search query string.
        max_suppliers: Max number of unique sellers to scrape.
        max_products_per_seller: Max products per seller from search results.
    headless: Deprecated (Scrapfly handles rendering).
        output: JSON output path. Defaults to ./aliexpress_{slug}.json
        csv: Optional CSV output path.
    proxy: Deprecated.
    timeout: Deprecated.
    respect_robots: Deprecated.
        limit: Number of search listings to scan.
    download_images: Whether to download images to local folder.
    concurrency: Deprecated.
    user_agent_list: Deprecated.
    retries: Deprecated.
    backoff_base: Deprecated.
        debug: Enable extra logging and file log.
    abort_on_antibot: Deprecated.
    """

    query: str
    max_suppliers: int = 5
    max_products_per_seller: int = 1
    headless: bool = True
    output: Optional[Path] = None
    csv: Optional[Path] = None
    proxy: Optional[str] = None
    timeout: float = 30.0
    respect_robots: bool = False
    limit: int = 20
    download_images: bool = False
    concurrency: int = 3
    user_agent_list: Optional[Path] = None
    retries: int = 3
    backoff_base: float = 1.0
    debug: bool = False
    abort_on_antibot: bool = False

    def finalize(self) -> "Config":
        """Fill derived defaults like output path with slugified query."""
        if self.output is None:
            slug = slugify(self.query)
            self.output = Path(f"./aliexpress_{slug}.json")
        return self
