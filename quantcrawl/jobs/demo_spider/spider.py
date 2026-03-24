from __future__ import annotations

from typing import Any

from scrapy.http import Response

from quantcrawl.jobs.demo_spider.item import DemoSpiderItem
from quantcrawl.jobs.demo_spider.loader import DemoSpiderLoader
from quantcrawl.spiders.base import BaseSpider


class DemoSpider(BaseSpider):
    """Single framework demo spider. No business-specific parsing logic."""

    name = "demo_spider"
    allowed_domains = ["www.czce.com.cn", "czce.com.cn"]
    start_urls = ["http://www.czce.com.cn/"]
    source = "czce"
    dataset = "exchange_notice_demo"

    def parse_list(self, response: Response) -> Any:
        loader = DemoSpiderLoader(item=DemoSpiderItem(), response=response)  # type: ignore
        loader.add_value("source", self.source)
        loader.add_value("dataset", self.dataset)
        loader.add_value("symbol_or_topic", "homepage")
        loader.add_value("url_or_endpoint", response.url)
        loader.add_value("event_time", "")
        loader.add_value("collected_at", "")

        title = response.css("title::text").get(default="郑州商品交易所")
        payload = {
            "title": title,
            "content": title,
            "attributes": {"site": "CZCE", "page_type": "homepage"},
        }
        normalized = self.build_common_item(payload)

        loader.add_value("raw_payload_hash", normalized["raw_payload_hash"])
        loader.add_value("title", payload["title"])
        loader.add_value("content", payload["content"])
        loader.add_value("attributes", payload["attributes"])
        loader.add_value("metadata", payload["attributes"])
        yield loader.load_item()

    def parse_detail(self, response: Response) -> Any:
        return None

