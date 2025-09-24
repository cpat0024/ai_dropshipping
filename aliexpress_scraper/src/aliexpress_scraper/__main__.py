"""Module entrypoint for `python -m aliexpress_scraper`.

Now forwards to the built-in web server. For CLI, use `aliexpress-scraper`.
"""

from __future__ import annotations

from .web import run as main

if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
