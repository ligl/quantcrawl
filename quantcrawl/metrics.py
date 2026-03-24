from __future__ import annotations

from prometheus_client import Counter
from scrapy import signals
from scrapy.crawler import Crawler

REQUEST_COUNT = Counter("scrapy_requests_total", "Total requests", ["spider"])
ITEM_COUNT = Counter("scrapy_items_total", "Total items", ["spider", "dataset"])
ERROR_COUNT = Counter("scrapy_errors_total", "Total errors", ["spider"])
CHALLENGE_COUNT = Counter("scrapy_challenge_total", "Total challenge detections", ["spider"])


class StatsMetricsHooks:
    @classmethod
    def from_crawler(cls, crawler: Crawler) -> StatsMetricsHooks:
        ext = cls()
        crawler.signals.connect(ext.response_received, signal=signals.response_received)
        crawler.signals.connect(ext.item_scraped, signal=signals.item_scraped)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        return ext

    def response_received(self, response: object, request: object, spider: object) -> None:
        _ = response, request
        REQUEST_COUNT.labels(getattr(spider, "name", "unknown")).inc()

        stats = spider.crawler.stats
        challenge_hits = stats.get_value("antibot/challenge_detected", 0)
        if challenge_hits:
            CHALLENGE_COUNT.labels(getattr(spider, "name", "unknown")).inc(challenge_hits)
            stats.set_value("antibot/challenge_detected", 0)

    def item_scraped(self, item: object, response: object, spider: object) -> None:
        _ = response
        dataset = str(getattr(item, "get", lambda _k, _d=None: "unknown")("dataset", "unknown"))
        ITEM_COUNT.labels(getattr(spider, "name", "unknown"), dataset).inc()

    def spider_error(self, failure: object, response: object, spider: object) -> None:
        _ = failure, response
        ERROR_COUNT.labels(getattr(spider, "name", "unknown")).inc()
