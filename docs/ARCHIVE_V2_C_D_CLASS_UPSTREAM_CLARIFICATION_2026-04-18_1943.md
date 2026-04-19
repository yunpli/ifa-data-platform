# Archive V2 Upstream Clarification — C-class Highfreq Derived Families and D-class Proxy/Intraday Re-check

Generated: 2026-04-18 19:43 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Scope of this clarification batch

This is a narrow clarification pass only.
It answers two questions before any larger Archive V2 refactor:

### Part A
For current **C-class highfreq-derived daily archive families**:
- where they actually come from
- what raw/source inputs feed them
- which code path derives them
- whether the local dependency is truly unavoidable
- what a source-first / derivation-inside-archive alternative would look like

### Part B
For current **D-class proxy/intraday families**:
- whether true source-side direct data actually exists
- whether these families should be considered implementable later when explicitly enabled
- whether current unresolved status should stay unresolved or be revised

This batch does **not** perform the broader refactor yet.

---

## 2. Executive summary

### Part A — C-class highfreq-derived families
Truthfully, these families are local today because they are produced by a **specific derived-signal builder** in `src/ifa_data_platform/highfreq/derived_signals.py`, not because a local dependency is always conceptually unavoidable.

The actual chain is:

```text
source-side raw pulls
  -> highfreq working tables
  -> DerivedSignalBuilder logic
  -> derived working tables
  -> Archive V2 daily archive families
```

Important clarification:
- some of these local dependencies are **structurally derived products** and are therefore reasonable C-class families today
- but the current derivation logic is also **simplified / repo-local / builder-specific**, which means the final dependency is not automatically “unavoidable forever”
- if Archive V2 is allowed to re-run the same derivation logic internally from source-aligned raw inputs, some of these could become source-first-plus-internal-derivation later

### Part B — D-class proxy/intraday families
Re-check result:
- `proxy_1m / 15m / 60m` should **remain unresolved** today
- true source-side proxy intraday truth is **not proven** in the current repo
- current `highfreq_proxy_1m_working` is created from `ths_daily(...)` with a synthetic `15:00:00` timestamp, so it is **not true 1m source truth**

For the broader intraday families:
- `equity 1m/15m/60m`: true source-side direct path **does exist** via `stk_mins`
- `index 1m/15m/60m`: source-side direct path effectively exists through the repo’s current highfreq `fetch_index_1m(...)` use of `stk_mins`, with 15m/60m derivable from 1m
- `futures/commodity/precious_metal 1m/15m/60m`: true source-side direct path **does exist** via `ft_mins`

So these non-proxy intraday families should be treated as **implementable later in Archive V2 when explicitly enabled**, even though they are not part of the default production profile.

---

## 3. Part A — current C-class highfreq-derived daily families

Families in scope:
- `highfreq_event_stream_daily`
- `highfreq_limit_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

---

## 3.1 `highfreq_event_stream_daily`

### Current upstream raw/source inputs
Primary raw/source ingredients come from highfreq source pulls:
- `major_news`
- `anns_d`

These are fetched in highfreq adaptor event-stream logic and then persisted into:
- `ifa2.highfreq_event_stream_working`

### Code path
Source ingestion path:
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
  - `fetch_event_stream(...)`
  - `persist_event_stream(...)`

Archive V2 path:
- `src/ifa_data_platform/archive_v2/runner.py`
  - family kind: `event_daily`
  - source table: `highfreq_event_stream_working`
  - destination: `ifa_archive_highfreq_event_stream_daily`

### Transformation / derivation logic
For this family, the main transformation happens **before Archive V2**:
- source events are normalized into a unified event stream object
- that normalized event stream is persisted in `highfreq_event_stream_working`
- Archive V2 then archives event rows by business date using event semantics

### Why current Archive V2 depends on local working state
Because Archive V2 is not currently rebuilding the event-unification step itself.
It consumes the already-unified event stream table.

### Is that dependency truly unavoidable?
**Not strictly unavoidable.**

### Possible source-first / derivation-inside-archive alternative
Archive V2 could directly pull:
- `major_news`
- `anns_d`
for the requested date window, then run the same event normalization logic internally before archiving.

### Current truth judgment
- local dependency is currently practical
- but it is **not fundamentally unavoidable**
- this family is only C-class today because the event-unification logic lives in highfreq, not because the source ingredients are unavailable

---

## 3.2 `highfreq_limit_event_stream_daily`

### Current upstream raw/source inputs
This family does **not** come directly from a source endpoint.
It is built from local highfreq tables:
- `highfreq_close_auction_working`
- indirectly also from stock-side intraday state via the derived builder’s context

### Code path
Derivation path:
- `src/ifa_data_platform/highfreq/derived_signals.py`
- builder reads:
  - `highfreq_stock_1m_working`
  - `highfreq_proxy_1m_working`
  - `highfreq_close_auction_working`
- builder writes:
  - `highfreq_limit_event_stream_working`

Archive V2 path:
- `archive_v2/runner.py`
  - family kind: `event_daily`
  - source table: `highfreq_limit_event_stream_working`
  - destination: `ifa_archive_highfreq_limit_event_stream_daily`

### Transformation / derivation logic
In current code, this is a builder-generated proxy event stream:
- builder reads recent close-auction rows
- for each row, it creates an event object like:
  - `event_type = 'limit_event_proxy'`
  - `symbol = ts_code`
  - `price = close`
  - `payload = serialized source row`
- these rows are inserted into `highfreq_limit_event_stream_working`

### Why current Archive V2 depends on local working state
Because the actual final object is a **derived event product**, not a native source-side final table.
Archive V2 archives the derived event stream after the builder materializes it.

### Is that dependency truly unavoidable?
**Mostly yes under current semantics**, because the archived family is not a raw source object.
But it is only unavoidable if Archive V2 refuses to own derivation logic.

### Possible alternative path
Archive V2 could re-derive this internally from:
- source-side limit/auction inputs
- plus source-side raw intraday state

But that is no longer a simple direct pull; it is “source-first plus derivation-inside-archive.”

### Current truth judgment
- current local dependency is understandable and near-unavoidable under current family semantics
- but not philosophically permanent if Archive V2 absorbs derivation logic later

---

## 3.3 `highfreq_sector_breadth_daily`

### Plain-language chain
This is the clearest example.

Current chain is:

```text
Tushare stk_mins (stock 1m)
Tushare ths_daily (proxy daily snapshot, used as proxy context)
Tushare close-auction snapshot
  -> highfreq_stock_1m_working
  -> highfreq_proxy_1m_working
  -> highfreq_close_auction_working
  -> DerivedSignalBuilder computes breadth metrics
  -> highfreq_sector_breadth_working
  -> Archive V2 archives latest per-sector snapshot into highfreq_sector_breadth_daily
```

### Exact upstream raw/source inputs
Builder reads:
- `highfreq_stock_1m_working`: `ts_code`, `trade_time`, `open`, `close`, `amount`
- `highfreq_proxy_1m_working`: `proxy_code`, `trade_time`, `open`, `close`, `vol`
- `highfreq_close_auction_working`: `ts_code`, `trade_date`, `close`, `vol`, `amount`

Ultimately those come from source-side truth via:
- stock intraday source: `stk_mins`
- proxy context: currently a THS daily proxy snapshot path (`ths_daily`), not true intraday
- close auction source path

### Code path that derives it
- `src/ifa_data_platform/highfreq/derived_signals.py`

The builder computes:
- `up_count`: number of recent stock rows with `close > open`
- `down_count`: number with `close < open`
- `strong_count`: number with positive `amount`
- `limit_up_count`: count of recent close-auction rows
- `spread_ratio = (up_count - down_count) / max(up_count + down_count, 1)`
- `sector_code`: currently just the latest `proxy_code` if available

Then it inserts a row into:
- `ifa2.highfreq_sector_breadth_working`

Archive V2 then reads that table and archives the latest snapshot per `sector_code` for the requested day.

### Why final Archive V2 family currently depends on local working/derived state
Because Archive V2 currently **does not compute breadth itself**.
It only archives the builder’s output snapshot.

### Is that dependency truly unavoidable?
**Not fully unavoidable.**

What is truly required is:
- raw stock intraday inputs
- some sector/proxy grouping context
- breadth calculation logic

So if Archive V2 were willing to own:
- the grouping context
- the breadth calculation
- the “latest daily snapshot” selection

then it could reproduce the same object without depending on `highfreq_sector_breadth_working` specifically.

### What the source-first / derivation-inside-archive path would be
Possible alternative:
1. Archive V2 directly pulls source-side stock intraday rows for the requested date
2. Archive V2 obtains sector/proxy grouping context
3. Archive V2 computes breadth metrics itself
4. Archive V2 writes final daily snapshot rows directly

### Current truth judgment
- local dependency is current implementation reality
- it is **not fundamentally unavoidable**
- what is unavoidable is the **derivation**, not the dependency on the pre-written working table itself

---

## 3.4 `highfreq_sector_heat_daily`

### Current upstream inputs
Same upstream builder context as sector breadth:
- `highfreq_stock_1m_working`
- `highfreq_proxy_1m_working`
- `highfreq_close_auction_working`

### Code path
- `src/ifa_data_platform/highfreq/derived_signals.py`

### Transformation / derivation logic
Current implementation is simplified:
- choose latest proxy row
- set `sector_code = proxy_code`
- compute `heat_score = max(close - open, 0)` from proxy row
- insert into `highfreq_sector_heat_working`

Archive V2 then archives latest per-sector snapshot.

### Why current Archive V2 depends on local working state
Because the heat object is produced by the builder, not by Archive V2.

### Is dependency truly unavoidable?
**Not fully unavoidable.**
The proxy/sector heat metric could be recomputed inside Archive V2 if the source-side proxy/sector context were trustworthy.

### Limitation
Because proxy upstream itself is semantically shaky in current repo, this family’s standalone reproducibility is also weakened by the proxy question.

### Current truth judgment
- currently local because builder owns the metric
- not inherently impossible to move into Archive V2 later
- but depends on clarifying proxy truth first

---

## 3.5 `highfreq_leader_candidate_daily`

### Current upstream inputs
Builder reads:
- `highfreq_stock_1m_working`
- plus minimal context from other highfreq working inputs

### Code path
- `src/ifa_data_platform/highfreq/derived_signals.py`

### Transformation / derivation logic
Current builder logic:
- take recent stock rows
- for top rows, compute:
  - `candidate_score = (close - open) / open`
  - `confirmation_state = 'confirmed' if score > 0.01 else 'watch'`
  - `continuation_health = 'healthy' if score > 0 else 'fragile'`
- write one row per symbol into `highfreq_leader_candidate_working`

Archive V2 archives the latest per-symbol snapshot.

### Why current Archive V2 depends on local working state
Because the “leader candidate” object is a derived label/state object, not a raw source-side row type.

### Is dependency truly unavoidable?
**Mostly yes under current family semantics**, but only because the derivation lives outside Archive V2 today.

### Alternative path
Archive V2 could directly compute the same candidate score/state from stock intraday inputs if the rule set were frozen and internalized.

### Current truth judgment
- local dependency is currently practical
- but the deeper truth is: the family depends on **local derivation logic**, not necessarily on the specific working table forever

---

## 3.6 `highfreq_intraday_signal_state_daily`

### Current upstream inputs
Builder reads:
- `highfreq_stock_1m_working`
- `highfreq_proxy_1m_working`
- `highfreq_close_auction_working`

### Code path
- `src/ifa_data_platform/highfreq/derived_signals.py`

### Transformation / derivation logic
Builder computes simplified market-wide state:
- `turnover_progress`
- `amount_progress`
- `emotion_stage`
- `validation_state`
- `risk_opportunity_state`
- writes one `scope_key='market_scope'` row into `highfreq_intraday_signal_state_working`

Archive V2 archives the latest per-scope snapshot.

### Why current Archive V2 depends on local working state
Because this is a synthetic market-state object derived from local rules over intraday inputs.

### Is dependency truly unavoidable?
**Mostly yes under current semantics**, unless Archive V2 is explicitly allowed to own the signal-state rule engine.

### Alternative path
Archive V2 could re-run the same signal-state computation directly from source-aligned intraday inputs.
That would still be source-first, but not source-direct.

### Current truth judgment
- currently local dependency is justified
- but the true irreducible component is the rule engine, not necessarily the precomputed table itself

---

## 4. Part A conclusion — are C-class families truly unavoidable local dependencies?

### Short answer
**Not uniformly.**

There are two different cases hidden inside current C-class:

### Case 1 — source ingredients exist, derivation could be moved into Archive V2 later
- `highfreq_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

For these, the current local dependency is an implementation choice more than a hard impossibility.
What is unavoidable is the derivation logic, not necessarily the pre-written working table.

### Case 2 — derived-family semantics are still inherently local/constructed
- `highfreq_limit_event_stream_daily`

This one is the most clearly local/constructed in its current form, because it is a builder-generated proxy event stream rather than a direct source family.

### Practical corrective takeaway
For the next big Archive V2 correction batch, these C-class families should be split conceptually into:
- **C1: derivation-inside-archive possible later**
- **C2: keep local-derived for now**

That is more accurate than one flat “must remain local” bucket.

---

## 5. Part B — D-class proxy / intraday re-check

Focus requested:
- `proxy_60m`
- `proxy_15m`
- `proxy_1m`
- broader intraday truth question for equity / index / non-equity families

---

## 5.1 Proxy intraday families

Families:
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

### Current upstream truth in code
Highfreq proxy source path today is:
- `src/ifa_data_platform/highfreq/adaptor_tushare.py`
- `fetch_proxy_1m()`

This function does:
- query `ths_daily(ts_code='885728.TI', trade_date='20260415')`
- convert that one daily row into a pseudo row at `15:00:00`
- write it into `highfreq_proxy_1m_working`

### Key truth
This is **not true source-side 1m data**.
It is a daily row with a synthetic timestamp.

### Does true source-side direct proxy 1m/15m/60m data exist in the repo today?
**Not proven.**

### Conclusion for proxy families
- keep `proxy_1m / 15m / 60m` as **D-class unresolved**
- they should **not** yet be promoted to “implementable later with known truthful source”
- first we need proof of a real direct proxy/sector-style intraday source path

---

## 5.2 Equity intraday families

Families:
- `equity_1m`
- `equity_15m`
- `equity_60m`

### Direct source-side truth check
Yes, proven.

Repo evidence:
- `archive/stock_minute_archiver.py`
- `archive/stock_15min_archiver.py`
- direct Tushare source: `stk_mins`
- frequencies already used in repo: `1min`, `15min`
- 60m archive closure exists in legacy archive side using truthful upstream chain as well

### Conclusion
These families should be treated as:
- **source-side truth exists**
- **implementable later in Archive V2 when explicitly enabled**
- not part of default production scope unless chosen later

---

## 5.3 Index intraday families

Families:
- `index_1m`
- `index_15m`
- `index_60m`

### Direct source-side truth check
The repo already proves an index 1m direct path in practice:
- `highfreq/adaptor_tushare.py`
- `fetch_index_1m(...)`
- source call used: `stk_mins(..., freq='1min')`

### Current practical interpretation
- true source-side 1m pull appears to exist in current repo/client behavior
- 15m and 60m are derivable from 1m inside Archive V2 later

### Caveat
The repo currently proves this operationally through the highfreq adaptor, not yet as a clean independent Archive V2 fetcher.
But that is enough to say source truth exists.

### Conclusion
These families should be treated as:
- **source-side truth exists / implementable later**
- not default production scope today

---

## 5.4 Non-equity intraday families

Interpreted here as futures / commodity / precious_metal intraday families.

Families:
- `futures_1m / 15m / 60m`
- `commodity_1m / 15m / 60m`
- `precious_metal_1m / 15m / 60m`

### Direct source-side truth check
Yes, proven.

Repo evidence:
- `archive/futures_intraday_archiver.py`
- source call: `ft_mins`
- explicit frequencies used in repo: `1min`, `15min`
- 60m family also exists in legacy archive side with truthful upstream path

### Conclusion
These families should be treated as:
- **source-side truth exists**
- **implementable later in Archive V2 when explicitly enabled**
- not part of default production scope unless explicitly requested

---

## 6. Revised truth status after this clarification

## C-class refined view
### Likely keep local-derived for now, but not because source ingredients are absent
- `highfreq_event_stream_daily`
- `highfreq_sector_breadth_daily`
- `highfreq_sector_heat_daily`
- `highfreq_leader_candidate_daily`
- `highfreq_intraday_signal_state_daily`

These are currently local because derivation lives in highfreq, but they are candidates for future Archive-V2-internal derivation if desired.

### Most truly local/constructed family in current shape
- `highfreq_limit_event_stream_daily`

## D-class revised view
### Stay unresolved
- `proxy_1m`
- `proxy_15m`
- `proxy_60m`

### Should be considered implementable later when explicitly enabled
- `equity_1m / 15m / 60m`
- `index_1m / 15m / 60m`
- `futures_1m / 15m / 60m`
- `commodity_1m / 15m / 60m`
- `precious_metal_1m / 15m / 60m`

Important nuance:
These families are not being promoted to default production scope here.
This clarification only says that the source truth exists, so Archive V2 can support them later without depending on pre-written retained-history tables.

---

## 7. Final judgment

### Part A final judgment
The current C-class bucket was too coarse.
The real truth is:
- current Archive V2 depends on local derived working tables for these families
- but several of those dependencies are **implementation-local**, not fundamentally unavoidable
- Archive V2 could later reproduce several of these families by pulling source-aligned raw inputs and running derivation internally

### Part B final judgment
- `proxy_1m / 15m / 60m` remain **unresolved** because true direct proxy intraday source is not proven
- `equity / index / futures / commodity / precious_metal` intraday families should be treated as **implementable later** because direct source-side intraday truth is already evidenced in repo code

That is the corrected upstream-truth picture before the next larger Archive V2 correction step.
