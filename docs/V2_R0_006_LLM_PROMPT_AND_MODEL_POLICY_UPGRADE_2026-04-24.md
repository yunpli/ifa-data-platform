# V2-R0-006 LLM Prompt 与模型策略升级（2026-04-24）

## 1. Current LLM call path

### 1.1 FSJ main（early / mid / late）
- entry: `src/ifa_data_platform/fsj/{early_main_producer.py,mid_main_producer.py,late_main_producer.py}`
- assist layer: `src/ifa_data_platform/fsj/llm_assist.py`
- formal gateway path: `ifa-business-layer/scripts/ifa_llm_cli.py`
- actual invocation shape:
  1. deterministic producer computes `contract_mode / completeness_label / degrade_reason`
  2. slot-specific `evidence_packet` is built in `llm_assist.py`
  3. `BusinessRepo*LLMClient` shells into business-layer CLI
  4. business-layer `LLMService` resolves provider/model from `config/llm/models.yaml`
  5. parsed JSON is re-validated by slot parser before any text fields are adopted

### 1.2 Support（macro / commodities / ai_tech）
- entry: `ifa-business-layer/ifa_business_layer/support/{macro.py,commodities.py,ai_tech.py}`
- invocation owner: support producer -> `LLMService.invoke(...)`
- formal gateway path: still the business-layer utility/service stack (`scripts/ifa_llm_cli.py` + `ifa_business_layer/llm/service.py`)
- current runtime behavior:
  - LLM output must match strict support bundle JSON shape
  - invalid / non-JSON output falls back to deterministic rule assembly (`assembly_mode=hybrid` or `rule_assembled`)

## 2. Stronger target model strategy and fallback policy

Implemented policy source:
- `ifa-business-layer/config/llm/models.yaml` -> `fsj_assist_policy`

Policy:
- `policy_version = fsj_assist_model_policy_v1`
- `strategy_name = fsj_main_and_support_strict_gateway`
- primary: `grok41_expert`
- fallbacks: `grok41_thinking -> gemini31_pro_jmr`
- if all configured attempts fail: `deterministic_degrade`

Why this shape:
- keep all formal business LLM traffic on the business-layer gateway
- make the model chain explicit in config instead of hidden in scattered code
- prefer stronger synthesis quality first, but preserve already-working fallback paths
- keep failure outcome auditable via `policy_version / strategy_name / attempted_model_chain / prior_failures / operator_tag`

## 3. Boundary protections for evidence / time-window / schema

### 3.1 Evidence boundary
- producer-owned evidence packet only
- audit stores `input_digest`
- `evidence_binding = input_digest_and_evidence_packet_only`
- `evidence_owner = deterministic_data_platform_inputs`

### 3.2 Time-window boundary
- early: `candidate_only`
- mid: `intraday_working`
- late: `same_day_close`
- audit field: `time_window_guard`
- slot policy forbids rewriting cross-window truth and forbids upgrading degrade posture

### 3.3 Schema boundary
- `required_json_schema` remains slot-specific
- parser validation remains mandatory before any text adoption
- audit field: `schema_enforcement = slot_specific_required_json_schema_plus_parser_validation`
- only validated text fields may be adopted; deterministic owner fields remain outside model authority

## 4. Concrete files changed

### data-platform
- `src/ifa_data_platform/fsj/llm_assist.py`
- `tests/unit/test_fsj_early_llm_assist.py`
- `docs/V2_R0_006_LLM_PROMPT_AND_MODEL_POLICY_UPGRADE_2026-04-24.md`
- `docs/IFA_Execution_Progress_Monitor.md`

### business-layer
- `config/llm/models.yaml`
- `ifa_business_layer/support/macro.py`
- `ifa_business_layer/support/commodities.py`
- `ifa_business_layer/support/ai_tech.py`

## 5. Validation executed
- `python -m pytest -q tests/unit/test_fsj_early_llm_assist.py`
- `python -m py_compile src/ifa_data_platform/fsj/llm_assist.py`
- `python -m pytest -q tests/unit/test_macro_support_producer.py tests/unit/test_commodities_support_producer.py tests/unit/test_ai_tech_support_producer.py`

## 6. Evidence paths
- `src/ifa_data_platform/fsj/llm_assist.py`
- `ifa-business-layer/config/llm/models.yaml`
- `ifa-business-layer/ifa_business_layer/support/macro.py`
- `ifa-business-layer/ifa_business_layer/support/commodities.py`
- `ifa-business-layer/ifa_business_layer/support/ai_tech.py`
- `tests/unit/test_fsj_early_llm_assist.py`
- `docs/V2_R0_006_LLM_PROMPT_AND_MODEL_POLICY_UPGRADE_2026-04-24.md`

## 7. Acceptance readout
- business-layer gateway remained the only formal business LLM path: yes
- deterministic boundaries weakened: no
- free-form model sprawl introduced in data-platform: no
- model strategy + fallback explicit + auditable: yes
- strict evidence / time-window / schema protections preserved and surfaced: yes

Conclusion: V2-R0-006 acceptance met for smallest safe closure.
