"""Pydantic data models for declarative scraping configurations."""
from __future__ import annotations

from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator


class ExtractType(str, Enum):
    TEXT = "text"
    INNER_HTML = "inner_html"
    OUTER_HTML = "outer_html"
    ATTR = "attr"
    REGEX = "regex"
    COUNT = "count"


class EngineType(str, Enum):
    STATIC = "static"
    DYNAMIC = "dynamic"


class PaginationType(str, Enum):
    NONE = "none"
    NEXT_BUTTON = "next_button"
    URL_PATTERN = "url_pattern"
    SCROLL = "scroll"


class FieldConfig(BaseModel):
    """Configuration for extracting a single field from HTML elements."""
    selector: str | None = Field(default=None, description="CSS selector")
    xpath: str | None = Field(default=None, description="XPath selector")
    extract: ExtractType = Field(default=ExtractType.TEXT, description="What to extract from the element")
    attribute: str | None = Field(default=None, description="HTML attribute to extract when extract='attr' (e.g., href, src)")
    regex: str | None = Field(default=None, description="Regex pattern or capture group")
    multiple: bool = Field(default=False, description="Extract all matching elements as a list instead of just the first")
    default: Any = Field(default=None, description="Default value if element not found")
    transforms: list[str] = Field(
        default_factory=list,
        description="List of transform functions to apply (e.g. ['strip', 'to_float', 'resolve_url'])"
    )
    required: bool = Field(default=False, description="Whether this field must be present and non-empty")


class ItemConfig(BaseModel):
    """Configuration for item-level extraction."""
    container_selector: str | None = Field(
        default=None,
        description="CSS selector for list of items. If None, extracts a single item from the page."
    )
    container_xpath: str | None = Field(default=None, description="XPath selector for item container")
    fields: dict[str, FieldConfig] = Field(default_factory=dict, description="Field extractors for the item")


class PaginationConfig(BaseModel):
    """Configuration for multi-page crawling."""
    type: PaginationType = Field(default=PaginationType.NONE, description="Pagination strategy")
    selector: str | None = Field(default=None, description="CSS selector for next page link/button")
    xpath: str | None = Field(default=None, description="XPath for next page link")
    url_pattern: str | None = Field(default=None, description="Template URL with {page} placeholder")
    start_page: int = Field(default=1, description="Starting page number for url_pattern pagination")
    max_pages: int | None = Field(default=None, description="Maximum number of pages to scrape (None = unlimited)")
    stop_condition_selector: str | None = Field(
        default=None,
        description="CSS selector indicating end of results (e.g. 'div.no-results')"
    )


class DetailCrawlConfig(BaseModel):
    """Configuration for following links to scrape child/detail pages and merging into the parent item."""
    url_field: str = Field(description="Name of the field in parent item containing the detail URL")
    fields: dict[str, FieldConfig] = Field(description="Field extractors to run on the detail page")
    max_concurrency: int = Field(default=3, description="Concurrency limit for detail page fetching")


class ExportConfig(BaseModel):
    """Configuration for persisting scraped results."""
    format: Literal["json", "jsonl", "csv", "sqlite", "markdown"] = Field(default="json")
    filepath: str = Field(description="Target output file path")
    table_name: str = Field(default="scraped_data", description="Table name for SQLite export")


class ScraperConfig(BaseModel):
    """Complete declarative configuration for a scraping task."""
    name: str = Field(description="Unique identifier or friendly name for the scraper")
    description: str | None = Field(default=None, description="Scraper description or notes")
    start_urls: list[str] = Field(description="Initial URL or list of URLs to crawl")
    engine: EngineType = Field(default=EngineType.STATIC, description="Scraping engine: static (HTTPX) or dynamic (Playwright)")
    item: ItemConfig = Field(default_factory=ItemConfig, description="Item extraction rules")
    pagination: PaginationConfig | None = Field(default=None, description="Pagination configuration")
    detail_crawl: DetailCrawlConfig | None = Field(default=None, description="Secondary detail-page crawling rules")
    
    # HTTP & Anti-bot settings
    headers: dict[str, str] = Field(default_factory=dict, description="Custom HTTP headers")
    cookies: dict[str, str] = Field(default_factory=dict, description="Custom cookies")
    user_agent_mode: Literal["desktop", "mobile", "any"] = Field(default="desktop")
    rotate_user_agent: bool = Field(default=True, description="Rotate User-Agent across requests")
    proxies: list[str] = Field(default_factory=list, description="List of proxy URLs")
    
    # Politeness & Network settings
    min_delay: float = Field(default=0.5, description="Minimum polite delay between requests (seconds)")
    max_delay: float = Field(default=1.5, description="Maximum polite delay with random jitter (seconds)")
    timeout: float = Field(default=30.0, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retries for network/rate-limit errors")
    follow_redirects: bool = Field(default=True, description="Follow HTTP redirects")
    
    # Post-processing & Features
    deduplicate_by: list[str] | None = Field(
        default=None,
        description="Field names used to deduplicate items. If None, deduplication is disabled."
    )
    auto_extract_json_ld: bool = Field(
        default=False,
        description="Automatically parse schema.org JSON-LD microdata if present"
    )
    export: ExportConfig | None = Field(default=None, description="Output export specification")

    @field_validator("start_urls", mode="before")
    @classmethod
    def ensure_start_urls_list(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [v]
        return list(v)
