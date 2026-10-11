"""HTML parser supporting CSS selectors, XPath, JSON-LD, meta tags, and structured extraction."""
from __future__ import annotations

import json
import logging
import re
from typing import Any
from bs4 import BeautifulSoup, Tag
import lxml.html

from omniscrape.config.models import ExtractType, FieldConfig, ItemConfig
from omniscrape.extractors.transforms import apply_transforms

logger = logging.getLogger("omniscrape.parser")


class HTMLParser:
    """Parses HTML content using BeautifulSoup and lxml for selector and metadata extraction."""

    def __init__(self, html_content: str, base_url: str = ""):
        self.html_content = html_content
        self.base_url = base_url
        self._soup: BeautifulSoup | None = None
        self._lxml_tree: Any = None

    @property
    def soup(self) -> BeautifulSoup:
        if self._soup is None:
            self._soup = BeautifulSoup(self.html_content, "lxml")
        return self._soup

    @property
    def lxml_tree(self) -> Any:
        if self._lxml_tree is None:
            try:
                self._lxml_tree = lxml.html.fromstring(self.html_content)
            except Exception as e:
                logger.warning(f"Failed to parse lxml tree: {e}")
                self._lxml_tree = None
        return self._lxml_tree

    def extract_field(self, field: FieldConfig, context_node: Tag | None = None) -> Any:
        """Extract a field from the document or from a specific context node."""
        root = context_node or self.soup

        # Count extraction shortcut
        if field.extract == ExtractType.COUNT:
            if field.selector:
                return len(root.select(field.selector))
            elif field.xpath and self.lxml_tree is not None:
                return len(self.lxml_tree.xpath(field.xpath))
            return 0

        # CSS or XPath element selection
        if field.xpath:
            nodes = self._select_xpath(field.xpath, context_node)
        elif field.selector:
            nodes = root.select(field.selector)
        else:
            nodes = [root] if context_node else []

        if not nodes:
            raw_val = field.default
            return apply_transforms(raw_val, field.transforms, base_url=self.base_url)

        if field.multiple:
            values = [self._extract_node_value(node, field) for node in nodes]
            return apply_transforms(values, field.transforms, base_url=self.base_url)
        else:
            raw_val = self._extract_node_value(nodes[0], field)
            val = raw_val if raw_val is not None else field.default
            return apply_transforms(val, field.transforms, base_url=self.base_url)

    def _select_xpath(self, xpath: str, context_node: Tag | None = None) -> list[Any]:
        """Execute an XPath query using lxml."""
        if context_node is not None:
            # Parse context node into lxml tree
            try:
                sub_tree = lxml.html.fromstring(str(context_node))
                return sub_tree.xpath(xpath)
            except Exception:
                return []
        if self.lxml_tree is not None:
            return self.lxml_tree.xpath(xpath)
        return []

    def _extract_node_value(self, node: Any, field: FieldConfig) -> Any:
        """Extract raw value from an element based on ExtractType."""
        # 1. BeautifulSoup Tag handling
        if isinstance(node, Tag):
            if field.extract == ExtractType.TEXT:
                return node.get_text()
            elif field.extract == ExtractType.ATTR and field.attribute:
                val = node.get(field.attribute)
                if isinstance(val, list):
                    return " ".join(val)
                return val
            elif field.extract == ExtractType.INNER_HTML:
                return node.decode_contents()
            elif field.extract == ExtractType.OUTER_HTML:
                return str(node)
            elif field.extract == ExtractType.REGEX and field.regex:
                match = re.search(field.regex, str(node))
                return match.group(1) if (match and match.groups()) else (match.group(0) if match else None)
            return node.get_text()

        # 2. lxml Element handling
        if callable(getattr(node, "text_content", None)):
            text = node.text_content()
            if field.extract == ExtractType.TEXT:
                return text
            elif field.extract == ExtractType.ATTR and field.attribute:
                return node.attrib.get(field.attribute)
            elif field.extract == ExtractType.INNER_HTML:
                return "".join(lxml.html.tostring(c, encoding="unicode") for c in node)
            elif field.extract == ExtractType.OUTER_HTML:
                return lxml.html.tostring(node, encoding="unicode")
            return text

        return str(node)

    def extract_items(self, item_config: ItemConfig) -> list[dict[str, Any]]:
        """Extract all items matching the item configuration."""
        items: list[dict[str, Any]] = []

        if item_config.container_selector:
            containers = self.soup.select(item_config.container_selector)
            for container in containers:
                record = {}
                is_valid = True
                for name, field_cfg in item_config.fields.items():
                    val = self.extract_field(field_cfg, context_node=container)
                    if field_cfg.required and (val is None or val == "" or val == []):
                        is_valid = False
                        break
                    record[name] = val
                if is_valid:
                    items.append(record)
        else:
            # Single page-level record
            record = {}
            is_valid = True
            for name, field_cfg in item_config.fields.items():
                val = self.extract_field(field_cfg)
                if field_cfg.required and (val is None or val == "" or val == []):
                    is_valid = False
                    break
                record[name] = val
            if is_valid and record:
                items.append(record)

        return items

    def extract_json_ld(self) -> list[dict[str, Any]]:
        """Extract all JSON-LD structured data blocks from the document."""
        scripts = self.soup.find_all("script", type="application/ld+json")
        data_blocks: list[dict[str, Any]] = []
        for script in scripts:
            if not script.string:
                continue
            try:
                data = json.loads(script.string.strip())
                if isinstance(data, list):
                    data_blocks.extend(data)
                elif isinstance(data, dict):
                    data_blocks.append(data)
            except Exception:
                pass
        return data_blocks

    def extract_meta_tags(self) -> dict[str, str]:
        """Extract OpenGraph, Twitter, and standard HTML meta tags."""
        meta_dict = {}
        for tag in self.soup.find_all("meta"):
            key = tag.get("name") or tag.get("property")
            val = tag.get("content")
            if key and val:
                meta_dict[str(key)] = str(val)
        return meta_dict
