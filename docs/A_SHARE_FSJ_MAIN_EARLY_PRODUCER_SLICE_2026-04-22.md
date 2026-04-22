# A股 FSJ Main Agent Early Producer 首个生产切片（2026-04-22）

## 1. 这批实现解决什么

这批不是继续写合同，而是把 **A股主 Agent / early slot / main producer** 做成第一条真实可落盘路径：

- 从当前真实 early-slot 输入边界出发
- 只实现 `main` / `early` / `pre_open_main`
- 装配出最小但正确的 FSJ bundle graph
- 通过 `FSJStore` 持久化
- 明确哪些是本批已实现，哪些仍然故意延后

代码入口：

- `src/ifa_data_platform/fsj/early_main_producer.py`

---

## 2. 对齐的合同来源

本实现直接对齐以下已冻结合同：

- data contract:
  - `docs/A_SHARE_REPORT_SLOT_DATA_CONTRACT_V1.md`
- business contract:
  - `../ifa-business-layer/docs/A_SHARE_EARLY_MID_LATE_DATA_CONSUMPTION_CONTRACT_V1.md`
  - `../ifa-business-layer/docs/A_SHARE_FSJ_AND_EVIDENCE_MAPPING_V1.md`
  - `../ifa-business-layer/docs/A_SHARE_MAIN_AGENT_DELIVERY_CONTRACT.md`
- collector matrix:
  - `docs/SLOT_COLLECTOR_INPUT_MATRIX_2026-04-19_0800.md`

本切片严格遵守的 early 约束：

1. early 主输入只使用：
   - `highfreq_open_auction_working`
   - `highfreq_event_stream_working`
   - `highfreq_leader_candidate_working`
   - `highfreq_intraday_signal_state_working`
   - `trade_cal_history`
   - `focus_lists / focus_list_items`
   - 近期低频文本催化（news / announcements / research / investor_qa）
2. T-1 背景只能作为 `historical_reference`，不能冒充 same-day confirmed evidence。
3. 当 high layer 缺失时，producer 必须降级为 candidate/watch 模式。
4. 不伪造晚报/收盘 final 证据。

---

## 3. 当前已实现的 producer slice

### 3.1 生产接口

`EarlyMainFSJProducer`

提供两个入口：

- `produce(...)`
  - 读取 early slot 输入
  - 装配 FSJ graph
  - 只返回 payload，不落库
- `produce_and_persist(...)`
  - 装配后经 `FSJStore.upsert_bundle_graph(...)` 落库
  - 再回读 bundle graph 作为提交结果

### 3.2 seam / 可替换边界

`EarlyMainInputReader` 是生产 seam。

当前有两个消费模式：

- `SqlEarlyMainInputReader`
  - 真实读取当前 data-platform tables
- fake reader / fixture reader
  - 测试中注入 deterministic 输入

这保证了：

- 生产路径不是假代码
- 测试不依赖 live source 波动
- 将来可替换成更显式的 slot freeze / replay / upstream adapter，而无需重写 assembler

### 3.3 当前 bundle graph 结构

当前 early main slice 固定生成：

#### facts
- `fact:early:market_inputs`
  - 盘前 auction / event / leader / signal-state 覆盖事实
- `fact:early:reference_scope`
  - 当前 focus/key_focus 观察池事实
- `fact:early:text_catalysts`（可选）
  - 隔夜/近期文本催化事实
- `fact:early:t_minus_1_background`（可选）
  - T-1 背景锚点，仅 historical reference

#### signal
- `signal:early:mainline_candidate_state`
  - 明确表达“这是待开盘验证候选，不是已确认主线”

#### judgment
- `judgment:early:mainline_plan`
  - high 存在时：`thesis + validate`
  - high 缺失时：`watch_item + watch`

#### edges
- `fact_to_signal`
- `signal_to_judgment`

#### evidence / observed linkage
- source-observed evidence links
- slot replay link（如果调用时提供 `replay_id`）
- observed-record rows 保存当时具体看到的摘要 payload

---

## 4. 降级语义

这是本批最重要的生产边界之一。

### 4.1 high layer 可用

输出：

- judgment `object_type=thesis`
- `judgment_action=validate`
- statement 明确要求开盘验证

这意味着：

- producer 可以形成盘前主线候选
- 但绝不把它写成“今天主线已确认”

### 4.2 high layer 缺失，但 low/text 还在

输出：

- judgment `object_type=watch_item`
- `judgment_action=watch`
- signal 退化为 candidate/risk 语义

这对应合同中的：

- 允许写“事件驱动候选”
- 不允许写“市场已经选择该方向”

### 4.3 只剩 reference/seed

仍会生成 bundle，但 judgment 保持 watch-only 语义；
不会伪装成 thesis-confirmed。

---

## 5. 为什么这是“第一条真实 producer path”

因为它已经同时具备：

1. **真实 contract grounding**
   - 输入边界来自 early-slot contract，而不是拍脑袋字段
2. **真实 source seam**
   - `SqlEarlyMainInputReader` 直连当前真实表
3. **真实 FSJ graph**
   - facts / signal / judgment / edges / evidence / observed-record 都落地
4. **真实 persistence**
   - 通过 `FSJStore` 写入 phase1 schema
5. **真实 degrade discipline**
   - 不把 unavailable late/final evidence 硬塞进 early slot

---

## 6. 本批故意未做

以下明确 deferred，不属于本次 slice：

1. support-agent inputs 合并（macro / commodities / ai_tech）
2. 多 section 并行装配（如 observation list / risk block / validation plan 各自独立 bundle）
3. sector/theme chain mapping 的更细 object graph
4. slot replay 自动 hydration
5. report artifact link 写回
6. supersede orchestration / active-bundle replacement policy
7. report-layer 全接线消费

这些都留在下一批，不在本批伪实现。

---

## 7. 测试覆盖

### unit
- `tests/unit/test_fsj_main_early_producer.py`
  - high evidence 存在时生成 thesis/validate judgment
  - high evidence 缺失时正确降级为 watch-only judgment

### integration
- `tests/integration/test_fsj_main_early_producer.py`
  - 用 fake reader 驱动 producer
  - 经 `FSJStore` 落到真实 `ifa2.ifa_fsj_*` 表
  - 验证 objects / edges / evidence / observed-record 均已写入

---

## 8. 后续最自然扩展方向

在当前设计上，后续最自然的下一步是：

1. 把 `pre_open_main` 扩展成多个 section bundle
2. 引入 support-agent support/adjust/counter relations
3. 把 replay/freeze evidence 变成 first-class reader source
4. 对 active bundle 增加 supersede policy
5. 为 report assembly 提供稳定 query façade

当前切片的目标不是一次做完，而是把 **first production-grade early main path** 做对、做稳、做可扩展。
