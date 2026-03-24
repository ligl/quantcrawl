from __future__ import annotations

from scrapy import Request, Spider
from scrapy.crawler import Crawler


class DataGuardMiddleware:
    """Hook for custom signature/cookie validation logic without breaking Scrapy flow."""

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> DataGuardMiddleware:
        _ = crawler
        return cls()

    def process_request(self, request: Request, spider: Spider) -> None:
        _ = spider
        policy = request.meta.get("policy")
        guard = getattr(policy, "data_guard_policy", {})
        signature_header = guard.get("signature_header")
        signature_value = guard.get("signature_value")
        if signature_header and signature_value:
            request.headers[str(signature_header)] = str(signature_value)
