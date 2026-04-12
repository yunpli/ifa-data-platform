# Job 10: Lowfreq Asset Plan

## Goal

沉淀一批**非 2.0 必需、但长期高复用**的低频资产型数据，接入 lowfreq 主链（raw → current → history/version），但**不阻塞 daily_light**，优先放入 `weekly_deep` 或独立 `asset_layer` 组。

---

## Dataset Selection (fixed scope only)

本次只从允许范围中选取**优先值得沉淀且已有 API 可验证**的 dataset。

| Dataset | Tushare API | Domain | Worth Keeping | Suggested Group |
|---|---|---|---|---|
| top10_holders | `top10_holders` | 公司/资本结构 | 股东结构长期高价值，可用于机构持仓/控制权分析 | weekly_deep / asset_layer |
| top10_floatholders | `top10_floatholders` | 公司/资本结构 | 流通股东结构对筹码和风格判断有价值 | weekly_deep / asset_layer |
| pledge_stat | `pledge_stat` | 公司/资本结构 | 质押风险是长期风险画像核心变量 | weekly_deep / asset_layer |
| income | `income` | 财务/业绩 | 收入/利润是最基础财务沉淀层 | weekly_deep / asset_layer |
| balance | `balancesheet` | 财务/业绩 | 资产负债结构是长期资产画像基石 | weekly_deep / asset_layer |
| forecast | `forecast` | 财务/业绩 | 业绩预告具备事件+财务双属性 | weekly_deep / asset_layer |
| express | `express` | 财务/业绩 | 业绩快报是正式财报前的高价值快照 | weekly_deep / asset_layer |
| margin | `margin` | 市场慢变量 | 融资融券是市场风险偏好慢变量 | weekly_deep / asset_layer |
| north_south_flow | `moneyflow_hsgt` | 市场慢变量 | 北南向资金是中长期风格流向核心变量 | weekly_deep / asset_layer |
| convertible_bond_basic | `cb_basic` | 衍生资产 | 可转债资产池长期有复用价值 | weekly_deep / asset_layer |
| bond_basic (optional) | `bond_basic` | 衍生资产 | 可做债券层扩展，但当前 API 不可用/待确认 | 暂不进入 |

---

## Canonical Field Design

以下采用**最小可用 canonical**，先保留长期分析最常用字段，不做大而全映射。

### 1) top10_holders_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `holder_name`
- `hold_amount`
- `hold_ratio`
- `hold_float_ratio`
- `hold_change`
- `holder_type`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, holder_name)`

### 2) top10_floatholders_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `holder_name`
- `hold_amount`
- `hold_ratio`
- `hold_float_ratio`
- `hold_change`
- `holder_type`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, holder_name)`

### 3) pledge_stat_current
- `id`
- `ts_code`
- `end_date`
- `pledge_count`
- `unrest_pledge`
- `rest_pledge`
- `total_share`
- `pledge_ratio`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date)`

### 4) income_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `report_type`
- `basic_eps`
- `diluted_eps`
- `total_revenue`
- `revenue`
- `operate_profit`
- `total_profit`
- `n_income`
- `n_income_attr_p`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, report_type)`

### 5) balance_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `report_type`
- `total_share`
- `money_cap`
- `accounts_receiv`
- `inventories`
- `total_cur_assets`
- `total_nca`
- `total_assets`
- `total_cur_liab`
- `total_ncl`
- `total_liab`
- `total_hldr_eqy_exc_min_int`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, report_type)`

### 6) forecast_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `forecast_type`
- `p_change_min`
- `p_change_max`
- `net_profit_min`
- `net_profit_max`
- `last_parent_net`
- `summary`
- `change_reason`
- `update_flag`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, ann_date)`

### 7) express_current
- `id`
- `ts_code`
- `ann_date`
- `end_date`
- `revenue`
- `operate_profit`
- `total_profit`
- `n_income`
- `total_assets`
- `diluted_eps`
- `diluted_roe`
- `bps`
- `yoy_sales`
- `yoy_op`
- `yoy_tp`
- `yoy_dedu_np`
- `yoy_eps`
- `yoy_roe`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code, end_date, ann_date)`

### 8) margin_current
- `id`
- `trade_date`
- `exchange_id`
- `rzye`
- `rzmre`
- `rzche`
- `rqye`
- `rqmcl`
- `rzrqye`
- `rqyl`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(trade_date, exchange_id)`

### 9) north_south_flow_current
- `id`
- `trade_date`
- `ggt_ss`
- `ggt_sz`
- `hgt`
- `sgt`
- `north_money`
- `south_money`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(trade_date)`

### 10) convertible_bond_basic_current
- `id`
- `ts_code`
- `bond_full_name`
- `bond_short_name`
- `cb_code`
- `stk_code`
- `stk_short_name`
- `maturity`
- `par`
- `issue_price`
- `issue_size`
- `remain_size`
- `value_date`
- `maturity_date`
- `coupon_rate`
- `list_date`
- `delist_date`
- `exchange`
- `version_id`
- `created_at`
- `updated_at`

Unique key:
- `(ts_code)`

### 11) bond_basic (optional)
- 当前先不设计 canonical 落库实现
- 原因：`bond_basic` 本轮 API 验证未通过，先不把不稳定入口纳入 Job 10 首批实现

---

## History / Version Policy

原则：**除明确只做临时快照的数据外，全部进入 history/version**。

| Dataset | History | Version | Reason |
|---|---|---|---|
| top10_holders | yes | yes | 股东结构会变，必须支持版本对比 |
| top10_floatholders | yes | yes | 流通股东变化具备强时间价值 |
| pledge_stat | yes | yes | 风险画像需要时间序列 |
| income | yes | yes | 财报天然需要版本沉淀 |
| balance | yes | yes | 财报天然需要版本沉淀 |
| forecast | yes | yes | 预告有更新/修正版本 |
| express | yes | yes | 快报具有时间价值 |
| margin | yes | yes | 市场慢变量是时间序列 |
| north_south_flow | yes | yes | 资金流本质是时间序列 |
| convertible_bond_basic | yes | yes | 转债池会增删变化 |
| bond_basic (optional) | TBD | TBD | API 未确认前不接入 |

---

## Routing Decision

### Not in daily_light
以下 dataset **不进入 daily_light**：
- top10_holders
- top10_floatholders
- pledge_stat
- income
- balance
- forecast
- express
- margin
- north_south_flow
- convertible_bond_basic
- bond_basic (optional)

原因：
- 都属于“长期资产沉淀层”，不是主链保活所需基线
- 一旦接口不稳或权限有差异，不应阻塞 daily_light
- 更新频率相对较慢，更适合周批或独立资产组

### Preferred placement
- **weekly_deep**：`top10_holders`, `top10_floatholders`, `pledge_stat`, `income`, `balance`, `forecast`, `express`, `convertible_bond_basic`
- **asset_layer（新 group，建议）**：`margin`, `north_south_flow`，以及后续成熟后的 `bond_basic`

建议：
- 若想最小改动，先挂到 `weekly_deep`
- 若想边界更清晰，新增 `asset_layer` 更合理

---

## Why each dataset is worth keeping

- `top10_holders`：机构/大股东结构是中长期判断核心资产
- `top10_floatholders`：流通筹码结构可复用于风格和筹码分析
- `pledge_stat`：质押是长期风险监控高价值变量
- `income`：利润表是基本面沉淀基础层
- `balance`：资产负债表决定公司质量画像
- `forecast`：预告常早于正式财报，具备前瞻价值
- `express`：快报是财报季高价值过渡层
- `margin`：融资融券反映市场风险偏好
- `north_south_flow`：北南向资金是长期市场风格变量
- `convertible_bond_basic`：转债池是独立可复用资产层
- `bond_basic`：债券资产层长期有价值，但当前先不纳入首批

---

## Implementation Boundary (what not to do)

本次 Job 10 **不做**：
- 不改 Job 8 / Job 9 已通过链路
- 不改 daemon 主体逻辑
- 不做 facts / signals
- 不扩固定范围之外的 dataset
- 不做性能优化
- 不做架构重构
- 不强行把资产层 dataset 放进 daily_light
- 不把 `bond_basic` 在 API 未确认前硬接进主链

---

## Recommended Phase Split

### Phase 10A (recommended first implementation batch)
优先实现：
- top10_holders
- top10_floatholders
- pledge_stat
- income
- balance
- forecast
- margin
- north_south_flow
- convertible_bond_basic

理由：
- API 已验证可通
- 长期资产价值明确
- 字段模式清晰

### Phase 10B (optional / follow-up)
后续再做：
- express
- bond_basic

理由：
- `express` 本轮样本返回为 0，需要再找稳定参数窗口
- `bond_basic` 当前 API 未验证通过

---

## Deliverables for implementation phase

实现阶段（代码部分才走 ACP）应产出：
- migration
- canonical current persistence
- history persistence
- Tushare adaptor fetch methods
- dataset registration
- weekly_deep / asset_layer group wiring
- integration validation
- `job10_lowfreq_asset_report.md`

---

## Final Recommendation

Job 10 应按“**资产层沉淀，不阻塞主链**”原则推进：
- daily_light：不加新负担
- weekly_deep / asset_layer：承接 Job 10
- 首批实现以 API 已验证可通的数据为主
- `bond_basic` 暂缓
