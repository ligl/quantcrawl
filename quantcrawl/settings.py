from __future__ import annotations

from .config import get_app_settings
from .job_loader import build_spider_pipelines, build_spider_profiles

app = get_app_settings()

BOT_NAME = "quantcrawl"

SPIDER_MODULES = ["quantcrawl.jobs"]
NEWSPIDER_MODULE = "quantcrawl.jobs"

ROBOTSTXT_OBEY = False
COOKIES_ENABLED = True
TELNETCONSOLE_ENABLED = False

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"

DOWNLOAD_TIMEOUT = app.request_timeout_seconds
RETRY_ENABLED = True
RETRY_TIMES = app.retry_times
DOWNLOAD_DELAY = app.default_download_delay
RANDOMIZE_DOWNLOAD_DELAY = True
CONCURRENT_REQUESTS = 16

DEFAULT_REQUEST_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en",
}

LOG_LEVEL = "INFO"
LOG_DIR = app.log_dir
LOG_MAX_BYTES = app.log_max_bytes
LOG_BACKUP_COUNT = app.log_backup_count

STORAGE_BACKEND = app.storage_backend
SQLITE_PATH = app.sqlite_path
POSTGRES_DSN = app.postgres_dsn

DEFAULT_UA_PLATFORM = app.default_ua_platform

ALERT_EMAIL_ENABLED = app.alert_email_enabled
ALERT_EMAIL_TO = app.alert_email_to
ALERT_EMAIL_FROM = app.alert_email_from
SMTP_HOST = app.smtp_host
SMTP_PORT = app.smtp_port
SMTP_USER = app.smtp_user
SMTP_PASSWORD = app.smtp_password

ALERT_FEISHU_ENABLED = app.alert_feishu_enabled
ALERT_FEISHU_WEBHOOK = app.alert_feishu_webhook

ALERT_DINGTALK_ENABLED = app.alert_dingtalk_enabled
ALERT_DINGTALK_WEBHOOK = app.alert_dingtalk_webhook

CHALLENGE_PROVIDER_REGISTRY = app.challenge_provider_registry
CHALLENGE_PROVIDER_CONFIGS = app.challenge_provider_configs

ANTIBOT_DEFAULT_PROFILE = {
    "header_profile": {
        "platform": app.default_ua_platform,
        "accept": DEFAULT_REQUEST_HEADERS["Accept"],
        "accept_language": "en-US,en;q=0.9",
    },
    "ip_policy": {},
    "behavior_policy": {"jitter": True},
    "fingerprint_mode": "web_only",
    "data_guard_policy": {},
    "challenge_enabled": False,
    "allowed_challenge_types": [],
    "solver_provider_ref": "",
    "max_challenge_attempts": 1,
    "on_fail_action": "pause",
}

ANTIBOT_SPIDER_PROFILES = build_spider_profiles()

DOWNLOADER_MIDDLEWARES = {
    "quantcrawl.middlewares.policy_binding.PolicyBindingMiddleware": 80,
    "quantcrawl.middlewares.header_policy.HeaderPolicyMiddleware": 100,
    "quantcrawl.middlewares.proxy_policy.ProxyPolicyMiddleware": 110,
    "quantcrawl.middlewares.data_guard.DataGuardMiddleware": 120,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": 550,
    "quantcrawl.middlewares.challenge_detection.ChallengeDetectionMiddleware": 900,
}

ITEM_PIPELINES = {
    "quantcrawl.pipelines.validation.ValidationPipeline": 100,
    "quantcrawl.pipelines.dedup.DedupPipeline": 200,
    "quantcrawl.pipelines.storage_router.StorageRouterPipeline": 300,
}

SPIDER_ITEM_PIPELINES = build_spider_pipelines()
pipeline_conflicts = set(ITEM_PIPELINES).intersection(SPIDER_ITEM_PIPELINES)
if pipeline_conflicts:
    conflicts = ", ".join(sorted(pipeline_conflicts))
    raise ValueError(f"Spider pipeline conflicts with framework pipelines: {conflicts}")
ITEM_PIPELINES = {**ITEM_PIPELINES, **SPIDER_ITEM_PIPELINES}

EXTENSIONS = {
    "quantcrawl.spider_logging.SpiderLogHooks": 10,
    "quantcrawl.metrics.StatsMetricsHooks": 20,
    "quantcrawl.alerts.AlertHooks": 30,
}

# Distributed mode (optional, Redis-backed)
if app.distributed_enabled:
    SCHEDULER = "scrapy_redis.scheduler.Scheduler"
    DUPEFILTER_CLASS = "scrapy_redis.dupefilter.RFPDupeFilter"
    REDIS_URL = app.redis_url

FEED_EXPORT_ENCODING = "utf-8"
