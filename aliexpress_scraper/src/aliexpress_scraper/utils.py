from __future__ import annotations

"""Utility helpers: slugify, time, retry, sleep, robots.txt check."""
import asyncio
import random
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Awaitable, Callable, Optional, TypeVar
from urllib.parse import urlparse
from urllib import robotparser

T = TypeVar("T")


def slugify(text: str) -> str:
    s = text.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "query"


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def random_sleep(min_s: float = 0.25, max_s: float = 1.5) -> Awaitable[None]:
    """Async sleep with jitter."""
    delay = random.uniform(min_s, max_s)
    return asyncio.sleep(delay)


@dataclass
class BackoffConfig:
    retries: int = 3
    base: float = 1.0
    factor: float = 2.0
    jitter: float = 0.2


def exponential_backoff_retry(
    *,
    retries: int = 3,
    base: float = 1.0,
    factor: float = 2.0,
    jitter: float = 0.2,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Retry async function with exponential backoff and jitter."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            delay = base
            last_exc: Optional[BaseException] = None
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:  # type: ignore[misc]
                    last_exc = exc
                    # jittered delay
                    d = delay * (1 + random.uniform(-jitter, jitter))
                    await asyncio.sleep(max(0.1, d))
                    delay *= factor
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


def check_robots_txt(url: str, user_agent: str = "*") -> bool:
    """Return True if URL is allowed by robots.txt for given UA."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        # If robots cannot be fetched, default to allowed=False only if respect flag used elsewhere
        return True
    return rp.can_fetch(user_agent, url)
