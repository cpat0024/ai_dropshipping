from __future__ import annotations

"""Data models for the AliExpress scraper.

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
          "shipping_options": [{"destination":"AU","cost":"$2.99","estimated_days":"7-15"}],
          "estimated_delivery": "Aug 20 - Aug 30",
          "return_policy": "15 days return",
          "last_scraped": "2025-08-31T12:34:56+10:00"
        }
      ]
    }
  ]
}
"""
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from .utils import iso_now


@dataclass
class Product:
    product_title: str
    product_url: str
    product_id: str
    price: Optional[str] = None
    currency: Optional[str] = None
    original_price: Optional[str] = None
    discount_percent: Optional[int] = None
    rating: Optional[float] = None
    num_ratings: Optional[int] = None
    num_orders: Optional[int] = None
    available_skus: List[Dict[str, Any]] = field(default_factory=list)
    stock_availability: Optional[str] = None
    image_urls: List[str] = field(default_factory=list)
    shipping_options: List[Dict[str, Any]] = field(default_factory=list)
    estimated_delivery: Optional[str] = None
    return_policy: Optional[str] = None
    warranty: Optional[str] = None
    last_scraped: str = field(default_factory=iso_now)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Seller:
    seller_name: str
    seller_url: str
    seller_rating: Optional[float] = None
    num_followers: Optional[int] = None
    store_location: Optional[str] = None
    seller_badges: List[str] = field(default_factory=list)
    years_on_platform: Optional[int] = None
    total_reviews: Optional[int] = None
    products: List[Product] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["products"] = [p.to_dict() for p in self.products]
        return d


@dataclass
class ScrapeResult:
    query: str
    scrape_time: str = field(default_factory=iso_now)
    suppliers: List[Seller] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "scrape_time": self.scrape_time,
            "suppliers": [s.to_dict() for s in self.suppliers],
        }
