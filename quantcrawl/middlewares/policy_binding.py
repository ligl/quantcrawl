from __future__ import annotations

from scrapy import Request, Spider
from scrapy.crawler import Crawler

from quantcrawl.policy import PolicyResolver


class PolicyBindingMiddleware:
    """Attach per-spider policy to request meta for downstream middlewares."""

    def __init__(self, resolver: PolicyResolver) -> None:
        self.resolver = resolver

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> PolicyBindingMiddleware:
        return cls(resolver=PolicyResolver.from_settings(crawler.settings))

    def process_request(self, request: Request, spider: Spider) -> None:
        if "policy" not in request.meta:
            source = str(request.meta.get("source") or getattr(spider, "source", "")).strip()
            dataset = str(request.meta.get("dataset") or getattr(spider, "dataset", "")).strip()
            request.meta["policy"] = self.resolver.resolve(
                spider_name=spider.name,
                source=source,
                dataset=dataset,
            )
