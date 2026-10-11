"""Core scraper orchestrator managing URLs, engines, pagination, detail crawls, and pipelines."""
from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncGenerator, Generator
from urllib.parse import urljoin

from omniscrape.config.models import (
    EngineType,
    PaginationType,
    ScraperConfig,
)
from omniscrape.engines.base import BaseEngine
from omniscrape.engines.dynamic import DynamicEngine
from omniscrape.engines.static import StaticEngine
from omniscrape.extractors.parser import HTMLParser
from omniscrape.pipelines.deduplication import ItemDeduplicator
from omniscrape.pipelines.exporters import export_data

logger = logging.getLogger("omniscrape.scraper")


class Scraper:
    """Universal configurable web scraper orchestrator."""

    def __init__(self, config: ScraperConfig):
        self.config = config
        self.deduplicator = ItemDeduplicator(key_fields=config.deduplicate_by)
        self.stats: dict[str, Any] = {
            "pages_crawled": 0,
            "items_scraped": 0,
            "duplicates_dropped": 0,
            "errors": 0,
        }

    def _create_engine(self) -> BaseEngine:
        """Instantiate the configured scraping engine."""
        if self.config.engine == EngineType.DYNAMIC:
            return DynamicEngine(self.config)
        return StaticEngine(self.config)

    async def _fetch_and_parse(self, engine: BaseEngine, url: str) -> tuple[HTMLParser, str]:
        """Fetch page via engine and return initialized parser and resolved final URL."""
        response = await engine.fetch(url)
        self.stats["pages_crawled"] += 1
        parser = HTMLParser(response.text, base_url=response.url)
        return parser, response.url

    async def _crawl_details(
        self,
        engine: BaseEngine,
        item: dict[str, Any],
        base_url: str,
    ) -> dict[str, Any]:
        """Fetch detail page if detail_crawl is configured and merge fields into parent item."""
        if not self.config.detail_crawl:
            return item

        detail_cfg = self.config.detail_crawl
        target_url = item.get(detail_cfg.url_field)
        if not target_url or not isinstance(target_url, str):
            return item

        resolved_detail_url = urljoin(base_url, target_url)
        try:
            detail_parser, _ = await self._fetch_and_parse(engine, resolved_detail_url)
            for field_name, field_cfg in detail_cfg.fields.items():
                val = detail_parser.extract_field(field_cfg)
                item[field_name] = val
        except Exception as e:
            logger.warning(f"Failed to crawl detail page {resolved_detail_url}: {e}")
            self.stats["errors"] += 1

        return item

    async def astream(self) -> AsyncGenerator[dict[str, Any], None]:
        """Asynchronously stream scraped items one by one as they are discovered."""
        engine = self._create_engine()
        try:
            for start_url in self.config.start_urls:
                current_url: str | None = start_url
                page_count = 0

                while current_url:
                    page_count += 1
                    logger.info(f"Crawling [page {page_count}]: {current_url}")

                    try:
                        parser, resolved_url = await self._fetch_and_parse(engine, current_url)
                    except Exception as e:
                        logger.error(f"Error fetching {current_url}: {e}")
                        self.stats["errors"] += 1
                        break

                    # Extract primary items
                    page_items = parser.extract_items(self.config.item)

                    # Auto-extract JSON-LD if enabled
                    if self.config.auto_extract_json_ld:
                        json_ld = parser.extract_json_ld()
                        if json_ld:
                            for pi in page_items:
                                pi["_json_ld"] = json_ld

                    for raw_item in page_items:
                        # Process detail crawl if defined
                        if self.config.detail_crawl:
                            item = await self._crawl_details(engine, raw_item, resolved_url)
                        else:
                            item = raw_item

                        # Deduplicate
                        if self.config.deduplicate_by is not None:
                            if self.deduplicator.is_duplicate(item):
                                self.stats["duplicates_dropped"] = self.deduplicator.duplicates_dropped
                                continue

                        self.stats["items_scraped"] += 1
                        yield item

                    # Determine next page URL
                    next_url: str | None = None
                    pagination = self.config.pagination

                    if pagination and pagination.type != PaginationType.NONE:
                        # Check stop condition
                        if pagination.stop_condition_selector:
                            if parser.soup.select_one(pagination.stop_condition_selector):
                                logger.info("Pagination stop condition selector encountered.")
                                break

                        # Check max pages
                        if pagination.max_pages and page_count >= pagination.max_pages:
                            logger.info(f"Reached max pages limit ({pagination.max_pages}).")
                            break

                        if pagination.type == PaginationType.NEXT_BUTTON:
                            if pagination.selector:
                                next_el = parser.soup.select_one(pagination.selector)
                                if next_el and next_el.get("href"):
                                    href = str(next_el.get("href"))
                                    next_url = urljoin(resolved_url, href)
                            elif pagination.xpath and parser.lxml_tree is not None:
                                nodes = parser.lxml_tree.xpath(pagination.xpath)
                                if nodes:
                                    href = nodes[0].get("href") if hasattr(nodes[0], "get") else str(nodes[0])
                                    if href:
                                        next_url = urljoin(resolved_url, href)

                        elif pagination.type == PaginationType.URL_PATTERN and pagination.url_pattern:
                            next_page_num = pagination.start_page + page_count
                            next_url = pagination.url_pattern.format(page=next_page_num)

                    current_url = next_url

        finally:
            await engine.close()

    def stream(self) -> Generator[dict[str, Any], None, None]:
        """Synchronous generator wrapper for astream()."""
        loop = asyncio.new_event_loop()
        async_gen = self.astream()
        try:
            while True:
                try:
                    yield loop.run_until_complete(async_gen.__anext__())
                except StopAsyncIteration:
                    break
        finally:
            try:
                loop.run_until_complete(async_gen.aclose())
            except Exception:
                pass
            loop.close()

    async def arun(self) -> list[dict[str, Any]]:
        """Run scraping task asynchronously and return all extracted records."""
        results: list[dict[str, Any]] = []
        async for item in self.astream():
            results.append(item)

        if self.config.export:
            export_data(results, self.config.export)

        return results

    def run(self) -> list[dict[str, Any]]:
        """Run scraping task synchronously and return all extracted records."""
        return asyncio.run(self.arun())
