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
    """Scrape product info with focus on price, reviews, and shipping details."""
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
                rendering_wait=10000,
            )
        )
        
        if res.status_code != 200:
            return None, None
        
        sel = Selector(res.content)
        
        # === TITLE EXTRACTION - Better strategy ===
        title = ""
        
        # Strategy 1: Look in standard title tags
        title_selectors = [
            "//h1[@data-pl]//text()",
            "//h1//text()",
            "//title//text()",
            "//*[contains(@class, 'product-title')]//text()",
            "//*[@data-role='product-title']//text()"
        ]
        
        for selector in title_selectors:
            candidates = sel.xpath(selector).getall()
            for candidate in candidates:
                candidate = candidate.strip()
                if len(candidate) > 15 and not any(skip in candidate.lower() for skip in ['aliexpress', 'buy', 'cheap', 'global']):
                    title = candidate
                    break
            if title:
                break
        
        # Strategy 2: Look in JSON data
        if not title:
            scripts = sel.xpath('//script//text()').getall()
            for script in scripts:
                title_patterns = [
                    r'"title":\s*"([^"]+)"',
                    r'"productTitle":\s*"([^"]+)"',
                    r'"displayTitle":\s*"([^"]+)"'
                ]
                for pattern in title_patterns:
                    matches = re.findall(pattern, script)
                    for match in matches:
                        if len(match) > 15:
                            title = match
                            break
                    if title:
                        break
                if title:
                    break
        
        # === PRICE EXTRACTION - Multiple strategies ===
        price_text = None
        currency = "USD"  # Default
        
        # Strategy 1: Look for price in JSON data within scripts
        import re
        scripts = sel.xpath('//script//text()').getall()
        for script in scripts:
            # Look for price patterns in JSON
            price_patterns = [
                r'"formattedPrice":\s*"([^"]+)"',
                r'"salePrice":\s*{\s*[^}]*"formattedPrice":\s*"([^"]+)"',
                r'"minPrice":\s*([0-9]+\.?[0-9]*)',
                r'"price":\s*"([^"]+)"',
                r'"currentPrice":\s*"([^"]+)"'
            ]
            
            for pattern in price_patterns:
                matches = re.findall(pattern, script)
                for match in matches:
                    if match and ('$' in match or any(c.isdigit() for c in match)):
                        # Clean the price
                        if '$' in match:
                            price_text = match
                            if 'AU' in match or 'AUD' in match:
                                currency = "AUD"
                            break
                        elif match.replace('.', '').isdigit():
                            # Just a number, need to determine currency from context
                            if 'AUD' in script or 'AU' in script:
                                price_text = f"AU ${match}"
                                currency = "AUD"
                            else:
                                price_text = f"${match}"
                            break
                if price_text:
                    break
            if price_text:
                break
        
        # Strategy 2: Look in HTML elements with price classes
        if not price_text:
            price_selectors = [
                "//span[contains(@class,'price-current')]//text()",
                "//span[contains(@class,'price-now')]//text()",
                "//div[contains(@class,'price')]//span//text()",
                "//*[contains(@class,'price') and contains(@class,'sale')]//text()",
                "//*[contains(@class,'current-price')]//text()",
                "//*[@data-spm-anchor-id]//span[contains(text(),'$')]//text()",
            ]
            
            for selector in price_selectors:
                candidates = sel.xpath(selector).getall()
                for candidate in candidates:
                    candidate = candidate.strip()
                    if '$' in candidate and any(c.isdigit() for c in candidate):
                        # Extract just the price part
                        price_match = re.search(r'(AU\s*)?[\$]\s*(\d+[\.,]?\d*)', candidate)
                        if price_match:
                            price_text = price_match.group(0)
                            if price_match.group(1):  # AU prefix found
                                currency = "AUD"
                            break
                if price_text:
                    break
        
        # Strategy 3: Look in meta tags
        if not price_text:
            meta_price = sel.xpath("//meta[@property='product:price:amount']/@content").get()
            meta_currency = sel.xpath("//meta[@property='product:price:currency']/@content").get()
            if meta_price:
                price_text = f"${meta_price}"
                if meta_currency:
                    currency = meta_currency
        
        # Strategy 4: Search all text for price patterns
        if not price_text:
            all_text = sel.xpath("//text()").getall()
            for text in all_text:
                text = text.strip()
                if len(text) < 20:  # Only look at short text snippets to avoid false positives
                    price_patterns = [
                        r'AU\s*\$\s*(\d+\.?\d*)',
                        r'USD\s*\$?\s*(\d+\.?\d*)',
                        r'\$\s*(\d+\.?\d*)',
                        r'(\d+\.?\d*)\s*AUD',
                        r'(\d+\.?\d*)\s*USD'
                    ]
                    
                    for pattern in price_patterns:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            if 'AU' in text.upper():
                                price_text = f"AU ${match.group(1) if match.group(1) else match.group(0)}"
                                currency = "AUD"
                            else:
                                price_text = f"${match.group(1) if match.group(1) else match.group(0)}"
                                currency = "USD"
                            break
                if price_text:
                    break
        
        # === RATING ===
        rating = None
        import re
        rating_patterns = [
            r'(\d\.\d)\s*(?:star|rating)',
            r'rating["\s:]*(\d\.\d)',
            r'(\d\.\d)\s*out\s*of\s*5'
        ]
        page_text = sel.xpath('//text()').getall()
        for text in page_text:
            for pattern in rating_patterns:
                match = re.search(pattern, text.lower())
                if match:
                    try:
                        rating = float(match.group(1))
                        break
                    except ValueError:
                        continue
            if rating:
                break
        
        # === REVIEWS COUNT ===
        num_reviews = None
        import re
        review_patterns = [
            r'(\d+(?:,\d+)*)\s*(?:review|rating)',
            r'(\d+(?:,\d+)*)\s*people\s*rated',
            r'based\s*on\s*(\d+(?:,\d+)*)'
        ]
        for text in page_text:
            for pattern in review_patterns:
                match = re.search(pattern, text.lower())
                if match:
                    try:
                        num_reviews = int(match.group(1).replace(',', ''))
                        break
                    except ValueError:
                        continue
            if num_reviews:
                break
        
        # === ORDERS/SOLD COUNT ===
        num_orders = None
        import re
        order_patterns = [
            r'(\d+(?:,\d+)*(?:\.\d+)?[k]?)\s*(?:sold|order|piece)',
            r'(\d+(?:,\d+)*)\s*people\s*bought',
            r'(\d+(?:,\d+)*)\+?\s*sold'
        ]
        for text in page_text:
            for pattern in order_patterns:
                match = re.search(pattern, text.lower())
                if match:
                    try:
                        sold_str = match.group(1).replace(',', '')
                        if 'k' in sold_str.lower():
                            num_orders = int(float(sold_str.lower().replace('k', '')) * 1000)
                        else:
                            num_orders = int(sold_str)
                        break
                    except ValueError:
                        continue
            if num_orders:
                break
        
        # === SHIPPING INFO ===
        shipping_info = []
        shipping_text = sel.xpath("//*[contains(text(), 'shipping') or contains(text(), 'delivery') or contains(text(), 'days')]//text()").getall()
        for text in shipping_text:
            text = text.strip().lower()
            if ('free' in text and 'shipping' in text) or ('day' in text and any(c.isdigit() for c in text)):
                shipping_info.append(text[:100])  # Limit length
        
        # === IMAGES - Get main product images only ===
        main_images = []
        img_selectors = [
            "//div[contains(@class, 'image-view')]//img/@src",
            "//div[contains(@class, 'product-image')]//img/@src", 
            "//img[contains(@alt, 'product')]/@src"
        ]
        for selector in img_selectors:
            imgs = sel.xpath(selector).getall()
            for img in imgs[:5]:  # Max 5 images
                if img.startswith('http') and 'aliexpress' in img:
                    main_images.append(img)
            if main_images:
                break
        
        # === PRODUCT ID ===
        pid = url.split("item/")[-1].split(".")[0]
        
        # === CREATE PRODUCT OBJECT ===
        product = Product(
            product_title=title,
            product_url=url,
            product_id=pid,
            price=price_text,
            currency=currency,
            rating=rating,
            num_ratings=num_reviews,
            num_orders=num_orders,
            image_urls=main_images[:10],  # Limit to 10 images max
            shipping_options=[{"info": info} for info in shipping_info[:3]]  # Max 3 shipping options
        )
        
        # === STORE EXTRACTION - Focus on AliExpress stores only ===
        store_url = None
        store_name = "Unknown Store"
        
        # Look for actual AliExpress store links only
        store_links = sel.xpath("//a[contains(@href, '/store/') and contains(@href, 'aliexpress')]/@href").getall()
        if not store_links:
            # Broader search but filter for aliexpress
            all_store_links = sel.xpath("//a[contains(@href, '/store/')]/@href").getall()
            store_links = [link for link in all_store_links if 'aliexpress' in link]
        
        if store_links:
            store_url = store_links[0]
            if not store_url.startswith("http"):
                store_url = "https://www.aliexpress.com" + store_url
        
        # If no store link found, try to construct from product page patterns
        if not store_url:
            # Try to find seller ID in scripts or data attributes
            scripts = sel.xpath('//script//text()').getall()
            for script in scripts:
                store_patterns = [
                    r'"sellerId":\s*"?(\d+)"?',
                    r'"storeNum":\s*"?(\d+)"?',
                    r'store/(\d+)',
                    r'seller.*?(\d{10,})'  # Look for long seller IDs
                ]
                for pattern in store_patterns:
                    match = re.search(pattern, script)
                    if match:
                        seller_id = match.group(1)
                        if len(seller_id) >= 8:  # Valid seller ID length
                            store_url = f"https://www.aliexpress.com/store/{seller_id}"
                            break
                if store_url:
                    break
        
        # Extract store name - avoid common non-store text
        if store_url:
            # Strategy 1: Look near store links
            store_name_candidates = sel.xpath("//a[contains(@href, '/store/')]//text()").getall()
            
            # Strategy 2: Look in JSON data for store name
            if not any(len(c.strip()) > 3 for c in store_name_candidates):
                for script in scripts:
                    name_patterns = [
                        r'"storeName":\s*"([^"]+)"',
                        r'"sellerName":\s*"([^"]+)"',
                        r'"companyName":\s*"([^"]+)"'
                    ]
                    for pattern in name_patterns:
                        match = re.search(pattern, script)
                        if match and len(match.group(1)) > 3:
                            store_name_candidates.append(match.group(1))
            
            # Strategy 3: Look for seller display elements
            seller_elements = sel.xpath("//*[contains(@class, 'seller') or contains(@class, 'store')]//text()").getall()
            store_name_candidates.extend(seller_elements)
            
            # Filter and select best store name
            for candidate in store_name_candidates:
                candidate = candidate.strip()
                if (len(candidate) > 3 and len(candidate) < 80 and 
                    not candidate.isdigit() and 
                    not any(word in candidate.lower() for word in [
                        'visit', 'store', 'shop', 'view', 'see', 'more', 'google', 'play', 
                        'app', 'download', 'install', 'mobile', 'click', 'link', 'url'
                    ])):
                    store_name = candidate
                    break
            
            # If still no good name, use a generic name based on the seller ID
            if store_name == "Unknown Store" and store_url:
                seller_id = re.search(r'/store/(\d+)', store_url)
                if seller_id:
                    store_name = f"Store {seller_id.group(1)}"
        
        return product, (store_name, store_url) if store_url else None
        
    except Exception as e:
        logger = get_logger()
        logger.warning(f"Error scraping {url}: {e}")
        return None, None
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
        
        # Extract product information with better selectors
        title = sel.xpath(
            "//h1[@data-pl]/text()|"
            "//h1//span/text()|"
            "//h1/text()|"
            "//*[@class='product-title-text']/text()|"
            "//*[contains(@class, 'title')]/text()"
        ).get()
        
        # Better price extraction
        price_text = sel.xpath(
            "//span[contains(@class,'currentPrice')]/text()|"
            "//span[contains(@class,'notranslate')]/text()|"
            "//meta[@itemprop='price']/@content|"
            "//*[contains(@class,'price-current')]/text()|"
            "//*[contains(text(),'$') or contains(text(),'AU')]/text()"
        ).get()
        
        # Better currency extraction
        currency = sel.xpath(
            "//meta[@itemprop='priceCurrency']/@content|"
            "//span[contains(@class,'currency')]/text()|"
            "//script[contains(., 'currencyCode')]"
        ).get() or "AUD"
        
        if currency and '"currencyCode"' in currency:
            import re
            match = re.search(r'"currencyCode":"([^"]+)"', currency)
            currency = match.group(1) if match else "AUD"
        
        pid = url.split("item/")[-1].split(".")[0]
        
        # Better image extraction
        imgs = sel.xpath(
            "//img[contains(@class,'magnifier')]/@src|"
            "//img[contains(@class,'product')]/@src|"
            "//img/@data-src|"
            "//img/@src"
        ).getall()
        
        # Better rating extraction
        rating_text = sel.xpath(
            "//div[contains(@class,'rating-star')]/text()|"
            "//span[contains(@class,'rating')]/text()|"
            "//div[contains(@class,'rating--wrap')]/div/text()|"
            "//span[contains(@class,'overview-rating-average')]/text()|"
            "//*[contains(text(),'stars') or contains(text(),'rating')]/text()"
        ).get()
        
        # Better reviews count extraction
        num_ratings_text = sel.xpath(
            "//a[contains(@class,'reviewer--reviews')]/text()|"
            "//span[@id='j-cnt-review']/text()|"
            "//*[contains(text(),'review') and contains(text(),'+')]/text()|"
            "//*[contains(@class,'review')]/text()"
        ).get()
        
        # Extract additional product info
        original_price = sel.xpath(
            "//span[contains(@class,'original-price') or contains(@class,'old-price')]/text()|"
            "//del/text()"
        ).get()
        
        # Extract orders/sold information  
        orders_text = sel.xpath(
            "//*[contains(text(),'sold') or contains(text(),'orders')]/text()|"
            "//*[contains(@class,'trade')]/text()"
        ).get()
        
        # Extract shipping info
        shipping_text = sel.xpath(
            "//*[contains(@class,'shipping') or contains(text(),'free shipping')]/text()|"
            "//*[contains(text(),'delivery')]/text()"
        ).getall()
        
        def to_float(s: Optional[str]) -> Optional[float]:
            if not s:
                return None
            # Clean the string more thoroughly
            s = s.replace(",", ".").replace("$", "").replace("AU", "").replace("USD", "").strip()
            # Extract just numbers and decimal point
            import re
            match = re.search(r'(\d+\.?\d*)', s)
            if match:
                try:
                    return float(match.group(1))
                except Exception:
                    return None
            return None

        def to_int(s: Optional[str]) -> Optional[int]:
            if not s:
                return None
            # Extract digits from strings like "1,234+ sold" or "2.5K reviews"
            import re
            # Handle K, M suffixes
            if 'K' in s.upper():
                match = re.search(r'(\d+\.?\d*)\s*K', s.upper())
                if match:
                    return int(float(match.group(1)) * 1000)
            elif 'M' in s.upper():
                match = re.search(r'(\d+\.?\d*)\s*M', s.upper())
                if match:
                    return int(float(match.group(1)) * 1000000)
            
            # Regular number extraction
            digits = re.sub(r'[^\d]', '', s)
            return int(digits) if digits else None

        product = Product(
            product_title=(title or "").strip(),
            product_url=url,
            product_id=pid,
            price=price_text.strip() if price_text else None,
            currency=currency.strip() if currency else "AUD",
            original_price=original_price.strip() if original_price else None,
            rating=to_float(rating_text),
            num_ratings=to_int(num_ratings_text),
            num_orders=to_int(orders_text) if orders_text else None,
            image_urls=[i for i in imgs if i and i.startswith("http")][:20],
        )
        
        # Extract store information with better selectors
        store_links = sel.xpath("//a[contains(@href, '/store/')]/@href").getall()
        store_url = None
        store_name = "Unknown Seller"
        
        if store_links:
            store_url = store_links[0]
            # Fix the URL formatting issue
            if store_url.startswith("//"):
                store_url = "https:" + store_url
            elif store_url.startswith("/"):
                store_url = "https://www.aliexpress.com" + store_url
            elif not store_url.startswith("http"):
                store_url = "https://www.aliexpress.com/" + store_url
            
            # Better store name extraction
            store_name_candidates = sel.xpath(
                "//a[contains(@href, '/store/')]/text()|"
                "//a[contains(@href, '/store/')]//span/text()|"
                "//*[contains(@class,'shop-name')]/text()|"
                "//*[contains(@class,'store-name')]/text()|"
                "//*[contains(@class,'seller-name')]/text()|"
                "//*[@data-role='store-name']/text()|"
                "//div[contains(@class,'seller')]//text()[normalize-space()]"
            ).getall()
            
            # Filter and pick the best store name
            for candidate in store_name_candidates:
                candidate = candidate.strip()
                # Skip common non-name texts
                skip_words = ["sold by", "store", "shop", "seller", "visit", "follow", "contact"]
                if (candidate and 
                    len(candidate) > 2 and 
                    len(candidate) < 100 and 
                    not any(skip.lower() in candidate.lower() for skip in skip_words) and
                    not candidate.isdigit()):
                    store_name = candidate
                    break
            
            # If we still have a generic name, try to extract from URL
            if store_name in ["Unknown Seller", "Sold by"]:
                import re
                # Extract store ID from URL and use it
                store_id_match = re.search(r'/store/(\d+)', store_url)
                if store_id_match:
                    store_name = f"Store {store_id_match.group(1)}"

        return product, (store_name, store_url) if store_url else None
    
    except Exception:
        return None, None


async def scrape_seller_sf(sf_cfg: ScrapflyConfig, seller_name: str, seller_url: str) -> Seller:
    """Scrape seller info focusing on key metrics only."""
    try:
        ScrapflyClient, ScrapeConfig, Selector = _require_scrapfly()
        client = ScrapflyClient(key=sf_cfg.key)
        headers = {"accept-language": "en-US,en;q=0.9"}
        if sf_cfg.cookie:
            headers["cookie"] = sf_cfg.cookie
        
        res = await client.async_scrape(
            ScrapeConfig(seller_url, asp=True, country=sf_cfg.country, headers=headers, render_js=False)
        )
        
        if res.status_code != 200:
            raise Exception("Failed to load store page")
            
        sel = Selector(res.content)
        
        # Simple, clean extraction
        rating = None
        followers = None
        location = None
        
        # Look for rating (format: 4.8, 95.5%, etc.)
        rating_text = sel.xpath("//*[contains(text(), '.') and (contains(text(), '%') or contains(., '/5'))]//text()").getall()
        for text in rating_text[:5]:  # Check first 5 only
            import re
            match = re.search(r'(\d+\.?\d*)(?:%|/5)', text)
            if match:
                try:
                    rating_val = float(match.group(1))
                    if rating_val <= 5:  # Rating out of 5
                        rating = rating_val
                    elif rating_val <= 100:  # Percentage
                        rating = rating_val / 20  # Convert to 5-star scale
                    break
                except ValueError:
                    continue
        
        # Look for followers (format: 1,234 followers)
        followers_text = sel.xpath("//*[contains(text(), 'follow')]//text()").getall()
        for text in followers_text[:3]:
            import re
            match = re.search(r'(\d+(?:,\d+)*)', text)
            if match:
                try:
                    followers = int(match.group(1).replace(',', ''))
                    break
                except ValueError:
                    continue
        
        # Look for location
        location_candidates = sel.xpath("//text()").getall()
        for text in location_candidates:
            text = text.strip()
            # Look for country/city patterns
            if any(country in text for country in ['China', 'USA', 'UK', 'Germany', 'Japan']):
                if len(text) < 50:  # Reasonable location length
                    location = text
                    break
        
    except Exception:
        rating = None
        followers = None
        location = None
    
    return Seller(
        seller_name=seller_name,
        seller_url=seller_url,
        seller_rating=rating,
        num_followers=followers,
        store_location=location,
    )
    """Enhanced seller info extraction via page HTML."""
    ScrapflyClient, ScrapeConfig, Selector = _require_scrapfly()
    client = ScrapflyClient(key=sf_cfg.key)
    headers = {"accept-language": "en-US,en;q=0.9"}
    if sf_cfg.cookie:
        headers["cookie"] = sf_cfg.cookie
    
    try:
        res = await client.async_scrape(
            ScrapeConfig(seller_url, asp=True, country=sf_cfg.country, headers=headers, render_js=True, rendering_wait=5000)
        )
        sel = Selector(res.content)
        
        # Better rating extraction
        rating = sel.xpath(
            "//div[contains(@class,'store-rating')]/text()|"
            "//span[contains(@class,'score')]/text()|"
            "//div[contains(@class,'rating')]//text()[contains(.,'.')][1]|"
            "//*[contains(@class,'seller-score')]/text()"
        ).get()
        
        # Better followers extraction
        followers = sel.xpath(
            "//span[contains(@class,'follow')]/text()|"
            "//*[contains(text(),'followers') or contains(text(),'follow')]/text()|"
            "//*[contains(@class,'fans')]/text()"
        ).get()
        
        # Better location extraction  
        location = sel.xpath(
            "//span[contains(@class,'store-loc')]/text()|"
            "//*[@data-role='store-location']/text()|"
            "//*[contains(@class,'location')]/text()|"
            "//*[contains(text(),'China') or contains(text(),'Hong Kong') or contains(text(),'Taiwan')]/text()[1]"
        ).get()
        
        # Extract business time
        years_text = sel.xpath(
            "//*[contains(text(),'year') or contains(text(),'since')]/text()"
        ).get()
        
        # Extract store ratings count - filter out very long strings
        reviews_text = sel.xpath(
            "//*[contains(text(),'review') or contains(text(),'feedback')]/text()"
        ).get()
        
        # Filter out encoded/garbage data
        if reviews_text and len(reviews_text) > 100:
            reviews_text = None
        
    except Exception:
        rating = None
        followers = None
        location = None
        years_text = None
        reviews_text = None
    
    def to_float(s: Optional[str]) -> Optional[float]:
        if not s:
            return None
        # Clean and extract number
        import re
        s = s.replace(",", ".").strip()
        match = re.search(r'(\d+\.?\d*)', s)
        if match:
            try:
                return float(match.group(1))
            except Exception:
                return None
        return None
    
    def to_int(s: Optional[str]) -> Optional[int]:
        if not s:
            return None
        import re
        # Handle K, M suffixes for followers
        if 'K' in s.upper():
            match = re.search(r'(\d+\.?\d*)\s*K', s.upper())
            if match:
                return int(float(match.group(1)) * 1000)
        elif 'M' in s.upper():
            match = re.search(r'(\d+\.?\d*)\s*M', s.upper())
            if match:
                return int(float(match.group(1)) * 1000000)
        
        digits = re.sub(r'[^\d]', '', s)
        return int(digits) if digits else None
    
    return Seller(
        seller_name=seller_name,
        seller_url=seller_url,
        seller_rating=to_float(rating),
        num_followers=to_int(followers),
        store_location=location.strip() if location else None,
        years_on_platform=to_int(years_text),
        total_reviews=to_int(reviews_text),
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
