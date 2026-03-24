from __future__ import annotations

import json

from scrapy import Request, Spider
from scrapy.crawler import Crawler
from scrapy.exceptions import IgnoreRequest
from scrapy.http import Response

from quantcrawl.challenge import (
    ChallengeDefaultDetector,
    ChallengeDetector,
    ChallengeEvent,
    ChallengeOrchestrator,
    build_solver_providers,
    build_spider_detectors,
)


class ChallengeDetectionMiddleware:
    """Detect challenge responses and stop invalid data from entering parse pipeline."""

    def __init__(
        self,
        orchestrator: ChallengeOrchestrator,
        default_detector: ChallengeDetector,
        spider_detectors: dict[str, ChallengeDetector],
    ) -> None:
        self.orchestrator = orchestrator
        self.default_detector = default_detector
        self.spider_detectors = spider_detectors

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> ChallengeDetectionMiddleware:
        registry = crawler.settings.getdict("CHALLENGE_PROVIDER_REGISTRY")
        configs = crawler.settings.getdict("CHALLENGE_PROVIDER_CONFIGS")
        providers = build_solver_providers(registry=registry, configs=configs)
        spider_profiles = crawler.settings.getdict("ANTIBOT_SPIDER_PROFILES")
        spider_detectors = build_spider_detectors(spider_profiles=spider_profiles)
        return cls(
            orchestrator=ChallengeOrchestrator(providers=providers),
            default_detector=ChallengeDefaultDetector(),
            spider_detectors=spider_detectors,
        )

    def process_response(
        self,
        request: Request,
        response: Response,
        spider: Spider,
    ) -> Response | Request:
        policy = request.meta.get("policy")
        detector, detector_source = self._pick_detector(spider.name)
        detection = detector.detect(request=request, response=response, policy=policy)
        if not detection.matched:
            return response

        spider.crawler.stats.inc_value("antibot/challenge_detected")  # type: ignore
        spider.crawler.stats.inc_value(  # type: ignore
            f"antibot/challenge_type/{detection.challenge_type}",
        )
        challenge_event = {
            "url": response.url,
            "status": response.status,
            "spider": spider.name,
            "challenge_type": detection.challenge_type,
            "evidence": detection.evidence,
            "detector_source": detector_source,
            "allowed_challenge_types": list(getattr(policy, "allowed_challenge_types", [])),
        }
        spider.logger.warning(
            "challenge_detected=%s",
            json.dumps(challenge_event, ensure_ascii=True),
        )

        if not getattr(policy, "challenge_enabled", False):
            return response

        if not self._is_allowed_type(policy=policy, challenge_type=detection.challenge_type):
            spider.crawler.stats.inc_value("antibot/challenge_skipped/not_allowed_type")  # type: ignore
            return response

        event = ChallengeEvent(
            spider_name=spider.name,
            url=response.url,
            status=response.status,
            challenge_type=detection.challenge_type,
            provider_ref=str(getattr(policy, "solver_provider_ref", "")),
            max_attempts=int(getattr(policy, "max_challenge_attempts", 1)),
            on_fail_action=str(getattr(policy, "on_fail_action", "pause")),
            attempt=int(request.meta.get("challenge_attempt", 1)),
        )
        decision = self.orchestrator.handle_detection(event)
        spider.crawler.stats.inc_value(  # type: ignore
            f"antibot/challenge_action/{decision.action}",
        )
        if decision.action == "retry":
            current_attempt = int(request.meta.get("challenge_attempt", 1))
            max_attempts = max(int(getattr(policy, "max_challenge_attempts", 1)), 1)
            if current_attempt >= max_attempts:
                raise IgnoreRequest("Challenge detected; action=pause")
            return self._build_retry_request(request=request, attempt=current_attempt + 1)
        if decision.action == "pause":
            raise IgnoreRequest(f"Challenge detected; action={decision.action}")
        return response

    def _build_retry_request(self, request: Request, attempt: int) -> Request:
        retry_request = request.copy()
        retry_request.meta["challenge_attempt"] = attempt
        retry_request.dont_filter = True
        return retry_request

    def _pick_detector(self, spider_name: str) -> tuple[ChallengeDetector, str]:
        detector = self.spider_detectors.get(spider_name)
        if detector is not None:
            return detector, "spider"
        return self.default_detector, "default"

    def _is_allowed_type(self, policy: object, challenge_type: str) -> bool:
        allowed_raw = getattr(policy, "allowed_challenge_types", [])
        allowed = [str(item).strip().lower() for item in allowed_raw]
        if not allowed:
            return True
        return challenge_type.lower() in allowed
