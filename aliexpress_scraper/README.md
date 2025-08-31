# AliExpress Scraper (Scrapfly)

Robust, modular AliExpress scraper with a CLI and programmatic API using Scrapfly under the hood.

Ethics and caveats: Scraping may be fragile and region- or session-dependent. Respect site terms and laws. Do not bypass CAPTCHAs or other access controls. Enable `--respect-robots` to check robots.txt and exit if disallowed. Expect occasional failures due to anti-bot systems; mitigate with slower rates, proxies, headful mode, and human-in-the-loop when needed.

## Example output schema
```json
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
```

## Install

- Python 3.10+
- Install deps:

```bash
pip install -e .[dev]
```

Or runtime only:

```bash
pip install -e .
```

## Quick start

CLI:

```bash
export SCRAPFLY_KEY=YOUR_KEY
python -m aliexpress_scraper "wireless earbuds" \
  --country AU --limit 10 \
  --max-suppliers 2 --max-products-per-seller 1 \
  --output ./earbuds_sf.json --csv ./earbuds_sf.csv
```

Programmatic example is pending for the Scrapfly-only API.

You can pass a localization cookie if needed (e.g., to get USD):

```bash
python -m aliexpress_scraper "wireless earbuds" \
  --country AU --aep-cookie "aep_usuc_f=site=glo&c_tp=USD&b_locale=en_US" \
  --output ./earbuds_sf.json
```

## Features
- Scrapfly-powered scraping: search -> sellers -> products
- Modular parsing helpers and output writers
- Concurrency control, retries with exponential backoff, randomized delays
- Anti-bot detection with custom exception and graceful handling
- JSON/CSV output, optional image download
- Tests that don’t hammer the live site

## Troubleshooting
- See `docs/TROUBLESHOOTING.md` for CAPTCHAs, regional redirects, proxies, and tips.

## License
MIT
