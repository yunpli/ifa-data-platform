# Highfreq Milestone 2 — Raw Data Ingestion Layer (Batch 3)

_Date: 2026-04-16 03:48 _

## 1. Purpose of the batch
- Continue Milestone 2 on the next raw-scope priorities without leaving the milestone.
- Land the exact index 1-minute path.
- Land the first ETF/sector/style proxy-based highfreq path.
- Keep futures-family minute and L2 truthfully classified instead of guessed.

## 2. What was supposed to be done
Priority order for this batch:
1. futures / commodity / precious_metal 1-minute raw path
2. ETF / sector / style proxy 1-minute path
3. exact index 1-minute source verification and landing
4. L2 source verification and truthful implement/defer classification

## 3. What was actually done
### Source-truth verification results
- Exact index 1-minute source path is now verified:
  - `stk_mins` works for index code `000001.SH`
- ETF / sector / style proxy path is feasible via proxy modeling:
  - `ths_daily` works and provides real proxy data usable for the first landed path
- futures-family minute source remains only partially verified:
  - `ft_mins` exists as an API path
  - but the sample contracts used in this batch still did not provide non-zero closure evidence
- L2-related scope remains not source-proven in this batch

### Real raw-layer implementation landed in this batch
Implemented the next real source → storage → runtime closures for:
- `index_1m_ohlcv`
- `etf_sector_style_1m_ohlcv`

### Storage direction extended
Added working tables:
- `ifa2.highfreq_index_1m_working`
- `ifa2.highfreq_proxy_1m_working`

### Real implementation issue found and fixed
- First proxy landing failed because the initial `proxy_type` string exceeded the schema column width (`varchar(32)`).
- This was an implementation limitation, not a source limitation.
- Fixed by normalizing proxy type to a shorter stable value: `ths_sector_proxy`.

## 4. Code files changed
- `alembic/versions/029_highfreq_proxy_index_tables.py`
- `src/ifa_data_platform/highfreq/persistence.py`
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- `src/ifa_data_platform/highfreq/runner.py`
- `tests/integration/test_highfreq_milestone2_batch3.py`

## 5. Tests run and results
### Migration
- `alembic upgrade head`
- result: succeeded

### Focused integration tests
- `pytest tests/integration/test_highfreq_milestone2_batch3.py -q`
- result: `2 passed`

### Direct runtime validation
- `python scripts/runtime_manifest_cli.py run-once --lane highfreq --owner-type default --owner-id default`
- result: partial real-run, with index/proxy now succeeded

## 6. DB/runtime evidence
### Latest highfreq run
- run id: `a0e77b59-59c9-4225-bf51-3fe436076f39`
- lane: `highfreq`
- execution mode: `partial_real_run`
- unified final status: `partial`
- executed dataset count: `7`

Dataset truth in this run:
- `stock_1m_ohlcv` -> `succeeded`, `records_processed = 6`
- `index_1m_ohlcv` -> `succeeded`, `records_processed = 6`
- `etf_sector_style_1m_ohlcv` -> `succeeded`, `records_processed = 1`
- `futures_commodity_pm_1m_ohlcv` -> `deferred`, `records_processed = 0`
- `open_auction_snapshot` -> `succeeded`, `records_processed = 1`
- `close_auction_snapshot` -> `succeeded`, `records_processed = 1`
- `event_time_stream` -> `succeeded`, `records_processed = 400`

### Working-table evidence
- `highfreq_index_1m_working = 6`
- `highfreq_proxy_1m_working = 1`
- `highfreq_event_stream_working = 1600`
- `highfreq_stock_1m_working = 6`

This proves the highfreq raw layer now has multiple independent working-table outputs:
- stock minute
- index minute
- proxy minute-like path
- auction snapshots
- event stream

## 7. Truthful judgment / result
### What is now real in Milestone 2 after this batch
Real source → storage → runtime paths now exist for:
- stock 1-minute OHLCV
- index 1-minute OHLCV
- ETF/sector/style proxy-based path
- open auction snapshot
- close auction snapshot
- event timestamp stream

### What remains unclosed in Milestone 2
Still not truthfully closed yet:
- futures / commodity / precious_metal 1-minute raw path
- L2 snapshot
- order queue
- tick-by-tick order
- tick-by-tick trade

## 8. Residual gaps / blockers / deferred items
### Deferred in this batch
- `futures_commodity_pm_1m_ohlcv`
  - current batch status: `deferred`
  - reason class: **source verification incomplete**
  - note: `ft_mins` exists, but this batch still does not have live non-zero contract-resolution evidence
- `l2_snapshot`, `order_queue`, `tick_order`, `tick_trade`
  - current batch status: not landed
  - reason class: **source verification not completed yet**

### Implementation issue fixed in batch
- Proxy path first failed due to storage-column width mismatch for `proxy_type`.
- reason class: **implementation limitation**
- current state after fix: resolved and landed

## 9. Whether docs/runtime truth had to be corrected
Yes.
- `index_1m_ohlcv` is no longer deferred; it is now a landed real path.
- `etf_sector_style_1m_ohlcv` is no longer purely conceptual; it now has a first real proxy-based landed path.
- futures-family minute and L2 scope remain explicitly partial/deferred, not vaguely implied.
