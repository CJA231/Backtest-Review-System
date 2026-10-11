"""Offline trading-journal charts. Python standard library; no network calls.

Accounting values are supplied by the report builder. This module renders
those values and never infers an account return from NAV and external flows.
"""

from __future__ import annotations

import html
import math
from datetime import date
from typing import Iterable


PALETTE = ("#087f8c", "#4169b1", "#b46a1f", "#8055a3", "#517736", "#96605b")
POSITIVE = "#087f8c"
NEGATIVE = "#bc3c47"
MUTED = "#738293"
WIDTH, HEIGHT = 800, 360
LEFT, RIGHT, TOP, BOTTOM = 92, 30, 36, 66


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def _num(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def _fmt(value: object, digits: int = 2) -> str:
    number = _num(value)
    return "—" if number is None else f"{number:,.{digits}f}"


def _day(value: object) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _short(value: object, limit: int = 22) -> str:
    result = str(value)
    return result if len(result) <= limit else result[: limit - 1] + "…"


def _text(x: float, y: float, value: object, *, anchor: str = "start", css: str = "", color: str | None = None) -> str:
    fill = f' fill="{color}"' if color else ""
    return f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" class="{css}"{fill}>{_esc(value)}</text>'


def _line(x1: float, y1: float, x2: float, y2: float, *, color: str = "#dbe2e9", width: float = 1, dashed: bool = False) -> str:
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    return f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{color}" stroke-width="{width}"{dash}/>'


def _rect(x: float, y: float, width: float, height: float, color: str, tooltip: object = "", opacity: float = 1) -> str:
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(0, width):.2f}" height="{max(0, height):.2f}" '
            f'fill="{color}" opacity="{opacity}" rx="2"><title>{_esc(tooltip)}</title></rect>')


def _circle(x: float, y: float, radius: float, color: str, tooltip: object = "") -> str:
    return f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius}" fill="{color}" stroke="white" stroke-width="1.3"><title>{_esc(tooltip)}</title></circle>'


def _path(points: Iterable[tuple[float, float]], *, color: str, fill: str = "none", opacity: float = 1, close: bool = False, dashed: bool = False, width: float = 2.6) -> str:
    coords = list(points)
    if not coords:
        return ""
    command = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in coords) + (" Z" if close else "")
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    return f'<path d="{command}" fill="{fill}" stroke="{color}" stroke-width="{width}" opacity="{opacity}" stroke-linejoin="round"{dash}/>'


def _bounds(values: Iterable[float], *, zero: bool = False) -> tuple[float, float]:
    vals = [float(v) for v in values if math.isfinite(float(v))]
    if not vals:
        return 0.0, 1.0
    low, high = min(vals), max(vals)
    if zero:
        low, high = min(low, 0), max(high, 0)
    if low == high:
        pad = max(abs(low) * 0.05, 1.0)
        return low - pad, high + pad
    pad = (high - low) * 0.10
    return (low - pad if low != 0 else 0), high + pad


def _axis_value(value: float, percent: bool = False) -> str:
    if percent:
        return f"{value * 100:.1f}%"
    abs_value = abs(value)
    if abs_value >= 1_000_000:
        return f"{value / 1_000_000:.1f}m"
    if abs_value >= 10_000:
        return f"{value / 1_000:.1f}k"
    if abs_value >= 10:
        return f"{value:,.0f}"
    return f"{value:.1f}"


def _axes(low: float, high: float, *, unit: str, percent: bool = False, height: int = HEIGHT) -> tuple[str, object]:
    bottom = height - BOTTOM
    def y(value: float) -> float:
        return bottom - (value - low) / (high - low) * (bottom - TOP)
    parts = [_text(LEFT, 21, unit, css="axis-unit")]
    if unit in ("次数", "交易笔数") and low == 0:
        step_size = max(1, math.ceil(high / 5))
        tick_values = list(range(0, math.floor(high) + 1, step_size))
    else:
        tick_values = [low + (high - low) * step / 4 for step in range(5)]
    for value in tick_values:
        position = y(value)
        parts.append(_line(LEFT, position, WIDTH - RIGHT, position))
        label = str(value) if unit in ("次数", "交易笔数") else _axis_value(value, percent)
        parts.append(_text(LEFT - 12, position + 5, label, anchor="end", css="axis"))
    if low <= 0 <= high:
        parts.append(_line(LEFT, y(0), WIDTH - RIGHT, y(0), color="#627284", width=1.5))
    return "".join(parts), y


def _date_positions(rows: list[dict], *, key: str = "date") -> tuple[object, list[tuple[float, str]]]:
    dates = [_day(row.get(key)) for row in rows]
    if any(item is None for item in dates):
        def x(index: int) -> float:
            return LEFT + index * (WIDTH - LEFT - RIGHT) / max(1, len(rows) - 1)
    else:
        first = min(dates)
        span = max(1, (max(dates) - first).days)
        def x(index: int) -> float:
            return LEFT + (dates[index] - first).days / span * (WIDTH - LEFT - RIGHT)
    indexes = sorted({round(i * (len(rows) - 1) / min(5, len(rows) - 1)) for i in range(min(5, len(rows) - 1) + 1)}) if len(rows) > 1 else [0]
    labels = [(x(i), str(rows[i].get(key, ""))[:10]) for i in indexes]
    return x, labels


def _x_dates(labels: list[tuple[float, str]], *, height: int = HEIGHT) -> str:
    return "".join(_text(x, height - 29, label, anchor="start" if i == 0 else "end" if i == len(labels) - 1 else "middle", css="axis") for i, (x, label) in enumerate(labels))


def _svg(body: str, title: str, description: str, *, height: int = HEIGHT) -> str:
    return (f'<div class="svg-wrap"><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" '
            f'role="img" aria-label="{_esc(title + "。" + description)}">'
            f'<title>{_esc(title)}</title><desc>{_esc(description)}</desc>{body}</svg></div>')


def _legend(items: Iterable[tuple[str, str]]) -> str:
    return '<div class="legend">' + "".join(f'<span><i style="background:{color}"></i>{_esc(label)}</span>' for label, color in items) + "</div>"


def _card(title: str, visual: str, caption: str, *, legend: str = "", wide: bool = False) -> str:
    return f'<section class="card{" wide" if wide else ""}"><h3>{_esc(title)}</h3>{legend}{visual}<p class="caption">{_esc(caption)}</p></section>'


def _empty(title: str, reason: str) -> str:
    return f'<section class="card empty"><h3>{_esc(title)}</h3><p>{_esc(reason)}</p></section>'


def _line_chart(rows: list[dict], series: list[tuple[str, str, str]], *, title: str, unit: str, caption: str, percent: bool = False, zero: bool = False, dashed_keys: tuple[str, ...] = (), wide: bool = False, markers: bool = False, phases: bool = False) -> str:
    usable = [row for row in rows if any(_num(row.get(key)) is not None for key, _, _ in series)]
    if len(usable) < 2:
        return _empty(title, "至少需要两个有效估值时点；缺失数据不补零。")
    values = [_num(row.get(key)) for row in usable for key, _, _ in series]
    low, high = _bounds([v for v in values if v is not None], zero=zero)
    axes, y = _axes(low, high, unit=unit, percent=percent)
    x, labels = _date_positions(usable)
    body = _phase_backgrounds(usable, x) if phases else ""
    body += axes
    for key, label, color in series:
        segment = []
        for i, row in enumerate(usable):
            value = _num(row.get(key))
            if value is None:
                body += _path(segment, color=color, dashed=key in dashed_keys)
                segment = []
                continue
            segment.append((x(i), y(value)))
            display = f"{value * 100:.2f}%" if percent else _fmt(value)
            if len(usable) <= 80:
                body += _circle(x(i), y(value), 3.5, color, f'{row.get("date", "")} · {label}: {display}')
        body += _path(segment, color=color, dashed=key in dashed_keys)
    if markers:
        for i, row in enumerate(usable):
            flow = _num(row.get("external_flow"))
            if flow:
                body += _line(x(i), TOP, x(i), HEIGHT - BOTTOM, color="#b46a1f", dashed=True)
                body += _circle(x(i), TOP + 5, 5, "#b46a1f", f'{row.get("date", "")} · 当日净外部资金流: {_fmt(flow)} {unit}')
    body += _x_dates(labels)
    return _card(title, _svg(body, title, caption), caption, legend=_legend((label, color) for _, label, color in series), wide=wide)


def _phase_backgrounds(rows: list[dict], x: object) -> str:
    """Shade explicitly supplied chronological IS/OOS phases."""
    parts = []
    start = 0
    for end in range(1, len(rows) + 1):
        if end < len(rows) and rows[end].get("phase") == rows[start].get("phase"):
            continue
        phase = str(rows[start].get("phase", ""))
        if phase in ("IS", "OOS"):
            left = LEFT if start == 0 else (x(start - 1) + x(start)) / 2
            right = WIDTH - RIGHT if end == len(rows) else (x(end - 1) + x(end)) / 2
            color = "#ede9e2" if phase == "IS" else "#e1f1ee"
            parts.append(_rect(left, TOP, right - left, HEIGHT - TOP - BOTTOM, color, f'{phase}: {rows[start].get("date")} 至 {rows[end - 1].get("date")}'))
            if right - left >= 95:
                parts.append(_text((left + right) / 2, TOP + 19, "样本内 IS" if phase == "IS" else "样本外 OOS", anchor="middle", css="phase"))
        start = end
    return "".join(parts)


def _composition(rows: list[dict], currency: str) -> str:
    title = "资产构成：现金与持仓市值"
    valid = [row for row in rows if _num(row.get("cash")) is not None and _num(row.get("holdings")) is not None]
    if len(valid) < 2:
        return _empty(title, "至少需要两个完整的现金与持仓估值时点。")
    if any(float(row["cash"]) < 0 or float(row["holdings"]) < 0 for row in valid):
        return _empty(title, "本版堆叠面积图适用于现金与持仓市值均非负的账户。负值保留在账户数据中，不强行堆叠。")
    high = max(float(row["cash"]) + float(row["holdings"]) for row in valid)
    high = max(high * 1.08, 1)
    axes, y = _axes(0, high, unit=currency)
    x, labels = _date_positions(valid)
    cash = [(x(i), y(float(row["cash"]))) for i, row in enumerate(valid)]
    total = [(x(i), y(float(row["cash"]) + float(row["holdings"]))) for i, row in enumerate(valid)]
    body = _path([(x(0), y(0))] + cash + [(x(len(valid) - 1), y(0))], color=PALETTE[1], fill=PALETTE[1], opacity=0.30, close=True, width=1)
    body += _path(total + list(reversed(cash)), color=PALETTE[0], fill=PALETTE[0], opacity=0.47, close=True, width=1)
    body += axes + _path(total, color=PALETTE[0])
    for i, row in enumerate(valid):
        body += _circle(x(i), total[i][1], 3, PALETTE[0], f'{row.get("date")} · 现金 {_fmt(row["cash"])} / 持仓 {_fmt(row["holdings"])} {currency}')
    body += _x_dates(labels)
    caption = "以金额堆叠，现金＋持仓市值构成净资产。面积变化可能包含入出金，不代表投资收益率。"
    return _card(title, _svg(body, title, caption), caption, legend=_legend((("现金", PALETTE[1]), ("持仓市值", PALETTE[0]))))


def _waterfall(rows: list[dict], currency: str) -> str:
    title = "资产变化对账瀑布图"
    valid = [row for row in rows if _num(row.get("value")) is not None]
    if len(valid) < 2:
        return _empty(title, "需要期初、期末资产及期间变化项目。")
    values, bars = [0.0], []
    running = 0.0
    for row in valid:
        value = float(row["value"])
        if row.get("kind") == "total":
            start, end = 0.0, value
            running = value
        else:
            start, end = running, running + value
            running = end
        bars.append((row, start, end))
        values.extend((start, end))
    low, high = _bounds(values, zero=True)
    body, y = _axes(low, high, unit=currency)
    step = (WIDTH - LEFT - RIGHT) / len(bars)
    width = min(68, step * 0.65)
    for i, (row, start, end) in enumerate(bars):
        center = LEFT + step * (i + 0.5)
        color = PALETTE[1] if row.get("kind") == "total" else POSITIVE if end >= start else NEGATIVE
        label = str(row.get("label", ""))
        body += _rect(center - width / 2, min(y(start), y(end)), width, max(2, abs(y(end) - y(start))), color, f'{label}: {_fmt(row["value"])} {currency}')
        if i + 1 < len(bars):
            body += _line(center + width / 2, y(end), center + step - width / 2, y(end), color=MUTED, dashed=True)
        body += _text(center, min(y(start), y(end)) - 9, _fmt(row["value"], 0), anchor="middle", css="value")
        body += _text(center, HEIGHT - 43, _short(label, 9), anchor="middle", css="axis")
    caption = "期初净资产＋净外部资金流＋策略损益＋账户其他损益＝期末净资产。图中金额由账本模块提供。"
    return _card(title, _svg(body, title, caption), caption, legend=_legend((("资产总额", PALETTE[1]), ("正向变化", POSITIVE), ("负向变化", NEGATIVE))), wide=len(bars) > 7)


def _horizontal_bars(rows: list[dict], *, title: str, unit: str, caption: str, fields: list[tuple[str, str, str]], signed: bool = False) -> str:
    valid = [row for row in rows if any(_num(row.get(field)) is not None for field, _, _ in fields)]
    if not valid:
        return _empty(title, "没有可展示的记录。")
    # Extend vertically for long lists instead of silently dropping categories.
    height = max(270, 78 + len(valid) * (48 if len(fields) == 1 else 72))
    left, right = 215, WIDTH - 38
    values = [_num(row.get(field)) for row in valid for field, _, _ in fields]
    finite = [v for v in values if v is not None]
    low = min([0] + finite)
    high = max([0] + finite)
    if high == low:
        high = low + 1
    span = high - low
    low = low - span * 0.1 if low < 0 else low
    high = high + span * 0.15
    def x(value: float) -> float:
        return left + (value - low) / (high - low) * (right - left)
    body = _text(left, 23, unit, css="axis-unit")
    for j in range(5):
        value = low + (high - low) * j / 4
        body += _line(x(value), 35, x(value), height - 44)
        body += _text(x(value), height - 17, _axis_value(value), anchor="middle", css="axis")
    body += _line(x(0), 35, x(0), height - 44, color="#627284", width=1.5)
    group_height = (height - 78) / len(valid)
    for i, row in enumerate(valid):
        center_y = 35 + group_height * (i + 0.5)
        label = str(row.get("label", ""))
        body += _text(left - 12, center_y + 5, _short(label, 12), anchor="end", css="category")
        for j, (field, field_label, color) in enumerate(fields):
            value = _num(row.get(field))
            if value is None:
                continue
            bar_y = center_y - len(fields) * 11 + j * 22
            used_color = (POSITIVE if value >= 0 else NEGATIVE) if signed else color
            body += _rect(min(x(0), x(value)), bar_y, max(1, abs(x(value) - x(0))), 17, used_color, f'{label} · {field_label}: {_fmt(value, 2 if signed else 0)} {unit}')
            anchor = "start" if value >= 0 else "end"
            value_label = _axis_value(value) if abs(value) >= 10_000 else _fmt(value, 2 if signed else 0)
            body += _text(x(value) + (6 if value >= 0 else -6), bar_y + 14, value_label, anchor=anchor, css="value")
    return _card(title, _svg(body, title, caption, height=height), caption, legend=_legend((label, color) for _, label, color in fields) if len(fields) > 1 else "")


def _counts(rows: list[dict]) -> str:
    title = "月度交易频次：四种口径分别统计"
    valid = [row for row in rows if all(_num(row.get(key)) is not None for key in ("fills", "orders", "opened", "closed"))]
    if not valid:
        return _empty(title, "没有月度成交或交易统计。")
    fields = (("fills", "成交数", PALETTE[0]), ("orders", "已成交订单数", PALETTE[1]), ("opened", "新建交易数", PALETTE[2]), ("closed", "完全平仓交易数", PALETTE[3]))
    maximum = max(float(row[key]) for row in valid for key, _, _ in fields)
    body, y = _axes(0, max(1, maximum * 1.18), unit="次数")
    step = (WIDTH - LEFT - RIGHT) / len(valid)
    bar_width = min(28, step * 0.17)
    for i, row in enumerate(valid):
        center = LEFT + step * (i + 0.5)
        for j, (key, label, color) in enumerate(fields):
            value = float(row[key])
            left = center + (j - 2) * bar_width
            body += _rect(left, y(value), bar_width - 2, max(0, y(0) - y(value)), color, f'{row.get("month")} · {label}: {_fmt(value, 0)}')
            if len(valid) <= 6:
                body += _text(left + (bar_width - 2) / 2, y(value) - 8, _fmt(value, 0), anchor="middle", css="value")
        if len(valid) <= 12 or i % max(1, len(valid) // 12) == 0:
            body += _text(center, HEIGHT - 32, row.get("month", ""), anchor="middle", css="axis")
    caption = "成交、订单和完整交易不是同一单位，使用分组柱形而非相加堆叠。订单按每月去重，跨月订单不应机械累计为全年订单数。"
    return _card(title, _svg(body, title, caption), caption, legend=_legend((label, color) for _, label, color in fields), wide=len(valid) > 6)


def _r_histogram(rows: list[dict]) -> str:
    title = "完全平仓交易：净 R 分布"
    values = [float(row["r"]) for row in rows if _num(row.get("r")) is not None]
    missing = len(rows) - len(values)
    if len(values) < 2:
        return _empty(title, f"需要至少两笔风险预算已知的完全平仓交易。当前有效 {len(values)} 笔，风险预算缺失 {missing} 笔。")
    low, high = min(values), max(values)
    if low == high:
        low, high = low - 0.5, high + 0.5
    bins = min(12, max(3, math.ceil(math.sqrt(len(values)))))
    step = (high - low) / bins
    counts = [0] * bins
    for value in values:
        counts[min(bins - 1, max(0, int((value - low) / step)))] += 1
    body, y = _axes(0, max(1, max(counts) * 1.25), unit="交易笔数")
    width = (WIDTH - LEFT - RIGHT) / bins
    for i, count in enumerate(counts):
        a, b = low + i * step, low + (i + 1) * step
        color = NEGATIVE if b <= 0 else POSITIVE if a >= 0 else PALETTE[1]
        left = LEFT + i * width
        body += _rect(left + 2, y(count), width - 4, y(0) - y(count), color, f'[{a:.2f}, {b:.2f}{"]" if i == bins - 1 else ")"} R：{count} 笔')
        body += _text(left + width / 2, y(count) - 8, count, anchor="middle", css="value")
        body += _text(left + width / 2, HEIGHT - 33, f"{a:.1f}–{b:.1f}", anchor="middle", css="axis")
    if low <= 0 <= high:
        zero_x = LEFT + (0 - low) / (high - low) * (WIDTH - LEFT - RIGHT)
        body += _line(zero_x, TOP, zero_x, HEIGHT - BOTTOM, color=MUTED, dashed=True)
    body += _text(WIDTH - RIGHT, HEIGHT - 11, "净损益 / 固定初始风险（R）", anchor="end", css="axis-unit")
    caption = f"有效样本 {len(values)} 笔；风险预算缺失 {missing} 笔已排除。只纳入完全平仓交易，净损益已计费用。少量样本仅用于描述。"
    return _card(title, _svg(body, title, caption), caption)


def _r_scatter(rows: list[dict]) -> str:
    title = "持有时间与净 R"
    valid = [row for row in rows if _num(row.get("r")) is not None and _num(row.get("hold_days")) is not None]
    if len(valid) < 2:
        return _empty(title, "至少需要两笔同时具备持有时间与风险预算的完全平仓交易。")
    low, high = _bounds([float(row["r"]) for row in valid], zero=True)
    body, y = _axes(low, high, unit="净 R")
    xmax = max(1, max(float(row["hold_days"]) for row in valid) * 1.1)
    def x(value: float) -> float:
        return LEFT + value / xmax * (WIDTH - LEFT - RIGHT)
    for j in range(5):
        value = xmax * j / 4
        body += _text(x(value), HEIGHT - 30, _fmt(value, 1), anchor="middle", css="axis")
    strategies = list(dict.fromkeys(str(row.get("strategy", "未归属")) for row in valid))
    colors = {label: PALETTE[i % len(PALETTE)] for i, label in enumerate(strategies)}
    for row in valid:
        strategy = str(row.get("strategy", "未归属"))
        tooltip = f'{row.get("trade_id")} · {strategy} · 持有 {_fmt(row["hold_days"], 2)} 天 · {_fmt(row["r"], 2)} R'
        body += _circle(x(float(row["hold_days"])), y(float(row["r"])), 6, colors[strategy], tooltip)
    body += _text(WIDTH - RIGHT, HEIGHT - 9, "持有时间（天）", anchor="end", css="axis-unit")
    caption = f"有效样本 {len(valid)} 笔；只展示完全平仓且初始风险已知的交易。散点关系用于观察，不说明持有时间造成收益变化。"
    return _card(title, _svg(body, title, caption), caption, legend=_legend(colors.items()))


def _drawdown(rows: list[dict], *, title: str, caption: str, phases: bool = False) -> str:
    valid = [row for row in rows if _num(row.get("drawdown_pct")) is not None]
    if len(valid) < 2:
        return _empty(title, "至少需要两个已记录指数观察点对应的有效回撤值；缺失日期不补零。")
    # Percentage-point to fraction conversion only; no drawdown is calculated.
    values = [float(row["drawdown_pct"]) / 100 for row in valid]
    low = min(0, min(values))
    high = max(0, max(values))
    if low == high:
        low = -0.01
    else:
        low -= (high - low) * 0.08
    axes, y = _axes(low, high, unit="回撤（%）", percent=True)
    x, labels = _date_positions(valid)
    body = _phase_backgrounds(valid, x) if phases else ""
    body += _path([(x(0), y(0))] + [(x(i), y(v)) for i, v in enumerate(values)] + [(x(len(valid) - 1), y(0))], color=NEGATIVE, fill=NEGATIVE, opacity=0.17, close=True, width=1)
    body += axes
    body += _path([(x(i), y(v)) for i, v in enumerate(values)], color=NEGATIVE)
    for i, row in enumerate(valid):
        if len(valid) <= 80:
            body += _circle(x(i), y(values[i]), 3, NEGATIVE, f'{row.get("date")} · 回撤 {float(row["drawdown_pct"]):.2f}%')
    body += _x_dates(labels)
    return _card(title, _svg(body, title, caption), caption)


def _monthly_returns(rows: list[dict]) -> str:
    title = "月度收益率（标明实际覆盖区间）"
    valid = [row for row in rows if _num(row.get("return_pct")) is not None]
    if not valid:
        return _empty(title, "没有已验证的月度收益数据。")
    values = [float(row["return_pct"]) / 100 for row in valid]
    low, high = _bounds(values, zero=True)
    body, y = _axes(low, high, unit="TWR 收益率（%）", percent=True)
    step = (WIDTH - LEFT - RIGHT) / len(valid)
    width = min(62, step * 0.62)
    for i, (row, value) in enumerate(zip(valid, values)):
        center = LEFT + step * (i + 0.5)
        label = row.get("label", row.get("month", ""))
        tooltip = f'{label}: {float(row["return_pct"]):.2f}% · {row.get("start_date", "")} 至 {row.get("end_date", "")}'
        color = POSITIVE if value >= 0 else NEGATIVE
        body += _rect(center - width / 2, min(y(0), y(value)), width, abs(y(value) - y(0)), color, tooltip)
        if len(valid) <= 12:
            label_y = y(value) - 9 if value >= 0 else y(value) + 21
            body += _text(center, label_y, f'{float(row["return_pct"]):.2f}%', anchor="middle", css="value")
        if len(valid) <= 12 or i % max(1, len(valid) // 12) == 0:
            body += _text(center, HEIGHT - 31, row.get("month", ""), anchor="middle", css="axis")
    caption = "数值由绩效模块提供，不将每日百分比直接相加。不完整月份只代表覆盖区间；每月精确日期见下方表格。"
    return _card(title, _svg(body, title, caption), caption, wide=len(valid) > 6)


def _table(title: str, headers: list[str], rows: Iterable[Iterable[object]], *, note: str = "") -> str:
    cells = list(rows)
    if not cells:
        return ""
    head = "".join(f'<th scope="col">{_esc(item)}</th>' for item in headers)
    body = "".join("<tr>" + "".join(f"<td>{_esc(item)}</td>" for item in row) + "</tr>" for row in cells)
    return (f'<details class="data-table"><summary>{_esc(title)}（{len(cells)} 行）</summary>'
            f'<p class="caption">{_esc(note)}</p><div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div></details>')


CSS = """
:root{color-scheme:light;--ink:#192d40;--muted:#546779;--border:#dce5eb;--page:#f3f6f8;--positive:#087f8c;--negative:#bc3c47}
*{box-sizing:border-box}body{margin:0;background:var(--page);color:var(--ink);font-family:system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif;line-height:1.55}
main{max-width:1520px;margin:0 auto;padding:36px 28px 60px}h1{font-size:30px;line-height:1.3;margin:12px 0}h2{font-size:23px;margin:30px 0 15px}h3{font-size:18px;margin:0 0 14px;line-height:1.4}
.eyebrow{font-size:13px;color:var(--muted);letter-spacing:.04em}.meta{display:flex;flex-wrap:wrap;gap:9px 20px;color:var(--muted);font-size:14px}.badge{display:inline-block;border-radius:6px;padding:5px 10px;background:#e7eef4;font-size:13px;font-weight:650}.fictional{background:#fff0cd;color:#735109}
.lead,.scope{color:var(--muted);max-width:1120px}.scope{font-size:14px}.kpis{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin-top:24px}.kpi{background:white;border:1px solid var(--border);padding:18px;border-radius:12px}.kpi-label{font-size:13px;color:var(--muted)}.kpi-value{font-size:26px;font-weight:700;line-height:1.35;margin-top:4px}.kpi-note{font-size:12px;color:var(--muted);margin-top:5px}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}.card{background:white;border:1px solid var(--border);border-radius:12px;padding:21px;min-width:0}.wide{grid-column:1/-1}.empty p{color:var(--muted);font-size:14px;min-height:95px;margin:25px 0}.caption{font-size:13px;color:var(--muted);margin:12px 0 0}.legend{display:flex;flex-wrap:wrap;gap:8px 18px;margin-bottom:8px;font-size:13px;color:var(--muted)}.legend span{display:inline-flex;align-items:center;gap:7px}.legend i{width:11px;height:11px;border-radius:2px;display:inline-block}
.svg-wrap{width:100%;overflow-x:auto;overscroll-behavior-x:contain}svg{display:block;width:100%;min-width:610px;height:auto}svg text{fill:#43586a;font-size:15px;font-family:system-ui,-apple-system,"Microsoft YaHei",sans-serif}.axis-unit{font-size:14px}.value{font-size:14px;fill:#253f53}.category{font-size:16px}.phase{font-size:13px;fill:#5c696b}
.notice{margin:16px 0;padding:16px 18px;border:1px solid #ead7a7;border-radius:10px;background:#fff9ea;font-size:14px}.notice p{margin:4px 0}.notice ul{margin:8px 0;padding-left:23px}.details-meta{border-left:3px solid #087f8c;padding-left:15px;margin:12px 0 18px;color:var(--muted);font-size:14px}.details-meta p{margin:4px 0}
.data-table{margin-top:16px;background:white;border:1px solid var(--border);border-radius:10px;padding:13px 18px}.data-table summary{cursor:pointer;font-weight:600;font-size:14px}.table-wrap{overflow:auto;margin-top:12px}table{width:100%;border-collapse:collapse;font-size:13px;text-align:left}th,td{padding:10px 12px;border-bottom:1px solid #e6edf1;white-space:nowrap}th{background:#f4f7f9}footer{margin-top:32px;font-size:13px;color:var(--muted);border-top:1px solid var(--border);padding-top:18px}
@media(min-width:1280px){svg{min-width:0}}@media(max-width:900px){.grid{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}main{padding:24px 16px 40px}.wide{grid-column:auto}}@media(max-width:480px){h1{font-size:24px}.card{padding:16px}.kpi{padding:13px}.kpi-value{font-size:22px}}
@media print{body{background:white}main{padding:0;max-width:none}.grid{display:block}.card{break-inside:avoid;margin:12px 0}svg{min-width:0}.kpis{grid-template-columns:repeat(3,1fr)}.data-table{break-inside:avoid}.notice{break-inside:avoid}}
"""


def render_report(report: dict) -> str:
    """Return one standalone HTML document using precomputed report values.

    ``returns`` and ``backtest`` supply normalized indexes and drawdown values
    derived upstream from those recorded observations, in percentage points.
    Optional data is never substituted with account NAV.
    """
    title = str(report.get("title", "个人交易与资产报告"))
    currency = str(report.get("currency", "MYR"))
    summary = report.get("summary") or {}
    assets = report.get("assets") or []
    closed = report.get("closed_trades") or []
    period = f'{report.get("period_start", "—")} 至 {report.get("period_end", "—")}'
    fictional = bool(report.get("fictional"))
    badge = '<span class="badge fictional">虚构示例数据 · 非实际账户</span>' if fictional else '<span class="badge">账户记录报告</span>'
    parts = ['<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:; base-uri \'none\'; form-action \'none\'">',
             f'<title>{_esc(title)}</title><style>{CSS}</style></head><body><main>',
             '<header><div class="eyebrow">PERSONAL TRADING JOURNAL · 离线报告</div>',
             f'<h1>{_esc(title)}</h1>{badge}',
             f'<p class="meta"><span>账户：{_esc(report.get("account_id", "—"))}</span><span>区间：{_esc(period)}</span><span>记账币种：{_esc(currency)}</span></p>',
             '<p class="lead">从资产变化到交易频次，再到行为复盘。所有图表基于已提供记录；缺失的收益率与回测数据不作推断。</p>',
             '<p class="scope">当前核算范围：单币种、做多现金股票账户。图表展示已记录时点；不将缺失日期补成零，也不代表未记录期间。</p></header>']
    if fictional:
        parts.append('<div class="notice"><p>本报告仅演示记录与图表口径。示例覆盖有限交易日期，不代表全年表现或任何实际策略收益。</p></div>')
    warnings = report.get("warnings") or []
    if warnings:
        parts.append('<aside class="notice" aria-label="数据检查提示"><strong>数据检查提示</strong><ul>' + "".join(f'<li>{_esc(item)}</li>' for item in warnings) + '</ul></aside>')
    metrics = [("期末净资产", "closing_nav", currency, "现金＋持仓市值"),
               ("期间净投资损益", "net_pnl", currency, "扣除外部资金流影响的金额"),
               ("净外部资金流", "net_flow", currency, "入金减出金；不算投资收益"),
               ("成交次数", "total_fills", "次", "按成交编号统计"),
               ("已成交订单数", "total_orders", "个", "全区间订单编号去重"),
               ("完全平仓交易数", "closed_trades", "笔", "与成交次数分别统计")]
    parts.append('<div class="kpis">')
    for label, key, unit, note in metrics:
        value = _fmt(summary.get(key), 0 if unit in ("次", "个", "笔") else 2)
        parts.append(f'<div class="kpi"><div class="kpi-label">{_esc(label)}</div><div class="kpi-value">{value} <small>{_esc(unit)}</small></div><div class="kpi-note">{_esc(note)}</div></div>')
    parts.append('</div><h2>资产与金额贡献</h2><div class="grid">')
    parts.append(_line_chart(assets, [("nav", "账户净资产", PALETTE[0]), ("net_capital", "期初资产＋累计净外部资金流", PALETTE[1])], title="净资产与资金投入参考线", unit=currency,
                             caption="两条线的金额差反映累计净投资损益；参考线不是账户成本基础。净资产曲线受入出金影响，不能直接当作收益或投资回撤曲线。纵轴未必从零开始。", dashed_keys=("net_capital",), wide=True))
    parts.append(_composition(assets, currency))
    parts.append(_waterfall(report.get("waterfall") or [], currency))
    parts.append(_horizontal_bars(report.get("contributions") or [], title="各策略期间净损益贡献", unit=currency, caption="金额贡献包含期间已实现损益与未实现损益变化，及可归属股息与费用；账户其他项单列。共享资金下的金额贡献不等于策略收益率。", fields=[("value", "净损益贡献", POSITIVE)], signed=True))
    parts.append('</div>')
    parts.append(_table("资产快照明细", ["日期", f"现金 {currency}", f"持仓市值 {currency}", f"净资产 {currency}", f"资金投入参考线 {currency}"], ([row.get("date", ""), _fmt(row.get("cash")), _fmt(row.get("holdings")), _fmt(row.get("nav")), _fmt(row.get("net_capital"))] for row in assets), note="保留原记录日期，未插值生成额外资产快照。"))
    parts.append('<h2>收益率与风险</h2><div class="grid">')
    performance = report.get("returns")
    if performance:
        return_rows = performance.get("rows") or []
        series = [("index", "账户 TWR 净值", PALETTE[0])]
        if any(_num(row.get("benchmark_index")) is not None for row in return_rows):
            series.append(("benchmark_index", "基准净值", PALETTE[1]))
        parts.append(_line_chart(return_rows, series, title="排除外部资金流影响的收益净值", unit="归一化指数（起点＝100）", caption=f'来源：{performance.get("source", "未注明")}。区间 TWR：{_fmt(performance.get("total_return_pct"))}%。此图只展示已提供的 TWR_INDEX，不从资产快照推算。', wide=True))
        parts.append(_drawdown(return_rows, title="账户收益净值回撤", caption=f'按已记录的 TWR_INDEX 观察点计算。已记录指数点的最大回撤：{_fmt(performance.get("max_drawdown_pct"))}%。观察点之间遗漏的高点或低点可能使全期间回撤被低估；缺失日期不补零。'))
        parts.append(_monthly_returns(performance.get("monthly") or []))
    else:
        parts.append(_empty("收益净值、基准与回撤：尚未提供", "请提供券商或已核验来源的每日 TWR_INDEX。仅有每日资产与净入出金不足以保证精确 TWR；本报告不会以净资产代替收益净值。"))
        parts.append(_empty("月度收益率：尚未提供", "需要连续且口径一致的收益指数。利润金额、净资产增长率和 TWR 是不同指标。"))
    parts.append('</div>')
    if performance:
        parts.append(_table("月度收益实际覆盖范围", ["月份与覆盖说明", "起始日期", "结束日期", "收益率"], ([row.get("label", row.get("month", "")), row.get("start_date", ""), row.get("end_date", ""), f'{_fmt(row.get("return_pct"))}%'] for row in performance.get("monthly") or []), note="部分月份明确标注区间，不把部分月份结果称为整月收益。"))
    parts.append('<h2>交易频次与行为复盘</h2><div class="grid">')
    parts.append(_counts(report.get("monthly_counts") or []))
    parts.append(_r_histogram(closed))
    parts.append(_r_scatter(closed))
    parts.append(_horizontal_bars(report.get("behaviors") or [], title="行为偏差：事件数与涉及交易数", unit="次数 / 笔数", caption="一笔交易可以有多次偏差，同一交易也可能出现在多个类别。没有行为记录不等于遵守规则；这里不推断遵守率，也不将交易损失直接归因给偏差。", fields=[("events", "偏差事件数", PALETTE[2]), ("affected_trades", "涉及交易数", PALETTE[3])]))
    parts.append('</div>')
    parts.append(_table("完全平仓交易明细", ["交易编号", "策略与版本", f"净损益 {currency}", "净 R", "持有天数"], ([row.get("trade_id", ""), row.get("strategy", ""), _fmt(row.get("net_pnl")), _fmt(row.get("r")), _fmt(row.get("hold_days"))] for row in closed), note="未平仓交易不纳入该表；风险预算未知的交易保留金额损益，但 R 显示为缺失。"))
    parts.append('<h2>回测验证</h2>')
    backtest = report.get("backtest")
    if backtest:
        parts.append('<div class="details-meta">')
        for label, key in [("运行编号", "run_id"), ("名称", "label"), ("策略", "strategy"), ("来源", "source"), ("成本假设", "costs"), ("说明", "notes")]:
            parts.append(f'<p><strong>{label}：</strong>{_esc(backtest.get(key, "—"))}</p>')
        parts.append('</div><div class="grid">')
        back_rows = backtest.get("rows") or []
        back_series = [("index", "回测策略净值", PALETTE[0])]
        if any(_num(row.get("benchmark_index")) is not None for row in back_rows):
            back_series.append(("benchmark_index", "回测基准净值", PALETTE[1]))
        parts.append(_line_chart(back_rows, back_series, title="回测净值：样本内与样本外", unit="归一化指数（起点＝100）", caption=f'模拟结果，币种 {backtest.get("currency", currency)}；区间收益 {_fmt(backtest.get("total_return_pct"))}%。底色区分 IS 与 OOS；样本外表现仍需实盘验证。', phases=True))
        parts.append(_drawdown(back_rows, title="回测回撤", caption=f'按已记录的回测指数观察点计算。已记录指数点的最大回撤：{_fmt(backtest.get("max_drawdown_pct"))}%。观察点之间遗漏的高点或低点可能使全期间回撤被低估；缺失日期不补零。底色区分样本内 IS 与样本外 OOS。', phases=True))
        parts.append('</div>')
    else:
        parts.append('<div class="grid">' + _empty("回测净值与回撤：尚未提供", "交易日志不能自动变成策略回测。请另外提供带运行编号、策略版本、成本假设与 IS/OOS 标记的模拟结果；本报告只展示结果，不运行回测引擎。") + '</div>')
    parts.append(f'<footer>核算由交易账本模块完成；图表模块仅显示提供的数值。期间已记录费用 {_fmt(summary.get("fees"))} {_esc(currency)}，费用为信息字段，已扣费损益不再次扣除。报告完全离线，无外部字体、脚本、CDN 或 API。</footer></main></body></html>')
    return "".join(parts)
