"""Run with: python3 -m trading_journal --data-dir examples/2026 --output output/report.html"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from .ledger import DataError, build_report
from .charts import render_report


def main() -> int:
    parser = argparse.ArgumentParser(description="生成个人交易与资产的离线图表报告；不需要网络或 API。")
    parser.add_argument("--data-dir", type=Path, required=True, help="包含 dataset.json 与记录 CSV 的目录")
    parser.add_argument("--output", type=Path, required=True, help="输出 HTML 文件路径")
    parser.add_argument("--backtest-dir", type=Path, help="可选回测目录，包含 metadata.json 与 equity.csv")
    args = parser.parse_args()
    temporary = None
    try:
        report = build_report(args.data_dir, args.backtest_dir)
        content = render_report(report)
        output = args.output.resolve()
        if output.suffix.lower() != ".html":
            raise DataError("报告输出文件必须使用 .html 后缀。")
        if output == Path(__file__).resolve() or output.is_dir():
            raise DataError("输出路径无效。")
        output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, prefix=".report-", suffix=".tmp", delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(content)
        os.replace(temporary, output)
        temporary = None
        print(f"报告已生成：{output}")
        print(f"期间净投资损益：{report['summary']['net_pnl']:.2f} {report['currency']}")
        print("请用浏览器打开 HTML 文件；虚构示例与真实账户数据分别保存。")
        return 0
    except (DataError, OSError) as exc:
        print(f"未生成报告：{exc}")
        return 1
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
