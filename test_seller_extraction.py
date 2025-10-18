#!/usr/bin/env python3
"""
Test script to check seller name and rating extraction.
"""

import asyncio
import os
import sys
import json
sys.path.append('aliexpress_scraper/src')

from aliexpress_scraper.scrapfly_adapter import ScrapflyConfig, scrape_product_and_store_sf

async def test_seller_extraction():
    # Test with a specific product
    product_url = "https://www.aliexpress.com/item/1005008970616137.html"
    
    sf_cfg = ScrapflyConfig(
        key=os.environ.get('SCRAPFLY_KEY', 'scp-live-8afea162f0f44a54a71193fb1e19cae6'),
        country='AU'
    )
    
    print(f"🔍 Testing seller extraction for product:")
    print(f"URL: {product_url}")
    print("=" * 70)
    
    try:
        product, store_info = await scrape_product_and_store_sf(sf_cfg, product_url)
        
        if product:
            print(f"\n📦 Product Information:")
            print(f"   Title: {product.product_title}")
            print(f"   Price: {product.price}")
            print(f"   Rating: {product.rating}")
            print(f"   Reviews: {product.num_ratings}")
            print(f"   Orders: {product.num_orders}")
        else:
            print("❌ Failed to scrape product")
            
        if store_info:
            store_name, store_url = store_info
            print(f"\n🏪 Seller Information:")
            print(f"   Store Name: {store_name}")
            print(f"   Store URL: {store_url}")
        else:
            print("\n❌ Failed to extract seller information")
            
        # Now test the full scraping with seller data
        print(f"\n" + "=" * 70)
        print("Testing full supplier scraping with seller details...")
        
        from aliexpress_scraper.scrapfly_adapter import run_with_scrapfly
        
        result = await run_with_scrapfly(
            query="wireless headphones",
            max_suppliers=1,
            max_products_per_seller=1,
            limit=1,
            country='AU',
            key=sf_cfg.key,
            cookie=None
        )
        
        print(f"\n📊 Full Result:")
        print(f"   Query: {result.query}")
        print(f"   Suppliers found: {len(result.suppliers)}")
        
        if result.suppliers:
            for i, supplier in enumerate(result.suppliers):
                print(f"\n   Supplier {i+1}:")
                print(f"      Name: {supplier.seller_name}")
                print(f"      URL: {supplier.seller_url}")
                print(f"      Rating: {supplier.seller_rating}")
                print(f"      Followers: {supplier.num_followers}")
                print(f"      Location: {supplier.store_location}")
                print(f"      Products: {len(supplier.products)}")
                
                if supplier.products:
                    for j, prod in enumerate(supplier.products):
                        print(f"\n         Product {j+1}:")
                        print(f"            Title: {prod.product_title[:60]}...")
                        print(f"            Rating: {prod.rating}")
                        print(f"            Reviews: {prod.num_ratings}")
                        print(f"            Orders: {prod.num_orders}")
                
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_seller_extraction())
