"""
Improved scraper focused on extracting key data: price, reviews, shipping
"""

async def scrape_product_and_store_sf_improved(sf_cfg: ScrapflyConfig, url: str) -> Tuple[Optional[Product], Optional[Tuple[str, str]]]:
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
        
        # === TITLE EXTRACTION ===
        title = ""
        title_candidates = sel.xpath("//h1//text()").getall()
        for candidate in title_candidates:
            candidate = candidate.strip()
            if len(candidate) > 10:  # Get a meaningful title, not just short text
                title = candidate
                break
        
        # === PRICE EXTRACTION ===
        price_text = None
        # Look for price in various formats
        all_text = sel.xpath("//*[contains(text(), '$') or contains(text(), 'AU')]//text()").getall()
        for text in all_text:
            text = text.strip()
            # Match price patterns like $12.34, AU $45.67, etc.
            import re
            price_match = re.search(r'(AU\s*)?[\$]\s*(\d+[\.,]?\d*)', text)
            if price_match:
                price_text = price_match.group(0)
                break
        
        # Try script data for price if not found
        if not price_text:
            scripts = sel.xpath('//script[contains(., "price") or contains(., "Price")]//text()').getall()
            for script in scripts:
                price_match = re.search(r'"price":\s*"?(\d+\.?\d*)"?|"formattedPrice":\s*"([^"]+)"', script)
                if price_match:
                    price_text = price_match.group(1) or price_match.group(2)
                    break
        
        # === CURRENCY ===
        currency = "USD"
        if price_text and ("AU" in price_text or "AUD" in price_text):
            currency = "AUD"
        
        # === RATING ===
        rating = None
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
                    except:
                        continue
            if rating:
                break
        
        # === REVIEWS COUNT ===
        num_reviews = None
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
                    except:
                        continue
            if num_reviews:
                break
        
        # === ORDERS/SOLD COUNT ===
        num_orders = None
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
                    except:
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
        
        # === STORE EXTRACTION ===
        store_url = None
        store_name = "Unknown Store"
        
        # Look for store links
        store_links = sel.xpath("//a[contains(@href, '/store/') or contains(@href, '/shop/')]/@href").getall()
        if store_links:
            store_url = store_links[0]
            if not store_url.startswith("http"):
                store_url = "https://www.aliexpress.com" + store_url
        
        # Extract store name from various places
        store_name_candidates = [
            *sel.xpath("//a[contains(@href, '/store/')]//text()").getall(),
            *sel.xpath("//span[contains(@class, 'store') or contains(@class, 'seller')]//text()").getall(),
            *sel.xpath("//*[contains(text(), 'Store') or contains(text(), 'Shop')]//text()").getall()
        ]
        
        for candidate in store_name_candidates:
            candidate = candidate.strip()
            if len(candidate) > 3 and len(candidate) < 50 and not candidate.isdigit():
                # Filter out common non-store text
                if not any(word in candidate.lower() for word in ['visit', 'store', 'shop', 'view', 'see', 'more']):
                    store_name = candidate
                    break
        
        return product, (store_name, store_url) if store_url else None
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None, None


async def scrape_seller_sf_improved(sf_cfg: ScrapflyConfig, seller_name: str, seller_url: str) -> Seller:
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
                except:
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
                except:
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
        seller_badges=[],  # Keep empty to avoid clutter
        total_reviews=None  # Avoid long encoded strings
    )
