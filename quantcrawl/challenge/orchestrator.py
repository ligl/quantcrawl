from __future__ import annotations

from .provider import SolverProvider
from .types import Action, ChallengeDecision, ChallengeEvent


class ChallengeOrchestrator:
    """Challenge orchestration state machine with pluggable providers."""

    def __init__(self, providers: dict[str, SolverProvider] | None = None) -> None:
        self.providers = providers or {}

    def handle_detection(self, event: ChallengeEvent) -> ChallengeDecision:
        if event.attempt > max(event.max_attempts, 1):
            return self._fallback(
                event=event,
                reason=f"max_attempts_exceeded:{event.max_attempts}",
            )

        if not event.provider_ref:
            return self._fallback(event=event, reason="provider_not_configured")

        provider = self.providers.get(event.provider_ref)
        if provider is None:
            return self._fallback(event=event, reason="provider_not_found")

        if not self._provider_available(provider):
            return self._fallback(event=event, reason="provider_unavailable")

        healthy, health_reason = self._provider_health(provider)
        if not healthy:
            return self._fallback(
                event=event,
                reason=f"provider_unhealthy:{health_reason}",
            )

        solved = provider.solve(event)
        if solved:
            return ChallengeDecision(action="continue", solved=True, reason="challenge_solved")

        return self._fallback(event=event, reason="challenge_unsolved")

    def _provider_available(self, provider: SolverProvider) -> bool:
        check = getattr(provider, "is_available", None)
        if check is None:
            return True
        return bool(check())

    def _provider_health(self, provider: SolverProvider) -> tuple[bool, str]:
        check = getattr(provider, "healthcheck", None)
        if check is None:
            return True, "not_implemented"

        try:
            healthy, reason = check()
        except Exception as exc:
            return False, f"healthcheck_error:{exc}"
        return bool(healthy), str(reason)

    def _fallback(self, event: ChallengeEvent, reason: str) -> ChallengeDecision:
        action = self._normalize_action(event.on_fail_action)
        return ChallengeDecision(action=action, solved=False, reason=reason)

    def _normalize_action(self, raw: str) -> Action:
        value = raw.strip().lower()
        if value == "retry":
            return "retry"
        if value == "continue":
            return "continue"
        return "pause"
