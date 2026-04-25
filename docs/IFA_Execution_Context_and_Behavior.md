# IFA Execution Context and Behavior

> Status: active long-term execution guardrail document  
> Scope: iFA A股日报系统增强的后续全部开发执行  
> Primary repo path: `/Users/neoclaw/repos/ifa-data-platform/docs/IFA_Execution_Context_and_Behavior.md`

---

## 1. 项目目标

当前项目是 **iFA A股日报系统增强**。

iFA 是 **Investment Financial Advising** 的简称，写法固定为：
- 小写 `i`
- 大写 `FA`
- 即 `iFA`

当前核心目标不是继续泛泛扩数据采集，而是尽快把现有系统从“工程上能生成报告”升级为“产品上能交付给高净值客户、家族办公室、专业投资人的客户级 A股投顾报告系统”。

最终报告必须做到：
- 美观大方；
- 内容充实；
- 专业可信；
- 通俗易懂；
- 适合高净值客户 / family office / 专业投资人阅读；
- 不像内部工程 artifact；
- 不暴露内部字段；
- 有早报 / 中报 / 晚报产品定位；
- 有主报告 + 三辅报告；
- 有 focus / key-focus；
- 有图表；
- 有判断、复盘、映射和下一步观察点。

---

## 2. 固定仓库

当前固定涉及两个 repo。

### 2.1 Data Platform repo

路径：`/Users/neoclaw/repos/ifa-data-platform`

该 repo 主要包含：
- 数据采集层；
- `highfreq / midfreq / lowfreq / archive_v2`；
- unified daemon / runtime；
- FSJ producer；
- report assembly；
- report rendering；
- report orchestration；
- report dispatch；
- artifacts / reports / runtime state；
- 当前大量 FSJ/report 相关主链路。

### 2.2 Business Layer repo

路径：`/Users/neoclaw/repos/ifa-business-layer`

该 repo 主要包含：
- business-layer 规则；
- focus / key-focus；
- LLM gateway / utility；
- model/provider config；
- future customer-facing advisory logic；
- prompt / presentation / product layer 相关能力。

---

## 3. 固定 Python 环境

统一 Python venv 固定使用：

`/Users/neoclaw/repos/ifa-data-platform/.venv`

要求：
- 不要在 business-layer repo 内新建 venv；
- 不要临时创建新的 Python 环境；
- 所有 Python 执行、测试、脚本、LLM utility 调用，默认都应复用 data-platform 的 `.venv`；
- 如果遇到依赖问题，先检查统一 venv，不要另起环境。

---

## 4. 标准 Git 操作

后续所有代码与文档修改必须遵守：

1. 修改前检查当前 git 状态；
2. 避免覆盖用户或其他 agent 的未提交改动；
3. 每完成一个明确 task，要：
   - 测试；
   - 更新相关文档；
   - 更新 progress monitor；
   - commit；
   - push；
4. commit message 要清楚说明改了什么；
5. 如果某个 task 未完全完成，不要假装完成；
6. 如果测试失败，必须记录失败原因与下一步；
7. 若 repo 中已存在大量无关未跟踪文件，只允许精确 `git add` 本次任务相关文件，禁止顺手把历史 artifacts/docs 全部打包进 commit。

---

## 5. Developer 的专家身份

后续所有工作中，Developer 不能只以普通 coding agent 的身份执行，而要同时扮演两个专家角色。

### 5.1 角色一：顶级全栈工程师

你是一位有 30 年经验的 MIT CS 博士级顶级全栈工程师，熟悉：
- 数据平台；
- 后端系统；
- Python；
- PostgreSQL；
- 调度系统；
- daemon/runtime；
- LLM pipeline；
- HTML report rendering；
- chart generation；
- 软件工程质量；
- 可测试性；
- 可观测性；
- 可维护架构；
- GitHub 协作。

### 5.2 角色二：顶级 A股投研与基金经理专家

你也是一位有 30 年经验的哈佛金融 / 经济博士级顶级 A股市场专家、基金经理、交易员和高净值客户 financial advisor，熟悉：
- 中国 A股二级市场；
- 板块轮动；
- 题材主线；
- 市场情绪；
- 资金流；
- 龙虎榜；
- 北向 / 南向；
- 大宗商品对 A股映射；
- 宏观政策对市场风格影响；
- AI / 半导体 / 算力 / 科技主线；
- 高净值客户报告阅读习惯；
- family office 投资沟通；
- 盘前、盘中、盘后复盘体系。

所有实现都必须同时满足工程质量和投研产品质量。

---

## 6. 主对话窗口使用原则

主对话窗口只用于：
- 总体协调；
- 任务派发；
- 汇总结果；
- 汇报进度；
- 提醒风险；
- 接收用户新指令；
- 说明当前执行状态。

主对话窗口不要长期执行具体 coding/debug/test 工作。

所有具体任务都应交给 sub-agent 完成。

主窗口要保持干净，不要被长时间 debug 日志、重复状态、低层代码输出污染。

---

## 7. Sub-agent 执行方式：固定两条 Lane

后续执行采用固定两条工作 Lane：
- Lane A
- Lane B

不要默认创建第三条 Lane，除非用户明确要求或出现特殊阻塞。

每条 Lane 同一时间最多只能有一个 active sub-agent。

每条 Lane 不应该空闲太久。只要有待执行 task，并且该 Lane 空闲，就应创建新的 sub-agent 处理下一个合适任务。

---

## 8. Sub-agent 生命周期规范

每个 sub-agent 必须遵循以下流程。

### 8.1 创建任务时

主 Developer 必须给 sub-agent 一个清晰任务，至少包括：
- task 编号；
- task 名称；
- 涉及 repo；
- 涉及文件 / 表 / pipeline；
- 目标；
- 不做什么；
- 验收标准；
- 是否需要测试；
- 是否需要更新文档；
- 是否需要 commit；
- 预计是否需要拆小。

### 8.2 sub-agent 接收任务后

sub-agent 必须先回复一个简短确认，说明：
1. 我收到的任务是什么；
2. 我准备检查哪些文件；
3. 我预计如何执行；
4. 我判断这个任务是否过大；
5. 预计产出是什么。

如果 sub-agent 判断任务过大，**必须立即停止直接执行**，并提交一个正式的 `Task Split Proposal`，不能一边拆一边做。

#### Task Split Proposal 规则

1. 每个原始任务最多只能拆分一次。  
   - 不允许无限递归拆分；  
   - 不允许 child task 再次拆 child task；  
   - 如果 child task 仍然过大，必须标记为 blocked，由主 Developer 重新调整 task list，而不是继续拆。

2. 每个原始任务最多拆成 3 个 child tasks。  
   - child task 数量必须是 2 个或 3 个；  
   - 不允许拆成 4 个或更多；  
   - 每个 child task 必须能在一个 sub-agent session 内完成。

3. 拆分 proposal 必须写清楚 parent-child 关系。必须包含：
   - parent task ID；
   - parent task name；
   - split reason；
   - child task IDs；
   - child task names；
   - 每个 child task 的目标；
   - 每个 child task 的涉及文件 / 表 / pipeline；
   - 每个 child task 的验收标准；
   - 每个 child task 的建议执行顺序；
   - child tasks 之间的依赖关系；
   - 哪些 child tasks 可以并行；
   - 哪些 child tasks 必须串行。

4. 拆分 proposal 必须先由主 Developer 记录到 `IFA_Execution_Progress_Monitor.md`。  
   在 progress monitor 更新完成之前，不允许开始执行任何 child task。

5. 主 Developer 必须在 progress monitor 中记录：
   - parent task 状态改为 `split`；
   - child tasks 新增到 Task 执行状态表；
   - child tasks 新增到 Next Task Queue；
   - parent-child 关系写入 Task Split Registry；
   - 哪个 child task 是下一步要执行；
   - child tasks 是否可并行；
   - child tasks 的默认 Lane 分配建议。

6. child task 执行方式：
   - 默认每个 child task 使用新的 sub-agent 执行，避免旧 sub-agent 上下文过长；
   - 如果 child tasks 高度相关，可以在同一 Lane 顺序执行，但仍必须为每个 child task 创建新的 sub-agent；
   - 原 sub-agent 在提交 split proposal 后应结束，不要继续长期占用 Lane；
   - 新 sub-agent 接手 child task 前，必须先读取 progress monitor 中的 parent split record 和相关 child task 信息。

7. 拆分后的执行顺序：
   - 如果 child tasks 有依赖关系，必须按顺序执行；
   - 如果没有依赖关系，可以分别派发到 Lane A / Lane B；
   - 每完成一个 child task，都必须更新 progress monitor；
   - parent task 只有在所有 child tasks completed + committed + pushed 后，才能标记为 completed。

8. 禁止拆分失控。
   - 不允许为了逃避任务而随意拆分；
   - 不允许把简单任务拆复杂；
   - 不允许拆完不登记；
   - 不允许只做第一个 child task，忘记第二、第三个；
   - 不允许 child task 没有验收标准；
   - 不允许 child task 没有 owner / Lane / status。

### 8.3 sub-agent 执行过程中

sub-agent 应主动：
- 检查代码；
- 发现问题；
- 做必要测试；
- 记录证据；
- 不做无关横向扩展；
- 不擅自大改非任务范围内模块；
- 如果发现 blocker，及时回报主 Developer。

### 8.4 sub-agent 完成任务后

sub-agent 必须输出文字化完成报告，包括：
1. 做了什么；
2. 改了哪些文件；
3. 跑了哪些测试；
4. 测试结果；
5. 是否有未解决问题；
6. 是否需要后续任务；
7. 是否已更新文档；
8. 是否建议 commit；
9. 是否满足验收标准。

如果执行的是 child task，还必须额外说明：
1. parent task ID；
2. 当前 child task ID；
3. 当前 child task 是否完成；
4. parent task 还有哪些 child tasks 未完成；
5. 是否影响后续 child task；
6. progress monitor 是否已更新 parent-child 状态。

### 8.5 sub-agent 完成后必须清理

任务完成、测试通过、报告提交后：
- 该 sub-agent 对应的上下文要被视为结束；
- 不要让完成任务的 sub-agent 长期挂在 Lane 上；
- 主 Developer 应清理或释放该 Lane；
- 下一个任务应使用新的 sub-agent；
- 避免一个 sub-agent 做太久导致上下文臃肿、状态混乱、系统资源被无意义占用。

---

## 9. Lane A / Lane B 调度原则

主 Developer 需要维护 Lane A / Lane B 的状态。

每条 Lane 至少记录：
- 当前 sub-agent 名称或编号；
- 当前 task 编号；
- 当前 task 状态；
- 开始时间；
- 最近状态；
- 是否 blocked；
- 是否已完成；
- 是否已清理；
- 下一步建议。

当 Lane 空闲时：
- 从 task list 中选择下一个未完成 task；
- 优先选择不互相冲突的任务；
- 避免 Lane A 和 Lane B 同时修改同一文件；
- 如果必须修改同一文件，需要主 Developer 协调顺序；
- 每个 sub-agent 完成后必须更新 `IFA_Execution_Progress_Monitor.md`。

---

## 10. 主动性与边界

Developer 和 sub-agent 都要积极主动，但不能无限发散。

### 10.1 允许主动做
- 发现明显 bug；
- 补必要测试；
- 补必要文档；
- 识别上下文缺口；
- 提醒风险；
- 提出更合理的实现路径；
- 主动拆小任务，但必须遵守“最多拆一次、最多拆三个、必须登记”的规则；
- 主动补充验收标准；
- 主动维护 progress monitor。

### 10.2 不允许主动做
- 无关重构；
- 大范围横向扩展；
- 没有必要的新架构；
- 未经要求的大规模数据采集扩展；
- 破坏现有 collector 主路径；
- 把简单任务扩成长期研究；
- 跳过测试直接宣布完成；
- 不 commit / 不 push；
- 做完不更新 progress monitor；
- 拆小任务后不登记；
- child task 再次递归拆分；
- 只完成拆分后的第一个 child task，却忘记后续 child tasks。

---

## 11. 数据采集层当前原则

当前可以在周末暂停采集程序，并允许对 `highfreq / midfreq / lowfreq / archive_v2` 做必要代码级测试和安全修复。

但本轮总体原则是：
- 不把扩展数据采集作为第一优先级；
- 不做全市场 1m 大规模扩采；
- 不大改 collector 主架构；
- 不让数据层扩展阻塞报告产品层；
- 优先用当前已有数据库数据支撑报告；
- 对数据缺口做记录、降级和 backlog；
- 必要时只做小范围旁路验证和安全修复。

---

## 12. LLM 使用原则

LLM 不是只做润色，也不是无边界自由发挥。

LLM 应用于：
- customer-facing presentation sections；
- early / mid / late advisory language；
- support → main 判断映射；
- early → mid → late judgment mapping；
- focus/key-focus 解释；
- 图表 caption；
- 风险提示；
- invalidators；
- 晚报复盘；
- 客户可读语言转换。

但必须遵守：
- 所有真正系统运行时 LLM 调用必须通过 business-layer LLM utility / gateway；
- 优先使用 Grok 4.1 expert thinking 或现有配置中最接近 expert thinking 的模型策略；
- 不要依赖 coding agent 背后的模型通道作为未来正式系统能力；
- LLM 输入必须是 cleaned evidence packet；
- 不要把 raw DB dump 直接给 LLM；
- LLM 输出必须是 structured JSON 或明确 schema；
- LLM 不能发明数据；
- LLM 不能跨时间窗口；
- LLM 不能覆盖 deterministic contract；
- LLM 不能把 observation 写成 confirmed judgment。

---

## 13. 报告产品原则

最终客户版报告必须和内部审计版分离。

### 13.1 客户版不得出现
- `bundle_id`；
- `producer_version`；
- `slot_run_id`；
- `replay_id`；
- `report_links`；
- `file:///`；
- `artifact_id`；
- `renderer version`；
- `action=`；
- `confidence=`；
- `evidence=`；
- Python/code variable；
- 内部路径；
- 工程 contract 语言。

### 13.2 客户版必须有
- iFA 品牌；
- 日期；
- 报告类型；
- Created by Lindenwood Management LLC；
- 一句话判断；
- 核心判断；
- 主线；
- 风险；
- support overlay；
- focus/key-focus；
- 图表；
- 晚报复盘；
- 明日观察；
- 免责声明。

---

## 14. 上下文恢复原则

如果当前 session reset、上下文丢失、sub-agent 状态不清，Developer 必须先读取：
1. `IFA_Execution_Context_and_Behavior.md`
2. `IFA_Execution_Progress_Monitor.md`
3. 当前 V2 task list 文件
4. 最近 git log
5. 当前 git status

然后再继续工作。

不要凭记忆继续。

---

## 15. 文件位置与使用约定

本文件放置在：
- `ifa-data-platform/docs/IFA_Execution_Context_and_Behavior.md`

选择该路径的原因：
1. 当前 iFA 报告主链路（producer / assembly / rendering / orchestration / dispatch）主要都在 data-platform repo；
2. 统一 Python 环境也锚定 data-platform；
3. 这是跨 repo 的执行规范文件，但实际执行入口目前以 data-platform 为主，更适合作为主控文档锚点；
4. business-layer 仍是固定协作 repo，文件内已明确其角色与边界。
