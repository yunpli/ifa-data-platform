# LOWFREQ_OPERATIONS_GUIDE.md

> 强制规则：每次新 session 在处理 iFA lowfreq 相关工作前，先读取 `IFA_PROJECT_CONTEXT.md`，再读取本文件。

## 1. lowfreq 系统是什么

iFA lowfreq 是 iFA 项目的第一阶段数据底座，负责把 A 股低频数据收成一套可运行、可维护、可查询、可版本化的 ingestion 系统。

它覆盖的核心能力包括：
- `symbol_universe` 驱动的采集范围控制
- source / raw mirror
- canonical current tables
- history / version 保留与切换
- daemon / group / state / health
- 基础 runbook / 文档 / summary 入口

它的目标不是做策略或信号，而是为后续中频 / 高频提供统一的数据与运行基座。

---

## 2. 当前完成到什么程度

当前按第一阶段收口基线理解：

- Job 1–10A 已完成或完成主体
- lowfreq framework 已建立
- current / history / version 机制已建立
- daemon 已可运行
- Universe（A / B / C）已建立
- lowfreq 已从全市场模式切到 Universe 驱动模式

当前 lowfreq 的职责是：
- 慢变量
- 文档 / 公告 /基础表
- 资产层与低频结构化数据

当前不做：
- 中频开发
- 高频开发
- facts / signals
- 另起一套 runtime / ingestion 体系

---

## 3. A / B / C Universe 怎么工作

### 定义
- A：高频
- B：中频
- C：低频

### 关系
- `A ⊂ B ⊂ C`

### 采集边界
- 低频只读 C
- 中频只读 B
- 高频只读 A
- 不允许回到全市场采集

### 当前 lowfreq 规则
lowfreq 所有按股票循环的 dataset，必须从 `ifa2.symbol_universe` 中读取 `universe_type='C'` 的有效 symbol。

### 强制约束
- 不允许跳过 `symbol_universe`
- 不允许直接跑全市场股票清单
- 不允许让 lowfreq 再回退到旧的全市场模式

---

## 4. symbol_universe 怎么维护

### 数据表
- 数据库：`ifa_db`
- schema：`ifa2`
- 表：`ifa2.symbol_universe`

### 关键字段
- `symbol`
- `name`
- `universe_type` (`A` / `B` / `C`)
- `is_active`
- `source`

### CLI
当前 repo 中提供：
- `scripts/symbol_universe_cli.py`

常见操作：
- seed 初始 Universe
- list 查看 A/B/C
- add 增加 symbol
- remove 停用 symbol
- move 在 A/B/C 之间迁移

### 维护原则
- lowfreq 只消费 C
- 调整 Universe 时优先改 `symbol_universe`，不要在 dataset 代码里硬编码名单
- 不要制造多份 Universe 来源

---

## 5. lowfreq daemon 怎么启动 / 停止 / 查看状态

### 启动方式
在 repo 根目录执行：

```bash
python -m ifa_data_platform.lowfreq.daemon --once
python -m ifa_data_platform.lowfreq.daemon --loop
```

也可使用校验脚本：

```bash
python scripts/validate_daemon.py --once
python scripts/validate_daemon.py --health
python scripts/validate_daemon.py --show-config
```

### 停止
- loop 模式下用前台中断停止（例如 `Ctrl+C`）
- 如果后续由宿主进程托管，则按宿主进程方式停止

### 查看状态
推荐优先使用：

```bash
python scripts/validate_daemon.py --health
```

它会输出：
- daemon 总体状态
- group 状态
- dataset freshness

---

## 6. current / history / version 怎么看

### current
- 用于表示“当前有效数据”
- 表名通常是 `*_current`
- 查询时默认先看 current

### history
- 用于保留历史版本的数据快照
- 表名通常是 `*_history`
- 支持按 version_id 回看历史状态

### version
- 注册表：`ifa2.dataset_versions`
- 每次 ingest 会创建 candidate version
- promote 后成为 active
- 原 active 会变成 superseded

### 典型理解
- `current` = 当前口径
- `history` = 历史记录
- `dataset_versions` = 版本控制与切换索引

### 查询建议
- 看当前状态 → 查 `*_current`
- 看历史版本 → 查 `dataset_versions` + 对应 `*_history`
- 看某 dataset 最近运行状态 → 查 `ifa2.lowfreq_runs`

---

## 7. daily_light / weekly_deep 怎么工作

### daily_light
用于较轻量、日常刷新的低频数据组。

默认调度窗口：
- `22:45` Asia/Shanghai
- fallback：`01:30` Asia/Shanghai

### weekly_deep
用于更重、更慢、更深的数据组。

默认调度窗口：
- `10:00` Asia/Shanghai
- 周六窗口（当前配置）

### 运行语义
- daemon 根据当前时间匹配 window
- 匹配后执行对应 group
- group 执行结果进入 `GroupExecutionSummary`
- group / daemon state 写入 DB
- 同一窗口成功后会被 dedupe，避免重复执行

---

## 8. TUSHARE_TOKEN 从哪里读取

强制规则：
- `TUSHARE_TOKEN` 从本地 `config/runtime/tushare.env` 读取
- 不要把真实 token 写进代码、repo、文档、测试或 commit

当前代码还有 runtime fallback 逻辑，但项目基线应始终按本地安全配置管理 token，不按 repo 内明文值管理。

---

## 9. 数据库 / schema 是什么

- 数据库：`ifa_db`
- schema：`ifa2`

### 强制规则
- 所有 lowfreq / ingest / 查询必须在 `ifa2` 下执行
- 不允许改用 `public`
- 所有脚本、运维、核查、查询都应显式确认目标是 `ifa2`

---

## 10. 常见故障与排查方法

### 1) daemon 显示 skipped
常见原因：
- 当前 window 当天已成功
- schedule memory / group state 判定已完成

排查：
- `python scripts/validate_daemon.py --health`
- 检查 `ifa2.lowfreq_group_state`
- 仅在明确需要时，最小重置运行态；不要动 dataset 数据

### 2) dataset failed
排查：
- 查看 `ifa2.lowfreq_runs`
- 看最近 failed 的 `error_message`
- 确认是否是 token、API 参数、表缺失、import 或 schema 漂移问题

### 3) 查不到 current / history 表
排查：
- 确认 migration 是否真的已执行到目标环境
- 确认 `alembic_version` 与真实表状态是否一致
- 确认目标表在 `ifa2` 而不是 `public`

### 4) Universe 不生效
排查：
- 查 `ifa2.symbol_universe`
- 确认 `is_active=true`
- 确认读取的是正确的 `universe_type`
- 不要从旧的全市场列表读取 symbol

### 5) token 问题
排查：
- 确认本地 `config/runtime/tushare.env`
- 确认运行环境确实加载了 `TUSHARE_TOKEN`
- 不要把 token 问题通过改代码硬编码解决

---

## 11. 推荐先读文件顺序

处理 iFA lowfreq 时，推荐按以下顺序：

1. `IFA_PROJECT_CONTEXT.md`
2. `LOWFREQ_OPERATIONS_GUIDE.md`
3. `IFA_MID_HIGH_PLAN.md`
4. 再进入具体 job 报告、代码、数据库状态

---

## 12. 一句话目标

把 lowfreq 第一阶段当作 iFA 后续中频 / 高频的统一基础设施，而不是一次性的低频脚本集合。
