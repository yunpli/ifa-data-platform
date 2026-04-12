# B4 Midfreq Runtime Clarification

> Date: 2026-04-12

---

## 一、当前实际运行方式

| 项目 | 状态 |
|------|------|
| 运行模式 | daemon 持续运行 + cron 外部触发混合 |
| 主要方式 | `run_loop()` - daemon 自己持续运行，while True 循环 |
| Cron 角色 | 辅助/兜底：通过 `--once --group post_close_final` 临时触发 |
| --once 模式 | 支持，用于测试/手动触发 |

### daemon.py 运行模式
```python
# 方式1: 持续运行 (默认)
python -m ifa_data_platform.midfreq.daemon
# 内部: while True + sleep(config.loop_interval_sec)

# 方式2: 单次运行 (手动/测试)
python -m ifa_data_platform.midfreq.daemon --once
python -m ifa_data_platform.midfreq.daemon --group post_close_final
```

---

## 二、是否用了 Cron

**当前：Cron 非必须，daemon 可独立运行**

| 触发方式 | 状态 |
|---------|------|
| daemon 自循环 | ✅ 已实现（run_loop） |
| cron 调用 --once | 可选，辅助 |
| 手动 --group | 可选，测试 |

### 为什么会这样设计？
中频特点：
- 交易时段窗口明确（7:20, 08:35, 11:20, 11:45, 15:05, 15:20, 20:30）
- 非交易日不需要运行
- 持续 daemon 不断轮询判断窗口是浪费

所以设计是：
- daemon 启动后持续运行，自己判断窗口
- 窗口到了就执行，窗口过了就 sleep
- cron 只用作"确保 daemon 存活"的兜底

---

## 三、设计目标是否对齐

| 应该有的职责 | 当前状态 |
|-------------|----------|
| 自己持续运行 | ✅ run_loop() |
| 自己判断窗口 | ✅ config.get_matching_window() |
| 自己执行采集 | ✅ orchestrator.run_group() |
| 自己写 summary / state | ⚠️ 有 to_json()，未持久化到文件 |
| 自己被 watchdog 监控 | ⚠️ 有 health 数据库，无外部 watchdog |
| 异常后恢复 / 拉起 | ⚠️ 有 retry 逻辑，无自动拉起 |

### 偏差说明

1. **summary 未写入文件** - 只有 to_json() 输出到 stdout，未持久化
2. **无外部 watchdog** - 只有数据库 health 记录，无独立监控进程
3. **daemon 崩溃后无自动拉起** - 依赖外部 cron 兜底

---

## 四、Summary / 运行报告

| 项目 | 状态 | 说明 |
|------|------|------|
| 每轮执行 summary | ⚠️ 部分 | GroupExecutionSummary 有 to_json()，但只输出到 stdout |
| 写到数据库 | ⚠️ 部分 | 写到 midfreq_window_state，未写 summary 表 |
| 写到固定文件 | ❌ 未实现 | 只有 stdout 输出 |
| 可被查询 | ⚠️ 部分 | health 可查运行状态，无详细 summary |

**当前实际行为：**
```python
# 执行后输出到 stdout
print(summary.to_json())
# 写入 schedule_memory
schedule_memory.update_daemon_loop(...)
```

---

## 五、Watchdog / 健康

| 项目 | 状态 | 说明 |
|------|------|------|
| daemon 心跳 | ⚠️ 数据库 | latest_loop_at 记录到 midfreq_daemon_state |
| health check | ⚠️ 基础 | get_daemon_health() 可查 |
| freshness 检查 | ❌ 未实现 | 只有状态，无 freshness 阈值 |
| watchdog 进程 | ❌ 未实现 | 无独立 watchdog daemon |
| 自动恢复 | ⚠️ 重试 | 窗口级 retry，daemon 崩溃无恢复 |

**当前实际行为：**
```python
# health 查询
python -m ifa_data_platform.midfreq.daemon --health

# 数据库状态
SELECT * FROM ifa2.midfreq_daemon_state
SELECT * FROM ifa2.midfreq_window_state
```

---

## 六、收口建议

### 最小收口项（建议实现）
1. **summary 持久化** - 每轮执行后写入 summary 到数据库或文件
2. **外部 watchdog** - 可以复用 lowfreq 的 watchdog 或新��简单 cron job 检查 daemon 存活

### 保持现状也可接受
当前设计基本对齐 lowfreq：
- daemon 是主形态
- cron 是辅助兜底
- 有窗口判断
- 有重试
- 有运行记录

差异点：summary 未文件化、无独立 watchdog daemon

---

## 七、_commit

当前 commit: e8ebbb1
新增文件: B4_midfreq_batch1_final_report.md, B4_midfreq_runtime_clarification.md

---

## 回复要点总结

1. **当前 midfreq 实际运行方式是什么？**
   - daemon 自持续运行（run_loop）为主，cron 外部触发为辅
   
2. **是否用了 cron？**
   - cron 非必须，是辅助兜底角色
   
3. **cron 是主驱动还是辅助？**
   - 辅助。daemon 自己循环判断窗口执行
   
4. **当前 midfreq daemon 是否真正像 lowfreq daemon 一样持续运行？**
   - ✅ 是。run_loop() 持续运行，while True + sleep
   
5. **当前是否已有 summary / 运行报告？**
   - ⚠️ 部分有。GroupExecutionSummary.to_json() 输出到 stdout，未持久化文件
   
6. **当前是否已有 watchdog / 健康恢复？**
   - ⚠️ 基础有。数据库 health，无独立 watchdog 进程
   
7. **是否已生成说明文档？**
   - ✅ 是。本文档 B4_midfreq_runtime_clarification.md
   
8. **commit hash**
   - e8ebbb1
   
9. **当前 blocker（如果有）**
   - 无 blocker，daemon 可正常运行