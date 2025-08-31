from __future__ import annotations

"""Optional Scrapfly-based scraping backend.

Implements search (hidden JSON extraction), product parsing with JS rendering,
and simple seller info via the Scrapfly API. This is optional; install extras:

    pip install -e .[scrapfly]

and provide an API key via Config.scrapfly_key or SCRAPFLY_KEY env.
"""
import json
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .exceptions import ScraperError
from .logger import get_logger
from .models import Product, ScrapeResult, Seller
from .utils import random_sleep


_INIT_DATA_RE = re.compile(r"_init_data_\s*=\s*{\s*data:\s*({.+}) }", re.S)


@dataclass
class ScrapflyConfig:
    key: str
    country: str = "AU"
    cookie: Optional[str] = None  # e.g., aep_usuc_f=...


def _require_scrapfly():
    try:
        from scrapfly import ScrapflyClient, ScrapeConfig  # type: ignore
        from parsel import Selector  # type: ignore
    except Exception as e:  # pragma: no cover
        raise ScraperError(
            "Scrapfly extras not installed. Run: pip install -e .[scrapfly]"
        ) from e
    return ScrapflyClient, ScrapeConfig, Selector


async def search_products_sf(sf_cfg: ScrapflyConfig, query: str, limit: int = 20) -> List[Dict]:
    """Use Scrapfly to fetch search pages and return list of product preview dicts.

    Returns minimal dicts with productId and product URL.
    """
    ScrapflyClient, ScrapeConfig, Selector = _require_scrapfly()
    client = ScrapflyClient(key=sf_cfg.key)
    headers = {"accept-language": "en-US,en;q=0.9"}
    if sf_cfg.cookie:
        headers["cookie"] = sf_cfg.cookie

    async def fetch_page(page: int):
        url = (
            "https://www.aliexpress.com/wholesale?trafficChannel=main"
            f"&d=y&CatId=0&SearchText={query.replace(' ', '+')}&ltype=wholesale&SortType=default&page={page}"
        )
        res = await client.async_scrape(
            ScrapeConfig(url, asp=True, country=sf_cfg.country, headers=headers, render_js=False)
        )
        sel = Selector(res.content)
        scripts = sel.xpath('//script[contains(.,"_init_data_=")]')
        if not scripts:
            return []
        m = _INIT_DATA_RE.search("\n".join(s.get() for s in scripts))
        if not m:
            return []
        data = json.loads(m.group(1))
        fields = data.get("data", {}).get("root", {}).get("fields", {})
        items = fields.get("mods", {}).get("itemList", {}).get("content", [])
        out: List[Dict] = []
        for it in items:
            pid = it.get("productId")
            if not pid:
                continue
            out.append(
                {
                    "productId": str(pid),
                    "url": f"https://www.aliexpress.com/item/{pid}.html",
                    "title": it.get("title", {}).get("displayTitle"),
                }
            )
        return out

    first = await fetch_page(1)
    results = first[:]
    # scrape next pages until limit is reached, up to 3 pages politely
    page = 2
    while len(results) < limit and page <= 3:
        others = await fetch_page(page)
        results.extend(others)
        page += 1
        await random_sleep(0.5, 1.0)
    return results[:limit]


async def scrape_product_and_store_sf(sf_cfg: ScrapflyConfig, url: str) -> Tuple[Optional[Product], Optional[Tuple[str, str]]]:
    """Scrape both product info and store info from a product page.
    
    Returns (Product, (store_name, store_url)) or (None, None) if failed.
    """
    ScrapflyClient, ScrapeConfig, Selector = _require_scrapfly()
    client = ScrapflyClient(key=sf_cfg.key)
    headers = {"accept-language": "en-US,en;q=0.9"}
    if sf_cfg.cookie:
        headers["cookie"] = sf_cfg.cookie

    try:
        res = await client.async_scrape(
            ScrapeConfig(
                url,
                asp=True,
                country=sf_cfg.country,
                headers=headers,
                render_js=True,
                auto_scroll=True,
                rendering_wait=8000,
            )
        )
        
        if res.status_code != 200:
            return None, None
        
        sel = Selector(res.content)
        
        # Extract product information
        title = sel.xpath("//h1[@data-pl]/text()|//h1/text()").get()
        price_text = sel.xpath("//span[contains(@class,'currentPrice')]/text()|//meta[@itemprop='price']/@content").get()
        currency = sel.xpath("//meta[@itemprop='priceCurrency']/@content").get() or "USD"
        pid = url.split("item/")[-1].split(".")[0]
        imgs = sel.xpath("//img/@src|//img/@data-src").getall()
        rating_text = sel.xpath("//div[contains(@class,'rating--wrap')]/div/text()|//span[contains(@class,'overview-rating-average')]/text()").get()
        num_ratings_text = sel.xpath("//a[contains(@class,'reviewer--reviews')]/text()|//span[@id='j-cnt-review']/text()").get()

        def to_float(s: Optional[str]) -> Optional[float]:
            if not s:
                return None
            s = s.replace(",", ".")
            num = "".join(ch for ch in s if (ch.isdigit() or ch == "."))
            try:
                return float(num)
            except Exception:
                return None

        def to_int(s: Optional[str]) -> Optional[int]:
            if not s:
                return None
            digits = "".join(ch for ch in s if ch.isdigit())
            return int(digits) if digits else None

        product = Product(
            product_title=title or "",
            product_url=url,
            product_id=pid,
            price=price_text,
            currency=currency,
            rating=to_float(rating_text),
            num_ratings=to_int(num_ratings_text),
            image_urls=[i for i in imgs if i and i.startswith("http")][:20],
        )
        
        # Extract store information
        store_links = sel.xpath("//a[contains(@href, '/store/')]/@href").getall()
        store_url = None
        store_name = "Unknown Seller"
        
        if store_links:
            store_url = store_links[0]
            if not store_url.startswith("http"):
                store_url = "https://www.aliexpress.com" + store_url
            
            # Try to extract store name from the page
            store_name_candidates = sel.xpath(
                "//a[contains(@href, '/store/')]//text()|"
                "//span[contains(@class, 'seller')]/text()|"
                "//div[contains(@class, 'store')]//text()"
            ).getall()
            
            for candidate in store_name_candidates:
                candidate = candidate.strip()
                if candidate and len(candidate) > 3:  # Basic filter for meaningful names
                    store_name = candidate
                    break

        return product, (store_name, store_url) if store_url else None
    
    except Exception:
        return None, None


async def scrape_seller_sf(sf_cfg: ScrapflyConfig, seller_name: str, seller_url: str) -> Seller:
    """Minimal seller info via page HTML; may be sparse depending on localization."""
    ScrapflyClient, ScrapeConfig, Selector = _require_scrapfly()
    client = ScrapflyClient(key=sf_cfg.key)
    headers = {"accept-language": "en-US,en;q=0.9"}
    if sf_cfg.cookie:
        headers["cookie"] = sf_cfg.cookie
    
    try:
        res = await client.async_scrape(
            ScrapeConfig(seller_url, asp=True, country=sf_cfg.country, headers=headers, render_js=False)
        )
        sel = Selector(res.content)
        rating = sel.xpath("//div[contains(@class,'store-rating') or contains(@class,'score')]/text()").get()
        followers = sel.xpath("//span[contains(@class,'follow')]/text()").get()
        location = sel.xpath("//span[contains(@class,'store-loc')]/text()|//*[@data-role='store-location']/text()").get()
    except Exception:
        rating = None
        followers = None
        location = None
    
    def to_float(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        s = s.replace(",", ".")
        num = "".join(ch for ch in s if (ch.isdigit() or ch == "."))
        try:
            return float(num)
        except Exception:
            return None
    
    def to_int(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits) if digits else None
    
    return Seller(
        seller_name=seller_name,
        seller_url=seller_url,
        seller_rating=to_float(rating),
        num_followers=to_int(followers),
        store_location=location,
    )


async def run_with_scrapfly(query: str, *, max_suppliers: int, max_products_per_seller: int, limit: int, country: str, key: str, cookie: Optional[str] = None) -> ScrapeResult:
    """End-to-end scrape orchestrated via Scrapfly backend - FIXED VERSION."""
    logger = get_logger()
    sf_cfg = ScrapflyConfig(key=key, country=country, cookie=cookie)
    
    # Get product URLs from search
    logger.info(f"Searching for products: {query}")
    previews = await search_products_sf(sf_cfg, query, limit=limit)
    logger.info(f"Found {len(previews)} product URLs")
    
    if not previews:
        logger.warning("No products found in search results")
        return ScrapeResult(query=query)
    
    # Scrape products and collect store information
    sellers_map: Dict[str, Tuple[str, List[Product]]] = {}
    processed_products = 0
    
    for preview in previews:
        if processed_products >= limit or len(sellers_map) >= max_suppliers:
            break
            
        try:
            logger.info(f"Scraping product: {preview['url']}")
            product, store_info = await scrape_product_and_store_sf(sf_cfg, preview["url"])
            
            if product and store_info:
                store_name, store_url = store_info
                if store_url not in sellers_map:
                    sellers_map[store_url] = (store_name, [])
                sellers_map[store_url][1].append(product)
                processed_products += 1
                logger.info(f"Successfully scraped product from store: {store_name}")
            else:
                logger.warning(f"Failed to extract product or store info from {preview['url']}")
            
            # Be polite
            await random_sleep(0.5, 1.2)
            
        except Exception as e:
            logger.warning(f"Error scraping product {preview['url']}: {e}")
            continue
    
    logger.info(f"Found {len(sellers_map)} unique sellers")
    
    # Build result with sellers
    result = ScrapeResult(query=query)
    seller_count = 0
    
    for store_url, (store_name, products) in sellers_map.items():
        if seller_count >= max_suppliers:
            break
            
        try:
            seller = await scrape_seller_sf(sf_cfg, store_name, store_url)
            # Add products (limited by max_products_per_seller)
            seller.products = products[:max_products_per_seller]
            result.suppliers.append(seller)
            seller_count += 1
            logger.info(f"Added seller: {store_name} with {len(seller.products)} products")
            
            # Be polite
            await random_sleep(0.3, 0.8)
            
        except Exception as e:
            logger.warning(f"Error scraping seller info for {store_name}: {e}")
            continue
    
    logger.info(f"Final result: {len(result.suppliers)} suppliers")
    return result
