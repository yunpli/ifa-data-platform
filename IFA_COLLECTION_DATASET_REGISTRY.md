# IFA_COLLECTION_DATASET_REGISTRY.md

> 目的：把当前 repo 中 lowfreq / midfreq 已实现 dataset 做成逐项台账，供长期维护使用。
>
> 说明：
> - 本文档优先追求“接手可用”，不是营销式完成口径。
> - “表存在”不等于“生产级闭环”。
> - 成熟度定义：
>   - S0：只有设计或结构
>   - S1：current 已接通
>   - S2：history/version 已接通
>   - S3：daemon/summary/验收较完整

---

## 1. MIDFREQ DATASETS

### 1.1 equity_daily_bar
- dataset 名称：`equity_daily_bar`
- 层级：midfreq
- 读取 Universe：B
- source / API：Tushare / `daily`
- 频率 / 窗口：`post_close_final`（15:20 Asia/Shanghai）
- current 表：`ifa2.equity_daily_bar_current`
- history 表：`ifa2.equity_daily_bar_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 有真实链路
  - 早期文档明确有 dummy/test 数据痕迹
  - 当前维护时不要默认全表纯真实生产数据

### 1.2 index_daily_bar
- dataset 名称：`index_daily_bar`
- 层级：midfreq
- 读取 Universe：例外（固定指数列表，不是从 B symbol_universe 逐 symbol 拉取）
- source / API：Tushare / `index_daily`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.index_daily_bar_current`
- history 表：`ifa2.index_daily_bar_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 代码里使用固定指数列表
  - 历史上也有 dummy/test 数据痕迹
  - 这是 Universe 规则的一个现实例外点

### 1.3 etf_daily_bar
- dataset 名称：`etf_daily_bar`
- 层级：midfreq
- 读取 Universe：例外（固定 ETF 列表）
- source / API：Tushare / `etf_daily`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.etf_daily_bar_current`
- history 表：`ifa2.etf_daily_bar_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：
  - 历史文档提到 Tushare `etf_daily` 有接口/权限异常（如 40101）
  - 历史数据纯度需复查

### 1.4 northbound_flow
- dataset 名称：`northbound_flow`
- 层级：midfreq
- 读取 Universe：例外（全局资金流，不是逐 symbol B list）
- source / API：Tushare / `moneyflow_hsgt`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.northbound_flow_current`
- history 表：`ifa2.northbound_flow_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 早期文档显示存在 dummy/test 数据混入历史

### 1.5 limit_up_down_status
- dataset 名称：`limit_up_down_status`
- 层级：midfreq
- 读取 Universe：例外（按交易日聚合，不是逐 symbol B list）
- source / API：Tushare / `stk_limit`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.limit_up_down_status_current`
- history 表：`ifa2.limit_up_down_status_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - B4 文档明确：曾有 “1 Dummy + 2 Real” 混合状态
  - 后续若做纯生产台账，需要清洗历史版本

### 1.6 margin_financing
- dataset 名称：`margin_financing`
- 层级：midfreq
- 读取 Universe：B
- source / API：Tushare / `margin`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.margin_financing_current`
- history 表：`ifa2.margin_financing_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 当前 DB 实测：current=80, history=240
  - B6 Batch 2 已补 history + active 痕迹
  - 但 latest summary 证据仍需再硬化

### 1.7 turnover_rate
- dataset 名称：`turnover_rate`
- 层级：midfreq
- 读取 Universe：B
- source / API：Tushare / `daily`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.turnover_rate_current`
- history 表：`ifa2.turnover_rate_history`
- dataset_versions：启用
- 当前成熟度：S1~S2
- 备注：
  - 当前文档显示可能为 0 条
  - 周日/非交易日无数据是常见原因
  - 不能把“结构接通”误判为“生产闭环”

### 1.8 southbound_flow
- dataset 名称：`southbound_flow`
- 层级：midfreq
- 读取 Universe：例外（全局资金流，不是逐 symbol B list）
- source / API：Tushare / `moneyflow_hsgt`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.southbound_flow_current`
- history 表：`ifa2.southbound_flow_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：
  - B6 文档显示 current=1
  - 需要继续积累稳定执行证据

### 1.9 main_force_flow
- dataset 名称：`main_force_flow`
- 层级：midfreq
- 读取 Universe：B
- source / API：Tushare / `moneyflow`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.main_force_flow_current`
- history 表：`ifa2.main_force_flow_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 当前 DB 实测：current=19, history=19
  - B6 Batch 2 已补 history + active 痕迹
  - latest summary 里尚未形成最硬新证据

### 1.10 sector_performance
- dataset 名称：`sector_performance`
- 层级：midfreq
- 读取 Universe：例外 / 结构预留
- source / API：当前代码未形成真实 fetch（fetch 中返回空）
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.sector_performance_current`
- history 表：`ifa2.sector_performance_history`
- dataset_versions：启用（架构上）
- 当前成熟度：S0~S1
- 备注：
  - 已接入 daemon config
  - 但当前不应视为真实生产 dataset

### 1.11 dragon_tiger_list
- dataset 名称：`dragon_tiger_list`
- 层级：midfreq
- 读取 Universe：B（业务目标），API 实际按 trade_date 查询
- source / API：Tushare / `top_list`
- 频率 / 窗口：`post_close_final`
- current 表：`ifa2.dragon_tiger_list_current`
- history 表：`ifa2.dragon_tiger_list_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：
  - 当前 DB 实测：current=88, history=88
  - B6 Batch 2 已补 history + active 痕迹

### 1.12 limit_up_detail
- dataset 名称：`limit_up_detail`
- 层级：midfreq
- 读取 Universe：例外（trade_date 级明细）
- source / API：Tushare / `stk_limit`
- 频率 / 窗口：`post_close_extended`
- current 表：`ifa2.limit_up_detail_current`
- history 表：`ifa2.limit_up_detail_history`
- dataset_versions：启用
- 当前成熟度：S1
- 备注：
  - 结构已接上
  - 当前仍偏“已定义/已接入”，不是完整生产闭环

---

## 2. LOWFREQ DATASETS（生产/业务向）

> 说明：lowfreq_datasets 表里存在大量 test_* / e2e_* / dummy 数据集注册项。
>
> 本节优先列生产/业务向 dataset；测试项单独放在文末。

### 2.1 trade_cal
- dataset 名称：`trade_cal`
- 层级：lowfreq
- 读取 Universe：C（但本质为全市场交易日历，Universe 约束弱）
- source / API：Tushare / trade calendar
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.trade_cal_current`
- history 表：`ifa2.trade_cal_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：基础表，维护优先级高

### 2.2 stock_basic
- dataset 名称：`stock_basic`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stock_basic`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.stock_basic_current`
- history 表：`ifa2.stock_basic_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：Universe seed / 基础资产台账核心依赖

### 2.3 index_basic
- dataset 名称：`index_basic`
- 层级：lowfreq
- 读取 Universe：例外（指数基础表）
- source / API：Tushare / `index_basic`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.index_basic_current`
- history 表：`ifa2.index_basic_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：指数类通常是 Universe 例外，不是逐 C symbol 拉取

### 2.4 fund_basic_etf
- dataset 名称：`fund_basic_etf`
- 层级：lowfreq
- 读取 Universe：例外（ETF 基础主数据）
- source / API：Tushare / `fund_basic`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.fund_basic_etf_current`
- history 表：`ifa2.fund_basic_etf_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：与 `etf_basic` 存在命名重叠，要谨慎区分

### 2.5 etf_basic
- dataset 名称：`etf_basic`
- 层级：lowfreq
- 读取 Universe：例外
- source / API：Tushare / `fund_basic`
- 频率 / 窗口：历史注册项
- current 表：未统一到单独 `etf_basic_current`（以当前 DB/代码实际为准）
- history 表：未统一
- dataset_versions：理论上启用
- 当前成熟度：S0~S1
- 备注：当前 lowfreq_datasets 表里是 disabled=0，命名与 `fund_basic_etf` 重叠，建议后续治理统一

### 2.6 sw_industry_mapping
- dataset 名称：`sw_industry_mapping`
- 层级：lowfreq
- 读取 Universe：C / 例外（行业映射基础层）
- source / API：Tushare / 行业映射
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.sw_industry_mapping_current`
- history 表：`ifa2.sw_industry_mapping_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：板块/行业归属基础表

### 2.7 announcements
- dataset 名称：`announcements`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / 公告相关接口
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.announcements_current`
- history 表：`ifa2.announcements_history`
- dataset_versions：启用
- 当前成熟度：S3
- 备注：低频文档/公告主干之一

### 2.8 news
- dataset 名称：`news`
- 层级：lowfreq
- 读取 Universe：C / 例外（新闻并不总是逐 symbol）
- source / API：Tushare / news
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.news_current`
- history 表：`ifa2.news_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：与 `news_basic` 并存，注意区分

### 2.9 news_basic
- dataset 名称：`news_basic`
- 层级：lowfreq
- 读取 Universe：例外
- source / API：Tushare / `news`
- 频率 / 窗口：已注册，实际窗口依当前调度/runner 使用而定
- current 表：`ifa2.news_basic_current`
- history 表：`ifa2.news_basic_history`
- dataset_versions：启用
- 当前成熟度：S1~S2
- 备注：更偏新闻元数据层

### 2.10 research_reports
- dataset 名称：`research_reports`
- 层级：lowfreq
- 读取 Universe：C
- source / API：研究报告抓取（当前统一归在 tushare/source registry 体系）
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.research_reports_current`
- history 表：`ifa2.research_reports_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：业务价值高，但需确认实际 provider 覆盖深度

### 2.11 investor_qa
- dataset 名称：`investor_qa`
- 层级：lowfreq
- 读取 Universe：C
- source / API：投资者问答相关源
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.investor_qa_current`
- history 表：`ifa2.investor_qa_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：文档/互动信息层

### 2.12 index_weight
- dataset 名称：`index_weight`
- 层级：lowfreq
- 读取 Universe：例外（指数成分权重）
- source / API：Tushare / `index_weight`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.index_weight_current`
- history 表：`ifa2.index_weight_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：指数相关结构层

### 2.13 etf_daily_basic
- dataset 名称：`etf_daily_basic`
- 层级：lowfreq
- 读取 Universe：例外（ETF 统计）
- source / API：Tushare / ETF daily basic
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.etf_daily_basic_current`
- history 表：`ifa2.etf_daily_basic_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：ETF 结构层，不一定是最核心基座表

### 2.14 share_float
- dataset 名称：`share_float`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / share float
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.share_float_current`
- history 表：`ifa2.share_float_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：股本/流通层资产表

### 2.15 company_basic
- dataset 名称：`company_basic`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / company basic
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.company_basic_current`
- history 表：`ifa2.company_basic_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：基础公司画像层

### 2.16 stk_managers
- dataset 名称：`stk_managers`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stk_managers`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.stk_managers_current`
- history 表：`ifa2.stk_managers_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：与 `management` 存在命名重叠

### 2.17 management
- dataset 名称：`management`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stock_manager`
- 频率 / 窗口：`weekly_deep`（更合理）
- current 表：`ifa2.management_current`
- history 表：`ifa2.management_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：和 `stk_managers` 语义高度接近，后续需统一

### 2.18 new_share
- dataset 名称：`new_share`
- 层级：lowfreq
- 读取 Universe：例外（IPO 相关）
- source / API：Tushare / `new_share`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.new_share_current`
- history 表：`ifa2.new_share_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：IPO 时间表/结果层

### 2.19 new_stock
- dataset 名称：`new_stock`
- 层级：lowfreq
- 读取 Universe：例外
- source / API：Tushare / 新股相关
- 频率 / 窗口：历史注册项
- current 表：`ifa2.new_stock_current`
- history 表：`ifa2.new_stock_history`
- dataset_versions：启用
- 当前成熟度：S1
- 备注：与 `new_share` 也有语义重叠风险

### 2.20 stk_holdernumber
- dataset 名称：`stk_holdernumber`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stk_holdernumber`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.stk_holdernumber_current`
- history 表：`ifa2.stk_holdernumber_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：股东户数层

### 2.21 name_change
- dataset 名称：`name_change`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stock_namechange`
- 频率 / 窗口：`daily_light`, `weekly_deep`
- current 表：`ifa2.name_change_current`
- history 表：`ifa2.name_change_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：证券更名历史层

### 2.22 top10_holders
- dataset 名称：`top10_holders`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `top10_holders`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.top10_holders_current`
- history 表：`ifa2.top10_holders_history`
- dataset_versions：启用
- 当前成熟度：S2~S3
- 备注：股东结构深度层

### 2.23 top10_floatholders
- dataset 名称：`top10_floatholders`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `top10_floatholders`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.top10_floatholders_current`
- history 表：`ifa2.top10_floatholders_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：与 top10_holders 一起构成股东层深度集

### 2.24 pledge_stat
- dataset 名称：`pledge_stat`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `pledge_stat`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.pledge_stat_current`
- history 表：`ifa2.pledge_stat_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：股权质押层

### 2.25 forecast
- dataset 名称：`forecast`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `forecast`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.forecast_current`
- history 表：`ifa2.forecast_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：业绩预告层

### 2.26 margin
- dataset 名称：`margin`
- 层级：lowfreq
- 读取 Universe：例外 / C 相关
- source / API：Tushare / `margin`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.margin_current`
- history 表：`ifa2.margin_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：与 midfreq `margin_financing` 语义相关但不相同

### 2.27 north_south_flow
- dataset 名称：`north_south_flow`
- 层级：lowfreq
- 读取 Universe：例外（全局资金流）
- source / API：Tushare / `moneyflow_hsgt`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.north_south_flow_current`
- history 表：`ifa2.north_south_flow_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：与 midfreq northbound/southbound_flow 要明确层次区分

### 2.28 stock_repurchase
- dataset 名称：`stock_repurchase`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stock_repurchase`
- 频率 / 窗口：已注册，适合 `weekly_deep`
- current 表：`ifa2.stock_repurchase_current`
- history 表：`ifa2.stock_repurchase_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：公司行为层

### 2.29 stock_dividend
- dataset 名称：`stock_dividend`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `dividend`
- 频率 / 窗口：已注册，适合 `weekly_deep`
- current 表：`ifa2.stock_dividend_current`
- history 表：`ifa2.stock_dividend_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：分红派息层

### 2.30 stock_equity_change
- dataset 名称：`stock_equity_change`
- 层级：lowfreq
- 读取 Universe：C
- source / API：Tushare / `stock_equity_change`
- 频率 / 窗口：`weekly_deep`
- current 表：`ifa2.stock_equity_change_current`
- history 表：`ifa2.stock_equity_change_history`
- dataset_versions：启用
- 当前成熟度：S2
- 备注：股本变动层

### 2.31 china_a_share_daily
- dataset 名称：`china_a_share_daily`
- 层级：lowfreq
- 读取 Universe：不建议视为生产项
- source / API：Tushare / dummy runner 痕迹
- 频率 / 窗口：历史测试/骨架用途
- current 表：需按实际表映射核查
- history 表：需核查
- dataset_versions：可能启用
- 当前成熟度：S0~S1
- 备注：应视为遗留/测试性质，非当前正式维护主项

---

## 3. LOWFREQ DATASETS（测试 / E2E / Dummy 注册项）

> 这些 dataset 出现在 `ifa2.lowfreq_datasets` 中，但不应作为正式生产 collection 台账主项使用。
> 维护时若做正式清理，应单独评估是否禁用/隔离。

### 3.1 测试/占位数据集清单
- `e2e_test_dataset`
- `test_adaptor_path`
- `test_as_of_time`
- `test_current_after_first`
- `test_current_latest`
- `test_dataset`
- `test_disabled_runner`
- `test_e2e_dummy`
- `test_error_status`
- `test_first_ingest_active`
- `test_history_accumulation`
- `test_history_trade_cal`
- `test_history_version_registry`
- `test_idempotent_rerun`
- `test_job4_first_ingest`
- `test_job5_active_switch`
- `test_job5_asof`
- `test_job5_current_stability`
- `test_job5_promoted_at`
- `test_job5_rerun_stability`
- `test_job5_stock_basic_history`
- `test_job5_superseded`
- `test_job5_trade_cal_history`
- `test_job5_version_growth`
- `test_list_enabled`
- `test_list_versions`
- `test_promote_explicit`
- `test_promote_explicit2`
- `test_rerun_stable`
- `test_second_ingest_retained`
- `test_stock_basic_snapshot`
- `test_trade_cal_incremental`
- `test_trigger_runner`
- `test_upsert`
- `test_version_by_id`
- `test_vq_as_of`
- `test_watermark_advance`

### 3.2 处理建议
- 默认不要把这些测试 dataset 纳入生产巡检主报表
- 如果后续做正式治理：
  1. 先导出清单
  2. 判断哪些仍被单元/集成测试依赖
  3. 再决定是否 disable / 隔离 / 清理

---

## 4. 当前最重要的维护提醒

1. `dataset_versions` 的 active 语义并不完全干净，不能默认“一 dataset 仅一 active row”。
2. `midfreq_execution_summary` latest 记录尚不足以证明 B6 Batch 2 三 dataset 已形成最强最新闭环证据。
3. 部分 midfreq 表混有早期 dummy/test 数据。
4. lowfreq 注册表中含有大量 test_* / e2e_* / dummy 项，维护时需要显式区分生产与测试。
5. `fund_basic_etf` vs `etf_basic`、`management` vs `stk_managers`、`new_share` vs `new_stock` 都存在重叠语义，后续应治理统一。
6. 指数/ETF/资金流类 dataset 常常是 Universe 规则的例外路径，不能机械套用“全部逐 symbol 读 A/B/C”。

---

## 5. 一句话结论

当前 dataset 台账已经足够支持维护接手，但接手人必须始终记住：**“已注册/已建表/已接入 daemon” 不等于 “已完全生产级收口”。** 真正判断成熟度，必须结合 current、history、dataset_versions、latest summary/state、以及是否混有测试数据一并核查。
