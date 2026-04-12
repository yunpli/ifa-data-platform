# B4 最终收口文档

> 2026-04-12

---

## 一、B4 数据集分类

### 当前实现的 5 个 dataset（全部为日级数据）

| Dataset | 级别 | 采集时机 | 状态 |
|---------|------|----------|------|
| equity_daily_bar | 日级 | 收盘后一次性 | ✅ 已实现 |
| index_daily_bar | 日级 | 收盘后一次性 | ✅ 已实现 |
| etf_daily_bar | 日级 | 收盘后一次性 | ✅ 已实现 |
| northbound_flow | 日级 | 收盘后一次性 | ✅ 已实现 |
| limit_up_down_status | 日级 | 收盘后一次性 | ✅ 已实现 |

### 未实现的分钟级/准实时数据集（在设计中）

以下在 `IFA_MID_FREQUENCY_DESIGN.md` 中定义但**不在 B4 范围内**：
- equity_intraday_bar（5m/15m）
- index_intraday_bar（5m/15m）
- etf_intraday_bar（5m/15m）
- sector_intraday_performance

**这些属于 B5 范围，B4 不包含。**

---

## 二、中频窗口快照化定义

**中频 ≠ 实时流系统**

中频设计原则：
1. **窗口采样**：每个执行窗口形成一个确定性 snapshot
2. **非持续流**：不订阅 tick 级数据流
3. **有结束点**：每轮 run 必须有明确结束点
4. **生成 artifacts**：current / history / version / summary

当前 B4实现的5个dataset全部是**日级窗口采样**：
- 窗口：post_close_final (15:20)
- 采集方式：一次性快照
- 生成物：current + version + summary

**如果未来 B5 实现分钟级数据，也遵循同样的窗口快照化原则，而非持续流。**

---

## 三、Watchdog 实现确认

### 当前实现
- **运行方式**：`run_loop()` - daemon 自己持续运行（while True + sleep）
- **主驱动**：daemon 自己循环判断窗口执行
- **cron 角色**：外部辅助兜底（确保 daemon 存活），不驱动业务逻辑

### 代码证据
```python
# daemon.py
def run_loop(config: DaemonConfig) -> None:
    while True:
        window = config.get_matching_window(current_time)
        if window:
            summary = orchestrator.run_group(window.group_name)
        time.sleep(config.loop_interval_sec)
```

### Watchdog 能力
- 心跳记录：`DaemonWatchdog.record_heartbeat()`
- 健康检查：`python -m ifa_data_platform.midfreq.daemon --watchdog`
- Freshness 阈值：10分钟

---

## 四、工程状态

| 项目 | 状态 |
|------|------|
| 代码结构 | ✅ 完成 |
| Tushare 接入 | ✅ 完成 |
| 真实 ingest | ✅ 执行 |
| Active version | ✅ 5/5 已 promote |
| Summary 持久化 | ✅ 数据库 |
| Watchdog | ✅ 已实现 |
| 文档 | ✅ 已更新 |
| Commit | ee33604 |
| Push | ✅ 已推送 |

---

## 回复用户问题

1. **B4 当前是否包含分钟级/准实时数据需求？**
   - ❌ 否。B4 实现的5个dataset全部是日级

2. **哪些 dataset 属于这类需求？**
   - 无。分钟级数据（intraday_bar 等）在设计中但属于 B5 范围

3. **这些需求是否已真实验证？**
   - N/A - B4 不涉及分钟级数据

4. **是否已明确写成"窗口快照化"而不是持续流？**
   - ✅ 是。本文档明确说明

5. **当前 watchdog 是否以 daemon 为主、而不是 cron 为主？**
   - ✅ 是。daemon 自持续运行，cron 仅辅助兜底

6. **是否已更新文档？**
   - ✅ 是。本文档 B4_midfreq_final_closure.md

7. **是否已 commit？**
   - ✅ ee33604

8. **是否已 push？**
   - ✅ 已推送

9. **现在 B4 是否可以算完全收口？**
   - ✅ 是