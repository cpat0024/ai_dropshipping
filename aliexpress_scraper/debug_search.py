#!/usr/bin/env python3
"""Debug script to test the search parsing logic."""

import asyncio
import os
import json
import re
from scrapfly import ScrapflyClient, ScrapeConfig
from parsel import Selector

_INIT_DATA_RE = re.compile(r"_init_data_\s*=\s*{\s*data:\s*({.+}) }", re.S)

async def debug_search():
    key = os.environ.get("SCRAPFLY_KEY")
    if not key:
        print("Please set SCRAPFLY_KEY environment variable")
        return
    
    client = ScrapflyClient(key=key)
    query = "wireless earbuds"
    
    url = (
        "https://www.aliexpress.com/wholesale?trafficChannel=main"
        f"&d=y&CatId=0&SearchText={query.replace(' ', '+')}&ltype=wholesale&SortType=default&page=1"
    )
    
    print(f"Fetching URL: {url}")
    
    headers = {"accept-language": "en-US,en;q=0.9"}
    res = await client.async_scrape(
        ScrapeConfig(url, asp=True, country="AU", headers=headers, render_js=False)
    )
    
    print(f"Response status: {res.status_code}")
    print(f"Response length: {len(res.content)}")
    
    # Save raw HTML for inspection
    with open("debug_response.html", "w", encoding="utf-8") as f:
        f.write(res.content)
    print("Saved raw HTML to debug_response.html")
    
    # Parse with Parsel
    sel = Selector(res.content)
    scripts = sel.xpath('//script[contains(.,"_init_data_=")]')
    print(f"Found {len(scripts)} scripts with _init_data_")
    
    if not scripts:
        print("No scripts found with _init_data_")
        # Let's try to find other potential data sources
        all_scripts = sel.xpath('//script/text()').getall()
        print(f"Total scripts found: {len(all_scripts)}")
        
        for i, script in enumerate(all_scripts[:5]):  # Check first 5 scripts
            if "product" in script.lower() or "item" in script.lower():
                print(f"Script {i} contains product/item data (first 200 chars):")
                print(script[:200])
                print("---")
        return
    
    # Try to extract JSON data
    script_content = "\n".join(s.get() for s in scripts)
    print("Found script with _init_data_")
    
    # Save script content
    with open("debug_script.js", "w", encoding="utf-8") as f:
        f.write(script_content)
    print("Saved script content to debug_script.js")
    
    m = _INIT_DATA_RE.search(script_content)
    if not m:
        print("Could not match _init_data_ pattern")
        # Let's try a broader search
        if "_init_data_" in script_content:
            print("_init_data_ found in script, but regex didn't match")
            # Find the actual pattern
            lines = script_content.split('\n')
            for i, line in enumerate(lines):
                if "_init_data_" in line:
                    print(f"Line {i}: {line}")
        return
    
    print("Successfully matched _init_data_ pattern")
    json_str = m.group(1)
    
    try:
        data = json.loads(json_str)
        print("Successfully parsed JSON")
        
        # Save parsed data
        with open("debug_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print("Saved parsed data to debug_data.json")
        
        # Navigate the data structure
        fields = data.get("data", {}).get("root", {}).get("fields", {})
        print(f"Fields keys: {list(fields.keys())}")
        
        mods = fields.get("mods", {})
        print(f"Mods keys: {list(mods.keys())}")
        
        item_list = mods.get("itemList", {})
        print(f"ItemList keys: {list(item_list.keys())}")
        
        content = item_list.get("content", [])
        print(f"Found {len(content)} items in content")
        
        if content:
            print("First item keys:", list(content[0].keys()))
            print("First item:", json.dumps(content[0], indent=2))
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing failed: {e}")
        # Save the problematic JSON for inspection
        with open("debug_json_raw.txt", "w", encoding="utf-8") as f:
            f.write(json_str[:1000])  # First 1000 chars
        print("Saved problematic JSON to debug_json_raw.txt")

if __name__ == "__main__":
    asyncio.run(debug_search())
