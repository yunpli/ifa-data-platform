# Job 7 — iFA 2.0 中国市场低频覆盖盘点与扩展规划

## 1. Background

Job 1–6 已经在本仓库内建立了 iFA 中国市场 / A 股 lowfreq 的最小可运行基座：

- Tushare client / adaptor
- dataset registry
- run state / raw persistence / canonical persistence
- version registry + history tables
- lowfreq daemon (`daily_light` / `weekly_deep`)
- daemon state / group state / health / validate tooling

但 Job 1–6 的重点是**把 lowfreq 基础设施跑起来**，不是证明“当前 lowfreq 覆盖面已经足以支撑 iFA 2.0 中国市场产品定义”。

因此 Job 7 的目标不是继续大规模接入新 dataset，而是先回答两个产品级问题：

1. **当前 lowfreq 体系是否已经足以支撑 iFA 2.0 中国市场？**
2. **如果不够，下一步应该优先补哪些低频对象？哪些适合作为长期沉淀的数据资产？**

本文件基于以下三部分进行盘点：

- iFA 2.0 产品定义（`README.md`, `docs/architecture.md`）
- 当前 lowfreq 已实现能力（`docs/lowfreq_framework.md` 及 `src/ifa_data_platform/lowfreq/*`）
- Tushare 作为中国市场 lowfreq 来源的扩展机会（本次由于本地无可用 token，仅做规划层判断，不做权限实测）

---

## 2. Current implemented lowfreq scope

### 2.1 已真实实现并进入运行体系的 lowfreq 对象

当前 repo 中，**真实接入 + 版本化 + daemon 化**的 lowfreq dataset 只有两个：

1. `trade_cal`
2. `stock_basic`

证据：

- `scripts/register_datasets.py` 仅注册这两个 dataset
- `src/ifa_data_platform/lowfreq/adaptors/tushare.py` 仅实现这两个 dataset 的真实 fetch/persist 分支
- `src/ifa_data_platform/lowfreq/daemon_config.py` 中 `daily_light` / `weekly_deep` 两个 group 当前都只包含：
  - `trade_cal`
  - `stock_basic`
- `docs/lowfreq_framework.md` 明确写明 Tushare 已接入对象仅有这两个

### 2.2 当前 lowfreq 运行能力已经具备什么

当前 lowfreq 不是脚本碎片，而是已有一套最小运行体系：

- **注册层**：`lowfreq_datasets`
- **执行层**：`lowfreq_runs`
- **原始抓取层**：`lowfreq_raw_fetch`
- **当前态 canonical**：
  - `trade_cal_current`
  - `stock_basic_current`
- **历史版本层**：
  - `dataset_versions`
  - `trade_cal_history`
  - `stock_basic_history`
- **编排层**：`lowfreq daemon`
- **状态层**：
  - `lowfreq_daemon_state`
  - `lowfreq_group_state`
- **查询层**：`CurrentQuery` / `VersionQuery`

### 2.3 当前两个 dataset 对应 iFA 2.0 中国市场的什么需求

#### A. `trade_cal`

**对应产品需求：**

- 中国市场交易日历
- 报告日程判定
- pre / intraday / post 节奏控制
- 非交易日 / 周末 / 节假日逻辑基底

**价值：**

- 是市场时钟系统的基础真值表
- 是后续 ingest、fact、report、delivery 时间语义的公共依赖
- 没有它，所有 A 股运行节奏都不可靠

**是否足够支撑该块需求：**

- **对“交易日历”这一单块需求本身，基本足够**
- 但只覆盖 calendar，不覆盖指数、证券池、板块、公告、新闻等产品输入

#### B. `stock_basic`

**对应产品需求：**

- A 股证券主表 / instrument master
- 标的标准化、名称映射、市场字段、行业字段
- 后续公告/新闻/研报/问答/指标对象与证券主键的 join 基座

**价值：**

- 是 A 股对象层的基本主索引
- 支持 ts_code / symbol / market / industry 等基础映射
- 没有它，后续低频对象难以稳定归属到具体证券

**是否足够支撑该块需求：**

- **对“基础证券主表”这一块，部分足够**
- 但对 iFA 2.0 中国市场整体产品需求远远不够

### 2.4 当前 `daily_light` / `weekly_deep` 的实际含义

当前 daemon 虽然已存在：

- `daily_light`
- `weekly_deep`

但它们当前只是**运行编排分组**，不是“低频覆盖已经完整”的证明。

因为两个 group 当前都只包含：

- `trade_cal`
- `stock_basic`

所以 Job 6 证明的是：

- lowfreq runtime 已经成型
- 但 lowfreq **coverage 还非常窄**

---

## 3. iFA 2.0 China-market lowfreq requirements

基于 `README.md` 与 `docs/architecture.md`，iFA 2.0 中国市场产品不是单纯“定时生成文字”，而是一个面向：

- briefing
- long report
- pre / intraday / post continuity
- evidence-backed professional output

的市场情报系统。

这意味着中国市场 lowfreq 层至少要覆盖下列模块。

### 3.1 市场时钟与对象主表

1. **交易日历**
   - trade calendar
   - 假期/周末/开闭市逻辑

2. **证券基础主表**
   - A-share stock basic
   - 上市/退市/暂停/恢复等基础状态

3. **指数基础表**
   - 宽基指数、行业指数、主题指数基础信息

4. **ETF / LOF / fund 基础表**
   - ETF 基本信息
   - ETF 与指数、主题、行业的映射基底

### 3.2 分类映射与横截面组织层

5. **行业/板块/主题映射**
   - 申万行业
   - 概念板块
   - 行业 / 主题成员关系

6. **证券与指数/ETF/板块的成员关系**
   - 指数成分股
   - 板块成分股
   - ETF 跟踪对象

这是 iFA 2.0 中国市场“讲清楚市场结构”的关键，不属于中频，而是典型低频/慢频资产。

### 3.3 事件与信息源元数据层

7. **公告元数据**
   - 公司公告列表、发布日期、标题、类型、附件链接等

8. **新闻元数据**
   - 市场新闻 / 公司新闻的结构化元数据

9. **政策法规 / 监管动态**
   - 证监会、交易所、国务院、部委层面的规则/政策更新元数据

10. **券商研报元数据**
   - 研报发布时间、机构、评级、目标价、覆盖标的等

11. **董秘问答 / 互动平台问答**
   - 公司 IR / 投资者关系问答元数据

### 3.4 公司基础变化与长期资产层

12. **名称变更 / 上市状态变更 / 新股发行**
13. **高管 / 董监高 / 公司治理基本对象**
14. **股本变动 / 解禁 / 分红送转 / 质押等慢变量**
15. **股东结构 / 十大股东 / 十大流通股东**

### 3.5 财报与慢变量财务层

16. **财务报表元数据 / 指标层**
   - income / balance sheet / cashflow
   - 业绩预告 / 快报
   - 关键财务指标

这些虽然不一定立即进入 Job 8 的最小闭环，但从产品逻辑上看依然属于 lowfreq / slow-moving substrate。

---

## 4. Gap analysis

## 4.1 对问题 A 的直接回答

**结论：当前 lowfreq 体系仅“部分足够”，不足以完整支撑 iFA 2.0 中国市场低频需求。**

### 已覆盖的部分

- 市场日历：有
- A 股基础证券主表：有
- 最小运行体系（runner / version / daemon / health）：有

### 未覆盖的关键部分

- 指数基础表：无
- ETF 基础表：无
- 行业/主题/板块映射：无
- 公告元数据：无
- 新闻元数据：无
- 政策法规：无
- 券商研报：无
- 董秘问答：无
- 公司慢变量（股本/分红/股东/治理等）：无
- 财报/业绩慢变量：无

## 4.2 为什么当前不够

当前 lowfreq 已经能够回答的问题主要是：

- 今天是不是交易日？
- 这个 A 股代码/名称/市场/行业基础信息是什么？

但 iFA 2.0 中国市场要做的是：

- 解释市场结构
- 支撑盘前/盘中/盘后连贯叙事
- 建立“指数-行业-ETF-个股-事件”的结构化背景
- 让后续 facts / signals / briefing blocks 有可复用底座

只靠 `trade_cal + stock_basic`，只能解决“什么时候跑”和“对象叫什么”，不能解决：

- 市场到底由哪些核心指数/ETF/行业结构构成
- 当天热点/政策/公告/研报/问答的低频侧资产沉淀
- 主题、行业、成分关系的长期复用

因此，**当前 lowfreq runtime 是成立的，但 lowfreq coverage 远未完成。**

## 4.3 当前 lowfreq 对 iFA 2.0 的支撑等级

### 足够支撑

- Job runtime / state / version / replay 基础
- A 股 lowfreq 最小技术闭环
- 市场时钟基本语义
- A 股证券主表的基本归一

### 只能部分支撑

- 中国市场 briefing 的对象定位
- 长报告中的结构化市场背景
- A 股标的归属和基础行业字段

### 明显无法支撑

- 板块/主题/指数/ETF 结构叙事
- 公告/新闻/政策/研报/IR 问答类事件面
- 长周期资产沉淀型低频知识底座

---

## 5. Tushare additional lowfreq opportunities

### 5.1 说明

本次 Job 7 先检查了本地 runtime config / env：

- 当前本地 **没有可用 TUSHARE_TOKEN**
- `.env` 不存在
- shell 环境中也未发现 `TUSHARE_TOKEN`

因此本次无法基于真实 token 做“权限实测清单”。

下面的机会盘点是基于：

- 当前中国市场产品需求
- Tushare 常见低频/慢频对象能力面
- 与 iFA 2.0 lowfreq substrate 的适配度

所以这是**规划层候选清单**，不是“已实测权限可用清单”。

### 5.2 Layer 1 — iFA 2.0 当前必需

这些对象如果不补，iFA 2.0 中国市场 lowfreq 层就仍然明显不完整。

#### 1. `index_basic`
- **用途**：指数基础主表
- **价值**：建立宽基 / 行业 / 主题指数对象层
- **为什么必需**：没有指数主表，就缺少中国市场结构化叙事主轴

#### 2. `fund_basic`（优先 ETF / LOF 维度）
- **用途**：ETF / 场内基金基础对象
- **价值**：把“主题表达”和“可交易篮子”接入底座
- **为什么必需**：iFA 2.0 中国市场若要解释热点/风格/板块，ETF 是高价值桥梁

#### 3. 行业/板块映射对象（优先申万 / 概念成员关系）
- **候选方向**：`index_member` / `concept` / `concept_detail` / 行业分类映射能力
- **用途**：建立个股 ↔ 行业 / 主题 / 板块关系
- **为什么必需**：没有它，2.0 中国市场无法稳定输出“哪个板块、哪些成分、谁在带动”

#### 4. 公告元数据
- **候选方向**：公告/披露列表类接口
- **用途**：低频事件主源之一
- **为什么必需**：A 股市场专业输出离不开公告证据层

#### 5. 新闻元数据
- **候选方向**：新闻快讯 / 公司新闻 / 市场新闻元数据
- **用途**：支持 briefing 与 long report 的事件层输入
- **为什么必需**：没有新闻元数据，事件侧 substrate 不完整

#### 6. 研报元数据
- **候选方向**：券商研报列表 / 评级 / 目标价元数据
- **用途**：机构视角沉淀
- **为什么必需**：对长报告与板块/个股背景解释有明显增益

#### 7. 董秘问答 / IR 问答元数据
- **用途**：公司层面的管理层表述与问答证据
- **为什么必需**：对中国市场公司事件理解有真实价值，且属于慢频资产

### 5.3 Layer 2 — iFA 2.0 增强型

这些对象不是 2.0 启动最小集，但补齐后会显著增强产品质量。

#### 1. `namechange`
- 名称变更历史
- 适合提升历史连续性与对象稳定性

#### 2. `new_share`
- 新股发行 / 新上市元数据
- 提升市场结构变化感知

#### 3. `stk_managers`
- 董监高 / 管理层对象
- 支持公司治理层低频资产沉淀

#### 4. `dividend`
- 分红送转
- 适合做长期公司画像与事件补充

#### 5. `share_float` / `share_change`
- 股本变化 / 解禁 / 流通变化
- 适合增强个股中长期背景解释

#### 6. `top10_holders` / `top10_floatholders`
- 股东结构变化
- 对重要公司长期画像与资金结构解释有价值

#### 7. `pledge_stat` / `pledge_detail`
- 股权质押慢变量
- 提升风险背景层

#### 8. `forecast` / `express`
- 业绩预告 / 业绩快报
- 属于典型财报季慢变量增强层

### 5.4 Layer 3 — 未来资产型沉淀

这些对象短期未必直接进入 2.0 报告，但值得纳入 iFA 的长期数据资产底座。

#### 1. 财务报表全量层
- `income`
- `balancesheet`
- `cashflow`
- `fina_indicator`

#### 2. 沪深港通 / 持仓慢变量
- `hk_hold`
- `moneyflow_hsgt`
- `ggt_daily`

#### 3. 融资融券慢变量
- `margin`
- `margin_detail`

#### 4. 指数权重 / 成分权重
- `index_weight`
- 适合做市场结构演化资产

#### 5. 可转债 / 债券 / 衍生品基础主表
- `cb_basic`
- `bond_basic`
- `fut_basic`
- `opt_basic`

#### 6. 停复牌 / 交易状态慢变量
- `suspend` / 相关状态类对象

这些对象对未来：

- 2.1 watchlist intelligence
- 2.2 holdings intelligence
- 3.x strategy intelligence

都会产生复利价值。

---

## 6. Priority tiers

## P0 — must-have for iFA 2.0

这部分是建议 Job 8 优先处理的范围。

1. `index_basic`
2. `fund_basic`（优先 ETF）
3. 行业 / 板块 / 主题映射（优先申万/概念成员关系）
4. 公告元数据
5. 新闻元数据
6. 券商研报元数据
7. 董秘问答 / IR 问答元数据

### P0 的核心逻辑

P0 不是为了“多抓点数据”，而是为了补齐 2.0 中国市场最关键的 lowfreq substrate 空洞：

- **市场结构对象层**：指数、ETF、行业、主题
- **事件元数据层**：公告、新闻、研报、IR 问答

这两块不补，2.0 中国市场就只能停留在“交易日历 + 证券主表”的初级状态。

## P1 — strong enhancement

1. `namechange`
2. `new_share`
3. `stk_managers`
4. `dividend`
5. `share_float` / `share_change`
6. `top10_holders` / `top10_floatholders`
7. `pledge_*`
8. `forecast` / `express`

## P2 — long-term asset

1. 财务报表与关键财务指标
2. 港股通 / 北向 / 南向慢变量
3. 融资融券慢变量
4. 指数权重 / ETF 追踪结构
5. 可转债 / 债券 / 期货 / 期权基础对象
6. 交易状态慢变量（停复牌等）

---

## 7. Recommended next jobs

## Job 8 should do what

**Job 8 应聚焦“P0 的结构对象层 + 最小事件元数据层”，而不是一下子全铺开。**

建议 Job 8 范围：

1. 新增并打通 **指数基础表**
2. 新增并打通 **ETF / fund 基础表**
3. 新增并打通 **行业/主题/板块映射**（至少一条稳定主线）
4. 新增并打通 **公告元数据**
5. 保持与现有 lowfreq framework 一致：
   - registry
   - runner
   - raw persistence
   - canonical current
   - version/history（按需要最小化）
   - daemon group 纳入策略

### Job 8 的目标状态

Job 8 完成后，lowfreq 应能回答：

- 市场有哪些核心指数 / ETF / 板块对象
- 个股属于哪些结构篮子
- 当天/近期有哪些公司公告进入底座

## Job 9 should do what

**Job 9 应聚焦“P0 事件面扩展 + P1 慢变量增强”。**

建议 Job 9 范围：

1. 新闻元数据
2. 研报元数据
3. 董秘问答 / IR 问答
4. 名称变更 / 新股 / 管理层 / 分红 / 股本变化等慢变量中挑 2–4 个高价值对象
5. 补 daemon group 语义，使：
   - `daily_light` 承担日常元数据刷新
   - `weekly_deep` 承担较重的结构对象/慢变量刷新

### Job 9 的目标状态

Job 9 完成后，lowfreq 中国市场底座应能形成：

- 结构对象层
- 事件元数据层
- 基础慢变量层

从而为后续 facts/signals / briefing / report assembly 提供更像“产品底座”的输入，而不只是技术 demo。

---

## 8. Non-goals / what not to do now

本次 Job 7 明确不做：

- 不大规模开发新 dataset
- 不改 daemon 主体架构
- 不直接做 facts/signals
- 不做 report/delivery
- 不直接进入中频层
- 不在没有 token 的情况下伪造权限验证结果

本次只做：

- 覆盖盘点
- 产品对照
- gap 梳理
- P0/P1/P2 分层
- Job 8 / Job 9 的建议拆分

---

## 9. Final conclusion

### 问题 A：当前 lowfreq 是否已经足够支撑 iFA 2.0 中国市场低频需求？

**结论：部分足够，但明显不完整。**

- runtime / daemon / version 机制：已经基本成立
- 数据 coverage：当前只有 `trade_cal` + `stock_basic`
- 因此只能支撑最小的“市场时钟 + 证券主表”能力
- 还不足以完整支撑 iFA 2.0 中国市场的结构化市场情报产品定义

### 问题 B：最应该优先补什么？

#### 2.0 现在就必须补齐（优先顺序建议）

1. 指数基础表
2. ETF / fund 基础表
3. 行业 / 板块 / 主题映射
4. 公告元数据
5. 新闻元数据
6. 券商研报元数据
7. 董秘问答 / IR 问答元数据

#### 虽然 2.0 不一定立刻全用，但值得沉淀为 iFA 长期资产

1. 名称变更 / 新股 / 管理层对象
2. 股本变化 / 分红 / 解禁 / 质押
3. 十大股东 / 十大流通股东
4. 财务报表 / 财务指标 / 业绩预告 / 快报
5. 港股通 / 北向 / 南向 / 融资融券慢变量
6. 指数权重 / ETF 跟踪结构
7. 可转债 / 债券 / 衍生品基础主表

### Job 7 产出判断

本规划已经把：

- 当前已实现 lowfreq scope
- iFA 2.0 中国市场 lowfreq requirements
- 关键 gap
- Tushare lowfreq 候选分层
- Job 8 / Job 9 的拆分边界

盘清楚到可以直接作为下一阶段工作的 planning baseline。

### 当前唯一 blocker

**缺本地可用 Tushare token，无法对“当前账号权限可访问的额外低频接口”做真实权限验证。**

在 token 补齐前，Job 8 / Job 9 仍可先做：

- 数据模型设计
- dataset 清单冻结
- registry / persistence / migration 设计

但一旦进入真实接入阶段，必须先补凭证并做权限实测。 
