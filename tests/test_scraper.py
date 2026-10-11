import pytest
from omniscrape.config.models import (
    ScraperConfig,
    ItemConfig,
    FieldConfig,
    ExtractType,
    PaginationConfig,
    PaginationType,
)
from omniscrape.core.scraper import Scraper
from omniscrape.engines.base import BaseEngine, EngineResponse


PAGE_1 = """
<html>
<body>
    <div class="item"><h2 class="title">Product 1</h2><a class="next" href="/page2">Next</a></div>
    <div class="item"><h2 class="title">Product 2</h2></div>
</body>
</html>
"""

PAGE_2 = """
<html>
<body>
    <div class="item"><h2 class="title">Product 3</h2></div>
</body>
</html>
"""


class MockEngine(BaseEngine):
    def __init__(self, *args, **kwargs):
        self.pages = {
            "https://mocksite.local/": PAGE_1,
            "https://mocksite.local/page2": PAGE_2,
        }

    async def fetch(self, url: str) -> EngineResponse:
        html_content = self.pages.get(url, "<html></html>")
        return EngineResponse(url=url, status_code=200, text=html_content, headers={})

    async def close(self) -> None:
        pass


@pytest.mark.asyncio
async def test_scraper_orchestrator(monkeypatch):
    config = ScraperConfig(
        name="test_orchestrator",
        start_urls=["https://mocksite.local/"],
        min_delay=0,
        max_delay=0,
        item=ItemConfig(
            container_selector="div.item",
            fields={
                "title": FieldConfig(selector="h2.title", extract=ExtractType.TEXT)
            }
        ),
        pagination=PaginationConfig(
            type=PaginationType.NEXT_BUTTON,
            selector="a.next",
            max_pages=2,
        ),
    )

    scraper = Scraper(config)
    monkeypatch.setattr(scraper, "_create_engine", lambda: MockEngine())

    results = await scraper.arun()
    assert len(results) == 3
    assert results[0]["title"] == "Product 1"
    assert results[1]["title"] == "Product 2"
    assert results[2]["title"] == "Product 3"
    assert scraper.stats["pages_crawled"] == 2
