"""High-performance asynchronous static HTTP engine powered by httpx."""
from __future__ import annotations

import logging
import time
import httpx

from omniscrape.config.models import ScraperConfig
from omniscrape.engines.base import BaseEngine, EngineResponse
from omniscrape.middleware.proxies import ProxyManager
from omniscrape.middleware.rate_limiter import RateLimiter, retry_with_backoff
from omniscrape.middleware.user_agents import UserAgentRotator

logger = logging.getLogger("omniscrape.engine.static")


class StaticEngine(BaseEngine):
    """Asynchronous HTTP engine with proxy rotation, polite delays, and backoff retries."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.rate_limiter = RateLimiter(min_delay=config.min_delay, max_delay=config.max_delay)
        self.ua_rotator = UserAgentRotator(mode=config.user_agent_mode)
        self.proxy_manager = ProxyManager(proxies=config.proxies)
        self._client: httpx.AsyncClient | None = None

    def _get_headers(self) -> dict[str, str]:
        """Generate browser headers merged with custom user headers."""
        headers = self.ua_rotator.get_browser_headers() if self.config.rotate_user_agent else {}
        if self.config.headers:
            headers.update(self.config.headers)
        return headers

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            proxy = self.proxy_manager.get_proxy()
            self._client = httpx.AsyncClient(
                proxy=proxy,
                cookies=self.config.cookies,
                timeout=httpx.Timeout(self.config.timeout),
                follow_redirects=self.config.follow_redirects,
                http2=False,  # default http/1.1 for broad compatibility
            )
        return self._client

    async def fetch(self, url: str) -> EngineResponse:
        """Fetch URL with rate limiting, header rotation, and exponential retry."""
        await self.rate_limiter.wait()

        async def _do_request() -> EngineResponse:
            client = await self._get_client()
            headers = self._get_headers()
            t0 = time.time()
            resp = await client.get(url, headers=headers)
            elapsed = time.time() - t0

            resp.raise_for_status()
            return EngineResponse(
                url=str(resp.url),
                status_code=resp.status_code,
                text=resp.text,
                headers=dict(resp.headers),
                elapsed=elapsed,
            )

        return await retry_with_backoff(
            _do_request,
            max_retries=self.config.max_retries,
        )

    async def close(self) -> None:
        """Close the HTTP client session."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
