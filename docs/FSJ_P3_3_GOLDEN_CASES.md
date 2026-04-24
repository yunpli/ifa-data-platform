# FSJ P3-3 Golden Cases

Date: 2026-04-23  
Owner: Developer Lindenwood  
Scope: `ifa-data-platform` FSJ MAIN early/mid/late producer seams

## Why this slice

`P3-3` asked for the thinnest durable benchmark/golden seam, not a broad harness rewrite.

The narrowest production-grade anchor is the already-real FSJ MAIN producer integration path:
- fixed slot input contract
- real FSJ graph production
- real DB persistence
- slot-specific judgment semantics
- slot-specific evidence-role expectations

That seam is stable enough to benchmark and close enough to production truth to catch regressions that matter.

## Canonical fixture pattern

Reusable fixture catalog:
- `tests/integration/fsj_main_slot_golden_cases.py`

Executable golden regression:
- `tests/integration/test_fsj_main_slot_golden_cases.py`

This pattern defines canonical `SlotGoldenCase` coverage across three MAIN benchmark families:
1. `early_main`
   - `early_candidate_validation`
   - `early_llm_fallback_applied`
   - `early_llm_deterministic_degrade`
2. `mid_main`
   - `mid_intraday_adjustment`
   - `mid_llm_fallback_applied`
3. `late_main`
   - `late_llm_fallback_applied`
   - `late_provisional_close_monitor`

Each case fixes:
- producer type
- slot + section key
- expected judgment action
- expected object type
- optional contract-mode invariant
- required evidence-role / ref-system pairs
- minimum persisted graph counts (`objects`, `edges`, `evidence_links`, `observed_records`)

## What this protects

This thin suite is intentionally governance-heavy rather than presentation-heavy.

It catches regressions where a slot still "runs" but stops being the same business behavior, for example:
- early no longer produces `validate` judgment semantics
- mid stops carrying prior-slot or historical references
- late loses provisional-close contract tagging
- persistence quietly drops evidence/observed-record coverage
- slot contracts drift while unit tests still pass locally

## Current coverage boundary

Covered now:
- MAIN early/mid/late producer golden semantics
- dedicated family entrypoints for `early_main`, `mid_main`, and `late_main`
- DB-persisted graph minimums
- evidence-role invariants by slot

Not covered yet:
- degraded-data cases
- LLM timeout/fallback cases
- support standalone golden cases
- rendered HTML/package artifact snapshots

Those should extend this same fixture pattern rather than creating a separate competing harness.

## Next extension path

Recommended next B-lane follow-up:
- add one degraded-data benchmark family reusing the same catalog shape, or split explicit LLM timeout/fallback families out of the slot-family coverage if separate operator ownership is needed.
