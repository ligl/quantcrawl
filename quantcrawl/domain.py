from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DomainSpec:
    """Domain-level declaration for job wiring and policy reference."""

    name: str
    item_path: str
    loader_path: str
    pipeline_path: str
    policy_ref: str

