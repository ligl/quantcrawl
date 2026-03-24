from __future__ import annotations

from typing import Protocol

from scrapy import Request

from .policy import SpiderPolicyProfile


class PolicyPlugin(Protocol):
    """Middleware policy plugin contract."""

    name: str

    def process_request(self, request: Request, profile: SpiderPolicyProfile) -> None:
        """Apply policy to outgoing request in-place."""

