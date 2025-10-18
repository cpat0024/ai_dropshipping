#!/usr/bin/env python3
"""
Test script to check if rating and review extraction is working properly.
"""

import asyncio
import os
import sys
sys.path.append('aliexpress_scraper/src')

from aliexpress_scraper.scrapfly_adapter import ScrapflyConfig, search_products_sf, scrape_product_and_store_sf

async def test_rating_extraction():
    # Test with some product search
    query = "wireless headphones"
    sf_cfg = ScrapflyConfig(
        key=os.environ.get('SCRAPFLY_KEY', 'scp-live-8afea162f0f44a54a71193fb1e19cae6'),
        country='AU'
    )
    
    print(f"🔍 Testing rating extraction for: {query}")
    print("=" * 50)
    
    # Get some products from search
    try:
        previews = await search_products_sf(sf_cfg, query, limit=3)
        print(f"Found {len(previews)} products in search")
        
        for i, preview in enumerate(previews):
            print(f"\n📦 Product {i+1}:")
            print(f"   Title: {preview.get('title', 'N/A')}")
            print(f"   Price: {preview.get('price', 'N/A')} {preview.get('currency', '')}")
            print(f"   Rating: {preview.get('rating', 'N/A')}")
            print(f"   Reviews: {preview.get('num_ratings', 'N/A')}")
            print(f"   Orders: {preview.get('num_orders', 'N/A')}")
            
        # Test detailed scraping on first product
        if previews:
            print(f"\n🔬 Testing detailed scraping on first product...")
            first_url = previews[0]['url']
            print(f"URL: {first_url}")
            
            product, store_info = await scrape_product_and_store_sf(sf_cfg, first_url)
            if product:
                print(f"\n📊 Detailed Product Data:")
                print(f"   Title: {product.product_title}")
                print(f"   Price: {product.price}")
                print(f"   Rating: {product.rating}")
                print(f"   Num Ratings: {product.num_ratings}")
                print(f"   Num Orders: {product.num_orders}")
            else:
                print("❌ Failed to scrape detailed product data")
                
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rating_extraction())