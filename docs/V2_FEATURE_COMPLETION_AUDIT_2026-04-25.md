# V2 Feature Completion Audit + Data Truth Audit (2026-04-25)

## Audit scope and method

This audit was executed as an **audit-first, no-schema-change, no-collector-expansion** pass across:
- repo: `/Users/neoclaw/repos/ifa-data-platform`
- repo: `/Users/neoclaw/repos/ifa-business-layer`
- DB schema: `ifa2`
- primary required context docs:
  - `docs/IFA_Execution_Context_and_Behavior.md`
  - `docs/IFA_Execution_Progress_Monitor.md`
  - `IFA_Implementation_Enhancement_Task_List_V2.md`
  - `docs/POST_P6_DB_TRUTH_001_DB_TABLE_TRUTH_AND_REPORT_DATA_CONTRACT_AUDIT_2026-04-25.md`

This document intentionally re-checks repo + DB truth instead of trusting prior acceptance framing.

---

## 1) V2 Feature Completion Audit

Audit basis: every active-work task from `IFA_Implementation_Enhancement_Task_List_V2.md` under the current/near-term execution lanes:
- `3.1.*` current reality reclassification
- `3.2.*` current missing-capability reclassification
- `1.1.*` to `1.5.*` P0 weekend tasks
- `2.1.*` to `2.3.*` immediate-after P1 tasks

Status vocabulary used exactly as required:
- `done`
- `bounded_done`
- `partial`
- `not_started`
- `blocked`
- `deferred_by_design`

### 1.1 Task-by-task audit

#### 3.1.1 已有完整但分散的报告生产流程组件
- **current status**: `done`
- **completed evidence**:
  - `scripts/fsj_main_early_publish.py`, `scripts/fsj_main_mid_publish.py`, `scripts/fsj_main_late_publish.py`
  - `scripts/fsj_main_report_publish.py`, `scripts/fsj_main_report_morning_delivery.py`, `scripts/fsj_support_batch_publish.py`
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
  - persisted/report tables already in use: `ifa2.ifa_fsj_bundles`, `ifa2.ifa_fsj_report_artifacts`, `ifa2.ifa_fsj_report_links`
- **related files**:
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
  - `scripts/fsj_main_report_publish.py`
  - `scripts/fsj_support_batch_publish.py`
- **related commits**:
  - historical closure recorded in `docs/IFA_Execution_Progress_Monitor.md` under `V2-R0-003`
- **tests run**:
  - prior CLI help / generate / status probes recorded in progress monitor
- **current sample / artifact**:
  - `artifacts/v2_r0_003_validation/*`
- **residual gap**:
  - components exist, but operator mental model is still script-fragmented
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - keep the existing chain; do not re-architect it again for naming/polish only

#### 3.1.2 已有 business-layer LLM utility / gateway，但默认策略不够强
- **current status**: `done`
- **completed evidence**:
  - `src/ifa_data_platform/fsj/llm_assist.py` shells into business-layer CLI bridge
  - `ifa-business-layer/config/llm/models.yaml` contains `grok41_expert`, `grok41_thinking`, `gemini31_pro_jmr`
  - policy block explicitly says business-layer gateway is the formal path
- **related files**:
  - `src/ifa_data_platform/fsj/llm_assist.py`
  - `/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml`
  - `/Users/neoclaw/repos/ifa-business-layer/scripts/ifa_llm_cli.py`
- **related commits**:
  - progress monitor `V2-R0-006`: DP `f68b381` / `e9f118f`; BL `f7511bb`
- **tests run**:
  - `tests/unit/test_fsj_early_llm_assist.py`
  - support producer tests recorded in progress monitor
- **current sample / artifact**:
  - LLM policy/role lineage appears in main publish/operator summary surfaces
- **residual gap**:
  - policy exists, but product quality is still constrained more by deterministic content wiring than by model choice
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - freeze model-policy churn until report-content completeness is fixed

#### 3.1.3 已有 FSJ 主链，但当前产品面不是 unified operator surface
- **current status**: `bounded_done`
- **completed evidence**:
  - `scripts/fsj_report_cli.py` now exists and wraps main/support generate/status/registry
  - it threads `subject`, `slot`, `mode`, `output_profile`, `output_root`
- **related files**:
  - `scripts/fsj_report_cli.py`
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
- **related commits**:
  - `edcbb3e72f006f0c5c19d2930d0ff3dbaf58e57a`
- **tests run**:
  - help / generate / status probes recorded under `V2-R0-003`
- **current sample / artifact**:
  - `artifacts/v2_r0_003_validation/command_outputs/*.json`
- **residual gap**:
  - unified CLI exists, but it remains a thin wrapper over mixed legacy semantics; not all report truth/completeness concerns are unified behind it
- **affects final customer-grade iFA report**: indirectly yes
- **next-step recommendation**:
  - treat the CLI as sufficiently closed for now; shift effort to data/use-contract closure

#### 3.2.1 还没有统一的报告生成控制入口
- **current status**: `bounded_done`
- **completed evidence**:
  - `scripts/fsj_report_cli.py generate/status/registry`
  - main/support flow selection implemented
- **related files**:
  - `scripts/fsj_report_cli.py`
- **related commits**:
  - `edcbb3e72f006f0c5c19d2930d0ff3dbaf58e57a`
- **tests run**:
  - CLI probes recorded in progress monitor
- **current sample / artifact**:
  - `artifacts/v2_r0_003_validation`
- **residual gap**:
  - no new canonical semantic layer for content truth; only control-plane closure
- **affects final customer-grade iFA report**: indirectly yes
- **next-step recommendation**:
  - no further CLI work before report data/use gaps are fixed

#### 3.2.2 还没有严格对齐 customer/internal/review 三类输出面的产品层
- **current status**: `bounded_done`
- **completed evidence**:
  - renderer has customer/internal/review branching
  - main/support publish wrappers thread `output_profile`
  - customer HTML hides engineering-visible package/lineage details
- **related files**:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
  - `scripts/fsj_main_report_publish.py`
  - `scripts/fsj_support_report_publish.py`
- **related commits**:
  - `1fc24b83fd87820f7599ffbb678ac24501483015`
  - `fb789d3`, `e3d4aef`
- **tests run**:
  - `tests/unit/test_fsj_report_rendering.py`
  - `tests/unit/test_fsj_main_report_publish_script.py`
  - `tests/unit/test_fsj_support_report_publish_script.py`
- **current sample / artifact**:
  - multiple customer/review dry-run HTMLs recorded in `artifacts/accept_p1_001`, `artifacts/post_p1_customer_report_001`, `artifacts/post_p5_section_prose_001`
- **residual gap**:
  - profile separation is mostly presentation-layer; data completeness is still not profile-complete
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - stop profile polishing; treat profile seam as closed enough

#### 3.2.3 还没有把 stronger LLM usage 收紧到 strict evidence / time-window / schema policy 下
- **current status**: `done`
- **completed evidence**:
  - `build_fsj_role_policy()` in `llm_assist.py`
  - slot-specific forbidden decisions / boundary invariants / deterministic owner fields
  - business-layer model strategy config in `models.yaml`
- **related files**:
  - `src/ifa_data_platform/fsj/llm_assist.py`
  - `/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml`
- **related commits**:
  - `V2-R0-006` commit set plus later field-lineage tightening on branch head
- **tests run**:
  - `tests/unit/test_fsj_early_llm_assist.py`
- **current sample / artifact**:
  - operator summary surfaces expose LLM lineage status and policy versions
- **residual gap**:
  - deterministic upstream payload still thin; stricter policy cannot invent missing market content
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - keep policy stable; enrich deterministic evidence routing instead

#### 3.2.4 还没有一套“周末停 runtime + 修改 + 回放 + 重启”的正式纪律
- **current status**: `bounded_done`
- **completed evidence**:
  - freeze plan doc and runtime snapshots exist
- **related files**:
  - `docs/V2_R0_001_WEEKEND_RUNTIME_FREEZE_PLAN_2026-04-24.md`
  - `artifacts/runtime_freeze/*`
- **related commits**:
  - `3c07c8e`
- **tests run**:
  - runtime status / preflight commands recorded in progress monitor
- **current sample / artifact**:
  - `artifacts/runtime_freeze/runtime_process_snapshot_20260424_1758_PDT.txt`
- **residual gap**:
  - process discipline exists as doc/runbook, not as a hardened operator control plane
- **affects final customer-grade iFA report**: indirectly
- **next-step recommendation**:
  - sufficient for now; no more freeze/runbook work before report truth closure

#### 1.1.1 制定并执行“周末 runtime 冻结窗口”方案
- **current status**: `done`
- **completed evidence**:
  - freeze plan and pre-freeze state snapshots committed
- **related files**:
  - `docs/V2_R0_001_WEEKEND_RUNTIME_FREEZE_PLAN_2026-04-24.md`
- **related commits**:
  - `3c07c8e`
- **tests run**:
  - runtime status/preflight command set in progress monitor
- **current sample / artifact**:
  - `artifacts/runtime_freeze/*`
- **residual gap**:
  - none material for this task
- **affects final customer-grade iFA report**: no direct content effect
- **next-step recommendation**:
  - keep as historical execution evidence only

#### 1.1.2 建立周末 rollback / restart checklist
- **current status**: `bounded_done`
- **completed evidence**:
  - rollback/restart discipline captured in freeze plan / execution behavior docs
- **related files**:
  - `docs/IFA_Execution_Context_and_Behavior.md`
  - `docs/V2_R0_001_WEEKEND_RUNTIME_FREEZE_PLAN_2026-04-24.md`
- **related commits**:
  - `487df77f749ffbe013bcaa4cd139244020904f8e`, `3c07c8e`
- **tests run**:
  - procedural, doc-reviewed
- **current sample / artifact**:
  - runtime freeze artifacts
- **residual gap**:
  - checklist is operational, not system-enforced
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - defer further hardening unless runtime work resumes

#### 1.2.1 先做 CLI audit 收口：列出现有命令能覆盖什么、不能覆盖什么
- **current status**: `done`
- **completed evidence**:
  - dedicated audit doc + validation outputs committed
- **related files**:
  - `docs/V2_R0_003_UNIFIED_REPORT_CLI_AUDIT_AND_CLOSURE_2026-04-24.md`
  - `scripts/fsj_report_cli.py`
- **related commits**:
  - `edcbb3e72f006f0c5c19d2930d0ff3dbaf58e57a`
- **tests run**:
  - help / generate / status probes in progress monitor
- **current sample / artifact**:
  - `artifacts/v2_r0_003_validation/command_outputs/*`
- **residual gap**:
  - audit was honest, but later execution over-focused on surface polish
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - keep as baseline; do not reopen unless CLI semantics break

#### 1.2.2 实现最小 canonical command，统一控制 main / support 报告生成
- **current status**: `bounded_done`
- **completed evidence**:
  - `scripts/fsj_report_cli.py generate --subject main|support`
- **related files**:
  - `scripts/fsj_report_cli.py`
- **related commits**:
  - `edcbb3e72f006f0c5c19d2930d0ff3dbaf58e57a`
- **tests run**:
  - dry-run generate probes recorded in monitor
- **current sample / artifact**:
  - `artifacts/v2_r0_003_validation/main_early_2026-04-23_dry_run`
  - `artifacts/v2_r0_003_validation/support_late_2026-04-23_dry_run`
- **residual gap**:
  - command unifies execution, not content contract quality
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - freeze CLI; move to content/data completeness

#### 1.2.3 为 unified CLI 加入 replay / backfill-test / dry-run 周末验证面
- **current status**: `bounded_done`
- **completed evidence**:
  - mode surface exists in wrapper: `realtime`, `replay`, `backfill-test`, `dry-run`
  - business-layer CLI drift/replay closure task completed
- **related files**:
  - `scripts/fsj_report_cli.py`
  - `/Users/neoclaw/repos/ifa-business-layer/scripts/ifa_llm_cli.py`
- **related commits**:
  - `1a442c9` (BL), `4ce1ac5` (DP)
- **tests run**:
  - replay-mode probe commands recorded in progress monitor
- **current sample / artifact**:
  - `artifacts/post_p0_bldrift_probe`
- **residual gap**:
  - wrapper semantics still rely on isolated output-root routing, not full native replay semantics across all flows
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - good enough for audit/debug use; do not widen before content fix

#### 1.3.1 建立 customer / internal / review 三种 output profile
- **current status**: `done`
- **completed evidence**:
  - renderer/publish path profile threading is landed and tested
- **related files**:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/main_publish_cli.py`
  - `scripts/fsj_main_early_publish.py`
  - `scripts/fsj_support_batch_publish.py`
- **related commits**:
  - `1fc24b83fd87820f7599ffbb678ac24501483015`
  - `fb789d3`, `e3d4aef`
- **tests run**:
  - renderer and publish tests in progress monitor
- **current sample / artifact**:
  - customer/review/internal dry-run outputs across `artifacts/accept_p1_001` and related task artifacts
- **residual gap**:
  - none material at profile-routing level
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - consider closed

#### 1.3.2 客户版先做“内容减噪 + 结构重排”，不追求一次性重写全模板体系
- **current status**: `done`
- **completed evidence**:
  - multiple customer-only renderer passes: editorial compression, phrase sanitization, section prose, watchlist naming
  - `ACCEPT-P6-001` reports section-level editorial acceptance pass
- **related files**:
  - `src/ifa_data_platform/fsj/report_rendering.py`
- **related commits**:
  - `ae28b0d`, `f8eb951`, `3a7b938`, `a9f0876`, plus later customer copy adjustments on branch head `31d0260`
- **tests run**:
  - repeated `tests/unit/test_fsj_report_rendering.py`
- **current sample / artifact**:
  - `artifacts/post_p5_section_prose_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T064752Z.html`
- **residual gap**:
  - wording is now much cleaner, but still often describing thin upstream content rather than rich report substance
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - stop customer prose tuning until upstream data/use completeness improves

#### 1.3.3 先把 reports 正式输出目录和 artifacts 分层清楚
- **current status**: `bounded_done`
- **completed evidence**:
  - report registry/manifest tightening completed
  - artifact lineage/registry query path exists
- **related files**:
  - `src/ifa_data_platform/fsj/store.py`
  - `scripts/fsj_artifact_lineage.py`
  - `scripts/fsj_report_cli.py`
- **related commits**:
  - `ced7863e650b1c1d258d8e0dced9b0b7a382562d`, `6466a3904274df4c6b1a118af533ed8e7d3dfd60`
- **tests run**:
  - `tests/unit/test_fsj_store_json_serialization.py`
  - `tests/unit/test_fsj_artifact_lineage_script.py`
  - `tests/unit/test_fsj_report_cli_registry.py`
- **current sample / artifact**:
  - active report surfaces in `ifa2.ifa_fsj_report_artifacts`
- **residual gap**:
  - repo working tree still mixes large local artifacts and untracked output; operational cleanliness is not fully closed
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - do not rework storage layout now; only document operator expectations

#### 1.4.1 明确本周末 LLM 策略：必须走 business-layer utility / gateway
- **current status**: `done`
- **completed evidence**:
  - current code path already enforces this
- **related files**:
  - `src/ifa_data_platform/fsj/llm_assist.py`
  - `/Users/neoclaw/repos/ifa-business-layer/scripts/ifa_llm_cli.py`
- **related commits**:
  - `V2-R0-006` closure set
- **tests run**:
  - LLM assist smoke/unit tests in progress monitor
- **current sample / artifact**:
  - operator summary LLM lineage metadata
- **residual gap**:
  - none material on routing policy
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - closed

#### 1.4.2 模型优先级改为“Grok 4.1 Expert 优先，否则选择最接近 expert-like 的已配置策略”
- **current status**: `done`
- **completed evidence**:
  - `DEFAULT_FSJ_PRIMARY_MODEL_ALIAS = "grok41_expert"`
  - fallback chain explicitly configured
- **related files**:
  - `src/ifa_data_platform/fsj/llm_assist.py`
  - `/Users/neoclaw/repos/ifa-business-layer/config/llm/models.yaml`
- **related commits**:
  - `V2-R0-006` closure set
- **tests run**:
  - same as above
- **current sample / artifact**:
  - policy/config files
- **residual gap**:
  - actual report substance is still bottlenecked upstream, not by model rank
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - closed

#### 1.4.3 把 stronger LLM usage 明确限制在 strict evidence / time-window / schema boundary 内
- **current status**: `done`
- **completed evidence**:
  - explicit slot policy, deterministic owner fields, override precedence, forbidden decisions
- **related files**:
  - `src/ifa_data_platform/fsj/llm_assist.py`
- **related commits**:
  - `V2-R0-006` plus later lineage tightening
- **tests run**:
  - `tests/unit/test_fsj_early_llm_assist.py`
- **current sample / artifact**:
  - role policy payloads in operator/review surfaces
- **residual gap**:
  - none on policy definition; real gap is missing deterministic evidence use
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - closed

#### 1.5.1 产出一套 weekend golden samples（以报告产品层为中心）
- **current status**: `done`
- **completed evidence**:
  - multiple acceptance/golden sample artifacts exist across P0-P6 and post-P tasks
- **related files**:
  - `docs/V2_P0_ACCEPTANCE_SUMMARY_2026-04-25.md`
  - `docs/V2_P1_GOLDEN_SAMPLE_ACCEPTANCE_2026-04-25.md`
  - `docs/V2_P6_FINAL_SECTION_LEVEL_EDITORIAL_ACCEPTANCE_2026-04-25.md`
- **related commits**:
  - `0f9fe4d`, `b9f6339`, `a9f0876`
- **tests run**:
  - repeated dry-run sample generation commands recorded in progress monitor
- **current sample / artifact**:
  - see HTML bookkeeping section below
- **residual gap**:
  - golden samples exist, but current chosen golden date/sample overstates overall V2 completeness
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - re-baseline “golden sample” around data-backed completeness, not customer copy quality alone

#### 1.5.2 用 unified CLI 跑一次完整 weekend 执行演示序列
- **current status**: `bounded_done`
- **completed evidence**:
  - acceptance/probe artifacts include main/support dry-runs via unified CLI
- **related files**:
  - `scripts/fsj_report_cli.py`
  - acceptance docs/artifacts
- **related commits**:
  - see `ACCEPT-P0-001`, `ACCEPT-P1-001`
- **tests run**:
  - CLI dry-run commands in monitor
- **current sample / artifact**:
  - `artifacts/accept_p0_001/*`, `artifacts/accept_p1_001/*`
- **residual gap**:
  - “demonstrated execution” does not equal content-complete report system
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - no more demo-sequence work until content closure

#### 2.1.1 从 package-level review 升级到 judgment item 级 review
- **current status**: `bounded_done`
- **completed evidence**:
  - judgment review/mapping foundation added
- **related files**:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/store.py`
- **related commits**:
  - `1bc194a`, `17fafa3`
- **tests run**:
  - `tests/unit/test_fsj_report_rendering.py`
  - `tests/unit/test_fsj_main_report_publish_script.py`
- **current sample / artifact**:
  - review surfaces include judgment mapping ledger material
- **residual gap**:
  - foundation exists, but not yet a mature operator review workflow
- **affects final customer-grade iFA report**: indirect but important
- **next-step recommendation**:
  - treat as bounded_done until a real operator review use-case demands more

#### 2.1.2 建立 evidence → support → main → customer wording 的映射台账
- **current status**: `partial`
- **completed evidence**:
  - renderer now emits some judgment mapping / learning asset candidate info
  - minimal ledger surfaces exist
- **related files**:
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/store.py`
- **related commits**:
  - `1bc194a`, `17fafa3`
- **tests run**:
  - renderer/publish tests only
- **current sample / artifact**:
  - mapping ledger fields in manifests/review surfaces
- **residual gap**:
  - no fully trustworthy end-to-end mapping ledger proving how major customer claims derive from real DB evidence and support bundles
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - this should be one of the next real implementation tasks

#### 2.2.1 把 reports 正式目录、artifact registry、manifest schema 做成统一契约
- **current status**: `bounded_done`
- **completed evidence**:
  - registry/artifact lineage/manifest closure task pushed
- **related files**:
  - `src/ifa_data_platform/fsj/store.py`
  - `scripts/fsj_artifact_lineage.py`
  - `scripts/fsj_report_cli.py`
- **related commits**:
  - `ced7863e650b1c1d258d8e0dced9b0b7a382562d`, `6466a3904274df4c6b1a118af533ed8e7d3dfd60`
- **tests run**:
  - registry/store tests in monitor
- **current sample / artifact**:
  - report artifacts and manifest pointers in DB/operator summary
- **residual gap**:
  - contract exists, but does not solve content truth gaps
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - closed enough

#### 2.2.2 把发送回执、状态查询、operator status 收口到统一状态面
- **current status**: `bounded_done`
- **completed evidence**:
  - `fsj_report_cli.py status`, delivery status scripts, operator board surfaces exist
- **related files**:
  - `scripts/fsj_report_cli.py`
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`
- **related commits**:
  - `V2-R0-003` and registry closure commits
- **tests run**:
  - CLI status probes in monitor
- **current sample / artifact**:
  - status JSON artifacts in `artifacts/v2_r0_003_validation/command_outputs`
- **residual gap**:
  - operationally adequate; not the current bottleneck
- **affects final customer-grade iFA report**: indirect only
- **next-step recommendation**:
  - closed enough

#### 2.3.1 在不改变周末主线的前提下补图表最小闭环
- **current status**: `bounded_done`
- **completed evidence**:
  - chart pack exists and is wired to main/customer HTML and delivery package
- **related files**:
  - `src/ifa_data_platform/fsj/chart_pack.py`
  - `src/ifa_data_platform/fsj/report_rendering.py`
- **related commits**:
  - `4473c78`
- **tests run**:
  - chart/rendering tests in monitor
- **current sample / artifact**:
  - chart manifests under generated publish dirs
- **residual gap**:
  - chart pack remains narrow: index + focus line/bar only; readiness frequently partial because input data are sparse and symbol selection is default-seed driven
- **affects final customer-grade iFA report**: yes
- **next-step recommendation**:
  - expand only after focus/customer contract is fixed

#### 2.3.2 把 focus / key-focus 提升为报告正式模块
- **current status**: `partial`
- **completed evidence**:
  - producer pulls DB focus list items and metadata
  - renderer builds formal focus module and watchlist tiers
  - chart pack prioritizes key-focus symbols
- **related files**:
  - `src/ifa_data_platform/fsj/early_main_producer.py`
  - `src/ifa_data_platform/fsj/report_rendering.py`
  - `src/ifa_data_platform/fsj/chart_pack.py`
- **related commits**:
  - `0611241`, `6d01af8`, `b5bbf79`, `7c073b7`, `ca8bf7b`, branch head `31d0260`
- **tests run**:
  - `tests/unit/test_fsj_main_early_producer.py`
  - `tests/unit/test_fsj_report_rendering.py`
  - `tests/unit/test_fsj_early_llm_assist.py`
- **current sample / artifact**:
  - `artifacts/post_p6_db_backed_focus_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T075756Z.html`
  - `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.html`
- **residual gap**:
  - module is formalized technically, but customer-facing semantics are still wrong: default seed lists are being shown as if they were formal customer focus pools
- **affects final customer-grade iFA report**: yes, materially
- **next-step recommendation**:
  - separate collection/archive seed scope from customer-facing focus display contract before any more wording polish

### 1.2 Summary judgment on V2 task audit

- **clearly done / bounded_done**: runtime freeze discipline, unified CLI, output profile separation, LLM boundary policy, registry/manifest, basic chart pack
- **still materially partial**:
  - focus/key-focus productization as a customer contract
  - evidence → support → main → customer mapping ledger
  - actual report content completeness vs available DB truth
- **important meta-finding**:
  - many recent passes closed **presentation seams** and **operator seams**, not the deeper **data-use completeness seam**

---

## 2) Focus / Key-Focus Seed Truth

### 2.1 Direct DB truth

#### focus_lists overview

Live DB query result in `ifa2.focus_lists`:
- owner scope present: only **`owner_type=default`, `owner_id=default`**
- total lists: **11**
- families:
  - archive targets: 3
  - focus: 4
  - key_focus: 4

Current lists:
- `default_stock_key_focus` (`key_focus`, `asset_type=stock`) — 20 active items
- `default_stock_focus` (`focus`, `asset_type=stock`) — 80 active items
- `default_macro_key_focus` — 5
- `default_macro_focus` — 10
- `default_tech_key_focus` — 20
- `default_tech_focus` — 50
- `default_asset_key_focus` — 12
- `default_asset_focus` — 20
- `default_archive_targets_minute` — 19
- `default_archive_targets_15min` — 36
- `default_archive_targets_daily` — 170

#### counts by list_type
- `archive_targets`: 3 lists
- `focus`: 4 lists
- `key_focus`: 4 lists

#### example rows
Stock focus head from live DB:
- `000001.SZ 平安银行 priority=1`
- `000333.SZ 美的集团 priority=2`
- `000651.SZ 格力电器 priority=3`
- `000977.SZ 浪潮信息 priority=4`
- `002230.SZ 科大讯飞 priority=5`
- ... continuing through large-cap / canonical A-share names

Rule samples from `ifa2.focus_list_rules`:
- `default_stock_focus.seed_origin = a_share_only_tushare_supported`
- `default_stock_focus.target_size = 80`
- `default_stock_key_focus.target_size = 20`
- `default_asset_focus.identity_strategy = rolling_canonical_contract`
- `default_asset_focus.sub_buckets = precious_metal,base_metal,energy,black_chain,agri,chemicals`

### 2.2 Seed source files and contracts

#### business-layer seed source files
Primary seed source is business-layer defaults:
- `/Users/neoclaw/repos/ifa-business-layer/ifa_business_layer/defaults.py`
- `/Users/neoclaw/repos/ifa-business-layer/README.md`
- `/Users/neoclaw/repos/ifa-business-layer/scripts/focus_cli.py`

What `defaults.py` does:
- builds canonical seeded families for stock/macro/tech/asset
- sets `owner_scope = default`
- explicitly seeds:
  - `default_stock_key_focus` from first 20 stock items
  - `default_stock_focus` from first 80 stock items
  - `default_macro_*`
  - `default_tech_*`
  - `default_asset_*`
- also seeds archive target lists separately

The business-layer README is explicit:
- canonical owner scope is `owner_type=default`, `owner_id=default`
- `seed-default` removes legacy default-owner `focus` / `key_focus` lists not part of the canonical set
- stock family is seeded from **A-share only**, because current local universe support is Tushare/A-share constrained

### 2.3 Producer usage contract

#### what A-share early main producer actually reads
`src/ifa_data_platform/fsj/early_main_producer.py` queries:
```sql
from ifa2.focus_lists fl
join ifa2.focus_list_items fi on fi.list_id = fl.id
...
where fl.owner_type='default' and fl.owner_id='default'
  and fl.list_type in ('key_focus','focus','tech_key_focus','tech_focus')
  and coalesce(fi.asset_category, 'stock') = 'stock'
```

So the current A-share early main report reads:
- **owner_type** = `default`
- **owner_id** = `default`
- list types filtered to focus/key_focus plus tech variants
- stock-only rows only

### 2.4 Renderer usage contract

`src/ifa_data_platform/fsj/report_rendering.py`:
- builds a formal focus module from payload `focus_scope`
- derives key-focus vs focus-watch display tiers from per-symbol list type metadata
- customer profile rewrites names/copy, but does **not** change the underlying owner/list semantic

Meaning:
- renderer trusts producer payload as if it is already product-facing focus truth
- renderer does not know whether symbols came from customer mandate vs default coverage seed

### 2.5 Chart pack usage contract

`src/ifa_data_platform/fsj/chart_pack.py` has two behaviors:
1. it first tries to resolve focus symbols from assembled payload / evidence links
2. if still short, it falls back to querying `ifa2.focus_lists` / `ifa2.focus_list_items`

Important caveat:
- the chart-pack fallback query is **not owner-scoped**; it filters by active list type and active items, but not by `owner_type/owner_id`
- today that is harmless only because the DB currently contains only `default/default`
- structurally this is weaker than the early main producer contract

### 2.6 Answers to the required focus truth questions

1. **Do both `default/default` and `system/default` exist?**
   - **No.** Live DB query shows only `default/default`.

2. **Which `owner_type / owner_id` does A-share main report actually read?**
   - **`default/default`**.

3. **Where do current key_focus / focus seeds come from?**
   - From **business-layer canonical default seed logic** in `ifa_business_layer/defaults.py`, usually applied by `scripts/focus_cli.py seed-default`.

4. **Why does A-share focus look like a continuous sequence from `000001.SZ` onward?**
   - Because the stock seed is a deterministic canonical A-share default list in business-layer defaults, ordered by the bundled stock seed list / assigned priority. It is not customer-specific research output.

5. **Is this an intentional default seed?**
   - **Yes.** The README and rules explicitly describe it as canonical default owner seed.

6. **Are these seeds for dev coverage / collection coverage / formal customer focus pool?**
   - They are best interpreted as **default business-layer seed / baseline coverage objects** for system operation and fallback business scope.
   - They are **not sufficient evidence of a formal customer focus mandate**.

7. **Is the current report mistakenly surfacing default seed as formal customer focus list?**
   - **Yes, materially yes.** The current customer report presents these default seed lists as “核心关注 / 关注” watchlists without a customer-specific contract layer separating default seed from customer-facing display scope.

8. **Theoretical key_focus count?**
   - Stock 20 + macro 5 + tech 20 + asset 12 = **57** total seeded `key_focus` items across families.
   - For A-share main stock-consumable scope, early main can read stock + stock-like tech rows if `asset_category` passes its filter, but customer surface currently emphasizes stock-watchlist consumption.

9. **Theoretical focus count?**
   - Stock 80 + macro 10 + tech 50 + asset 20 = **160** total seeded `focus` items across families.

10. **Do A-share / Asset / Tech / Macro each have their own focus & key_focus?**
   - **Yes.** DB and defaults confirm distinct domain/family lists exist.

11. **Do current support reports actually use domain-specific focus lists?**
   - **AI/Tech support: yes, partially.** It explicitly reads `default_tech_focus` and `default_tech_key_focus`.
   - **Macro support: no focus-list family dependency; it uses macro/archive/news/northbound inputs.**
   - **Commodities support: no focus-list family dependency; it uses commodity/futures/news inputs.**

12. **How should we distinguish collection scope vs archive target vs product-facing focus list vs customer-facing display list?**
   - **collection scope**: what the system collects to maintain operational coverage; may be broad and engineering-oriented
   - **archive target**: explicit retention targets for persistence/backfill; current `archive_targets` lists belong here
   - **product-facing focus list**: formal business-layer watchlist object meant for report logic consumption
   - **customer-facing display list**: a curated subset/projection of product-facing focus, with clear semantics for why it is shown to the customer
   - Current system collapses the last two categories and partially conflates them with the first two.

13. **Should default seeds be hidden/compressed at report layer by default?**
   - **Yes.** Default seeds should not be surfaced as-is to customers. They should be hidden, compressed, or relabeled as system baseline coverage unless a higher-level product contract explicitly promotes a subset into customer-facing focus.

### 2.7 Whether current customer report behavior is reasonable

**Judgment: not reasonable enough for a final customer-grade contract.**

Why:
- the underlying seed is canonical system default, not customer-specific watchlist truth
- the report turns that seed into a polished customer-facing advisory watchlist
- this makes the presentation look more intentional/customer-owned than the underlying data contract actually is

### 2.8 Recommended fix direction

1. **Introduce explicit focus-scope taxonomy**
   - `coverage_seed`
   - `archive_target`
   - `product_watchlist`
   - `customer_display_watchlist`

2. **Stop treating `default/default` as customer display truth by default**
   - it may remain fallback product scope, but customer rendering should not blindly publish it

3. **Make early main producer read a product-facing focus contract first**
   - if absent, degrade explicitly rather than silently upgrading default seed to customer watchlist

4. **Keep chart-pack fallback aligned with the same contract**
   - add owner/list semantic parity with producer or consume only already-resolved payload scope

---

## 3) 2026-04-23 Early Report DB Availability and Usage Audit

Audit window required:
- `2026-04-22` after close -> `2026-04-23` premarket / early-report context

### 3.1 What data actually exists locally in that window

#### market / index data
- `ifa2.index_daily_bar_history`
  - `2026-04-22`: 8 rows
  - `2026-04-23`: 8 rows
- `ifa2.equity_daily_bar_history`
  - `2026-04-22`: 20 rows
  - `2026-04-23`: 20 rows
- `ifa2.northbound_flow_history`
  - `2026-04-22`: 1 row
  - `2026-04-23`: 1 row
  - sample: `2026-04-23 north_money=353095.2600`

#### sector / theme / performance / heat / breadth / leader concepts
- `ifa2.sector_performance_history`
  - `2026-04-22`: 394 rows
  - `2026-04-23`: 394 rows
  - sample top sector on `2026-04-23`: `885860.TI 中船系 1.9530%`
- `ifa2.ifa_archive_sector_performance_daily`
  - `2026-04-22`: 550 rows
  - `2026-04-23`: 550 rows
- **missing/empty for this window**:
  - `ifa2.highfreq_sector_breadth_working`: 0 rows
  - `ifa2.highfreq_sector_heat_working`: 0 rows
  - `ifa2.highfreq_leader_candidate_working`: 0 rows
  - `ifa2.highfreq_intraday_signal_state_working`: 0 rows

#### fund flow / margin / dragon_tiger / ETF/proxy
- `ifa2.dragon_tiger_list_history`
  - `2026-04-22`: 68 rows
  - `2026-04-23`: 61 rows
  - sample: `002008.SZ net_amount=991889450.9800`
- `ifa2.northbound_flow_history`
  - available as above
- **not evidenced in this audit window as locally available / wired**:
  - margin financing table usage in current early path not found
  - ETF/proxy productized usage not found in early path

#### sentiment (limit up/down, 连板, 炸板, 高位 proxies)
- `ifa2.limit_up_detail_history`
  - `2026-04-22`: 79 rows
  - `2026-04-23`: 85 rows
- `ifa2.limit_up_down_status_history`
  - `2026-04-22`: 1 row
  - `2026-04-23`: 1 row
- `ifa2.highfreq_event_stream_working`
  - `2026-04-22`: 1256 rows
  - `2026-04-23`: 3954 rows
- but **leader / intraday state / breadth / heat working tables are empty in this window**

#### news / announcements / research_reports / investor_qa
- `ifa2.news_history`
  - `2026-04-22`: 2570 rows
  - `2026-04-23`: 2564 rows
- `ifa2.announcements_history`
  - `2026-04-22`: 20163 rows
  - `2026-04-23`: 1935 rows
- `ifa2.research_reports_history`
  - `2026-04-22`: 792 rows
  - `2026-04-23`: 655 rows
- `ifa2.investor_qa_history`
  - `2026-04-22`: 4344 rows
  - `2026-04-23`: 2017 rows

Example records:
- announcements: `603629.SH ... 关于控股股东部分股份解除质押的公告`
- research: `601808.SH 国金证券_国际地缘政治与油价剧烈动荡，公司营收保持稳步提升_20260423.pdf`
- investor_qa: `600545.SH 董秘您好！中国巨石是贵司的客户吗？`

#### commodity / asset data and mapping potential
- `ifa2.commodity_15min_history`: 0 rows in this window
- `ifa2.precious_metal_15min_history`: 0 rows in this window
- `ifa2.futures_history`: 0 rows in this window
- `ifa2.highfreq_futures_minute_working`: 0 rows in this window
- however asset focus lists themselves exist in business-layer seed scope

#### macro data and mapping potential
- `ifa2.macro_history`: no rows dated `2026-04-22/23`, but historical rows exist (latest sampled rows were `2026-02-01`)
- `ifa2.ifa_archive_macro_daily`
  - `2026-04-22`: 3 rows
  - `2026-04-23`: 3 rows
- `ifa2.ifa_archive_news_daily`
  - `2026-04-22`: 6990 rows
  - `2026-04-23`: 6766 rows

#### tech / AI support data and mapping potential
- `ifa2.sector_performance_history` available and used for AI/tech support
- `default_tech_focus` / `default_tech_key_focus` exist in focus tables
- AI/tech support producer can derive sector snapshots and tech focus counts

#### focus/key_focus symbol-specific availability
For focus items, early main producer can enrich each symbol with:
- name / industry from `stock_basic_current` / `stock_basic_history`
- latest daily bar availability from `equity_daily_bar_history`
- text-event counts from announcements / research / investor QA / dragon tiger / limit-up tables
- event count from `highfreq_event_stream_working`

But practical symbol-level market history is thin because:
- `equity_daily_bar_history` has only **20 rows per day** in this sample window
- many default focus symbols do not have complete daily-bar coverage

### 3.2 What is already used by current report generation

#### early main producer already uses
`src/ifa_data_platform/fsj/early_main_producer.py` currently consumes:
- focus lists + focus items (`default/default` stock-ish scope)
- `equity_daily_bar_history` for per-symbol evidence
- `announcements_history`
- `research_reports_history`
- `investor_qa_history`
- `dragon_tiger_list_history`
- `limit_up_detail_history`
- `highfreq_event_stream_working`
- `highfreq_open_auction_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- latest text union from news/announcements/research/QA

#### chart pack uses
- `index_daily_bar_history`
- `equity_daily_bar_history`
- focus symbols resolved from payload/DB

#### support producers use
- macro support: `macro_history`, `news_history`, `announcements_history`, `ifa_archive_macro_daily`, `ifa_archive_news_daily`, optionally `northbound_flow_history`
- commodities support: `commodity_15min_history`, `precious_metal_15min_history`, `futures_history`, `highfreq_futures_minute_working`, `news_history`
- AI/tech support: `default_tech_*` focus, `sector_performance_history`, `news_history`, `ifa_archive_sector_performance_daily`

### 3.3 What exists but is not used enough / not surfaced enough in the early customer report

Substantial data exists locally but is underused or only lightly summarized:
- `sector_performance_history` (394 rows/day) — not a core early-customer content block today
- `northbound_flow_history` — not central in early customer output
- `dragon_tiger_list_history` — only used as thin symbol evidence count, not a market section
- `limit_up_down_status_history` — available, but not a visible early customer section
- `news_history`, `announcements_history`, `research_reports_history`, `investor_qa_history` — large volume available, but only lightly collapsed into text catalyst counts / snippets
- `ifa_archive_macro_daily`, `ifa_archive_news_daily`, `ifa_archive_sector_performance_daily` — available for support/backdrop use, but not integrated into a richer early main narrative

### 3.4 What truly does not exist in this window

For `2026-04-23` early-report context, these are effectively absent locally:
- `highfreq_open_auction_working`: empty
- `highfreq_stock_1m_working`: empty
- `stock_60min_history`: empty
- `ifa_archive_equity_60m`: total table count = 0
- `highfreq_sector_breadth_working`: empty
- `highfreq_sector_heat_working`: empty
- `highfreq_leader_candidate_working`: empty
- `highfreq_intraday_signal_state_working`: empty
- `commodity_15min_history`: empty
- `precious_metal_15min_history`: empty
- `futures_history`: empty
- `highfreq_futures_minute_working`: empty

### 3.5 Why current report does not reflect market / sector / fundflow / sentiment / dragon_tiger / news / announcements etc.

**It is not mainly because the DB is empty.**

The truth is split:
1. **Some important intraday/auction structures really are absent** in this date window (`open_auction`, `1m`, `60m`, breadth/heat/leader working tables)
2. **But a lot of valuable low/mid-frequency market content does exist and is not fully connected into the customer report**

Most important examples of “exists but under-connected”:
- sector performance
- northbound flow
- dragon tiger summary
- limit up/down status summary
- massive announcement/news/research/investor-QA availability

### 3.6 Is the gap due to data absence or report-layer non-connection?

**Answer: both, but mainly report-layer non-connection for the low/mid-frequency side.**

- **absence-driven gaps**:
  - auction / intraday breadth / heat / leader / 1m / 60m / commodity intraday
- **report-layer connection gaps**:
  - sector/theme performance not elevated into main early customer structure
  - northbound / sentiment summaries underused
  - dragon tiger and text corpus reduced to light evidence counters rather than substantive market sections
  - focus module overconsumes default seed while underusing broader available market context

### 3.7 Highest-value available information without new collection

Without adding collectors, the highest-value DB-backed early-report content would be:
1. **index + sector performance backdrop** (`index_daily_bar_history`, `sector_performance_history`)
2. **northbound + limit-up/down + dragon tiger sentiment package**
3. **same-day / T-1 text catalyst digest** from announcements + research + investor QA + news
4. **focus symbol evidence pack** only for a curated/promoted subset, not full default seed spillover
5. **macro/AI-tech support background** via archive + sector performance + curated text

### 3.8 Is `2026-04-23` truly the best golden sample date?

**Not fully.**

It is a useful customer-surface editorial sample because many recent artifacts already use it, but it is **not the best proof date for “DB-backed completeness”** because several intraday tables that early/mid/late logic expects are empty on that date in the local environment.

### 3.9 If not, which date is better for DB-backed golden sample?

**A better DB-backed golden sample date should be the most recent day where these tables are non-empty together**:
- `highfreq_open_auction_working`
- `highfreq_stock_1m_working` or equivalent intraday bar coverage
- `highfreq_sector_breadth_working`
- `highfreq_sector_heat_working`
- `highfreq_leader_candidate_working`
- `highfreq_intraday_signal_state_working`
- plus the low/mid-frequency market/text tables already present

This audit did not find such a better date within the constrained pass, so the precise replacement date remains **to be selected by a targeted non-implementation DB scan**. Until then, `2026-04-23` should be treated as **editorial / partial-data golden sample**, not full-truth golden sample.

### 3.10 Minimum viable DB-backed early report without adding collectors

Minimum viable content should include:
1. **index / market backdrop**
2. **sector performance top movers / top themes**
3. **northbound flow summary if available**
4. **limit-up/down and dragon-tiger sentiment summary**
5. **text catalyst digest from news + announcements + research + investor QA**
6. **curated focus subset with symbol evidence**
7. **explicit degrade block for missing auction / intraday / breadth / heat tables**

### 3.11 Data category table

| Data category | Related tables | Window row count | Example records | Already used by report | Reason if unused / underused | Minimum integration recommendation | Affects customer quality |
|---|---|---:|---|---|---|---|---|
| Market/index | `index_daily_bar_history`, `equity_daily_bar_history` | 8/day index, 20/day equity | main index daily bars | Yes | equity coverage thin | keep index section, reduce dependence on thin equity universe | Yes |
| Sector/theme | `sector_performance_history`, `ifa_archive_sector_performance_daily` | 394/day live, 550/day archive | 中船系 +1.95% | Partially | not elevated into customer main structure | add explicit sector/theme backdrop block | Yes |
| Fund flow | `northbound_flow_history` | 1/day | north_money 353095.2600 | Mostly no in early | low-frequency value not surfaced centrally | add northbound summary if present | Yes |
| Sentiment | `limit_up_detail_history`, `limit_up_down_status_history`, `dragon_tiger_list_history` | 85 + 1 + 61 on 2026-04-23 | top net dragon tiger symbols | Only lightly | currently reduced to evidence counters | add compact market-sentiment package | Yes |
| News/text | `news_history`, `announcements_history`, `research_reports_history`, `investor_qa_history` | 2564 + 1935 + 655 + 2017 | announcement / research / QA examples above | Partially | only lightly summarized | add curated catalyst digest | Yes |
| Intraday event stream | `highfreq_event_stream_working` | 3954 | major_news events | Partially | mostly used as counts/snippets | use as supporting event digest only | Moderate |
| Auction/intraday microstructure | `highfreq_open_auction_working`, `highfreq_stock_1m_working`, `stock_60min_history`, `ifa_archive_equity_60m` | 0 / 0 / 0 / 0 | none | No | data absent | degrade explicitly | Yes |
| Breadth/heat/leader working | `highfreq_sector_breadth_working`, `highfreq_sector_heat_working`, `highfreq_leader_candidate_working`, `highfreq_intraday_signal_state_working` | all 0 | none | No | data absent | degrade explicitly | Yes |
| Macro support | `macro_history`, `ifa_archive_macro_daily`, `ifa_archive_news_daily` | macro live stale; archive present 3/day and 6k+/day news archive | CPI/PMI/PPI historical snapshots | Yes in support | fresh macro sparse | keep as support backdrop, not main hard claim | Moderate |
| Commodities/asset support | `commodity_15min_history`, `precious_metal_15min_history`, `futures_history`, `highfreq_futures_minute_working` | all 0 | none | Support path exists but effectively empty | data absent | explicit degrade; do not oversell asset support | Moderate |
| Tech/AI support | `default_tech_*` focus + `sector_performance_history` + `news_history` + `ifa_archive_sector_performance_daily` | present | AI-tech sector snapshots | Yes in support | not strongly tied back into main | keep support role; do not misstate as main proof | Moderate |

---

## 4) Functional block audit

### Unified report generation CLI
- **status**: `bounded_done`
- **evidence**:
  - `scripts/fsj_report_cli.py` supports `generate`, `status`, `registry`
  - covers main/support, mode, output profile
- **why not full done**:
  - unified operator surface exists, but it does not solve semantic/data completeness

### Customer/internal/review profile separation
- **status**: `done`
- **evidence**:
  - renderer and publish path thread explicit profiles end-to-end
  - customer surface strips engineering-visible objects

### Slot-specific customer report
- **status**: `bounded_done`
- **evidence**:
  - slot-specific customer surface task landed (`87d0548` and related)
  - renderer differentiates early/mid/late top judgment/risk/next-step blocks
- **why not full done**:
  - slot differentiation is presentation-stronger, but underlying slot data readiness remains inconsistent by date

### DB-backed focus/key-focus
- **status**: `partial`
- **evidence**:
  - producer now reads DB focus metadata and symbol evidence
  - renderer classifies per-symbol key_focus/focus
  - chart pack prioritizes key-focus first
- **why partial**:
  - DB-backed technically, but still semantically wrong as customer-facing contract because it reads canonical default seed directly

### Customer-facing focus list contract
- **status**: `partial`
- **evidence**:
  - customer copy polished repeatedly; module naming upgraded
- **why partial**:
  - no real separation between system default seed and customer-display watchlist
  - this is one of the highest-value unresolved product-contract gaps

### Chart package
- **status**: `bounded_done`
- **evidence**:
  - chart pack closed minimally with manifest + embed blocks
- **why not full done**:
  - narrow chart family; readiness depends on sparse focus/equity coverage and default seed semantics

### Customer report content completeness
- **status**: `partial`
- **evidence**:
  - customer wording/structure is much improved
  - however many available DB-backed market sections are not fully surfaced
- **why partial**:
  - report looks polished but not content-complete

### FSJ / judgment mapping / learning asset
- **status**: `partial`
- **evidence**:
  - minimal judgment review foundation and learning-asset candidate surfaces exist in renderer
- **why partial**:
  - no mature, trustworthy end-to-end evidence-to-customer mapping ledger yet

### LLM gateway / prompt / model policy
- **status**: `done`
- **evidence**:
  - strict role policy, boundary invariants, model selection, fallback chain, business-layer-only route

### Report registry / manifest / output
- **status**: `bounded_done`
- **evidence**:
  - registry / artifact lineage / manifest persistence are in place
- **why not full done**:
  - operationally adequate, but surrounding workspace/output hygiene is still messy and content truth is not guaranteed by registry presence alone

---

## 5) Stage judgment

### Reality-based choice

**Judgment: B**

> **B. presentation layer mostly complete, but real data / real report / content completeness still not complete**

### Why not A
Not credible because:
- the customer focus/watchlist contract is still semantically wrong
- a large amount of existing DB-backed content is still underconnected to the customer report
- some earlier “acceptance” work mostly accepted presentation polish, not full report-data truth

### Why not C
C would say V2 is still generally mid-implementation across the board. That is too pessimistic because:
- control CLI exists
- profile separation exists
- LLM boundary policy exists
- registry/manifest exists
- chart pack exists
- customer rendering is already materially productized

### Precise interpretation
V2 is **not** “only final polish remains.”
It is better described as:
- **operator/presentation shell mostly there**
- **data truth and content completeness layer still incomplete**
- **focus/customer contract still not product-correct**

If forced into a sharper internal phrasing:
- **the shell is late-stage, but the report truth layer is still mid-stage**

---

## 6) HTML attachment bookkeeping

No new HTML was generated by this audit pass.

Existing recent artifacts most relevant for human review:

1. `artifacts/post_p6_symbol_evidence_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T084056Z.html`
   - generation command: `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p6_symbol_evidence_001 --report-run-id-prefix post-p6-symbol-evidence-main-early`
   - business_date: `2026-04-23`
   - slot: `early`
   - profile: `customer`
   - surface: customer
   - leakage status: previously recorded as leakage-clean in task receipt
   - recommended for human review: **yes**, because it represents the current best focus-evidence customer sample while still exposing the default-seed contract issue

2. `artifacts/post_p6_db_backed_focus_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T075756Z.html`
   - generation command: `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p6_db_backed_focus_001 --report-run-id-prefix post-p6-db-backed-focus-main-early`
   - business_date: `2026-04-23`
   - slot: `early`
   - profile: `customer`
   - surface: customer
   - leakage status: task recorded as successful dry-run; use as prior comparison sample
   - recommended for human review: optional comparison only

3. `artifacts/post_p5_section_prose_001/main_early_2026-04-23_dry_run/publish/a_share_main_report_2026-04-23_20260425T064752Z.html`
   - generation command: `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode dry-run --output-profile customer --output-root artifacts/post_p5_section_prose_001 --report-run-id-prefix post-p5-section-prose-main-early`
   - business_date: `2026-04-23`
   - slot: `early`
   - profile: `customer`
   - surface: customer
   - leakage status: accepted in `ACCEPT-P6-001`
   - recommended for human review: optional, as editorial baseline comparison

---

## 7) Final audit conclusion

### Bottom line
The current system is **not blocked on presentation polish anymore**.
The real remaining blockers are:
1. **customer-facing focus contract is still semantically wrong** because canonical default seed is being shown as if it were formal customer watchlist truth
2. **early report underuses substantial existing DB-backed market/text data**
3. **golden sample framing overstates completeness** by focusing on clean customer HTML more than on data-use completeness

### Top recommended next steps
1. **Fix the focus contract first**: separate default coverage seed from customer-facing display watchlist
2. **Implement minimum viable DB-backed early report completeness** using sector performance + northbound + sentiment + text digest already present locally
3. **Re-baseline golden sample date/definition**: editorial sample vs true DB-backed completeness sample must be separated
4. **Build the evidence → support → main → customer mapping ledger one level deeper** for major visible claims
5. **Pause all further wording/focus naming polish** until the above three are closed
