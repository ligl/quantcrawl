from __future__ import annotations

from types import SimpleNamespace

from scrapy import Request
from scrapy.http import TextResponse

from quantcrawl.challenge import ChallengeDefaultDetector, ChallengeType


def _response(*, body: bytes, status: int = 200, url: str = "https://example.com") -> TextResponse:
    request = Request(url=url)
    return TextResponse(
        url=url,
        status=status,
        body=body,
        encoding="utf-8",
        request=request,
    )


def test_detects_captcha() -> None:
    detector = ChallengeDefaultDetector()
    result = detector.detect(
        request=Request("https://example.com"),
        response=_response(body=b"please click to verify"),
        policy=SimpleNamespace(),
    )
    assert result.matched is True
    assert result.challenge_type == ChallengeType.CAPTCHA.value


def test_detects_slider() -> None:
    detector = ChallengeDefaultDetector()
    result = detector.detect(
        request=Request("https://example.com"),
        response=_response(body=b"drag to complete the puzzle"),
        policy=SimpleNamespace(),
    )
    assert result.matched is True
    assert result.challenge_type == ChallengeType.SLIDER.value


def test_detects_js_challenge() -> None:
    detector = ChallengeDefaultDetector()
    result = detector.detect(
        request=Request("https://example.com"),
        response=_response(body=b"__cf_chl please wait 5 seconds"),
        policy=SimpleNamespace(),
    )
    assert result.matched is True
    assert result.challenge_type == ChallengeType.JS_CHALLENGE.value


def test_detects_rate_limit_from_status() -> None:
    detector = ChallengeDefaultDetector()
    result = detector.detect(
        request=Request("https://example.com"),
        response=_response(body=b"normal", status=429),
        policy=SimpleNamespace(),
    )
    assert result.matched is True
    assert result.challenge_type == ChallengeType.RATE_LIMIT.value


def test_returns_not_matched_when_no_patterns_hit() -> None:
    detector = ChallengeDefaultDetector()
    result = detector.detect(
        request=Request("https://example.com"),
        response=_response(body=b"hello world"),
        policy=SimpleNamespace(),
    )
    assert result.matched is False
