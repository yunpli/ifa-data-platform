# A股 2.0 FSJ 本地持久化与存储策略（Phase 1）

_日期：2026-04-22_

## 1. 文档目的

这份文档定义 data-platform 对 A 股 2.0 FSJ 的 **本地持久化策略**。

目标不是直接拍板最终所有实现细节，而是把 Phase 1 必须落地的存储合同冻结下来，使 business-layer、data-platform、report-layer 后续不再反复争论：

- FSJ 在本地应以什么层次落盘
- 推荐的表模型是什么
- 主维度/主键怎么定
- observed representation 与 corrected representation 如何共存
- 怎么挂接 slot replay evidence / Archive V2 / source evidence / report artifacts
- Phase 1 现在必须做什么，哪些增强项留到后续

配套业务合同见：

- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_FSJ_PERSISTENCE_CONTRACT_PHASE1_2026-04-22.md`
- `/Users/neoclaw/repos/ifa-business-layer/docs/A_SHARE_FSJ_AND_EVIDENCE_MAPPING_V1.md`
- `docs/A_SHARE_REPORT_DATA_CONSUMPTION_AND_EVIDENCE_BOUNDARY_V1.md`
- `docs/FINAL_ARCHIVE_LAYER_REDESIGN_DEFINITION_2026-04-18_0058.md`

---

## 2. 当前系统现实（必须作为设计前提）

当前 repo 已经有三类与 FSJ 强相关、但语义不同的持久化层：

1. **runtime / collection 层**  
   - `lowfreq` / `midfreq` / `highfreq` working 与 history
   - 职责：采集、运行时状态、working truth、近端保留

2. **Archive V2 层**  
   - `ifa_archive_*` finalized truth 表
   - 以及 `ifa_archive_runs` / `ifa_archive_run_items` / `ifa_archive_completeness` / `ifa_archive_repair_queue`
   - 职责：长期 finalized historical truth、回放/研究/修复

3. **报告/运行证据层**  
   - slot replay evidence、run id、report artifact、运行日志、输出文件
   - 职责：说明“某次业务装配/输出到底基于什么输入和什么执行上下文”

FSJ 不应挤进任何一个现有层并假装等价。

正确定位是：

> **FSJ 是 business semantic layer 的本地持久化层。它引用 source truth、Archive V2、slot replay 和 report artifacts，但不替代它们。**

---

## 3. 设计原则

## 3.1 先支持可审计的最小图结构，再谈高级分析

Phase 1 的目标不是图数据库炫技，而是先保证：

- bundle 可查
- object 可查
- edge 可查
- evidence linkage 可查
- active/superseded 版本状态可查

## 3.2 物理模型可以是关系型，但语义必须保留图关系

FSJ 的关系本质上是图：

- fact -> signal
- signal -> judgment
- bundle -> evidence
- bundle -> report artifact

但 Phase 1 不需要引入专门图存储。

推荐做法：

- 用普通关系表保存对象
- 用 edges / links 表保存关联
- 保留 JSON payload 作为补充字段，而不是唯一真相

## 3.3 corrected business representation 必须与 observed source evidence 分离

当前系统里已经明确：

- Archive V2 是 finalized truth layer
- collection retained truth 与 archive finalized truth 不是同一个语义层

FSJ 也必须贯彻同样纪律：

- observed/source 证据引用不能丢
- corrected/business 表达不能被 source 原文直接替代

---

## 4. 推荐本地表模型（Phase 1）

Phase 1 推荐最少 4 张核心表 + 2 张链接表。

## 4.1 `ifa_fsj_bundles`

用途：保存一条 FSJ bundle 的业务上下文与版本语义。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null unique,
market text not null,
business_date date not null,
slot text not null,
agent_domain text not null,
section_key text not null,
section_type text not null,
producer text not null,
producer_version text not null,
assembly_mode text not null,
status text not null,                -- active|superseded|withdrawn
supersedes_bundle_id text null,
slot_run_id text null,
replay_id text null,
report_run_id text null,
summary text not null,
payload_json jsonb null,
created_at timestamptz not null,
updated_at timestamptz not null
```

建议唯一索引：

- `unique(bundle_id)`
- `idx_fsj_bundles_lookup(business_date, slot, agent_domain, section_key, status)`

### 为什么必须有 bundles 表

因为 report-layer、QA、回放查询的第一入口通常是：

- 某一天
- 某个 slot
- 某个 agent
- 某个 section

不是先从零散 fact 开始拼。bundle 是最自然的业务入口。

## 4.2 `ifa_fsj_objects`

用途：统一保存 fact / signal / judgment 对象。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null references ifa_fsj_bundles(bundle_id),
object_id text not null,
fsj_kind text not null,              -- fact|signal|judgment
object_key text not null,
statement text not null,
object_type text null,               -- fact_type / signal_type / judgment_type
judgment_action text null,
direction text null,
priority text null,
signal_strength text null,
horizon text null,
evidence_level text null,
confidence text null,
entity_refs jsonb null,
metric_refs jsonb null,
invalidators jsonb null,
attributes_json jsonb null,
created_at timestamptz not null
```

建议唯一索引：

- `unique(bundle_id, fsj_kind, object_key)`

建议查询索引：

- `(business_date via join, slot via join, agent_domain via join)`
- `(fsj_kind, object_type)`

### 为什么 object 统一表优于三张独立对象表

Phase 1 里用统一表更稳：

- 简化 bundle 全量读取
- 简化同一 object_key 不同 fsj_kind 的比较
- 减少早期 schema 反复变更成本

如果后续分析压力上来，再拆表也不晚。

## 4.3 `ifa_fsj_edges`

用途：保存对象间业务关系。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null references ifa_fsj_bundles(bundle_id),
edge_type text not null,             -- fact_to_signal|signal_to_judgment|judgment_to_judgment
from_fsj_kind text not null,
from_object_key text not null,
to_fsj_kind text not null,
to_object_key text not null,
role text null,                      -- support|counter|confirm|risk
created_at timestamptz not null
```

建议唯一索引：

- `unique(bundle_id, edge_type, from_object_key, to_object_key)`

### 为什么 edges 不能省

如果只有 objects，没有 edges，那么 `based_on_fact_keys` / `based_on_signal_keys` 最终只能藏在 JSON 里，下游查询和审计都会退化。

Phase 1 可以保留冗余字段，但 edges 表必须存在并成为正式查询面。

## 4.4 `ifa_fsj_evidence_links`

用途：挂接 source evidence / slot replay / Archive V2 / runtime control evidence。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null references ifa_fsj_bundles(bundle_id),
object_key text null,                -- null 表示作用于整个 bundle
fsj_kind text null,
evidence_role text not null,         -- source_observed|slot_replay|archive_background|runtime_run|report_material
ref_system text not null,            -- lowfreq|midfreq|highfreq|archive_v2|runtime|report
ref_family text null,
ref_table text null,
ref_key text null,
ref_locator_json jsonb null,
observed_at timestamptz null,
created_at timestamptz not null
```

### 关键语义

- 这张表保存“指向证据”的引用，不复制大块源数据。
- `object_key is null` 表示 bundle 级证据，如整次 slot replay。
- `object_key not null` 表示具体 fact/signal/judgment 级证据。

## 4.5 `ifa_fsj_observed_records`

用途：保存必要的 observed representation 摘要，避免 corrected 后彻底丢失原始表示。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null references ifa_fsj_bundles(bundle_id),
object_key text not null,
fsj_kind text not null,
source_layer text not null,
source_family text null,
source_table text null,
source_record_key text null,
observed_label text null,
observed_payload_json jsonb null,
created_at timestamptz not null
```

### 为什么 observed_records 值得单列

因为当前系统现实已经证明：

- source-side truth
- archive-final truth
- business-corrected truth

不能混成一个层。

FSJ 若只保存 corrected statement，将来做 replay/QA 时会失去“当时具体看到了什么”的可核查性。

## 4.6 `ifa_fsj_report_links`

用途：保存 FSJ bundle 与最终报告/导出物的关系。

建议字段：

```sql
id uuid/text primary key,
bundle_id text not null references ifa_fsj_bundles(bundle_id),
report_run_id text null,
artifact_type text not null,         -- markdown|html|telegram_message|snapshot|pdf
artifact_uri text null,
artifact_locator_json jsonb null,
section_render_key text null,
created_at timestamptz not null
```

这张表让“报告产物”成为可回查对象，而不是只能靠聊天记录找。

---

## 5. 主维度 / 主键建议

## 5.1 查询主维度

FSJ 的主查询维度应该稳定围绕以下组合展开：

- `market`
- `business_date`
- `slot`
- `agent_domain`
- `section_key`
- `status`

这是 Phase 1 最重要的运营查询面。

## 5.2 业务幂等键

建议 bundle 幂等键：

- `market + business_date + slot + agent_domain + section_key + bundle_topic_key + producer_version`

建议 object 幂等键：

- `bundle_id + fsj_kind + object_key`

建议 edge 幂等键：

- `bundle_id + edge_type + from_object_key + to_object_key`

### 为什么不能只靠 statement 去重

因为：

- 文案会微调
- 相同意思可能换表述
- 同 statement 在不同 slot/business_date 语义不同

所以只能把 `statement` 当内容字段，不能当主键。

---

## 6. observed vs corrected representation：本地怎么落

## 6.1 当前观察到的错误倾向

如果不提前冻结口径，FSJ 落盘很容易滑向以下错误表示：

1. **只存 corrected judgment 文案**  
   - 结果：无法还原证据来源

2. **把 source row 直接当 business object**  
   - 结果：业务语义没被显式建模

3. **把整个 bundle 当一个 summary blob**  
   - 结果：无法逐层查询 fact / signal / judgment

## 6.2 正确表示

Phase 1 应采用“双层表示”策略：

### observed representation

保存在：

- `ifa_fsj_evidence_links`
- `ifa_fsj_observed_records`

内容包括：

- source layer / family / table / row key
- 原始标题、原始主题名、原始值片段
- slot replay 包里的冻结对象摘要
- Archive V2 row_key / family / business_date 引用

### corrected representation

保存在：

- `ifa_fsj_bundles`
- `ifa_fsj_objects`
- `ifa_fsj_edges`

内容包括：

- 归一后的 `object_key`
- 业务 statement
- `signal_type` / `judgment_action` / `direction`
- 实际采用的 lineage 边关系

### 关键纪律

> observed 是“看到了什么”；corrected 是“业务最终怎么表达”。两者必须可链接，但不能混为一个字段。

---

## 7. 与 slot replay / Archive V2 / source evidence / report artifacts 的挂接合同

## 7.1 slot replay evidence

Phase 1 必须支持：

- bundle 级关联到某次 `slot_run_id` / `replay_id`
- 必要时 object 级关联到 replay package 内的具体对象 key/hash

推荐做法：

- `ifa_fsj_bundles.slot_run_id` / `replay_id` 保存快捷入口
- `ifa_fsj_evidence_links` 保存更细的 replay object locator

## 7.2 Archive V2

FSJ 对 Archive V2 的关系是“引用 finalized background truth”，不是“写进 Archive V2 代替 FSJ”。

Phase 1 必须支持以下引用：

- `ifa_archive_*` 的 `family/table`
- `business_date`
- `row_key` 或可恢复定位的 locator
- 对应 archive run id（若需要）

适用场景：

- 晚报引用 T-1 / same-day finalized 背景
- QA / replay 时说明 judgment 使用了哪批 archive-final facts

## 7.3 source evidence

source evidence 主要来自：

- `lowfreq` / `midfreq` / `highfreq` history 或 working
- 文本 history 表
- working snapshot / event stream

Phase 1 不要求平台对每条 evidence 做硬 FK，但必须能保存：

- source_layer
- source_family / source_table
- record locator（主键、row_key、hash、时间戳、symbol、title/url 等任一足够定位的组合）

## 7.4 report artifacts

FSJ 与 report artifact 的关系也必须是一等公民：

- 哪个 bundle 最终进入了哪次 report run
- 被渲染到哪个 section
- 对应 markdown/html/pdf/telegram message 在哪里

如果没有这层链接，未来用户问“这段结论当时来自哪条 judgment”，系统仍然答不出来。

---

## 8. 版本与 supersede 语义

盘前/盘中/晚间同一 section 可能出现修订；盘中也可能因为 replay/人工纠错导致 bundle 重建。

Phase 1 不应采用“直接覆盖旧记录、历史消失”的策略。

建议语义：

- `active`：当前默认消费版本
- `superseded`：被更晚的 bundle 替代
- `withdrawn`：明确撤回、不应继续用于 report/QA

建议规则：

- report-layer 默认只消费 `active`
- QA/replay 可以查看全版本链
- 若是修订写入，保留 `supersedes_bundle_id`

---

## 9. Phase 1 实施边界

## 9.1 Phase 1 必须做

1. 至少落 bundles / objects / edges / evidence_links 四类正式表。  
2. 支持 bundle 级 active/superseded/withdrawn。  
3. 支持通过 `business_date + slot + agent_domain + section_key` 查到 active bundle。  
4. 支持从 judgment 反查 signals，再反查 facts。  
5. 支持从 bundle 或 object 反查到 slot replay / Archive V2 / source evidence / report artifact。  
6. observed representation 至少要能摘要保存，不能只剩 corrected 文案。  

## 9.2 Phase 1 可以暂缓

1. 不要求把所有 evidence 引用做成数据库硬 FK。  
2. 不要求通用全文检索/向量检索。  
3. 不要求跨市场统一抽象到 US / macro 全覆盖。  
4. 不要求自动质量评分、命中率归因、graph analytics。  
5. 不要求把 Archive V2 原始 payload 再完整复制一份到 FSJ 层。  

---

## 10. 推荐查询面（实现时应优先支持）

至少应支持以下查询：

1. 某日某 slot 某 agent 的 active FSJ bundles。  
2. 某个 section_key 当前 active judgment 列表。  
3. 某条 judgment 的上游 signals/facts。  
4. 某条 fact 对应的 source evidence locator。  
5. 某个 report artifact 使用了哪些 bundles。  
6. 某次 replay/slot_run 产生了哪些 bundles。  
7. 某 bundle 的 supersede 历史链。  

这是比“先做漂亮 schema”更重要的 Phase 1 验收标准。

---

## 11. 一句话冻结结论

A 股 2.0 的 FSJ 本地持久化在 Phase 1 已明确为：

> **以 bundles / objects / edges / evidence-links 为核心的关系型本地语义层，显式区分 observed source evidence 与 corrected business representation，并可挂接 slot replay、Archive V2、source tables、report artifacts；FSJ 不替代 source truth，也不退化成 summary blob。**
