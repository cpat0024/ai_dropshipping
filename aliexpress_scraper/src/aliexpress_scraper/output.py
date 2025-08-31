from __future__ import annotations

"""Output writers for JSON/CSV and optional image downloading."""
import csv
import json
from pathlib import Path
from typing import Iterable, List, Optional

import requests

from .logger import get_logger
from .models import Product, ScrapeResult, Seller
from .utils import slugify


def write_json(path: Path, result: ScrapeResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)


def write_csv(path: Path, result: ScrapeResult) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in result.suppliers:
            for p in s.products:
                w.writerow({
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
                })


def download_images(base_dir: Path, sellers: Iterable[Seller]) -> None:
    logger = get_logger()
    for s in sellers:
        seller_dir = base_dir / slugify(s.seller_name)
        seller_dir.mkdir(parents=True, exist_ok=True)
        for p in s.products:
            local_paths: List[str] = []
            for idx, url in enumerate(p.image_urls[:10]):
                try:
                    r = requests.get(url, timeout=15)
                    r.raise_for_status()
                    ext = ".jpg"
                    fname = f"{slugify(p.product_id or str(idx))}{ext}"
                    fpath = seller_dir / fname
                    fpath.write_bytes(r.content)
                    local_paths.append(str(fpath))
                except Exception as e:
                    logger.warning("Failed to download image %s: %s", url, e)
            if local_paths:
                p.image_urls = local_paths


def print_summary(result: ScrapeResult) -> None:
    print(f"Query: {result.query}")
    print(f"Suppliers: {len(result.suppliers)}")
    for s in result.suppliers:
        print(f"  - {s.seller_name} ({s.seller_url}) -> {len(s.products)} products")
