# Highfreq Milestone 5 — Business Layer Alignment and Dynamic Upgrade Logic

_Date: 2026-04-16 06:14 _

## 1. Purpose of the batch
- Make highfreq truly shaped by Business Layer scope rather than remaining only technically runnable.
- Land DB-backed active scope management and dynamic intraday upgrade logic.
- Explicitly distinguish active scope, dynamic upgraded scope, and remaining unsupported/deferred areas.

## 2. What was supposed to be done
- Align current highfreq active scope to:
  - `key_focus`
  - `focus`
  - `tech_key_focus`
  - `tech_focus`
- Make Business Layer selector truth materially shape highfreq runtime scope.
- Implement dynamic intraday upgrade logic for:
  - leader candidates
  - hot movers
  - sector-driven temporary priority elevation
- Clearly distinguish:
  - active highfreq scope
  - unsupported scope
  - deferred scope

## 3. What was actually done
### Scope-management schema landed
Added DB-backed scope-management tables:
- `ifa2.highfreq_active_scope`
- `ifa2.highfreq_dynamic_candidate`

### Business Layer alignment landed
Implemented `highfreq/scope_manager.py` so that the current Business Layer lists now materially populate highfreq scope:
- `key_focus`
- `focus`
- `tech_key_focus`
- `tech_focus`

Priority/tier mapping landed in code:
- `key_focus` -> priority `100`, tier `deep_focus`
- `tech_key_focus` -> priority `95`, tier `deep_focus`
- `focus` -> priority `70`, tier `medium_focus`
- `tech_focus` -> priority `65`, tier `medium_focus`

This means highfreq now has a real DB-backed active scope whose priority is explicitly shaped by Business Layer list type.

### Dynamic intraday upgrade logic landed
Implemented DB-backed dynamic-candidate generation from the derived leader layer:
- input source: `highfreq_leader_candidate_working`
- output table: `highfreq_dynamic_candidate`

Current dynamic upgrade logic uses:
- candidate score
- confirmation state
- continuation health

Trigger reason mapping landed:
- `leader_confirmed`
- `continuation_healthy`
- `leader_candidate`

Upgrade status landed:
- `upgraded`
- `watch`

### Runtime/operator integration landed
Highfreq daemon health now rebuilds and exposes scope status, including:
- `active_count`
- `dynamic_count`
- `active_scope_status`
- `dynamic_scope_status`

So Business Layer alignment is no longer hidden behind code only; it is now visible at the operator surface level.

## 4. Code files changed
- `alembic/versions/033_highfreq_scope_management.py`
- `src/ifa_data_platform/highfreq/scope_manager.py`
- `src/ifa_data_platform/highfreq/daemon.py`
- `tests/integration/test_highfreq_milestone5.py`

## 5. Tests run and results
### Migration
- `alembic upgrade head`
- result: succeeded

### Focused integration tests
- `pytest tests/integration/test_highfreq_milestone5.py -q`
- result: `2 passed`

### Direct validation
- executed `ScopeManager().rebuild()` directly
- executed `python src/ifa_data_platform/highfreq/daemon.py --health`
- both succeeded and returned DB-backed scope evidence

## 6. DB/runtime evidence
### Scope-build result
Direct scope rebuild returned:
- `active_scope_status = active_scope_landed`
- `dynamic_scope_status = dynamic_upgrade_landed`
- `active_count > 0`
- `dynamic_count > 0`

### Active-scope DB evidence
`highfreq_active_scope` is populated from Business Layer lists and includes fields proving provenance and runtime meaning:
- `symbol`
- `asset_category`
- `source_list_type`
- `source_list_name`
- `scope_priority`
- `scope_tier`
- `scope_status`
- `reason`

Sample active-scope rows now show Business Layer provenance directly.

### Dynamic-candidate DB evidence
`highfreq_dynamic_candidate` is populated and includes:
- `symbol`
- `candidate_type`
- `trigger_reason`
- `priority_score`
- `upgrade_status`

This proves highfreq now has a real dynamic upgrade substrate rather than a vague future idea.

### Operator evidence
`python src/ifa_data_platform/highfreq/daemon.py --health` now includes a `scope_status` block with:
- active scope count
- dynamic scope count
- active scope status
- dynamic scope status

## 7. Truthful judgment / result
### What is now real in Milestone 5
- Business Layer lists now materially shape highfreq active scope in a DB-backed way.
- Highfreq now distinguishes priority/tier by Business Layer list type.
- Highfreq now has a real dynamic intraday upgrade table driven from derived leader signals.
- Operator surfaces can now see scope-management status.

### What is still limited / partial
The current dynamic upgrade logic is **real but first-generation**.
It is not yet a fully rich intraday promotion engine.
Current limitations:
- dynamic upgrade is currently driven mainly by leader-candidate derived output
- hot-mover logic is still approximated through the same candidate/score pathway
- sector-driven temporary priority elevation is present only indirectly through current derived signal inputs and active-scope prioritying, not yet a richer standalone sector-expansion engine

These are implementation-depth limitations, not fake-support issues.

## 8. Residual gaps / blockers / deferred items
### Partial in this batch
- hot movers
  - current state: partially implemented through leader/candidate scoring pathway
  - reason class: **implementation depth limitation**
- sector-driven temporary priority elevation
  - current state: partially implemented / indirect only
  - reason class: **implementation depth limitation**

### No fake completeness maintained
This batch claims:
- real Business Layer alignment
- real DB-backed active scope
- real DB-backed dynamic candidate upgrade substrate

It does **not** claim the full final richness of future intraday promotion logic is complete.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- Before this batch, Business Layer influenced highfreq only implicitly through the broader manifest story.
- After this batch, highfreq has explicit DB-backed active scope and explicit DB-backed dynamic candidates.
- Dynamic intraday upgrade logic must be described as landed-but-first-generation, not fully mature.
