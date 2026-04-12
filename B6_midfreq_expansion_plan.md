# B6 Midfreq Expansion Plan

> 2026-04-12

---

## 一、B6 扩展范围

### 已确认要扩展的数据类别

#### A. 行情类扩展
| Dataset | Tushare API | 频率 | B Universe | 窗口 | 状态 |
|---------|------------|------|------------|------|------|
| equity_intraday_bar | daily + intraday | 5m/15m | B | 日内窗口 | ⬜ 规划 |
| index_intraday_bar | index_daily | 5m/15m | - | 日内窗口 | ⬜ 规划 |
| etf_intraday_bar | etf_daily | 5m/15m | B | 日内窗口 | ⬜ 规划 |

#### B. 资金类扩展
| Dataset | Tushare API | 频率 | B Universe | 窗口 | 状态 |
|---------|------------|------|------------|------|------|
| southbound_flow | moneyflow_hsgt | 日级 | - | post_close | ⬜ 规划 |
| margin_financing_balance | margin | 日级 | B | post_close | ⬜ 规划 |
| margin_finance_detail | margin_detail | 日级 | B | post_close | ⬜ 规划 |
| etf_fund_flow | etf_fund_flow | 日级 | B | post_close | ⬜ 规划 |

#### C. 结构类扩展
| Dataset | Tushare API | 频率 | B Universe | 窗口 | 状态 |
|---------|------------|------|------------|------|------|
| dragon_tiger_list | daily | 日级 | - | pre_open | ⬜ 规划 |
| turnover_rate | daily | 日级 | B | post_close | ⬜ 规划 |
| market_breadth | - | 日级 | - | post_close | ⬜ 规划 |
| limit_up_detail | stk_limit | 日级 | - | post_close | ⬜ 规划 |

#### D. 板块/行业动态扩展
| Dataset | Tushare API | 频率 | B Universe | 窗口 | 状态 |
|---------|------------|------|------------|------|------|
| sector_daily_performance | daily | 日级 | - | post_close | ⬜ 规划 |
| industry_leadership | stock_basic | 日级 | B | post_close | ⬜ 规划 |

---

## 二、分批策略

### Batch 1: 最核心扩展（优先实现）
- equity_intraday_bar（分钟级窗口采样）
- southbound_flow（南北向资金）
- margin_financing_balance（融资余额）
- limit_up_detail（涨跌停明细）

### Batch 2: 结构/板块增强
- dragon_tiger_list（龙虎榜）
- turnover_rate（换手率）
- sector_daily_performance（板块日表现）

### Batch 3: 资产沉淀型
- market_breadth（市场广度）
- industry_leadership（行业领导）
- 其他适合沉淀的市场数据

---

## 三、架构约束

1. **Universe 约束**：全部从 symbol_universe (type=B) 读取
2. **复用架构**：统一使用 current/history/version 模式
3. **窗口采样**：每轮执行形成确定性 snapshot，不是持续流
4. **Version 规则**：无变化不建新 version

---

## 四、验收标准

1. 每个新 dataset：
   - 有 canonical current persistence
   - 可被 daemon 调用
   - 正确写 version
   - 生成 summary
   
2. Daemon 集成：
   - 新 dataset 已配置到 daemon 窗口
   - 执行成功可查询

3. Watchdog：
   - 保持正常运行

4. 文档：
   - 有 B6 扩展报告

---

## 五、Tushare API 映射

| 数据需求 | Tushare API | 需要的 token 权限 |
|----------|------------|-------------------|
| 融资余额 | margin | margin |
| 融资明细 | margin_detail | margin |
| 龙虎榜 | daily (limit) | daily |
| 南北向 | moneyflow_hsgt | moneyflow |
| ETF 资金 | etf_fund_flow | moneyflow |

---

## 六、执行计划

- Batch 1: 立即开始
- Batch 2: Batch 1 完成无 blocker 后继续
- Batch 3: Batch 2 完成无 blocker 后继续

每批完成后都 commit + push。