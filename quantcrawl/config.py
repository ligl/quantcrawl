from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import dotenv_values
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore", env_prefix="")

    app_env: Literal["dev", "staging", "prod"] = "dev"

    storage_backend: Literal["sqlite", "postgres"] = "sqlite"
    sqlite_path: str = "data/quantcrawl.db"
    postgres_dsn: str = ""

    distributed_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"

    log_dir: str = "logs"
    log_max_bytes: int = 20 * 1024 * 1024
    log_backup_count: int = 10

    alert_email_enabled: bool = False
    alert_email_to: str = ""
    alert_email_from: str = ""
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""

    alert_feishu_enabled: bool = False
    alert_feishu_webhook: str = ""

    alert_dingtalk_enabled: bool = False
    alert_dingtalk_webhook: str = ""

    default_ua_platform: str = "desktop"

    default_download_delay: float = 0.25
    max_download_delay: float = 3.0

    request_timeout_seconds: int = 20
    retry_times: int = 3

    antibot_default_profile: dict[str, object] = Field(default_factory=dict)
    antibot_spider_profiles: dict[str, dict[str, object]] = Field(default_factory=dict)
    challenge_provider_registry: dict[str, str] = Field(default_factory=dict)
    challenge_provider_configs: dict[str, dict[str, object]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_conditional_required_fields(self) -> AppSettings:
        missing: list[str] = []

        if self.storage_backend == "postgres" and not self.postgres_dsn.strip():
            missing.append("POSTGRES_DSN (required when STORAGE_BACKEND=postgres)")

        if self.distributed_enabled and not self.redis_url.strip():
            missing.append("REDIS_URL (required when DISTRIBUTED_ENABLED=true)")

        if self.alert_email_enabled:
            email_required = {
                "ALERT_EMAIL_TO": self.alert_email_to,
                "ALERT_EMAIL_FROM": self.alert_email_from,
                "SMTP_HOST": self.smtp_host,
                "SMTP_USER": self.smtp_user,
                "SMTP_PASSWORD": self.smtp_password,
            }
            for key, value in email_required.items():
                if not str(value).strip():
                    missing.append(f"{key} (required when ALERT_EMAIL_ENABLED=true)")
            if self.smtp_port <= 0:
                missing.append("SMTP_PORT (must be > 0 when ALERT_EMAIL_ENABLED=true)")

        if self.alert_feishu_enabled and not self.alert_feishu_webhook.strip():
            missing.append(
                "ALERT_FEISHU_WEBHOOK (required when ALERT_FEISHU_ENABLED=true)"
            )

        if self.alert_dingtalk_enabled and not self.alert_dingtalk_webhook.strip():
            missing.append(
                "ALERT_DINGTALK_WEBHOOK (required when ALERT_DINGTALK_ENABLED=true)"
            )

        unknown_provider_refs = set(self.challenge_provider_configs).difference(
            self.challenge_provider_registry,
        )
        if unknown_provider_refs:
            refs = ", ".join(sorted(unknown_provider_refs))
            missing.append(
                "CHALLENGE_PROVIDER_CONFIGS contains unknown provider_ref(s): "
                f"{refs}. Please define them in CHALLENGE_PROVIDER_REGISTRY first.",
            )

        if missing:
            raise ValueError("Invalid configuration:\n- " + "\n- ".join(missing))

        return self


def _load_env() -> None:
    base_values = {
        key: value
        for key, value in dotenv_values(".env").items()
        if value is not None
    }
    env = os.getenv("APP_ENV") or base_values.get("APP_ENV") or "dev"
    env_values = {
        key: value
        for key, value in dotenv_values(f".env.{env}").items()
        if value is not None
    }

    merged = {**base_values, **env_values}
    for key, value in merged.items():
        # Keep process-level env vars as highest priority.
        os.environ.setdefault(key, value)


@lru_cache(maxsize=1)
def get_app_settings() -> AppSettings:
    _load_env()
    settings = AppSettings()

    Path(settings.log_dir).mkdir(parents=True, exist_ok=True)
    if settings.storage_backend == "sqlite":
        Path(settings.sqlite_path).parent.mkdir(parents=True, exist_ok=True)

    return settings
