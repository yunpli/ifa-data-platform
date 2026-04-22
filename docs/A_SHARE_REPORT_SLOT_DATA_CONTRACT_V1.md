# A-share 报告时段数据合同（Early / Mid / Late，Phase 1 / v1）

## 1. 文档目的

这份文档从 `ifa-data-platform` 角度，正式定义 A股报告系统在 **early / mid / late** 三个时段可以如何消费当前数据层。

它回答的不是“业务上想写什么”，而是：

- 当前哪些层可以作为该 slot 的 **主输入层**
- 哪些层只能作为 **辅助 / fallback**
- freshness / completeness 的真实最低口径是什么
- 数据不足时，上游应该如何被下游识别为 degrade，而不是被误读成正常完整输入
- 哪些层在当前阶段 **不能被业务层误当成 same-day finalized truth**

对应业务侧合同见：

- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_MAIN_AGENT_DELIVERY_CONTRACT.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_SUPPORT_AGENTS_DELIVERY_CONTRACT.md`

---

## 2. 当前系统现实（必须接受的前提）

Phase 1 当前数据现实已经明确：

- **early / mid 的主工作层是 highfreq working**，不是 finalized daily truth
- **late 的主工作层是 same-day daily-final + lowfreq latest history**
- **archive_v2 当前是 nightly finalized 历史层**，主要适用于 T-1 / 历史背景 / replay / 对照，不是盘中 final 替身
- **slot replay evidence 是审计 / 回放层**，不是默认 live 主输入层

因此：

- 盘前、盘中的强判断能力天然低于晚报
- 任何把 archive/replay 误当 live finalized 的实现，都属于违约

---

## 3. 层级定义

## 3.1 high layer

典型对象：

- `highfreq_open_auction_working`
- `highfreq_stock_1m_working`
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- `highfreq_event_stream_working`

角色：

- early / mid 主输入层
- late 的补充层

风险：

- working 状态
- 可能延迟、断档、派生不齐
- 不能当 official final truth

## 3.2 mid layer

典型对象：

- `equity_daily_bar_history`
- `etf_daily_bar_history`
- `dragon_tiger_list_history`
- `limit_up_detail_history`
- `limit_up_down_status_history`
- `sector_performance_history`
- `northbound_flow_history`

角色：

- late 主输入层
- early / mid 的 T-1 背景对照层

## 3.3 low layer

典型对象：

- `trade_cal_history`
- `announcements_history`
- `news_history`
- `research_reports_history`
- `investor_qa_history`
- business seed / focus / mapping 所依赖的稳定 reference object

角色：

- early / late 的重要支撑层
- mid 的事件解释层

## 3.4 archive layer

典型对象：

- `ifa_archive_*` finalized nightly facts

角色：

- T-1 / 历史对照
- finalized historical truth
- replay / QA / audit 支撑

禁止误读：

- 不得当 same-day intraday final
- 不得当 late same-day final 替代物

## 3.5 replay evidence layer

典型对象：

- slot freeze 后的证据包
- slot replay / snapshot input bundle

角色：

- 审计 / 回放 / 一致性复现

禁止误读：

- 默认不能替代 live source freshness

---

## 4. 时段级数据合同

## 4.1 Early（盘前）

### 主输入层
- `high`：盘前竞价 / 盘前事件 / 可用盘前派生 working
- `low`：交易日历、近期公告/新闻/研报/问答
- `reference`：focus / key focus / business seed / chain mapping

### 次级 / fallback 层
- `archive(T-1)`：只用于昨日背景、延续性、历史定位
- `replay(last valid slot)`：只用于审计“之前看到了什么”

### freshness 合同
- 盘前 `high` 必须来自当日盘前窗口，否则为 `stale-hard`
- `low` 必须可确认对今日仍有解释意义
- `archive` 默认标记为历史层，不参与“当日已发生” freshness

### completeness 合同
至少应满足：

- 有可消费的盘前 high 或 low 事实锚点
- 有有效 reference object 作为观察对象锚点
- 若 high 与 low 都缺，slot 应显式输出 `insufficient_for_thesis`

### degrade 规则
- 盘前 high 缺失 -> 仅允许 watchlist / setup，不允许 thesis-confirmed
- 只有 reference -> 只能给观察对象，不能给正式盘前主判断

### 不得作为主输入层
- same-day archive
- T-1 archive 单独支撑今日结论
- replay evidence 冒充实时盘前输入

## 4.2 Mid（盘中）

### 主输入层
- `high`：1m、breadth、heat、leader、intraday-signal、event-stream

### 次级 / fallback 层
- `T-1 mid`
- `T-1 archive`
- `low latest text`
- `current-slot replay`（仅审计/回放）

### freshness 合同
- `high` 主表必须处于盘中可接受延迟窗口
- 若主 high 表时间戳不可得，必须降为 `freshness_unknown`
- `freshness_unknown` 不得支撑盘中强结论

### completeness 合同
至少应满足：

- 至少一类结构型 high 表可用（breadth / heat / leader / signal-state / stock-1m / event-stream 中之一）
- 若所有结构型 high 表都不可用，则 slot 只能输出 `monitoring_only`

### degrade 规则
- 轻微延迟：允许 provisional intraday status
- 明显断档：只能输出 follow-up/watch，不能输出 confirmed strengthening/weakening
- 仅有 T-1/low：只能作背景说明

### 不得作为主输入层
- T-1 archive
- 低频文本事件
- replay evidence

## 4.3 Late（收盘后）

### 主输入层
- `mid`：same-day daily-final / stable post-close market tables
- `low`：same-day 或最近可追溯文本/事件事实

### 次级 / fallback 层
- `archive(T-1)`：历史对照
- `same-day high retained`：补充日内演变
- `late-slot replay`：审计/回放

### freshness 合同
- `mid` 主表必须进入盘后 stable 可消费状态
- 若关键 `mid` 主表尚未 ready，必须向下游暴露 `provisional_close_only`
- `low` 必须带 source_time，未知时间的 narrative 不可升级为正式证据

### completeness 合同
至少应满足：

- 至少一类 same-day stable market table ready
- 至少一类文本/事件或稳定背景层 ready
- 若二者缺一，late slot 只能输出部分可用，不得宣称 full close package

### degrade 规则
- mid 不齐 -> 输出 provisional close package
- 只有 high + low -> 只能写盘后初步观察，不得写 final daily structure
- 只有 archive -> 只能写历史对照，不能写今日复盘

### 不得作为主输入层
- working-only highfreq
- archive(T-1)
- replay-only bundle

---

## 5. 面向下游的最小状态暴露要求

为了让 business/report 层正确降级，data layer 至少应能暴露以下语义：

- `source_layer`
- `source_table`
- `source_time`
- `freshness_label`
- `completeness_label`
- `is_finalized_equivalent`
- `degrade_reason`

推荐最小枚举：

### freshness_label
- `fresh`
- `stale-soft`
- `stale-hard`
- `unknown`

### completeness_label
- `complete`
- `partial`
- `sparse`
- `missing`

### is_finalized_equivalent
- `true`：仅用于 same-day late stable tables 或 archive finalized history
- `false`：working / replay / unknown freshness

### degrade_reason
- `upstream_delay`
- `table_missing`
- `freshness_unknown`
- `partial_family_coverage`
- `historical_only`

---

## 6. 对主 Agent 与 support Agent 的不同含义

同一份 data contract，在不同 agent 上解释不同：

### 主 Agent
- 需要更高的跨层装配完整度
- 必须优先使用该 slot 的主输入层
- 不能用 support 域里局部强证据替代全市场主证据

### 宏观 support
- 更常把 `low + archive` 用成主层
- 但这只说明宏观背景，不说明盘面已确认

### 商品 support / AI科技 support
- 在 early/mid 更依赖 `high`
- 但它们只能输出本域局部结构，不得冒充全市场最终结构

---

## 7. 实现约束（给后续工程）

后续任何 slot 装配逻辑，至少应满足：

1. slot 先判定当前层级是否可作为主输入层
2. 不可用时先降级，不得补叙事掩盖缺口
3. archive/replay 进入 prompt 或 JSON 时必须带明确层标签
4. late slot 必须显式区分：
   - same-day stable final-like facts
   - T-1 archive background facts
   - same-day intraday retained facts

---

## 8. 一句话结论

Phase 1 的真实数据合同非常明确：**早报靠 high+low 建预案，中报靠 high 判结构，晚报靠 mid+low 做结论；archive 与 replay 都重要，但都不是 same-day live final 的替身。**
