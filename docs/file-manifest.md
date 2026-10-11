# Complete File Manifest 完整文件清单

本清单对应 Backtest-Review-System 的全部发布文件。真实账户记录和 Python 缓存不属于发布内容。

| 文件 | 用途 |
|---|---|
| [`.github/workflows/check.yml`](../.github/workflows/check.yml) | GitHub 自动检查 |
| [`.gitignore`](../.gitignore) | 真实记录及本地产物排除规则 |
| [`COPY_CONTENTS.md`](../COPY_CONTENTS.md) | 全部文件的手动复制版本 |
| [`README.md`](../README.md) | 项目入口与使用说明 |
| [`demo/report.html`](../demo/report.html) | 13 张图表的虚构离线报告 |
| [`docs/accounting-rules.md`](../docs/accounting-rules.md) | 使用与技术说明 |
| [`docs/data-dictionary.md`](../docs/data-dictionary.md) | 使用与技术说明 |
| [`docs/file-manifest.md`](../docs/file-manifest.md) | 完整文件清单 |
| [`docs/github-setup.md`](../docs/github-setup.md) | 使用与技术说明 |
| [`docs/visualization-guide.md`](../docs/visualization-guide.md) | 使用与技术说明 |
| [`examples/2026/behavior-events.csv`](../examples/2026/behavior-events.csv) | 虚构示例数据 |
| [`examples/2026/broker-performance.csv`](../examples/2026/broker-performance.csv) | 虚构示例数据 |
| [`examples/2026/cash-events.csv`](../examples/2026/cash-events.csv) | 虚构示例数据 |
| [`examples/2026/daily-assets.csv`](../examples/2026/daily-assets.csv) | 虚构示例数据 |
| [`examples/2026/dataset.json`](../examples/2026/dataset.json) | 虚构示例数据 |
| [`examples/2026/fills.csv`](../examples/2026/fills.csv) | 虚构示例数据 |
| [`examples/2026/opening-lots.csv`](../examples/2026/opening-lots.csv) | 虚构示例数据 |
| [`examples/2026/positions-daily.csv`](../examples/2026/positions-daily.csv) | 虚构示例数据 |
| [`examples/2026/review.md`](../examples/2026/review.md) | 虚构示例数据 |
| [`examples/2026/strategies.csv`](../examples/2026/strategies.csv) | 虚构示例数据 |
| [`examples/2026/trade-TR-001.md`](../examples/2026/trade-TR-001.md) | 虚构示例数据 |
| [`examples/2026/trades.csv`](../examples/2026/trades.csv) | 虚构示例数据 |
| [`examples/backtests/demo-run/equity.csv`](../examples/backtests/demo-run/equity.csv) | 虚构示例数据 |
| [`examples/backtests/demo-run/metadata.json`](../examples/backtests/demo-run/metadata.json) | 虚构示例数据 |
| [`templates/annual-review.md`](../templates/annual-review.md) | 空白记录或配置模板 |
| [`templates/backtest/equity.csv`](../templates/backtest/equity.csv) | 空白记录或配置模板 |
| [`templates/backtest/metadata.json`](../templates/backtest/metadata.json) | 空白记录或配置模板 |
| [`templates/behavior-events.csv`](../templates/behavior-events.csv) | 空白记录或配置模板 |
| [`templates/broker-performance.csv`](../templates/broker-performance.csv) | 空白记录或配置模板 |
| [`templates/cash-events.csv`](../templates/cash-events.csv) | 空白记录或配置模板 |
| [`templates/daily-assets.csv`](../templates/daily-assets.csv) | 空白记录或配置模板 |
| [`templates/dataset.json`](../templates/dataset.json) | 空白记录或配置模板 |
| [`templates/fills.csv`](../templates/fills.csv) | 空白记录或配置模板 |
| [`templates/opening-lots.csv`](../templates/opening-lots.csv) | 空白记录或配置模板 |
| [`templates/positions-daily.csv`](../templates/positions-daily.csv) | 空白记录或配置模板 |
| [`templates/strategies.csv`](../templates/strategies.csv) | 空白记录或配置模板 |
| [`templates/strategy.md`](../templates/strategy.md) | 空白记录或配置模板 |
| [`templates/trade-review.md`](../templates/trade-review.md) | 空白记录或配置模板 |
| [`templates/trades.csv`](../templates/trades.csv) | 空白记录或配置模板 |
| [`templates/weekly-review.md`](../templates/weekly-review.md) | 空白记录或配置模板 |
| [`tests/__init__.py`](../tests/__init__.py) | 核算验证 |
| [`tests/test_ledger.py`](../tests/test_ledger.py) | 核算验证 |
| [`trading_journal/__init__.py`](../trading_journal/__init__.py) | 核算与报告程序 |
| [`trading_journal/__main__.py`](../trading_journal/__main__.py) | 核算与报告程序 |
| [`trading_journal/charts.py`](../trading_journal/charts.py) | 核算与报告程序 |
| [`trading_journal/ledger.py`](../trading_journal/ledger.py) | 核算与报告程序 |

共 **46 个文件**。GitHub 网页中的 HTML 是源文件；下载整个仓库后打开 `demo/report.html` 即可看到图表。

创建真实记录时，复制 templates 中的核心 CSV、dataset.json 及可选文件到本地 records/2026；不要用 examples 的虚构行代替自己的记录。
