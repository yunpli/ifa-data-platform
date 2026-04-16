# Tech Seed + Archive Backfill Clarification

_Date: 2026-04-16_0926_

## Scope
This focused batch covers only:
1. seeding missing tech Business Layer lists
2. archive backfill coverage/progress clarification
3. commodity / precious_metal key-focus/focus presence check

Artifacts created:
- `scripts/seed_tech_focus_lists.py`
- `artifacts/tech_focus_seed_2026-04-16_0922.json`
- `scripts/check_archive_and_commodity_lists.py`
- `artifacts/archive_and_commodity_check_2026-04-16_0924.json`

## 1. Tech list seeding result
Missing lists were seeded now:
- `default_tech_key_focus`
- `default_tech_focus`

### default_tech_key_focus
Result:
- inserted count: `20`
- unresolved count: `0`

Resolved inserts:
1. 寒武纪 -> `688256`
2. 海光信息 -> `688041`
3. 中际旭创 -> `300308`
4. 新易盛 -> `300502`
5. 天孚通信 -> `300394`
6. 润泽科技 -> `300442`
7. 中科曙光 -> `603019`
8. 浪潮信息 -> `000977`
9. 工业富联 -> `601138`
10. 沪电股份 -> `002463`
11. 生益科技 -> `600183`
12. 兆易创新 -> `603986`
13. 中微公司 -> `688012`
14. 北方华创 -> `002371`
15. 拓荆科技 -> `688072`
16. 澜起科技 -> `688008`
17. 芯原股份 -> `688521`
18. 佰维存储 -> `688525`
19. 三花智控 -> `002050`
20. 奥比中光-UW -> `688322`

### default_tech_focus
Result:
- inserted count: `65`
- unresolved count: `2`

Resolved examples include the full 20-name core plus broader tech names such as:
- 源杰科技 -> `688498`
- 东山精密 -> `002384`
- 胜宏科技 -> `300476`
- 协创数据 -> `300857`
- 宏景科技 -> `301396`
- 光环新网 -> `300383`
- 数据港 -> `603881`
- 网宿科技 -> `300017`
- 芯源微 -> `688037`
- 安集科技 -> `688019`
- 江丰电子 -> `300666`
- 雅克科技 -> `002409`
- 鼎龙股份 -> `300054`
- 伟测科技 -> `688372`
- 联动科技 -> `301369`
- 怡合达 -> `301029`
- 埃斯顿 -> `002747`
- 汇川技术 -> `300124`
- 绿的谐波 -> `688017`
- 中大力德 -> `002896`
- 柯力传感 -> `603662`
- 鸣志电器 -> `603728`
- 机器人 -> `300024`
- 博众精工 -> `688097`
- 思源电气 -> `002028`
- 海兴电力 -> `603556`
- 中国动力 -> `600482`
- 东方电气 -> `600875`
- 应流股份 -> `603308`
- 万泽股份 -> `000534`
- 固德威 -> `688390`
- 阳光电源 -> `300274`
- 中科江南 -> `301153`
- 深信服 -> `300454`
- 用友网络 -> `600588`
- 金山办公 -> `688111`
- 中科星图 -> `688568`
- 中国软件 -> `600536`
- 拓尔思 -> `300229`
- 科大讯飞 -> `002230`
- 虹软科技 -> `688088`
- 万兴科技 -> `300624`
- 德明利 -> `001309`
- 芯朋微 -> `688508`
- 圣邦股份 -> `300661`

Unresolved names (not force-inserted):
- 金海通
- 三星医疗

### Tech seeding judgment
- missing tech BL definitions were successfully created
- seeding was symbol-resolved against current DB truth, not inserted blindly by raw name
- unresolved names were explicitly left out rather than forced

## 2. Archive target coverage counts by category/frequency
Observed archive lists:
- `default_archive_targets_15min` -> `40` items
- `default_archive_targets_minute` -> `20` items
- no archive daily list was observed in current focus-list layer

### 15min archive targets
- stock: `22`
- futures: `2`
- commodity: `6`
- precious_metal: `2`
- macro: `8`
- index: `0` explicitly observed

### minute archive targets
- stock: `10`
- commodity: `4`
- precious_metal: `2`
- macro: `4`
- futures: `0` explicitly observed in current list breakdown
- index: `0` explicitly observed

### daily archive targets
- no dedicated archive daily target list was observed in current focus-list layer
- however `archive_target_catchup` does contain `stock` / `daily` rows, so daily archive/backfill logic exists in progression state even though a daily target list is not currently represented as a focus list

### Coverage judgment
Current explicit archive target scope is uneven:
- stock: present in 15min + minute
- futures: present only in 15min list
- commodity: present in 15min + minute
- precious_metal: present in 15min + minute
- macro: present in 15min + minute
- index: no explicit archive target coverage observed in current archive lists
- daily: no explicit archive target list observed; daily appears only via catch-up/progression state, not via a first-class current archive target list

## 3. Archive backfill progress summary
This section is based on:
- `archive_checkpoints`
- `archive_target_catchup`
- archive history table row counts

### Checkpoint truth by dataset/category
Observed checkpoint rows indicate uneven progress:

**stock**
- `stock_15min_history` -> checkpoint max date `2026-04-15`
- `stock_minute_history` -> checkpoint max date `2026-04-15`
- `stock_daily` -> checkpoint max date `2026-04-13`
- `stock_daily_catchup` -> checkpoint max date `2026-04-15`

**futures**
- `futures_15min_history` -> checkpoint max date `2025-09-12`
- `futures_minute_history` -> checkpoint max date `2025-09-12`
- `futures_history` -> checkpoint max date `2026-04-15`

**commodity**
- `commodity_15min_history` -> checkpoint max date `2025-06-16`
- `commodity_minute_history` -> checkpoint max date `2025-06-16`
- `commodity_history` -> checkpoint max date `2026-04-15`

**precious_metal**
- `precious_metal_15min_history` -> checkpoint max date `2025-06-16`
- `precious_metal_minute_history` -> checkpoint max date `2025-06-16`
- `precious_metal_history` -> checkpoint max date `2026-04-15`

**macro**
- `macro_history` -> checkpoint max date `2026-04-16`

### Row-count context for archive history tables
Current row counts:
- `stock_15min_history` = `1290`
- `stock_minute_history` = `2410`
- `futures_15min_history` = `22912`
- `futures_minute_history` = `32000`
- `commodity_15min_history` = `49456`
- `commodity_minute_history` = `56000`
- `precious_metal_15min_history` = `16000`
- `precious_metal_minute_history` = `16000`

### Catch-up state
Observed `archive_target_catchup` rows:
- `macro` / `minute` / `pending` -> `6`
- `stock` / `daily` / `completed` -> `1`
- `stock` / `daily` / `observed` -> `1`

### Archive backfill judgment
- archive progress is **not uniform** across category/frequency
- stock minute/15min has advanced through `2026-04-15`
- stock daily checkpointing is behind that (`2026-04-13` for `stock_daily`, with catch-up state through `2026-04-15`)
- futures minute/15min are materially older at `2025-09-12`
- commodity minute/15min are materially older at `2025-06-16`
- precious_metal minute/15min are materially older at `2025-06-16`
- macro appears freshest (`2026-04-16`)

So the truthful current state is:
- stock archive is relatively advanced
- macro is relatively advanced
- futures/commodity/precious_metal 15min/minute backfill remains significantly older and therefore uneven
- index archive coverage/progress is effectively absent from the current explicit archive target layer

## 4. Commodity / precious_metal key-focus/focus presence check
Result:
- no commodity/precious_metal key-focus/focus style lists were found in current Business Layer focus-list definitions using name-pattern presence check
- `pm_commodity_lists` result was empty

### Truthful answer
1. Do such lists already exist?
- **No explicit commodity / precious_metal key-focus/focus lists were found.**

2. Since they do not exist:
- this is an explicit Business Layer definition gap if such thematic focus routing is intended

### Clean supplemental proposal for next seeding
Based on the currently accepted runtime/archive universe, next supplemental BL additions should likely include:
- a commodity key-focus list
- a commodity focus list
- a precious_metal key-focus list
- a precious_metal focus list

Seed source should come from the current accepted runtime/archive universe already represented in:
- `default_archive_targets_15min`
- `default_archive_targets_minute`
- current archive checkpoints/catch-up scope

At this batch stage, these lists were **not** auto-seeded because no concrete approved name set was provided here.
That gap is therefore recorded explicitly rather than guessed/faked.

## 5. Explicit missing definitions / gaps
1. Tech BL gap was real and is now fixed:
- `default_tech_key_focus`
- `default_tech_focus`

2. Tech unresolved names remain:
- `金海通`
- `三星医疗`

3. Archive target-definition gaps still present:
- no explicit archive index target coverage observed
- no explicit archive daily target list observed in current focus-list layer

4. Commodity / precious_metal focus-list gaps still present:
- no commodity key-focus/focus list found
- no precious_metal key-focus/focus list found

## 6. Truthful final judgment
- tech Business Layer seeding is now materially improved and usable:
  - `default_tech_key_focus` seeded with 20 resolved A-share names
  - `default_tech_focus` seeded with 65 resolved names
- unresolved tech names were handled truthfully and not force-inserted
- archive target coverage is currently uneven by category/frequency
- stock and macro progression are relatively current, while futures/commodity/precious_metal 15min/minute backfill are materially older
- archive index coverage is not explicitly present in current target definitions
- commodity / precious_metal focus-style BL definitions do not currently exist and remain an explicit next-gap if that routing is desired
