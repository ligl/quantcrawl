from __future__ import annotations

from scrapy import Request, Spider
from scrapy.crawler import Crawler


class ProxyPolicyMiddleware:
    @classmethod
    def from_crawler(cls, crawler: Crawler) -> ProxyPolicyMiddleware:
        _ = crawler
        return cls()

    def process_request(self, request: Request, spider: Spider) -> None:
        _ = spider
        policy = request.meta.get("policy")
        ip_policy = getattr(policy, "ip_policy", {})
        proxy = ip_policy.get("proxy")
        if proxy:
            request.meta["proxy"] = proxy
