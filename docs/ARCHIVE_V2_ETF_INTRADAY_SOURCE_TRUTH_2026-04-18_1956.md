# Archive V2 ETF Intraday Source Truth Clarification

Generated: 2026-04-18 19:56 PDT  
Repo: `/Users/neoclaw/repos/ifa-data-platform`

## 1. Executive summary

This was a narrow verification batch on ETF intraday source truth.

### Final answer
- **Yes**, official source-side ETF historical minute truth exists.
- The correct source path is:
  - **Tushare `stk_mins` with ETF `ts_code`**
- Our current codebase does **not** use that ETF intraday historical path anywhere.
- Current repo usage around “ETF/sector/style 1m” is **not real ETF intraday raw truth**. It is a proxy/synthetic path built from `ths_daily`, not ETF minute history.
- Therefore ETF intraday should now move from **unresolved** to:
  - **later implementable when explicitly enabled** in Archive V2
  - **OFF by default** in the normal production profile

Important explicit conclusion:

> ETF intraday should be treated like equity intraday for future Archive V2 optional support, because the source-side historical minute truth exists.  
> “Not default now” does **not** mean “never implemented.”

---

## 2. Official source-side truth confirmed

Per the official Tushare documentation already checked by the user:
- endpoint: `stk_mins`
- supports: `1min / 5min / 15min / 30min / 60min`
- params include:
  - `ts_code`
  - `freq`
  - `start_date`
  - `end_date`
- official note says the path can provide more than 10 years of ETF historical minute data

### Practical implication
There is no longer a source-side uncertainty question for ETF intraday.
The source truth **does exist**.

---

## 3. Current repo usage truth

## 3.1 What the repo already does correctly for ETF
The repo already uses correct ETF source-side **daily** truth:
- `src/ifa_data_platform/midfreq/adaptors/tushare.py`
- dataset: `etf_daily_bar`
- source endpoint: `fund_daily`

Archive V2 also already uses ETF daily correctly:
- `src/ifa_data_platform/archive_v2/runner.py`
- family: `etf_daily`
- source endpoint: `fund_daily(trade_date=...)`

So ETF daily is already source-first and correct.

## 3.2 What the repo does **not** do today
The repo does **not** currently use:
- `stk_mins` with ETF `ts_code`
for ETF historical minute truth anywhere in:
- `highfreq`
- `archive`
- `archive_v2`
- `midfreq`

Search truth from the current codebase:
- `stk_mins` is used for:
  - stock 1m / 15m archival paths
  - index 1m highfreq path
- `ft_mins` is used for futures-family intraday
- there is **no ETF-specific intraday archiver**
- there is **no ETF-specific intraday Archive V2 family**
- there is **no ETF-specific highfreq minute raw path** using `stk_mins`

### Exact answer
**No, our current codebase does not already use ETF historical minute truth correctly.**

---

## 4. What the repo currently uses instead (and why it is not enough)

The only nearby path in current repo is:
- highfreq dataset: `etf_sector_style_1m_ohlcv`
- implementation path: `src/ifa_data_platform/highfreq/adaptor_tushare.py::fetch_proxy_1m()`
- source endpoint used there: `ths_daily`
- hard-coded example code path:
  - query `ths_daily(ts_code='885728.TI', trade_date='20260415')`
  - stamp row with synthetic `15:00:00`
  - persist to `highfreq_proxy_1m_working`

### Why this is wrong for ETF intraday truth
This path is:
- not ETF-specific minute data
- not historical minute truth
- not `stk_mins`
- not a true 1m bar series
- just a daily row with a synthetic intraday timestamp

### Truth judgment
This is a **pseudo/synthetic proxy path**, not real ETF historical minute truth.

So:
- it should **not** be used as evidence that ETF intraday is already implemented correctly
- it should **not** block ETF intraday from later being implemented correctly via true `stk_mins`

---

## 5. Exact gap in our current implementation

### Missing pieces in repo today
There is currently no:
- ETF intraday raw fetcher using `stk_mins(ts_code=<ETF>, freq=...)`
- ETF minute history table family like:
  - `etf_minute_history`
  - `etf_15min_history`
  - `etf_60min_history`
- Archive V2 family definitions for:
  - `etf_1m`
  - `etf_15m`
  - `etf_60m`
- Archive V2 direct-source intraday fetch path for ETF

### Exact implementation gap
The gap is not source availability.
The gap is entirely **repo-side implementation**.

In other words:
- source-side truth exists
- repo does not currently use it
- Archive V2 later-enable ETF intraday support is therefore a **missing implementation**, not a missing-source problem

---

## 6. Should Archive V2 later-enable intraday support include ETF?

### Families
- `etf_1m`
- `etf_15m`
- `etf_60m`

### Conclusion
**Yes.**

These should now be treated as:
- valid **later-enable Archive V2 intraday families**
- **OFF by default** in the normal production profile
- implemented later using the true raw/source path:
  - `stk_mins` with ETF `ts_code`

### Explicit correction to prior unresolved status
ETF intraday should no longer be left in the vague “unresolved / maybe no source truth” bucket.

The correct new status is:

> **ETF intraday source truth exists. Repo support is missing. Archive V2 should support ETF 1m/15m/60m later when explicitly enabled.**

---

## 7. Should the correct source path be direct `stk_mins` with ETF `ts_code`?

### Yes
That is the correct source-side raw path.

### Why
Because:
- official source-side truth explicitly exists there
- it is historical minute truth, not a proxy reconstruction
- it aligns with the corrected Archive V2 principle:
  - source-first where possible
  - no dependence on pseudo proxy/synthetic minute objects

### What it should **not** use
It should **not** use:
- `highfreq_proxy_1m_working`
- `ths_daily` pseudo intraday proxy rows
- synthetic timestamped daily rows

---

## 8. Is there any repo/client-layer reason ETF intraday cannot be treated similarly to equity intraday later?

### Current factual answer
**No repo/client-layer blocker is evidenced in the current codebase.**

What we do know:
- repo already uses `stk_mins` successfully for other tradable intraday families
- repo/client already supports the general call shape:
  - `ts_code`
  - `freq`
  - `start_date`
  - `end_date`
- ETF daily is already handled correctly elsewhere with ETF universes and ETF `ts_code`

### What is missing
Only the ETF-specific intraday implementation path is missing.

### Practical meaning
ETF intraday should be treated similarly to equity intraday in the Archive V2 roadmap:
- not default-active now
- but valid for later explicit enablement
- with direct source-side raw fetch, not pseudo proxy fallback

---

## 9. Practical Archive V2 roadmap conclusion

### ETF intraday roadmap status
Move ETF intraday from:
- **unresolved**

to:
- **later implementable when explicitly enabled**

### Family set that should later be supported
- `etf_1m`
- `etf_15m`
- `etf_60m`

### Correct implementation principle
When implemented later, ETF intraday should use:
- direct `stk_mins` with ETF `ts_code`

not:
- proxy/synthetic `ths_daily`-based minute approximation

### Production-profile implication
These ETF intraday families should remain:
- **OFF by default** in the normal production profile

But they should remain:
- **supported in the overall Archive V2 roadmap**
- available later when explicitly enabled by profile/operator intent

---

## 10. Truthful final judgment

### Exact answer to the required question
1. **Does our current codebase already use ETF historical minute truth correctly anywhere?**  
   - **No.**

2. **If not, where is the current implementation wrong or missing?**  
   - Missing ETF intraday raw fetch path via `stk_mins`
   - Missing ETF intraday history families/tables
   - Missing Archive V2 `etf_1m / etf_15m / etf_60m`
   - Current nearby path (`highfreq_proxy_1m_working` from `ths_daily`) is pseudo/synthetic and not valid ETF minute truth

3. **Should Archive V2 later-enable intraday support include `etf_1m / etf_15m / etf_60m`?**  
   - **Yes.**

4. **Should the correct source path be direct `stk_mins` with ETF `ts_code` rather than pseudo proxy/synthetic path?**  
   - **Yes.**

5. **Is there any reason in our repo/client layer why ETF intraday cannot be treated similarly to equity intraday later?**  
   - **No clear blocker is evidenced.**

### Final roadmap statement

> ETF intraday should now be treated as a **later-enable Archive V2 family group** backed by true source-side raw truth.  
> It should remain **OFF by default** in the normal production profile, but it should **not** be treated as “never implemented” or left in unresolved status anymore.
