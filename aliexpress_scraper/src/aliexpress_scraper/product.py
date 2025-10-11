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


async def scrape_product_details(page: Page, url: str) -> dict:
    """Scrape comprehensive product details including reviews and supplier info."""
    try:
        # Navigate to product page
        await page.goto(url, wait_until="domcontentloaded")
        await random_sleep(1.0, 2.0)  # Wait for dynamic content
        
        html = await page.content()
        if detect_antibot(html):
            raise AntiBotDetected("Anti-bot page detected on product details")

        # Basic product info
        title = await _first_text(page, ["h1.product-title-text", "h1", ".product-title"]) or "Unknown Product"
        price = await _first_text(page, [".product-price-value", "span#j-sku-price", ".price-current"])
        original_price = await _first_text(page, [".product-price-del", ".price-original"])
        
        # Detailed product specs
        description = await _first_text(page, [".product-description", ".detail-desc", ".product-detail"])
        brand = await _first_text(page, [".product-brand", ".brand-name"])
        category = await _first_text(page, [".product-category", ".breadcrumb"])
        
        # Shipping and logistics
        shipping_info = await _first_text(page, [".product-shipping", ".shipping-info", ".logistics-info"])
        delivery_time = await _first_text(page, [".delivery-time", ".shipping-time"])
        
        # Seller information
        seller_name = await _first_text(page, [".seller-name", ".store-name", ".shop-name"])
        seller_rating = await _first_number(page, [".seller-rating", ".store-rating"])
        seller_years = await _first_text(page, [".seller-years", ".store-years"])
        seller_followers = await _first_int(page, [".seller-followers", ".store-followers"])
        
        # Product ratings and reviews
        rating = await _first_number(page, [".product-rating", ".overview-rating-average"])
        num_ratings = await _first_int(page, [".total-reviews", "#j-cnt-review"])
        num_orders = await _first_int(page, [".product-sold", "#j-order-num"])
        
        # Try to get some reviews
        reviews = []
        try:
            # Look for review elements
            review_elements = await page.query_selector_all(".review-item, .feedback-item, .comment-item")
            for element in review_elements[:5]:  # Get first 5 reviews
                review_text = await element.query_selector(".review-content, .comment-content, .feedback-content")
                review_rating = await element.query_selector(".review-stars, .rating-stars")
                review_author = await element.query_selector(".review-author, .reviewer-name")
                
                if review_text:
                    review_content = await review_text.inner_text()
                    rating_stars = 5  # default
                    author_name = "Anonymous"
                    
                    if review_rating:
                        rating_text = await review_rating.inner_text()
                        rating_stars = len([c for c in rating_text if c == '★'])
                    
                    if review_author:
                        author_name = await review_author.inner_text()
                    
                    reviews.append({
                        "author": author_name.strip(),
                        "rating": rating_stars,
                        "comment": review_content.strip()[:200]  # Limit comment length
                    })
        except Exception:
            pass  # Reviews are optional
        
        # Product specifications
        specs = {}
        try:
            spec_elements = await page.query_selector_all(".product-spec, .specification-item, .attr-item")
            for element in spec_elements[:10]:  # Get first 10 specs
                spec_name = await element.query_selector(".spec-name, .attr-name")
                spec_value = await element.query_selector(".spec-value, .attr-value")
                
                if spec_name and spec_value:
                    name = await spec_name.inner_text()
                    value = await spec_value.inner_text()
                    specs[name.strip()] = value.strip()
        except Exception:
            pass

        # Get product images
        images = []
        try:
            images = await page.eval_on_selector_all(
                ".product-image img, .gallery-img, .product-gallery img",
                "els => Array.from(els).map(e => e.src).filter(s => s && s.startsWith('http'))"
            )
        except Exception:
            pass

        return {
            "basic_info": {
                "title": title,
                "price": price,
                "original_price": original_price,
                "brand": brand,
                "category": category,
                "description": description[:500] if description else None  # Limit description
            },
            "ratings": {
                "rating": rating,
                "num_ratings": num_ratings,
                "num_orders": num_orders
            },
            "seller": {
                "name": seller_name,
                "rating": seller_rating,
                "years_in_business": seller_years,
                "followers": seller_followers
            },
            "shipping": {
                "info": shipping_info,
                "delivery_time": delivery_time
            },
            "reviews": reviews,
            "specifications": specs,
            "images": images[:10] if images else []  # Limit to 10 images
        }
    
    except Exception as e:
        return {"error": f"Failed to scrape details: {str(e)}"}


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
