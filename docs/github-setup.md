# 一步一步建立 GitHub 项目

本次目标仓库：[CJA231/Backtest-Review-System](https://github.com/CJA231/Backtest-Review-System)。该仓库已由你创建并选定，公开仓库只上传模板、程序与虚构示例。直接从第 3 步添加文件；第 2 步用于以后新建仓库时参考。

## 输入、结果与预计成本

| 项目 | 说明 |
|---|---|
| 输入 | GitHub 账户、本项目全部文件、自己的电脑 |
| 结果 | 模板与程序仓库，以及可在浏览器查看的本地 HTML 报告 |
| 建立时间 | 批量上传约 15–30 分钟；逐文件复制约 1–2 小时 |
| 依赖 | 浏览器、网络；运行程序建议 Python 3.11+ |
| API 成本 | 无行情或 AI API 费用 |
| 风险 | 文件遗漏、CSV 数据错误、个人资料误上传、旧报告被当作新结果 |
| 自动化 | 本版可核对记录并生成报告；没有自动下载行情或交易下单 |

GitHub 保存与展示源文件。Python 在自己的电脑执行，生成的 HTML 在自己的浏览器打开；上传文件不等于发布可运行的网站。本流程没有配置 GitHub Pages。

## 1 确定仓库用途

| 用途 | 可见性 | 应放内容 |
|---|---|---|
| 发布模板和程序 | Public | 模板、说明、程序、测试、虚构示例 |
| 管理自己的真实交易 | Private | 上述文件加自己的真实记录和报告 |

需要公开分享项目，同时管理真实交易时，建议保留一个 Public 模板仓库，再建立一个 Private 个人仓库。模板仓库不上传券商原始文件、真实持仓、账户编号和密钥。

## 2 创建仓库

打开 [GitHub 新建仓库](https://github.com/new)。

| 项目 | 建议填写 |
|---|---|
| Repository name | `Backtest-Review-System` |
| Description | `Trading records, asset tracking, behavior reviews and offline visualization.` |
| Visibility | 按第 1 步选择 Public 或 Private |
| README | 手动复制流程可勾选初始化 README，稍后替换 |
| License | 按自己希望授权的使用范围选择；不确定时先不添加 |

点击 **Create repository**。公开可见不等于已授予开源使用许可；选择许可证是独立决定。[GitHub 创建仓库说明](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-new-repository)

## 3A 逐个手动复制文件

这是你希望自己复制建立项目的方式。

1. 打开交付的 `COPY_CONTENTS.md`，先看对应文件路径，再复制该文件的完整内容。
2. 仓库首页打开 `README.md`，点击编辑图标，替换正文，预览后点击 **Commit changes**。
3. 其他文件点击 **Add file → Create new file**。
4. 文件名填写完整相对路径，例如 `trading_journal/ledger.py`。
5. 粘贴对应文件内容。只复制内容，不复制包围内容的反引号围栏。
6. 点击 **Commit changes**，提交说明写明新增的文件或模块。
7. 重复，直到 [完整文件清单](file-manifest.md) 中的项目文件全部建立。

GitHub 会根据文件名中的 `/` 创建文件夹；也能创建 `.gitignore` 和 `.github/workflows/check.yml`。本版没有需要手动创建的空文件夹。

简单个人仓库可以提交到当前分支；有分支保护时建立新分支，再创建并合并 pull request。[GitHub 创建文件说明](https://docs.github.com/en/repositories/working-with-files/managing-files/creating-new-files)

推荐顺序：

| 顺序 | 文件组 | 原因 |
|---|---|---|
| 1 | README.md、.gitignore | 建立首页和本地忽略规则 |
| 2 | docs/ | 建立流程、数据与图表说明 |
| 3 | templates/ | 空白配置、七张核心 CSV、可选表和文档模板 |
| 4 | trading_journal/ | 添加完整报告程序，四个文件都需要 |
| 5 | examples/2026/ | 添加可直接运行的虚构账户示例 |
| 6 | examples/backtests/demo-run/ | 添加独立回测展示示例 |
| 7 | tests/、.github/workflows/check.yml | 添加自动检查 |
| 8 | demo/report.html | 可选预生成示例；本地打开即可查看 |

`COPY_CONTENTS.md` 是复制辅助文件，可不上传。其正文中的相对链接按目标文件的位置解释，不是按复制包的位置解释。CSV 保留第一行表头及字段顺序；JSON 不能加入注释或尾逗号；Python 文件保留缩进。

## 3B 使用压缩包批量上传

如果逐个复制太耗时，可以使用这条路径：

1. 下载并解压交付的项目压缩包。
2. 进入包含 `README.md` 与 `trading_journal/` 的项目目录。
3. 在 GitHub 点击 **Add file → Upload files**。
4. 上传项目目录内的文件和子目录，使 `README.md` 位于仓库根目录，避免多包一层目录。
5. 显示隐藏文件，单独检查 `.gitignore` 与 `.github/workflows/check.yml`；遗漏时按 3A 创建。
6. 提交前检查上传列表，确认只有模板、代码和虚构示例。

GitHub 网页上传有数量和大小限制，遇到提示时分批上传。[GitHub 上传文件说明](https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository)

## 4 检查 GitHub 文件是否齐全

- [ ] README 的文档链接和 Mermaid 图正常显示。
- [ ] `trading_journal/` 的四个程序文件齐全。
- [ ] 七张核心 CSV、dataset.json 和示例文件与文件清单一致。
- [ ] 示例账户是 DEMO-01，真实资料未混入。
- [ ] 期初净资产 100000 MYR，期末 110111 MYR，扣除净入金后损益 111 MYR。
- [ ] GitHub 的 Actions 页面可以看到检查结果；若失败，先阅读错误再修正文件。

网页检查只能确认文件和自动检查状态；本地报告仍要按后续步骤实际运行。

## 5 下载到自己的电脑

打开 [Backtest-Review-System 仓库](https://github.com/CJA231/Backtest-Review-System)，点击 **Code → Download ZIP**，解压到你容易找到的位置。[GitHub 下载源代码说明](https://docs.github.com/en/repositories/working-with-files/using-files/downloading-source-code-archives)

**立即预览无需安装 Python：**解压后进入项目目录，双击 `demo/report.html`，用浏览器打开预生成的虚构报告。下载的 ZIP 常使用 `Backtest-Review-System-main` 等目录名，以实际分支为准。这个报告在本地浏览，不是已发布的在线网站。

打开解压后的文件夹，确认其中直接包含：

```text
README.md
templates/
examples/
trading_journal/
tests/
```

在这个文件夹中打开终端。macOS/Linux 使用下面的命令；Windows 可把 `python3` 替换为 `py -3`，或使用已配置的 `python`。

```bash
python3 --version
```

建议版本为 3.11 或以上。如未安装，从 [Python 官方下载页](https://www.python.org/downloads/) 安装，再重新打开终端。本项目没有 `pip install` 步骤。

## 6 运行虚构示例

```bash
python3 -m trading_journal --data-dir examples/2026 --output output/demo-report.html --backtest-dir examples/backtests/demo-run
```

成功后双击 `output/demo-report.html`，使用浏览器打开。报告将展示资产、现金与持仓、资金变化、策略金额贡献、频次、行为、R 分布、持有时间、券商示例收益指数及回测示例。

也可直接下载 `demo/report.html` 并在本地打开预生成示例。GitHub 普通文件页面展示 HTML 源码，不会把它自动变成交互网页。

运行项目检查：

```bash
python3 -m unittest discover -s tests -v
```

检查结果用于发现核算和程序问题，不代表策略收益有效，也不验证输入来源的真实性。

## 7 创建自己的真实记录

在 Private 仓库或自己电脑的私密目录中建立：

```text
records/2026/              # dataset.json、七张核心 CSV、需要时的可选表
strategies/               # 策略及版本文档
journal/2026/             # 事前计划与每笔复盘
reports/2026/weekly/      # 每周 Markdown 复盘
reports/2026/annual.md    # 年度 Markdown 复盘
private/broker-exports/   # 原始券商文件，只做私密保存
```

具体操作：

1. 从 `templates/` 复制 dataset.json 和七张仅含表头的核心 CSV 到 `records/2026/`。
2. 修改配置中的 `account_id`、`currency`、`timezone_offset`；真实记录设 `fictional: false`，保留 `cost_method: "FIFO"`。
3. 填写第一个日末资产快照，作为期间基准。有持仓时，同时填写该日完整持仓和 opening-lots.csv 的历史批次。
4. 资金与成交 CSV 只填写基准日之后的事件；已有持仓成本由期初批次提供，不重复录入旧买单。
5. 建立策略版本和交易资料，复制策略与复盘文档模板。跨年未平仓交易保持原 trade_id。
6. 后续每个交易日保存完整资产和持仓；无持仓时资产表的持仓市值为零，不添加零数量持仓行。
7. 有可靠券商 TWR 指数时添加 broker-performance.csv；没有时可暂不提供，不影响金额及行为图。

不要把虚构示例改成真实交易来省步骤，也不要把未知字段填零。[字段字典](data-dictionary.md) 解释每个文件，[核算规则](accounting-rules.md) 解释期初和跨年处理。

`.gitignore` 忽略本地 records、private、output 等目录，避免常规 Git 操作误提交。**它不阻止网页手动上传，也不会删除已经提交的历史。**确实希望在 Private 仓库通过 Git 同步记录时，先确认仓库私有，再有选择地修改对应忽略项；券商原始文件仍建议独立私密备份。[GitHub 忽略文件说明](https://docs.github.com/en/get-started/git-basics/ignoring-files)

## 8 生成真实报告

```bash
python3 -m trading_journal --data-dir records/2026 --output output/2026-report.html
```

打开输出文件，先看数据性质、区间和核对状态，再看图表。数据错误时程序提示具体文件或记录，按券商依据修正后重跑。失败后已有的旧 HTML 可能仍在，不能当成最新报告。

收益数据缺失或存在覆盖断点时，会保留金额及行为图，提示收益图不可用。需要展示独立回测时，按 [图表指南](visualization-guide.md) 准备回测目录，然后附加 `--backtest-dir` 参数。

## 9 日常、每周与年度维护

| 时间 | 操作 | 输出 |
|---|---|---|
| 交易前 | 写计划，固定策略版本和 initial_risk | 可追溯交易依据 |
| 成交后 | 更新成交和交易状态，记录行为 | 完整成交链 |
| 收盘后 | 更新资金、账户、持仓，重跑报告 | 最新资产图与核对结果 |
| 每周 | 查看频次和行为，填写周复盘 | reports/2026/weekly/YYYY-Www.md |
| 年末 | 归档全年图表和原始证据，填写年度复盘 | 年度报告与下一年期初数据 |

跨年时，用上一年末可用日末估值作为下一年基准，复制仍未平仓的交易资料和历史批次，保留真实成本。跨年资料重复引用不算新建交易。未实现损益不清零，已实现和费用 YTD 按新年度口径处理。

## 10 常见问题

| 情况 | 处理 |
|---|---|
| `No module named trading_journal` | 确认终端当前目录直接包含 trading_journal 文件夹，检查四个文件是否齐全 |
| 提示没有 dataset.json | 将配置放在 --data-dir 指定目录内，而不是仓库根目录 |
| CSV 核对失败 | 按错误核对编号、时间、费用、期初批次、数量和现金，不为通过检查而改造原始事实 |
| 找不到报告 | 检查命令是否成功，以及 output 文件夹；失败不会产生新的有效报告 |
| 没有收益和回撤图 | 检查 broker-performance 的 TWR_INDEX、baseline、complete 覆盖和连续性 |
| 月度图只显示部分月份 | 数据只能覆盖所提供的期间，部分月份会明确标注 |
| GitHub 中打开 HTML 看到代码 | 下载后在自己的浏览器打开；普通仓库页面不运行 HTML 应用 |
| 想发布在线仪表板 | 作为后续部署工作单独处理；公开模板仓库不应直接使用真实资产数据 |
