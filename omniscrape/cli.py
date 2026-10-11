"""Command-line interface for OmniScraper: run, test, inspect, and init."""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from omniscrape.config.loader import ConfigLoader
from omniscrape.config.models import ExportConfig
from omniscrape.core.scraper import Scraper
from omniscrape.engines.static import StaticEngine
from omniscrape.extractors.parser import HTMLParser
from omniscrape.pipelines.exporters import export_data

console = Console()


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def cmd_run(args: argparse.Namespace) -> None:
    """Execute a full scraping task using a configuration file."""
    setup_logging(args.verbose)
    try:
        config = ConfigLoader.from_file(args.config)
    except Exception as e:
        console.print(f"[bold red]Error loading config:[/] {e}")
        sys.exit(1)

    # CLI override for output file
    if args.output:
        fmt = args.format or Path(args.output).suffix.lstrip(".").lower() or "json"
        config.export = ExportConfig(filepath=args.output, format=fmt)

    console.print(Panel(
        f"[bold cyan]Scraper:[/] {config.name}\n"
        f"[bold cyan]Start URLs:[/] {', '.join(config.start_urls)}\n"
        f"[bold cyan]Engine:[/] {config.engine.value}\n"
        f"[bold cyan]Output:[/] {config.export.filepath if config.export else 'Console only'}",
        title="[bold green]OmniScraper Run[/]",
        expand=False,
    ))

    scraper = Scraper(config)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task("[cyan]Scraping data...", total=None)
        items: list[dict[str, Any]] = []

        for item in scraper.stream():
            items.append(item)
            progress.update(task, description=f"[cyan]Scraped {len(items)} items from {scraper.stats['pages_crawled']} pages...")
            if args.limit and len(items) >= args.limit:
                break

    if config.export and items:
        export_data(items, config.export)

    # Summary table
    table = Table(title="Scraping Execution Summary", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Total Items Scraped", str(len(items)))
    table.add_row("Pages Crawled", str(scraper.stats["pages_crawled"]))
    table.add_row("Duplicates Dropped", str(scraper.stats["duplicates_dropped"]))
    table.add_row("Errors Encountered", str(scraper.stats["errors"]))
    if config.export:
        table.add_row("Export Destination", str(config.export.filepath))

    console.print(table)

    if not config.export and items:
        console.print(Panel(
            json.dumps(items[:5], indent=2, ensure_ascii=False, default=str),
            title="Sample Results (first 5 records)",
        ))


def cmd_test(args: argparse.Namespace) -> None:
    """Test a scraper configuration against the first page and display sample records."""
    setup_logging(args.verbose)
    try:
        config = ConfigLoader.from_file(args.config)
    except Exception as e:
        console.print(f"[bold red]Error loading config:[/] {e}")
        sys.exit(1)

    # Force single page limit
    if config.pagination:
        config.pagination.max_pages = 1
    config.export = None

    console.print(f"[bold yellow]Testing configuration on first page:[/] {config.start_urls[0]}")
    scraper = Scraper(config)
    items: list[dict[str, Any]] = []

    for item in scraper.stream():
        items.append(item)
        if len(items) >= (args.limit or 3):
            break

    if not items:
        console.print("[bold red]No items extracted![/] Please check container_selector or field rules.")
        sys.exit(1)

    console.print(f"[bold green]Successfully extracted {len(items)} test items:[/]")
    for i, it in enumerate(items, 1):
        console.print(Panel(json.dumps(it, indent=2, default=str), title=f"Item #{i}"))


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect a live webpage to discover selectors, JSON-LD, or meta tags."""
    async def _inspect() -> None:
        from omniscrape.config.models import ScraperConfig, ItemConfig
        dummy_cfg = ScraperConfig(
            name="inspector",
            start_urls=[args.url],
            item=ItemConfig(),
        )
        engine = StaticEngine(dummy_cfg)
        try:
            with console.status(f"[cyan]Fetching {args.url}...[/]"):
                resp = await engine.fetch(args.url)
            parser = HTMLParser(resp.text, base_url=resp.url)

            console.print(f"[bold green]HTTP {resp.status_code}[/] from [underline]{resp.url}[/]\n")

            if args.meta:
                meta = parser.extract_meta_tags()
                table = Table(title="Meta Tags", show_header=True)
                table.add_column("Tag Name/Property", style="cyan")
                table.add_column("Content", style="white")
                for k, v in list(meta.items())[:20]:
                    table.add_row(k, v)
                console.print(table)

            if args.json_ld:
                json_ld = parser.extract_json_ld()
                console.print(Panel(
                    json.dumps(json_ld, indent=2, default=str),
                    title=f"Schema.org JSON-LD ({len(json_ld)} blocks found)",
                ))

            if args.selector:
                matched = parser.soup.select(args.selector)
                console.print(f"[bold cyan]Selector '{args.selector}' matched {len(matched)} elements:[/]")
                for i, el in enumerate(matched[:10], 1):
                    preview = el.get_text(strip=True)[:100]
                    console.print(f"  [green]{i}.[/] <{el.name}> [dim]class={el.get('class')}[/] -> [white]{preview}[/]")
                if len(matched) > 10:
                    console.print(f"  [dim]... and {len(matched) - 10} more elements[/]")
        finally:
            await engine.close()

    asyncio.run(_inspect())


def cmd_init(args: argparse.Namespace) -> None:
    """Generate a starter YAML template for a new scraper profile."""
    name = args.name or "my_scraper"
    target_path = Path(f"{name}.yaml")
    if target_path.exists():
        console.print(f"[bold red]File {target_path} already exists![/]")
        return

    sample_template = f"""# OmniScraper Profile: {name}
name: "{name}"
description: "Reusable scraper configuration for client website"
start_urls:
  - "https://quotes.toscrape.com/"

# Engine: static (fast HTTPX) or dynamic (Playwright headless browser)
engine: "static"

# Anti-blocking & politeness settings
user_agent_mode: "desktop"
rotate_user_agent: true
min_delay: 0.5
max_delay: 1.5
timeout: 30.0
max_retries: 3

# Data extraction rules
item:
  container_selector: "div.quote"
  fields:
    quote:
      selector: "span.text"
      extract: "text"
      transforms: ["strip", "html_unescape"]
      required: true
    author:
      selector: "small.author"
      extract: "text"
      transforms: ["strip"]
    tags:
      selector: "a.tag"
      extract: "text"
      multiple: true
      transforms: ["strip"]

# Multi-page pagination
pagination:
  type: "next_button"
  selector: "li.next > a"
  max_pages: 5

# Export settings (optional: json, jsonl, csv, sqlite, markdown)
export:
  format: "json"
  filepath: "output/{name}.json"
"""
    target_path.write_text(sample_template, encoding="utf-8")
    console.print(f"[bold green]Created starter configuration file:[/] {target_path.resolve()}")
    console.print("You can test it immediately by running:")
    console.print(f"  [cyan]python -m omniscrape test {target_path}[/]")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="omniscrape",
        description="OmniScraper: Universal, reusable web scraping toolkit for any client and any website.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # run command
    p_run = subparsers.add_parser("run", help="Run a scraper profile to completion")
    p_run.add_argument("config", help="Path to YAML or JSON config file")
    p_run.add_argument("-o", "--output", help="Override output file path")
    p_run.add_argument("-f", "--format", choices=["json", "jsonl", "csv", "sqlite", "markdown"], help="Output format")
    p_run.add_argument("--limit", type=int, help="Limit maximum total items scraped")
    p_run.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    p_run.set_defaults(func=cmd_run)

    # test command
    p_test = subparsers.add_parser("test", help="Test a config against 1 page and preview records")
    p_test.add_argument("config", help="Path to config file")
    p_test.add_argument("--limit", type=int, default=3, help="Number of preview records to show")
    p_test.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging")
    p_test.set_defaults(func=cmd_test)

    # inspect command
    p_inspect = subparsers.add_parser("inspect", help="Inspect a live URL to discover selectors, meta, or JSON-LD")
    p_inspect.add_argument("url", help="Target URL to inspect")
    p_inspect.add_argument("-s", "--selector", help="Test a CSS selector on the target page")
    p_inspect.add_argument("--meta", action="store_true", help="Display meta tags")
    p_inspect.add_argument("--json-ld", action="store_true", help="Display JSON-LD structured data")
    p_inspect.set_defaults(func=cmd_inspect)

    # init command
    p_init = subparsers.add_parser("init", help="Generate a starter configuration YAML file")
    p_init.add_argument("name", nargs="?", default="my_scraper", help="Scraper profile name")
    p_init.set_defaults(func=cmd_init)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
