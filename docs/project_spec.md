# QuantCrawl Project Spec

本文件用于统一管理 QuantCrawl 项目规范，作为我和其他 AI 在本仓库协作时的执行基线。
目标：提供可直接执行的 Python/Scrapy 最佳工程实践，减少人工逐条检查成本。

## 关联文档

- 项目入口与使用说明：[README.md](../README.md)
- 架构计划与范围约束：[quant_crawl_plan.md](./quant_crawl_plan.md)

协作顺序建议：

1. 先阅读 `README.md`，了解运行方式、环境约定与任务流程。
2. 再阅读 `docs/quant_crawl_plan.md`，对齐架构边界与设计方向。
3. 最后按本规范执行实现、测试、评审与发布。

## 1. 代码规范（Python）

### 1.1 命名与结构

- MUST：文件名使用 `snake_case`，类名使用 `PascalCase`，函数/变量使用 `snake_case`，常量使用 `UPPER_SNAKE_CASE`。
- MUST：一个模块只承担一个主职责，禁止把日志、指标、告警、业务解析混在同一文件。
- SHOULD：公共能力优先抽到稳定模块（如 `utils`），避免跨模块复制粘贴。

### 1.2 类型注解与契约

- MUST：对外函数、核心链路函数、构造函数、关键数据转换函数添加类型注解。
- MUST：优先使用精确类型（如 `dict[str, str]`、`list[int]`），避免滥用 `Any`。
- SHOULD：结构化输入输出使用 `dataclass/TypedDict/Protocol` 描述契约。
- SHOULD：复杂返回值使用专门类型而不是“多字段裸字典”。

### 1.3 错误处理与可维护性

- MUST：关键失败路径显式抛出带上下文信息的异常（fail-fast）。
- MUST：禁止吞异常且不记录；如果需降级处理，至少记录可定位日志。
- SHOULD：保持函数短小，控制副作用；I/O 与纯逻辑尽量分离，便于测试。

### 1.4 代码风格与静态检查

- MUST：提交前通过 Ruff：`uv run --extra dev python -m ruff check .`。
- MUST：修复导入顺序、未使用符号、长行、可疑语法等 lint 问题。
- SHOULD：新增代码保持与项目当前风格一致，优先可读性而非“技巧性写法”。

## 2. 配置规范

### 2.1 多环境与分离策略

- MUST：使用 `APP_ENV=dev|staging|prod`。
- MUST：环境文件命名统一为 `.env.dev`、`.env.staging`、`.env.prod`。
- MUST：加载优先级固定为：进程环境变量 > `.env.<APP_ENV>` > `.env` > 代码默认值。
- SHOULD：`.env` 放公共默认值，`.env.<APP_ENV>` 放环境差异值。

### 2.2 敏感信息与校验

- MUST：密钥/密码/令牌不进入仓库，不写入 `.env.example`。
- MUST：配置在应用启动阶段执行条件必填校验并 fail-fast（如 Postgres/Redis/告警）。
- MUST：校验错误信息要包含“缺失项 + 条件”，便于快速定位。
- SHOULD：生产环境全部敏感配置由部署系统注入。

### 2.3 Challenge Provider 注入规范

- MUST：使用 `CHALLENGE_PROVIDER_REGISTRY`（JSON）声明 provider 注册表：`provider_ref -> import.path.ClassName`。
- MUST：使用 `CHALLENGE_PROVIDER_CONFIGS`（JSON）声明 provider 初始化参数：`provider_ref -> kwargs`。
- MUST：`CHALLENGE_PROVIDER_CONFIGS` 中的 `provider_ref` 必须在 registry 中存在，否则启动 fail-fast。
- MUST：provider 类必须实现 `solve(event)`；推荐实现 `is_available()` 与 `healthcheck()` 用于运行时可用性治理。
- MUST：导入失败、构造失败、协议不匹配均在启动阶段报错。
- SHOULD：provider 凭据通过环境变量注入，不写入仓库文件。
- MUST：`allowed_challenge_types` 仅允许 `captcha|slider|js_challenge|rate_limit|generic`，空列表表示允许全部。
- SHOULD：特殊站点可在 spider policy 中配置 `challenge_detector_ref` 覆盖默认检测器；未配置时使用框架默认规则检测器。

## 3. 测试规范（pytest + Scrapy）

### 3.1 单元测试

- MUST：覆盖配置解析、策略解析、中间件行为、Pipeline 契约、扩展信号处理。
- MUST：单元测试可重复、无外部网络依赖、可并行执行。
- SHOULD：按行为命名测试函数，明确输入与预期输出。

### 3.2 集成与冒烟

- MUST：至少覆盖以下命令链路：
  - `uv run --extra dev python -m pytest`
  - `APP_ENV=dev|staging|prod uv run python -m scrapy list`
  - `uv run python -m scrapy crawl demo_spider -s CLOSESPIDER_TIMEOUT=1`
- SHOULD：验证核心路径“请求 -> 解析 -> pipeline -> 存储/日志/指标/告警”不报错。

### 3.3 Mock 策略

- MUST：DB/Webhook/第三方服务默认 mock，避免测试不稳定。
- SHOULD：真实集成测试单独标识并与常规单测隔离。

## 4. 文档规范

### 4.1 README 规范

- MUST：README 维护项目入口、快速启动、环境配置、任务新增流程。
- MUST：路径变化、命令变化、配置键变化后同步更新 README。

### 4.2 设计与接口文档

- MUST：对外扩展点（settings 键、插件接口、公共类型）提供最小可用文档。
- SHOULD：架构变更同步更新 `docs/quant_crawl_plan.md` 与本文件。

### 4.3 变更记录

- MUST：破坏性变更、配置语义变更、运行行为变更需记录。
- SHOULD：维护 `CHANGELOG.md`；若暂未维护，则在 PR 描述完整记录影响面与迁移方式。

## 5. 架构规范

### 5.1 Scrapy 分层职责

- MUST：`jobs/<job_name>/spider.py` 负责抓取入口与字段提取，不承载反爬细节。
- MUST：`middlewares` 负责请求/响应策略与反爬行为。
- MUST：`pipelines` 负责清洗、校验、去重、存储。
- MUST：扩展模块（如 `spider_logging.py`、`metrics.py`、`alerts.py`）只做观测/运维职责。

### 5.2 模块边界

- MUST：禁止跨层“反向依赖”污染（例如 `utils` 依赖业务层）。
- MUST：job 私有逻辑（item/loader/pipeline/config）放在 `quantcrawl/jobs/<job_name>/` 内聚管理。
- MUST：框架通用层（`middlewares`、通用 pipeline、`utils`、`BaseSpider`）不得下沉到 job 私有目录。
- SHOULD：新增能力优先“新增模块 + settings 注册”接入，降低回归风险。
- SHOULD：公共接口保持稳定，破坏性变更提供迁移说明。

### 5.3 接口设计原则

- MUST：配置驱动优先，避免在 spider 中硬编码环境差异策略。
- MUST：新接口需定义输入、输出、失败行为与默认值。
- SHOULD：对关键配置提供合理默认值与显式校验。

## 6. 流程规范

### 6.1 Git 工作流

- MUST：一次变更只解决一个主题，保持可审查粒度。
- SHOULD：分支命名使用 `feat/*`、`fix/*`、`chore/*`。

### 6.2 Code Review

- MUST：审查正确性、回归风险、测试覆盖、文档更新是否齐全。
- MUST：阻断项修复后才可合并。
- SHOULD：评审意见聚焦可执行建议，减少含糊描述。

### 6.3 版本管理

- SHOULD：遵循 SemVer 思路管理兼容性。
- MUST：破坏性变更必须声明影响面和迁移路径。

## 7. 安全规范

### 7.1 敏感信息

- MUST：密钥、密码、Token、DSN 不得写入仓库与日志。
- MUST：示例文档与示例配置使用占位符。

### 7.2 权限与数据保护

- MUST：生产凭据遵循最小权限原则。
- SHOULD：日志与告警对敏感字段进行脱敏输出。
- SHOULD：导出/共享数据前进行脱敏检查。

## 8. 运维规范

### 8.1 日志规范

- MUST：按 spider 维度可追踪，关键字段统一（spider/source/dataset/trace）。
- MUST：使用滚动日志，避免单文件无限增长。

### 8.2 监控与告警

- MUST：至少监控请求量、错误量、挑战命中、产出量。
- SHOULD：告警按环境分级，避免开发告警干扰生产。

### 8.3 部署规范

- MUST：部署前通过最小检查：
  - `uv run --extra dev python -m ruff check .`
  - `uv run --extra dev python -m pytest`
  - `APP_ENV=<env> uv run python -m scrapy list`
- MUST：发布方案包含回滚与故障处置说明。

## 9. AI 协作附加约定

- MUST：AI 修改代码前必须先对齐 `README.md` 与本文件。
- MUST：当实现与 `quant_crawl_plan.md` 冲突时，优先遵守架构边界并显式说明取舍。
- MUST：AI 交付说明至少包含：
  - 改动摘要（做了什么）
  - 风险说明（可能影响什么）
  - 验证结果（跑了哪些检查）
