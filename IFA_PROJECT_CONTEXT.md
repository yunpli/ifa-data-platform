# IFA_PROJECT_CONTEXT.md

> 强制规则：每次新 session，developer 必须先读取本文件，再开始工作。

## 1. 项目定位

- 项目名称：iFA
- 当前阶段：低频数据体系已完成第一阶段（Job 1–10A）
- 当前重点：进入低频收尾 / 中频准备 / 后续高频准备

---

## 2. Workspace 说明（非常重要）

- 真实开发 repo：`/Users/neoclaw/repos/ifa-data-platform`
- OpenClaw workspace（不要用于代码开发）：`~/.openclaw/workspace`

### 强制规则

- 开发代码只允许在 `repos` 下进行，不在 `openclaw workspace`
- `~/.openclaw/workspace` 只用于 OpenClaw 会话、技能、上下文与辅助文件，不作为 iFA 正式代码开发目录
- 任何代码修改、脚本新增、迁移、文档、提交，默认都应在真实 repo 内完成

---

## 3. 数据库与 schema

- 数据库：`ifa_db`
- schema：`ifa2`

### 强制规则

- 所有 lowfreq / ingest / 查询必须在 `ifa2` 下执行
- 不允许使用 `public` schema
- 所有 SQL、迁移、脚本、健康检查、运维命令默认都应显式以 `ifa2` 为目标

---

## 4. Tushare token

- `TUSHARE_TOKEN` 从本地 `config/runtime/tushare.env` 读取
- 不要写真实 token 值
- 不允许把 token 写入代码、repo、文档、测试样例或提交记录

---

## 5. Universe 规则（A / B / C）

- A：持仓（高频）
- B：中频
- C：低频

### 强制规则

- `A ⊂ B ⊂ C`
- 所有 lowfreq dataset 只允许从 `C` 读取
- 所有 midfreq dataset 只允许从 `B` 读取
- 所有 highfreq dataset 只允许从 `A` 读取
- 不允许全市场采集
- 不允许绕过 `symbol_universe`

### 作用说明

- C 用于低频慢变量、基础表、文档与资产层采集
- B 用于中频重点池的日内更新、结构化行情、板块与重点个股状态更新
- A 用于高频持仓层的更细颗粒度、更高频、更强资源约束的数据采集

---

## 6. ACP / 执行规则

- 编码 → 用 ACP / OpenCode
- 验收 / 查 DB / 跑 ingest → 不用 ACP（直接本机）

### 强制规则

- 最后一公里不用 ACP
- 代码实现、重构、复杂改动可交给 ACP / OpenCode
- 真实验收、数据库核查、ingest 运行、daemon 验证、状态检查，默认直接在本机完成

---

## 7. 当前系统状态

- lowfreq framework：完成
- Job 1–10A：已完成或完成主体
- dataset：8A / 8B / 9 已完成
- Universe 驱动：已完成
- lowfreq 已从全市场模式切换到 Universe 驱动模式
- daemon：可运行

---

## 8. 中频 / 高频基本原则

- 接下来固定顺序：先中频，再高频
- 中频 / 高频必须延续低频逻辑，不允许另起炉灶
- 必须尽量复用：
  - `symbol_universe`
  - raw / source mirror
  - canonical current
  - history / version
  - daemon / state
  - summary / docs / runbook

### 分层理解

- 低频：慢变量、文档、基础表、资产层
- 中频：B list 上的日内更新 / 结构化行情 / 板块与重点个股状态更新
- 高频：A list 上的更高频、更精细、更强资源约束的数据层

---

## 9. 当前禁止事项

- 不允许全市场扫描
- 不允许跳过 `symbol_universe`
- 不允许写 token 到代码或 repo
- 不允许改 schema 到 `public`
- 不允许中频 / 高频另起一套独立 ingestion/runtime 体系

---

## 10. 会话启动要求

- 每次新 session，developer 必须先读取本文件，再开始工作
- iFA 相关工作还必须继续读取：`IFA_MID_HIGH_PLAN.md`
- 若本文件与临时聊天上下文冲突，以本文件中的项目基线为准，再结合当前用户明确指令执行
- 若发现工作目录、数据库、schema、Universe 使用方式偏离本文件，必须先纠正再继续

---

## 8. 当前禁止事项

- 不允许全市场扫描
- 不允许跳过 `symbol_universe`
- 不允许写 token 到代码或 repo
- 不允许改 schema 到 `public`

---

## 9. 会话启动要求

- 每次新 session，developer 必须先读取本文件，再开始工作
- 若本文件与临时聊天上下文冲突，以本文件中的项目基线为准，再结合当前用户明确指令执行
- 若发现工作目录、数据库、schema、Universe 使用方式偏离本文件，必须先纠正再继续
