from __future__ import annotations

from typing import Protocol

from .types import ChallengeEvent


class SolverProvider(Protocol):
    """Pluggable challenge solver provider."""

    name: str

    def is_available(self) -> bool:
        """Return whether the provider is ready for solving challenges."""
        raise NotImplementedError

    def healthcheck(self) -> tuple[bool, str]:
        """Return (healthy, reason) for runtime diagnostics."""
        raise NotImplementedError

    def solve(self, event: ChallengeEvent) -> bool:
        """Return True when challenge solved successfully."""
        raise NotImplementedError
