from __future__ import annotations

from scrapy import signals
from scrapy.crawler import Crawler

from .utils.notifier import DingTalkNotifier, EmailNotifier, FeishuNotifier, Notifier


class AlertHooks:
    """Send spider failures to enabled channels (Email/Feishu/DingTalk)."""

    def __init__(self, notifiers: list[Notifier]) -> None:
        self.notifiers = notifiers

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> AlertHooks:
        settings = crawler.settings
        notifiers: list[Notifier] = []

        if settings.getbool("ALERT_EMAIL_ENABLED", False):
            notifiers.append(
                EmailNotifier(
                    smtp_host=settings.get("SMTP_HOST", ""),
                    smtp_port=settings.getint("SMTP_PORT", 587),
                    smtp_user=settings.get("SMTP_USER", ""),
                    smtp_password=settings.get("SMTP_PASSWORD", ""),
                    sender=settings.get("ALERT_EMAIL_FROM", ""),
                    to=settings.get("ALERT_EMAIL_TO", ""),
                )
            )

        if settings.getbool("ALERT_FEISHU_ENABLED", False):
            webhook = settings.get("ALERT_FEISHU_WEBHOOK", "")
            if webhook:
                notifiers.append(FeishuNotifier(webhook=webhook))

        if settings.getbool("ALERT_DINGTALK_ENABLED", False):
            webhook = settings.get("ALERT_DINGTALK_WEBHOOK", "")
            if webhook:
                notifiers.append(DingTalkNotifier(webhook=webhook))

        ext = cls(notifiers=notifiers)
        crawler.signals.connect(ext.spider_error, signal=signals.spider_error)
        crawler.signals.connect(ext.spider_closed, signal=signals.spider_closed)
        return ext

    def spider_error(self, failure: object, response: object, spider: object) -> None:
        _ = response
        title = f"[QuantCrawl] spider error: {getattr(spider, 'name', 'unknown')}"
        body = str(failure)
        self._notify(title, body)

    def spider_closed(self, spider: object, reason: str) -> None:
        if reason == "finished":
            return
        title = f"[QuantCrawl] spider closed: {getattr(spider, 'name', 'unknown')}"
        body = f"reason={reason}"
        self._notify(title, body)

    def _notify(self, title: str, body: str) -> None:
        for notifier in self.notifiers:
            try:
                notifier.send(title=title, body=body)
            except Exception:
                continue
