# Highfreq Milestone 4 — Derived Signal Layer (Batch 1)

_Date: 2026-04-16 04:07 _

## 1. Purpose of the batch
- Land the first serious highfreq derived business objects.
- Move highfreq beyond raw bars / raw event ingestion.
- Create real derived storage/runtime outputs for leader, emotion, validation, risk/opportunity, limit-event, breadth/heat, and turnover/amount progress.

## 2. What was supposed to be done
Attempt the milestone-4 derived scope:
- sector breadth
- sector heat
- leader candidate pool
- leader confirmation state
- continuation health
- emotion stage
- intraday validation state for prior judgment
- end-of-day risk / opportunity state
- limit-up / limit-down / broken-board / re-seal event stream
- intraday turnover / amount progress

## 3. What was actually done
Implemented the first derived-signal builder and landed derived storage tables for:
- sector breadth
- sector heat
- leader candidate pool
- leader confirmation state
- continuation health
- emotion stage
- intraday validation state
- end-of-day / scope-level risk-opportunity state
- limit-event stream (first proxy form)
- turnover / amount progress

The implementation uses the currently landed raw layer as its source substrate:
- `highfreq_stock_1m_working`
- `highfreq_proxy_1m_working`
- `highfreq_close_auction_working`
- other already-landed highfreq working/raw tables as supporting context

## 4. Code files changed
- `alembic/versions/032_highfreq_derived_signal_tables.py`
- `src/ifa_data_platform/highfreq/derived_signals.py`
- `tests/integration/test_highfreq_milestone4.py`

## 5. Tests run and results
### Migration
- `alembic upgrade head`
- result: succeeded

### Focused integration tests
- `pytest tests/integration/test_highfreq_milestone4.py -q`
- result: `2 passed`

### Direct derived build validation
- direct builder execution via `DerivedSignalBuilder().build()`
- result: succeeded and returned structured derived metrics

## 6. DB/runtime evidence
### Direct derived result snapshot
Latest builder result produced fields including:
- `sector_code`
- `up_count`
- `down_count`
- `limit_up_count`
- `strong_count`
- `spread_ratio`
- `heat_score`
- `leader_candidate_count`
- `limit_event_count`
- `emotion_stage`
- `validation_state`
- `risk_opportunity_state`
- `turnover_progress`
- `amount_progress`

### Derived table evidence
Current row counts after the batch:
- `highfreq_sector_breadth_working > 0`
- `highfreq_sector_heat_working > 0`
- `highfreq_leader_candidate_working > 0`
- `highfreq_limit_event_stream_working > 0`
- `highfreq_intraday_signal_state_working > 0`

This proves the derived layer is not conceptual only; it now has real DB-backed outputs.

## 7. Truthful judgment / result
### What is now real in Milestone 4
The following derived highfreq business objects are now real and persisted:
- sector breadth (first implementation)
- sector heat (first implementation)
- leader candidate pool
- leader confirmation state
- continuation health
- emotion stage
- intraday validation state
- end-of-day / scope-level risk-opportunity state
- limit-event stream (first proxy form)
- turnover / amount progress

### Important truthful limitation
Sector breadth and sector heat are currently **implemented but coverage-limited**.
Reason:
- the currently landed proxy universe is still thin
- therefore breadth/heat are real derived objects, but not yet broad/complete multi-sector coverage

This is a coverage limitation, not a fake implementation claim.

### Interpretation of current derived objects
- leader pool / confirmation / continuation are currently driven from the landed stock 1m substrate and score-based heuristics
- limit-event stream is currently a first proxy form derived from close-auction / available highfreq state, not yet a fully rich board-event engine
- validation / risk-opportunity / emotion are now real persisted states, but still a first-generation heuristic layer rather than a fully mature judgment engine

## 8. Residual gaps / blockers / deferred items
### Coverage-limited / still partial in this batch
- sector breadth
- sector heat
  - reason class: **coverage limitation / upstream proxy breadth not yet broad enough**

### Still needing richer future refinement
- broken-board / re-seal event semantics are not yet a rich independent event engine; current implementation is a first proxy event stream
- intraday validation state and risk/opportunity state are first-generation heuristic outputs and should be refined in later highfreq batches

### No fake completeness maintained
This batch claims first real derived-layer landing, not final maturity of the whole highfreq judgment layer.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- Highfreq is no longer only raw-ingestion + schedule substrate.
- It now has a real first-generation derived signal layer.
- Sector breadth/heat must be described as implemented-but-coverage-limited, not broad-complete.
