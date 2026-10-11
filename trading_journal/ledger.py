"""Validate a cash-stock ledger and prepare data for an offline report.

Money is computed with Decimal. Return indexes are supplied inputs: no TWR is
inferred from account balances. This is a reporting ledger, not a trading engine.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ZERO = Decimal("0")
TOL = Decimal("0.02")

SCHEMAS = {
    "cash-events.csv": "event_id,timestamp,account_id,event_type,amount,trade_id,note",
    "fills.csv": "fill_id,broker_fill_id,broker_order_id,trade_id,timestamp,side,quantity,price,fees",
    "trades.csv": "trade_id,account_id,symbol,strategy_id,strategy_version,opened_at,closed_at,planned_entry,planned_stop,initial_risk,status,plan_path",
    "daily-assets.csv": "date,account_id,cash,positions_market_value,nav,external_flow,realized_pnl_ytd,unrealized_pnl,fees_ytd,source",
    "positions-daily.csv": "date,account_id,trade_id,symbol,quantity,mark_price,cost_basis,market_value,unrealized_pnl,source",
    "strategies.csv": "strategy_id,version,name,active_from,active_to,rules_path",
    "behavior-events.csv": "behavior_id,event_at,recorded_at,trade_id,behavior_type,is_deviation,description,review_path",
    "opening-lots.csv": "lot_id,trade_id,acquired_at,quantity,cost_basis",
    "broker-performance.csv": "date,account_id,return_index,benchmark_index,currency,basis,coverage,source",
    "equity.csv": "run_id,date,return_index,benchmark_index,phase",
}


class DataError(ValueError):
    """An input cannot be reconciled or is outside the documented data scope."""


def number(value: str, field: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise DataError(f"{field}: 需要有效数字，不能使用空值。") from None
    if not result.is_finite():
        raise DataError(f"{field}: 不能使用 NaN 或无穷大。")
    return result


def iso_date(value: str) -> date:
    try:
        result = date.fromisoformat(value)
    except ValueError:
        raise DataError(f"无效日期：{value}") from None
    if result.isoformat() != value:
        raise DataError(f"日期必须为 YYYY-MM-DD：{value}")
    return result


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise DataError(f"无效时间：{value}") from None
    if result.tzinfo is None:
        raise DataError(f"时间必须包含时区偏移：{value}")
    return result


def offset_timezone(value: str) -> timezone:
    if not isinstance(value, str) or len(value) != 6 or value[0] not in "+-" or value[3] != ":":
        raise DataError("timezone_offset 必须为 +08:00 等固定偏移。")
    try:
        hours, minutes = int(value[1:3]), int(value[4:6])
    except ValueError:
        raise DataError("timezone_offset 无效。") from None
    if hours > 23 or minutes > 59:
        raise DataError("timezone_offset 超出范围。")
    return timezone(timedelta(minutes=(hours * 60 + minutes) * (1 if value[0] == "+" else -1)))


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise DataError(f"无法读取 {path.name}：{exc}") from None
    if not isinstance(data, dict):
        raise DataError(f"{path.name} 必须是 JSON 对象。")
    return data


def load_csv(folder: Path, name: str, optional: bool = False) -> list[dict]:
    path = folder / name
    if optional and not path.exists():
        return []
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            expected = SCHEMAS[name].split(",")
            if reader.fieldnames != expected:
                raise DataError(f"{name} 表头必须为：{SCHEMAS[name]}")
            rows = []
            for row in reader:
                if None in row or any(v is None for v in row.values()):
                    raise DataError(f"{name} 第 {reader.line_num} 行列数错误。")
                row = {k: v.strip() for k, v in row.items()}
                if any(row.values()):
                    rows.append(row)
            return rows
    except OSError as exc:
        raise DataError(f"无法读取 {name}：{exc}") from None


def unique(rows: list[dict], keys: tuple[str, ...], label: str) -> None:
    seen = set()
    for row in rows:
        key = tuple(row[k] for k in keys)
        if any(not part for part in key) or key in seen:
            raise DataError(f"{label} 编号为空或重复：{key}")
        seen.add(key)


def equal(actual: Decimal, expected: Decimal, label: str, tolerance: Decimal = TOL) -> None:
    if abs(actual - expected) > tolerance:
        raise DataError(f"{label} 对账失败：计算值 {actual}，记录值 {expected}。")


def index_analytics(rows: list[dict]) -> dict:
    """Use a complete supplied index; preserve its coverage rather than extrapolate."""
    initial = rows[0]["index"]
    benchmark = rows[0]["benchmark_index"]
    complete_benchmark = all(r["benchmark_index"] is not None for r in rows)
    normalized = []
    peak = Decimal("100")
    for row in rows:
        index = row["index"] / initial * 100
        peak = max(peak, index)
        normalized.append({
            "date": row["date"], "index": float(index),
            "benchmark_index": float(row["benchmark_index"] / benchmark * 100) if complete_benchmark else None,
            "drawdown_pct": float((index / peak - 1) * 100),
            **({"phase": row["phase"]} if "phase" in row else {}),
        })
    monthly = []
    for row_index, row in enumerate(rows[1:], start=1):
        month = row["date"][:7]
        if not monthly or monthly[-1]["month"] != month:
            previous = rows[row_index - 1]
            monthly.append({"month": month, "start_date": previous["date"], "end_date": row["date"], "start_index": previous["index"], "end_index": row["index"]})
        else:
            monthly[-1]["end_date"] = row["date"]
            monthly[-1]["end_index"] = row["index"]
    for item in monthly:
        item["return_pct"] = float((item.pop("end_index") / item.pop("start_index") - 1) * 100)
        item["label"] = item["month"] + "（月内覆盖区间）"
    return {
        "rows": normalized, "monthly": monthly,
        "total_return_pct": float((rows[-1]["index"] / initial - 1) * 100),
        "max_drawdown_pct": min(r["drawdown_pct"] for r in normalized),
    }


def load_performance(folder: Path, metadata: dict, start: date, end: date, warnings: list[str], snapshot_dates: set[date] | None = None) -> dict | None:
    rows = load_csv(folder, "broker-performance.csv", optional=True)
    if not rows:
        warnings.append("没有可用 TWR 指数：收益率、收益回撤和月内收益图暂不生成。资产金额仍可核对。")
        return None
    unique(rows, ("date", "account_id"), "收益指数")
    parsed = []
    for row in rows:
        day = iso_date(row["date"])
        if row["account_id"] != metadata["account_id"] or row["currency"] != metadata["currency"]:
            raise DataError("收益指数的账户或币种与 dataset.json 不一致。")
        if row["basis"] != "TWR_INDEX" or row["coverage"] not in {"baseline", "complete", "gap"} or not row["source"]:
            raise DataError("收益指数必须注明 TWR_INDEX、有效 coverage 和 source。")
        index = number(row["return_index"], "return_index")
        benchmark = number(row["benchmark_index"], "benchmark_index") if row["benchmark_index"] else None
        if index <= 0 or (benchmark is not None and benchmark <= 0):
            raise DataError("收益与基准指数必须为正数。")
        parsed.append({**row, "day": day, "index": index, "benchmark_index": benchmark})
    parsed.sort(key=lambda r: r["day"])
    if len(parsed) < 2 or parsed[0]["coverage"] != "baseline" or any(r["coverage"] != "complete" for r in parsed[1:]):
        warnings.append("收益指数存在缺口、重启或缺少基准点；本版不连接不同区间，不生成合并收益率与回撤。")
        return None
    if parsed[0]["day"] != start or parsed[-1]["day"] != end:
        warnings.append("收益指数与账户报告起止日期不同；暂不展示混合区间的收益率。请提供同区间指数。")
        return None
    if snapshot_dates is not None and not snapshot_dates <= {r["day"] for r in parsed}:
        warnings.append("收益指数缺少账户快照日期；日期覆盖不完整，不生成合并收益率与收益回撤。")
        return None
    if not all(r["benchmark_index"] is not None for r in parsed):
        warnings.append("基准指数不完整，基准对照线省略，不补零或向前填充。")
    if len({r["source"] for r in parsed}) != 1:
        warnings.append("收益指数包含多个来源，请人工确认口径和连续性。")
    result = index_analytics(parsed)
    result.update(source="; ".join(sorted({r["source"] for r in parsed})), basis="TWR_INDEX")
    return result


def load_backtest(folder: Path | None, currency: str) -> dict | None:
    if folder is None:
        return None
    metadata = load_json(folder / "metadata.json")
    required = {"schema_version", "run_id", "label", "currency", "strategy_id", "strategy_version", "source", "costs", "notes", "initial_capital", "flow_policy", "continuous_index"}
    if not required <= metadata.keys() or metadata["schema_version"] != 2:
        raise DataError("回测 metadata.json 缺少必需字段或版本不为 2。")
    if metadata["currency"] != currency or metadata["flow_policy"] != "NONE" or metadata["continuous_index"] is not True:
        raise DataError("回测必须同币种、无外部资金流并使用同一次运行的连续指数。")
    if number(metadata["initial_capital"], "initial_capital") <= 0:
        raise DataError("回测初始资本必须为正数。")
    if not isinstance(metadata["costs"], dict) or not {"commission", "slippage"} <= metadata["costs"].keys():
        raise DataError("回测需注明 commission 和 slippage 成本假设。")
    if not metadata["run_id"] or not metadata["source"]:
        raise DataError("回测必须注明运行编号和数据来源。")
    rows = load_csv(folder, "equity.csv")
    unique(rows, ("date",), "回测日期")
    if len(rows) < 2:
        raise DataError("回测至少需要两个净值点。")
    parsed = []
    for row in rows:
        iso_date(row["date"])
        index = number(row["return_index"], "回测 return_index")
        benchmark = number(row["benchmark_index"], "回测 benchmark_index") if row["benchmark_index"] else None
        if row["run_id"] != metadata["run_id"] or row["phase"] not in {"IS", "OOS"} or index <= 0 or (benchmark is not None and benchmark <= 0):
            raise DataError("回测行编号、阶段或指数无效。")
        parsed.append({**row, "index": index, "benchmark_index": benchmark})
    parsed.sort(key=lambda r: r["date"])
    phases = [r["phase"] for r in parsed]
    if "OOS" in phases and "IS" in phases[phases.index("OOS"):]:
        raise DataError("单次回测阶段只能从 IS 转为 OOS，不能交替拼接不同测试。")
    result = index_analytics(parsed)
    result.update(run_id=metadata["run_id"], label=metadata["label"], currency=currency,
                  strategy=f"{metadata['strategy_id']}/{metadata['strategy_version']}",
                  source=metadata["source"], costs=metadata["costs"], notes=metadata["notes"])
    return result


def build_report(data_dir: Path, backtest_dir: Path | None = None) -> dict:
    folder = Path(data_dir)
    metadata = load_json(folder / "dataset.json")
    required = {"schema_version", "account_id", "currency", "timezone_offset", "fictional", "cost_method"}
    if not required <= metadata.keys() or metadata["schema_version"] != 2 or metadata["cost_method"] != "FIFO" or type(metadata["fictional"]) is not bool:
        raise DataError("dataset.json 必須包含版本 2、账户、币种、时区偏移、fictional 布尔值与 FIFO 成本方法。")
    if not isinstance(metadata["account_id"], str) or not isinstance(metadata["currency"], str) or not metadata["account_id"] or not metadata["currency"]:
        raise DataError("账户与币种不能为空。")
    tz = offset_timezone(metadata["timezone_offset"])
    account = metadata["account_id"]
    data = {name: load_csv(folder, name) for name in list(SCHEMAS)[:7]}
    fills, events, trades = data["fills.csv"], data["cash-events.csv"], data["trades.csv"]
    snapshots, positions, strategies = data["daily-assets.csv"], data["positions-daily.csv"], data["strategies.csv"]
    behaviors = data["behavior-events.csv"]
    for name, key in [("fills.csv", "fill_id"), ("cash-events.csv", "event_id"), ("trades.csv", "trade_id"), ("behavior-events.csv", "behavior_id")]:
        unique(data[name], (key,), name)
    unique([f for f in fills if f["broker_fill_id"]], ("broker_fill_id",), "券商成交编号")
    unique(strategies, ("strategy_id", "version"), "策略")
    unique(snapshots, ("date", "account_id"), "资产快照")
    unique(positions, ("date", "account_id", "trade_id"), "持仓快照")
    if len(snapshots) < 2:
        raise DataError("至少需要一个日末期初基准和一个期末快照。")
    strategy_keys = {(s["strategy_id"], s["version"]) for s in strategies}
    trade_map = {t["trade_id"]: t for t in trades}
    for t in trades:
        if t["account_id"] != account or (t["strategy_id"], t["strategy_version"]) not in strategy_keys or not t["symbol"]:
            raise DataError(f"交易 {t['trade_id']} 的账户、策略或标的无效。")
        t["open_dt"] = timestamp(t["opened_at"]).astimezone(tz)
        t["close_dt"] = timestamp(t["closed_at"]).astimezone(tz) if t["closed_at"] else None
        if t["status"] not in {"OPEN", "CLOSED"} or (t["status"] == "CLOSED") != bool(t["close_dt"]):
            raise DataError(f"交易 {t['trade_id']} 状态与关闭时间不一致。")
        if t["close_dt"] and t["close_dt"] < t["open_dt"]:
            raise DataError("交易关闭时间不能早于开仓。")
        t["risk"] = number(t["initial_risk"], "initial_risk") if t["initial_risk"] else ZERO
        if t["risk"] < 0:
            raise DataError("initial_risk 不能为负数。")
    for s in snapshots:
        s["day"] = iso_date(s["date"])
        if s["account_id"] != account:
            raise DataError("每日资产包含不同账户。")
        for field in ("cash", "positions_market_value", "nav", "external_flow", "realized_pnl_ytd", "unrealized_pnl", "fees_ytd"):
            s[field] = number(s[field], field)
        if s["cash"] < 0 or s["positions_market_value"] < 0 or s["fees_ytd"] < 0:
            raise DataError("本版现金账户不支持负现金、负持仓市值或负费用。")
        equal(s["cash"] + s["positions_market_value"], s["nav"], s["date"] + " NAV")
    snapshots.sort(key=lambda s: s["day"])
    start, end = snapshots[0]["day"], snapshots[-1]["day"]
    days = {s["day"] for s in snapshots}
    warnings = ["报告为单账户、单币种、做多现金股票的记录分析；不包含自动下单、税务核算或自动回测。"]
    warnings.append("快照日期由用户提供，程序不能核实交易日历与券商数据是否完整；报告仅覆盖标注区间。")
    position_days = defaultdict(list)
    for p in positions:
        day = iso_date(p["date"])
        if day not in days or p["account_id"] != account or p["trade_id"] not in trade_map or p["symbol"] != trade_map[p["trade_id"]]["symbol"]:
            raise DataError("持仓快照的日期、账户、交易或标的不匹配。")
        for key in ("quantity", "mark_price", "cost_basis", "market_value", "unrealized_pnl"):
            p[key] = number(p[key], key)
        if p["quantity"] <= 0 or p["mark_price"] < 0 or p["cost_basis"] < 0:
            raise DataError("持仓数量必须为正；成本和估值不能为负。")
        position_days[day].append(p)
    opening = load_csv(folder, "opening-lots.csv", optional=True)
    unique(opening, ("lot_id",), "期初成本批次")
    lots = defaultdict(deque)
    for row in sorted(opening, key=lambda r: timestamp(r["acquired_at"])):
        tid = row["trade_id"]
        acquired = timestamp(row["acquired_at"]).astimezone(tz)
        qty, cost = number(row["quantity"], "opening quantity"), number(row["cost_basis"], "opening cost_basis")
        if tid not in trade_map or acquired.date() > start or trade_map[tid]["open_dt"] > acquired or qty <= 0 or cost < 0:
            raise DataError("期初批次必须关联已有交易，取得时间不晚于基准，数量为正、成本非负。")
        lots[tid].append([qty, cost / qty])
    if snapshots[0]["positions_market_value"] != 0 and not opening:
        raise DataError("非空仓期初必须提供 opening-lots.csv 和期初持仓快照，不能推造历史成本。")
    def snapshot_check(s):
        ps = position_days[s["day"]]
        active = {tid for tid, queue in lots.items() if queue}
        if active != {p["trade_id"] for p in ps}:
            raise DataError(s["date"] + "：持仓快照与实际剩余交易不一致。")
        market_value, unrealized = ZERO, ZERO
        by_trade = {}
        for p in ps:
            qty = sum((lot[0] for lot in lots[p["trade_id"]]), ZERO)
            cost = sum((lot[0] * lot[1] for lot in lots[p["trade_id"]]), ZERO)
            equal(qty, p["quantity"], p["trade_id"] + " 数量", Decimal("0.00000001"))
            equal(cost, p["cost_basis"], p["trade_id"] + " 剩余成本")
            value = qty * p["mark_price"]
            equal(value, p["market_value"], p["trade_id"] + " 市值")
            equal(value - cost, p["unrealized_pnl"], p["trade_id"] + " 未实现损益")
            market_value += value
            unrealized += value - cost
            by_trade[p["trade_id"]] = value - cost
        equal(market_value, s["positions_market_value"], s["date"] + " 总市值")
        equal(unrealized, s["unrealized_pnl"], s["date"] + " 未实现总损益")
        return by_trade
    opening_unrealized = snapshot_check(snapshots[0])
    fully_exited = {tid for tid, trade in trade_map.items()
                    if trade["open_dt"].date() <= start and tid not in opening_unrealized}
    fill_days, event_days = defaultdict(list), defaultdict(list)
    orders = {}
    for f in fills:
        if f["trade_id"] not in trade_map:
            raise DataError("成交关联的交易不存在。")
        f["dt"] = timestamp(f["timestamp"]).astimezone(tz)
        day = f["dt"].date()
        if not start < day <= end or day not in days:
            raise DataError("成交必须晚于期初基准日期且当日有资产快照；不能重复录入基准已包含的成交。")
        for field in ("quantity", "price", "fees"):
            f[field] = number(f[field], field)
        if f["side"] not in {"BUY", "SELL"} or f["quantity"] <= 0 or f["price"] <= 0 or f["fees"] < 0:
            raise DataError("成交方向、数量、价格或费用无效。")
        if f["dt"] < trade_map[f["trade_id"]]["open_dt"]:
            raise DataError("成交时间不能早于交易开仓。")
        if f["broker_order_id"]:
            signature = (f["trade_id"], f["side"])
            if f["broker_order_id"] in orders and orders[f["broker_order_id"]] != signature:
                raise DataError("同一券商订单编号不能属于不同交易或方向。")
            orders[f["broker_order_id"]] = signature
        fill_days[day].append(f)
    for e in events:
        e["dt"] = timestamp(e["timestamp"]).astimezone(tz)
        day = e["dt"].date()
        e["amount"] = number(e["amount"], "amount")
        allowed = {"DEPOSIT", "WITHDRAWAL", "DIVIDEND", "INTEREST", "ACCOUNT_FEE"}
        positive = e["event_type"] in {"DEPOSIT", "DIVIDEND", "INTEREST"}
        if e["account_id"] != account or e["event_type"] not in allowed or (positive and e["amount"] < 0) or (not positive and e["amount"] > 0):
            raise DataError("资金事件的账户、类型或金额符号无效。")
        if not start < day <= end or day not in days:
            raise DataError("资金事件必须晚于期初基准日期且当日有资产快照。")
        if e["trade_id"] and e["trade_id"] not in trade_map:
            raise DataError("资金事件关联的交易不存在。")
        event_days[day].append(e)
    for b in behaviors:
        if b["trade_id"] not in trade_map or b["is_deviation"] not in {"true", "false", "unknown"}:
            raise DataError("行为记录的交易或偏差标签无效。")
        b["event_dt"] = timestamp(b["event_at"]).astimezone(tz)
        if timestamp(b["recorded_at"]) < timestamp(b["event_at"]):
            raise DataError("行为录入时间不能早于发生时间。")
    cash, realized_ytd, fees_ytd = (snapshots[0][key] for key in ("cash", "realized_pnl_ytd", "fees_ytd"))
    cumulative_flow, period_fees, other_income = ZERO, ZERO, ZERO
    realized_by_trade, assigned_income = defaultdict(lambda: ZERO), defaultdict(lambda: ZERO)
    output_assets = [{"date": snapshots[0]["date"], "cash": float(cash), "holdings": float(snapshots[0]["positions_market_value"]), "nav": float(snapshots[0]["nav"]), "net_capital": float(snapshots[0]["nav"])}]
    year = start.year
    closing_unrealized = opening_unrealized
    for s in snapshots[1:]:
        if s["day"].year != year:
            year, realized_ytd, fees_ytd = s["day"].year, ZERO, ZERO
        for f in sorted(fill_days[s["day"]], key=lambda f: f["dt"]):
            tid, qty, price, fee = f["trade_id"], f["quantity"], f["price"], f["fees"]
            period_fees += fee
            fees_ytd += fee
            if f["side"] == "BUY":
                if tid in fully_exited:
                    raise DataError(f"交易 {tid} 已完全退出；再次买入必须使用新的 trade_id。")
                cash -= qty * price + fee
                lots[tid].append([qty, (qty * price + fee) / qty])
            else:
                cash += qty * price - fee
                remaining, sold_cost = qty, ZERO
                while remaining:
                    if not lots[tid]:
                        raise DataError(f"{tid} 卖出超过现有持仓数量。")
                    available, unit_cost = lots[tid][0]
                    take = min(available, remaining)
                    sold_cost += take * unit_cost
                    remaining -= take
                    lots[tid][0][0] -= take
                    if lots[tid][0][0] == 0:
                        lots[tid].popleft()
                if not lots[tid]:
                    fully_exited.add(tid)
                pnl = qty * price - fee - sold_cost
                realized_ytd += pnl
                realized_by_trade[tid] += pnl
        day_flow = ZERO
        for e in event_days[s["day"]]:
            cash += e["amount"]
            if e["event_type"] in {"DEPOSIT", "WITHDRAWAL"}:
                day_flow += e["amount"]
            else:
                if e["event_type"] == "ACCOUNT_FEE":
                    period_fees -= e["amount"]
                    fees_ytd -= e["amount"]
                if e["trade_id"] and e["event_type"] in {"DIVIDEND", "ACCOUNT_FEE"}:
                    assigned_income[e["trade_id"]] += e["amount"]
                else:
                    other_income += e["amount"]
        if cash < -TOL:
            raise DataError("期末经济现金为负，超出现金账户范围。")
        cumulative_flow += day_flow
        equal(cash, s["cash"], s["date"] + " 现金")
        equal(day_flow, s["external_flow"], s["date"] + " 外部资金流")
        equal(realized_ytd, s["realized_pnl_ytd"], s["date"] + " 年内已实现损益")
        equal(fees_ytd, s["fees_ytd"], s["date"] + " 年内费用")
        closing_unrealized = snapshot_check(s)
        output_assets.append({"date": s["date"], "cash": float(cash), "holdings": float(s["positions_market_value"]), "nav": float(s["nav"]), "net_capital": float(snapshots[0]["nav"] + cumulative_flow)})
    for t in trades:
        tf = sorted((f for f in fills if f["trade_id"] == t["trade_id"]), key=lambda f: f["dt"])
        if not tf and t["trade_id"] not in opening_unrealized:
            if start < t["open_dt"].date() <= end or (t["close_dt"] and start < t["close_dt"].date() <= end):
                raise DataError("期间交易缺少相应成交或期初批次。")
            continue
        if t["open_dt"].date() > start and (not tf or tf[0]["side"] != "BUY" or t["open_dt"] != tf[0]["dt"]):
            raise DataError("新交易 opened_at 必须等于首次买入时间。")
        if lots[t["trade_id"]]:
            if t["status"] != "OPEN":
                raise DataError("仍有持仓的交易必须为 OPEN。")
        elif t["status"] != "CLOSED" or not tf or t["close_dt"] != tf[-1]["dt"]:
            raise DataError("已完全退出的交易必须 CLOSED，关闭时间等于最后成交。")
    contribution_values = defaultdict(lambda: ZERO)
    for tid in trade_map:
        t = trade_map[tid]
        label = t["strategy_id"] + "/" + t["strategy_version"]
        contribution_values[label] += realized_by_trade[tid] + closing_unrealized.get(tid, ZERO) - opening_unrealized.get(tid, ZERO) + assigned_income[tid]
    pnl = snapshots[-1]["nav"] - snapshots[0]["nav"] - cumulative_flow
    equal(sum(contribution_values.values(), ZERO) + other_income, pnl, "期间损益归因")
    contributions = [{"label": label, "value": float(value)} for label, value in sorted(contribution_values.items())]
    contributions.append({"label": "ACCOUNT_OTHER / 账户其他", "value": float(other_income)})
    monthly = {}
    for s in snapshots[1:]:
        month = s["date"][:7]
        monthly.setdefault(month, {"month": month, "fills": 0, "orders": set(), "opened": 0, "closed": 0})
    for f in fills:
        m = monthly[f["dt"].strftime("%Y-%m")]
        m["fills"] += 1
        if f["broker_order_id"]:
            m["orders"].add(f["broker_order_id"])
    new_trades, closed_count, closed = 0, 0, []
    for t in trades:
        if start < t["open_dt"].date() <= end:
            new_trades += 1
            monthly.setdefault(t["open_dt"].strftime("%Y-%m"), {"month": t["open_dt"].strftime("%Y-%m"), "fills": 0, "orders": set(), "opened": 0, "closed": 0})["opened"] += 1
        if t["close_dt"] and start < t["close_dt"].date() <= end:
            closed_count += 1
            monthly[t["close_dt"].strftime("%Y-%m")]["closed"] += 1
            if t["open_dt"].date() <= start:
                warnings.append(f"跨期交易 {t['trade_id']} 完全平仓，但本次输入缺少期初之前已实现记录；不纳入完整交易 R 分布。")
                continue
            trade_pnl = realized_by_trade[t["trade_id"]] + assigned_income[t["trade_id"]]
            closed.append({"trade_id": t["trade_id"], "strategy": t["strategy_id"] + "/" + t["strategy_version"], "net_pnl": float(trade_pnl), "r": float(trade_pnl / t["risk"]) if t["risk"] > 0 else None, "hold_days": (t["close_dt"] - t["open_dt"]).total_seconds() / 86400})
    missing_orders = sum(not f["broker_order_id"] for f in fills)
    if missing_orders:
        warnings.append(f"{missing_orders} 次成交缺少订单编号；订单次数只包含已知编号，不代表全部委托。")
    behavior_counts = defaultdict(lambda: {"events": 0, "trades": set()})
    for b in behaviors:
        if start < b["event_dt"].date() <= end:
            key = b["behavior_type"] + " / " + b["is_deviation"]
            behavior_counts[key]["events"] += 1
            behavior_counts[key]["trades"].add(b["trade_id"])
    warnings.append("行为图展示记录次数，不将无记录视为合规，也不把涉及损益解释为偏差造成的损失。")
    return {
        "title": "个人交易与资产报告", "currency": metadata["currency"], "account_id": account,
        "fictional": metadata["fictional"], "period_start": start.isoformat(), "period_end": end.isoformat(), "warnings": warnings,
        "summary": {"opening_nav": float(snapshots[0]["nav"]), "closing_nav": float(snapshots[-1]["nav"]), "net_flow": float(cumulative_flow), "net_pnl": float(pnl), "fees": float(period_fees), "total_fills": len(fills), "total_orders": len(orders), "new_trades": new_trades, "closed_trades": closed_count},
        "assets": output_assets,
        "waterfall": [{"label": "期初资产", "value": float(snapshots[0]["nav"]), "kind": "total"}, {"label": "净外部资金流", "value": float(cumulative_flow), "kind": "delta"}] + [{**c, "kind": "delta"} for c in contributions] + [{"label": "期末资产", "value": float(snapshots[-1]["nav"]), "kind": "total"}],
        "contributions": contributions,
        "monthly_counts": [{**m, "orders": len(m["orders"])} for _, m in sorted(monthly.items())],
        "closed_trades": closed,
        "behaviors": [{"label": k, "events": v["events"], "affected_trades": len(v["trades"])} for k, v in sorted(behavior_counts.items())],
        "returns": load_performance(folder, metadata, start, end, warnings, snapshot_dates=days),
        "backtest": load_backtest(Path(backtest_dir) if backtest_dir is not None else None, metadata["currency"]),
    }
