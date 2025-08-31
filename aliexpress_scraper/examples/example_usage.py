import asyncio
import os

from aliexpress_scraper import Config
from aliexpress_scraper.scrapfly_adapter import run_with_scrapfly


async def main() -> None:
    cfg = Config(query="wireless earbuds", max_suppliers=2).finalize()
    key = os.environ.get("SCRAPFLY_KEY")
    assert key, "Set SCRAPFLY_KEY environment variable"
    result = await run_with_scrapfly(
        cfg.query,
        max_suppliers=cfg.max_suppliers,
        max_products_per_seller=cfg.max_products_per_seller,
        limit=cfg.limit,
        country="AU",
        key=key,
        cookie=None,
    )
    print(result.to_dict())


if __name__ == "__main__":
    asyncio.run(main())
