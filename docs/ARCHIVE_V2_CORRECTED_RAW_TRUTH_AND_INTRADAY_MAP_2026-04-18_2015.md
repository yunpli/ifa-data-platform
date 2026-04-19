# Archive V2 Corrected Raw-Truth and Intraday Family Map

Generated: 2026-04-18 20:15 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Purpose

This document freezes the corrected upstream/raw-truth direction before the next Archive V2 implementation/refactor batch.

It applies the now-accepted principles:

1. **raw truth first, derive later**
2. current C-class highfreq-derived families must be split into:
   - families that can move toward raw-first / derive-later now
   - families that still need temporary derived retention because raw archive coverage is not complete yet
3. true source-side intraday families remain valid Archive V2 families
4. **ETF intraday is now explicitly included in the valid/default model**
5. proxy pseudo-intraday stays out of the valid raw archive family set unless a true source-side path is proven

---

## 2. Corrected intraday family model

## 2.1 Valid true source-side intraday family groups
The following family groups are now treated as valid Archive V2 intraday families because true source-side historical intraday truth exists:

- **equity** → source path: `stk_mins`
- **ETF** → source path: `stk_mins`
- **index** → source path: `idx_mins`
- **futures** → source path: `ft_mins`
- **commodity** → source path: `ft_mins`
- **precious_metal** → source path: `ft_mins`

### Practical Archive V2 interpretation
- These are valid real families in the Archive V2 roadmap.
- They are **not pseudo**.
- They should not be conflated with proxy/sector pseudo-intraday paths.

## 2.2 Default-active vs default-off rule
### Default-enabled in model
- `etf_1m`
- `etf_15m`
- `etf_60m`

ETF intraday is now explicitly included in the **default model**.

### Valid but still default-off unless explicitly enabled
- `equity_1m / 15m / 60m`
- `index_1m / 15m / 60m`
- `futures_1m / 15m / 60m`
- `commodity_1m / 15m / 60m`
- `precious_metal_1m / 15m / 60m`

These remain valid future families, but they do not all have to be active in the normal production profile.

## 2.3 Proxy exclusion rule
Proxy/sector-style pseudo intraday families remain excluded from the valid raw archive family set unless a true source-side intraday path is proven.

That means:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

must stay outside the valid raw family set for now if their current path still depends on:
- `ths_daily`
- synthetic intraday timestamps
- any similar pseudo/synthetic conversion pattern

---

## 3. C-class family-by-family raw truth mapping

Families in scope:
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

The key question here is not “what live working table is used now?”
The key question is:

> what exact raw historical truth would Archive V2 need in order to reproduce the family later without archiving the derived object by default?

---

## 3.1 `highfreq_event_stream_daily`

### Current live/realtime path
- source-side inputs:
  - `major_news`
  - `anns_d`
- current highfreq path:
  - normalize into `highfreq_event_stream_working`
- Archive V2 current family:
  - archive `highfreq_event_stream_working` as `highfreq_event_stream_daily`

### Exact raw truth required to reproduce later
- historical news rows
- historical announcement rows
- event timestamps / metadata

### Is that raw truth already archived by Archive V2?
**Yes, effectively yes** if `highfreq_event_stream_daily` is treated as the raw-preserved event archive family itself.

### Should this move to raw-first / derive-later now?
**Yes.**
In practice it already is the raw-preserved family.

### Conclusion
- keep `highfreq_event_stream_daily`
- treat it as a default raw/event truth family, not as a higher-order derived signal artifact

---

## 3.2 `highfreq_limit_event_stream_daily`

### Current live/realtime path
Current builder uses:
- `highfreq_close_auction_working`
- stock intraday context
- builder-generated event transformation into `limit_event_proxy`
- output table: `highfreq_limit_event_stream_working`

### Exact raw truth required to reproduce later
At minimum:
- raw close-auction truth
- raw stock intraday truth for the relevant date/range
- the rule set that turns those raw inputs into limit-event objects

### Is that raw truth already archived by Archive V2?
**No.**
Current default Archive V2 truth does not yet preserve enough raw auction/intraday context to rebuild this later.

### Should this move to raw-first / derive-later now?
**No, not yet.**

### Conclusion
- keep temporarily as derived retention family
- later remove from default truth only after raw auction/intraday coverage is added

---

## 3.3 `highfreq_sector_breadth_daily`

### Current live/realtime path
Current builder uses:
- `highfreq_stock_1m_working`
- `highfreq_proxy_1m_working`
- `highfreq_close_auction_working`
- then computes breadth metrics and writes `highfreq_sector_breadth_working`

### Exact raw truth required to reproduce later
To reproduce breadth historically, Archive V2 needs:
- raw stock intraday truth
- raw sector/grouping truth
- raw close-auction or equivalent end-of-session context
- the breadth computation rule set

### Is that raw truth already archived by Archive V2?
**No.**
The required raw truth is still incomplete, especially:
- stock intraday raw is not default-covered
- close-auction raw is not default-covered
- proxy/grouping context is not yet trustworthy as true raw truth

### Should this move to raw-first / derive-later now?
**Not fully yet.**
The principle is correct, but the raw archive coverage is still insufficient.

### Conclusion
- keep temporarily as derived retention family
- later migrate to raw-first / derive-later when raw stock intraday + raw auction + trustworthy grouping context are archived

---

## 3.4 `highfreq_sector_heat_daily`

### Current live/realtime path
Current builder uses:
- current proxy/sector context from `highfreq_proxy_1m_working`
- builder-owned heat metric computation
- output: `highfreq_sector_heat_working`

### Exact raw truth required to reproduce later
- trustworthy raw sector/proxy historical truth
- potentially stock/market context needed by heat rule set
- the heat metric rule set itself

### Is that raw truth already archived by Archive V2?
**No.**
The critical issue is that proxy raw truth is still not proven as a valid true intraday family.

### Should this move to raw-first / derive-later now?
**No, not yet.**

### Conclusion
- keep temporarily as derived retention family
- later reconsider after proxy/sector raw truth is clarified or replaced with a trustworthy raw grouping family

---

## 3.5 `highfreq_leader_candidate_daily`

### Current live/realtime path
Current builder uses:
- `highfreq_stock_1m_working`
- builder-owned candidate scoring / confirmation / continuation logic
- output: `highfreq_leader_candidate_working`

### Exact raw truth required to reproduce later
- raw stock intraday truth
- the leader-candidate scoring rule set

### Is that raw truth already archived by Archive V2?
**No.**
Archive V2 default truth does not yet preserve stock intraday raw by default.

### Should this move to raw-first / derive-later now?
**Not yet.**
The eventual principle is correct, but raw coverage is still insufficient.

### Conclusion
- keep temporarily as derived retention family
- later migrate after stock intraday raw archive support is added

---

## 3.6 `highfreq_intraday_signal_state_daily`

### Current live/realtime path
Current builder uses:
- `highfreq_stock_1m_working`
- `highfreq_proxy_1m_working`
- `highfreq_close_auction_working`
- builder-owned market-state logic
- output: `highfreq_intraday_signal_state_working`

### Exact raw truth required to reproduce later
- raw stock intraday truth
- raw auction/end-of-session truth
- trustworthy sector/proxy context or replacement grouping truth
- the signal-state rule engine

### Is that raw truth already archived by Archive V2?
**No.**

### Should this move to raw-first / derive-later now?
**Not yet.**

### Conclusion
- keep temporarily as derived retention family
- later move to raw-first / derive-later only when raw coverage and rule reproducibility are both in place

---

## 4. Which C-class families should move to raw-first / derive-later now?

### Move now / already essentially raw-first
- `highfreq_event_stream_daily`

Reason:
- it already behaves as a raw-preserved event family over direct source-side event inputs

### Still need temporary derived retention
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

Reason:
- Archive V2 default truth still does not preserve all raw historical ingredients needed to rebuild them later

---

## 5. Corrected intraday family map

## 5.1 Equity intraday
- families:
  - `equity_1m`
  - `equity_15m`
  - `equity_60m`
- true source-side raw endpoint:
  - `stk_mins`
- corrected status:
  - valid Archive V2 family group
  - default-off unless explicitly enabled

## 5.2 ETF intraday
- families:
  - `etf_1m`
  - `etf_15m`
  - `etf_60m`
- true source-side raw endpoint:
  - `stk_mins`
- corrected status:
  - valid Archive V2 family group
  - **included in default model**
  - correct implementation later should use direct ETF `ts_code` minute pull

## 5.3 Index intraday
- families:
  - `index_1m`
  - `index_15m`
  - `index_60m`
- true source-side raw endpoint:
  - `idx_mins`
- corrected status:
  - valid Archive V2 family group
  - default-off unless explicitly enabled

## 5.4 Futures intraday
- families:
  - `futures_1m`
  - `futures_15m`
  - `futures_60m`
- true source-side raw endpoint:
  - `ft_mins`
- corrected status:
  - valid Archive V2 family group
  - default-off unless explicitly enabled

## 5.5 Commodity intraday
- families:
  - `commodity_1m`
  - `commodity_15m`
  - `commodity_60m`
- true source-side raw endpoint:
  - `ft_mins`
- corrected status:
  - valid Archive V2 family group
  - default-off unless explicitly enabled

## 5.6 Precious metal intraday
- families:
  - `precious_metal_1m`
  - `precious_metal_15m`
  - `precious_metal_60m`
- true source-side raw endpoint:
  - `ft_mins`
- corrected status:
  - valid Archive V2 family group
  - default-off unless explicitly enabled

---

## 6. Explicit ETF intraday inclusion

This is now an explicit rule:

- `etf_1m`
- `etf_15m`
- `etf_60m`

must be treated as valid Archive V2 roadmap families.

### Important nuance
ETF intraday is now different from the previous “ETF unresolved” state.
That older uncertainty is closed.

The correct position is now:
- source truth exists
- repo later needs implementation
- Archive V2 should support ETF intraday
- ETF intraday is part of the corrected default model conceptually

---

## 7. Explicit proxy intraday exclusion

Proxy/sector-style intraday families remain excluded from the valid raw archive family set unless a true source-side intraday path is proven.

Current exclusion applies to:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

Reason:
- current path still depends on `ths_daily`
- current rows use synthetic intraday timestamps
- this is not valid true raw intraday archive truth

So proxy intraday must remain separated from:
- equity intraday
- ETF intraday
- index intraday
- futures intraday
- commodity intraday
- precious metal intraday

---

## 8. Truthful final judgment

### C-class judgment
The corrected principle is now clear:
- do **not** keep derived objects as default archive truth if their raw truth can be archived directly
- but only `highfreq_event_stream_daily` is currently close enough to that state
- the other current C-class families still need temporary derived retention until raw archive coverage is added

### Intraday judgment
The corrected intraday family map is now:
- valid real raw families:
  - equity / ETF / index / futures / commodity / precious_metal intraday
- excluded pseudo family:
  - proxy intraday unless true source path is proven

### Practical implication for the next refactor
The next Archive V2 refactor should:
1. keep `highfreq_event_stream_daily` as a raw-preserved default family
2. treat the other current C-class families as temporary derived retention only
3. add/plan proper source-first intraday support for:
   - equity
   - ETF
   - index
   - futures
   - commodity
   - precious_metal
4. keep proxy intraday outside the valid raw family set until proven otherwise
