# V2-R0-003 Unified report generation CLI 审计与收口

- Task ID: `V2-R0-003`
- Date: `2026-04-24`
- Repo: `ifa-data-platform`
- Scope: 仅审计并收口报告 generation / publish / delivery CLI 控制面；**不重写 producer / assembly / render / orchestration 主链**

---

## 1. Executive conclusion

结论：**不适合继续维持多个零散 operator 脚本作为唯一入口；应新增一个最小 canonical entry，统一封装已有 entrypoints，而不是重写主链。**

本任务已采用该结论落地：
- 新增 `scripts/fsj_report_cli.py`
- 该脚本只做参数统一、模式/输出根目录收口、main/support/status 路由
- 底层仍复用现有：
  - `scripts/fsj_main_early_publish.py`
  - `scripts/fsj_main_mid_publish.py`
  - `scripts/fsj_main_late_publish.py`
  - `scripts/fsj_main_report_morning_delivery.py`
  - `scripts/fsj_support_batch_publish.py`
  - `scripts/fsj_main_delivery_status.py`
  - `scripts/fsj_support_delivery_status.py`
  - `scripts/fsj_operator_board.py`

这满足“最小 canonical entry”与“禁止大重构”两条约束。

---

## 2. Existing entrypoint coverage matrix

### 2.1 Generation / publish / delivery surfaces

| Entrypoint | Main / Support | Slot coverage | Core responsibility | Existing parameters / control surface | Gaps vs unified operator surface |
|---|---|---:|---|---|---|
| `src/ifa_data_platform/fsj/main_publish_cli.py` | Main | early/mid/late via caller config | Shared helper for persist + publish summary | `business_date`, `output_root`, `generated_at`, `report_run_id_prefix`, `include_empty`, injected producer factory | Not a direct operator CLI; no support routing; no top-level mode/profile abstraction |
| `scripts/fsj_main_early_publish.py` | Main | early | Persist + publish early main | `business-date`, `output-root`, `generated-at`, `report-run-id-prefix`, `include-empty` | Slot-specific only; no support; no unified status path; no mode/profile |
| `scripts/fsj_main_mid_publish.py` | Main | mid | Persist + publish mid main | same as above | Same gap |
| `scripts/fsj_main_late_publish.py` | Main | late | Persist + publish late main | same as above | Same gap |
| `scripts/fsj_main_report_publish.py` | Main | slot-agnostic package publish on already-assembled main | Build/publish main HTML + delivery package | `business-date`, `output-dir`, `report-run-id`, `generated-at`, `include-empty`, `package-only` | Requires caller knowledge of when/how to use; does not cover persist step; no support routing |
| `scripts/fsj_main_report_morning_delivery.py` | Main | morning delivery workflow; slot intent not explicit in CLI contract | Package + eval + dispatch selection + review/send manifests | `business-date`, `output-dir`, `report-run-id`, `generated-at`, `include-empty`, comparison args | Specialized workflow, not canonical generation entry; not support-aware; no unified interface |
| `scripts/fsj_support_batch_publish.py` | Support | early/late | Batch persist + publish support domains | `business-date`, `slot`, `output-root`, `agent-domain[]`, `generated-at`, `report-run-id-prefix`, `require-ready` | Separate semantics from main; no mid; no unified main/support switch; no status integration |
| `scripts/fsj_support_report_publish.py` | Support | early/late | Single-domain support publish | `business-date`, `agent-domain`, `slot`, `output-dir`, `report-run-id`, `generated-at`, `html-only`, `require-ready` | Single-domain helper only; still separate from main surface |

### 2.2 Status / operator surfaces

| Entrypoint | Scope | Responsibility | Notes |
|---|---|---|---|
| `scripts/fsj_main_delivery_status.py` | Main | Active/history delivery/operator status for main | Good read surface, but separate command family |
| `scripts/fsj_support_delivery_status.py` | Support | Active/history delivery/operator status for one support domain | Requires separate domain selection |
| `scripts/fsj_operator_board.py` | Fleet | Unified board across main + support | Status board exists, but generation CLI remains fragmented |

---

## 3. Gap list

### 3.1 Confirmed control-surface gaps

1. **No single top-level operator command** for `main` and `support` generation.
2. **Main slot commands are fragmented** into early/mid/late wrappers.
3. **Support publish path is separate** and uses different argument conventions from main.
4. **Status queries are also fragmented** across main/support/board scripts.
5. Existing operator must still remember **which script to run for which scenario**.

### 3.2 Remaining functional gaps not solved in this task

These are intentionally **documented, not expanded into a refactor**:

1. `output_profile=customer` is **not implemented** in the current publish/render chain.
2. `output_profile=review` does not yet mean an alternate renderer; it currently maps to the existing package/operator-review surfaces.
3. `mode=replay / backfill-test / dry-run` is **not a native behavior switch** in the underlying chain. In the minimal canonical entry, mode is treated as:
   - operator intent label
   - isolated output-root routing
   - non-live/manual execution discipline
4. Main delivery orchestration is represented by a specialized `morning_delivery` path; there is not yet one generalized delivery workflow contract across all slots.
5. Support batch path does not expose a unified single-domain HTML-only mode through the new wrapper; direct script remains available for that edge case.

---

## 4. Decision: consolidate existing entrypoints vs add minimal canonical entry

### Decision

**Add minimal canonical entry.**

### Why not “consolidate only” by documentation?

Because documentation alone would still leave operators manually choosing among:
- `fsj_main_early_publish.py`
- `fsj_main_mid_publish.py`
- `fsj_main_late_publish.py`
- `fsj_main_report_morning_delivery.py`
- `fsj_support_batch_publish.py`
- multiple status scripts

That is still a fragmented control plane.

### Why not a larger refactor?

Because that would violate current constraints:
- no broad refactor
- no rewriting producer/assembly/render/orchestration chain
- no scope expansion beyond CLI control surface

### Chosen implementation shape

新增一个 **thin wrapper**：`scripts/fsj_report_cli.py`

它只做：
- top-level argument normalization
- `main` / `support` routing
- `generate` / `status` command grouping
- isolated output-root routing for non-realtime intent modes
- explicit rejection of unsupported `customer` profile

它**不做**：
- producer rewrite
- render rewrite
- orchestration rewrite
- DB contract rewrite
- delivery state model rewrite

---

## 5. Concrete implementation files

### Added
- `scripts/fsj_report_cli.py`
- `docs/V2_R0_003_UNIFIED_REPORT_CLI_AUDIT_AND_CLOSURE_2026-04-24.md`

### Updated
- `docs/IFA_Execution_Progress_Monitor.md`

---

## 6. Recommended command format

### 6.1 Canonical generation command

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject <main|support> \
  --business-date YYYY-MM-DD \
  --slot <early|mid|late> \
  --mode <realtime|replay|backfill-test|dry-run> \
  --output-profile <internal|review> \
  --output-root <non-live-output-root>
```

### 6.2 Main examples

#### Main publish
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot early \
  --mode dry-run \
  --output-profile review \
  --output-root artifacts/v2_r0_003
```

#### Main morning delivery workflow
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject main \
  --business-date 2026-04-23 \
  --slot early \
  --main-flow morning-delivery \
  --mode dry-run \
  --output-profile review \
  --output-root artifacts/v2_r0_003
```

### 6.3 Support examples

#### Support batch publish
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject support \
  --business-date 2026-04-23 \
  --slot late \
  --mode dry-run \
  --output-profile review \
  --output-root artifacts/v2_r0_003
```

#### Support selected domains only
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate \
  --subject support \
  --business-date 2026-04-23 \
  --slot late \
  --mode dry-run \
  --output-profile internal \
  --output-root artifacts/v2_r0_003 \
  --agent-domain macro \
  --agent-domain ai_tech
```

### 6.4 Canonical status commands

#### Main status
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py status \
  --subject main \
  --business-date 2026-04-23 \
  --format json
```

#### Support status
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py status \
  --subject support \
  --agent-domain macro \
  --business-date 2026-04-23 \
  --format json
```

#### Fleet board
```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py status \
  --subject board \
  --latest \
  --format json
```

---

## 7. Test / validation method

### 7.1 CLI contract validation

1. `--help` for new wrapper
2. `generate` main dry-run-intent call against isolated output root
3. `generate` support dry-run-intent call against isolated output root
4. `status` main/support/board wrapper calls in JSON mode

### 7.2 Validation principle

- Use the unified repo venv only: `/Users/neoclaw/repos/ifa-data-platform/.venv`
- Use **non-live / isolated output roots** only
- Do not alter the producer/assembly/render/orchestration chain
- Validate wrapper routing and command compatibility, not a new report architecture

### 7.3 Acceptance for this task

This task is accepted when:
1. audit matrix exists
2. gap list exists
3. decision is explicit
4. minimal canonical entry exists and runs
5. progress monitor updated
6. commit + push completed

---

## 8. Acceptance status

At doc authoring time inside this task:
- audit matrix: done
- gap list: done
- decision: done
- minimal canonical entry: done
- validation: to be recorded in progress monitor and task report
- commit/push: to be recorded in task report

