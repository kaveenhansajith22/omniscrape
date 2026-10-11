"""Data exporters for JSON, JSON Lines, CSV, SQLite, and Markdown formats."""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
import sqlite3
from typing import Any

from omniscrape.config.models import ExportConfig

logger = logging.getLogger("omniscrape.exporters")


class BaseExporter:
    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        raise NotImplementedError


class JSONExporter(BaseExporter):
    """Exports items as a standard indented JSON array."""

    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(items, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Exported {len(items)} items to JSON: {path.resolve()}")


class JSONLinesExporter(BaseExporter):
    """Exports items as JSON Lines (one JSON object per line, ndjson)."""

    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False, default=str) + "\n")
        logger.info(f"Exported {len(items)} items to JSONL: {path.resolve()}")


class CSVExporter(BaseExporter):
    """Exports items to CSV with automated column discovery and nested data serialization."""

    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        if not items:
            logger.warning("No items to export to CSV.")
            return

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Collect union of all keys in items preserving order
        fieldnames: list[str] = []
        for it in items:
            for k in it.keys():
                if k not in fieldnames:
                    fieldnames.append(k)

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for it in items:
                row = {}
                for k in fieldnames:
                    val = it.get(k)
                    if isinstance(val, (list, dict)):
                        row[k] = json.dumps(val, ensure_ascii=False, default=str)
                    else:
                        row[k] = val
                writer.writerow(row)
        logger.info(f"Exported {len(items)} items to CSV: {path.resolve()}")


class SQLiteExporter(BaseExporter):
    """Exports items into a SQLite database with dynamic table creation and upserts."""

    def __init__(self, table_name: str = "scraped_data"):
        self.table_name = table_name

    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        if not items:
            return

        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Infer columns from items
        columns: set[str] = set()
        for it in items:
            columns.update(it.keys())
        col_list = sorted(list(columns))

        conn = sqlite3.connect(path)
        try:
            cursor = conn.cursor()
            cols_def = ", ".join(f'"{col}" TEXT' for col in col_list)
            cursor.execute(f'CREATE TABLE IF NOT EXISTS "{self.table_name}" ({cols_def})')

            placeholders = ", ".join("?" for _ in col_list)
            cols_names = ", ".join(f'"{col}"' for col in col_list)
            sql = f'INSERT INTO "{self.table_name}" ({cols_names}) VALUES ({placeholders})'

            rows_to_insert = []
            for it in items:
                row = []
                for col in col_list:
                    val = it.get(col)
                    if isinstance(val, (list, dict)):
                        row.append(json.dumps(val, ensure_ascii=False, default=str))
                    elif val is not None:
                        row.append(str(val))
                    else:
                        row.append(None)
                rows_to_insert.append(row)

            cursor.executemany(sql, rows_to_insert)
            conn.commit()
            logger.info(f"Exported {len(items)} items to SQLite table '{self.table_name}' in {path.resolve()}")
        finally:
            conn.close()


class MarkdownExporter(BaseExporter):
    """Exports items as formatted Markdown document, ideal for human review or LLM pipelines."""

    def export(self, items: list[dict[str, Any]], filepath: str | Path) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        lines: list[str] = [
            "# Scraped Data Report\n",
            f"**Total Records:** {len(items)}\n",
            "---\n",
        ]

        for i, item in enumerate(items, 1):
            title = item.get("title") or item.get("name") or f"Record #{i}"
            lines.append(f"### {i}. {title}\n")
            for k, v in item.items():
                if k in ("title", "name"):
                    continue
                if isinstance(v, list):
                    lines.append(f"- **{k}:** {', '.join(str(x) for x in v)}")
                else:
                    lines.append(f"- **{k}:** {v}")
            lines.append("\n---\n")

        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info(f"Exported {len(items)} items to Markdown: {path.resolve()}")


def export_data(items: list[dict[str, Any]], export_cfg: ExportConfig) -> None:
    """Convenience helper to route data to the appropriate exporter."""
    fmt = export_cfg.format.lower()
    if fmt == "json":
        JSONExporter().export(items, export_cfg.filepath)
    elif fmt == "jsonl":
        JSONLinesExporter().export(items, export_cfg.filepath)
    elif fmt == "csv":
        CSVExporter().export(items, export_cfg.filepath)
    elif fmt == "sqlite":
        SQLiteExporter(table_name=export_cfg.table_name).export(items, export_cfg.filepath)
    elif fmt == "markdown":
        MarkdownExporter().export(items, export_cfg.filepath)
    else:
        raise ValueError(f"Unsupported export format: {fmt}")
