# V2-R0-001 周末安全窗口与 runtime 冻结计划

> 时间：2026-04-24 17:58 PDT  
> 范围：仅覆盖 unified daemon/runtime 周末 freeze、pre-freeze 状态记录、rollback/restart checklist、服务停复边界。  
> 不包含：collector refactor、非 runtime 架构扩展、报告产品层实现。

---

## 1. 结论先行

当前现场结论：

1. **official runtime model 仍是 unified daemon**：`python -m ifa_data_platform.runtime.unified_daemon --loop`。  
2. **当前 service wrapper 显示 unified daemon 未在运行**：`zsh scripts/unified_daemon_service.sh status` 返回 `not_running`。  
3. **runtime DB 仍保留最近 scheduled execution 证据**，说明最近正式运行痕迹存在，但当前不是 live loop 正在跑的状态。  
4. **preflight 当前为绿**：无 stale active runtime、无 orphan active unified run、无 in-progress checkpoint/catchup 脏状态。  
5. **周末 freeze 可以按“控制面冻结 + 禁止重新拉起 live loop + 所有验证仅走 replay/backfill-test/dry-run”执行**，风险可控。  

---

## 2. 当前 unified daemon / runtime 状态确认

### 2.1 进程/服务面

- `zsh scripts/unified_daemon_service.sh status` → `not_running`
- 额外进程扫描未确认到可归属的 live unified daemon / legacy lane daemon 进程
- 因此，**当前 freeze 起点不是“先停一个正在运行的统一 daemon”**，而是：
  - 保持停止态
  - 不要在周末变更窗口内重新启动 live loop
  - 所有验证转到非 live 执行面

### 2.2 DB / runtime state 面

来自 `python -m ifa_data_platform.runtime.unified_daemon --status` 的关键事实：

- `runtime_day_type = saturday`
- `archive_v2` 是当前交易日 nightly 正式路径，legacy `archive` schedule 均已 `enabled=false`
- `archive_v2` 最近一次状态：
  - `last_status = succeeded`
  - `last_schedule_key = archive_v2:trade_day_nightly_daily_final`
  - `last_started_at = 2026-04-24 06:40:57 UTC`
- `highfreq` 最近一次状态：`succeeded`
- `midfreq` 最近一次状态：`succeeded`
- `lowfreq` 最近一次 worker state 表面为 `succeeded`，但 recent runs 中可见多个 `timed_out` / `runtime_preflight_repaired=true` 痕迹
- watchdog 当前显示：
  - `archive_v2 = stale_missed_schedule`
  - `lowfreq = stale_missed_schedule`
  - `midfreq = stale_missed_schedule`
  - `highfreq = idle_waiting_for_next_due`

### 2.3 preflight restart-safety 面

`zsh scripts/unified_daemon_service.sh preflight` 输出：

- `total_findings = 0`
- `stale_runtime_active = 0`
- `orphan_unified_runtime_active = 0`
- `in_progress_checkpoints = 0`
- `catchup_pending_or_observed = 0`
- `trade_calendar_status = ok`

结论：

- **当前系统不处于“脏 active state”**
- **适合进入周末 freeze / 文档化变更窗口**
- 但 **lowfreq 最近存在 orphan/timed_out 修复历史**，因此恢复时必须把 lowfreq 作为重点复核对象

---

## 3. Pre-freeze runtime state 记录

本次 freeze 前证据已固化到以下路径：

- `artifacts/runtime_freeze/runtime_process_snapshot_20260424_1758_PDT.txt`
- `artifacts/runtime_freeze/unified_daemon_status_pre_freeze_20260424_1758_PDT.json`
- `artifacts/runtime_freeze/runtime_preflight_pre_freeze_20260424_1758_PDT.json`

Freeze 基线摘要：

- unified daemon live service：**not_running**
- 当前 preflight：**clean / repair-free**
- latest successful scheduled lanes seen in DB:
  - `archive_v2`
  - `highfreq`
  - `midfreq`
- lowfreq 近窗存在 `timed_out + runtime_preflight_repaired` 痕迹，恢复时必须先复核

---

## 4. 周末 freeze plan

### 4.1 freeze 目标

本周末 freeze 的目标不是长期停机，而是：

- 固定 runtime 输入面
- 避免 live schedule 在代码/文档调整期间引入新变量
- 把验证统一收口到 replay / backfill-test / dry-run
- 为周末后恢复提供可回滚、可检查、可 restart 的纪律

### 4.2 freeze 执行口径

冻结窗口内执行规则：

1. **不得启动 unified daemon `--loop`**。  
2. **不得启动 legacy lane daemon `--loop`**。  
3. 允许的执行面仅限：
   - `python -m ifa_data_platform.runtime.unified_daemon --status`
   - `zsh scripts/unified_daemon_service.sh preflight`
   - bounded manual validation / replay / dry-run / backfill-test
4. 任何需要验证 runtime 行为的动作，必须：
   - 使用 repo-local venv
   - 使用明确输出目录/证据路径
   - 不把测试结果混入 live service bring-up

### 4.3 freeze 起止建议

- **freeze start**：本文件落地并提交后立即生效
- **freeze end**：满足“恢复前检查清单”全部通过后，由 operator 明确解除
- **责任人**：Developer Lindenwood / 当前执行 owner

---

## 5. 哪些服务可以停，哪些必须恢复

### 5.1 freeze 期间可保持停止 / 禁止拉起

1. `unified daemon --loop`  
   - 周末 freeze 期间应保持停止态
2. legacy long-running daemons（如仍有遗留 owner path）  
   - `lowfreq.daemon --loop`
   - `midfreq.daemon --loop`
   - `highfreq.daemon --loop`
   - legacy archive loop path
   - 原因：当前官方 long-running 模型已经收口到 unified daemon；freeze 期间不应出现并行 loop

### 5.2 freeze 期间允许使用的非 live 面

1. `unified_daemon --status`
2. `scripts/unified_daemon_service.sh preflight`
3. `unified_daemon --worker <lane>` 的**有界人工验证**（仅在确有必要时）
4. Archive V2 专用 backfill / replay / dry-run CLI
5. 仅生成证据、不恢复 live service 的 operator 查询脚本

### 5.3 恢复前必须可恢复的服务/能力

恢复 live 前，以下能力必须重新可确认：

1. unified daemon status 可读
2. preflight 仍为 clean
3. trade calendar 仍为 `ok`
4. `archive_v2` schedule 仍是正式 nightly path，legacy `archive` 仍保持 fallback-only/disabled
5. `highfreq / midfreq / lowfreq / archive_v2` 的 worker state 无 active/orphan 脏状态
6. 如要恢复 live collection/runtime，**最终必须恢复的唯一 long-running entry 是 unified daemon**

---

## 6. rollback checklist

若周末改动后需要回滚，按以下顺序执行：

1. `git status --short` 检查变更范围，仅回退本轮目标文件
2. 对目标文件执行模块化回退（优先 `git restore <files>` 或回退指定 commit）
3. 重新运行：
   - `zsh scripts/unified_daemon_service.sh preflight`
   - `python -m ifa_data_platform.runtime.unified_daemon --status`
4. 确认：
   - preflight 无 finding
   - `archive_v2` 仍是 nightly 主路径
   - 未产生新的 active/orphan runtime 行
5. 必要时做一次**非 live** bounded validation，确认 rollback 后 status 面仍可读

触发优先回滚的条件：

- runtime status 面不可读
- preflight 出现新的 dirty state
- schedule truth 被误改
- legacy archive / unified archive_v2 主次关系被弄乱
- lowfreq 再次出现无法解释的 active/orphan run residue

---

## 7. restart checklist

### 7.1 restart 前检查

恢复 live runtime 前必须全部满足：

1. `git status --short` 已清理或仅剩明确可接受的未跟踪 artifact
2. `zsh scripts/unified_daemon_service.sh preflight` = clean
3. `python -m ifa_data_platform.runtime.unified_daemon --status` 可成功返回
4. 核对 worker states：
   - no `active_run_id`
   - no stale orphan active markers
5. 核对 schedule truth：
   - `archive_v2` trading-day nightly schedule enabled
   - legacy `archive` schedules disabled
6. lowfreq 专项复核：
   - recent runs 不再新增 `runtime_preflight_repaired=true` 异常
   - 如存在疑点，先不要恢复 live loop

### 7.2 restart 顺序

建议恢复顺序：

1. `preflight`
2. `status`
3. 必要时单 worker bounded smoke（优先 lowfreq，若它是最大风险项）
4. `zsh scripts/unified_daemon_service.sh start`
5. 再次 `zsh scripts/unified_daemon_service.sh status`
6. 再次 `python -m ifa_data_platform.runtime.unified_daemon --status`
7. 检查 heartbeat / PID / worker state / next_due
8. 才允许恢复正式节奏观察

### 7.3 restart 后观察点

启动后优先观察：

- unified daemon PID/heartbeat 是否稳定
- lowfreq 是否再次出现 orphan/timed_out residue
- `midfreq/highfreq/archive_v2` 是否按 schedule truth 正常更新 `next_due_at_utc`
- 是否出现 legacy daemon 意外共存

---

## 8. 本任务接受判断

本任务范围内，当前接受结论为：

- [x] confirm current unified daemon/runtime state
- [x] define weekend freeze plan
- [x] record pre-freeze runtime state
- [x] define rollback/restart checklist
- [x] define which services can stop and which must recover
- [x] 未扩展到 collector refactor
- [x] 未扩展到非 runtime 架构工作

残留注意事项：

- 当前 unified daemon 本身未运行；freeze 期间这反而降低了停机复杂度，但恢复时必须显式完成 bring-up 检查
- lowfreq 最近有 runtime preflight repair/timed_out 历史，是恢复阶段第一风险点
