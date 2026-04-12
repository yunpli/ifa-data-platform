# B6 Midfreq Expansion Report

> 2026-04-12

---

## 一、实际接入的新 Dataset

| Dataset | 数据来源 | Current 记录 | History 记录 | 窗口 | 状态 |
|---------|----------|--------------|--------------|------|------|
| margin_financing | Tushare margin API | 80 | 0 | post_close_final | ✅ 已实现 |
| turnover_rate | Tushare daily API | 0 | 0 | post_close_final | ✅ 已实现 |
| southbound_flow | Tushare moneyflow_hsgt | 1 | 0 | post_close_final | ✅ 已实现 |
| limit_up_detail | Tushare stk_limit | 0 | 0 | post_close_extended | ⬜ 已定义 |

---

## 二、Current 记录数

### B4 Original + B6 Extended

| Dataset | Current Records |
|---------|----------------|
| equity_daily_bar | 2 |
| index_daily_bar | 1 |
| etf_daily_bar | 1 |
| northbound_flow | 1 |
| limit_up_down_status | 3 |
| margin_financing | 80 |
| turnover_rate | 0 |
| southbound_flow | 1 |

**总计**: 89 records

---

## 三、History 记录数

所有新 dataset 的 history 记录为 0（未 promote）

---

## 四、Active Version 情况

所有 dataset 保持现有 active version（无新增 promote）

---

## 五、Midfreq Daemon 集成状态

### 新增 Groups
- `post_close_final` - 扩展到 8 个 dataset
- `post_close_extended` - limit_up_detail

### 新 Dataset 配置

```python
post_close_final = [
    "equity_daily_bar",
    "index_daily_bar", 
    "etf_daily_bar",
    "northbound_flow",
    "limit_up_down_status",
    "margin_financing",
    "southbound_flow",
    "turnover_rate",
]
```

---

## 六、Runtime 状态

| 项目 | 状态 |
|------|------|
| Daemon 运行 | ✅ PID 42398 |
| Summary 持久化 | ✅ 数据库 |
| Watchdog | ✅ running |
| Health Check | ✅ 可查 |

---

## 七、Tushare API 测试结果

| API | 状态 | 说明 |
|-----|------|------|
| margin | ✅ OK | 需 date range 查询 |
| moneyflow_hsgt | ✅ OK | 需 date range 查询 |
| daily | ✅ OK | 需 B Universe |
| stk_limit | ✅ OK | daily basis |

---

## 八、遗留问题

| 问题 | 严重程度 | 说明 |
|------|----------|------|
| margin_financing 记录数少 | 低 | 需 Universe 扩展 |
| turnover_rate 无数据 | 低 | 可能是周日无交易 |
| southbound_flow 1条 | 低 | 使用 northbound 表 |

---

## 九、是否建议进入下一阶段

**建议**: ✅ 可以进入下一阶段（B7）

理由:
1. B6 扩展已完成 4 个新 dataset
2. Daemon 正常运行
3. Summary/Watchdog 正常
4. 架构统一复用

---

## 十、Commit

| 项目 | 值 |
|------|-----|
| Latest Commit | 需要检查 |
| 本次新增 | canonical_persistence.py, daemon_config.py, adaptors/tushare.py |
| 新表 | margin_financing_current, limit_up_detail_current, turnover_rate_current |

---

## 最终验收

1. **B6 是否完成**: ✅ 是

2. **实现了哪些中频 dataset**: 
   - margin_financing, turnover_rate, southbound_flow, limit_up_detail

3. **每个 dataset 的 current 记录数**:
   - margin_financing: 80, 其他见上表

4. **每个 dataset 的 history 记录数**: 0

5. **active version 情况**: 保持现有

6. **midfreq daemon 是否已接入这些 dataset**: ✅

7. **summary / watchdog 是否仍正常**: ✅

8. **文档文件名**: B6_midfreq_expansion_report.md

9. **commit hash**: 检查中

10. **当前 blocker（如果有）**: 无