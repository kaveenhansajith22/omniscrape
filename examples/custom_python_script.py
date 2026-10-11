"""Programmatic Python API usage example for OmniScraper."""
import asyncio
from omniscrape import (
    Scraper,
    ScraperConfig,
    ItemConfig,
    FieldConfig,
    ExtractType,
    PaginationConfig,
    PaginationType,
    TransformRegistry,
    ExportConfig,
)

# 1. Register a custom data cleaner/transform
@TransformRegistry.register("sentiment_label")
def custom_sentiment(value: str, **kwargs) -> str:
    """Example custom transformer adding business logic."""
    if not isinstance(value, str):
        return "neutral"
    lower = value.lower()
    if any(w in lower for w in ["love", "great", "inspire", "truth", "good"]):
        return "positive"
    return "reflective"


# 2. Build configuration programmatically
config = ScraperConfig(
    name="programmatic_quotes",
    start_urls=["https://quotes.toscrape.com/"],
    min_delay=0.2,
    max_delay=0.6,
    item=ItemConfig(
        container_selector="div.quote",
        fields={
            "quote": FieldConfig(
                selector="span.text",
                extract=ExtractType.TEXT,
                transforms=["strip", "html_unescape"],
                required=True,
            ),
            "sentiment": FieldConfig(
                selector="span.text",
                extract=ExtractType.TEXT,
                transforms=["sentiment_label"],
            ),
            "author": FieldConfig(
                selector="small.author",
                extract=ExtractType.TEXT,
                transforms=["strip"],
            ),
            "tags": FieldConfig(
                selector="a.tag",
                extract=ExtractType.TEXT,
                multiple=True,
                transforms=["strip"],
            ),
        },
    ),
    pagination=PaginationConfig(
        type=PaginationType.NEXT_BUTTON,
        selector="li.next > a",
        max_pages=2,
    ),
    deduplicate_by=["quote"],
    export=ExportConfig(
        filepath="output/programmatic_quotes.json",
        format="json",
    ),
)


async def main():
    print(f"Starting programmatic scraper: {config.name}")
    scraper = Scraper(config)

    # Stream results in real-time as they arrive
    count = 0
    async for item in scraper.astream():
        count += 1
        print(f"[{count}] {item['author']}: {item['quote'][:40]}... (Sentiment: {item['sentiment']})")

    print("\n--- Summary Stats ---")
    print(f"Total Items: {scraper.stats['items_scraped']}")
    print(f"Pages Crawled: {scraper.stats['pages_crawled']}")


if __name__ == "__main__":
    asyncio.run(main())
