from __future__ import annotations

"""CLI wrapper using argparse (Scrapfly-only)."""
import argparse
import asyncio
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from .config import Config
from .logger import add_file_handler, get_logger
from .scrapfly_adapter import run_with_scrapfly


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="AliExpress scraper (Scrapfly backend)")
    p.add_argument("query", help="Search query")
    p.add_argument("--max-suppliers", type=int, default=5)
    p.add_argument("--max-products-per-seller", type=int, default=1)
    p.add_argument("--output", type=Path)
    p.add_argument("--csv", type=Path)
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--debug", action="store_true")
    # Scrapfly options
    p.add_argument(
        "--scrapfly-key", type=str, help="Scrapfly API key (or set SCRAPFLY_KEY env)"
    )
    p.add_argument(
        "--country",
        type=str,
        default="AU",
        help="Country code for localization with Scrapfly",
    )
    p.add_argument(
        "--aep-cookie", type=str, help="Optional aep_usuc_f cookie for localization"
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    # Load environment variables from .env file
    load_dotenv()

    parser = build_parser()
    args = parser.parse_args(argv)

    cfg = Config(
        query=args.query,
        max_suppliers=args.max_suppliers,
        max_products_per_seller=args.max_products_per_seller,
        output=args.output,
        csv=args.csv,
        limit=args.limit,
        debug=args.debug,
    ).finalize()

    logger = get_logger(debug=cfg.debug)
    if cfg.debug:
        add_file_handler(logger, Path("scraper.debug.log"))

    async def runner() -> int:
        key = args.scrapfly_key or os.environ.get("SCRAPFLY_KEY")
        if not key:
            print(
                "Scrapfly API key required: pass --scrapfly-key or set SCRAPFLY_KEY env"
            )
            return 2
        result = await run_with_scrapfly(
            args.query,
            max_suppliers=args.max_suppliers,
            max_products_per_seller=args.max_products_per_seller,
            limit=args.limit,
            country=args.country,
            key=key,
            cookie=args.aep_cookie,
        )
        # Write outputs (applies to both backends)
        if cfg.csv:
            from .output import write_csv

            write_csv(cfg.csv, result)
        if cfg.output:
            from .output import write_json

            write_json(cfg.output, result)
        from .output import print_summary

        print_summary(result)
        return 0

    return asyncio.run(runner())


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
