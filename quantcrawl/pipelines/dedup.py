from __future__ import annotations

from typing import Any

from scrapy.exceptions import DropItem


class DedupPipeline:
    def __init__(self) -> None:
        self._seen: set[str] = set()

    def process_item(self, item: Any, spider: Any) -> Any:
        _ = spider
        key = f"{item.get('source')}|{item.get('dataset')}|{item.get('raw_payload_hash')}"
        if key in self._seen:
            raise DropItem(f"Duplicate item detected: {key}")
        self._seen.add(key)
        return item
