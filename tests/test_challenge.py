from __future__ import annotations

from quantcrawl.challenge import ChallengeEvent, ChallengeOrchestrator


class _OkProvider:
    name = "ok"

    def is_available(self) -> bool:
        return True

    def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"

    def solve(self, event: ChallengeEvent) -> bool:
        _ = event
        return True


class _FailProvider:
    name = "fail"

    def is_available(self) -> bool:
        return True

    def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"

    def solve(self, event: ChallengeEvent) -> bool:
        _ = event
        return False


class _UnavailableProvider:
    name = "unavailable"

    def is_available(self) -> bool:
        return False

    def healthcheck(self) -> tuple[bool, str]:
        return True, "ok"

    def solve(self, event: ChallengeEvent) -> bool:
        _ = event
        return True


class _UnhealthyProvider:
    name = "unhealthy"

    def is_available(self) -> bool:
        return True

    def healthcheck(self) -> tuple[bool, str]:
        return False, "bad_session"

    def solve(self, event: ChallengeEvent) -> bool:
        _ = event
        return True


def _event(
    provider_ref: str,
    max_attempts: int = 1,
    on_fail_action: str = "pause",
    attempt: int = 1,
) -> ChallengeEvent:
    return ChallengeEvent(
        spider_name="s1",
        url="https://example.com",
        status=403,
        challenge_type="generic",
        provider_ref=provider_ref,
        max_attempts=max_attempts,
        on_fail_action=on_fail_action,
        attempt=attempt,
    )


def test_orchestrator_continue_when_provider_succeeds() -> None:
    orchestrator = ChallengeOrchestrator(providers={"ok": _OkProvider()})
    decision = orchestrator.handle_detection(_event(provider_ref="ok"))
    assert decision.action == "continue"
    assert decision.solved is True


def test_orchestrator_fallback_when_provider_missing() -> None:
    orchestrator = ChallengeOrchestrator(providers={})
    decision = orchestrator.handle_detection(_event(provider_ref="unknown", on_fail_action="pause"))
    assert decision.action == "pause"
    assert decision.solved is False


def test_orchestrator_retry_when_unsolved_and_retry_policy() -> None:
    orchestrator = ChallengeOrchestrator(providers={"fail": _FailProvider()})
    decision = orchestrator.handle_detection(_event(provider_ref="fail", on_fail_action="retry"))
    assert decision.action == "retry"
    assert decision.solved is False


def test_orchestrator_fails_when_max_attempts_exceeded() -> None:
    orchestrator = ChallengeOrchestrator(providers={"ok": _OkProvider()})
    decision = orchestrator.handle_detection(
        _event(provider_ref="ok", max_attempts=1, on_fail_action="pause", attempt=2),
    )
    assert decision.action == "pause"
    assert decision.solved is False


def test_orchestrator_fallback_when_provider_unavailable() -> None:
    orchestrator = ChallengeOrchestrator(providers={"u1": _UnavailableProvider()})
    decision = orchestrator.handle_detection(_event(provider_ref="u1", on_fail_action="retry"))
    assert decision.action == "retry"
    assert decision.solved is False
    assert decision.reason == "provider_unavailable"


def test_orchestrator_fallback_when_provider_unhealthy() -> None:
    orchestrator = ChallengeOrchestrator(providers={"u1": _UnhealthyProvider()})
    decision = orchestrator.handle_detection(_event(provider_ref="u1", on_fail_action="pause"))
    assert decision.action == "pause"
    assert decision.solved is False
    assert decision.reason == "provider_unhealthy:bad_session"
