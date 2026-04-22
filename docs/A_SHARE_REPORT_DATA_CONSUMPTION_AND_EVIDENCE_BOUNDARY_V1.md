# A-share Phase 1 报告数据消费与证据边界（v1）

## 1. 文档目的

这份文档不是产品合同本体，而是 data-layer 对 business/report layer 的消费边界说明。

目标：

- 说明早 / 中 / 晚各时段，当前数据层能稳定支持到什么程度
- 明确哪些层可以被当成 finalized evidence，哪些只能当成 timely working evidence
- 为主 Agent / support Agent 的判断力度提供真实上限

对应的 business 合同文档在：

- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_MAIN_AGENT_DELIVERY_CONTRACT.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_SUPPORT_AGENTS_DELIVERY_CONTRACT.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_FSJ_AND_EVIDENCE_MAPPING_V1.md`

slot 级数据合同补充见：

- `/Users/neoclaw/repos/ifa-data-platform/docs/A_SHARE_REPORT_SLOT_DATA_CONTRACT_V1.md`

---

## 2. 当前数据现实的统一结论

基于当前 repo 和既有审计文档，Phase 1 应采用以下真实边界：

- **早 / 中**：以 `highfreq working + lowfreq text/reference + business seed` 为主
- **晚**：以 `midfreq daily-final + lowfreq history + T-1 archive_v2` 为主
- **archive_v2**：当前最适合作为 finalized historical truth，但主要适用于 nightly / T-1 级别背景，不应在盘中伪装成 same-day final truth

因此：

- 盘前和盘中判断允许做，但必须接受 working-layer 的不确定性
- 收盘后判断的证据质量显著更高，可以承担更强的 judgment

---

## 3. 时段级消费边界

## 3.1 Early（盘前）

### 当前可依赖层
- `highfreq_open_auction_working`
- `highfreq_event_stream_working`
- 部分 `highfreq_*_working` 派生表
- `trade_cal_history`
- `announcements_history` / `news_history` / `research_reports_history` 的近期内容
- business seed / focus families

### 适合支持的结论
- 预案类判断
- 候选主线判断
- 开盘验证计划

### 不适合支持的结论
- 当日已确认最终主线
- 已确认日终扩散结构
- 依赖完整 same-day final 数据的强归因

## 3.2 Mid（盘中）

### 当前可依赖层
- `highfreq_stock_1m_working`
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- `highfreq_event_stream_working`
- T-1 的 daily-final / archive_v2 背景数据

### 适合支持的结论
- 盘前预案是否被验证
- 当前结构强化 / 分歧 / 转弱
- 午后观察重点

### 不适合支持的结论
- 过强的最终归因
- 假定 highfreq working 一定完整无缺
- 把 working snapshots 写成 official finalized truth

## 3.3 Late（收盘后）

### 当前可依赖层
- `equity_daily_bar_history`
- `etf_daily_bar_history`
- `dragon_tiger_list_history`
- `limit_up_detail_history`
- `limit_up_down_status_history`
- `sector_performance_history`
- `northbound_flow_history` 等盘后稳定表
- `announcements_history` / `news_history` / `research_reports_history` / `investor_qa_history`
- T-1 `ifa_archive_*` nightly facts

### 适合支持的结论
- 日终主线结论
- 主线归因
- 结构强弱与扩散判断
- 次日准备输入

### 仍需注意
- same-day archive_v2 并不是晚报强依赖前提
- 晚报应以 same-day daily-final + lowfreq latest 为主，archive_v2 更偏背景/历史对照层

---

## 4. 证据层级口径

## 4.1 Finalized evidence

当前 Phase 1 可视为较强 finalized evidence 的主要是：

- midfreq daily-final history tables
- 已稳定写入的 lowfreq history tables
- archive_v2 nightly finalized tables（主要用于 T-1 / 历史背景）

## 4.2 Working evidence

当前 Phase 1 可视为 working evidence 的主要是：

- highfreq working tables
- open auction snapshot
- intraday signal state / leader candidate / sector heat 等盘中派生状态

使用要求：

- 必须显式接受 freshness 波动
- 必须支持 degrade
- 不应升级成“已确认 final truth”措辞

## 4.3 Reference evidence

当前 Phase 1 的 reference evidence 主要是：

- focus lists
- key focus families
- business seed universe
- canonical mappings

使用要求：

- 适合回答“该看什么”
- 不足以单独回答“今天已经发生了什么”

---

## 5. 对主 Agent / support Agent 的约束

## 5.1 主 Agent 约束
- early / mid 必须允许 confidence 和力度下降
- late 可以承担更强 judgment，但仍需基于可追溯表级事实
- 若 freshness 不足，应降级为观察项/风险项，而非强结论

## 5.2 support Agent 约束
- 宏观 support 可更多使用 finalized + reference 证据
- 商品 support 在盘前/盘中更容易落在 working + reference 混合态
- AI科技 support 在盘前/盘中往往更依赖 highfreq + lowfreq 最新文本，必须注意不把主题热度误写成 finalized conclusion

---

## 6. 降级规则（degrade contract）

当任一 section 的关键证据不足时，应按以下原则降级：

1. **降结论力度**：从 thesis 降为 watch item / risk item
2. **降确定性措辞**：从“成立”降为“待验证 / 倾向 / 观察到初步迹象”
3. **保留证据缺口说明**：明确告诉上层为什么不能给强结论

最不允许的行为是：

- 数据不全但口气不变
- working data 缺失却继续输出强 intraday judgment
- 把 reference watchlist 当成当日事实证据

---

## 7. Phase 1 的实现含义

这份边界文档意味着：

- business repo 可以先放心定义一主三辅合同
- report layer 可以按 slot 开始做 section-level assembly
- 但必须尊重 data layer 当前“早中较弱、晚间较强”的现实

这不是缺点，而是诚实的 phase-1 系统边界。
