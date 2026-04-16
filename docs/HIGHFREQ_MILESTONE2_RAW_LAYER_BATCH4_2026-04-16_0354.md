# Highfreq Milestone 2 — Raw Data Ingestion Layer (Batch 4)

_Date: 2026-04-16 03:54 _

## 1. Purpose of the batch
- Continue Milestone 2 on the remaining raw-scope closure.
- Land the real futures / commodity / precious_metal 1-minute path with non-zero live contract-resolution evidence.
- Finish the current truthful L2 source-verification classification.

## 2. What was supposed to be done
- Close `futures_commodity_pm_1m_ohlcv` only if there is real non-zero live contract-resolution evidence.
- Verify L2-related source support and classify it truthfully instead of implying support.

## 3. What was actually done
### Futures-family minute source truth
- Verified that `ft_mins` is a real source path.
- Implemented live contract resolution using `fut_basic` by selecting currently valid contracts from multiple representative roots across:
  - precious metal
  - commodity
  - general futures/industrial futures
- Verified non-zero live source evidence, especially for an actually trading representative contract:
  - `SC2605.INE` returned non-zero volume/amount minute rows
- Landed the real futures-family minute source → storage → runtime path.

### L2 truth verification
Checked candidate Tushare/source paths for true L2-style requirements.
Current result:
- no source-proven Tushare path was verified for true:
  - snapshot
  - order queue
  - tick-by-tick order
  - tick-by-tick trade
- Some market-structure/behavior proxies do exist and work (for example `cyq_perf`, `moneyflow_ind_ths`, `moneyflow_ind_dc`, `limit_list_d`, `hm_list`), but they are **not** true L2 snapshot/order-queue/tick-by-tick interfaces.
- Therefore L2 scope is truthfully classified as deferred due to source limitation.

## 4. Code files changed
- `alembic/versions/030_highfreq_futures_minute.py`
- `src/ifa_data_platform/highfreq/persistence.py`
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- `src/ifa_data_platform/highfreq/runner.py`
- `tests/integration/test_highfreq_milestone2_batch4.py`

## 5. Tests run and results
### Migration
- `alembic upgrade head`
- result: succeeded

### Focused integration tests
- `pytest tests/integration/test_highfreq_milestone2_batch4.py -q`
- result: `2 passed`

### Direct runtime validation
- `python scripts/runtime_manifest_cli.py run-once --lane highfreq --owner-type default --owner-id default`
- result: full currently-landed raw set now succeeds end-to-end

## 6. DB/runtime evidence
### Latest highfreq run
- run id: `3b039d5e-47c7-4fb3-a7a9-f1e4cfa2529b`
- lane: `highfreq`
- execution mode: `partial_real_run`
- unified final status: `succeeded`
- executed dataset count: `7`

Dataset truth in this run:
- `stock_1m_ohlcv` -> `succeeded`, `records_processed = 6`
- `index_1m_ohlcv` -> `succeeded`, `records_processed = 6`
- `etf_sector_style_1m_ohlcv` -> `succeeded`, `records_processed = 1`
- `futures_commodity_pm_1m_ohlcv` -> `succeeded`, `records_processed = 40`
- `open_auction_snapshot` -> `succeeded`, `records_processed = 1`
- `close_auction_snapshot` -> `succeeded`, `records_processed = 1`
- `event_time_stream` -> `succeeded`, `records_processed = 400`

### Live contract-resolution evidence
Representative resolved contracts with real minute rows in this batch included examples such as:
- `AU2604.SHF`
- `AG2604.SHF`
- `I2604.DCE`
- `TA2604.ZCE`
- `SC2605.INE`
- `RB2604.SHF`
- `JM2604.DCE`
- `FG2604.ZCE`

Important truthful evidence:
- not all resolved contracts had non-zero `vol/amount`
- but the path is now truthfully closed because live non-zero representative evidence exists, especially `SC2605.INE`

### Working-table evidence
- `highfreq_futures_minute_working = 40`
- `highfreq_index_1m_working = 6`
- `highfreq_proxy_1m_working = 1`
- `highfreq_event_stream_working = 2000`
- `highfreq_stock_1m_working = 6`

This proves the currently landed raw layer spans:
- stock minute
- index minute
- proxy path
- futures-family minute
- auction snapshots
- event stream

## 7. Truthful judgment / result
### What is now real in Milestone 2 after this batch
Real source → storage → runtime paths now exist for:
- stock 1-minute OHLCV
- index 1-minute OHLCV
- ETF/sector/style proxy-based path
- futures / commodity / precious_metal 1-minute path
- open auction snapshot
- close auction snapshot
- event timestamp stream

### L2 truth after verification
The current milestone result for true L2 scope is:
- `snapshot` -> deferred
- `order queue` -> deferred
- `tick-by-tick order` -> deferred
- `tick-by-tick trade` -> deferred

Reason class for all four:
- **source limitation**

There is no source-proven true L2 interface verified in the current source/runtime path.

## 8. Residual gaps / blockers / deferred items
### Deferred in this batch
- `l2_snapshot`
  - reason class: **source limitation**
- `order_queue`
  - reason class: **source limitation**
- `tick_order`
  - reason class: **source limitation**
- `tick_trade`
  - reason class: **source limitation**

### No fake completeness maintained
- The raw Day-1 non-L2 layer is now materially landed.
- True L2 scope is **not** silently implied; it is explicitly deferred because current source truth did not verify support.

## 9. Whether docs/runtime truth had to be corrected
Yes.
- `futures_commodity_pm_1m_ohlcv` is no longer deferred; it is now a landed real path.
- L2-like market-structure proxy APIs are explicitly distinguished from true L2 snapshot/order-queue/tick-level interfaces.
- Therefore the truthful current state is:
  - core Day-1 highfreq raw layer materially landed
  - true L2 scope deferred due to source limitation
