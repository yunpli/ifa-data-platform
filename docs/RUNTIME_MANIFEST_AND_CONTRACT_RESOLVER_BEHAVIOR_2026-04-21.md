# Runtime manifest + contract resolver behavior update (2026-04-21)

## What changed

### 1) Canonical futures aliases now resolve to the nearest still-active live contract

Before this fix, aliases such as `AU0` / `SC0` were resolved by sorting `fut_basic` candidates from oldest to newest, which could map them to long-expired historical contracts like `AU0806.SHF` / `SC1809.INE`.

Now the resolver:
- filters to contracts whose `delist_date >= today`
- chooses the nearest active contract by earliest upcoming `delist_date`

Operational meaning:
- canonical aliases now point to a currently live contract instead of a historical one
- explicit contract `ts_code` inputs like `AU2605.SHF` still pass through unchanged

### 2) Lowfreq/midfreq runtime manifests now collapse overlapping `focus` + `key_focus` duplicates

Before this fix, the target manifest could emit duplicate lowfreq/midfreq entries for the same symbol when the same owner/list family contained both `focus` and `key_focus` coverage.

Now the manifest builder collapses duplicate `dedupe_key` entries and keeps the stronger record, preferring:
1. `key_focus` over `focus`
2. lower numeric priority when needed

Operational meaning:
- `owner=default` lowfreq/midfreq manifests no longer double-count overlapping targets such as `AU0`, `SC0`, or overlapping stock symbols
- when both scopes exist, `key_focus` wins for the retained manifest item

## Validation path

Use non-daemon checks only:
- `pytest tests/unit/test_contract_resolver.py tests/unit/test_target_manifest.py -q`
- targeted manifest inspection via `build_target_manifest(...)` or `scripts/runtime_manifest_cli.py manifest`
