from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Action = Literal["pause", "continue", "retry"]


@dataclass(frozen=True, slots=True)
class ChallengeEvent:
    spider_name: str
    url: str
    status: int
    challenge_type: str
    provider_ref: str
    max_attempts: int
    on_fail_action: str
    attempt: int = 1


@dataclass(frozen=True, slots=True)
class ChallengeDecision:
    action: Action
    solved: bool
    reason: str
