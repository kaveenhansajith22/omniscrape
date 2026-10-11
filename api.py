"""FastAPI backend for the OmniScrape web application."""

from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from omniscrape.config.loader import ConfigLoader
from omniscrape.core.scraper import Scraper


BASE_DIR = Path(__file__).resolve().parent
BOOKS_CONFIG = BASE_DIR / "examples" / "books_detail_crawler.yaml"

app = FastAPI(
    title="OmniScrape API",
    description="API connecting the OmniScrape engine to its React frontend.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ScrapeRequest(BaseModel):
    url: str = Field(
        default="https://books.toscrape.com/catalogue/page-1.html",
        description="URL to scrape on the supported books test website.",
    )
    max_pages: int = Field(default=1, ge=1, le=5)


@app.get("/api/health")
async def health_check():
    """Check whether the API is running."""
    return {"status": "ok", "service": "OmniScrape API"}


@app.post("/api/scrape")
async def scrape_website(request: ScrapeRequest):
    """Run the existing books scraper and return its results."""

    parsed_url = urlparse(request.url)

    if parsed_url.scheme != "https":
        raise HTTPException(
            status_code=400,
            detail="The URL must use HTTPS.",
        )



    if parsed_url.username or parsed_url.password:
        raise HTTPException(
            status_code=400,
            detail="URLs containing usernames or passwords are not allowed.",
        )

    if not BOOKS_CONFIG.is_file():
        raise HTTPException(
            status_code=500,
            detail="The books scraper configuration file was not found.",
        )

    try:
        config = ConfigLoader.from_file(BOOKS_CONFIG)

        config.start_urls = [request.url]

        if config.pagination:
            config.pagination.max_pages = request.max_pages

        # The browser will receive the results directly from the API.
        # Disable file export for this first integration.
        config.export = None

        scraper = Scraper(config)
        items = await scraper.arun()

        return {
            "status": "success",
            "url": request.url,
            "items_count": len(items),
            "pages_crawled": scraper.stats["pages_crawled"],
            "duplicates_dropped": scraper.stats["duplicates_dropped"],
            "errors": scraper.stats["errors"],
            "items": items,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Scraping failed: {str(exc)}",
        ) from exc
