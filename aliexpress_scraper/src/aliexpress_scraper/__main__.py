from __future__ import annotations

"""Module entrypoint for `python -m aliexpress_scraper`.

Just forwards to CLI main.
"""
from .cli import main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
