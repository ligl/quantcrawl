from __future__ import annotations

from logging import Handler, Logger
from logging.handlers import RotatingFileHandler
from pathlib import Path

from scrapy import signals
from scrapy.crawler import Crawler


class SpiderLogHooks:
    """Attach one rotating file handler per spider."""

    def __init__(self, log_dir: str, max_bytes: int, backup_count: int) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.handlers: dict[str, Handler] = {}

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> SpiderLogHooks:
        ext = cls(
            log_dir=crawler.settings.get("LOG_DIR", "logs"),
            max_bytes=crawler.settings.getint("LOG_MAX_BYTES", 20 * 1024 * 1024),
            backup_count=crawler.settings.getint("LOG_BACKUP_COUNT", 10),
        )
        crawler.signals.connect(ext.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_opened(self, spider: object) -> None:
        logger = self._resolve_logger(spider)
        spider_name = getattr(spider, "name", "unknown")
        path = self.log_dir / f"{spider_name}.log"

        handler = RotatingFileHandler(
            filename=path,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        logger.addHandler(handler)
        self.handlers[spider_name] = handler

    def spider_closed(self, spider: object, reason: str) -> None:
        _ = reason
        logger = self._resolve_logger(spider)
        spider_name = getattr(spider, "name", "unknown")
        handler = self.handlers.pop(spider_name, None)
        if handler is None:
            return
        logger.removeHandler(handler)
        handler.close()

    def _resolve_logger(self, spider: object) -> Logger:
        logger = spider.logger # type: ignore
        resolved = getattr(logger, "logger", logger)
        if isinstance(resolved, Logger):
            return resolved
        raise TypeError(f"Unsupported spider logger type: {type(resolved)!r}")
