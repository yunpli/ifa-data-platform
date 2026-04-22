# A股 FSJ Main Agent Mid Producer 首个生产切片（2026-04-22）

## 1. 这批实现解决什么

这批不是继续写合同，而是把 **A股主 Agent / mid slot / main producer** 做成第一条真实可落盘路径：

- 从当前真实 mid-slot 输入边界出发
- 只实现 `main` / `mid` / `midday_main`
- 装配出最小但正确的 FSJ bundle graph
- 通过 `FSJStore` 持久化
- 明确哪些是本批已实现，哪些仍然故意延后

代码入口：

- `src/ifa_data_platform/fsj/mid_main_producer.py`

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

本切片严格遵守的 mid 约束：

1. mid 主输入只使用：
   - `highfreq_stock_1m_working`
   - `highfreq_sector_breadth_working`
   - `highfreq_sector_heat_working`
   - `highfreq_leader_candidate_working`
   - `highfreq_intraday_signal_state_working`
   - `highfreq_event_stream_working`
   - same-day `early` FSJ summary 作为 prior-slot anchor
   - 近期低频文本（news / announcements / research / investor_qa）作为解释上下文
   - 可选 T-1 `late` FSJ background
2. mid slot 允许输出盘中结构更新，但 **不能** 冒充收盘 final truth。
3. 当 intraday high layer 不足或 freshness 不够时，producer 必须降级为 monitoring/watch 模式。
4. early slot 只能作为 `prior_slot_reference`，T-1 late 只能作为 `historical_reference`。

---

## 3. 当前已实现的 producer slice

### 3.1 生产接口

`MidMainFSJProducer`

提供两个入口：

- `produce(...)`
  - 读取 mid slot 输入
  - 装配 FSJ graph
  - 只返回 payload，不落库
- `produce_and_persist(...)`
  - 装配后经 `FSJStore.upsert_bundle_graph(...)` 落库
  - 再回读 bundle graph 作为提交结果

### 3.2 seam / 可替换边界

`MidMainInputReader` 是生产 seam。

当前有两个消费模式：

- `SqlMidMainInputReader`
  - 真实读取当前 data-platform tables
- fake reader / fixture reader
  - 测试中注入 deterministic 输入

这保证了：

- 生产路径不是假代码
- 测试不依赖 live source 波动
- 将来可替换成更显式的 slot freeze / replay / upstream adapter，而无需重写 assembler

### 3.3 当前 bundle graph 结构

当前 mid main slice 固定生成：

#### facts
- `fact:mid:intraday_structure`
  - 盘中 1m / breadth / heat / signal-state 结构覆盖事实
- `fact:mid:leader_and_event_state`
  - 盘中龙头候选 / 事件流覆盖事实
- `fact:mid:early_plan_anchor`（可选）
  - same-day early FSJ 锚点，仅 prior-slot reference
- `fact:mid:t_minus_1_background`（可选）
  - T-1 背景锚点，仅 historical reference
- `fact:mid:latest_text_context`（可选）
  - 近期文本/公告/研报/问答形成的解释性上下文

#### signals
- `signal:mid:plan_validation_state`
  - 当前盘中结构是否足以回答盘前预案的验证状态
- `signal:mid:afternoon_tracking_state`
  - 午后继续验证/跟踪重点

#### judgment
- `judgment:mid:mainline_update`
  - freshness + evidence 足够时：`thesis + adjust`
  - 证据不足/不新鲜时：`watch_item + watch`

#### edges
- `fact_to_signal`
- `signal_to_judgment`

#### evidence / observed linkage
- source-observed evidence links
- prior-slot reference link
- historical reference link
- slot replay link（如果调用时提供 `replay_id`）
- observed-record rows 保存当时具体看到的摘要 payload

---

## 4. 降级语义

这是本批最重要的生产边界之一。

### 4.1 intraday structure 充足且 freshness 新鲜

输出：

- judgment `object_type=thesis`
- `judgment_action=adjust`
- signal 可输出 `confirmation` 语义

这意味着：

- producer 可以对盘前预案做盘中结构修正
- 但绝不把它写成“收盘已确认 final truth”

### 4.2 intraday structure 有，但不足或 freshness 变差

输出：

- judgment `object_type=watch_item`
- `judgment_action=watch`
- signal 退化为 risk / monitoring 语义

这对应合同中的：

- 允许写“盘中跟踪/观察级更新”
- 不允许写“强化/分歧/转强已确认”这类强结论

### 4.3 只剩 early anchor / T-1 / text context

仍会生成 bundle，但 judgment 保持 watch-only / monitoring-only 语义；
不会伪装成 mid thesis-confirmed。

---

## 5. 为什么这是“第一条真实 mid producer path”

因为它已经同时具备：

1. **真实 contract grounding**
   - 输入边界来自 mid-slot contract，而不是拍脑袋字段
2. **真实 source seam**
   - `SqlMidMainInputReader` 直连当前真实表
3. **真实 FSJ graph**
   - facts / signals / judgment / edges / evidence / observed-record 都落地
4. **真实 persistence**
   - 通过 `FSJStore` 写入 phase1 schema
5. **真实 degrade discipline**
   - 不把 unavailable final truth 硬塞进 mid slot

---

## 6. 本批故意未做

以下明确 deferred，不属于本次 slice：

1. support-agent inputs 合并（macro / commodities / ai_tech）
2. 多 section 并行装配（例如 observation block / risk block / validation block 拆分）
3. theme-chain / sector diffusion 的更细 object graph
4. replay/freeze evidence 自动 hydration
5. report artifact link 写回
6. supersede orchestration / active-bundle replacement policy
7. report-layer 全接线消费

这些都留在下一批，不在本批伪实现。

---

## 7. 测试覆盖

### unit
- `tests/unit/test_fsj_main_mid_producer.py`
  - intraday structure 新鲜且充分时，生成 thesis/adjust judgment
  - intraday structure 缺失时，正确降级为 monitoring/watch-only judgment

### integration
- `tests/integration/test_fsj_main_mid_producer_integration.py`
  - 用 fake reader 驱动 producer
  - 经 `FSJStore` 落到真实 `ifa2.ifa_fsj_*` 表
  - 验证 objects / edges / evidence / observed-record 均已写入

---

## 8. 后续最自然扩展方向

在当前设计上，后续最自然的下一步是：

1. 把 `midday_main` 扩展成多个 section bundle
2. 引入 support-agent support/adjust/counter relations
3. 把 replay/freeze evidence 变成 first-class reader source
4. 对 active bundle 增加 supersede policy
5. 为 report assembly 提供稳定 query façade

当前切片的目标不是一次做完，而是把 **first production-grade mid main path** 做对、做稳、做可扩展。
