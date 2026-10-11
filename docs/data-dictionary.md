# 数据字段与填写规则

CSV 使用 UTF-8、英文逗号、点号小数，无千位分隔符；空值代表未知，不用零代替未知。金额保留适合币种的精度。示例所有金额为 MYR；其他币种替换前先统一券商记账口径。

时间采用 ISO 8601，例如 `2026-01-05T10:00:00+08:00`。日期采用 `YYYY-MM-DD`。编号不含个人账户信息，示例账户使用 `DEMO-01`。自由文字如含逗号、双引号或换行，按 CSV 规则引用；手动录入时尽量使用简短说明。

## 数据目录与配置 dataset.json

每个 `--data-dir` 指定的目录包含 dataset.json 和以下七张核心表；即使没有事件，也保留 CSV 表头：cash-events、fills、trades、strategies、daily-assets、positions-daily、behavior-events。

```json
{
  "schema_version": 2,
  "account_id": "DEMO-01",
  "currency": "MYR",
  "timezone_offset": "+08:00",
  "fictional": true,
  "cost_method": "FIFO"
}
```

| 字段 | 规则 |
|---|---|
| schema_version | 本版为 2 |
| account_id | 所有账户字段一致；使用账户别名 |
| currency | 单一记账币种，例如 MYR；本版不进行汇率转换 |
| timezone_offset | 统一时区偏移，例如 +08:00；事件按该时区归属日期 |
| fictional | JSON 布尔值 true/false；真实数据设 false |
| cost_method | 本版只支持 FIFO；其他成本法需扩展程序 |

JSON 使用双引号，不允许注释和尾逗号。时间字段应包含明确时区；每日日期对应配置中的当地日末。

第一张 daily-assets 快照是日末基准，不是程序重放交易的第一天。资金事件和成交只录入**基准日期之后**的记录；历史持仓通过 opening-lots 提供成本。快照基准的同日交易已经反映在余额中，不应再次录入。

## 资金事件 cash-events.csv

| 字段 | 含义 |
|---|---|
| event_id | 唯一编号 |
| timestamp | 入账时间 |
| account_id | 账户别名 |
| event_type | DEPOSIT / WITHDRAWAL / DIVIDEND / INTEREST / ACCOUNT_FEE |
| amount | 有符号金额；入金、股息、利息为正，出金、账户费为负 |
| trade_id | 股息可关联交易；无法明确归属则留空 |
| note | 原始报表依据或简短说明 |

只记录非买卖现金事件。成交现金变动及成交手续费仅记录在 fills.csv。尚未到账的应计股息、利息不纳入此最小版；如券商净资产含应计款，先扩展应收项目并核对。

## 成交 fills.csv

| 字段 | 含义 |
|---|---|
| fill_id | 本账本唯一成交编号 |
| broker_fill_id | 券商成交编号，缺失时留空并注明依据 |
| broker_order_id | 券商订单编号；多次部分成交可共用订单编号 |
| trade_id | 关联完整交易 |
| timestamp | 实际成交时间 |
| side | BUY / SELL |
| quantity | 正数数量 |
| price | 单位成交价 |
| fees | 本次成交全部交易费用，非负；不含另列的账户费 |

标的和策略通过 trade_id 查询。手续费若券商按订单合计收费，按成交数量比例分配，尾差归最后一笔；分配合计必须等于原费用。一条真实成交在最小版中只归属一个 trade_id，不得复制给多个策略。

## 交易 trades.csv

| 字段 | 含义 |
|---|---|
| trade_id | 完整交易唯一编号 |
| account_id / symbol | 账户别名和标的 |
| strategy_id / strategy_version | 对应 strategies.csv 的有效组合 |
| opened_at / closed_at | 第一笔买入及最终平仓时间；未平仓 closed_at 留空 |
| planned_entry / planned_stop | 事前参考入场与失效价格；非价格止损可留空并在计划中解释 |
| initial_risk | 事前为完整交易确定的风险预算金额，包含计划加仓；R 分母固定 |
| status | OPEN / CLOSED |
| plan_path | 仓库内计划及复盘文件相对路径 |

模板仅适用于真实已建仓交易；未成交的候选计划单独保存在计划文档中。新增计划外风险记录行为偏差，不调大历史 initial_risk。初始风险未知时留空，不计算 R。

## 策略 strategies.csv

| 字段 | 含义 |
|---|---|
| strategy_id / version | 联合唯一键 |
| name | 策略名称 |
| active_from / active_to | 新交易使用该版本的起止日期；持续使用时终止日期留空 |
| rules_path | 完整策略规则文档路径 |

两个版本的有效期可重叠，但每笔交易只关联一个版本。版本停用后，旧持仓可以继续按旧规则管理；不要为匹配当前版本而改写旧交易。

## 每日账户资产 daily-assets.csv

| 字段 | 含义 |
|---|---|
| date / account_id | 每日每账户唯一键 |
| cash | 同一估值时点的现金，包含应收应付买卖结算款后的经济现金 |
| positions_market_value | 所有持仓当日市值合计 |
| nav | cash + positions_market_value |
| external_flow | 当日入金减出金；与资金事件核对 |
| realized_pnl_ytd | 年初至今累计已实现交易净损益，含已平仓批次分配的买卖费 |
| unrealized_pnl | 当前全部持仓的未实现净损益，剩余买入费计入成本 |
| fees_ytd | 年初至今成交费用和账户费用总额，仅供信息展示 |
| source | 估值和报表依据 |

完整年度报告需保存年初之前最近一个可用期初快照。也可以从年中某个日末开始，报告只代表之后提供的区间。基准行的 realized_pnl_ytd 和 fees_ytd 可包含该年度此前累计数值；后续同年核对从其上继续累积，跨年按新年口径重置。未实现损益不重置；年度贡献比较期初与期末未实现损益。源字段使用别名或相对路径，不放敏感信息。

## 每日持仓 positions-daily.csv

| 字段 | 含义 |
|---|---|
| date / account_id / trade_id | 联合唯一键 |
| symbol / quantity | 标的与当前剩余数量 |
| mark_price | 当日估值价格 |
| cost_basis | 剩余持仓总成本，包含分配后的买入手续费 |
| market_value | quantity × mark_price |
| unrealized_pnl | market_value - cost_basis |
| source | 估值依据 |

每个账户快照日期都提交完整持仓列表。当天无持仓则没有该日持仓行，daily-assets.positions_market_value 必须为零。未平仓交易各自一行；同一标的不同策略分别列出后再汇总。

## 行为事件 behavior-events.csv

| 字段 | 含义 |
|---|---|
| behavior_id | 唯一编号 |
| event_at / recorded_at | 行为发生时间及录入时间，避免事后记录伪装成事前记录 |
| trade_id | 关联交易 |
| behavior_type | EARLY_EXIT / UNPLANNED_ENTRY / STOP_MOVED / UNPLANNED_ADD / OVERTRADING / PLAN_ADHERENCE / OTHER |
| is_deviation | true / false / unknown，按事前计划判断 |
| description | 当时行为与依据，不凭亏损推测情绪 |
| review_path | 复盘文档路径，可留空 |

同一交易可有多个事件。没有偏差事件不代表已核实遵守计划；周报另外记录已审查交易数量和资料缺失数量。

## 可选期初批次 opening-lots.csv

期初无持仓时文件可以省略或只含表头；有期初持仓时必须提供可核对的批次。

| 字段 | 含义 |
|---|---|
| lot_id | 批次唯一编号 |
| trade_id | 关联仍持有的完整交易 |
| acquired_at | 实际历史买入时间，不能晚于期初基准；不早于交易 opened_at |
| quantity | 基准时该批次仍持有的正数数量 |
| cost_basis | 基准时该批次剩余总成本，含分配后的买入费用 |

它是**基准日剩余批次**，不是把全部历史买单重新录入。按 trade_id 合计的数量与 cost_basis 必须等于第一张 positions-daily 快照。多个历史批次分别保留时间以确定 FIFO 顺序，不合并成虚构的新买入。

跨年使用同一 trade_id、原始 opened_at 和剩余历史批次；新年度卖出使用保留的成本核算。完全平仓交易的完整生命周期 R，需要足够的生命周期记录；年度片段不能冒充完整交易。

## 可选券商收益指数 broker-performance.csv

| 字段 | 含义 |
|---|---|
| date | 当地估值日期，覆盖相同账户快照区间 |
| account_id | 与 dataset.json 一致 |
| return_index | 正数、连续的券商账户 TWR 指数，不是净资产金额 |
| benchmark_index | 同期正数基准指数；可以留空，缺失时不展示基准线 |
| currency | 与配置一致；基准应使用可比较的币种与收益口径 |
| basis | 固定为 TWR_INDEX |
| coverage | 第一行 baseline，后续 complete；complete 表示自上一点至本点的完整区间 |
| source | 券商报告或导出依据；示例明确为虚构 |

该文件的指数应在账户快照日期上完整对齐。第一行 baseline 建立指数起点；后续不能重设基准、拼接不同来源或跨越未知收益期间。`complete` 是输入者对区间完整性的声明，程序无法证明数据来源真实。

缺少日期、重复 baseline 或存在非 complete 区间时，报告警告并停用合并收益曲线、收益回撤和月度收益图，保留金额及行为图。基准只要不完整，就省略整条基准线，不用插值补造。

指数可以从 100 或其他正数开始；展示时归一到 100。月度图计算实际覆盖区间的首末指数变化，明确写出起止日期，不把部分月份称为完整月收益。回撤只针对提供的指数历史计算，不代表更早时期的回撤。

## 可选回测目录

回测属于独立数据源，不混入真实成交表。通过 `--backtest-dir` 指定包含 metadata.json 和 equity.csv 的目录。空白模板位于 `templates/backtest/`，示例位于 `examples/backtests/demo-run/`。

### metadata.json

| 字段 | 含义 |
|---|---|
| schema_version | 2 |
| run_id / label | 本次运行编号与显示名称 |
| currency | 回测记账币种 |
| strategy_id / strategy_version | 回测策略及版本 |
| source | 回测工具、导出文件或研究依据 |
| costs.commission / costs.slippage | 明确说明手续费和滑点假设；不是由本程序补扣费用 |
| notes | 数据、估值、成交模型、样本限制等说明 |
| initial_capital | 正数期初模拟资本，用于标示回测背景 |
| flow_policy | 固定 NONE；本版回测文件不支持期间资金进出 |
| continuous_index | 必须为 true；确认指数连续，样本分区没有重置本金或净值 |

### equity.csv

| 字段 | 含义 |
|---|---|
| run_id | 与 metadata.json 相同 |
| date | 唯一且递增的估值日期 |
| return_index | 正数、连续、已反映元数据所列成本的回测指数 |
| benchmark_index | 可选正数同期基准指数；不完整时省略基准 |
| phase | IS（样本内）或 OOS（样本外），按真实测试设计填写 |

IS/OOS 是来源提供的分区标签，本程序只负责展示。它不实施训练、不检查模型是否偷看未来、不验证参数稳健性，也不自动执行回测。不同运行或重新开始的 OOS 曲线不能靠标注 continuous_index 强行连接。
