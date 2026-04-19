# Archive V2 Raw-Truth Clarification Before Refactor

Generated: 2026-04-18 19:48 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Summary judgment

This batch clarifies the upstream/raw-truth model that should guide the next Archive V2 refactor.

### Core principle confirmed
For current C-class highfreq-derived families, the right default principle is:

> **archive raw truth first, derive later**

not:

> archive the derived object by default

However, this principle only works if Archive V2 is actually archiving the raw historical truth needed to reproduce the derived object later.

### Current state of Archive V2 against that principle
Current Archive V2 is only partially aligned:
- it **does** already archive one important raw-ish highfreq family: `highfreq_event_stream_daily`
- but for several other current C-class derived families, the raw truth needed to rebuild them later is **not yet fully archived by default**
- therefore some derived families still need to stay in the model **for now**, until the raw archive coverage is expanded

### Intraday clarification confirmed
For non-proxy intraday families, true source-side intraday truth exists in repo code and should remain in the Archive V2 roadmap:
- `equity 1m / 15m / 60m`
- `index 1m / 15m / 60m`
- `futures 1m / 15m / 60m`
- `commodity 1m / 15m / 60m`
- `precious_metal 1m / 15m / 60m`

Important explicit conclusion:

> These families should remain **supported later in Archive V2 when explicitly enabled**, even if they are **OFF by default in the normal production profile right now**.

Proxy/sector-style intraday families are different:
- `proxy_1m / 15m / 60m` are still backed by a pseudo/synthetic path, not proven true intraday source truth
- they should **not yet be treated as valid raw archive families**

---

## 2. Part A — C-class raw-first / derive-later clarification

Families examined:
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

---

## 2.1 `highfreq_event_stream_daily`

### Exact upstream raw truth needed
Raw truth needed to reproduce this family later:
- source-side `major_news`
- source-side `anns_d`
- normalized event timestamps / metadata fields

### Current chain
```text
major_news + anns_d
  -> highfreq adaptor event-stream normalization
  -> highfreq_event_stream_working
  -> Archive V2 highfreq_event_stream_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**Mostly yes.**

Why:
- this family is already close to a raw preserved event family rather than a higher-order derived signal object
- Archive V2 archives `highfreq_event_stream_working`, which is the normalized event stream directly built from raw source events

### What raw family is still missing, if any?
No major additional raw family is strictly required if this normalized event stream is accepted as the raw archive truth layer.

### Should the current derived-family archive object remain?
**No, as a special derived object it is not needed beyond this raw event archive layer.**
The archived event stream itself is the raw-preservation layer.

### Does current derivation depend on live/current working tables only?
It depends on a local normalized working table, but that table is built directly from source events and is not a higher-order strategy derivation.

### Classification
**A. raw truth can be archived directly; derived archive object is not needed by default**

### Practical implication
Keep `highfreq_event_stream_daily` as a default Archive V2 truth family.
It is effectively the raw archive-preservation family for highfreq events.

---

## 2.2 `highfreq_limit_event_stream_daily`

### Exact upstream raw truth needed
To reproduce this family later, the current builder uses:
- `highfreq_close_auction_working`
- indirectly stock intraday context from `highfreq_stock_1m_working`
- current builder rule that transforms rows into `limit_event_proxy` events

### Current chain
```text
stk_auction_c + stock intraday context
  -> highfreq_close_auction_working (+ stock_1m context)
  -> DerivedSignalBuilder creates synthetic limit_event_proxy rows
  -> highfreq_limit_event_stream_working
  -> Archive V2 highfreq_limit_event_stream_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**No.**

Current Archive V2 default profile does **not** archive:
- `highfreq_close_auction_working` as a raw daily archive family
- `highfreq_stock_1m_working` as a raw archive family in default daily production scope

### What raw family is still missing?
At minimum:
- a raw close-auction archive family
- likely stock intraday raw archive coverage for the same day/range if the event derivation depends on broader intraday context

### Should the current derived-family archive object remain?
**Yes, for now.**
Because Archive V2 does not yet preserve enough raw truth by default to rebuild it later safely.

### Does current derivation depend on live/current working tables only?
Yes — current builder uses live/working tables, not an explicitly archived historical raw family set.

### Classification
**B. raw truth is not yet fully covered; derived archive object still needed for now**

### Practical implication
Keep `highfreq_limit_event_stream_daily` for now.
In the later refactor, it should only be removable after raw close-auction / raw intraday coverage is archived adequately.

---

## 2.3 `highfreq_sector_breadth_daily`

### Exact upstream raw truth needed
To reproduce breadth later, current builder effectively needs:
- stock intraday raw truth (`highfreq_stock_1m_working` today; source is `stk_mins`)
- proxy/sector grouping context (`highfreq_proxy_1m_working` today)
- close-auction or related market-state context (`highfreq_close_auction_working` today)

### Current chain
```text
stk_mins + proxy context + close-auction context
  -> highfreq_stock_1m_working
  -> highfreq_proxy_1m_working
  -> highfreq_close_auction_working
  -> DerivedSignalBuilder computes up_count/down_count/strong_count/limit_up_count/spread_ratio
  -> highfreq_sector_breadth_working
  -> Archive V2 highfreq_sector_breadth_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**No.**

Missing from default Archive V2 truth model today:
- stock intraday raw archive by default
- close-auction raw archive family
- trustworthy sector/proxy raw grouping family

### What raw family is still missing?
At minimum:
- a raw stock intraday archive family for the relevant time resolution
- a raw close-auction archive family
- a trustworthy sector/proxy grouping source that is historically reproducible

### Should the current derived-family archive object remain?
**Yes, for now.**
Because the raw truth required to re-derive it later is not yet fully retained by Archive V2’s default model.

### Does current derivation depend on live/current working tables only?
Yes, currently it depends on working tables built by highfreq live/realtime collection.

### Classification
**B. raw truth is not yet fully covered; derived archive object still needed for now**

### Practical implication
Do **not** remove `highfreq_sector_breadth_daily` from the model yet.
Later, once raw stock intraday + raw close-auction + trustworthy grouping context are archived, this family can move to raw-first / derive-later.

---

## 2.4 `highfreq_sector_heat_daily`

### Exact upstream raw truth needed
Current builder uses:
- `highfreq_proxy_1m_working` as proxy context
- plus broader stock/auction context indirectly available in the same builder pass

### Current chain
```text
proxy context (+ builder context)
  -> highfreq_proxy_1m_working
  -> DerivedSignalBuilder computes heat_score from proxy row
  -> highfreq_sector_heat_working
  -> Archive V2 highfreq_sector_heat_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**No.**
And even more importantly, the proxy upstream is not currently proven as true intraday raw truth.

### What raw family is still missing?
- a trustworthy raw sector/proxy historical source family

### Should the current derived-family archive object remain?
**Yes, for now.**
Because the raw truth / grouping truth underneath is not clean enough yet.

### Does current derivation depend on live/current working tables only?
Yes — current metric is builder-owned and uses current proxy working rows.

### Classification
**B. raw truth is not yet fully covered; derived archive object still needed for now**

### Practical implication
Keep for now.
This family should only move to raw-first / derive-later after proxy/sector raw truth is clarified and archived properly.

---

## 2.5 `highfreq_leader_candidate_daily`

### Exact upstream raw truth needed
Current builder effectively needs:
- stock intraday raw truth (`highfreq_stock_1m_working` today)
- the candidate-scoring rule set

### Current chain
```text
stock intraday raw
  -> highfreq_stock_1m_working
  -> DerivedSignalBuilder computes candidate_score / confirmation_state / continuation_health
  -> highfreq_leader_candidate_working
  -> Archive V2 highfreq_leader_candidate_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**No.**
Archive V2 default profile does not currently preserve stock intraday raw truth by default.

### What raw family is still missing?
- stock intraday raw archive coverage for the relevant day/range

### Should the current derived-family archive object remain?
**Yes, for now.**
Without stock intraday raw archive coverage, the leader-candidate object cannot be reproducibly rebuilt later from Archive V2 default truth.

### Does current derivation depend on live/current working tables only?
Yes — current implementation depends on live/current working rows.

### Classification
**B. raw truth is not yet fully covered; derived archive object still needed for now**

### Practical implication
Keep for now; later it can move to raw-first / derive-later once stock intraday raw archive coverage is retained in Archive V2.

---

## 2.6 `highfreq_intraday_signal_state_daily`

### Exact upstream raw truth needed
Current builder uses:
- stock intraday raw truth (`highfreq_stock_1m_working`)
- proxy context (`highfreq_proxy_1m_working`)
- close-auction context (`highfreq_close_auction_working`)
- local state-rule logic

### Current chain
```text
stock intraday + proxy context + close-auction context
  -> working tables
  -> DerivedSignalBuilder computes emotion_stage / validation_state / risk_opportunity_state / turnover_progress / amount_progress
  -> highfreq_intraday_signal_state_working
  -> Archive V2 highfreq_intraday_signal_state_daily
```

### Is the raw truth already fully covered by Archive V2 today?
**No.**
Missing by default:
- stock intraday raw archive coverage
- close-auction raw archive coverage
- trustworthy proxy raw path

### What raw family is still missing?
- stock intraday raw family
- close-auction raw family
- trustworthy proxy/sector context family

### Should the current derived-family archive object remain?
**Yes, for now.**
Because Archive V2 default truth is not sufficient yet to reconstruct this state reliably later.

### Does current derivation depend on live/current working tables only?
Yes.

### Classification
**B. raw truth is not yet fully covered; derived archive object still needed for now**

### Practical implication
Keep for now. Later removable from default model only after raw truth coverage is expanded enough.

---

## 3. Part A conclusion — C-class raw-first / derive-later classification

| Family | Raw truth already fully covered by Archive V2 default truth today? | Classification | Practical implication |
|---|---:|---|---|
| `highfreq_event_stream_daily` | Yes / mostly yes | **A** | Keep as raw event archive family; derived object not separately needed |
| `highfreq_limit_event_stream_daily` | No | **B** | Keep for now |
| `highfreq_sector_breadth_daily` | No | **B** | Keep for now |
| `highfreq_sector_heat_daily` | No | **B** | Keep for now |
| `highfreq_leader_candidate_daily` | No | **B** | Keep for now |
| `highfreq_intraday_signal_state_daily` | No | **B** | Keep for now |

### Practical C-class conclusion
- `highfreq_event_stream_daily` already fits the raw-first principle closely enough to remain a default Archive V2 truth family.
- The other current C-class families should **not** yet be removed from the model, because Archive V2 default raw truth is still insufficient to rebuild them later.
- The next refactor should therefore separate:
  - **raw preserved families**
  - **temporary derived defaults kept only until raw coverage is complete**

---

## 4. Part B — intraday source-side clarification

The question here is not “should these be default-active now?”
The question is:

> If later we explicitly want to archive 1m / 15m / 60m for selected dates or ranges, what is the correct true source-side raw path?

---

## 4.1 Equity intraday

Families:
- `equity_1m`
- `equity_15m`
- `equity_60m`

### Exact source-side endpoint/path
- Tushare `stk_mins`
- frequencies evidenced in repo: `1min`, `15min`
- 60m family is also part of truthful archive-side intraday closure path

### Does current repo prove that path works?
**Yes.**
Repo evidence:
- `src/ifa_data_platform/archive/stock_minute_archiver.py`
- `src/ifa_data_platform/archive/stock_15min_archiver.py`
- both directly call `stk_mins`

### Should Archive V2 later support it when explicitly enabled?
**Yes.**

### Should it remain OFF by default in normal production profile?
**Yes.**

### Is current implementation using the correct source path or a pseudo/synthetic one?
Current Archive V2 implementation is **not source-first yet**; it uses retained local tables (`stock_minute_history`, `stock_15min_history`, `stock_60min_history`).
So the later implementation should be corrected toward direct source-side raw pull.

### Classification
**B. true source-side intraday exists, but current implementation path is wrong and should later be corrected**

### Practical implication
- default off
- later implementable
- keep in Archive V2 roadmap

---

## 4.2 Index intraday

Families:
- `index_1m`
- `index_15m`
- `index_60m`

### Exact source-side endpoint/path
- practical source path evidenced in repo: `stk_mins(..., freq='1min')`
- 15m / 60m derivable from true 1m raw truth

### Does current repo prove that path works?
**Yes, operationally.**
Repo evidence:
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- `fetch_index_1m(...)` directly calls `stk_mins(..., freq='1min')`

### Should Archive V2 later support it when explicitly enabled?
**Yes.**

### Should it remain OFF by default in normal production profile?
**Yes.**

### Is current implementation using the correct source path or a pseudo/synthetic one?
Current Archive V2 uses `highfreq_index_1m_working` as upstream, so it is **not yet source-first**.
But the source truth path itself is real.

### Classification
**B. true source-side intraday exists, but current implementation path is wrong and should later be corrected**

### Practical implication
- default off
- later implementable
- keep in Archive V2 roadmap

---

## 4.3 ETF intraday

### Exact source-side endpoint/path
No true ETF intraday source path is proven in current repo for Archive V2 purposes.

### Does current repo prove a working raw intraday path?
**No.**
Only ETF daily is clearly proven (`fund_daily`).

### Should Archive V2 later support it when explicitly enabled?
Not enough source evidence yet.

### Should it remain OFF by default?
Yes.

### Is current implementation using the correct source path or a pseudo/synthetic one?
No first-class ETF intraday Archive V2 family exists now.

### Classification
**D. unresolved / not enough source evidence yet**

### Practical implication
- not yet valid even as optional until source truth is proven cleanly

---

## 4.4 Futures intraday

Families:
- `futures_1m`
- `futures_15m`
- `futures_60m`

### Exact source-side endpoint/path
- Tushare `ft_mins`

### Does current repo prove that path works?
**Yes.**
Repo evidence:
- `src/ifa_data_platform/archive/futures_intraday_archiver.py`
- direct `ft_mins` use

### Should Archive V2 later support it when explicitly enabled?
**Yes.**

### Should it remain OFF by default in normal production profile?
**Yes.**

### Is current implementation using the correct source path or a pseudo/synthetic one?
Current Archive V2 uses retained local tables (`futures_minute_history`, `futures_15min_history`, `futures_60min_history`), so the current path is **not source-first yet**.

### Classification
**B. true source-side intraday exists, but current implementation path is wrong and should later be corrected**

### Practical implication
- default off
- later implementable
- keep in roadmap

---

## 4.5 Commodity intraday

Families:
- `commodity_1m`
- `commodity_15m`
- `commodity_60m`

### Exact source-side endpoint/path
- Tushare `ft_mins`

### Does current repo prove that path works?
**Yes.**
Repo evidence:
- commodity intraday is handled through the futures-family intraday archiver path

### Should Archive V2 later support it when explicitly enabled?
**Yes.**

### Should it remain OFF by default in normal production profile?
**Yes.**

### Is current implementation using the correct source path or a pseudo/synthetic one?
Current Archive V2 path is not source-first yet; it uses retained local history tables.

### Classification
**B. true source-side intraday exists, but current implementation path is wrong and should later be corrected**

### Practical implication
- default off
- later implementable
- keep in roadmap

---

## 4.6 Precious metal intraday

Families:
- `precious_metal_1m`
- `precious_metal_15m`
- `precious_metal_60m`

### Exact source-side endpoint/path
- Tushare `ft_mins`

### Does current repo prove that path works?
**Yes.**
Repo evidence:
- precious-metal intraday is handled through the futures-family intraday archiver path

### Should Archive V2 later support it when explicitly enabled?
**Yes.**

### Should it remain OFF by default in normal production profile?
**Yes.**

### Is current implementation using the correct source path or a pseudo/synthetic one?
Current Archive V2 path is retained-history-first, not source-first.

### Classification
**B. true source-side intraday exists, but current implementation path is wrong and should later be corrected**

### Practical implication
- default off
- later implementable
- keep in roadmap

---

## 5. Proxy-specific clarification

Families:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

### Is there a true source-side proxy intraday path?
**Not proven in current repo.**

### What current path exists?
Current repo path in `highfreq/adaptor_tushare.py`:
- `fetch_proxy_1m()` calls `ths_daily(ts_code='885728.TI', trade_date=...)`
- then stamps the row with synthetic `15:00:00`
- then writes it into `highfreq_proxy_1m_working`

### Truth judgment
This is **pseudo/synthetic**, not true intraday source truth.

### Classification
**C. current path is only pseudo/synthetic and should not be treated as true archive family yet**

### Practical implication
- not yet valid even as optional true intraday archive family
- do not conflate with equity/index/futures/commodity/precious-metal intraday truth

---

## 6. Part B conclusion — intraday family classification

| Family group | Classification | Practical implication |
|---|---|---|
| `equity_1m/15m/60m` | **B** | true source-side intraday exists; default off; later implementable; current retained-history-first path should be corrected |
| `index_1m/15m/60m` | **B** | true source-side intraday exists; default off; later implementable; current working-table-first path should be corrected |
| `futures_1m/15m/60m` | **B** | true source-side intraday exists; default off; later implementable |
| `commodity_1m/15m/60m` | **B** | true source-side intraday exists; default off; later implementable |
| `precious_metal_1m/15m/60m` | **B** | true source-side intraday exists; default off; later implementable |
| `ETF intraday` | **D** | unresolved / not enough source evidence yet |
| `proxy_1m/15m/60m` | **C** | current path pseudo/synthetic; not yet valid even as optional true intraday archive family |

---

## 7. Explicit practical Archive V2 conclusion

### What should be default Archive V2 truth
- core direct-source daily/final families
- raw-preserved event family `highfreq_event_stream_daily`
- other currently necessary derived highfreq daily families should stay for now **only where raw archive coverage is still insufficient**

### What should remain optional later-enable families
These should remain in the Archive V2 roadmap and be supported later when explicitly enabled by profile:
- `equity_1m / 15m / 60m`
- `index_1m / 15m / 60m`
- `futures_1m / 15m / 60m`
- `commodity_1m / 15m / 60m`
- `precious_metal_1m / 15m / 60m`

Important explicit statement:

> **Not default-active now does NOT mean never implemented.**  
> These true intraday families should remain supported in the overall Archive V2 roadmap for later explicit enablement.

### What should not yet be treated as valid archive families
- `proxy_1m / 15m / 60m` as true intraday archive families
- ETF intraday until a real source-side raw path is proven cleanly

---

## 8. Truthful final judgment

### Part A
The corrected principle is confirmed:
- for C-class families, the right end-state is generally **raw-first, derive-later**
- but today Archive V2 default truth does **not yet retain enough raw intraday/auction/proxy context** to safely drop most of the current derived highfreq families
- therefore only `highfreq_event_stream_daily` clearly behaves like a raw-preserved default family today
- the other C-class derived families should stay for now until raw coverage is expanded

### Part B
The intraday truth picture is now clean:
- non-proxy intraday families have real source-side truth in repo code and should remain later-enable Archive V2 families
- proxy intraday families are still pseudo/synthetic and should not yet be treated as valid true archive families
- ETF intraday remains unresolved in current repo truth

This is the upstream/raw-truth picture that should guide the next Archive V2 refactor.
