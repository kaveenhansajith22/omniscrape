"""OmniScraper: Universal, reusable web scraping framework for any client and any website."""
from __future__ import annotations

from omniscrape.config.loader import ConfigLoader
from omniscrape.config.models import (
    DetailCrawlConfig,
    EngineType,
    ExportConfig,
    ExtractType,
    FieldConfig,
    ItemConfig,
    PaginationConfig,
    PaginationType,
    ScraperConfig,
)
from omniscrape.core.scraper import Scraper
from omniscrape.extractors.parser import HTMLParser
from omniscrape.extractors.transforms import TransformRegistry, apply_transforms

__all__ = [
    "Scraper",
    "ScraperConfig",
    "ConfigLoader",
    "ItemConfig",
    "FieldConfig",
    "PaginationConfig",
    "PaginationType",
    "DetailCrawlConfig",
    "ExportConfig",
    "ExtractType",
    "EngineType",
    "HTMLParser",
    "TransformRegistry",
    "apply_transforms",
]

__version__ = "1.0.0"
