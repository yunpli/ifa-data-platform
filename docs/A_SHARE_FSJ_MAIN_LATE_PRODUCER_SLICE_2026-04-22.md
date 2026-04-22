# A股 FSJ Main Agent Late Producer 首个生产切片（2026-04-22）

## 1. 这批实现解决什么

这批把 **A股主 Agent / late slot / main producer** 做成真实可落盘的 FSJ 生产路径：

- 从 late-slot 已冻结数据合同出发
- 以 **same-day stable/final market tables** 作为主证据
- 以 **same-day text with source_time** 作为晚报事实补充
- 以 **retained intraday highfreq** 仅作为日内演变上下文
- 通过 `FSJStore` 持久化成最小但正确的 FSJ bundle graph
- 在 same-day final 证据不齐时，明确降级为 `provisional_close_only` 或 `post_close_observation_only`

代码入口：

- `src/ifa_data_platform/fsj/late_main_producer.py`

---

## 2. 对齐的合同来源

本实现直接对齐以下已冻结合同：

- data contract:
  - `docs/A_SHARE_REPORT_SLOT_DATA_CONTRACT_V1.md`
- business contract:
  - `../ifa-business-layer/docs/A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1.md`
  - `../ifa-business-layer/docs/A_SHARE_FSJ_AND_EVIDENCE_MAPPING_V1.md`
  - `../ifa-business-layer/docs/A_SHARE_MAIN_AGENT_DELIVERY_CONTRACT.md`

本切片严格遵守的 late 约束：

1. late 主输入优先使用 same-day stable/final：
   - `equity_daily_bar_history`
   - `northbound_flow_history`
   - `limit_up_detail_history`
   - `limit_up_down_status_history`
   - `dragon_tiger_list_history`
   - `sector_performance_history`
2. same-day 文本证据必须带 `source_time`，否则不能升级为正式晚报证据。
3. retained intraday highfreq 只能作为 **intraday evolution/context**，不能替代 close confirmation。
4. T-1 archive/background 只能作为 **historical reference**，不得冒充 same-day late final。
5. 当 same-day stable/final 覆盖不足时，producer 必须显式输出：
   - `provisional_close_only`，或
   - `post_close_observation_only`

---

## 3. 当前已实现的 producer slice

### 3.1 生产接口

`LateMainFSJProducer`

提供两个入口：

- `produce(...)`
  - 读取 late slot 输入
  - 装配 FSJ graph
  - 只返回 payload，不落库
- `produce_and_persist(...)`
  - 装配后经 `FSJStore.upsert_bundle_graph(...)` 落库
  - 再回读 bundle graph 作为提交结果

### 3.2 seam / 可替换边界

`LateMainInputReader` 是生产 seam。

当前有两个消费模式：

- `SqlLateMainInputReader`
  - 真实读取当前 data-platform same-day stable/final + retained intraday tables
- fake reader / fixture reader
  - 测试中注入 deterministic 输入

这保证了：

- 生产路径是真连真实 retained/stable 表
- 测试不依赖 live source 波动
- 将来切到 slot freeze / replay bundle / 上游 façade 时，不必重写 assembler

### 3.3 当前 bundle graph 结构

当前 late main slice 固定生成：

#### facts
- `fact:late:same_day_final_market`
  - same-day stable/final market coverage 主事实
- `fact:late:same_day_text_evidence`（可选）
  - same-day 带时间文本/事件事实
- `fact:late:same_day_mid_anchor`（可选）
  - same-day mid slot 锚点，仅 prior-slot reference
- `fact:late:retained_intraday_context`（可选）
  - same-day intraday evolution/context，仅 context
- `fact:late:t_minus_1_background`（可选）
  - T-1 历史对照，仅 archive background

#### signals
- `signal:late:close_package_state`
  - full close / provisional close / observation-only 状态
- `signal:late:intraday_to_close_context`
  - 日内到收盘的演化解释状态，仅 context

#### judgment
- `judgment:late:mainline_close`
  - `confirm`：only when full close package ready
  - `monitor`：when provisional close only
  - `watch`：when no same-day final structure exists

#### edges
- `fact_to_signal`
- `signal_to_judgment`

#### evidence / observed linkage
- same-day midfreq final/stable source links
- same-day retained intraday source links
- prior-slot FSJ summary link
- T-1 archive reference link
- slot replay link（如果调用时提供 `replay_id`）
- observed-record rows 保存当时看到的 stable/final 与 intraday context 摘要

---

## 4. 降级语义

这是本批最重要的生产边界。

### 4.1 full close package

前提：

- `equity_daily_bar_history` same-day ready
- 至少一类 same-day stable post-close market support ready
- 至少一类 same-day text with source_time ready

输出：

- judgment `object_type=thesis`
- `judgment_action=confirm`
- contract mode = `full_close_package`

这意味着：

- 可以输出正式晚报主线收盘结论
- intraday retained 只做演化解释
- T-1 只做历史对照

### 4.2 provisional close only

前提：

- same-day final structure 已出现
- 但 stable support 或 same-day timed text 未齐

输出：

- judgment `object_type=watch_item`
- `judgment_action=monitor`
- contract mode = `provisional_close_only`

这意味着：

- 允许描述收盘初步结构
- 不允许宣称 full confident close package
- 不允许把“目前先看到的收盘结构”写成完整最终确认

### 4.3 post-close observation only

前提：

- 缺少 same-day final structure
- 只有 retained intraday context 或 same-day low/text

输出：

- judgment `object_type=watch_item`
- `judgment_action=watch`
- contract mode = `post_close_observation_only`

这对应合同中的：

- 只能写盘后观察 / 待补全项
- 不得写 final daily structure judgment

---

## 5. 为什么这个切片符合 late-slot 合同

核心点只有三条：

1. **主证据层没有漂移**
   - same-day stable/final tables 是晚报主证据
   - 不是 working-only highfreq
2. **intraday evidence 只做 context**
   - retained highfreq 明确标为 `background_only / not_for_final_confirmation`
   - 不会冒充收盘 final confirmation
3. **历史层没有冒充 same-day**
   - T-1 仅保留为 `historical_reference`
   - 不允许把 archive/background 包装成 same-day late ready

---

## 6. 测试覆盖

### unit
- `tests/unit/test_fsj_main_late_producer.py`
  - full close ready 时生成 `thesis/confirm`
  - stable/final 不齐时正确降级为 `provisional_close_only`
  - 只有 intraday/text 时正确降级为 `post_close_observation_only`

### integration
- `tests/integration/test_fsj_main_late_producer_integration.py`
  - 用 fake reader 驱动 producer
  - 经 `FSJStore` 落到真实 `ifa2.ifa_fsj_*` 表
  - 验证 objects / edges / evidence / observed-record 均已写入

---

## 7. 本批故意未做

以下明确 deferred，不属于本次 slice：

1. support-agent evidence merge
2. 多 section 并行装配
3. report artifact link 写回
4. automatic supersede / active-bundle replacement policy
5. report-layer query façade
6. slot replay 自动 hydration

---

## 8. 一句话结论

当前 late producer 已经把 **same-day stable/final 主证据 + timed low/text + retained intraday context + T-1 background** 这四层边界做清楚，并能真实落盘；证据不齐时只会降级，不会伪造 full close judgment。
