# Dedupe and Idempotency Notes

This repo now treats the affected write paths as **idempotent by business identity**, not append-only by run/version.

## Midfreq history

- Path: `src/ifa_data_platform/midfreq/runner.py`
- Behavior: current→history copy now inserts a new history row **only when the business key is new or the material payload changed**.
- Effect: repeated real-runs with unchanged upstream data do **not** grow `*_history` tables anymore.

## Highfreq derived working tables

- Path: `src/ifa_data_platform/highfreq/derived_signals.py`
- Behavior: derived working tables are rebuilt as a **replace-snapshot**, not append-only.
- Effect: rerunning derived-state build refreshes the working snapshot and prevents cumulative duplicate growth.

## Lowfreq `news_history`

- Path: `src/ifa_data_platform/lowfreq/version_persistence.py`
- Behavior: exact duplicate news rows are suppressed across versions using null-safe field comparison on the stored payload columns.
- Effect: repeated real-runs with identical news payloads do **not** append duplicate history rows; materially changed news records still land.

## Operator expectation

For reruns against unchanged source data:

- `midfreq *_history` growth should be `0`
- `highfreq *_working` row counts should stay flat after the first successful rebuild
- `lowfreq news_history` growth should be `0`

If counts keep growing on identical reruns, treat that as a regression in write-path idempotency.
