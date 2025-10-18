#!/usr/bin/env python3
"""
Test the improved AI scoring formula with sample products.
Demonstrates how the new algorithm works with different product scenarios.
"""

import math


def calculate_ai_score_improved(product):
    """
    Enhanced AI scoring algorithm:
    Score = 0.4×(Rating) + 0.3×(log-Sales) + 0.2×(Inventory/Price) + 0.1×(AI-Insight)
    """
    rating = product.get("rating", 0)
    orders = product.get("num_orders", 0)
    num_ratings = product.get("num_ratings", 0)
    price = product.get("price", 0)

    # 1. Rating Score (40% weight)
    rating_score = (rating / 5) * 100

    # 2. Logarithmic Sales Volume Score (30% weight)
    sales_score = (
        (math.log10(orders + 1) / math.log10(10000)) * 100 if orders > 0 else 0
    )
    sales_score = min(sales_score, 100)

    # 3. Inventory/Price Availability Score (20% weight)
    inventory_score = 0
    if price > 0:
        inventory_score += 50  # Has valid price
        if 1 <= price <= 50:
            inventory_score += 30
        elif 50 < price <= 100:
            inventory_score += 20
        else:
            inventory_score += 10

        if orders > 100:
            inventory_score += 20
        elif orders > 0:
            inventory_score += 10
    inventory_score = min(inventory_score, 100)

    # 4. AI-Insight Factor (10% weight)
    ai_insight = 50  # Baseline
    if num_ratings > 1000:
        ai_insight += 30
    elif num_ratings > 100:
        ai_insight += 20
    elif num_ratings > 10:
        ai_insight += 10

    if rating >= 4.5 and orders > 500:
        ai_insight += 20
    elif rating >= 4.0 and orders > 100:
        ai_insight += 10
    ai_insight = min(ai_insight, 100)

    # Calculate weighted final score
    final_score = (
        rating_score * 0.4
        + sales_score * 0.3
        + inventory_score * 0.2
        + ai_insight * 0.1
    )

    return {
        "final_score": round(final_score, 1),
        "components": {
            "rating_score": round(rating_score, 1),
            "sales_score": round(sales_score, 1),
            "inventory_score": round(inventory_score, 1),
            "ai_insight": round(ai_insight, 1),
        },
    }


def calculate_ai_score_old(product):
    """Old simple formula for comparison."""
    rating = product.get("rating", 0)
    orders = product.get("num_orders", 0)
    return round((rating / 5 * 50) + (min(orders / 1000, 1) * 50), 1)


# Test products
test_products = [
    {
        "name": "Premium Bestseller",
        "rating": 4.8,
        "num_orders": 5000,
        "num_ratings": 2500,
        "price": 25,
    },
    {
        "name": "Mid-Range Popular",
        "rating": 4.2,
        "num_orders": 150,
        "num_ratings": 80,
        "price": 45,
    },
    {
        "name": "New Promising Product",
        "rating": 4.5,
        "num_orders": 12,
        "num_ratings": 8,
        "price": 30,
    },
    {
        "name": "High Volume Low Rating",
        "rating": 3.5,
        "num_orders": 10000,
        "num_ratings": 5000,
        "price": 15,
    },
    {
        "name": "Perfect Rating Few Sales",
        "rating": 5.0,
        "num_orders": 5,
        "num_ratings": 3,
        "price": 75,
    },
    {
        "name": "No Data Product",
        "rating": 0,
        "num_orders": 0,
        "num_ratings": 0,
        "price": 0,
    },
]


def print_comparison():
    """Print comparison of old vs new formula."""
    print("=" * 100)
    print("AI SCORING FORMULA COMPARISON")
    print("=" * 100)
    print("\nOLD FORMULA: Score = 0.5×(Rating/5) + 0.5×(min(Orders/1000, 1))")
    print(
        "NEW FORMULA: Score = 0.4×(Rating) + 0.3×(log-Sales) + 0.2×(Inventory/Price) + 0.1×(AI-Insight)"
    )
    print("=" * 100)
    print()

    for product in test_products:
        print(f"\n📦 {product['name']}")
        print(
            f"   Rating: {product['rating']}/5 | Orders: {product['num_orders']:,} | Reviews: {product['num_ratings']:,} | Price: ${product['price']}"
        )
        print("-" * 100)

        # Old score
        old_score = calculate_ai_score_old(product)
        print(f"   OLD SCORE: {old_score}/100")

        # New score
        new_result = calculate_ai_score_improved(product)
        new_score = new_result["final_score"]
        components = new_result["components"]

        print(f"   NEW SCORE: {new_score}/100")
        print(
            f"   └─ Rating:     {components['rating_score']}/100 × 0.4 = {components['rating_score'] * 0.4:.1f}"
        )
        print(
            f"   └─ Sales:      {components['sales_score']}/100 × 0.3 = {components['sales_score'] * 0.3:.1f}"
        )
        print(
            f"   └─ Inventory:  {components['inventory_score']}/100 × 0.2 = {components['inventory_score'] * 0.2:.1f}"
        )
        print(
            f"   └─ AI-Insight: {components['ai_insight']}/100 × 0.1 = {components['ai_insight'] * 0.1:.1f}"
        )

        # Interpretation
        if new_score >= 90:
            grade = "⭐⭐⭐⭐⭐ EXCELLENT"
        elif new_score >= 80:
            grade = "⭐⭐⭐⭐ VERY GOOD"
        elif new_score >= 70:
            grade = "⭐⭐⭐ GOOD"
        elif new_score >= 60:
            grade = "⭐⭐ FAIR"
        elif new_score >= 50:
            grade = "⭐ POOR"
        else:
            grade = "❌ VERY POOR"

        print(f"   RATING: {grade}")

        # Show score change
        change = new_score - old_score
        change_symbol = "↑" if change > 0 else "↓" if change < 0 else "→"
        print(f"   CHANGE: {change_symbol} {abs(change):.1f} points from old formula")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print("=" * 100)
    print("\n✅ Improved formula provides:")
    print("   • More nuanced scoring across all product types")
    print("   • Better handling of extreme sales volumes (logarithmic scaling)")
    print("   • Consideration of price and availability")
    print("   • Review credibility assessment")
    print("   • Fair scoring that doesn't over-reward any single metric")
    print("\n" + "=" * 100)


if __name__ == "__main__":
    print_comparison()
