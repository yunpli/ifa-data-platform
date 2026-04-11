# Job 9: Lowfreq Asset Extension Plan

## Overview

Extends iFA data platform with low-frequency slow variable and structural datasets from Tushare. These datasets provide long-term asset value for the iFA China-market data platform.

## Dataset List

| # | Dataset | Tushare API | Description | Priority |
|---|---------|------------|-------------|----------|
| 1 | index_weight | index_weight | Index constituent weights | P0 |
| 2 | etf_basic | fund_basic (ETF subset) | ETF structure | P0 |
| 3 | etf_daily_basic | etf_daily_basic | ETF daily market data | P0 |
| 4 | name_change | name_change | Stock name history | P1 |
| 5 | company_basic | company_basic | Company registration info | P0 |
| 6 | stk_managers | stk_managers | Management info | P1 |
| 7 | new_share | new_share | IPO data | P1 |
| 8 | share_float | share_float | Floating share data | P0 |
| 9 | stk_holdernumber | stk_holdernumber | Shareholder count | P2 |
| 10 | stk_holdernumber (alternative) | - | Fallback for share_float | P2 |

## Field Design

### index_weight_current
- `id`: UUID (PK)
- `index_code`: string (index identifier)
- `trade_date`: date
- `con_code`: string (constituent code)
- `weight`: float
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (index_code, trade_date, con_code)

### etf_daily_basic_current
- `id`: UUID (PK)
- `ts_code`: string (ETF code)
- `trade_date`: date
- `unit_nav`: float (unit NAV)
- `unit_total`: float (total units)
- `total_mv`: float (total market value)
- `nav_mv`: float (NAV market value)
- `share`: float
- `adj_factor`: float
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code, trade_date)

### share_float_current
- `id`: UUID (PK)
- `ts_code`: string
- `float_date`: date
- `float_share`: float
- `total_share`: float
- `free_share`: float
- `float_mv`: float
- `total_mv`: float
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code, float_date)

### company_basic_current
- `id`: UUID (PK)
- `ts_code`: string
- `exchange`: string
- `chairman`: string
- `manager`: string
- `secretary`: string
- `registered_capital`: float
- `paid_in_capital`: float
- `setup_date`: date
- `province`: string
- `city`: string
- `introduction`: text
- `website`: string
- `email`: string
- `office`: string
- `employees`: integer
- `main_business`: text
- `business_scope`: text
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code)

### stk_managers_current
- `id`: UUID (PK)
- `ts_code`: string
- `name`: string
- `title`: string
- `gender`: string
- `edu`: string
- `nationality`: string
- `birthday`: string
- `begin_date`: date
- `end_date`: date
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code, name, begin_date)

### new_share_current
- `id`: UUID (PK)
- `ts_code`: string
- `name`: string
- `ipo_date`: date
- `issue_date`: date
- `issue_price`: float
- `amount`: float
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code)

### stk_holdernumber_current
- `id`: UUID (PK)
- `ts_code`: string
- `end_date`: date
- `holder_num`: integer
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code, end_date)

### name_change_current
- `id`: UUID (PK)
- `ts_code`: string
- `name`: string
- `start_date`: date
- `end_date`: date
- `version_id`: UUID
- `created_at`: timestamp
- `updated_at`: timestamp

**Unique constraint**: (ts_code, start_date)

## Raw/Canonical/History Design

### Raw Layer (lowfreq_raw_fetch)
- Stores original Tushare API response payload
- Includes: run_id, source_name, dataset_name, request_params_json, fetched_at_utc, raw_payload_json, record_count, watermark, status

### Canonical Current
- Uses upsert with version_id tracking
- Each record tracks which version it belongs to
- Active version has version_id = None (CURRENT_VERSION_ID_SENTINEL)

### History Layer
- Each fetch creates a new version in dataset_versions
- All records are copied to *_history tables keyed by version_id
- Supports time-travel queries via version_id

## Daemon Integration

### Schedule Windows
- daily_light: 22:45 (Shanghai timezone)
- daily_light_fallback: 01:30 (Shanghai timezone)
- weekly_deep: 10:00 Friday (Shanghai timezone)

### Non-Trading Day Execution
All datasets can run on non-trading days (slow variables are not T+1 dependent).

### Groups
- daily_light: All asset datasets
- weekly_deep: All asset datasets

## Acceptance Criteria

1. **Migration**: All tables created in schema ifa2
2. **Ingest**: Tushare adaptor fetches all datasets successfully
3. **Persistence**: raw -> canonical current -> history flow
4. **Versioning**: dataset_versions grows on each ingest
5. **Daemon**: daily_light and weekly_deep include asset datasets
6. **Tests**: Integration tests verify flow
7. **No Token Leakage**: .env not committed

## Implementation Files

- `alembic/versions/010_lowfreq_asset.py` - Migration
- `src/ifa_data_platform/lowfreq/canonical_persistence.py` - Current classes
- `src/ifa_data_platform/lowfreq/version_persistence.py` - History classes
- `src/ifa_data_platform/lowfreq/adaptors/tushare.py` - Fetch methods
- `src/ifa_data_platform/lowfreq/daemon_config.py` - Daemon config