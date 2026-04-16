# Trailblazer Remaining Work To-Do

> **Document status:** Intermediate durable remaining-work baseline. Preserved for continuity and auditability. Not itself the canonical runtime-truth document set.
_Date: 2026-04-15 22:51 _

## 1. Current source-of-truth context
- Data Platform repo: `/Users/neoclaw/repos/ifa-data-platform`
- Business Layer repo: `/Users/neoclaw/repos/ifa-business-layer`
- Database URL: `postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp`
- DB schema: `ifa2`
- Current branch: `main`
- Current HEAD at file creation: `d11a8ba`
- Current active phase meaning:
  - Trailblazer main-line work is already done.
  - Current work is production-closure and truth-alignment for archive / lowfreq / midfreq / minute under real repo + DB + runtime evidence.
  - Highfreq remains out of immediate scope unless current repo/runtime truth changes.

## 2. Remaining work understanding

### Archive
In scope:
- current archive implementation vs Business Layer archive target reality
- explicit truth for daily / 15min / minute
- explicit truth for stock / macro / futures / commodity / precious_metal where relevant
- real source/storage/runtime alignment
- operator/query/runtime evidence alignment
- doc correction where old wording drifts from current truth

Current understanding:
- unified archive lane now runs in `real_run`
- truthful active archive scope is now:
  - stock / futures / commodity / precious_metal: daily + 15min + minute
  - macro: historical/daily only
- Business Layer still contains macro intraday archive targets that exceed current truthful support
- archive runtime scope is now aligned to truthful support, but docs/tests/operator wording still need full cleanup against that reality

### Lowfreq
In scope:
- runnable coverage truth
- storage truth
- daemon/service-mode truth
- operator/audit/query truth
- current category-coverage truth vs selector/config presence
- residual production gaps that still matter for 24x7 operation

Current understanding:
- lowfreq current proof set has real non-dry-run evidence and is materially stronger than older single-dataset wording
- lowfreq still needs disciplined truth statement separating:
  - selector/category breadth
  - configured dataset breadth
  - actually proven runtime/storage/operational breadth
- service-mode / operator visibility / state persistence truth still needs durable reconciliation against current runtime, not just prior docs

### Midfreq
In scope:
- mandatory proof-set truth
- broader configured-set truth
- real non-dry-run vs dry-run truth
- TUSHARE_TOKEN production expectation
- schema drift / runtime drift / service-mode truth
- operator/audit/query truth

Current understanding:
- midfreq current proof set is materially stronger than older docs suggested
- real-run evidence exists for the current proof set under the current environment
- broader configured-set truth still needs explicit separation from the current proven set
- TUSHARE_TOKEN remains a real production dependency and must be stated as such
- any remaining configured-set/schema mismatches must be classified individually, not hand-waved

### Minute data
In scope:
- minute must be explicitly accounted for wherever Business Layer currently defines minute targets
- every minute path must be either:
  - implemented/proven, or
  - explicitly classified as unsupported by current source/schema/runtime truth

Current understanding:
- minute archive is now real for stock / futures / commodity / precious_metal
- macro minute is not truthfully supported and has been removed from active archive runtime scope
- remaining minute-related work is mainly truth alignment and any residual operator/doc/test cleanup around this corrected scope

### Final production closure
In scope:
- 24x7 operability standard
- state persistence
- checkpoint / resume truth
- queryability
- operator visibility
- service-mode smoke truth
- runtime evidence
- final doc truth alignment

Current understanding:
- remaining work is no longer broad architecture design
- remaining work is disciplined closure of runtime truth, operator truth, test truth, and doc truth against current repo + DB + runtime evidence

### Out of scope right now
- highfreq implementation expansion
- Business Layer repo modifications unless explicitly required later
- ACP / Codex / delegation execution paths

## 3. Comparison section: current understanding vs required remaining work

### Did current understanding fully match the required scope?
- **Not fully at first. It needed correction and broadening.**

### What was missing / under-scoped and how it was corrected
1. **Archive scope was initially treated too narrowly as a runtime-only fix surface.**
   - Corrected to include explicit comparison against Business Layer archive target definitions by category and frequency.
2. **Lowfreq and midfreq remaining work were initially under-emphasized after archive truth alignment started landing.**
   - Corrected to keep both lanes in active remaining-work scope for runtime truth, storage truth, service truth, and operator truth.
3. **Minute data risked being treated as “already handled” once archive minute execution was proven.**
   - Corrected to treat minute as an ongoing scope item wherever Business Layer defines minute targets, with explicit truth classification still required for unsupported categories like macro.
4. **Final closure criteria needed to be framed as 24x7 operability, not just successful one-shot execution.**
   - Corrected by explicitly including persistence, checkpointing, service-mode truth, operator visibility, queryability, and doc truth alignment in the durable to-do scope.

## 4. Actionable to-do list

### A1. Refresh archive tests to corrected truthful runtime scope
- Type: validation work + doc-correction work
- Why it matters: tests must match the corrected supported scope after disabling unsupported macro intraday archive jobs
- Depends on real support: yes; expectations must follow current real source/storage/runtime support

### A2. Reconcile archive docs/operators surfaces to corrected macro support truth
- Type: doc-correction work + evidence work
- Why it matters: stale docs/tests/operator assumptions can silently recreate false support claims
- Depends on real support: yes; macro intraday must remain classified unsupported unless made real

### A3. Re-ground lowfreq current 24x7 truth
- Type: validation work + evidence work + possible implementation work
- Why it matters: lowfreq must be judged by runnable/service/operator/storage truth, not just current proof-set success
- Depends on real support: yes; category claims must track actual source/storage/runtime support

### A4. Re-ground midfreq current 24x7 truth
- Type: validation work + evidence work + possible implementation work
- Why it matters: current proof set is stronger, but broader configured-set truth and service truth still need exact classification
- Depends on real support: yes; dry-run/non-dry-run/service claims must follow actual runtime behavior and TUSHARE-backed source reality

### A5. Reconcile Business Layer asks vs Data Platform truth lane-by-lane
- Type: evidence work + doc-correction work + possible implementation work
- Why it matters: unsupported assumptions must become either implemented reality or explicit documented truth
- Depends on real support: yes by definition

### A6. Final closure packaging at production standard
- Type: evidence work + doc-correction work
- Why it matters: final state must be operator-readable, auditable, resumable, and stable under session resets
- Depends on real support: yes; no fake completeness claims allowed

## 5. Truth-handling rule
- If something lacks real source/schema/runtime/storage support, it must not remain in an ambiguous implied-supported state.
- It must become one of the following:
  1. implemented truthfully, or
  2. explicitly documented as unsupported / limited / deferred with exact reason.
- Selector presence, config presence, and runtime support are not interchangeable.

## 6. Reporting discipline
- Every future real batch gets its own new timestamped Markdown file under `docs/`.
- Do not overwrite ambiguous filenames as the primary batch record.
- Each batch record must include:
  - purpose
  - intended work
  - actual work done
  - changed files
  - tests run and results
  - DB/runtime evidence
  - truthful judgment
  - residual gaps/blockers
  - whether docs had to be corrected
- Do not rely on stale chat summaries as the continuity layer.
