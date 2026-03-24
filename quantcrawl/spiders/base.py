from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

import scrapy
from scrapy import Request
from scrapy.http import Response


class BaseSpider(scrapy.Spider):
    custom_settings = {
        "DOWNLOAD_TIMEOUT": 20,
    }

    dataset: str = "base_dataset"
    source: str = "unknown_source"

    def build_record_hash(self, payload: dict[str, Any]) -> str:
        return sha256(str(sorted(payload.items())).encode("utf-8")).hexdigest()

    def build_common_item(self, payload: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC).isoformat()
        payload.setdefault("source", self.source)
        payload.setdefault("dataset", self.dataset)
        payload.setdefault("collected_at", now)
        payload.setdefault("event_time", now)
        payload.setdefault("raw_payload_hash", self.build_record_hash(payload))
        payload.setdefault("metadata", {})
        return payload

    def start_requests(self) -> Any:
        for url in self.start_urls:
            yield Request(
                url,
                callback=self.parse_list,
                errback=self.on_request_error,
                meta={
                    "source": self.source,
                    "dataset": self.dataset,
                },
            )

    def parse_list(self, response: Response) -> Any:
        raise NotImplementedError

    def parse_detail(self, response: Response) -> Any:
        raise NotImplementedError

    def on_request_error(self, failure: Any) -> None:
        self.crawler.stats.inc_value("request_error_count") # type: ignore
        self.logger.error("request_failed=%s", failure)
