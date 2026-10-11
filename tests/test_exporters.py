import json
import sqlite3
from pathlib import Path
from omniscrape.pipelines.exporters import (
    JSONExporter,
    JSONLinesExporter,
    CSVExporter,
    SQLiteExporter,
    MarkdownExporter,
)


def test_json_and_jsonl_exporter(tmp_path: Path):
    items = [
        {"id": 1, "title": "First", "tags": ["a", "b"]},
        {"id": 2, "title": "Second", "tags": ["c"]},
    ]

    # Test JSON
    json_path = tmp_path / "data.json"
    JSONExporter().export(items, json_path)
    assert json_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(loaded) == 2
    assert loaded[0]["title"] == "First"

    # Test JSONL
    jsonl_path = tmp_path / "data.jsonl"
    JSONLinesExporter().export(items, jsonl_path)
    assert jsonl_path.exists()
    lines = jsonl_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2


def test_csv_exporter(tmp_path: Path):
    items = [
        {"id": 1, "name": "Apple", "price": 1.25},
        {"id": 2, "name": "Banana", "price": 0.75},
    ]
    csv_path = tmp_path / "fruits.csv"
    CSVExporter().export(items, csv_path)
    assert csv_path.exists()
    content = csv_path.read_text(encoding="utf-8")
    assert "id,name,price" in content
    assert "Apple" in content


def test_sqlite_exporter(tmp_path: Path):
    items = [
        {"id": "100", "title": "Item A"},
        {"id": "200", "title": "Item B"},
    ]
    db_path = tmp_path / "test.db"
    SQLiteExporter(table_name="records").export(items, db_path)
    assert db_path.exists()

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title FROM records")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2
    assert rows[0] == ("100", "Item A")


def test_markdown_exporter(tmp_path: Path):
    items = [
        {"title": "Note 1", "author": "Alice"},
    ]
    md_path = tmp_path / "report.md"
    MarkdownExporter().export(items, md_path)
    assert md_path.exists()
    text = md_path.read_text(encoding="utf-8")
    assert "Note 1" in text
    assert "Alice" in text
