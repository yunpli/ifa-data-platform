# IFA_MID_FREQUENCY_DESIGN.md

> 强制规则：每次新 session 处理 iFA 中频相关工作前，先读取 `IFA_PROJECT_CONTEXT.md`、`IFA_MID_HIGH_PLAN.md`、再读取本文件。

## 1. 文档目标

本文件用于把 iFA 中频从“模糊概念”固化为“完整可执行的系统设计”。

本文件覆盖：
- 中频定义
- 中频 dataset 分类
- 中频与低频/高频的边界
- 中频 daemon / 调度设计
- 中频 DB / version / state / summary 设计
- transport / connection / rate limit / retry 设计
- watchdog / 健康恢复设计
- B2 / B3 / B4 / B5 job 拆分

本文件不做：
- 不写实现代码
- 不接入新 dataset
- 不修改 lowfreq / daemon 现有逻辑

---

## 2. 中频定义

### 2.1 中频不是什么

- 中频 ≠ 低频
- 中频 ≠ 高频
- 中频 ≠ 实时行情系统
- 中频 ≠ 盘中无限轮询系统
- 中频 ≠ 另一个独立 ingestion/runtime 产品

### 2.2 中频是什么

iFA 中频是：

> 面向 `B` 类 Universe，在交易日内按固定窗口多次刷新、为日报体系（2.0 报告）提供稳定结构化数据的生产层。

它的核心特征：
- 服务对象：`B` 类 Universe
- 更新频率：日内多次，但不是 tick 级/实时
- 输出目标：服务日报生成与盘中状态理解
- 运行要求：必须在报告生成前稳定、冻结、可追溯
- 架构要求：完全继承 lowfreq 既有框架，不另起炉灶

### 2.3 中频的典型更新频率

中频不是单一窗口，而是“预热 + 正式收口”双阶段窗口体系。

建议固定为以下窗口：

1. **清晨预热（prewarm_early）**
   - 时间建议：`07:20–07:50` Asia/Shanghai
   - 用途：连接预热、provider 健康检查、前序缓存加载、基础状态刷新

2. **盘前收口（pre_open_final）**
   - 时间建议：`08:35–09:00` Asia/Shanghai
   - 用途：盘前最终补漏与一致性确认，形成盘前稳定快照

3. **午间预热（midday_prewarm）**
   - 时间建议：`11:20–11:40` Asia/Shanghai
   - 用途：预取半日窗口所需数据、检查上半场运行态、准备午间收口

4. **午间收口（midday_final）**
   - 时间建议：`11:45–12:05` Asia/Shanghai
   - 用途：午间最终补漏与一致性确认，形成半日稳定快照

5. **收盘后预热（post_close_prewarm）**
   - 时间建议：`15:05–15:20` Asia/Shanghai
   - 用途：为收盘后主窗口做连接预热、任务排队、轻量预取

6. **收盘后收口（post_close_final）**
   - 时间建议：`15:20–15:55` Asia/Shanghai
   - 用途：生成日报前主数据稳定版，完成补漏、校验与最终一致性确认

7. **晚间补齐（night_settlement，可选）**
   - 时间建议：`20:30–21:30`
   - 用途：晚到数据补齐、轻量回补、健康修复，不作为日报生成中的主路径

设计原则：
- 预热窗口负责连接准备、轻量预取、健康检查、状态刷新
- 正式收口窗口负责补漏、最终一致性确认、冻结快照生成
- 正式窗口应偏轻，不承担重型全量刷新
- 日报必须读取窗口结束后冻结的数据快照

### 2.4 中频与日报生成时间的关系

中频必须服从“**先预热，后收口，冻结快照，再生成报告**”的顺序。

建议关系：
- `pre_open_final` → 服务盘前快照或晨间状态说明
- `midday_final` → 服务午间/半日状态判断
- `post_close_final` → 作为 **日报主数据源**

强制约束：
- 报告生成开始前，相关中频 final 窗口必须已完成并进入稳定状态
- 报告生成过程中，不允许同一批中频 dataset 继续写入 current
- 必须有“数据冻结点（freeze point）”或“run-complete snapshot”供报告读取
- **日报生成必须基于窗口结束后冻结的数据快照**，而不是读取仍在变化的 current 写入过程

推荐顺序：
1. `post_close_prewarm` 完成预热
2. `post_close_final` 完成收口
3. summary / health 校验通过
4. 生成冻结数据快照 / 确认 active 版本稳定
5. 报告读取该冻结快照
6. 开始日报生成

### 2.5 为什么这些数据属于中频而不是低频或高频

这些数据属于中频，因为它们同时满足：
- 需要在交易日内多次刷新
- 但不需要秒级/毫秒级实时性
- 要服务日报与结构化市场观察
- 在报告前必须稳定，而不是流式不停变化
- 即使非交易日/周末也需要轻量运行，以完成预热、补漏、健康检查与状态刷新

与低频的区别：
- 低频主要服务慢变量、基础表、公告/文档/资产层，不强调日内多轮刷新
- 中频强调“交易日内多窗口稳定刷新 + 非交易日轻量维护”

与高频的区别：
- 高频强调 A 类 Universe、强资源约束、更细颗粒度、更高刷新频率
- 中频不做实时逐笔或全日持续流式处理

---

## 3. 中频 dataset 统一分类

以下是中频第一版统一定义。此处追求“统一可执行”，不是一次性穷尽全部正确答案。

## 3.1 行情类（核心）

### 定义
面向 B Universe 的价格、成交、指数、ETF 等市场状态数据，是中频系统的主干。

### 建议 dataset
1. `equity_daily_bar`
   - A 股个股日线 OHLCV
   - 用于日报主行情框架、涨跌幅、成交额、量比基础

2. `equity_intraday_bar`
   - 个股分钟级聚合（可选，建议 5m / 15m，而不是 1m 起步）
   - 用于午间与收盘后结构分析

3. `index_daily_bar`
   - 宽基/风格/核心指数日线
   - 用于市场主线与风格判断

4. `index_intraday_bar`
   - 指数日内聚合行情
   - 用于盘中强弱、午间趋势判断

5. `etf_daily_bar`
   - 核心 ETF 日线
   - 用于主题与风险偏好代理

6. `etf_intraday_bar`
   - ETF 日内聚合行情
   - 用于板块轮动与主题热度识别

### 为什么属于中频
- 交易日内多次刷新有意义
- 但不需要 tick 级实时
- 直接服务日报 2.0 的盘前/午间/收盘后分析

---

## 3.2 资金类

### 定义
反映资金方向、杠杆变化、市场增量/减量流向的数据。

### 建议 dataset
1. `northbound_flow`
   - 北向资金净流入/流出
   - 支持指数、板块、重点股票层解释

2. `main_force_flow`
   - 主力资金方向（如可获得）
   - 用于结构轮动与热点强化解释

3. `margin_financing_balance`
   - 融资融券余额 / 变化
   - 用于杠杆风险偏好观察

4. `etf_fund_flow`
   - ETF 资金流（若源可得）
   - 用于主题风险偏好与资金承接判断

### 为什么属于中频
- 通常交易日内或收盘后更新即可
- 对日报非常关键，但不需要高频实时流

---

## 3.3 结构类

### 定义
反映市场微观结构、情绪层、交易特征层的数据。

### 建议 dataset
1. `limit_up_down_status`
   - 涨停/跌停家数、连板、炸板等
   - 用于情绪热度与强弱结构

2. `dragon_tiger_list`
   - 龙虎榜
   - 用于强势股与异常成交解释

3. `turnover_structure`
   - 成交额分布、放量/缩量、换手结构
   - 用于活跃度与风格判断

4. `market_breadth`
   - 涨跌家数、创新高/新低、中位数收益等
   - 用于市场宽度判断

### 为什么属于中频
- 结构层数据在日内阶段性更新就足够
- 是日报核心解释层，但不是低频慢变量，也不是高频流式行情

---

## 3.4 板块 / 行业动态

### 定义
反映行业、主题、概念板块层面的轮动、强弱与扩散状态。

### 建议 dataset
1. `sector_daily_performance`
   - 板块日线表现

2. `sector_intraday_performance`
   - 板块日内表现

3. `industry_rotation_state`
   - 行业轮动状态、排名变化、持续性

4. `theme_leadership_board`
   - 主题热点与领涨映射

### 为什么属于中频
- 板块轮动本质上是“日内阶段性变化”，最适合中频窗口
- 直接服务日报的主题归因与结构解释

---

## 3.5 第一批中频实现优先级建议

B4 第一批 dataset 建议按以下优先级：

### P0（必须先做）
- `equity_daily_bar`
- `index_daily_bar`
- `etf_daily_bar`
- `northbound_flow`
- `limit_up_down_status`
- `sector_daily_performance`

### P1（第二层）
- `equity_intraday_bar`（优先 5m/15m）
- `index_intraday_bar`
- `sector_intraday_performance`
- `market_breadth`
- `margin_financing_balance`

### P2（后续增强）
- `dragon_tiger_list`
- `main_force_flow`
- `etf_fund_flow`
- `turnover_structure`
- `theme_leadership_board`

---

## 4. 中频必须完全复用低频架构

中频不是另一个系统，而是 lowfreq 框架在更快节奏上的继承层。

### 4.1 必须复用的能力

中频完全复用：
- `symbol_universe`（使用 `B`）
- raw / source mirror
- canonical current
- history / version
- `dataset_versions`
- daemon / state
- summary / report

### 4.2 继承原则

中频只允许做：
- 新增中频 dataset 定义
- 新增中频调度窗口与运行编排
- 新增中频 summary / health 视图
- 在同一 DB / schema / version 语义下扩展

中频不允许做：
- 新建第二套 schema 语义
- 新建另一套 version 模型
- 绕过 `dataset_versions`
- 新建与 lowfreq 不兼容的 daemon/state 框架
- 回到全市场抓取

### 4.3 Universe 边界

- lowfreq → 读 `C`
- midfreq → 读 `B`
- highfreq → 读 `A`

强制关系：
- `A ⊂ B ⊂ C`

---

## 5. 中频 daemon 设计

## 5.1 设计原则

中频 daemon 必须：
- 与 lowfreq daemon **分开运行**
- 单独调度
- 不共享执行窗口
- 但复用同一套 daemon/state 设计范式

### 设计结论

应采用：
- **独立 midfreq daemon 进程**
- **共享统一框架抽象**
- **独立 midfreq group/window**
- **独立 midfreq 状态记录键**

即：
- 不是“低频 daemon 里塞更多窗口”
- 也不是“再造一个完全独立系统”
- 而是“同架构、分 daemon、分窗口、分状态域”

## 5.2 daemon 运行形态

建议中频 daemon 主入口语义：
- `midfreq.daemon --once`
- `midfreq.daemon --loop`
- `midfreq.daemon --group <group>`
- `midfreq.daemon --health`

此处是设计语义，不代表本次实现。

## 5.3 中频 group 设计

建议中频分为以下 groups：

1. `prewarm_early`
   - 清晨预热组
   - 重点：连接预热、provider 健康检查、缓存预热、轻量状态刷新

2. `pre_open_final`
   - 盘前收口组
   - 重点：前日收盘稳定版补漏、基础指数/ETF/板块状态最终确认

3. `midday_prewarm`
   - 午间预热组
   - 重点：半日数据预取、运行态检查、午间窗口准备

4. `midday_final`
   - 午间收口组
   - 重点：半日行情、半日资金、板块轮动、市场宽度最终确认

5. `post_close_prewarm`
   - 收盘后预热组
   - 重点：轻量预取、任务排队、连接与资源预热

6. `post_close_final`
   - 收盘后主收口组
   - 重点：日报主数据补漏、校验、最终一致性确认

7. `night_settlement`（可选）
   - 晚间补齐 / 晚到数据修复组
   - 重点：补漏、轻量回补、健康修复

设计要求：
- prewarm 组偏轻，负责准备与健康
- final 组偏轻，负责最终一致性确认与冻结，不承担重型全量
- 报告依赖的正式窗口必须是 final 组，而不是 prewarm 组

## 5.4 中频与 lowfreq daemon 的关系

- 进程分开
- 调度分开
- 执行窗口分开
- 健康检查逻辑可共享
- state 模式可共享
- summary 结构可共享

强制规则：
- 不允许 lowfreq 与 midfreq 在同一窗口争用同一批 dataset
- 不允许日报生成时 midfreq 还在改同一份 current

---

## 6. 执行时间设计

## 6.1 推荐时间窗口

### prewarm_early
- 时间：`07:20–07:50` Asia/Shanghai
- 截止：`08:00` 前结束
- 用途：清晨预热、连接检查、缓存预装载、健康状态刷新

### pre_open_final
- 时间：`08:35–09:00`
- 截止：`09:05` 前结束
- 用途：盘前最终补漏与一致性确认

### midday_prewarm
- 时间：`11:20–11:40`
- 截止：`11:45` 前结束
- 用途：午间窗口预热、预取、状态检查

### midday_final
- 时间：`11:45–12:05`
- 截止：`12:10` 前结束
- 用途：午间最终补漏与稳定快照形成

### post_close_prewarm
- 时间：`15:05–15:20`
- 截止：`15:20` 前结束
- 用途：收盘后主窗口前预热

### post_close_final
- 时间：`15:20–15:55`
- 截止：`16:00` 前结束
- 用途：日报主数据准备、补漏、最终一致性确认、冻结快照形成

### night_settlement（可选）
- 时间：`20:30–21:30`
- 截止：`21:40` 前结束
- 用途：少量补齐、轻量回补、健康修复，不作为日报主依赖

### 非交易日 / 周末策略
- 中频在非交易日/周末也应运行，但降级为**轻量模式**
- 轻量模式只做：
  - 预热
  - 补漏
  - 健康检查
  - 状态刷新
  - 晚到数据校验
- 非交易日 / 周末不做：
  - 重型全量刷新
  - 大范围历史重算
  - 高成本批量回灌

## 6.2 与报告生成避冲突原则

建议日报时间关系：
- 中频 `post_close_final` 结束 + summary 校验通过 + 冻结快照确认
- 再触发日报

强制要求：
- 不允许报告生成期间更新它所依赖的中频 current 表
- 报告应读取“本轮已完成且已冻结”的 current / active snapshot
- 如使用 `night_settlement`，补算结果默认不回写已开始生成的日报批次
- 正式窗口应偏轻，只做补漏与最终一致性确认，不承担重型全量

## 6.3 为什么这样安排

- `prewarm_early`：先把连接、缓存、健康状态准备好
- `pre_open_final`：盘前收口，避免接近开盘仍大规模写入
- `midday_prewarm` + `midday_final`：把预取与收口拆开，降低午间主窗口压力
- `post_close_prewarm` + `post_close_final`：保障日报前最后一轮数据稳定，不与报告生成冲突
- `night_settlement`：只做补齐，不打乱主流程
- 非交易日轻量运行：保证中频系统不停摆，但控制资源成本

---

## 7. 数据库与 version 设计

## 7.1 是否复用现有 DB / schema

结论：**复用现有 DB 与 schema**。

- 数据库：`ifa_db`
- schema：`ifa2`

不建议：
- 新增 schema
- 新增另一套独立 version 系统

## 7.2 表设计原则

新中频 dataset 继续采用：
- `*_current`
- `*_history`
- `dataset_versions`
- `midfreq_runs` 或统一运行表扩展（需在 B3 定版）
- `midfreq_daemon_state` / `midfreq_group_state` 或统一 state 扩展（需在 B3 定版）

### 推荐优先方案

推荐优先方案：
- 数据表层继续沿用 `current/history/version`
- 运行态层允许在同 schema 下新增 **midfreq 专属 state 表**
- 但字段语义、状态机、summary 结构与 lowfreq 保持兼容

即：
- **数据层共享语义**
- **运行层分 daemon 域**
- **不分裂架构**

## 7.3 version 是否继续复用

结论：**继续复用 current/history/version 与 `dataset_versions` 机制**。

原因：
- 报告需要稳定版本
- 需要版本可追溯
- 需要与 lowfreq 保持统一查询习惯
- 避免中频再造一套“临时缓存 + 覆盖写”系统

### 继承 lowfreq version 原则

中频必须继承 lowfreq 的 version 原则：
- **内容无变化时，不新建 version**
- 若本轮检查成功但内容未变化，只记录：
  - 本轮 run 成功
  - `checked_at`
  - 必要的 freshness / summary 状态
- 只有当内容发生真实变化并通过 promote 条件时，才创建新 version 并更新 active/current

这样做的目的：
- 避免 version 噪音膨胀
- 保持 history 的语义纯净
- 让“本轮成功检查”与“本轮产生新内容”区分开来

## 7.4 命名约束

中频 dataset 推荐显式命名含义，而不是再造抽象黑箱。例如：
- `equity_daily_bar_current`
- `equity_daily_bar_history`
- `sector_intraday_performance_current`

命名要求：
- 语义清晰
- 频率可感知
- 不与 lowfreq 现有 dataset 冲突

---

## 8. transport / connection / rate limit / retry 设计

## 8.1 总原则

必须避免：
- 每个 dataset 自己建立 transport
- 每个 dataset 自己乱控并发
- 全串行导致慢到不可用
- 并发爆炸导致 API 限流/封禁

## 8.2 transport 复用结论

结论：**复用低频已有的 Tushare transport 能力与 provider adaptor 设计**。

中频不应新增另一套 provider client。

应复用：
- 统一 provider adaptor
- 统一认证/token 注入
- 统一 request 包装
- 统一 retry / backoff / error 分类

## 8.3 connection pool 策略

建议：
- 共享 provider 级连接池/会话池
- 以 daemon 进程为单位持有 transport
- dataset runner 不直接 new client，而是从 transport manager 获取连接

即：
- **共享连接池**
- **共享 session**
- **按 source 分池**
- **按 daemon 生命周期管理**

## 8.4 并发策略

建议采用“**小规模、分层并发**”：

1. **group 内串行、dataset 内有限并发**
   - 先按 group 串行推进，避免窗口内过多竞争
   - 每个 dataset 自身可有有限 fan-out

2. **B Universe 分片执行**
   - 按 symbol batch 分片
   - 控制单批 symbol 数量

3. **默认并发上限保守**
   - 初期建议 source 级并发 `2–4`
   - dataset 内 fan-out `2–8`，视 API 能力调整

4. **重型与轻型 dataset 分层**
   - `pre_open` 放轻型
   - `midday` 控制中等负载
   - `post_close` 容纳主负载

## 8.5 rate limiting

必须统一到 transport 层，而不是 dataset 各自实现。

建议机制：
- provider 级令牌桶 / 漏桶
- endpoint 级 QPS 配额
- per-dataset 预算配置
- window 内全局速率上限

预算维度建议：
- requests per minute
- symbols per batch
- max concurrency
- max runtime seconds

## 8.6 retry / backoff

建议：
- 幂等读取请求允许自动 retry
- 使用指数退避 + jitter
- 可区分：网络错误 / 限流错误 / 参数错误 / 数据为空

规则建议：
- transient error → retry
- rate limit / 429 → 更长 backoff + 降低并发
- permanent schema / parameter error → 直接 fail 并记录
- 单 symbol 错误不应拖垮整个 dataset，允许局部失败汇总

## 8.7 关键工程结论

中频 transport 必须是：
- 统一 client
- 统一 pool
- 统一 limiter
- 统一 retry
- 统一 metrics

而不是 dataset 私自管理网络栈。

---

## 9. summary 设计

中频必须有类似 lowfreq 的正式 summary。

## 9.1 summary 最低字段要求

每轮 summary 至少包含：
- daemon 名称
- group 名称
- window 时间
- 开始时间 / 结束时间
- 本轮运行的 dataset 列表
- 每个 dataset 的成功 / 失败
- records 写入量 / 变化量
- version / run id
- 总体状态
- 异常摘要

## 9.2 summary 载体

允许两种并存：

1. **DB summary 表 / run state 表**
   - 用于查询、健康检查、调度联动

2. **文件 summary（Markdown / JSON）**
   - 用于开发者查看、日报前核查、审计留痕

推荐：
- DB 做主状态源
- 文件做人类可读摘要

## 9.3 summary 的作用

- 报告前确认本轮数据是否稳定
- 快速知道哪些 dataset 成功/失败
- 快速知道本轮变更量是否异常
- 记录哪些 dataset 只是 checked 而未生成新 version
- 为 watchdog / 健康诊断提供基础输入

---

## 10. watchdog / 健康机制

## 10.1 daemon 挂了怎么办

必须有明确机制：
- 检测 daemon 最近 heartbeat / loop 时间
- 若超过阈值未更新，则判定 unhealthy
- 由宿主进程或调度器负责拉起

## 10.2 如何检测不健康

建议不健康判定至少包含：
- daemon 超过阈值未 heartbeat
- 关键 group 连续失败
- 关键 dataset 连续失败
- summary 缺失
- 窗口应跑未跑
- records 变化异常（例如长期为 0）

## 10.3 是否自动重启

结论：**允许自动重启，但必须由宿主层完成**。

即：
- daemon 自己不做复杂自我守护
- 由 launchd / systemd / supervisor / cron wrapper 管理拉起

## 10.4 与低频是否共享逻辑

结论：**共享健康逻辑范式，但分 daemon 监控对象**。

共享内容：
- heartbeat 语义
- group health 规则
- dataset freshness 规则
- summary 校验模式

分离内容：
- midfreq daemon 名称
- midfreq group 窗口
- midfreq SLA 与超时阈值

## 10.5 推荐健康等级

建议健康等级：
- `healthy`
- `degraded`
- `stalled`
- `failed`

定义示例：
- `healthy`：全部关键 dataset 成功
- `degraded`：少量非关键失败，但日报仍可生成
- `stalled`：窗口应执行但未完成
- `failed`：关键 dataset 缺失，日报不应继续

---

## 11. Job 拆分（B2 / B3 / B4 / B5）

## B2：中频需求定义

### 目标
- 明确中频的业务职责、时间特征、Universe 范围、数据分类与优先级

### 边界
- 只做需求定义
- 不写代码
- 不接入新 dataset

### 输入
- `IFA_PROJECT_CONTEXT.md`
- `IFA_MID_HIGH_PLAN.md`
- lowfreq 既有架构与运行经验

### 输出
- 中频定义文档
- 中频 dataset 分类清单
- 中频时间窗口与报告关系说明

### 验收标准
- 明确中频只面向 `B`
- 明确中频不是低频也不是高频
- 明确中频服务日报体系
- 明确第一批 dataset 优先级

### 非目标
- 不实现 dataset
- 不修改 DB
- 不修改 daemon

---

## B3：中频架构设计

### 目标
- 设计中频 daemon、transport、DB/version/state/summary/watchdog 的完整方案

### 边界
- 只做设计
- 复用低频架构
- 不另起新系统

### 输入
- B2 输出
- lowfreq framework / version / daemon / state 现状

### 输出
- 中频 daemon 设计
- DB / state / summary / health 设计
- transport / pool / rate limit / retry 设计

### 验收标准
- 明确中频 daemon 与 lowfreq daemon 的关系
- 明确 current/history/version 是否复用
- 明确 transport 与并发控制策略
- 明确 watchdog 与健康恢复方式

### 非目标
- 不写实现代码
- 不落任何新 dataset
- 不进入高频设计实现

---

## B4：中频第一批 dataset 实现

### 目标
- 在 B Universe 上实现第一批最小中频 dataset
- 建立可跑通的中频主链路

### 边界
- 只做第一批最小集
- 严格限定在 B Universe
- 不做高频

### 输入
- B2 的需求定义
- B3 的系统设计

### 输出
- 第一批 dataset 代码/配置/文档
- 中频 daemon 最小运行链路
- current/history/version 正式接通

### 验收标准
- 第一批 dataset 可稳定 ingest
- 能产出 summary
- 能查健康状态
- 不破坏 lowfreq 稳定性

### 非目标
- 不一次性做完整中频全集
- 不做实时流系统
- 不做策略/信号层

---

## B5：中频运行与验收

### 目标
- 把中频从“能跑”收成“可运行、可维护、可验收”

### 边界
- 聚焦运行与收口
- 不继续扩 dataset 面

### 输入
- B4 的第一批实现结果
- lowfreq 运维经验

### 输出
- 中频 operations guide
- summary / runbook / health / recovery 文档
- 验收记录

### 验收标准
- 可启动 / 可停止 / 可查状态 / 可恢复
- 有 watchdog / summary / health 机制
- 日报生成前可验证数据稳定

### 非目标
- 不进入高频实现
- 不扩第二批 dataset
- 不做策略层

---

## 12. 中频与低频协同原则

### 12.1 协同方式

- lowfreq 提供慢变量、基础表、公告/资产层底座
- midfreq 提供日内多窗口的市场状态层
- 报告层统一从稳定版 current/version 读取

### 12.2 不允许的协同方式

- 不允许 midfreq 绕过 lowfreq 基础表
- 不允许 midfreq 独立维护另一套 symbol universe
- 不允许 midfreq 在报告执行时持续改写主读取表

### 12.3 推荐读取顺序

日报系统推荐读取：
1. lowfreq 稳态底座
2. midfreq post-close 稳定版
3. 再进行报告生成

---

## 13. 当前结论

中频在 iFA 中的正确定位是：

> 一个面向 `B` Universe、在交易日内按固定窗口多次刷新、为日报体系提供稳定结构化市场状态的生产层。

它必须：
- 不是实时系统
- 不是低频慢变量层
- 不是高频持仓层
- 必须复用 lowfreq 架构
- 必须独立 daemon 调度
- 必须在报告前稳定冻结
- 必须有 summary / state / watchdog / health

---

## 14. 一句话目标

把中频从“模糊概念”收成“可设计、可实现、可运维、可验收”的统一生产层设计。 
