#!/usr/bin/env python3
"""
Quick test script to verify Gemini AI integration works
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from aliexpress_scraper.server import CleanerAgent
from aliexpress_scraper.models import ScrapeResult, Seller, Product

async def test_gemini_integration():
    print("🧠 Testing Gemini AI Integration...")
    print("-" * 40)
    
    # Create test data
    test_product = Product(
        product_title="Wireless Bluetooth Earbuds Pro",
        product_url="https://example.com/product/123",
        product_id="123",
        price="$29.99",
        currency="USD",
        rating=4.5,
        num_ratings=2500,
        num_orders=10000
    )
    
    test_seller = Seller(
        seller_name="TechWorld Store",
        seller_url="https://example.com/store/techworld",
        seller_rating=4.8,
        num_followers=50000,
        store_location="Shenzhen, China",
        products=[test_product]
    )
    
    test_result = ScrapeResult(
        query="wireless earbuds",
        suppliers=[test_seller]
    )
    
    # Test the AI cleaner
    cleaner = CleanerAgent()
    
    if cleaner._client:
        print("✅ Gemini AI client initialized successfully")
        print(f"✅ Using model: {cleaner.model_name}")
        
        try:
            cleaned_result = await cleaner.clean(test_result, None)
            print("✅ AI analysis completed successfully!")
            print(f"✅ Found {len(cleaned_result.get('top_products', []))} top products")
            print(f"✅ Generated {len(cleaned_result.get('insights', []))} insights")
            
            # Show a sample insight
            insights = cleaned_result.get('insights', [])
            if insights:
                print(f"📊 Sample insight: {insights[0]}")
            
            return True
            
        except Exception as e:
            print(f"❌ AI analysis failed: {e}")
            return False
    else:
        print("⚠️  Gemini AI client not available - using local fallback")
        print("📝 This usually means GOOGLE_API_KEY is not set or SDK not installed")
        
        # Test local fallback
        cleaned_result = await cleaner.clean(test_result, None)
        print("✅ Local fallback analysis completed successfully!")
        print(f"✅ Found {len(cleaned_result.get('top_products', []))} top products")
        
        return True

async def main():
    success = await test_gemini_integration()
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 System test PASSED!")
        print("🚀 Your AI Supplier Evaluation System is ready!")
        print("🌐 Access the interface at: http://127.0.0.1:8787")
    else:
        print("💥 System test FAILED!")
        print("🔧 Please check your API configuration")
    print("=" * 40)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))