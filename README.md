# QuantCrawl

A Quantitative Trading System Data Collection Platform Based on Scrapy.


## Quick start

```bash
uv sync
uv run scrapy list
```

## Environment

Copy `.env.example` to `.env.dev` and adjust values.

```bash
cp .env.example .env.dev
```

Set runtime env:

```bash
export APP_ENV=dev
uv run scrapy crawl demo_spider
```

### Config conventions

- Environment naming: `.env.dev`, `.env.staging`, `.env.prod` (selected by `APP_ENV`).
- Recommended local usage: keep shared defaults in `.env`, keep environment-specific values in `.env.<APP_ENV>`.
- Recommended CI/CD usage: inject sensitive variables from the deployment system environment, do not commit them into repo files.
- Config precedence (high to low): process environment variables > `.env.<APP_ENV>` > `.env` > code defaults.

Examples:

```bash
# staging
export APP_ENV=staging
uv run scrapy list

# production
export APP_ENV=prod
uv run scrapy crawl demo_spider
```

Challenge provider injection (optional):

```bash
export CHALLENGE_PROVIDER_REGISTRY='{"demo":"your_pkg.providers.DemoSolver"}'
export CHALLENGE_PROVIDER_CONFIGS='{"demo":{"api_key":"***"}}'
```

- `CHALLENGE_PROVIDER_REGISTRY`: `provider_ref -> import.path.ClassName`
- `CHALLENGE_PROVIDER_CONFIGS`: `provider_ref -> kwargs`
- `CHALLENGE_PROVIDER_CONFIGS` 里的 `provider_ref` 必须先在 registry 中声明。

Provider implementation flow:

```python
from quantcrawl.challenge import ChallengeEvent


class DemoSolver:
    name = "demo"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def is_available(self) -> bool:
        return bool(self.api_key)

    def healthcheck(self) -> tuple[bool, str]:
        return (True, "ok") if self.api_key else (False, "missing_api_key")

    def solve(self, event: ChallengeEvent) -> bool:
        # call your solver backend here
        _ = event
        return True
```

Usage steps:
1. Implement your provider class (recommended methods: `is_available` / `healthcheck` / `solve`).
2. Register provider class path in `CHALLENGE_PROVIDER_REGISTRY`.
3. Inject provider kwargs in `CHALLENGE_PROVIDER_CONFIGS`.
4. In job config `POLICY_PROFILE`, set `challenge_enabled=true` and `solver_provider_ref=<provider_ref>`.

`allowed_challenge_types` (optional):
- Supported values: `captcha`, `slider`, `js_challenge`, `rate_limit`, `generic`.
- `[]` means allow all detected challenge types.
- Non-empty list means only listed types will enter solver orchestration.

Spider detector override (optional):
```python
POLICY_PROFILE = {
    "challenge_enabled": True,
    "solver_provider_ref": "demo",
    "allowed_challenge_types": ["captcha", "slider"],
    "challenge_detector_ref": "quantcrawl.jobs.demo_spider.detector.DemoSpiderDetector",
}
```

If `challenge_detector_ref` is configured for a spider, that detector is used for that spider.
If not configured, the framework uses the built-in `ChallengeDefaultDetector`.

## Distributed mode

Enable Redis scheduler/dupefilter in `.env.<env>`:

- `DISTRIBUTED_ENABLED=true`
- `REDIS_URL=redis://localhost:6379/0`

## Ops

- Scheduler/deploy: Scrapyd
- Web console: ScrapydWeb
- Metrics: `/metrics` (Prometheus endpoint extension)
- Alerts: Email / Feishu / DingTalk

## AI 协作上下文（重要）

为方便我和其他 AI 在本仓库中稳定协作，请先阅读并遵循：

- [docs/project_spec.md](docs/project_spec.md)
- [docs/quant_crawl_plan.md](docs/quant_crawl_plan.md)

该文档是当前项目的主计划与约束基线，包含以下关键上下文：

- 架构原则：Pythonic + Scrapy 原生工作流优先（`settings/middlewares/pipelines/extensions/signals`）。
- 范围边界：脚手架仅保留框架能力，业务站点/交易所解析逻辑不进入主干。
- 实现方式：反爬通过中间件和动态配置驱动，不侵入 spider 主逻辑。
- 运维与演进：支持分布式、监控告警、存储路由与后续可插拔扩展。

对 AI 协作的约定：

- 新增或修改代码前，先对齐该计划文档中的 `Scope Constraint` 与 `Key Changes`。
- 如实现与计划冲突，优先保持“非侵入 spider、配置驱动、可插拔”的方向。
- 涉及任务私有逻辑时，保持模块隔离，避免把业务规则固化到框架通用层。

## 新增任务流程

当需要添加一个新采集任务（新 spider）时，按下面流程执行：

快速生成模板（推荐）：

```bash
./scripts/new_job.sh <job_name>
# 例如
./scripts/new_job.sh funding_rate
```

1. 明确任务范围
- 定义 `source`、`dataset`、抓取频率、输入入口（网页/API）和验收标准。
- 确认该任务属于“框架可复用能力”还是“业务私有逻辑”（业务逻辑请放独立模块，不固化在脚手架主干）。

2. 配置与策略
- 在 `quantcrawl/jobs/<spider_name>/config.py` 中声明：
  - `SPIDER_NAME`
  - `POLICY_PROFILE`
  - `PIPELINES`
- 根据目标站点风险启用/调整中间件策略（Header、Proxy、DataGuard、ChallengeDetection）。

3. 实现 spider
- 在 `quantcrawl/jobs/<spider_name>/` 下维护 job 私有文件：
  - `spider.py`
  - `item.py`
  - `loader.py`
  - `pipeline.py`
  - `config.py`
- 在 spider 中仅引用该任务自己的 item/loader，不复用其他任务的业务字段定义。
- 在对应 `config.py` 的 `PIPELINES` 中注册该任务 pipeline。
- `parse_list` 输出框架必填字段（`source/dataset/event_time/collected_at/raw_payload_hash`）。
- 不要把任务专用规则写入框架通用层（middlewares/pipelines/loaders/items/spiders）。

4. 本地验证
- 运行 `uv run scrapy list` 确认 spider 已注册。
- 运行 `uv run scrapy crawl <spider_name>` 做链路冒烟。
- 运行 `uv run --extra dev pytest` 确认基础测试通过。

5. 上线准备
- 增加调度配置（Scrapyd/ScrapydWeb/Cron）。
- 检查日志、指标、告警是否生效（每 spider 独立日志 + Prometheus + 通知渠道）。
- 完成回滚方案与失败处置说明。
