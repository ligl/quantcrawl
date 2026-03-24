from __future__ import annotations

from fake_useragent import UserAgent
from scrapy import Request, Spider
from scrapy.crawler import Crawler


class HeaderPolicyMiddleware:
    def __init__(self, fallback_platform: str = "desktop") -> None:
        self.ua = UserAgent()
        self.fallback_platform = fallback_platform

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> HeaderPolicyMiddleware:
        return cls(fallback_platform=crawler.settings.get("DEFAULT_UA_PLATFORM", "desktop"))

    def process_request(self, request: Request, spider: Spider) -> None:
        _ = spider
        policy = request.meta.get("policy")
        header_profile = getattr(policy, "header_profile", {})

        if b"User-Agent" not in request.headers:
            platform = header_profile.get("platform", self.fallback_platform)
            request.headers["User-Agent"] = self.ua.random if platform else self.ua.random

        if b"Accept" not in request.headers:
            request.headers["Accept"] = header_profile.get(
                "accept",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            )

        if b"Accept-Language" not in request.headers:
            request.headers["Accept-Language"] = header_profile.get(
                "accept_language",
                "en-US,en;q=0.9",
            )

        referer = header_profile.get("referer")
        if referer and b"Referer" not in request.headers:
            request.headers["Referer"] = referer
