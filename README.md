# OmniScraper: Universal Reusable Web Scraping Framework

A production-ready, declarative, configuration-driven web scraping framework in Python engineered to be reused across **any client** and **any website** without rewriting scraping code.

---

## 🌟 Why OmniScraper?

Most scraping scripts are brittle, single-use, and hardcode website-specific CSS selectors into Python logic. When website structures change or a new client requests a different data schema, developers end up reinventing the wheel.

**OmniScraper** decouples scraping logic from site configuration:

1. **100% Declarative Profiles**: Define targets in readable YAML or JSON files. Hand off profile creation to clients or non-developers.
2. **Dual Scraping Engines**:
   - **Static Engine (`httpx`)**: Blazing-fast asynchronous HTTP engine with connection pooling and HTTP/2 support.
   - **Dynamic Engine (`playwright`)**: Headless browser automation for JavaScript-heavy single-page applications (React, Vue, Angular, infinite scroll).
3. **Multi-Tier Crawling (Detail Pages)**: Scrape a listing catalog, follow individual item links, and merge deep specifications (UPC, descriptions, specs) into a unified record.
4. **Resilient Data Cleaning & Casting**: Automatically cleans dirty text, parses prices (`"$1,299.99"` → `1299.99`), extracts numbers, decodes HTML entities, and resolves relative URLs into canonical URLs.
5. **Anti-Bot & Politeness Built-In**: Realistic User-Agent pool (Chrome, Safari, Firefox on macOS, Windows, Linux), proxy pool manager with error cooldowns, exponential backoff retries, and randomized jitter delays.
6. **Multi-Format Exporters**: One-click output to JSON, JSON Lines (`ndjson`), CSV, SQLite, and Markdown.
7. **Python SDK & Developer CLI**: Use as a command-line utility or import as an async Python library.

---

## 🏛️ Architecture Overview

```
                          ┌──────────────────────────┐
                          │   Declarative Profile    │
                          │   (YAML / JSON / Code)   │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │    Scraper Controller    │
                          └──────┬────────────┬──────┘
                                 │            │
                 ┌───────────────┴──┐      ┌──┴────────────────┐
                 ▼                  ▼      ▼                   ▼
         ┌───────────────┐  ┌──────────────┐  ┌─────────────┐  ┌─────────────┐
         │ Static Engine │  │Dynamic Engine│  │ Rate Limit  │  │ User-Agent  │
         │    (HTTPX)    │  │ (Playwright) │  │  & Backoff  │  │  & Proxies  │
         └───────┬───────┘  └──────┬───────┘  └─────────────┘  └─────────────┘
                 └───────────────┬──┘
                                 │ Raw HTML / DOM
                                 ▼
                    ┌──────────────────────────┐
                    │ HTML Parser & Extractors │
                    │ (CSS, XPath, JSON-LD)    │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Transformation Pipeline  │
                    │ (strip, to_float, etc.)  │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ Deduplication Filter     │
                    └────────────┬─────────────┘
                                 │
                                 ▼
        ┌─────────────────────────────────────────────────────────┐
        │                        Exporters                        │
        │    [JSON]       [JSONL]       [CSV]   [SQLite]   [MD]   │
        └─────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### 1. Installation

Create a virtual environment and install dependencies:

```bash
cd omniscrape
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Or install in editable mode:
pip install -e .
```

To enable dynamic browser rendering for JavaScript-heavy websites:
```bash
pip install playwright
playwright install chromium
```

---

## 💻 CLI Commands

### 1. Test a Config on a Single Page (`test`)
Test your selectors against page 1 without crawling the entire website:

```bash
python -m omniscrape test examples/quotes_scraper.yaml --limit 3
```

### 2. Run a Full Scrape Job (`run`)
Crawl target websites across pages and export to the desired destination:

```bash
# Run with export defined in YAML
python -m omniscrape run examples/quotes_scraper.yaml

# Override output destination and format on the fly
python -m omniscrape run examples/quotes_scraper.yaml -o results.csv --format csv --limit 50
```

### 3. Inspect Any Webpage Live (`inspect`)
Test CSS selectors, view page metadata, or check for Schema.org JSON-LD microdata before writing your config:

```bash
# Test CSS selectors on a live website
python -m omniscrape inspect "https://quotes.toscrape.com/" -s "div.quote span.text"

# View OpenGraph and meta tags
python -m omniscrape inspect "https://quotes.toscrape.com/" --meta

# View Schema.org JSON-LD structured data
python -m omniscrape inspect "https://example.com/product" --json-ld
```

### 4. Initialize a New Scraper Profile (`init`)
Generate a starter configuration profile:

```bash
python -m omniscrape init client_scraper
# Creates client_scraper.yaml
```

---

## 📝 Declarative Profile Specification

A profile is a single YAML or JSON file containing everything OmniScraper needs to crawl a website:

```yaml
name: "ecommerce_crawler"
description: "Scrapes product catalog with detail specifications"

# Target entry URLs (supports ${ENV_VAR} interpolation)
start_urls:
  - "https://books.toscrape.com/catalogue/page-1.html"

# Engine: "static" (HTTPX) or "dynamic" (Playwright headless browser)
engine: "static"

# Anti-bot and politeness settings
user_agent_mode: "desktop"   # desktop, mobile, or any
rotate_user_agent: true
min_delay: 0.5               # minimum seconds between requests
max_delay: 1.5               # maximum seconds with random jitter
timeout: 30.0
max_retries: 3
proxies: []                  # optional list of proxy URLs (http/socks5)

# Primary item extraction rules
item:
  container_selector: "article.product_pod" # Repeats for each product card
  fields:
    title:
      selector: "h3 > a"
      extract: "attr"
      attribute: "title"
      transforms: ["strip"]
      required: true
    price:
      selector: "p.price_color"
      extract: "text"
      transforms: ["to_float"] # Converts "£51.77" -> 51.77
    product_link:
      selector: "h3 > a"
      extract: "attr"
      attribute: "href"
      transforms: ["resolve_url"] # Converts relative "../item.html" to absolute URL

# Multi-Tier Crawling: Follow product_link to detail page and merge deep fields
detail_crawl:
  url_field: "product_link"
  fields:
    upc:
      selector: "table tr:nth-of-type(1) td"
      extract: "text"
      transforms: ["strip"]
    description:
      selector: "#product_description + p"
      extract: "text"
      transforms: ["strip"]

# Multi-page pagination
pagination:
  type: "next_button"        # "next_button", "url_pattern", "scroll", or "none"
  selector: "li.next > a"
  max_pages: 5

# Deduplication
deduplicate_by:
  - "product_link"

# Export settings: "json", "jsonl", "csv", "sqlite", "markdown"
export:
  format: "json"
  filepath: "output/books.json"
```

---

## 🛠️ Field Extraction & Transforms

### Extraction Types (`extract`)
| Type | Description |
| :--- | :--- |
| `text` | Plain text of element (`get_text()`) |
| `attr` | Value of an HTML attribute (specify `attribute: "href"` / `"src"` / `"data-id"`) |
| `inner_html` | Inner HTML contents |
| `outer_html` | Outer HTML including the wrapping tag |
| `regex` | Extract value matching regex pattern |
| `count` | Total count of elements matching the selector |

### Built-in Transforms (`transforms`)
Chain transforms in order:
- `strip`: Remove extra whitespace and newlines.
- `lowercase` / `uppercase`: String casing.
- `html_unescape`: Decode entities like `&amp;` → `&`, `&#39;` → `'`.
- `to_int`: Extracts clean integer (`"Stock: 42 left"` → `42`).
- `to_float`: Extracts clean float or price (`"$1,299.99"` → `1299.99`).
- `resolve_url`: Converts relative path to absolute URL using the page base URL.
- `join:<delimiter>`: Joins list of values with delimiter (e.g. `join:, `).
- `split:<delimiter>`: Splits string into a list.
- `first`: Extracts first element from a list.
- `regex_search:<pattern>`: Extracts regex capture group.
- `regex_replace:<pattern>:<replacement>`: Replaces text matching pattern.
- `default:<value>`: Fallback value if field is missing or empty.

---

## 🐍 Python SDK Programmatic Usage

You can also use OmniScraper directly from Python:

```python
import asyncio
from omniscrape import Scraper, ScraperConfig, TransformRegistry

# 1. (Optional) Register custom transformation functions
@TransformRegistry.register("clean_sku")
def clean_sku(value, **kwargs):
    return str(value).replace("SKU-", "").strip().upper()

# 2. Load configuration from file or dict
config = ScraperConfig.from_file("my_scraper.yaml")

# 3. Stream items in real time
async def run():
    scraper = Scraper(config)
    async for item in scraper.astream():
        print(f"Scraped: {item['title']} - {item['price']}")

asyncio.run(run())
```

---

## 🧪 Testing

OmniScraper includes a comprehensive test suite covering parsers, transforms, config loaders, exporters, and the crawler orchestrator:

```bash
pytest -v
```

All 14 unit and integration tests pass out of the box.
## Screenshots

### FastAPI Backend — API Documentation
Shows the interactive API documentation used to test OmniScraper endpoints.

![OmniScraper API Documentation](screenshots/Screenshot 2026-10-14 at 20.26.02.png)

### React Frontend — Main Interface
Shows the user interface for interacting with OmniScraper.

![OmniScraper Frontend](screenshots/Screenshot 2026-10-14 at 20.27.14.png)

### React Frontend — Scraping Results
Shows the frontend displaying the results of a scraping request.

![OmniScraper Results](screenshots/Screenshot 2026-10-14 at 20.27.29.png)