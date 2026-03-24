from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from quantcrawl.config import get_app_settings


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


@pytest.fixture(autouse=True)
def _clear_settings_cache() -> None:
    get_app_settings.cache_clear()
    yield
    get_app_settings.cache_clear()


def _clear_known_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in [
        "APP_ENV",
        "STORAGE_BACKEND",
        "SQLITE_PATH",
        "POSTGRES_DSN",
        "DISTRIBUTED_ENABLED",
        "REDIS_URL",
        "LOG_DIR",
        "ALERT_EMAIL_ENABLED",
        "ALERT_EMAIL_TO",
        "ALERT_EMAIL_FROM",
        "SMTP_HOST",
        "SMTP_PORT",
        "SMTP_USER",
        "SMTP_PASSWORD",
        "ALERT_FEISHU_ENABLED",
        "ALERT_FEISHU_WEBHOOK",
        "ALERT_DINGTALK_ENABLED",
        "ALERT_DINGTALK_WEBHOOK",
        "DEFAULT_UA_PLATFORM",
        "CHALLENGE_PROVIDER_REGISTRY",
        "CHALLENGE_PROVIDER_CONFIGS",
    ]:
        monkeypatch.delenv(key, raising=False)


@pytest.mark.parametrize(
    ("env_name", "ua_platform"),
    [
        ("dev", "dev_ua"),
        ("staging", "staging_ua"),
        ("prod", "prod_ua"),
    ],
)
def test_loads_env_file_by_app_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    ua_platform: str,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", env_name)

    _write(tmp_path / ".env", "DEFAULT_UA_PLATFORM=base_ua\n")
    _write(tmp_path / f".env.{env_name}", f"DEFAULT_UA_PLATFORM={ua_platform}\n")

    settings = get_app_settings()
    assert settings.app_env == env_name
    assert settings.default_ua_platform == ua_platform


def test_process_env_has_highest_priority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.setenv("DEFAULT_UA_PLATFORM", "process_ua")

    _write(tmp_path / ".env", "DEFAULT_UA_PLATFORM=base_ua\n")
    _write(tmp_path / ".env.dev", "DEFAULT_UA_PLATFORM=env_ua\n")

    settings = get_app_settings()
    assert settings.default_ua_platform == "process_ua"


def test_raises_when_postgres_enabled_without_dsn(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(tmp_path / ".env.dev", "STORAGE_BACKEND=postgres\nPOSTGRES_DSN=\n")

    with pytest.raises(ValidationError, match="POSTGRES_DSN"):
        get_app_settings()


def test_raises_when_distributed_enabled_without_redis_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(tmp_path / ".env.dev", "DISTRIBUTED_ENABLED=true\nREDIS_URL=\n")

    with pytest.raises(ValidationError, match="REDIS_URL"):
        get_app_settings()


def test_raises_when_email_alert_enabled_with_missing_smtp_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(
        tmp_path / ".env.dev",
        "\n".join(
            [
                "ALERT_EMAIL_ENABLED=true",
                "ALERT_EMAIL_TO=",
                "ALERT_EMAIL_FROM=",
                "SMTP_HOST=",
                "SMTP_PORT=0",
                "SMTP_USER=",
                "SMTP_PASSWORD=",
            ]
        )
        + "\n",
    )

    with pytest.raises(ValidationError, match="ALERT_EMAIL_TO|SMTP_HOST|SMTP_PORT"):
        get_app_settings()


def test_raises_when_feishu_alert_enabled_without_webhook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(tmp_path / ".env.dev", "ALERT_FEISHU_ENABLED=true\nALERT_FEISHU_WEBHOOK=\n")

    with pytest.raises(ValidationError, match="ALERT_FEISHU_WEBHOOK"):
        get_app_settings()


def test_raises_when_dingtalk_alert_enabled_without_webhook(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(
        tmp_path / ".env.dev",
        "ALERT_DINGTALK_ENABLED=true\nALERT_DINGTALK_WEBHOOK=\n",
    )

    with pytest.raises(ValidationError, match="ALERT_DINGTALK_WEBHOOK"):
        get_app_settings()


def test_raises_when_challenge_provider_configs_has_unknown_provider_ref(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(
        tmp_path / ".env.dev",
        (
            'CHALLENGE_PROVIDER_REGISTRY={"demo":"quantcrawl.tests.Demo"}\n'
            'CHALLENGE_PROVIDER_CONFIGS={"unknown":{"api_key":"x"}}\n'
        ),
    )

    with pytest.raises(
        ValidationError,
        match="CHALLENGE_PROVIDER_CONFIGS contains unknown provider_ref",
    ):
        get_app_settings()


def test_loads_challenge_provider_registry_and_configs_from_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_known_env(monkeypatch)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_ENV", "dev")
    _write(
        tmp_path / ".env.dev",
        (
            'CHALLENGE_PROVIDER_REGISTRY={"demo":"quantcrawl.tests.Demo"}\n'
            'CHALLENGE_PROVIDER_CONFIGS={"demo":{"api_key":"x"}}\n'
        ),
    )

    settings = get_app_settings()
    assert settings.challenge_provider_registry == {"demo": "quantcrawl.tests.Demo"}
    assert settings.challenge_provider_configs == {"demo": {"api_key": "x"}}
