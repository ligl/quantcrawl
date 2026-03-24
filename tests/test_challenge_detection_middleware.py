from __future__ import annotations

from types import SimpleNamespace

import pytest
from scrapy import Request
from scrapy.exceptions import IgnoreRequest
from scrapy.http import TextResponse

from quantcrawl.challenge import (
    ChallengeDefaultDetector,
    ChallengeDetectionResult,
    ChallengeEvent,
    ChallengeOrchestrator,
)
from quantcrawl.middlewares.challenge_detection import ChallengeDetectionMiddleware


class _Stats:
    def __init__(self) -> None:
        self.values: dict[str, int] = {}

    def inc_value(self, key: str, count: int = 1) -> None:
        self.values[key] = self.values.get(key, 0) + count


class _Logger:
    def warning(self, msg: str, *args: object) -> None:
        _ = (msg, args)


class _FailProvider:
    name = "fail"

    def is_available(self) -> bool:
        return True

    def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"

    def solve(self, event: ChallengeEvent) -> bool:
        _ = event
        return False


def _build_spider() -> object:
    stats = _Stats()
    crawler = SimpleNamespace(stats=stats)
    return SimpleNamespace(name="demo_spider", logger=_Logger(), crawler=crawler)


def _build_policy(*, max_attempts: int = 2, on_fail_action: str = "retry") -> object:
    return SimpleNamespace(
        challenge_enabled=True,
        allowed_challenge_types=[],
        solver_provider_ref="fail",
        max_challenge_attempts=max_attempts,
        on_fail_action=on_fail_action,
    )


def _build_middleware(
    spider_detectors: dict[str, object] | None = None,
) -> ChallengeDetectionMiddleware:
    return ChallengeDetectionMiddleware(
        orchestrator=ChallengeOrchestrator(providers={"fail": _FailProvider()}),
        default_detector=ChallengeDefaultDetector(),
        spider_detectors=spider_detectors or {},
    )


def test_returns_retry_request_when_action_is_retry() -> None:
    middleware = ChallengeDetectionMiddleware(
        orchestrator=ChallengeOrchestrator(providers={"fail": _FailProvider()}),
        default_detector=ChallengeDefaultDetector(),
        spider_detectors={},
    )
    spider = _build_spider()
    request = Request(url="https://example.com")
    request.meta["policy"] = _build_policy(max_attempts=2, on_fail_action="retry")
    response = TextResponse(
        url="https://example.com",
        status=403,
        body=b"captcha challenge page",
        encoding="utf-8",
        request=request,
    )

    result = middleware.process_response(request=request, response=response, spider=spider)

    assert isinstance(result, Request)
    assert result.meta["challenge_attempt"] == 2
    assert result.dont_filter is True


def test_stops_retry_when_max_attempts_reached() -> None:
    middleware = _build_middleware()
    spider = _build_spider()
    request = Request(url="https://example.com")
    request.meta["policy"] = _build_policy(max_attempts=2, on_fail_action="retry")
    request.meta["challenge_attempt"] = 2
    response = TextResponse(
        url="https://example.com",
        status=403,
        body=b"captcha challenge page",
        encoding="utf-8",
        request=request,
    )

    with pytest.raises(IgnoreRequest, match="action=pause"):
        middleware.process_response(request=request, response=response, spider=spider)


def test_allows_all_types_when_allowed_challenge_types_is_empty() -> None:
    middleware = _build_middleware()
    spider = _build_spider()
    request = Request(url="https://example.com")
    request.meta["policy"] = _build_policy(on_fail_action="retry")
    response = TextResponse(
        url="https://example.com",
        status=429,
        body=b"too many requests",
        encoding="utf-8",
        request=request,
    )

    result = middleware.process_response(request=request, response=response, spider=spider)
    assert isinstance(result, Request)


def test_skips_when_detected_type_not_in_allowed_challenge_types() -> None:
    middleware = _build_middleware()
    spider = _build_spider()
    request = Request(url="https://example.com")
    policy = _build_policy(on_fail_action="retry")
    policy.allowed_challenge_types = ["slider"]
    request.meta["policy"] = policy
    response = TextResponse(
        url="https://example.com",
        status=429,
        body=b"too many requests",
        encoding="utf-8",
        request=request,
    )

    result = middleware.process_response(request=request, response=response, spider=spider)
    assert result is response
    assert spider.crawler.stats.values.get("antibot/challenge_skipped/not_allowed_type") == 1


def test_uses_spider_detector_when_defined() -> None:
    class _SpiderDetector:
        def __init__(self) -> None:
            self.used = False

        def detect(
            self,
            request: Request,
            response: TextResponse,
            policy: object,
        ) -> ChallengeDetectionResult:
            _ = (request, response, policy)
            self.used = True
            return ChallengeDetectionResult(
                matched=True,
                challenge_type="captcha",
                evidence=["spider_detector"],
            )

    spider_detector = _SpiderDetector()
    middleware = _build_middleware(spider_detectors={"demo_spider": spider_detector})
    spider = _build_spider()
    request = Request(url="https://example.com")
    request.meta["policy"] = _build_policy(on_fail_action="retry")
    response = TextResponse(
        url="https://example.com",
        status=200,
        body=b"<html>normal page</html>",
        encoding="utf-8",
        request=request,
    )

    result = middleware.process_response(request=request, response=response, spider=spider)
    assert spider_detector.used is True
    assert isinstance(result, Request)
