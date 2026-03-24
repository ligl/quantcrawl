from __future__ import annotations

from typing import Any

from scrapy.exceptions import DropItem


class ValidationPipeline:
    required_fields = ("source", "dataset", "event_time", "collected_at", "raw_payload_hash")

    def process_item(self, item: Any, spider: Any) -> Any:
        _ = spider
        missing = [field for field in self.required_fields if not item.get(field)]
        if missing:
            raise DropItem(f"Missing required fields: {missing}")
        return item
