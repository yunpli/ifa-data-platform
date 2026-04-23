# FSJ MAIN Late Runbook

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: operator-facing late MAIN persistence + publish for A-share FSJ

---

## 1. Current truth

The canonical operator entrypoint for late MAIN persistence + publish is:

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py \
  --business-date YYYY-MM-DD \
  --output-root artifacts/fsj_main_late_YYYYMMDD
```

This command is canonical because it does the production path in one operator seam:

1. persist the late MAIN FSJ bundle first
2. publish the MAIN delivery package second
3. write one machine-readable summary plus one operator summary over the combined result

**Important:** operators should not treat raw `LateMainFSJProducer().produce_and_persist(...)` + `scripts/fsj_main_report_publish.py` as the normal production path anymore. The canonical path is the single operator command above so persistence and publish remain version-linked and auditable.

---

## 2. Supported operator path

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py \
  --business-date YYYY-MM-DD \
  --output-root artifacts/fsj_main_late_YYYYMMDD
```

Optional:

```bash
--generated-at 2026-04-23T12:20:43Z
--report-run-id-prefix fsj-main-late
--include-empty
```

Use `--include-empty` only for bounded debugging/operator inspection when you intentionally want empty non-late sections surfaced in the assembled MAIN package.

---

## 3. What the command writes

Under `--output-root`, the command writes:

- `publish/`
  - the published MAIN HTML / QA / manifest / delivery package artifacts from `scripts/fsj_main_report_publish.py`
- `main_late_publish_summary.json`
  - machine-readable combined persist + publish result
- `operator_summary.txt`
  - concise operator-facing summary

The JSON summary includes:
- late MAIN persist status
- persisted bundle id and counts
- publish status and exit code
- delivery manifest/package lineage when publish succeeds

---

## 4. Exit semantics

- exit `0`: late MAIN persisted and published successfully
- exit `2`: persist or publish blocked

Persist failure is terminal for the canonical operator flow. The command intentionally does **not** continue into publish after a persist failure, because doing so could accidentally package an older active bundle and break version-link truthfulness.

---

## 5. Operator discipline

### Do
- use `scripts/fsj_main_late_publish.py` as the normal late MAIN operator command
- keep one output root per run for auditability
- inspect `main_late_publish_summary.json` and `operator_summary.txt` before claiming send-readiness

### Do not
- run late MAIN persistence manually as a routine pre-step
- run `scripts/fsj_main_report_publish.py` alone as the normal late MAIN production path
- claim late MAIN publish readiness based only on HTML existence without checking summary/package state

---

## 6. Bounded verification commands

```bash
cd /Users/neoclaw/repos/ifa-data-platform
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_main_late_publish.py --help
/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest tests/unit/test_fsj_main_late_publish_script.py -q
```

These checks verify:
- the canonical operator command is live
- persist-before-publish is enforced
- summary/operator surfaces still exist

---

## 7. Roadmap impact

### P0-3 Late slot end-to-end closure
Improved materially for MAIN:
- late MAIN now has a canonical operator path instead of an ad hoc manual chain
- same-run persistence + publish are linked in one auditable surface
- operator summary/evidence now exists for the late MAIN publish seam

### P1-1 Support standalone report production path
No direct scope change.

### P1-2 MAIN/support artifact convergence
Improved indirectly, not fully closed:
- late MAIN publish now sits on a canonical persisted late MAIN bundle step
- convergence proof still depends on continued validation that late MAIN consumes concise support summaries with correct provenance mapping

---

## 8. Out of scope for this runbook

This runbook does not cover:
- early or mid MAIN operator canonicalization
- customer dispatch/send commands
- unified operator control-plane UI
- deeper convergence correctness proof beyond this operator seam
