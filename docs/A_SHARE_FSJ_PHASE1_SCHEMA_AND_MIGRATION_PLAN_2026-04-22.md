# A股 FSJ Phase 1 首实现切片：Schema / Migration 计划

## 1. 目标

本批次不是继续讨论 FSJ 合同，而是把已冻结合同落成 **可执行、可测试、可审计** 的 data-platform 首切片实现。

本切片范围严格限制为：

1. 正式落表：`bundles / objects / edges / evidence_links / observed_records / report_links`
2. 明确版本语义：`active | superseded | withdrawn`
3. 明确 observed / corrected 双层表示的物理挂点
4. 提供一个最小可用 repository，支持写入、回查、链路追溯
5. 提供 integration tests，证明 schema 假设与 round-trip 成立

不在本切片内：

- 自动 FSJ 装配器
- report-layer 对 FSJ 的全面消费接线
- 通用 graph analytics / FTS / vector search
- 跨市场统一抽象

## 2. 本切片为什么选这 6 张表

虽然合同里说 Phase 1 最低核心是 4 张表（bundles / objects / edges / evidence_links），但从生产角度首切片只做 4 张会留下两个明显缺口：

1. **observed representation 无专门承载点**
   - 会逼着系统把 observed 信息塞进 evidence link locator 或 object attributes，后续一定脏
2. **report artifact 无正式关系面**
   - 未来做“这段结论当时落在哪个输出物里”时仍要翻聊天/文件

所以本批次直接把 `observed_records` 与 `report_links` 一起落下，但仍保持整体 scope 很小。

## 3. 核心建模决策

## 3.1 bundle 作为业务入口

`ifa_fsj_bundles` 是主入口，不从散落 fact 开始拼装。

主查询面优先围绕：

- `business_date`
- `slot`
- `agent_domain`
- `section_key`
- `status`
- `bundle_topic_key`（可空）

说明：本批次比最初草案多加了 `bundle_topic_key`，原因是合同已经显式提出 bundle 幂等建议里存在 topic 维度；没有它，`main_thesis` 这类 section 很容易无法承载同 slot 多主题并行 bundle。

## 3.2 object 统一表而不是三张表

Phase 1 仍坚持统一 `ifa_fsj_objects`：

- 减少 schema 抖动
- 降低一次性拆分成本
- 读取 bundle graph 更直接

差异字段通过：

- `object_type`
- `judgment_action`
- `direction`
- `priority`
- `signal_strength`
- `attributes_json`

承接。

## 3.3 observed 与 corrected 的物理边界

- corrected/business semantic layer：
  - `ifa_fsj_bundles`
  - `ifa_fsj_objects`
  - `ifa_fsj_edges`
- observed/audit hooks：
  - `ifa_fsj_evidence_links`
  - `ifa_fsj_observed_records`
- report artifact linkage：
  - `ifa_fsj_report_links`

这保证：

- corrected 语义不会退化成 source row copy
- observed 证据不会因为 corrected statement 成形而丢失

## 3.4 version 语义

本切片只冻结 bundle 级版本状态：

- `active`
- `superseded`
- `withdrawn`

并支持：

- `supersedes_bundle_id`
- `get_active_bundle(...)`
- 全版本历史回查

本切片**不强行加“每个 section 只能有一个 active”硬约束**，因为 `bundle_topic_key` 允许同一 section 下多 bundle 共存；唯一性留在 `bundle_id` 和业务写入方的 topic 纪律层处理。

## 4. migration 策略

## 4.1 Alembic revision

新增：

- `alembic/versions/039_fsj_persistence_phase1.py`

特点：

- 全部对象进 `ifa2` schema
- 显式唯一约束 / check constraint / 索引
- downgrade 完整可回滚

## 4.2 兼容现有 repo 的双轨方式

本 repo 既有 Alembic 迁移，也有 runtime/store 内 `ensure_schema()` 风格的 idempotent DDL 保底。

因此本批次采用：

1. Alembic 作为正式迁移定义
2. `FSJStore.ensure_schema()` 作为测试 / 本地开发 / 早期接线的幂等保底

这与 `archive_v2`、`slot_replay_evidence` 在 repo 中的现有工程现实保持一致。

## 5. 索引与约束

## 5.1 bundles

- `unique(bundle_id)`
- `ix_ifa_fsj_bundles_lookup(business_date, slot, agent_domain, section_key, status, bundle_topic_key)`
- `ix_ifa_fsj_bundles_supersedes(supersedes_bundle_id)`

## 5.2 objects

- `unique(bundle_id, fsj_kind, object_key)`
- `unique(bundle_id, object_id)`
- `ix_ifa_fsj_objects_kind_type(fsj_kind, object_type)`

## 5.3 edges

- `unique(bundle_id, edge_type, from_object_key, to_object_key)`

## 5.4 evidence / observed / report links

三类 link-like 表都使用 **自然键唯一索引**，目标是：

- 幂等重写不会爆炸复制
- 允许 repository 用 upsert 形式稳定落盘

## 6. 首切片验收标准

本批次完成后，至少要能证明：

1. 能写入一个完整 FSJ bundle graph
2. 能从 `business_date + slot + agent_domain + section_key (+ topic)` 查回 active bundle
3. 能从 judgment 反查 signals / facts（通过 edges）
4. 能看到 bundle/object 对应的 evidence links
5. 能看到 observed record 摘要
6. 能看到 report artifact link
7. 同一 bundle 重复写入时保持幂等，不膨胀重复行

## 7. 下一切片建议（不是本批次）

1. business-layer -> data-platform 的显式 FSJ payload schema / adapter
2. 基于 `slot_run_id` / `replay_id` 的自动 evidence hydration
3. report-layer 查询封装与 section consumption API
4. supersede 链的 operator/QA 可视化

## 8. 一句话结论

本批次把 FSJ Phase 1 从“合同与策略”推进到“真实 schema + migration + repository + tests”，并且首刀就把 observed/corrected/version/report-linkage 这些最容易后期返工的硬边界一次性钉住。
