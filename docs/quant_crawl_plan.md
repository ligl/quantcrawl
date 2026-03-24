## 多数据域量化采集平台计划 v8（Pythonic + Scrapy 原生工作流优先）

### Summary
- 全部实现遵循 Pythonic 设计与 Scrapy 官方规范，优先复用 Scrapy 原生机制（`settings/middlewares/pipelines/extensions/signals`）。
- 反爬能力不侵入 spider 主逻辑，不改写调度主流程，统一通过中间件与动态配置生效。
- 支持分布式（Redis）、多数据域、每 spider 策略编排、默认 SQLite（可切 PostgreSQL）、Scrapyd + ScrapydWeb 运维。

### Terminology
- `source`：数据来源（站点/系统），例如 `czce`、`binance`、`eastmoney`。
- `dataset`：来源下的数据主题（具体数据集），例如 `exchange_notice`、`funding_rate`、`kline_1m`。
- 三维解析：按 `spider + source + dataset` 解析策略，优先级从高到低建议为：
  - `spider + source + dataset`
  - `spider + source`
  - `spider`
  - 全局默认
- 示例 1：同一 spider 下，`source=czce,dataset=exchange_notice` 与 `source=czce,dataset=quote` 可使用不同策略。
- 示例 2：同一 `source=binance` 下，`dataset=funding_rate` 与 `dataset=order_book_snapshot` 可配置不同挑战与节律策略。

### Scope Constraint
- 脚手架仓库只包含“框架本身所需能力”：配置层、采集基类、策略中间件、Pipeline、扩展、工具、测试与运维模板。
- 具体业务内容不进入脚手架主干代码；仅保留 1 个 `demo` spider 用于链路验证与开发示例。
- 任何交易所/站点/数据域的业务解析逻辑，均作为后续独立业务模块或私有项目接入，不在框架模板中固化。
- spider 级私有逻辑采用 job 内聚目录：`quantcrawl/jobs/<job_name>/`，每个 job 自包含 `spider/item/loader/pipeline/config`。

### Key Changes
1. Scrapy 原生优先架构
- Spider 只负责“提取与产出 Item”，不承载反爬细节。
- 反爬策略全部放在 Downloader/Spider Middleware 与 Extension 中。
- 数据清洗、校验、去重、存储严格走 Pipeline 链。
- 监控与告警通过 Extension + Signal 回调实现，不在业务代码中散落埋点。

2. 反爬以中间件与动态配置驱动
- 新增 `PolicyResolver`：运行时按 `spider.name + source + dataset` 解析策略。
- 反爬插件化中间件（可启停、可排序）：
  - 请求头策略（UA/Referer/Accept 一致性）
  - IP/代理与限流策略
  - 行为节律策略（随机抖动、请求节奏）
  - 指纹通道策略（web/hybrid/browser 切换）
  - 数据完整性策略（签名/Cookie/session 校验钩子）
- 所有策略参数来自 settings/配置中心，不硬编码在 spider 内。

3. Pythonic 代码规范与可维护性
- 面向协议与小接口（`Protocol/ABC`）而非巨型类。
- 单一职责：一个组件只做一件事（resolver、middleware、notifier、storage adapter 分离）。
- 显式类型注解、清晰异常层次、最小副作用函数。
- 配置对象化（`pydantic-settings`）+ 依赖注入风格，减少全局状态耦合。

4. 挑战处理能力（接口预留，非内置实现）
- 已提供 `SolverProvider` 抽象接口与 `ChallengeOrchestrator` 状态机。
- challenge 能力按子包收敛（协议/编排器/加载器），保持 spider 非侵入。
- 挑战检测通过中间件调用编排器，不改 Scrapy 核心流程。
- 已支持通过 `CHALLENGE_PROVIDER_REGISTRY/CHALLENGE_PROVIDER_CONFIGS` 进行 provider 配置注入（注册表 + JSON 参数）。
- 具体 provider 仍由业务侧实现并放在可导入路径中（框架不内置破解实现）。

### Public Interfaces / Types
- `DomainSpec`：数据域声明（Item/Loader/Pipeline/PolicyRef）。
- `SpiderPolicyProfile`：每 spider 策略编排入口。
- `PolicyResolver`：动态解析策略。
- `PolicyPlugin`：中间件策略插件接口。
- `SolverProvider` / `ChallengeOrchestrator`：验证码能力抽象接口。
- `StorageRouter`：SQLite/PostgreSQL 路由。
- `Notifier`：Email/飞书/钉钉统一告警接口。

### Backlog（未实现功能清单）
> 说明：本清单是未实现项的单一事实来源。每次迭代只允许 1 个 ID 进入 `进行中`。

| ID | 功能项 | 当前状态 | 验收标准 | 关联测试 |
|---|---|---|---|---|
| BKL-002 | `PolicyPlugin` 插件总线接线 | 未实现 | 可通过“新增插件 + 配置注册”接入，不改业务 spider | 插件装配/执行链单测 + 中间件回归 |
| BKL-003 | 行为节律策略中间件 | 未实现 | 支持请求节奏/jitter 配置并可按 spider 启停 | middleware 单测 + 冒烟 |
| BKL-004 | 指纹通道策略切换（`web/hybrid/browser`） | 未实现 | `fingerprint_mode` 在运行时生效并可观测 | 策略切换单测 + 冒烟 |
| BKL-005 | `DomainSpec` 接线到 job 装配流程 | 未实现 | `DomainSpec` 进入 job 装配与策略引用链路 | loader/resolver 集成用例 |
| BKL-006 | 分布式+运维模板（`scrapy-redis`/Scrapyd/ScrapydWeb） | 未实现 | 提供可运行模板与最小集成冒烟命令 | 分布式启动冒烟 + 文档示例验证 |

### Execution Rule（实现一个、清除一个）
- 每次迭代只允许一个 Backlog ID 进入 `进行中`，其余保持 `未实现`。
- 功能代码完成并通过门禁后，从“未实现”迁移到“已完成记录”。
- 未通过验收不得改状态，避免“假完成”。
- 固定门禁命令：
  - `uv run --extra dev python -m ruff check .`
  - `uv run --extra dev python -m pytest`
  - `uv run python -m scrapy list`

### First Phase Sequence（最小风险顺序）
1. `BKL-002` PolicyPlugin 插件总线
2. `BKL-003` 行为节律策略 + `BKL-004` 指纹通道策略
3. `BKL-005` DomainSpec 接线 + `BKL-006` 分布式运维模板

### Completion Log（已完成记录）
| 日期 | ID | 变更点 | 验证命令 | 结果摘要 |
|---|---|---|---|---|
| 2026-03-25 | BKL-001 | `PolicyResolver` 支持 `spider + source + dataset` 三维解析（默认 -> spider -> source -> source+dataset）；`PolicyBindingMiddleware` 传入 source/dataset；补齐三维解析与维度配置校验测试 | `uv run --extra dev python -m ruff check .` ; `uv run --extra dev python -m pytest` ; `uv run python -m scrapy list` | 全部通过 |

### Test Plan
- 单元测试
  - `PolicyResolver` 合并优先级（全局/域级/spider 级）
  - 各反爬中间件独立行为与链式组合
  - Pipeline 契约（清洗 -> 校验 -> 去重 -> 存储）
  - 挑战状态机（mock provider）
- 集成冒烟
  - 单机与分布式（scrapy-redis）两种模式
  - 策略按 spider 动态启停与顺序变更
  - 异常场景（429/403/挑战页）下不破坏 Scrapy 主流程（请求、重试、落库、统计仍可控）
- 验收标准
  - 新策略通过“新增插件 + 配置注册”接入，无需改业务 spider
  - 关闭某策略后爬虫仍按 Scrapy 原生流程稳定运行
  - 代码风格与结构满足 Pythonic/Scrapy 规范审查

### Assumptions
- 你的要求“每 spider 自由启用策略”保留；同时建议加审计日志以便治理。
- 默认开发用 SQLite，生产分布式推荐 PostgreSQL。
- 如果我由于各种原因不能实现具体验证码破解代码，需要保留可插拔接口与流程。
- Backlog 状态仅在本文件维护；“清除一个”指从未实现清单迁移到完成记录，而非删除历史。
