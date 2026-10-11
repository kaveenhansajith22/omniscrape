"""Deduplication pipeline to ensure unique scraped records."""
from __future__ import annotations

import hashlib
import json
from typing import Any


class ItemDeduplicator:
    """Filters duplicate records based on specified key fields or overall content hash."""

    def __init__(self, key_fields: list[str] | None = None):
        self.key_fields = key_fields
        self._seen: set[str] = set()
        self.duplicates_dropped: int = 0
        self.unique_count: int = 0

    def _generate_fingerprint(self, item: dict[str, Any]) -> str:
        """Create a hash or composite key for the item."""
        if self.key_fields:
            key_values = [str(item.get(k, "")) for k in self.key_fields]
            return "|".join(key_values)
        else:
            # Deterministic JSON hash of entire item
            serialized = json.dumps(item, sort_keys=True, default=str)
            return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def is_duplicate(self, item: dict[str, Any]) -> bool:
        """Check if item has already been seen; marks as seen if new."""
        fp = self._generate_fingerprint(item)
        if fp in self._seen:
            self.duplicates_dropped += 1
            return True
        self._seen.add(fp)
        self.unique_count += 1
        return False
