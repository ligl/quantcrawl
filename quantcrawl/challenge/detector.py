from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol

from scrapy import Request
from scrapy.http import Response


class ChallengeType(StrEnum):
    CAPTCHA = "captcha"
    SLIDER = "slider"
    JS_CHALLENGE = "js_challenge"
    RATE_LIMIT = "rate_limit"
    GENERIC = "generic"


@dataclass(frozen=True, slots=True)
class ChallengeDetectionResult:
    matched: bool
    challenge_type: str = ChallengeType.GENERIC.value
    evidence: list[str] = field(default_factory=list)


class ChallengeDetector(Protocol):
    def detect(
        self,
        request: Request,
        response: Response,
        policy: Any,
    ) -> ChallengeDetectionResult:
        """Detect challenge in response and return structured result."""
        raise NotImplementedError


class ChallengeDefaultDetector:
    CHALLENGE_PATTERNS: dict[ChallengeType, tuple[str, ...]] = {
        ChallengeType.CAPTCHA: (
            r"captcha",
            r"验证码",
            r"verification",
            r"我不是机器人",
            r"click to verify",
        ),
        ChallengeType.SLIDER: (
            r"slider",
            r"drag",
            r"滑动验证",
            r"complete the puzzle",
        ),
        ChallengeType.JS_CHALLENGE: (
            r"<script>.*challenge",
            r"cf-clearance",
            r"__cf_chl",
            r"please wait.*seconds",
        ),
        ChallengeType.RATE_LIMIT: (
            r"429",
            r"too many requests",
            r"请求过于频繁",
            r"rate limit",
        ),
    }

    def __init__(self) -> None:
        self._compiled_patterns = {
            challenge_type: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
            for challenge_type, patterns in self.CHALLENGE_PATTERNS.items()
        }

    def detect(
        self,
        request: Request,
        response: Response,
        policy: Any,
    ) -> ChallengeDetectionResult:
        _ = (request, policy)
        text = response.text[:8000]
        evidence: list[str] = []

        # Hard signal for rate limiting.
        if response.status == 429:
            evidence.append("status=429")
            return ChallengeDetectionResult(
                matched=True,
                challenge_type=ChallengeType.RATE_LIMIT.value,
                evidence=evidence,
            )

        header_blob = " ".join(f"{k}:{v}" for k, v in response.headers.items())
        searchable = f"{text}\n{header_blob}\n{response.url}"

        ordered_types = (
            ChallengeType.RATE_LIMIT,
            ChallengeType.JS_CHALLENGE,
            ChallengeType.CAPTCHA,
            ChallengeType.SLIDER,
        )

        for challenge_type in ordered_types:
            for pattern in self._compiled_patterns[challenge_type]:
                if pattern.search(searchable):
                    evidence.append(pattern.pattern)
                    return ChallengeDetectionResult(
                        matched=True,
                        challenge_type=challenge_type.value,
                        evidence=evidence,
                    )

        return ChallengeDetectionResult(matched=False, challenge_type=ChallengeType.GENERIC.value)
