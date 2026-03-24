from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ALLOWED_CHALLENGE_TYPES = {
    "captcha",
    "slider",
    "js_challenge",
    "rate_limit",
    "generic",
}

SOURCE_PROFILES_KEY = "source_profiles"
SOURCE_DATASET_PROFILES_KEY = "source_dataset_profiles"


@dataclass(slots=True)
class SpiderPolicyProfile:
    name: str
    header_profile: dict[str, Any]
    ip_policy: dict[str, Any]
    behavior_policy: dict[str, Any]
    fingerprint_mode: str
    data_guard_policy: dict[str, Any]
    challenge_enabled: bool
    allowed_challenge_types: list[str]
    challenge_detector_ref: str
    solver_provider_ref: str
    max_challenge_attempts: int
    on_fail_action: str


class PolicyResolver:
    """Resolve anti-bot policy in precedence order: default < spider."""

    def __init__(
        self,
        default_profile: dict[str, Any],
        spider_profiles: dict[str, dict[str, Any]],
    ) -> None:
        self._validate_allowed_types("ANTIBOT_DEFAULT_PROFILE", default_profile)
        for spider_name, spider_profile in spider_profiles.items():
            self._validate_allowed_types(
                f"ANTIBOT_SPIDER_PROFILES[{spider_name}]",
                spider_profile,
            )
            self._validate_dimension_profiles(
                profile_name=f"ANTIBOT_SPIDER_PROFILES[{spider_name}]",
                spider_profile=spider_profile,
            )
        self.default_profile = default_profile
        self.spider_profiles = spider_profiles

    @classmethod
    def from_settings(cls, settings: Any) -> PolicyResolver:
        default_profile = settings.getdict("ANTIBOT_DEFAULT_PROFILE", {})
        spider_profiles = settings.getdict("ANTIBOT_SPIDER_PROFILES", {})
        return cls(default_profile=default_profile, spider_profiles=spider_profiles)

    def resolve(
        self,
        spider_name: str,
        source: str = "",
        dataset: str = "",
    ) -> SpiderPolicyProfile:
        merged: dict[str, Any] = dict(self.default_profile)
        spider_profile = self.spider_profiles.get(spider_name, {})
        merged.update(self._base_spider_profile(spider_profile))

        normalized_source = source.strip().lower()
        normalized_dataset = dataset.strip().lower()
        source_profile = self._get_source_profile(spider_profile, normalized_source)
        merged.update(source_profile)
        source_dataset_profile = self._get_source_dataset_profile(
            spider_profile=spider_profile,
            source=normalized_source,
            dataset=normalized_dataset,
        )
        merged.update(source_dataset_profile)

        raw_allowed = merged.get("allowed_challenge_types", [])
        allowed_types = self._normalize_allowed_types(raw_allowed)

        return SpiderPolicyProfile(
            name=spider_name,
            header_profile=dict(merged.get("header_profile", {})),
            ip_policy=dict(merged.get("ip_policy", {})),
            behavior_policy=dict(merged.get("behavior_policy", {})),
            fingerprint_mode=str(merged.get("fingerprint_mode", "web_only")),
            data_guard_policy=dict(merged.get("data_guard_policy", {})),
            challenge_enabled=bool(merged.get("challenge_enabled", False)),
            allowed_challenge_types=allowed_types,
            challenge_detector_ref=str(merged.get("challenge_detector_ref", "")),
            solver_provider_ref=str(merged.get("solver_provider_ref", "")),
            max_challenge_attempts=int(merged.get("max_challenge_attempts", 1)),
            on_fail_action=str(merged.get("on_fail_action", "pause")),
        )

    def _base_spider_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in profile.items()
            if key not in {SOURCE_PROFILES_KEY, SOURCE_DATASET_PROFILES_KEY}
        }

    def _get_source_profile(
        self,
        spider_profile: dict[str, Any],
        source: str,
    ) -> dict[str, Any]:
        if not source:
            return {}
        source_profiles = spider_profile.get(SOURCE_PROFILES_KEY, {})
        if not isinstance(source_profiles, dict):
            return {}
        profile = source_profiles.get(source)
        if not isinstance(profile, dict):
            return {}
        return dict(profile)

    def _get_source_dataset_profile(
        self,
        spider_profile: dict[str, Any],
        source: str,
        dataset: str,
    ) -> dict[str, Any]:
        if not source or not dataset:
            return {}
        source_dataset_profiles = spider_profile.get(SOURCE_DATASET_PROFILES_KEY, {})
        if not isinstance(source_dataset_profiles, dict):
            return {}
        key = f"{source}:{dataset}"
        profile = source_dataset_profiles.get(key)
        if not isinstance(profile, dict):
            return {}
        return dict(profile)

    def _validate_allowed_types(self, profile_name: str, profile: dict[str, Any]) -> None:
        if "allowed_challenge_types" not in profile:
            return
        _ = self._normalize_allowed_types(
            profile.get("allowed_challenge_types"),
            profile_name=profile_name,
        )

    def _normalize_allowed_types(
        self,
        value: Any,
        profile_name: str = "policy",
    ) -> list[str]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(
                f"{profile_name}.allowed_challenge_types must be list[str], got {type(value)!r}",
            )

        normalized = [str(item).strip().lower() for item in value]
        invalid = [item for item in normalized if item not in ALLOWED_CHALLENGE_TYPES]
        if invalid:
            allowed = ", ".join(sorted(ALLOWED_CHALLENGE_TYPES))
            items = ", ".join(invalid)
            raise ValueError(
                f"{profile_name}.allowed_challenge_types contains invalid values: "
                f"{items}. Allowed values: {allowed}",
            )
        return normalized

    def _validate_dimension_profiles(
        self,
        profile_name: str,
        spider_profile: dict[str, Any],
    ) -> None:
        source_profiles = spider_profile.get(SOURCE_PROFILES_KEY, {})
        if source_profiles and not isinstance(source_profiles, dict):
            raise ValueError(f"{profile_name}.{SOURCE_PROFILES_KEY} must be dict[str, dict]")
        if isinstance(source_profiles, dict):
            for source, profile in source_profiles.items():
                if not isinstance(profile, dict):
                    raise ValueError(
                        f"{profile_name}.{SOURCE_PROFILES_KEY}[{source!r}] "
                        "must be dict[str, object]",
                    )
                self._validate_allowed_types(
                    f"{profile_name}.{SOURCE_PROFILES_KEY}[{source!r}]",
                    profile,
                )

        source_dataset_profiles = spider_profile.get(SOURCE_DATASET_PROFILES_KEY, {})
        if source_dataset_profiles and not isinstance(source_dataset_profiles, dict):
            raise ValueError(
                f"{profile_name}.{SOURCE_DATASET_PROFILES_KEY} must be dict[str, dict]",
            )
        if isinstance(source_dataset_profiles, dict):
            for source_dataset, profile in source_dataset_profiles.items():
                if not isinstance(profile, dict):
                    raise ValueError(
                        f"{profile_name}.{SOURCE_DATASET_PROFILES_KEY}[{source_dataset!r}] "
                        "must be dict[str, object]",
                    )
                self._validate_allowed_types(
                    f"{profile_name}.{SOURCE_DATASET_PROFILES_KEY}[{source_dataset!r}]",
                    profile,
                )
