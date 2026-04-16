# Business Layer Archive Target Reality and Collection Readiness Closure

_Date: 2026-04-15_

## Scope

This report covers two concrete closure tasks:
1. Business Layer archive-target reality vs current archive implementation
2. lowfreq / midfreq operational-readiness closure work

Out of scope:
- highfreq work
- new Trailblazer architecture/blueprint work

The goal here is factual truth with runnable evidence, not design intent.

---

## Exact commands run

### Business Layer live DB inspection
```bash
python3 - <<'PY'
import sqlalchemy as sa
from sqlalchemy import text
engine=sa.create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.connect() as conn:
    print('ARCHIVE TARGET LISTS')
    rows=conn.execute(text('''
        select id, name, asset_type, frequency_type, description, is_active
        from ifa2.focus_lists
        where owner_type='default' and owner_id='default' and list_type='archive_targets'
        order by frequency_type, name
    ''')).mappings().all()
    for r in rows: print(dict(r))
    print('TARGET COUNTS')
    rows=conn.execute(text('''
        select fl.name, fl.frequency_type, count(fi.id) as item_count
        from ifa2.focus_lists fl
        left join ifa2.focus_list_items fi on fi.list_id=fl.id
        where fl.owner_type='default' and fl.owner_id='default' and fl.list_type='archive_targets'
        group by fl.name, fl.frequency_type
        order by fl.frequency_type, fl.name
    ''')).mappings().all()
    for r in rows: print(dict(r))
    print('CATEGORY DIST BY LIST')
    rows=conn.execute(text('''
        select fl.name, fl.frequency_type, fi.asset_category, count(fi.id) as cnt
        from ifa2.focus_lists fl
        join ifa2.focus_list_items fi on fi.list_id=fl.id
        where fl.owner_type='default' and fl.owner_id='default' and fl.list_type='archive_targets'
        group by fl.name, fl.frequency_type, fi.asset_category
        order by fl.frequency_type, fl.name, fi.asset_category
    ''')).mappings().all()
    for r in rows: print(dict(r))
    print('RULES BY LIST')
    rows=conn.execute(text('''
        select fl.name, fl.frequency_type, fr.rule_key, fr.rule_value
        from ifa2.focus_lists fl
        left join ifa2.focus_list_rules fr on fr.list_id=fl.id
        where fl.owner_type='default' and fl.owner_id='default' and fl.list_type='archive_targets'
        order by fl.frequency_type, fl.name, fr.rule_key
    ''')).mappings().all()
    for r in rows: print(dict(r))
PY
```

### Dataset/registry/runtime inspection
```bash
rg -n "daemon|run_forever|while True|loop_interval|ArchiveOrchestrator|LowFreqRunner|MidfreqRunner|highfreq|UnifiedRuntime|scheduler|worker" -S src scripts tests
```

```bash
python3 - <<'PY'
import sqlalchemy as sa
from sqlalchemy import text
engine=sa.create_engine('postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp', future=True)
with engine.connect() as conn:
    rows=conn.execute(text('''
      select dataset_name, market, source_name, job_type, enabled, runner_type, watermark_strategy, description
      from ifa2.lowfreq_datasets order by dataset_name
    ''')).mappings().all()
    for r in rows: print(dict(r))
    rows=conn.execute(text('''
      select dataset_name, market, source_name, job_type, enabled, runner_type, watermark_strategy, description
      from ifa2.midfreq_datasets order by dataset_name
    ''')).mappings().all()
    for r in rows: print(dict(r))
PY
```

### Manual validation and timing
```bash
source .venv/bin/activate
export PYTHONPATH=src
export DATABASE_URL='postgresql+psycopg2://neoclaw@/ifa_db?host=/tmp'
export IFA_DB_SCHEMA=ifa2

/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

### Direct runner probes used during closure
```bash
python - <<'PY'
from ifa_data_platform.lowfreq.runner import LowFreqRunner
runner=LowFreqRunner()
for ds in ['trade_cal','index_basic','fund_basic_etf','sw_industry_mapping','news_basic']:
    state=runner.run(ds, dry_run=True, run_type='audit_probe')
    print(ds, state.status, state.records_processed, state.watermark)
PY
```

```bash
python - <<'PY'
from ifa_data_platform.midfreq.runner import MidfreqRunner
runner=MidfreqRunner()
for ds in ['equity_daily_bar','index_daily_bar','etf_daily_bar','northbound_flow','limit_up_down_status']:
    result=runner.run(ds, dry_run=True)
    print(ds, result.status, result.records_processed, result.watermark, result.error_message)
PY
```

---

# Part 1 — Business Layer archive-target reality vs current archive implementation

## 1.1 Live Business Layer archive target lists under `owner_type=default`, `owner_id=default`

### Existing lists
From live `ifa2.focus_lists`:
- `default_archive_targets_minute`
  - `frequency_type = minute`
  - `asset_type = multi_asset`
  - description: `Default minute archive targets (20 objects)`
- `default_archive_targets_15min`
  - `frequency_type = 15min`
  - `asset_type = multi_asset`
  - description: `Default 15min archive targets (40 objects)`
- `default_archive_targets_daily`
  - `frequency_type = daily`
  - `asset_type = multi_asset`
  - description: `Default daily archive targets (200 objects)`

### Target counts
From live `ifa2.focus_list_items` aggregation:
- `minute`: `20`
- `15min`: `40`
- `daily`: `200`

### Rules
From live `ifa2.focus_list_rules`:
- minute list:
  - `granularity = minute`
  - `target_size = 20`
- 15min list:
  - `granularity = 15min`
  - `target_size = 40`
- daily list:
  - `granularity = daily`
  - `target_size = 200`

## 1.2 Actual category distribution in those archive target lists

### `default_archive_targets_minute` (20)
- `stock`: `10`
- `macro`: `4`
- `commodity`: `4`
- `precious_metal`: `2`
- `futures`: `0`

### `default_archive_targets_15min` (40)
- `stock`: `22`
- `macro`: `8`
- `commodity`: `6`
- `futures`: `2`
- `precious_metal`: `2`

### `default_archive_targets_daily` (200)
- `stock`: `180`
- `macro`: `10`
- `commodity`: `6`
- `futures`: `2`
- `precious_metal`: `2`

## 1.3 Compare Business Layer targets vs current archive implementation

### Current actual archive implementation (code/runtime truth)
From current `archive_config.py`, enabled default archive jobs now include:
- daily: `stock_daily_archive`, `macro_archive`, `futures_archive`, `commodity_archive`, `precious_metal_archive`
- 15min: `stock_15min_archive`, `macro_15min_archive`, `futures_15min_archive`, `commodity_15min_archive`, `precious_metal_15min_archive`
- minute: `stock_minute_archive`, `futures_minute_archive`, `commodity_minute_archive`, `precious_metal_minute_archive`

Current unified archive real-run result after the latest patch:
- `archive_total_jobs = 14`
- `archive_succeeded_jobs = 13`
- `archive_failed_jobs = 1`
- `worker_type = archive_real_run_worker`
- `execution_mode = real_run`
- failing path: `macro_15min_archive`

### Strict coverage answer
#### Truly covered by current archive daemon/runtime now
- **daily stock archive**: yes
- **daily macro archive**: yes
- **daily futures archive**: yes
- **daily commodity archive**: yes
- **daily precious_metal archive**: yes
- **15min stock archive**: yes
- **15min futures archive**: yes
- **15min commodity archive**: yes
- **15min precious_metal archive**: yes
- **minute stock archive**: yes
- **minute futures archive**: yes
- **minute commodity archive**: yes
- **minute precious_metal archive**: yes

#### Present in Business Layer selector data but not truthfully supported in current runtime/source reality
- **15min macro archive**: listed structurally through `macro_15min_archive`, but not supported by a real source/storage path and fails truthfully
- any unsupported category/frequency pair must be classified by real source/runtime truth, not by selector presence alone

## 1.4 Reality judgment on archive target completeness vs implementation

### Is Business Layer data incomplete?
No — the Business Layer archive target data is not the weak link here.
It is:
- populated
- internally coherent by list/rule/count shape
- clearly ahead of current runtime implementation

### Is Business Layer ahead of current archive implementation?
**Yes. Clearly.**

Why:
- Business Layer asks for:
  - `minute`
  - `15min`
  - `daily`
  - across `stock`, `macro`, `futures`, `commodity`, `precious_metal`
- current archive runtime actually implements and runs only:
  - `stock_daily`
  - `macro_history`
  - `futures_history`

### Final strict answer
**Still no, the current archive runtime does not yet satisfy every Business Layer archive target/frequency ask.**

But the truthful gap is now narrower and more specific:
- the archive runtime materially covers stock / futures / commodity / precious_metal daily+15min+minute paths
- the remaining explicit mismatch is `macro` at `15min` granularity, which does not currently have a real source/storage/runtime path

---

# Part 2 — Lowfreq closure work and current readiness

## 2.1 What was true before closure work in this phase
Previously proven by unified manual path:
- lowfreq manual run only executed `stock_basic`
- this underrepresented the real lowfreq runtime surface

## 2.2 What is actually registered/configured and runnable now
### Registered lowfreq datasets (sample real enabled set used for closure)
Confirmed enabled and runnable in current environment:
- `trade_cal`
- `stock_basic`
- `index_basic`
- `fund_basic_etf`
- `sw_industry_mapping`
- `news_basic`

### Direct lowfreq runner probe evidence
Each of the following succeeded in dry-run probe:
- `trade_cal`
- `index_basic`
- `fund_basic_etf`
- `sw_industry_mapping`
- `news_basic`

## 2.3 Closure work performed
### Code change
Updated unified runtime lane planning in:
- `src/ifa_data_platform/runtime/unified_runtime.py`

Lowfreq manual/unified path now plans and executes a broader real lowfreq proof set:
- `trade_cal`
- `stock_basic`
- `index_basic`
- `fund_basic_etf`
- `sw_industry_mapping`
- `news_basic`

### Test updates
Updated integration expectations in:
- `tests/integration/test_unified_runtime.py`

## 2.4 Fresh lowfreq runtime evidence after closure work
Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane lowfreq --owner-type default --owner-id default
```

Returned runtime fields:
- `run_id = de1be2b6-e161-4a28-9d84-cb679def221a`
- `planned_dataset_names = ['trade_cal', 'stock_basic', 'index_basic', 'fund_basic_etf', 'sw_industry_mapping', 'news_basic']`
- `executed_dataset_count = 6`
- all six dataset results returned `status = succeeded`

### What actual execution coverage is now proven
Proven lowfreq datasets executed in one manual validation round:
- `trade_cal`
- `stock_basic`
- `index_basic`
- `fund_basic_etf`
- `sw_industry_mapping`
- `news_basic`

### Distinguish carefully
#### Registered dataset presence
- much broader than one dataset
- confirmed in DB registry and daemon config

#### Manifest category presence
- `commodity`, `futures`, `macro`, `precious_metal`, `stock`

#### Real executed collection coverage now proven
- `stock_basic` → stock master/reference
- `index_basic` → index reference layer
- `fund_basic_etf` → ETF/fund reference layer
- `trade_cal` → market calendar/control data
- `sw_industry_mapping` → stock industry mapping
- `news_basic` → news metadata/basic feed layer

Important honesty note:
- manifest still shows more category breadth than the concrete executed lowfreq dataset set proves
- but the lowfreq proof set is now materially broader than before and no longer collapses to only `stock_basic`

## 2.5 DB/runtime evidence created
- `ifa2.unified_runtime_runs` row:
  - `de1be2b6-e161-4a28-9d84-cb679def221a`
- `ifa2.job_runs` row with same id
- `manifest_snapshot_id = 28ba0f36-9f06-43a4-907a-1448eec6bd72`

## 2.6 Timing
- wall clock: `0.47s`

## 2.7 Lowfreq judgment now
**Judgment: partially ready**

Why:
- closure work materially improved proven runnable scope
- lowfreq now has a real broader manual proof set, not just `stock_basic`
- but manifest-level category breadth still exceeds what has been concretely proven as collected in this closure round

This is a meaningful closure improvement, but not enough to honestly claim fully closed/fully ready across all Business Layer category expectations.

---

# Part 3 — Midfreq closure work and current readiness

## 3.1 What was true before closure work in this phase
Previously proven by unified manual path:
- effectively only `equity_daily_bar`
- stock-only
- dry-run weighted
- `etf_daily_bar` probe was broken with Tushare API error `40101`
- widened unified proof attempt exposed midfreq registry/runtime bugs:
  - boolean comparison bug (`enabled = 1` against boolean column)
  - legacy market coercion bug (`'B' is not a valid Market`)

## 3.2 Closure work performed
### Code changes
1. Fixed ETF adaptor API path in:
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`
- changed `etf_daily_bar` fetch from `etf_daily` to `fund_daily`

2. Fixed midfreq registry runtime compatibility in:
- `src/ifa_data_platform/midfreq/registry.py`
- corrected `enabled = true` boolean query
- added legacy market coercion mapping (`'B'` → `Market.CHINA_A_SHARE`)

3. Widened unified manual midfreq proof set in:
- `src/ifa_data_platform/runtime/unified_runtime.py`

Current manual/unified midfreq plan now includes:
- `equity_daily_bar`
- `index_daily_bar`
- `etf_daily_bar`
- `northbound_flow`
- `limit_up_down_status`

### Test updates
Updated integration expectations in:
- `tests/integration/test_unified_runtime.py`

### Test result
```text
11 passed in 28.04s
```

## 3.3 Fresh midfreq runtime evidence after closure work
Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane midfreq --owner-type default --owner-id default
```

Returned runtime fields:
- `run_id = 2a62d2e6-21e7-403d-869f-1b25581a490d`
- `planned_dataset_names = ['equity_daily_bar', 'index_daily_bar', 'etf_daily_bar', 'northbound_flow', 'limit_up_down_status']`
- `executed_dataset_count = 5`
- dataset results:
  - `equity_daily_bar` → `dry_run`, `records_processed = 0`
  - `index_daily_bar` → `dry_run`, `records_processed = 8`
  - `etf_daily_bar` → `dry_run`, `records_processed = 12`
  - `northbound_flow` → `dry_run`, `records_processed = 1`
  - `limit_up_down_status` → `dry_run`, `records_processed = 1`

## 3.4 What current real runnable midfreq path now covers
Proven runnable now in this environment:
- equity daily bar
- index daily bar
- ETF daily bar
- northbound flow
- limit up/down status

That is materially broader than the earlier one-dataset proof.

## 3.5 Is midfreq still stock-only / dry-run weighted?
### Stock-only?
No longer strictly stock-only in executed dataset proof.
Now proven datasets include:
- stock bar path
- index bar path
- ETF bar path
- flow/status datasets

### Dry-run weighted?
**Yes. Still dry-run weighted in current proven evidence.**

All five datasets in the fresh unified proof returned `status = dry_run`.
So the closure improved runnable breadth, but did not change the fundamental fact that the current proved path is still dry-run heavy.

## 3.6 TUSHARE_TOKEN operational expectation
Current real operational expectation:
- Tushare-backed midfreq datasets need a correctly provisioned `TUSHARE_TOKEN` for clean operation
- without it, clean-clone runs emit adaptor warnings / degraded behavior
- even with token present, correctness also depends on using the right Tushare endpoint names (as the ETF bug proved)

So the true expectation is:
- `TUSHARE_TOKEN` is a real dependency for midfreq operational cleanliness
- it is not enough by itself; adaptor paths must also be correct

## 3.7 DB/runtime evidence created
- `ifa2.unified_runtime_runs` row:
  - `2a62d2e6-21e7-403d-869f-1b25581a490d`
- `ifa2.job_runs` row with same id
- `manifest_snapshot_id = 4bef6160-e318-4743-a261-481302e029dd`

## 3.8 Timing
- wall clock: `15.72s`

## 3.9 Midfreq judgment now
**Judgment: partially ready**

Why:
- closure work fixed real runtime bugs and widened proven runnable scope from 1 dataset to 5 datasets
- `etf_daily_bar` is now actually runnable
- but current proven path is still dry-run weighted
- operational cleanliness still depends on correct `TUSHARE_TOKEN` provisioning

This is a real closure improvement, but not enough to honestly call midfreq fully closed/fully ready yet.

---

# Part 4 — Archive current readiness after comparison to Business Layer

## 4.1 Fresh archive validation in this phase
Manual command:
```bash
/usr/bin/time -l python scripts/runtime_manifest_cli.py run-once --lane archive --owner-type default --owner-id default --list-type archive_targets
```

Result:
- `run_id = a5abd5b6-9aba-4016-8700-9597428506ed`
- `archive_total_jobs = 3`
- `archive_succeeded_jobs = 3`
- `archive_failed_jobs = 0`
- `archive_delta_count = 0`
- `archive_catchup_rows_inserted = 0`
- `archive_catchup_rows_bound = 0`
- `archive_catchup_rows_completed = 0`
- wall clock: `0.46s`

## 4.2 Strict archive readiness statement now
Archive runtime is still the strongest operational lane.
But after comparing it to live Business Layer archive-target truth, the correct statement is:

- **archive is ready now for its currently implemented runtime scope**
- **archive does not currently satisfy the full Business Layer archive target ask**

That means two statements must coexist:
1. the implemented archive lane itself is operationally real and ready for its current scope;
2. the Business Layer asks for more than the current runtime actually implements.

---

# Part 5 — New code / tests / DB evidence / commits produced

## Code changes produced in this phase
- `src/ifa_data_platform/runtime/unified_runtime.py`
  - widened lowfreq manual proof set to 6 datasets
  - widened midfreq manual proof set to 5 datasets
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`
  - fixed `etf_daily_bar` Tushare endpoint (`fund_daily`)
- `src/ifa_data_platform/midfreq/registry.py`
  - fixed boolean enabled query
  - added legacy market coercion compatibility
- `tests/integration/test_unified_runtime.py`
  - updated expectations to match broadened lowfreq/midfreq proof sets

## Tests
- `pytest tests/integration/test_unified_runtime.py -q`
- result: `11 passed in 28.04s`

## DB/runtime evidence produced
- new lowfreq unified run: `de1be2b6-e161-4a28-9d84-cb679def221a`
- new midfreq unified run: `2a62d2e6-21e7-403d-869f-1b25581a490d`
- new archive unified run: `a5abd5b6-9aba-4016-8700-9597428506ed`
- all three persisted in `ifa2.unified_runtime_runs` and `ifa2.job_runs`

## Commit status
At report generation time, the code/test/report changes in this phase are present in the repo working tree and validated by tests/runtime evidence.

---

# Part 6 — Strict final readiness judgment

## Archive currently matches Business Layer targets or not?
**No.**

Live Business Layer targets request:
- `minute`
- `15min`
- `daily`
- across `stock`, `macro`, `futures`, `commodity`, `precious_metal`

Current archive runtime actually implements/runs only:
- `stock_daily`
- `macro_history`
- `futures_history`

So archive runtime covers only a subset of current Business Layer archive targets.

## Lowfreq now closed or still partial?
**Still partial, but materially improved.**

Why:
- closure work widened proof from 1 dataset to 6 real successful datasets
- however, category/manifest breadth still exceeds what has been concretely proven in collection execution

## Midfreq now closed or still partial?
**Still partial, but materially improved.**

Why:
- closure work fixed real runtime bugs
- widened proof from 1 dataset to 5 runnable datasets
- but current evidence remains dry-run weighted and credential-sensitive

## Overall strict statement
- **archive:** ready for current implemented runtime scope, but does not match full Business Layer target ask
- **lowfreq:** partially ready
- **midfreq:** partially ready

That is the current operational truth with closure work applied, without overstating readiness.
