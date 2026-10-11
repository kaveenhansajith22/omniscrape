"""Rate limiter and backoff retry middleware to scrape politely and resist anti-scraping blocks."""
from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("omniscrape.rate_limiter")


class RateLimiter:
    """Enforces polite request delays with configurable random jitter to mimic human browsing."""

    def __init__(self, min_delay: float = 0.5, max_delay: float = 1.5):
        self.min_delay = max(0.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        self._last_request_time: float = 0.0

    async def wait(self) -> None:
        """Asynchronously sleep if necessary to satisfy the rate limit."""
        if self.min_delay <= 0 and self.max_delay <= 0:
            return

        target_delay = random.uniform(self.min_delay, self.max_delay)
        elapsed = time.time() - self._last_request_time
        remaining = target_delay - elapsed
        if remaining > 0:
            await asyncio.sleep(remaining)
        self._last_request_time = time.time()

    def wait_sync(self) -> None:
        """Synchronous version of wait."""
        if self.min_delay <= 0 and self.max_delay <= 0:
            return

        target_delay = random.uniform(self.min_delay, self.max_delay)
        elapsed = time.time() - self._last_request_time
        remaining = target_delay - elapsed
        if remaining > 0:
            time.sleep(remaining)
        self._last_request_time = time.time()


async def retry_with_backoff(
    coro_func: Callable[[], Coroutine[Any, Any, Any]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retry_statuses: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> Any:
    """Execute an async operation with exponential backoff on retryable errors."""
    delay = initial_delay
    last_exception = None

    for attempt in range(max_retries + 1):
        try:
            return await coro_func()
        except Exception as exc:
            last_exception = exc
            status_code = getattr(getattr(exc, "response", None), "status_code", None)
            
            # Check if status code is retryable or if it's a connection / timeout error
            is_retryable = (
                status_code in retry_statuses
                or "timeout" in str(exc).lower()
                or "connection" in str(exc).lower()
                or "reset" in str(exc).lower()
            )

            if attempt == max_retries or not is_retryable:
                logger.error(f"Request failed permanently after {attempt + 1} attempts: {exc}")
                raise exc

            # Add jitter to backoff delay
            sleep_duration = delay * (0.8 + 0.4 * random.random())
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries + 1} failed ({exc}). Retrying in {sleep_duration:.2f}s..."
            )
            await asyncio.sleep(sleep_duration)
            delay *= backoff_factor

    if last_exception:
        raise last_exception
