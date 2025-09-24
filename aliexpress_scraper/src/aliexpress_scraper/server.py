"""Built-in HTTP server to serve the frontend and handle scrape requests.

This avoids external web frameworks. It serves files from the repo's `public/`
folder and exposes a JSON API at POST /api/scrape.

Flow:
1) Frontend POSTs a JSON body with a search query and optional params.
2) Server runs the Scrapfly-based scraper.
3) Server generates a temporary CSV, passes JSON/CSV to the CleanerAgent (Gemini).
4) CSV is deleted immediately after AI processing.
5) Server returns cleaned insights and the raw scraped JSON to the frontend.
"""

from __future__ import annotations

import asyncio
import json
import mimetypes
import os
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:  # graceful import for explicit Scrapfly error handling
    from scrapfly.errors import ApiHttpClientError as ScrapflyHttpError  # type: ignore
except Exception:  # pragma: no cover

    class ScrapflyHttpError(Exception):
        pass


try:
    from dotenv import load_dotenv  # type: ignore

    _HAS_DOTENV = True
except ImportError:  # pragma: no cover - optional
    _HAS_DOTENV = False

from .logger import get_logger
from .models import ScrapeResult
from .scrapfly_adapter import run_with_scrapfly


LOGGER = get_logger()
REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_DIR = REPO_ROOT / "public"

# Load .env from repo root explicitly if python-dotenv is available
if _HAS_DOTENV:  # pragma: no cover - optional
    try:
        load_dotenv(REPO_ROOT / ".env")
    except Exception:
        # Fallback to default resolution if direct path fails
        load_dotenv()


def scrape_result_to_csv_string(result: ScrapeResult) -> str:
    """Build a CSV string from ScrapeResult without touching disk."""
    import csv
    import io

    fields = [
        "seller_name",
        "seller_url",
        "product_title",
        "product_url",
        "product_id",
        "price",
        "currency",
        "rating",
        "num_ratings",
        "num_orders",
    ]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for s in result.suppliers:
        for p in s.products:
            w.writerow(
                {
                    "seller_name": s.seller_name,
                    "seller_url": s.seller_url,
                    "product_title": p.product_title,
                    "product_url": p.product_url,
                    "product_id": p.product_id,
                    "price": p.price or "",
                    "currency": p.currency or "",
                    "rating": p.rating or "",
                    "num_ratings": p.num_ratings or "",
                    "num_orders": p.num_orders or "",
                }
            )
    return buf.getvalue()


def write_temp_csv(content: str) -> Path:
    """Write CSV content to a temporary file in a temp dir within the repo."""
    tmp_dir = PUBLIC_DIR / "data" / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix="scrape_", suffix=".csv", dir=str(tmp_dir))
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return Path(path)


def delete_file_safe(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        LOGGER.warning("Failed to delete temp file: %s", path)


class CleanerAgent:
    """Simple AI cleaner using Google's Generative AI SDK (Gemini).

    Reads GOOGLE_API_KEY from environment. If not present or SDK not installed,
    falls back to returning a basic normalized summary derived locally.
    """

    def __init__(self, model: str = "gemini-1.5-flash") -> None:
        self.model_name = model
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self._client: Optional[Any] = None
        if self.api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model_name)
            except ImportError as e:  # pragma: no cover
                LOGGER.warning("google-generativeai not available: %s", e)
                self._client = None

    async def clean(
        self, result: ScrapeResult, csv_path: Optional[Path]
    ) -> Dict[str, Any]:
        """Return a cleaned summary dict. CSV is optional; if provided it's deleted here."""
        try:
            if self._client:
                prompt = (
                    "You are an AI-powered dropshipping supplier evaluation expert. Analyze the provided "
                    "AliExpress scraping results and generate intelligent insights for supplier selection. "
                    "Your analysis should focus on these key dropshipping metrics: "
                    "1. Product pricing competitiveness "
                    "2. Shipping performance and reliability "
                    "3. Customer satisfaction (reviews, ratings) "
                    "4. Supplier credibility and trustworthiness "
                    "5. Return policies and customer service "
                    "CRITICAL: Generate a comprehensive JSON response with: "
                    "- 'top_products': Array of up to 10 best products ranked by AI scoring algorithm. "
                    "  IMPORTANT: Each product MUST include ALL original fields: product_title, product_url, product_id, seller_name, price, currency, rating, num_ratings, num_orders, and add ai_score (0-100). "
                    "- 'top_sellers': Array of up to 5 best suppliers with ALL original seller fields preserved "
                    "- 'insights': Array of 5-8 actionable insights focusing on dropshipping strategy, market opportunities, pricing analysis, and risk assessment "
                    "- 'market_analysis': Object with competitive landscape, pricing trends, and demand indicators "
                    "- 'recommendations': Array of specific recommendations for dropshipping success "
                    "- 'risk_factors': Array of potential risks and mitigation strategies "
                    "PRESERVE ALL URLs: Keep all product_url and seller_url fields exactly as provided in the input data. "
                    "Apply advanced sentiment analysis to reviews and provide confidence scores. "
                    "Consider seasonal trends, shipping costs, and profit margins in your analysis. "
                    "Respond with valid JSON only, no markdown formatting."
                )
                # Send JSON as plain text content, not as structured data
                payload_text = json.dumps(
                    {
                        "query": result.query,
                        "suppliers": [
                            {
                                "seller_name": s.seller_name,
                                "seller_url": s.seller_url,
                                "seller_rating": s.seller_rating,
                                "num_followers": s.num_followers,
                                "store_location": s.store_location,
                                "products": [
                                    {
                                        "product_title": p.product_title,
                                        "product_url": p.product_url,
                                        "product_id": p.product_id,
                                        "price": p.price,
                                        "currency": p.currency,
                                        "rating": p.rating,
                                        "num_ratings": p.num_ratings,
                                        "num_orders": p.num_orders,
                                    }
                                    for p in s.products
                                ],
                            }
                            for s in result.suppliers
                        ],
                    },
                    indent=2,
                )

                # Create content as simple text
                content_parts = [prompt, "\n\nAliExpress Data:\n", payload_text]

                if csv_path and csv_path.exists():
                    try:
                        csv_content = csv_path.read_text(encoding="utf-8")
                        content_parts.append("\n\nCSV Data:\n")
                        content_parts.append(csv_content[:2000])  # Limit CSV size
                    except OSError:
                        pass

                # Send as single text content
                full_content = "".join(content_parts)
                resp = await asyncio.to_thread(
                    self._client.generate_content, full_content
                )  # type: ignore[union-attr]
                text = resp.text if hasattr(resp, "text") else str(resp)
                cleaned = self.extract_json(text)
            else:
                cleaned = self._local_fallback_clean(result)

            # Safety check: Ensure URLs are preserved in cleaned results
            if cleaned and "top_products" in cleaned:
                self._ensure_urls_preserved(cleaned["top_products"], result)

            return cleaned
        finally:
            # Always delete temp CSV if present
            if csv_path and csv_path.exists():
                delete_file_safe(csv_path)

    def _ensure_urls_preserved(
        self, ai_products: list, original_result: ScrapeResult
    ) -> None:
        """Ensure URLs are preserved in AI-processed products by matching with original data."""
        # Create a lookup of original products by title
        original_products = {}
        for supplier in original_result.suppliers:
            for product in supplier.products:
                if product.product_title:
                    original_products[product.product_title.lower().strip()] = {
                        "product_url": product.product_url,
                        "product_id": product.product_id,
                        "seller_url": supplier.seller_url,
                    }

        # Fill in missing URLs in AI products
        for ai_product in ai_products:
            if (
                not ai_product.get("product_url")
                or ai_product.get("product_url") == "#"
            ):
                title_key = (ai_product.get("product_title") or "").lower().strip()
                if title_key in original_products:
                    ai_product["product_url"] = original_products[title_key][
                        "product_url"
                    ]
                    if not ai_product.get("product_id"):
                        ai_product["product_id"] = original_products[title_key][
                            "product_id"
                        ]

    @staticmethod
    def extract_json(text: str) -> Dict[str, Any]:
        """Try to parse JSON from a model response; tolerate code fences."""
        import re

        s = text.strip()
        # Remove common markdown fences
        if s.startswith("```") or s.startswith("```json"):
            s = re.sub(r"^```(?:json)?\n|\n```$", "", s)
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            # Best-effort: find a JSON object in the string
            m = re.search(r"\{[\s\S]*\}$", s)
            if m:
                try:
                    return json.loads(m.group(0))
                except json.JSONDecodeError:
                    pass
        # Last resort minimal structure
        return {"insights": ["Cleaner could not parse response"], "raw": s}

    @staticmethod
    def _local_fallback_clean(result: ScrapeResult) -> Dict[str, Any]:
        """Enhanced local fallback cleaner with basic dropshipping analysis."""
        products: list[Dict[str, Any]] = []
        total_orders = 0
        total_ratings = 0
        rating_count = 0

        for s in result.suppliers:
            for p in s.products:
                orders = p.num_orders or 0
                rating = p.rating or 0
                total_orders += orders
                if rating > 0:
                    total_ratings += rating
                    rating_count += 1

                products.append(
                    {
                        "product_title": p.product_title,
                        "product_url": p.product_url,
                        "seller_name": s.seller_name,
                        "price": p.price,
                        "rating": rating,
                        "num_orders": orders,
                        "ai_score": min(
                            100, int((rating / 5 * 50) + (min(orders / 1000, 1) * 50))
                        ),
                    }
                )

        # Sort by AI score (rating + order volume)
        products.sort(
            key=lambda x: (
                x.get("ai_score", 0),
                x.get("rating", 0),
                x.get("num_orders", 0),
            ),
            reverse=True,
        )
        top_products = products[:10]

        # Analyze suppliers
        supplier_scores = []
        for s in result.suppliers:
            avg_product_rating = (
                sum(p.rating or 0 for p in s.products) / len(s.products)
                if s.products
                else 0
            )
            total_product_orders = sum(p.num_orders or 0 for p in s.products)

            supplier_scores.append(
                {
                    "seller_name": s.seller_name,
                    "seller_url": s.seller_url,
                    "seller_rating": s.seller_rating,
                    "num_products": len(s.products),
                    "avg_product_rating": round(avg_product_rating, 2),
                    "total_orders": total_product_orders,
                    "store_location": s.store_location,
                    "reliability_score": min(
                        100,
                        int(
                            (s.seller_rating or 0) / 5 * 60
                            + avg_product_rating / 5 * 40
                        ),
                    ),
                }
            )

        supplier_scores.sort(key=lambda x: x.get("reliability_score", 0), reverse=True)
        top_sellers = supplier_scores[:5]

        # Generate intelligent insights
        avg_rating = total_ratings / rating_count if rating_count > 0 else 0
        high_rated_products = len([p for p in products if (p.get("rating", 0) >= 4.5)])
        high_volume_products = len(
            [p for p in products if (p.get("num_orders", 0) >= 1000)]
        )

        insights = [
            f"Analyzed {len(result.suppliers)} suppliers with {len(products)} total products",
            f"Average product rating: {avg_rating:.1f}/5.0 ({rating_count} rated products)",
            f"Found {high_rated_products} highly-rated products (4.5+ stars) - excellent for dropshipping",
            f"Identified {high_volume_products} high-volume products (1000+ orders) - proven market demand",
            f"Total market orders: {total_orders:,} across all products analyzed",
        ]

        if avg_rating >= 4.0:
            insights.append(
                "⭐ Market shows strong quality indicators - good for brand reputation"
            )
        if high_volume_products >= 3:
            insights.append(
                "📈 Multiple proven bestsellers found - reduced market risk"
            )
        if len(result.suppliers) >= 3:
            insights.append(
                "🏪 Diverse supplier base available - good for supply chain resilience"
            )

        # Market analysis
        price_ranges = [
            float(p.get("price", "0").replace("$", "").replace(",", ""))
            for p in products
            if p.get("price")
        ]
        avg_price = sum(price_ranges) / len(price_ranges) if price_ranges else 0

        market_analysis = {
            "total_suppliers": len(result.suppliers),
            "total_products": len(products),
            "avg_rating": round(avg_rating, 2),
            "avg_price": round(avg_price, 2),
            "high_quality_ratio": round(high_rated_products / len(products) * 100, 1)
            if products
            else 0,
            "proven_demand_ratio": round(high_volume_products / len(products) * 100, 1)
            if products
            else 0,
        }

        recommendations = [
            "Focus on suppliers with 4.5+ ratings and 1000+ orders for reliable dropshipping",
            "Consider bulk ordering from top-rated suppliers to negotiate better prices",
            "Monitor seasonal trends and adjust inventory based on order volume patterns",
            "Establish relationships with multiple suppliers to ensure consistent stock availability",
        ]

        risk_factors = [
            "Verify supplier shipping times and costs for your target markets",
            "Check return policies and customer service responsiveness",
            "Monitor product quality through sample orders before bulk purchasing",
            "Consider currency fluctuations when planning profit margins",
        ]

        return {
            "top_products": top_products,
            "top_sellers": top_sellers,
            "insights": insights,
            "market_analysis": market_analysis,
            "recommendations": recommendations,
            "risk_factors": risk_factors,
        }


class OrchestratorAgent:
    """Optional planning agent using Gemini to validate/tune parameters.

    If the Google SDK isn't available, returns the input params unchanged.
    """

    def __init__(self, model: str = "gemini-1.5-flash") -> None:
        self.model_name = model
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self._client: Optional[Any] = None
        if self.api_key:
            try:
                import google.generativeai as genai  # type: ignore

                genai.configure(api_key=self.api_key)
                self._client = genai.GenerativeModel(self.model_name)
            except ImportError:
                self._client = None

    async def plan(self, query: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._client:
            return params
        prompt = (
            "Given the following scrape request parameters for an AliExpress product search, "
            "return a compact JSON with the same keys but with values clamped to safe ranges. "
            "Keys: max_suppliers (1..10), max_products_per_seller (1..10), limit (1..50), country (2 letters)."
        )

        # Send as plain text instead of structured content
        content = f"{prompt}\n\nRequest: {json.dumps({'query': query, **params})}"

        try:
            resp = await asyncio.to_thread(self._client.generate_content, content)  # type: ignore[union-attr]
            text = resp.text if hasattr(resp, "text") else str(resp)
            cleaned = CleanerAgent.extract_json(text)
            # Merge back into params conservatively
            out = dict(params)
            for k in ("max_suppliers", "max_products_per_seller", "limit", "country"):
                if k in cleaned:
                    out[k] = cleaned[k]
            # Clamp
            out["max_suppliers"] = max(1, min(10, int(out.get("max_suppliers", 5))))
            out["max_products_per_seller"] = max(
                1, min(10, int(out.get("max_products_per_seller", 1)))
            )
            out["limit"] = max(1, min(50, int(out.get("limit", 20))))
            c = str(out.get("country", "AU")).upper()
            out["country"] = c[:2] if len(c) >= 2 else "AU"
            return out
        except (RuntimeError, ValueError, TypeError):
            return params


class Handler(BaseHTTPRequestHandler):
    server_version = "AliScraperServer/0.1"

    def _set_cors(self) -> None:
        # Same-origin in practice, but allow basic CORS for local dev.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._set_cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        # Serve static files from public/
        rel_path = self.path.split("?", 1)[0]
        if rel_path == "/":
            rel_path = "/index.html"
        file_path = PUBLIC_DIR / rel_path.lstrip("/")
        if file_path.is_dir():
            file_path = file_path / "index.html"
        if not file_path.exists():
            self.send_response(HTTPStatus.NOT_FOUND)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        mime, _ = mimetypes.guess_type(str(file_path))
        try:
            data = file_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            if mime:
                self.send_header("Content-Type", mime)
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
        except OSError as e:
            LOGGER.error("Failed to read static file %s: %s", file_path, e)
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Error")

    def do_POST(self) -> None:  # noqa: N802
        if self.path.split("?", 1)[0] != "/api/scrape":
            self.send_response(HTTPStatus.NOT_FOUND)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw.decode("utf-8"))
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            self.send_response(HTTPStatus.BAD_REQUEST)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Invalid JSON")
            return

        # Extract params
        query = str(body.get("query", "")).strip()
        if not query:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Missing query")
            return

        max_suppliers = int(body.get("max_suppliers", 5))
        max_products_per_seller = int(body.get("max_products_per_seller", 1))
        limit = int(body.get("limit", 20))
        country = str(body.get("country", os.environ.get("SCRAPE_COUNTRY", "AU")))
        scrapfly_key = body.get("scrapfly_key") or os.environ.get("SCRAPFLY_KEY")
        aep_cookie = body.get("aep_cookie") or os.environ.get("AEP_USUC_F")

        if not scrapfly_key:
            self.send_response(HTTPStatus.BAD_REQUEST)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Missing Scrapfly API key")
            return

        # Run the orchestrator (optional), scraper, and cleaning agent
        async def _run() -> Tuple[ScrapeResult, Dict[str, Any]]:
            planned = await OrchestratorAgent().plan(
                query,
                {
                    "max_suppliers": max_suppliers,
                    "max_products_per_seller": max_products_per_seller,
                    "limit": limit,
                    "country": country,
                },
            )
            result = await run_with_scrapfly(
                query,
                max_suppliers=int(planned.get("max_suppliers", max_suppliers)),
                max_products_per_seller=int(
                    planned.get("max_products_per_seller", max_products_per_seller)
                ),
                limit=int(planned.get("limit", limit)),
                country=str(planned.get("country", country)),
                key=scrapfly_key,
                cookie=aep_cookie,
            )
            # Build CSV content and write to temp file
            csv_str = scrape_result_to_csv_string(result)
            tmp_csv = write_temp_csv(csv_str)
            cleaned = await CleanerAgent().clean(result, tmp_csv)
            return result, cleaned

        try:
            result, cleaned = asyncio.run(_run())
        except ScrapflyHttpError as e:
            # Surface upstream error details nicely to the frontend
            msg = str(e)
            LOGGER.error("Scrapfly error: %s", msg)
            payload = {"ok": False, "error": "scrapfly", "message": msg}
            data = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Content-Type", "application/json")
            self._set_cors()
            self.end_headers()
            self.wfile.write(data)
            return
        except (RuntimeError, OSError, ValueError) as e:
            LOGGER.error("Scrape job failed: %s", e)
            self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
            self._set_cors()
            self.end_headers()
            self.wfile.write(b"Scrape failed")
            return

        # Respond with cleaned + raw
        payload = {
            "ok": True,
            "query": query,
            "cleaned": cleaned,
            "raw": result.to_dict(),
        }
        data = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self._set_cors()
        self.end_headers()
        self.wfile.write(data)


def main(host: str = "127.0.0.1", port: int = 8787) -> int:
    httpd = ThreadingHTTPServer((host, port), Handler)
    addr = f"http://{host}:{port}"
    LOGGER.info("Serving frontend at %s (public dir: %s)", addr, PUBLIC_DIR)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:  # pragma: no cover
        LOGGER.info("Shutting down...")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
