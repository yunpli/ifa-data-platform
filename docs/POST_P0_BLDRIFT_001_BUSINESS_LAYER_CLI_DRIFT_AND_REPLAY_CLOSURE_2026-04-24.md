# POST-P0-BLDRIFT-001 — business-layer CLI drift + replay/backfill semantic closure

Date: 2026-04-24
Owner: Lane B

## 1. Surface audit

### 1.1 Business-layer CLI import/runtime drift
Observed primary drift:
- `ifa-business-layer/scripts/ifa_llm_cli.py` failed when executed directly as a script unless `PYTHONPATH` was manually pre-seeded.
- Reproduced from both repo contexts before fix:
  - `python3 scripts/ifa_llm_cli.py --help` in `ifa-business-layer`
  - `python3 /Users/neoclaw/repos/ifa-business-layer/scripts/ifa_llm_cli.py --help` in `ifa-data-platform`
- Failure mode:
  - `ModuleNotFoundError: No module named 'ifa_business_layer'`

Impact:
- `ifa-data-platform/src/ifa_data_platform/fsj/llm_assist.py` shells into that CLI as the only formal business LLM path.
- When the script import path drifted, FSJ main LLM assist degraded in acceptance shell / wrapper runs even though the intended gateway path was correct.

### 1.2 Replay/backfill wrapper semantics still overstated at control surface
Observed wrapper-level semantic drift in `scripts/fsj_report_cli.py`:
- non-`realtime` modes (`replay`, `backfill-test`, `dry-run`) were exposed as first-class choices
- but the wrapper itself already noted there was no native downstream mode switch
- `morning-delivery` could still be requested together with non-realtime mode, which overstated control-surface semantics and looked more native than it actually was

## 2. Minimal implementation path

### 2.1 Repair business-layer CLI direct-execution contract
- Add repo-root self-bootstrap in `scripts/ifa_llm_cli.py` via `Path(__file__).resolve().parents[1]` inserted into `sys.path` before package imports.
- This keeps the business-layer gateway/CLI as the only formal business LLM path while removing the script-entry drift.

### 2.2 Tighten replay/backfill semantics at wrapper surface only
- Keep existing canonical wrapper shape; do not rewrite publish/orchestration chain.
- Add explicit `mode_contract` to wrapper output.
- Persist `fsj_report_cli_intent.json` into the isolated output root for operator/audit visibility.
- Reject `--main-flow morning-delivery` for non-realtime mode, because that path is a realtime delivery surface, not a true replay/backfill-native path.

## 3. Files changed

### business-layer
- `scripts/ifa_llm_cli.py`
- `tests/integration/llm/test_llm_cli_smoke.py`

### data-platform
- `scripts/fsj_report_cli.py`
- `tests/unit/test_fsj_report_cli_registry.py`
- `docs/POST_P0_BLDRIFT_001_BUSINESS_LAYER_CLI_DRIFT_AND_REPLAY_CLOSURE_2026-04-24.md`

## 4. Validations run

### business-layer CLI / import-path validation
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/integration/llm/test_llm_cli_smoke.py`
- `python3 scripts/ifa_llm_cli.py --help`
- `python3 /Users/neoclaw/repos/ifa-business-layer/scripts/ifa_llm_cli.py --help`
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python - <<'PY' ... _run_business_repo_llm(...) ... PY`
  - after fix, failure is now provider/env truth (`missing API key for provider 'jmr-oai'; expected env var JMR_API_KEY`) rather than import drift

### wrapper semantic closure validation
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python -m pytest -q tests/unit/test_fsj_report_cli_registry.py`
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode replay --output-profile customer --output-root artifacts/post_p0_bldrift_probe --report-run-id-prefix post-p0-bldrift`
- `/Users/neoclaw/repos/ifa-data-platform/.venv/bin/python scripts/fsj_report_cli.py generate --subject main --business-date 2026-04-23 --slot early --mode replay --main-flow morning-delivery --output-root artifacts/post_p0_bldrift_probe`
  - expected guard hit: `--main-flow morning-delivery is realtime-only; use publish flow for replay/backfill-test/dry-run`

## 5. Evidence paths

- `ifa-business-layer/scripts/ifa_llm_cli.py`
- `ifa-business-layer/tests/integration/llm/test_llm_cli_smoke.py`
- `ifa-data-platform/scripts/fsj_report_cli.py`
- `ifa-data-platform/tests/unit/test_fsj_report_cli_registry.py`
- `ifa-data-platform/docs/POST_P0_BLDRIFT_001_BUSINESS_LAYER_CLI_DRIFT_AND_REPLAY_CLOSURE_2026-04-24.md`
- `ifa-data-platform/artifacts/post_p0_bldrift_probe/main_early_2026-04-23_replay/fsj_report_cli_intent.json`

## 6. Residual gaps

- Canonical wrapper still does not create a true downstream native replay/backfill execution contract; non-realtime remains an explicit wrapper/operator-intent surface plus isolated output-root routing.
- This task intentionally did not rewrite main/support publish scripts into a new execution substrate.
- Live provider invocation still depends on valid env/config (for example `JMR_API_KEY`), which is correct and now truthfully surfaced.

## 7. Acceptance for bounded task

Bounded acceptance: **met**.

Why:
- the real business-layer CLI import/runtime drift causing acceptance-shell LLM degrade is repaired
- formal business LLM path remains `ifa-data-platform -> ifa-business-layer/scripts/ifa_llm_cli.py -> LLMService`
- wrapper/control-surface replay semantics are now more explicit and less misleading without broad chain rewrite
- no FCJ work, no provider-direct scatter, no broad collector/data-path refactor was introduced
