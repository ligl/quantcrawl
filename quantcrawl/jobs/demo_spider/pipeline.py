from __future__ import annotations

from typing import Any


class DemoSpiderPipeline:
    """Example job pipeline for demo_spider."""

    def process_item(self, item: Any, spider: Any) -> Any:
        if getattr(spider, "name", "") != "demo_spider":
            return item

        attributes = item.get("attributes")
        if attributes is None:
            item["attributes"] = {}
        return item

