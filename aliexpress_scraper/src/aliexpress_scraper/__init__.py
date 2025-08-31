"""aliexpress_scraper package

Provides a programmatic API and CLI to scrape AliExpress using Scrapfly.

Example output schema:
{
  "query": "wireless earbuds",
  "scrape_time": "2025-08-31T12:34:56+10:00",
  "suppliers": [
    {
      "seller_name": "BestAudioStore",
      "seller_url": "https://www.aliexpress.com/store/123456",
      "seller_rating": 4.8,
      "num_followers": 12345,
      "store_location": "Shenzhen, China",
      "seller_badges": ["Top Brand", "Fast Delivery"],
      "products": [
        {
          "product_title": "Wireless Bluetooth Earbuds X100",
          "product_url": "https://www.aliexpress.com/item/1005001234567890.html",
          "product_id": "1005001234567890",
          "price": "29.99",
          "currency": "USD",
          "original_price": "59.99",
          "discount_percent": 50,
          "rating": 4.7,
          "num_ratings": 2345,
          "num_orders": 12340,
          "available_skus": [{"color":"black"},{"storage":"128GB"}],
          "stock_availability": "In stock",
          "image_urls": ["https://.../img1.jpg"],
          "shipping_options": [{"destination":"US","cost":"$2.99","estimated_days":"7-15"}],
          "estimated_delivery": "Aug 20 - Aug 30",
          "return_policy": "15 days return",
          "last_scraped": "2025-08-31T12:34:56+10:00"
        }
      ]
    }
  ]
}
"""
from .config import Config
from .exceptions import AntiBotDetected, ScraperError
from .models import Product, Seller, ScrapeResult

__all__ = [
  "Config",
  "AntiBotDetected",
  "ScraperError",
  "Product",
  "Seller",
  "ScrapeResult",
]

