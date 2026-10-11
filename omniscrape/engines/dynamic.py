"""Headless browser dynamic engine powered by Playwright for JavaScript-rendered sites."""
from __future__ import annotations

import logging
import time
from typing import Any

from omniscrape.config.models import ScraperConfig
from omniscrape.engines.base import BaseEngine, EngineResponse
from omniscrape.middleware.proxies import ProxyManager
from omniscrape.middleware.rate_limiter import RateLimiter
from omniscrape.middleware.user_agents import UserAgentRotator

logger = logging.getLogger("omniscrape.engine.dynamic")


class DynamicEngine(BaseEngine):
    """Dynamic headless browser engine using Playwright for SPAs and JavaScript-heavy websites."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.rate_limiter = RateLimiter(min_delay=config.min_delay, max_delay=config.max_delay)
        self.ua_rotator = UserAgentRotator(mode=config.user_agent_mode)
        self.proxy_manager = ProxyManager(proxies=config.proxies)

        self._playwright: Any = None
        self._browser: Any = None
        self._context: Any = None

    def _ensure_playwright_installed(self) -> None:
        try:
            import playwright  # noqa: F401
        except ImportError:
            raise ImportError(
                "Playwright is required for the dynamic engine. "
                "Install it with:\n"
                "  pip install playwright\n"
                "  playwright install chromium"
            )

    async def _init_browser(self) -> None:
        self._ensure_playwright_installed()
        from playwright.async_api import async_playwright

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        proxy_url = self.proxy_manager.get_proxy()
        proxy_dict = {"server": proxy_url} if proxy_url else None

        if self._browser is None:
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                proxy=proxy_dict,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )

        ua = self.ua_rotator.get_user_agent() if self.config.rotate_user_agent else None
        self._context = await self._browser.new_context(
            user_agent=ua,
            viewport={"width": 1440, "height": 900},
            extra_http_headers=self.config.headers or {}
        )

        if self.config.cookies:
            cookies_to_add = [
                {"name": k, "value": v, "url": self.config.start_urls[0]}
                for k, v in self.config.cookies.items()
            ]
            await self._context.add_cookies(cookies_to_add)

    async def fetch(self, url: str) -> EngineResponse:
        """Load URL in headless browser, wait for DOM content, and return rendered HTML."""
        await self.rate_limiter.wait()

        if self._context is None:
            await self._init_browser()

        page = await self._context.new_page()
        try:
            t0 = time.time()
            resp = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=int(self.config.timeout * 1000)
            )

            # Handle optional wait for item container
            if self.config.item.container_selector:
                try:
                    await page.wait_for_selector(
                        self.config.item.container_selector,
                        timeout=5000
                    )
                except Exception:
                    logger.debug("Container selector not immediately present; proceeding.")

            # Handle scroll pagination if requested
            if self.config.pagination and self.config.pagination.type.value == "scroll":
                await self._perform_scroll(page)

            html_content = await page.content()
            elapsed = time.time() - t0
            status_code = resp.status if resp else 200

            return EngineResponse(
                url=page.url,
                status_code=status_code,
                text=html_content,
                headers=dict(resp.headers) if resp else {},
                elapsed=elapsed
            )
        finally:
            await page.close()

    async def _perform_scroll(self, page: Any, scrolls: int = 3, delay: float = 1.0) -> None:
        """Scroll down to trigger dynamic loading / infinite scroll."""
        for _ in range(scrolls):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(int(delay * 1000))

    async def close(self) -> None:
        """Close browser context and playwright instance."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
