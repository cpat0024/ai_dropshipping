# AI Scoring Formula Documentation

## Overview
The AI Supplier Evaluation System uses a sophisticated scoring algorithm to rank products for dropshipping success. This formula combines multiple factors with weighted importance to provide accurate product rankings.

## Formula

```
Overall Score = 0.4×(Rating Score) + 0.3×(Sales Volume Score) + 0.2×(Inventory/Price Score) + 0.1×(AI-Insight Score)
```

**Final Score Range:** 0-100 (higher is better)

---

## Component Breakdown

### 1. Rating Score (40% Weight)
**Purpose:** Measures customer satisfaction and product quality

**Calculation:**
```
Rating Score = (Product Rating / 5) × 100
```

**Normalization:**
- 5-star rating → 100 points
- 4-star rating → 80 points
- 3-star rating → 60 points
- 2-star rating → 40 points
- 1-star rating → 20 points
- No rating → 0 points

**Why 40%?** Rating is the strongest indicator of customer satisfaction and product quality, making it the most important factor for dropshipping success.

---

### 2. Sales Volume Score (30% Weight)
**Purpose:** Indicates market demand and product popularity

**Calculation (Logarithmic Scaling):**
```
Sales Score = (log₁₀(orders + 1) / log₁₀(10000)) × 100
```

**Scale Examples:**
- 1 order → ~0 points
- 10 orders → ~33 points
- 100 orders → ~66 points
- 1,000 orders → ~100 points
- 10,000+ orders → 100 points (capped)

**Why Logarithmic?**
- Handles extreme variations in order volumes (from 1 to 100,000+)
- Diminishing returns: difference between 1 and 10 orders is more significant than between 10,000 and 10,010
- Prevents high-volume products from dominating the score unfairly

**Why 30%?** Sales volume is a strong indicator of market validation and demand, but quality (rating) is more important for long-term success.

---

### 3. Inventory/Price Availability Score (20% Weight)
**Purpose:** Evaluates product availability and pricing competitiveness

**Calculation:**
```
Base Score:
- Has valid price: +50 points

Price Competitiveness:
- $1-$50 (optimal range): +30 points
- $51-$100 (acceptable): +20 points
- $100+ (premium): +10 points

Stock Availability Indicators:
- 100+ orders: +20 points (high availability)
- 1-99 orders: +10 points (some availability)
- 0 orders: +0 points

Maximum: 100 points
```

**Why This Matters?**
- Ensures products are actually available for purchase
- Identifies competitively priced items with better profit margins
- Flags high-demand products with proven inventory flow

**Why 20%?** Price and availability are important but secondary to quality and demand validation.

---

### 4. AI-Insight Score (10% Weight)
**Purpose:** Advanced quality signals and market intelligence

**Calculation:**
```
Baseline: 50 points

Review Credibility Bonus:
- 1,000+ reviews: +30 points
- 100-999 reviews: +20 points
- 10-99 reviews: +10 points
- <10 reviews: +0 points

Quality + Demand Combination:
- Rating ≥4.5 AND Orders >500: +20 points (premium product)
- Rating ≥4.0 AND Orders >100: +10 points (good product)

Maximum: 100 points
```

**Why This Matters?**
- More reviews = more reliable rating (prevents fake review manipulation)
- Combines quality with demand to identify true winners
- Identifies premium products worth higher investment

**Why 10%?** Provides nuanced insights without overcomplicating the main scoring factors.

---

## Example Calculations

### Example 1: Premium Product
- Rating: 4.8/5 (96 points)
- Orders: 5,000 (92 points using log scale)
- Price: $25 (100 points - good price + high availability)
- Reviews: 2,500 (100 points - high credibility)

**Final Score:**
```
= (96 × 0.4) + (92 × 0.3) + (100 × 0.2) + (100 × 0.1)
= 38.4 + 27.6 + 20 + 10
= 96 points ⭐ Excellent
```

### Example 2: Mid-Range Product
- Rating: 4.2/5 (84 points)
- Orders: 150 (71 points using log scale)
- Price: $45 (80 points - good price + some availability)
- Reviews: 80 (70 points - moderate credibility)

**Final Score:**
```
= (84 × 0.4) + (71 × 0.3) + (80 × 0.2) + (70 × 0.1)
= 33.6 + 21.3 + 16 + 7
= 77.9 ≈ 78 points ✅ Good
```

### Example 3: New Product
- Rating: 4.5/5 (90 points)
- Orders: 12 (36 points using log scale)
- Price: $30 (80 points - good price + low availability)
- Reviews: 8 (50 points - baseline only)

**Final Score:**
```
= (90 × 0.4) + (36 × 0.3) + (80 × 0.2) + (50 × 0.1)
= 36 + 10.8 + 16 + 5
= 67.8 ≈ 68 points ⚠️ Promising but risky
```

---

## Score Interpretation

| Score Range | Rating | Description |
|-------------|--------|-------------|
| 90-100 | ⭐⭐⭐⭐⭐ Excellent | Premium products with proven success - highest confidence |
| 80-89 | ⭐⭐⭐⭐ Very Good | Strong products with solid metrics - recommended |
| 70-79 | ⭐⭐⭐ Good | Decent products worth considering - moderate risk |
| 60-69 | ⭐⭐ Fair | Marginal products - higher risk, requires caution |
| 50-59 | ⭐ Poor | Weak products - not recommended |
| 0-49 | ❌ Very Poor | Avoid - insufficient data or poor metrics |

---

## Advantages Over Simple Formulas

### Traditional Simple Formula:
```
Score = 0.5×(Rating) + 0.5×(Orders/1000)
```

**Problems:**
- Linear sales scaling doesn't handle outliers well
- Ignores price and availability
- No consideration for review credibility
- High-volume products dominate unfairly

### Our Improved Formula:
✅ Logarithmic scaling for fair sales comparison  
✅ Considers price competitiveness and availability  
✅ Accounts for review credibility  
✅ Identifies premium products through multi-factor analysis  
✅ Balanced weights prevent any single factor from dominating  
✅ Provides nuanced scoring for better decision-making  

---

## Implementation

### Frontend (JavaScript)
```javascript
calculateAIScore(product) {
  const rating = product.rating || 0;
  const orders = product.num_orders || 0;
  const numRatings = product.num_ratings || 0;
  const hasPrice = product.price && product.price !== 'N/A';
  
  // Apply the formula...
  return Math.round(finalScore);
}
```

### Backend (Python)
```python
# Calculate AI score using improved formula
rating_score = (rating / 5) * 100
sales_score = (math.log10(orders + 1) / math.log10(10000)) * 100
inventory_score = calculate_inventory_price_score(...)
ai_insight = calculate_ai_insight(...)

final_score = (
    rating_score * 0.4 +
    sales_score * 0.3 +
    inventory_score * 0.2 +
    ai_insight * 0.1
)
```

### AI Integration (Gemini)
The formula is also embedded in the Gemini AI prompt to ensure consistent scoring when AI processes the data:
```
AI SCORING FORMULA: ai_score = 0.4×(rating/5×100) + 0.3×(log10(orders+1)/log10(10000)×100) + 0.2×(inventory_price_score) + 0.1×(insight_score)
```

---

## Validation & Testing

To test the formula with real products:
1. Run the scraper on a product search
2. Check the AI Score column in the results table
3. Verify that high-quality, high-demand products rank at the top
4. Compare with manual assessment of product quality

---

## Future Enhancements

Potential improvements for future versions:
- **Shipping cost factor** (reduce score for expensive shipping)
- **Supplier rating integration** (factor in seller reputation)
- **Seasonal trend detection** (adjust for market timing)
- **Profit margin calculator** (estimated revenue potential)
- **Competition analysis** (market saturation metrics)
- **Return rate prediction** (quality assurance scoring)

---

## References

- Logarithmic scaling: [Understanding Log Scales](https://en.wikipedia.org/wiki/Logarithmic_scale)
- E-commerce metrics: Industry best practices for product evaluation
- AliExpress data: Real-world marketplace indicators
- Dropshipping success factors: Quality, demand, pricing, reliability

---

**Last Updated:** October 12, 2025  
**Version:** 2.0 (Enhanced Formula)  
**Status:** Active in Production
