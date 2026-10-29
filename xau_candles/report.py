"""Plain-text reading of a gold candle analysis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from xau_candles.classify import CANDLE_BIAS, CANDLE_MEANINGS
from xau_candles.models import (
    CandleRead,
    CandleType,
    Direction,
    MultiTimeframeAnalysis,
    Opportunity,
    PatternName,
    SetupStatus,
    TimeframeAnalysis,
    Trend,
)
from xau_candles.patterns import PATTERN_MEANINGS

try:
    from zoneinfo import ZoneInfo

    DHAKA = ZoneInfo("Asia/Dhaka")
except Exception:  # pragma: no cover - Windows embeds may lack the tz database
    DHAKA = timezone(timedelta(hours=6))


def format_time(moment: datetime) -> str:
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(DHAKA).strftime("%Y-%m-%d %H:%M") + " Asia/Dhaka"


def format_price(value: float | None) -> str:
    if value is None:
        return "-"
    if abs(value) >= 50:
        return f"{value:.2f}"
    return f"{value:.4f}"


def ascii_candle(read: CandleRead, width: int = 21) -> str:
    """Draw one candle with the low on the left and the high on the right."""

    span = read.high - read.low
    if span <= 0 or width < 3:
        return "◆"
    chars = ["│"] * width

    def place(price: float) -> int:
        raw = round((price - read.low) / span * (width - 1))
        return min(width - 1, max(0, raw))

    if read.direction is Direction.BULLISH:
        mark = "█"
    elif read.direction is Direction.BEARISH:
        mark = "░"
    else:
        mark = "◆"
    left, right = sorted((place(read.open), place(read.close)))
    for column in range(left, right + 1):
        chars[column] = mark
    return "".join(chars)


def _trend_label(trend: Trend) -> str:
    return {
        Trend.UP: "uptrend",
        Trend.DOWN: "downtrend",
        Trend.RANGE: "sideways",
        Trend.UNKNOWN: "not enough history",
    }[trend]


def _status_label(status: SetupStatus) -> str:
    return {
        SetupStatus.SIGNAL_CLOSED: "signal just closed",
        SetupStatus.STILL_VALID: "still valid",
        SetupStatus.ARMED: "armed, waiting for the break",
        SetupStatus.TRIGGERED: "break already traded",
        SetupStatus.WATCH: "watch only",
    }[status]


def render_opportunity(opportunity: Opportunity) -> list[str]:
    title = opportunity.pattern.value.replace("_", " ")
    if opportunity.status is SetupStatus.WATCH or opportunity.side is None:
        return [
            f"Watch: {title} ({opportunity.bias.value}, quality {opportunity.quality:.2f})",
            opportunity.rationale,
        ]
    grade = opportunity.grade.value if opportunity.grade else "-"
    lines = [
        f"{opportunity.side.value.upper()}  {title}  grade {grade}  {_status_label(opportunity.status)}",
        (
            f"Entry {format_price(opportunity.entry)}   "
            f"stop {format_price(opportunity.stop)}   "
            f"risk {format_price(opportunity.risk)}"
        ),
        (
            f"Target 1R {format_price(opportunity.target_1r)}   "
            f"target 2R {format_price(opportunity.target_2r)}   "
            f"stricter break {format_price(opportunity.break_level)}"
        ),
    ]
    if opportunity.also_matched:
        extras = ", ".join(name.value.replace("_", " ") for name in opportunity.also_matched)
        lines.append(f"Also on this signal: {extras}.")
    lines.append(opportunity.rationale)
    return lines


def render_timeframe(analysis: TimeframeAnalysis, *, last: int = 8) -> str:
    lines = [
        f"== {analysis.timeframe} ==",
        (
            f"Trend into the last candle: {_trend_label(analysis.trend)}. "
            f"Higher timeframe: {_trend_label(analysis.htf_bias)}."
        ),
    ]
    if not analysis.reads:
        lines.append("No candles to read.")
        return "\n".join(lines)

    window = analysis.reads[-last:]
    lines.append("")
    lines.append("Recent candles, low on the left and high on the right:")
    for read in window:
        lines.append(
            f"{format_time(read.time)}  {ascii_candle(read)}  "
            f"{read.candle_type.value:<22} color {read.direction.value:<8} bias {read.bias.value}"
        )
        if read.tags:
            lines.append(f"    tags: {', '.join(read.tags)}")
    last_read = analysis.reads[-1]
    lines.append("")
    lines.append(
        f"Last candle: {last_read.candle_type.value.replace('_', ' ')}. {last_read.meaning}"
    )

    closing = [pattern for pattern in analysis.patterns if pattern.end_index == last_read.index]
    if closing:
        lines.append("")
        lines.append("Groups that complete on the last candle:")
        for pattern in sorted(closing, key=lambda item: item.quality, reverse=True):
            lines.append(
                f"- {pattern.name.value.replace('_', ' ')} "
                f"({pattern.bias.value}, quality {pattern.quality:.2f}, {pattern.candles_involved} candles)"
            )

    lines.append("")
    board = analysis.board
    if board.conflict_note:
        lines.append(board.conflict_note)
    elif board.primary:
        lines.append("Trade opportunity:")
        lines.extend(render_opportunity(board.primary))
    else:
        lines.append("No trade is armed on this timeframe.")
        if board.watches:
            lines.append("")
            for watch in board.watches:
                lines.extend(render_opportunity(watch))
    return "\n".join(lines)


def render_confluence(analysis: MultiTimeframeAnalysis) -> str:
    swings = [
        f"{timeframe} {_trend_label(analysis.analyses[timeframe].trend)}"
        for timeframe in analysis.order
    ]
    sentences = [f"Swing read: {', '.join(swings)}."]
    setups: list[str] = []
    for timeframe in analysis.order:
        primary = analysis.analyses[timeframe].board.primary
        if primary is None or primary.side is None or primary.grade is None:
            continue
        setups.append(
            f"{timeframe} {primary.side.value} via {primary.pattern.value.replace('_', ' ')} "
            f"(grade {primary.grade.value})"
        )
    if setups:
        ordered = sorted(
            setups,
            key=lambda line: {"A": 0, "B": 1, "C": 2}[line.rsplit("grade ", 1)[-1][:1]],
        )
        sentences.append("Active opportunities: " + "; ".join(ordered) + ".")
    else:
        sentences.append("No timeframe has a trade plan inside the active window.")
    return " ".join(sentences)


def render_analysis(analysis: MultiTimeframeAnalysis, *, last: int = 8, generated_at: datetime | None = None) -> str:
    moment = generated_at or datetime.now(timezone.utc)
    header = [
        "XAUUSD candle section",
        f"Symbol {analysis.symbol}",
        f"Report time {format_time(moment)}",
    ]
    if analysis.source_note:
        header.append(analysis.source_note)
    header.append(
        "Color is the candle itself: close above open is bullish, close below open is bearish, "
        "and a flat close is neutral. Bias is what the type means. A gravestone doji can have a "
        "bullish color and still lean bearish, because the long upper wick was rejected."
    )
    header.append(
        "The swing trend is the 8 and 21 simple moving averages of closes before the candle. "
        "It lags a fresh turn. The candle group is what catches the turn."
    )
    header.append(render_confluence(analysis))
    sections = [render_timeframe(analysis.analyses[timeframe], last=last) for timeframe in analysis.order]
    footer = (
        "Educational read of candle structure. It is not an order to buy or sell. "
        "Gold gaps most often on the Sunday reopen; a stop beyond a wick can still be skipped."
    )
    return "\n\n".join(["\n".join(header), *sections, footer]) + "\n"


def render_glossary() -> str:
    lines = [
        "Candle types",
        "Color comes from the close versus the open. Bias is the reading of the type.",
        "",
    ]
    for candle_type in CandleType:
        lines.append(
            f"{candle_type.value:<22} bias {CANDLE_BIAS[candle_type].value:<12} {CANDLE_MEANINGS[candle_type]}"
        )
    lines.extend(["", "Groups", ""])
    for name in PatternName:
        lines.append(f"{name.value:<24} {PATTERN_MEANINGS[name]}")
    lines.extend(
        [
            "",
            "Grades: A agrees with the next higher timeframe, or the group is strong on its own. "
            "B is a valid setup that does not earn A. C fights the higher timeframe.",
            "A single rejection candle (hammer, star, doji) is a B setup unless a higher timeframe agrees.",
        ]
    )
    return "\n".join(lines) + "\n"


def analysis_to_dict(analysis: MultiTimeframeAnalysis, *, last: int = 8) -> dict:
    frames = []
    for timeframe in analysis.order:
        frame = analysis.analyses[timeframe]
        frames.append(
            {
                "timeframe": frame.timeframe,
                "trend": frame.trend.value,
                "htf_bias": frame.htf_bias.value,
                "last_candles": [
                    {
                        "time": format_time(read.time),
                        "open": read.open,
                        "high": read.high,
                        "low": read.low,
                        "close": read.close,
                        "direction": read.direction.value,
                        "bias": read.bias.value,
                        "type": read.candle_type.value,
                        "meaning": read.meaning,
                        "tags": list(read.tags),
                    }
                    for read in frame.reads[-last:]
                ],
                "opportunity": _opportunity_dict(frame.board.primary),
                "conflict": frame.board.conflict_note,
                "watches": [_opportunity_dict(watch) for watch in frame.board.watches],
            }
        )
    return {
        "symbol": analysis.symbol,
        "source": analysis.source_note,
        "summary": render_confluence(analysis),
        "timeframes": frames,
    }


def _opportunity_dict(opportunity: Opportunity | None) -> dict | None:
    if opportunity is None:
        return None
    return {
        "time": format_time(opportunity.time),
        "side": opportunity.side.value if opportunity.side else None,
        "pattern": opportunity.pattern.value,
        "also_matched": [name.value for name in opportunity.also_matched],
        "bias": opportunity.bias.value,
        "grade": opportunity.grade.value if opportunity.grade else None,
        "status": opportunity.status.value,
        "quality": round(opportunity.quality, 4),
        "entry": opportunity.entry,
        "stop": opportunity.stop,
        "target_1r": opportunity.target_1r,
        "target_2r": opportunity.target_2r,
        "break_level": opportunity.break_level,
        "risk": opportunity.risk,
        "candle_types": list(opportunity.candle_types),
        "rationale": opportunity.rationale,
    }
