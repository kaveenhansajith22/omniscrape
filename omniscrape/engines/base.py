"""Abstract base class and interface for scraping engines."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class EngineResponse:
    """Standardized response from any scraping engine."""
    url: str
    status_code: int
    text: str
    headers: dict[str, str]
    elapsed: float = 0.0


class BaseEngine(ABC):
    """Abstract interface for static and dynamic scraping engines."""

    @abstractmethod
    async def fetch(self, url: str) -> EngineResponse:
        """Fetch the given URL and return a standardized EngineResponse."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Clean up network resources, browsers, or client sessions."""
        pass

    async def __aenter__(self) -> BaseEngine:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()
