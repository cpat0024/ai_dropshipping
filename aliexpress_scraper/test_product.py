#!/usr/bin/env python3
"""Test scraping individual product pages to get store info."""

import asyncio
import os
from scrapfly import ScrapflyClient, ScrapeConfig
from parsel import Selector

async def test_product_scraping():
    key = os.environ.get("SCRAPFLY_KEY")
    if not key:
        print("Please set SCRAPFLY_KEY environment variable")
        return
    
    client = ScrapflyClient(key=key)
    
    # Test with one of the product URLs from our search results
    product_id = "1005008490033064"  # From the first item in our search results
    product_url = f"https://www.aliexpress.com/item/{product_id}.html"
    
    print(f"Fetching product: {product_url}")
    
    headers = {"accept-language": "en-US,en;q=0.9"}
    res = await client.async_scrape(
        ScrapeConfig(
            product_url,
            asp=True,
            country="AU",
            headers=headers,
            render_js=True,
            auto_scroll=True,
            rendering_wait=5000,
            timeout=60000,
        )
    )
    
    print(f"Response status: {res.status_code}")
    
    if res.status_code == 200:
        # Save the HTML for inspection
        with open("product_page.html", "w", encoding="utf-8") as f:
            f.write(res.content)
        print("Saved product HTML to product_page.html")
        
        # Parse with Parsel
        sel = Selector(res.content)
        
        # Look for store information
        store_links = sel.xpath("//a[contains(@href, '/store/')]/@href").getall()
        print(f"Found {len(store_links)} store links:")
        for link in store_links[:5]:
            print(f"  {link}")
        
        # Look for seller/store names
        store_names = sel.xpath("//span[contains(@class, 'store') or contains(@class, 'seller') or contains(@class, 'shop')]//text()").getall()
        print(f"Found potential store names:")
        for name in store_names[:10]:
            name = name.strip()
            if name:
                print(f"  '{name}'")
        
        # Look for any data attributes that might contain store info
        store_data = sel.xpath("//*[contains(@data-spm, 'store') or contains(@data-role, 'store')]").getall()
        print(f"Found {len(store_data)} elements with store data attributes")
        
        # Try to find JSON data that might contain store info
        scripts = sel.xpath('//script[contains(.,"store") or contains(.,"seller") or contains(.,"shop")]').getall()
        print(f"Found {len(scripts)} scripts containing store-related data")

if __name__ == "__main__":
    asyncio.run(test_product_scraping())
