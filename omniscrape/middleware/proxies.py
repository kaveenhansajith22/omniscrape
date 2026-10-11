"""Proxy management middleware with rotation and health tracking."""
from __future__ import annotations

import itertools
import random
import time
from typing import Literal


class ProxyManager:
    """Manages a pool of HTTP/HTTPS/SOCKS5 proxies with rotation and error cooldowns."""

    def __init__(
        self,
        proxies: list[str] | None = None,
        strategy: Literal["round_robin", "random"] = "round_robin",
        cooldown_seconds: float = 60.0,
    ):
        self.raw_proxies = proxies or []
        self.strategy = strategy
        self.cooldown_seconds = cooldown_seconds
        self._dead_proxies: dict[str, float] = {}  # proxy -> failure timestamp
        self._cycle = itertools.cycle(self.raw_proxies) if self.raw_proxies else None

    @property
    def has_proxies(self) -> bool:
        return len(self.raw_proxies) > 0

    def get_proxy(self) -> str | None:
        """Get the next healthy proxy from the pool."""
        if not self.raw_proxies:
            return None

        now = time.time()
        # Clean up cooled down proxies
        self._dead_proxies = {
            p: ts for p, ts in self._dead_proxies.items()
            if now - ts < self.cooldown_seconds
        }

        active = [p for p in self.raw_proxies if p not in self._dead_proxies]
        if not active:
            # If all are marked dead, reset and retry any to avoid complete starvation
            active = self.raw_proxies
            self._dead_proxies.clear()

        if self.strategy == "random":
            return random.choice(active)

        # Round robin
        for _ in range(len(self.raw_proxies)):
            p = next(self._cycle)
            if p in active:
                return p
        return active[0]

    def mark_failed(self, proxy: str | None) -> None:
        """Mark a proxy as failed to put it in cooldown."""
        if proxy and proxy in self.raw_proxies:
            self._dead_proxies[proxy] = time.time()
