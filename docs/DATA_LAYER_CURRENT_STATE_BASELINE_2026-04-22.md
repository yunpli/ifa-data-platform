# Data Layer 当前状态基线（2026-04-22）

> 面向：Yunpeng / 产品 / 业务规划
> 
> 口径：这份文档不是“理想架构图”，而是基于当前仓库代码、脚本、调度定义、轻量 DB 抽样、以及本机运行进程看到的**现实状态**。

---

## 一、先说结论：data layer 现在已经不是空壳，但也还没到“业务随便拿来就用”的成熟度

如果用一句话概括现在的数据层：

**底层采集、运行时调度、归档层、回放证据链，这四件事都已经有实物；其中 lowfreq / midfreq / Archive V2 已经能支撑部分业务交付，高freq 和 replay 更像是“能力底座已搭好，但产品化还差最后一层”。**

更直白一点：

- **已经能用来支撑业务的部分**：
  - 慢频基础资料与业务文本采集（公告、新闻、研报、问答等）
  - 收盘后 daily-final 类数据（龙虎榜、涨停细节、板块表现、日线条目等）
  - Archive V2 的 nightly daily/final 归档层
- **还不适合被当成稳定产品承诺的部分**：
  - 高频盘中 working/state 层
  - slot replay / 回放证据层
  - 统一 runtime 的“唯一生产入口”这件事，虽然已经运行起来，但现场仍有旧 daemon 共存，治理还没完全收口

所以现在的 data layer，已经不是“缺功能”，而是进入了一个更现实的阶段：

**真正的短板不是能不能采，而是“哪些已经是业务可依赖真相、哪些还只是底层技术能力”必须讲清楚。**

---

## 二、data layer 现在已经有什么

从仓库结构上看，当前 repo 已经形成了比较清楚的四层：

1. **lowfreq**：慢频/基础/reference 采集层
2. **midfreq**：日内较慢、但接近收盘后稳定事实的 daily-final 采集层
3. **highfreq**：盘中 working/state 快照层
4. **archive_v2**：归档后的“最终真相层”

同时外面包了一层：

5. **runtime / unified_daemon**：统一调度与运行治理层
6. **replay evidence**：针对 early / mid / late 三个业务时段的回放证据层

也就是说，现在不是“只有采集脚本”，而是已经有：

- 采集 registry
- 调度策略
- 统一 daemon
- DB 中的 history/current/working/archive_v2 四类表
- repair queue / completeness / operator CLI
- slot replay evidence 结构

这套东西的价值在于：

**它已经开始从“采到数据”走向“知道自己采了什么、什么时候采的、能不能补、能不能解释”。**

---

## 三、采集脚本大致有哪些、各自负责什么

这里不按每个零散脚本逐个罗列，而按“真正承担生产意义”的脚本/入口来讲。

### 1）统一运行时与调度入口

核心入口：

- `src/ifa_data_platform/runtime/unified_daemon.py`
- `scripts/unified_daemon_service.sh`
- `scripts/runtime_manifest_cli.py`

它们负责：

- 统一 lowfreq / midfreq / highfreq / archive_v2 的调度入口
- 将 schedule policy 落到 DB 表 `runtime_worker_schedules`
- 管理 `runtime_worker_state`
- 记录 `unified_runtime_runs`
- 做 overlap / timeout / governance 这类运行治理
- 在部分 schedule 触发后自动写 replay evidence

**现实状态判断**：这已经不是 demo CLI 了，而是实打实的运行时控制层。

### 2）lowfreq 采集层

代表代码：

- `src/ifa_data_platform/lowfreq/registry.py`
- `scripts/register_datasets.py`
- `scripts/trade_calendar_maintenance.py`
- `scripts/run_lowfreq_daemon.sh`

它负责：

- 交易日历、股票基础资料、ETF/指数基础资料
- 公告、新闻、研报、投资者问答
- 各类 reference / reference+history 型数据

当前 lowfreq 可执行 registry 数量约 **66**，但这里面混有不少 test/demo dataset。真正可视为 accepted production scope 的，是公告、新闻、研报、问答、trade_cal、stock_basic、index_basic、ETF 基础信息等那一组。

**业务理解**：lowfreq 不是盘中判断层，它更像“全系统的底稿层”。

### 3）midfreq 采集层

代表代码：

- `src/ifa_data_platform/midfreq/registry.py`
- midfreq runner（通过 unified runtime 接入）

它负责：

- equity / index / ETF daily bar
- 龙虎榜
- 涨停明细
- 涨跌停状态
- 北向/南向/主力资金/换手率
- 板块表现

当前 midfreq registry 大约 **12** 个，且比 lowfreq 干净很多，基本都是实际生产口径内的数据集。

**业务理解**：这是“收盘后最有业务价值的一层”，因为它最接近盘后总结、日报、策略复盘真正需要的 daily-final 事实。

### 4）highfreq 采集层

代表代码：

- `src/ifa_data_platform/highfreq/registry.py`

它负责：

- stock/index/proxy/futures commodity precious metal 的 1m OHLCV
- open / close auction snapshot
- event time stream
- 以及派生出来的 sector breadth、sector heat、leader candidate、intraday signal state 等 working 表

当前 enabled 的高频 executable dataset 大约 **7** 个；另有 L2 / order queue / tick 之类条目存在，但默认未启用，仍属于“未验证 / 未纳入生产口径”。

**业务理解**：这一层现在最像“盘中辅助驾驶系统”，还不是适合长期沉淀为 canonical truth 的那一层。

### 5）Archive V2 生产/操作脚本

代表脚本：

- `scripts/archive_v2_production_cli.py`
- `scripts/archive_v2_operator_cli.py`
- `src/ifa_data_platform/archive_v2/production.py`
- `src/ifa_data_platform/archive_v2/runner.py`

它负责：

- nightly daily/final 归档
- bounded backfill / replay
- repair-batch
- completeness / repair queue / operator 观察

**业务理解**：这是现在最接近“沉淀成业务可复用真相资产”的层。

### 6）回放 / replay 证据层

代表代码：

- `scripts/slot_replay_evidence_cli.py`
- `src/ifa_data_platform/runtime/replay_evidence.py`

它负责：

- 为 `early / mid / late` 三个 slot 记录当时到底用的是哪些 run / manifest / dataset snapshot
- 把“这次报告/时段是基于什么数据做出的”变成可追溯证据

**业务理解**：这是很有价值的治理能力，但目前更偏“审计与回放底座”，不是业务端可直接消费的成品功能。

---

## 四、现在数据库里，实际在收什么、存什么

我做了轻量抽样，不做重操作，只看代表表的行数与最新日期。结论很清楚：

### 1）lowfreq：真实在持续存

代表抽样：

- `announcements_history`：**150,196** 行，最新到 **2026-04-22**
- `news_history`：**60,511** 行，最新到 **2026-04-22 11:54:50**
- `investor_qa_history`：**11,605** 行，最新到 **2026-04-21**
- `research_reports_history`：**1,050** 行，最新到 **2026-04-21**

这说明 lowfreq 不是“定义了表但没跑”，而是已经形成了明显的历史沉淀，尤其公告/新闻已经是可观规模。

### 2）midfreq：daily-final 事实层也是真实在存

代表抽样：

- `equity_daily_bar_history`：**502** 行，最新到 **2026-04-21**
- `dragon_tiger_list_history`：**2,455** 行，最新到 **2026-04-21**
- `limit_up_detail_history`：**113,255** 行，最新到 **2026-04-21**
- `sector_performance_history`：**2,364** 行，最新到 **2026-04-21**

这里最重要的不是绝对行数，而是它确实已经形成了“按交易日稳定沉淀”的 daily-final 层。

### 3）highfreq：有内容，但成熟度明显不均匀

代表抽样：

- `highfreq_event_stream_working`：**12,400** 行，最新到 **2026-04-22 11:47:01**
- `highfreq_stock_1m_working`：**6** 行，最新到 **2026-04-15 09:35:00**
- `highfreq_sector_breadth_working`：**2** 行，最新到 **2026-04-15 09:35:00**
- `highfreq_intraday_signal_state_working`：**2** 行，最新到 **2026-04-15 09:35:00**

这说明高频层不是完全没有，但**很不均匀**：

- event stream 是活的
- 但很多 1m / breadth / signal state working 表，看起来更像“能力已实现、现实上未形成持续生产填充”

因此 highfreq 当前更应被定义为：

**有生产框架和部分真实输出，但整体仍偏 working layer / partial live layer。**

### 4）Archive V2：已经是“真的有归档结果”

代表抽样：

- `ifa_archive_equity_daily`：**16,488** 行，最新到 **2026-04-21**
- `ifa_archive_sector_performance_daily`：**6,050** 行，最新到 **2026-04-21**
- `ifa_archive_announcements_daily`：**34,241** 行，最新到 **2026-04-22**
- `ifa_archive_news_daily`：**76,766** 行，最新到 **2026-04-22**

这件事非常关键。

它说明 Archive V2 已经不是“设计层 / 控制表层”，而是真正在生产 `ifa_archive_*` 前缀的数据资产。

也就是说，**Archive V2 已经是一层真实存在、并且有体量的归档真相层。**

---

## 五、H / M / L 现在分别做到什么程度

这里把 H/M/L 解释为 highfreq / midfreq / lowfreq 三层。

### 1）L = lowfreq：已经是“基础供给层”

当前状态：

- registry、调度、history/current/reference 结构都在
- 公告、新闻、问答、研报、trade_cal、基础资料这些数据已经有真实存量
- 它是 downstream 的素材层

但它的问题也很清楚：

- registry 中混有大量 test/demo dataset
- “代码里能跑”与“正式生产口径”之间仍需人为区分
- 它很强，但还不够“口径干净”

所以 lowfreq 的真实评价应是：

**已能稳定支撑业务底稿，但还不是一个非常干净的产品化目录。**

### 2）M = midfreq：已经是“最能直接支撑业务”的一层

当前状态：

- 数据集范围相对干净
- 日内/收盘后的两次核心调度已经明确
- daily-final 的业务价值最高
- 是报告层、归档层最容易吃进去的一层

midfreq 的问题不是“没有”，而是：

- 某些 dataset 更偏 report support，不全是 universally finalized truth
- cadence 有交易日与周末差异，不是每一天都完全同构

但整体上，midfreq 已经是当前 data layer 里**离业务消费最近、也最容易做成稳定产品能力**的一层。

### 3）H = highfreq：已经有 runtime skeleton，但离稳定产品还差一层

当前状态：

- 有 schedule
- 有 executable dataset
- 有 working 表
- 有盘前 / 盘中 / 收盘几个关键时点

但从现实样本看，高频层存在明显的“框架领先于持续生产填充”的特点：

- event stream 活跃
- 很多 working 表并没有形成很厚的现实数据沉淀
- 它本身也不是 finalized truth，而是 session-time state

所以 highfreq 当前更适合被定位为：

**盘中支持能力已经搭起来，但还不是能稳定对外承诺的成熟业务层。**

---

## 六、Archive V2 现在做到什么程度

Archive V2 是当前 data layer 里最值得重视的进展。

它现在已经做到的不是“能跑一次 backfill”，而是：

### 1）它已经是一层独立的归档真相层

不是把 lowfreq / midfreq 原表简单复制一下，而是明确把：

- collector history
- archive finalized truth

分成了两层语义。

这点对于后续业务非常重要，因为业务最终拿的数据，不一定应该直接从 collector history 表拿。

### 2）它已经覆盖 daily/final 的主干家族

从代码与生产配置看，nightly scope 现在主要包括：

- tradable/final daily：
  - `equity_daily`
  - `index_daily`
  - `etf_daily`
  - `non_equity_daily`
  - `macro_daily`
- business/event daily：
  - `announcements_daily`
  - `news_daily`
  - `research_reports_daily`
  - `investor_qa_daily`
  - `dragon_tiger_daily`
  - `limit_up_detail_daily`
  - `limit_up_down_status_daily`
  - `sector_performance_daily`

这已经足以说明：

**Archive V2 的主战场不是实验性 intraday，而是“夜间收敛 daily/final 真相”。**

### 3）它已经有生产运行与操作治理概念

Archive V2 不是单纯 runner，还配了：

- profile
- completeness
- repair queue
- operator CLI
- manual backfill
- weekend catch-up

这说明它已经不是脚本集合，而是接近一个小型归档子系统。

### 4）它还没到哪一步

没到的部分也要说实话：

- 默认 nightly scope 不包括 60m / 15m / 1m
- 不包括高频派生 C 类 family 作为主 truth model
- repair 仍以 operator/manual 为主，不是完全自动自治
- multi-worker lease / claim / orchestration 还不是最终形态

所以 Archive V2 的真实评价是：

**daily/final 归档层已经成型并且可用；更深的 intraday archive 与自动修复仍在下一阶段。**

---

## 七、runtime 现在的现实状态是什么

这部分最值得更新“旧认知”。

### 当前机器上的真实进程状态

本机进程直接看到：

- `python -m ifa_data_platform.runtime.unified_daemon --loop` **正在运行**，而且不止一个实例痕迹
- `python -m ifa_data_platform.lowfreq.daemon --loop` **也还在运行**

这意味着：

**统一 runtime 并不是“还没起来”，而是已经起来了；但老 lowfreq daemon 也还没完全退场。**

这是一个很关键的现实结论：

- 从“能力是否存在”看：统一 runtime 已经存在，而且正在跑
- 从“生产入口是否唯一”看：还没有完全收口，现场仍有新旧并行残留

### 调度定义也说明 unified runtime 已经是正式调度面

DB 中 `runtime_worker_schedules` 显示：

- `highfreq` 交易日 09:15 / 09:27 / 11:25 / 14:57 启用
- `midfreq` 交易日 11:45 / 15:20 启用
- `archive_v2` 交易日 21:40 启用
- legacy `archive` 行保留但 disabled

这说明架构层面已经把：

**Archive V2 作为正式 nightly lane，legacy archive 退成 fallback。**

### 但 runtime 治理还没有完全闭环

目前已有：

- runtime budget
- overlap prevention
- worker state
- schedule seeding
- status 查询
- replay evidence 自动 capture

但还缺：

- 完全收口到“只有 unified daemon 是唯一正式入口”
- 更彻底的活跃实例治理
- 更强的外部 watchdog / hard-kill / auto-recover

因此 runtime 当前的真实评价是：

**它已经是可运行的统一调度层，但还处在“生产收口期”，不是完全收敛完毕的最终形态。**

---

## 八、replay / 回放层现在做到什么程度

回放层的价值，是让系统以后能回答这种问题：

- 某天 09:29 的 pre-open 结论，当时到底用的是哪一批数据？
- 是 observed 版本还是 corrected 版本？
- 对应了哪些 runtime run？
- 那一刻的 manifest 和 dataset snapshot 是什么？

从代码上看，这套结构已经比较完整：

- `slot_replay_evidence`
- `slot_replay_evidence_runs`
- `ReplayEvidenceStore`
- `slot_replay_evidence_cli.py`
- unified daemon 在部分 schedule 下可自动 capture

它已经具备：

- 按 `early / mid / late` 组织 replay 证据
- 挂 run_id / manifest / dataset snapshot
- 记录 artifact path/hash 的接口

但轻量 DB 抽样里，目前 `slot_replay_evidence` 还是空的。

这说明 replay 现在的状态是：

**设计和代码框架已经落地，且已接进 unified daemon；但现场“证据资产库”还没有形成明显积累。**

这是一种典型的“底座先行、业务使用还没跟上”的状态。

---

## 九、哪些数据层已经能支撑业务

### 已经能支撑业务的

#### 1. lowfreq 的基础资料 + 业务文本

可支撑：

- 早报/盘前的背景资料
- 个股/主题的公告、新闻、研报、问答补充
- 日历、基础信息、reference 解释

这是当前最适合做“信息底稿”的层。

#### 2. midfreq 的 daily-final 事实

可支撑：

- 收盘后日报
- 板块强弱、涨停结构、龙虎榜、主力/北向等盘后判断
- nightly archive 的主输入之一

这是当前最适合做“当天收盘后结论”的层。

#### 3. Archive V2 的 daily/final 归档

可支撑：

- 跨天复盘
- 稳定口径的历史查询
- 后续产品层统一消费
- 报告系统对 T-1 / T 日夜间归档资产的调用

如果业务问“有没有一层相对干净的最终真相表”，现在最接近答案的就是它。

---

## 十、哪些还只是底层能力，离产品交付还差一层

### 1）highfreq

它已经能支持 runtime 与部分盘中判断，但离业务交付还差：

- 更稳定的持续填充
- slot 级明确消费口径
- working/state 与 final truth 的明确边界说明
- 对外输出的标准化

### 2）replay evidence

它现在还是“治理能力”，不是“业务功能”。

离产品交付还差：

- 真正被日报/回放页面/审计页面消费
- artifact 真正持续落库
- replay 资产的稳定积累

### 3）统一 runtime 的唯一化

它现在已经很接近正式生产入口，但离“可放心对外说唯一入口已收口”还差：

- legacy daemon 退场
- 重复实例清理
- 更清晰的运行 owner / SRE 口径

---

## 十一、下一步 data layer 最值得做的几件事

如果只挑最值得做的几件事，我建议优先级如下。

### 第一优先级：把“业务可依赖真相层”彻底收口到 Archive V2 + 明确消费边界

目标：

- 让产品/业务明确知道该读哪一层
- collector history 不再被误当成最终产品数据
- 报告、回放、分析都尽量从 Archive V2 接口化消费

这是最值钱的一步，因为它直接解决“到底哪层可以对业务承诺”的问题。

### 第二优先级：把 unified runtime 真正收成唯一生产入口

目标：

- 关停 legacy lowfreq daemon 共存状态
- 消除多实例/双轨运行残留
- 把运行治理、schedule truth、status truth 完全统一到 unified daemon

这一步不一定直接增加业务功能，但它会显著降低现场混乱和误判成本。

### 第三优先级：把 highfreq 从“working 能力”往“可消费产品输入”推进一层

目标：

- 挑最关键的几个 slot（09:27、11:25、14:57）
- 明确每个 slot 真正依赖哪几张 highfreq 表
- 做出 slot 级 freshness / degrade contract

高频不需要一下子做成完美历史层，但至少要从“有 working 表”进化到“业务知道怎么安全使用”。

### 第四优先级：让 replay evidence 真正产生资产沉淀

目标：

- 不只是有 schema 和 CLI，而是真有 early/mid/late 的 replay 样本
- 把 artifact path/hash/run linkage 持续积累起来
- 给未来复盘、质检、回放页面留出真实证据链

这是一个短期看不炫，但中长期非常值钱的事情。

### 第五优先级：清理 lowfreq 的 registry 口径

目标：

- 把 test/demo dataset 和 production dataset 更明确分层
- 降低“代码里看起来很多，实际可上线的没那么多”的认知噪音
- 给业务/产品一个更清晰的 lowfreq 目录

这不是纯技术洁癖，而是为了让后续 planning 更少误会。

---

## 十二、最后的业务化判断

如果从“现在能不能支持业务规划”这个角度看，我会给出下面这版判断：

### 已经具备业务价值的部分

- lowfreq：可作为内容/背景/参考底稿层
- midfreq：可作为日终市场事实层
- Archive V2：可作为 nightly finalized truth 层

### 还不应过度承诺的部分

- highfreq：可做盘中辅助，但还不应宣称为成熟产品层
- replay：可做治理和回放底座，但当前还不是成型产品能力
- runtime 唯一入口：方向已对，但现场收口未彻底完成

### 所以最准确的总体评价是

**这套 data layer 已经能支撑“日报 + 复盘 + 夜间归档”三件核心事情，但若要进一步支撑更强的产品化、审计化、实时化能力，还需要把 runtime 收口、highfreq 消费契约、replay 资产沉淀这三件事继续做完。**

---

## 附：本次判断主要基于哪些现实证据

- 仓库目录：`src/ifa_data_platform/{lowfreq,midfreq,highfreq,archive_v2,runtime}`
- 统一调度入口：`src/ifa_data_platform/runtime/unified_daemon.py`
- 生产/操作脚本：
  - `scripts/runtime_manifest_cli.py`
  - `scripts/archive_v2_production_cli.py`
  - `scripts/archive_v2_operator_cli.py`
  - `scripts/slot_replay_evidence_cli.py`
- 文档与审计包：
  - `docs/DEVELOPER_COLLECTION_CONTEXT.md`
  - `docs/COLLECTION_LAYERS_REQUIREMENT_VS_IMPLEMENTATION_AUDIT_2026-04-19_0635.md`
  - `docs/COLLECTION_LAYER_DB_EVIDENCE_PACKAGE_2026-04-19_0648.md`
  - `docs/ARCHIVE_V2_PRODUCTION_RUNBOOK.md`
- 轻量 DB 现实抽样：
  - lowfreq / midfreq / highfreq / archive_v2 代表表的行数与最新日期
  - `runtime_worker_schedules`
- 本机进程现实：
  - unified daemon 在运行
  - legacy lowfreq daemon 也仍在运行

这份文档的核心价值，不是证明“架构看起来很完整”，而是把**现在已经可以当真相讲的部分**和**还只是底层能力的部分**分开讲清楚。