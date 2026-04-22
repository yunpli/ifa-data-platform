# A股 FSJ Phase 1 首实现切片：Repository / Service 设计

## 1. 设计目标

本批次 repository 不追求“最终优雅抽象”，只追求三件事：

1. **生产可落地**：能真实写库、查库、保幂等
2. **审计友好**：对象关系、evidence、observed、report link 都能回查
3. **后续易扩展**：下一批可以自然接上 assembler / report consumer

因此本批次采用一个聚合入口：`FSJStore`。

## 2. 为什么先做 Store，不先做 ORM 大模型

当前 repo 已有明显工程风格：

- `archive_v2/db.py`
- `runtime/replay_evidence.py`

都偏向：

- SQL-first
- DDL 明确
- repository/store 直接操作 JSONB + 显式 SQL

FSJ 首切片继续沿这个风格，优点是：

- 与现有代码库一致
- 可控、透明、好审计
- 对 schema 变更敏感期更稳

## 3. `FSJStore` 提供的最小能力

## 3.1 `ensure_schema()`

用途：

- 本地开发与测试时幂等建表
- 作为 Alembic 之外的保底入口

不是为了替代正式 migration，而是为了契合 repo 当前已有双轨现实。

## 3.2 `upsert_bundle_graph(payload)`

输入是一个 bundle 聚合载荷，内部拆成：

- `bundle`
- `objects`
- `edges`
- `evidence_links`
- `observed_records`
- `report_links`

写入策略：

- bundle：按 `bundle_id` upsert
- object：按 `(bundle_id, fsj_kind, object_key)` upsert
- edge：按 `(bundle_id, edge_type, from_object_key, to_object_key)` upsert
- evidence / observed / report：按自然键唯一索引 upsert

这个接口故意是“一个 bundle graph 一次提交”，因为 FSJ 的真实消费面就是 bundle 级，而不是让上层零散地分别写 6 张表。

## 3.3 `get_active_bundle(...)`

按以下主维度查询：

- `business_date`
- `slot`
- `agent_domain`
- `section_key`
- 可选 `bundle_topic_key`

默认只取 `status='active'`，并返回完整 graph。

## 3.4 `get_bundle_graph(bundle_id)`

返回完整聚合视图：

- bundle
- objects
- edges
- evidence_links
- observed_records
- report_links

这是 Phase 1 最实用的 query surface。

## 4. 输入校验策略

本批次先做轻量校验：

- bundle 必填字段检查
- `status` 值域检查
- `fsj_kind` 值域检查
- `edge_type` / edge 两端 kind 检查

不在本批次里做：

- 全量 business contract schema validator
- `fact` / `signal` / `judgment` 的深层字段互斥/依赖校验

原因很简单：当前目标是把持久化骨架稳定落地，不在第一刀就把 assembler-validator-service 全部塞进来。

## 5. 为什么 `bundle_topic_key` 在 repository 里被显式支持

如果没有 topic 维度，`main_thesis`、`risk_watch` 这类 section 很容易出现：

- section 相同
- slot 相同
- 但 bundle 实际对应不同主题

这种情况下只靠 `section_key` 会逼出两个坏结果之一：

1. 主题被硬拼成一个 bundle，语义脏
2. 多 bundle 共存但查询面无法精确定位

所以 repository 从第一天就支持 `bundle_topic_key`，但保持 nullable，避免过早全局强制。

## 6. 未来扩展点

本设计后续可以自然扩到：

1. `FSJAssembler`：把 business-layer payload 规范化后交给 `FSJStore`
2. `FSJQueryService`：为 report-layer / QA 暴露更稳定的读接口
3. `FSJEvidenceHydrator`：按 slot replay / archive / source locator 自动富化证据上下文
4. `FSJSupersedeService`：提供 supersede/withdraw 专门操作而不是纯 upsert

## 7. 一句话结论

`FSJStore` 是一个刻意克制的 Phase 1 聚合仓储：先把 bundle graph 的“落、查、追”三件事做稳，再把更高级的 assembler / service / query façade 留给下一批扩展。
