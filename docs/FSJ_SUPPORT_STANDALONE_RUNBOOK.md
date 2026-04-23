# FSJ Support Standalone Runbook

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: operator-facing standalone support artifact production for A-share FSJ support domains (`macro`, `commodities`, `ai_tech`)

---

## 1. Current truth

The canonical operator entrypoint for standalone support publishing is:

```bash
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot early \
  --output-root artifacts/fsj_support_batch_YYYYMMDD
```

This command is canonical because it does both halves of the operator flow in the correct order:

1. persist FSJ support bundles first
2. publish per-domain standalone support artifacts second
3. write one batch summary plus one operator summary over the combined result

**Important:** persistence is now built in.  
Operators should **not** treat `scripts/fsj_support_bundle_persist.py` as a separate normal pre-step for early support production. `persist-before-publish` is automatic inside `scripts/fsj_support_batch_publish.py`.

Use the lower-level scripts only for debugging, bounded verification, or implementation work:
- `scripts/fsj_support_bundle_persist.py`
- `scripts/fsj_support_report_publish.py`

---

## 2. Supported operator path

### 2.1 Early support batch publish

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot early \
  --output-root artifacts/fsj_support_batch_YYYYMMDD \
  --require-ready
```

### 2.2 Late support batch publish

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot late \
  --output-root artifacts/fsj_support_batch_YYYYMMDD_late \
  --require-ready
```

### 2.3 Limit to one or more domains

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py \
  --business-date YYYY-MM-DD \
  --slot early \
  --output-root artifacts/fsj_support_batch_macro_only \
  --agent-domain macro \
  --require-ready
```

Repeat `--agent-domain` to target multiple support domains.

Valid domains:
- `macro`
- `commodities`
- `ai_tech`

Valid slots:
- `early`
- `late`

---

## 3. What the batch command writes

Under `--output-root`, the command writes:

- `persist/`
  - persistence summary artifacts from the built-in persist phase
- `<domain>/`
  - published standalone support HTML/package outputs for each requested domain
- `batch_summary.json`
  - machine-readable batch result across persist + publish
- `operator_summary.txt`
  - concise operator-facing summary across all requested domains

The JSON summary includes:
- persist exit code
- per-domain publish status
- ready vs blocked counts
- bundle lineage/package state per domain

---

## 4. Exit semantics

- exit `0`: all requested domains published in ready state
- exit `2`: one or more requested domains blocked, missing, or non-ready

With `--require-ready`, missing/non-ready persisted bundles are treated as blocking instead of silently producing a degraded placeholder package.

---

## 5. Operator discipline

### Do
- use `scripts/fsj_support_batch_publish.py` as the normal operator command
- keep one output root per run for clean auditability
- use `--require-ready` for production-facing support publish runs
- inspect `batch_summary.json` and `operator_summary.txt` before claiming send-readiness

### Do not
- run `fsj_support_bundle_persist.py` manually as a routine production pre-step
- claim support publish is ready based only on HTML existence without checking batch/package state
- treat support standalone output as a MAIN-only side effect

---

## 6. Bounded verification commands

Confirm command surface:

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_support_batch_publish.py --help
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest tests/unit/test_fsj_support_batch_publish_script.py -q
```

These checks verify:
- the canonical operator command is live
- persist-before-publish is still enforced by tests
- batch summary/operator summary surfaces still exist

---

## 7. Roadmap impact

### P0-1 Early slot end-to-end closure
Improved materially for the support lane:
- early support now has a canonical operator batch command
- persistence + publish are linked in one auditable step
- artifact persistence/operator visibility are explicit in one batch surface

### P1-1 Support standalone report production path
Closed an operator-facing seam:
- standalone support publishing is no longer documented as an ambiguous two-step operator flow
- the canonical path now reflects implementation truth
- persistence is explicitly part of the support standalone publish path

### P1-2 MAIN/support artifact convergence
Improved indirectly, not fully closed:
- version linkage/provenance is stronger because publish runs now sit directly on top of the persisted bundle step
- MAIN/support convergence validation still needs separate correctness proof beyond this runbook

---

## 8. Out of scope for this runbook

This runbook does not cover:
- MAIN report publish/send flow
- support-to-MAIN merge correctness proof
- customer dispatch/send commands
- a unified operator control-plane UI
