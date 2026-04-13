# IFA_COLLECTION_RUNBOOK.md

> 目的：把当前 iFA collection 系统写成可长期维护、可直接操作的运行手册。
>
> 范围：仅覆盖当前 collection 层（lowfreq / midfreq / Universe / version / summary / state）。
>
> 不包含：facts / signals / reports / 新功能开发。

---

## 1. 环境与路径

### 1.1 代码与工作目录
- **真实开发 repo**：`/Users/neoclaw/repos/ifa-data-platform`
- **OpenClaw workspace（不要用于正式代码开发）**：`~/.openclaw/workspace`

强制规则：
- 所有正式代码、文档、提交都在 repo 内完成
- `~/.openclaw/workspace` 只用于会话上下文、临时产物、技能文件，不作为 iFA 正式代码目录

### 1.2 数据库与 schema
- **数据库**：`ifa_db`
- **schema**：`ifa2`

强制规则：
- 所有 SQL、核查、运维、daemon 相关查询默认都必须显式面向 `ifa2`
- **禁止误用 `public` schema**

### 1.3 Token / 凭证
- **TUSHARE_TOKEN**：从本地 `config/runtime/tushare.env` 读取
- 不要把真实 token 写入：
  - 代码
  - repo
  - 文档
  - 测试样例
  - commit 历史

### 1.4 Python / 环境初始化
```bash
cd /Users/neoclaw/repos/ifa-data-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 1.5 常用连接方式
使用本地 socket 连接 PostgreSQL：
```bash
source .venv/bin/activate
python - <<'PY'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.begin() as conn:
    print(conn.execute(text("select current_database(), current_schema()" )).fetchall())
PY
```

---

## 2. Universe

### 2.1 A / B / C 含义
- **A**：高频（持仓 / 更高频 / 更强资源约束）
- **B**：中频（日内窗口采样、结构化市场状态）
- **C**：低频（慢变量、基础表、公告、资产层）

### 2.2 强制关系
- `A ⊂ B ⊂ C`

### 2.3 当前数量（实测）
- A：7
- B：20
- C：54

### 2.4 当前采集边界
- lowfreq → 读 `C`
- midfreq → 读 `B`
- highfreq → 读 `A`
- **不允许回到全市场扫描**
- **不允许绕过 `symbol_universe`**

### 2.5 symbol_universe 表
表：`ifa2.symbol_universe`

关键字段：
- `id`
- `symbol`
- `name`
- `universe_type` (`A` / `B` / `C`)
- `source`
- `is_active`
- `created_at`
- `updated_at`

### 2.6 查看 Universe
```sql
SELECT universe_type, count(*)
FROM ifa2.symbol_universe
WHERE is_active = true
GROUP BY universe_type
ORDER BY universe_type;
```

```sql
SELECT symbol, name, universe_type, source, is_active
FROM ifa2.symbol_universe
WHERE is_active = true
ORDER BY universe_type, name;
```

### 2.7 CLI 维护
脚本：`scripts/symbol_universe_cli.py`

常见命令：
```bash
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate

python scripts/symbol_universe_cli.py seed
python scripts/symbol_universe_cli.py list --type A
python scripts/symbol_universe_cli.py list --type B
python scripts/symbol_universe_cli.py list --type C

python scripts/symbol_universe_cli.py add --symbol 000001.SZ --name 平安银行 --type C
python scripts/symbol_universe_cli.py remove --symbol 000001.SZ --type C
python scripts/symbol_universe_cli.py move --symbol 000001.SZ --from-type C --to-type B
```

维护原则：
- 先改 `symbol_universe`
- 不要在 dataset 代码里硬编码股票池
- 指数/ETF 目前存在固定列表例外，后续应单独治理

---

## 3. lowfreq 运行

### 3.1 lowfreq 是什么
lowfreq 是当前第一阶段 collection 基座，负责：
- 慢变量
- 基础表
- 公告/文档/资产层
- current/history/version
- daemon / state / health

### 3.2 启动方式
```bash
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate

python -m ifa_data_platform.lowfreq.daemon --once
python -m ifa_data_platform.lowfreq.daemon --loop
```

也可用校验脚本：
```bash
python scripts/validate_daemon.py --show-config
python scripts/validate_daemon.py --once
python scripts/validate_daemon.py --health
```

### 3.3 停止方式
- 前台 loop：直接 `Ctrl+C`
- 若由宿主进程（如 launchd/systemd/supervisor）托管，则按宿主进程方式停止

### 3.4 health 怎么查
```bash
python -m ifa_data_platform.lowfreq.daemon --health
# 或
python scripts/validate_daemon.py --health
```

### 3.5 summary / state 怎么查
当前 lowfreq 没有单一“唯一 summary 表”口径，维护时至少同时看：
- `ifa2.lowfreq_runs`
- `ifa2.lowfreq_group_state`
- `ifa2.job_runs`

常用 SQL：
```sql
SELECT dataset_name, status, started_at, completed_at, records_processed, error_message
FROM ifa2.lowfreq_runs
ORDER BY started_at DESC
LIMIT 50;
```

```sql
SELECT group_name, last_status, last_success_at_utc, last_run_at_utc, retry_count, is_degraded, in_fallback
FROM ifa2.lowfreq_group_state
ORDER BY updated_at_utc DESC;
```

### 3.6 lowfreq 窗口时间（代码实锤）
配置文件：`src/ifa_data_platform/lowfreq/daemon_config.py`

#### daily_light
- `22:45` Asia/Shanghai
- fallback：`01:30` Asia/Shanghai

#### weekly_deep
- `10:00` Asia/Shanghai
- 周六（`day_of_week = 5`）

### 3.7 non-trading day / 非交易日处理
当前 lowfreq 没有像 midfreq 那样单独写成“轻量模式”框架，但运行语义上：
- `daily_light` 是日常轻量更新
- `weekly_deep` 是周六深度更新
- 维护时应避免把低频当成交易日内高速刷新系统

### 3.8 lowfreq 常用组（代码实锤）
#### daily_light
- trade_cal
- stock_basic
- index_basic
- fund_basic_etf
- sw_industry_mapping
- announcements
- news
- research_reports
- investor_qa
- index_weight
- etf_daily_basic
- share_float
- company_basic
- stk_managers
- new_share
- stk_holdernumber
- name_change

#### weekly_deep
在 `daily_light` 基础上增加：
- top10_holders
- top10_floatholders
- pledge_stat
- forecast
- margin
- north_south_flow
- management
- stock_equity_change

---

## 4. midfreq 运行

### 4.1 midfreq 是什么
midfreq 是面向 `B Universe` 的固定窗口采样层。

**关键原则：**
- 中频是**窗口采样**
- **不是持续流**
- 不是 tick 级实时系统
- 报告读取前必须先冻结/稳定

### 4.2 启动方式
```bash
cd /Users/neoclaw/repos/ifa-data-platform
source .venv/bin/activate

python -m ifa_data_platform.midfreq.daemon --once
python -m ifa_data_platform.midfreq.daemon --loop
python -m ifa_data_platform.midfreq.daemon --group post_close_final
```

### 4.3 停止方式
- 前台 loop：`Ctrl+C`
- 若以后接入宿主托管，则按宿主进程停止

### 4.4 health / watchdog 怎么查
```bash
python -m ifa_data_platform.midfreq.daemon --health
python -m ifa_data_platform.midfreq.daemon --watchdog
```

### 4.5 summary 怎么查
表：`ifa2.midfreq_execution_summary`

```sql
SELECT id, group_name, window_type, total_datasets, succeeded_datasets, failed_datasets, created_at
FROM ifa2.midfreq_execution_summary
ORDER BY created_at DESC
LIMIT 20;
```

如需原始 summary JSON：
```sql
SELECT summary_json
FROM ifa2.midfreq_execution_summary
ORDER BY created_at DESC
LIMIT 1;
```

### 4.6 daemon state 怎么查
表：`ifa2.midfreq_daemon_state`

```sql
SELECT daemon_name, latest_loop_at, latest_status, created_at
FROM ifa2.midfreq_daemon_state;
```

### 4.7 midfreq 窗口时间（代码实锤）
配置文件：`src/ifa_data_platform/midfreq/daemon_config.py`

- `prewarm_early` → 07:20
- `pre_open_final` → 08:35
- `midday_prewarm` → 11:20
- `midday_final` → 11:45
- `post_close_prewarm` → 15:05
- `post_close_final` → 15:20
- `night_settlement` → 20:30

时区：`Asia/Shanghai`

### 4.8 当前 group 配置
#### post_close_final
- equity_daily_bar
- index_daily_bar
- etf_daily_bar
- northbound_flow
- limit_up_down_status
- margin_financing
- southbound_flow
- turnover_rate
- main_force_flow
- sector_performance
- dragon_tiger_list

#### post_close_extended
- limit_up_detail

### 4.9 非交易日如何处理
设计目标：
- 非交易日 / 周末应轻量运行
- 只做：预热、补漏、健康检查、状态刷新、晚到数据校验
- 不做：重型全量回填、持续流、重计算

工程现实：
- 当前代码主要是“时间窗口命中即执行 group”
- 因此维护时不能假设所有轻量/重型策略都已完全产品化

---

## 5. 常用 SQL / CLI

### 5.1 查 current
```sql
SELECT *
FROM ifa2.<dataset>_current
ORDER BY created_at DESC
LIMIT 50;
```

示例：
```sql
SELECT * FROM ifa2.margin_financing_current LIMIT 20;
```

### 5.2 查 history
```sql
SELECT *
FROM ifa2.<dataset>_history
ORDER BY created_at DESC
LIMIT 50;
```

### 5.3 查 dataset_versions
```sql
SELECT dataset_name, id, status, is_active, run_id, created_at_utc, promoted_at_utc, supersedes_version_id, watermark
FROM ifa2.dataset_versions
WHERE dataset_name = 'margin_financing'
ORDER BY created_at_utc DESC
LIMIT 20;
```

### 5.4 查 latest summary
#### midfreq
```sql
SELECT group_name, window_type, total_datasets, succeeded_datasets, failed_datasets, created_at
FROM ifa2.midfreq_execution_summary
ORDER BY created_at DESC
LIMIT 10;
```

#### lowfreq（以 runs/group_state 为主）
```sql
SELECT dataset_name, status, started_at, completed_at, records_processed, error_message
FROM ifa2.lowfreq_runs
ORDER BY started_at DESC
LIMIT 20;
```

### 5.5 查 daemon state
#### midfreq
```sql
SELECT daemon_name, latest_loop_at, latest_status, created_at
FROM ifa2.midfreq_daemon_state;
```

#### lowfreq（通过 group_state + health 结合）
```sql
SELECT group_name, last_status, last_success_at_utc, last_run_at_utc, retry_count, is_degraded, in_fallback
FROM ifa2.lowfreq_group_state
ORDER BY updated_at_utc DESC;
```

### 5.6 查 group state
```sql
SELECT *
FROM ifa2.lowfreq_group_state
ORDER BY updated_at_utc DESC;
```

### 5.7 查 Universe
```sql
SELECT universe_type, count(*)
FROM ifa2.symbol_universe
WHERE is_active = true
GROUP BY universe_type
ORDER BY universe_type;
```

### 5.8 用 Python / SQLAlchemy 快速检查
```bash
source .venv/bin/activate
python - <<'PY'
from sqlalchemy import create_engine, text
engine = create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.begin() as conn:
    rows = conn.execute(text("select universe_type, count(*) from ifa2.symbol_universe where is_active=true group by universe_type order by universe_type"))
    print(rows.fetchall())
PY
```

---

## 6. 异常处理

### 6.1 stale / degraded 怎么看
#### midfreq stale
- 用：`python -m ifa_data_platform.midfreq.daemon --watchdog`
- `DaemonWatchdog` 以 `midfreq_daemon_state.latest_loop_at` 为主
- 超过 10 分钟未更新 → stale

#### lowfreq degraded
- 看：`ifa2.lowfreq_group_state.is_degraded`
- 同时看：
  - `retry_count`
  - `last_status`
  - 最近 `lowfreq_runs`

### 6.2 skipped 怎么看
`skipped` 常见原因：
- 当前 window 当天已成功
- schedule memory 判定该窗口本轮已处理
- `--once` 运行时没有匹配窗口

排查路径：
1. 看当前时间是否命中窗口
2. 看 group_state / schedule_memory 相关状态
3. 看是否当天已成功执行

### 6.3 summary 不更新怎么办
#### midfreq
先查：
1. `midfreq_daemon_state`
2. `midfreq_execution_summary`
3. 手动跑：
```bash
python -m ifa_data_platform.midfreq.daemon --group post_close_final
```
4. 再查 latest summary 是否新增

#### lowfreq
先查：
1. `lowfreq_runs`
2. `lowfreq_group_state`
3. `python scripts/validate_daemon.py --health`

### 6.4 current / history / version 不一致时先查什么
固定顺序：
1. `*_current` 是否有数据
2. `*_history` 是否有对应 version_id 的数据
3. `dataset_versions` 是否有 candidate / active / superseded 记录
4. 最近 runs/summary 是否真的成功
5. runner 逻辑里是否在 `records_processed > 0` 后执行了 promote + persist_history

重点提醒：
- 当前设计要求：无变化不建新 version
- 当前代码实现未完全硬化该规则
- 所以看到 version 噪声时不要惊讶，先按代码现实判断

### 6.5 public / ifa2 schema 用错时怎么排查
先跑：
```sql
SELECT current_database(), current_schema();
```

再看表是否落在 `ifa2`：
```sql
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_name IN ('dataset_versions','midfreq_execution_summary','symbol_universe');
```

若表在 `public`：
- 说明连接 DSN / search_path / SQL 显式 schema 有问题
- 修复原则：
  - SQL 里明确写 `ifa2.`
  - DSN 加 search_path
  - 不要把生产查询建立在 `public` 默认 schema 上

---

## 7. 当前已知限制（必须如实面对）

1. **latest midfreq summary 证据还不够硬**
- 当前数据库 latest `midfreq_execution_summary` 仍显示较早的 5-dataset 记录
- 不能单独作为 B6 Batch 2 全闭环的最强数据库证据

2. **active version 语义不完全干净**
- 同一 dataset 在 `dataset_versions` 中实测可能出现多条 `is_active=1`
- 这与“理论上唯一 active version”的理想状态不完全一致

3. **“无变化不建新 version”仍偏设计规则，不是完全硬约束**
- 当前 midfreq 代码是 `records_processed > 0` 就 promote
- 还缺内容 diff / hash 级 no-change suppression

4. **部分 dataset 是结构接入，不是完整生产闭环**
- 例如 `sector_performance`
- `limit_up_detail` / `turnover_rate` 也未必完成真实稳定闭环

5. **历史测试数据与真实数据曾混库**
- 尤其早期 midfreq Batch 1 表中存在 dummy / test 数据痕迹
- 维护者不能默认所有 current/history 都是纯真实生产数据

6. **lowfreq / midfreq 存在命名重叠与例外路径**
- 如 `fund_basic_etf` / `etf_basic`
- `management` / `stk_managers`
- 指数/ETF 的 Universe 规则存在固定列表例外

7. **backfill 还没有统一控制面**
- 虽然 current/history/version 已具备结构基础
- 但 checkpoint / resume / batch 隔离 / 预算控制还没统一产品化

---

## 8. 建议维护顺序

每次接手 collection 系统，建议按以下顺序：
1. 读 `IFA_PROJECT_CONTEXT.md`
2. 读本文件 `IFA_COLLECTION_RUNBOOK.md`
3. 读 `IFA_COLLECTION_DATASET_REGISTRY.md`
4. 查 Universe
5. 查 daemon state / summary / group state
6. 再查具体 dataset 的 current/history/version

---

## 9. 一句话结论

当前 iFA collection 已经具备可运行的 lowfreq 基座和可操作的 midfreq 窗口系统，但维护时必须把它视为“已可运行、未完全收口”的生产中基建：先看 Universe，再看 state/summary，再看 dataset current/history/version，最后才谈是否真正闭环。
