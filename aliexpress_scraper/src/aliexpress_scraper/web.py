"""Console entry to run the built-in server."""

from __future__ import annotations

from .server import main


def run() -> int:
    return main()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(run())
