"""Custom exceptions for the scraper."""

class ScraperError(Exception):
    """Base exception for scraper errors."""


class AntiBotDetected(ScraperError):
    """Raised when a known anti-bot or CAPTCHA page is detected."""


class RobotsDisallowed(ScraperError):
    """Raised when robots.txt disallows scraping for a given path."""
