#!/usr/bin/env python3
"""Analyze the actual structure of items to find store information."""

import json

# Load the debug data
with open("debug_data.json", "r") as f:
    data = json.load(f)

# Get the items
items = data["data"]["root"]["fields"]["mods"]["itemList"]["content"]
print(f"Total items: {len(items)}")

# Analyze first few items for store information
for i, item in enumerate(items[:5]):
    print(f"\n=== Item {i} ===")
    print(f"Product ID: {item.get('productId')}")
    print(f"Title: {item.get('title', {}).get('displayTitle', '')[:50]}...")
    
    # Check if there's a store field
    if 'store' in item:
        print(f"Store field found: {item['store']}")
    else:
        print("No direct 'store' field")
    
    # Check trace field for store info
    trace = item.get('trace', {})
    if trace:
        # Check p4pExposure
        p4p_exposure = trace.get('p4pExposure', {})
        if p4p_exposure and 'p4pExtendParam' in p4p_exposure:
            print(f"P4P store info: {p4p_exposure['p4pExtendParam']}")
        
        # Check utLogMap for store info
        ut_log = trace.get('utLogMap', {})
        store_keys = [k for k in ut_log.keys() if 'store' in k.lower()]
        if store_keys:
            print(f"Store keys in utLogMap: {store_keys}")
            for key in store_keys:
                print(f"  {key}: {ut_log[key]}")
    
    # Check all top-level keys
    print(f"Top-level keys: {list(item.keys())}")
    
print(f"\n=== Summary ===")
# Count items with different types of store information
store_field_count = sum(1 for item in items if 'store' in item)
p4p_store_count = sum(1 for item in items if 'p4pExtendParam' in item.get('trace', {}).get('p4pExposure', {}))
print(f"Items with 'store' field: {store_field_count}")
print(f"Items with p4pExtendParam: {p4p_store_count}")

# Look for any pattern in how store URLs might be constructed
print("\n=== Store URL Analysis ===")
for i, item in enumerate(items[:3]):
    product_id = item.get('productId')
    if product_id:
        print(f"Product {i} ID: {product_id}")
        # AliExpress store URLs are often in format: https://www.aliexpress.com/store/{store_id}
        # But we need to figure out how to get the store_id
