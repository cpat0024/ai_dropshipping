from __future__ import annotations

"""Logging configuration for the scraper.

Provides a configured logger with optional file logging when debug is enabled.
"""
import logging
from logging import Logger
from pathlib import Path


def get_logger(name: str = "aliexpress_scraper", *, debug: bool = False) -> Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    level = logging.DEBUG if debug else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    ch = logging.StreamHandler()
    ch.setLevel(level)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler added lazily via add_file_handler
    return logger


def add_file_handler(logger: Logger, log_path: Path) -> None:
    fh = logging.FileHandler(log_path)
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    fh.setFormatter(formatter)
    logger.addHandler(fh)
