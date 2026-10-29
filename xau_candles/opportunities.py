"""Turn a candle group into a levelled long or short plan."""

from __future__ import annotations

from xau_candles.constants import (
    HTF_AGREE_GRADE_A,
    MIN_RISK_ATR,
    MIN_TRADE_QUALITY,
    SOLO_GROUP_GRADE_A,
    STOP_ATR_BUFFER,
)
from xau_candles.models import (
    Bias,
    Grade,
    Opportunity,
    PatternName,
    PatternSignal,
    SetupBoard,
    SetupStatus,
    Side,
    Trend,
)
from xau_candles.patterns import Scan


def grade_setup(
    side: Side,
    quality: float,
    htf_bias: Trend,
    candles_involved: int,
) -> Grade:
    """A agrees with the higher timeframe or is a strong group on its own.

    C is a setup whose side fights the next higher timeframe. B is a valid
    read that does not earn A.
    """

    if htf_bias in (Trend.UP, Trend.DOWN):
        agrees = (htf_bias is Trend.UP and side is Side.LONG) or (
            htf_bias is Trend.DOWN and side is Side.SHORT
        )
        if not agrees:
            return Grade.C
        if quality >= HTF_AGREE_GRADE_A:
            return Grade.A
        return Grade.B
    if quality >= SOLO_GROUP_GRADE_A and candles_involved >= 2:
        return Grade.A
    if quality >= MIN_TRADE_QUALITY:
        return Grade.B
    return Grade.C


def _side_of(pattern: PatternSignal) -> Side | None:
    if pattern.bias is Bias.BULLISH:
        return Side.LONG
    if pattern.bias is Bias.BEARISH:
        return Side.SHORT
    return None


def _trend_side(trend: Trend) -> Side | None:
    if trend is Trend.UP:
        return Side.LONG
    if trend is Trend.DOWN:
        return Side.SHORT
    return None


def _levels(
    scan: Scan,
    pattern: PatternSignal,
    side: Side,
    *,
    entry: float,
    stop_anchor: float,
    break_level: float,
) -> tuple[float, float, float, float, float, float] | None:
    atr = scan.atr[pattern.end_index]
    buffer = STOP_ATR_BUFFER * atr
    # A stop glued to a tiny wick sits inside normal gold noise. Half an ATR is the floor.
    noise_floor = MIN_RISK_ATR * atr
    if side is Side.LONG:
        stop = min(stop_anchor - buffer, entry - noise_floor)
        risk = entry - stop
        if risk <= 0:
            return None
        return entry, stop, entry + risk, entry + 2 * risk, break_level, risk
    stop = max(stop_anchor + buffer, entry + noise_floor)
    risk = stop - entry
    if risk <= 0:
        return None
    return entry, stop, entry - risk, entry - 2 * risk, break_level, risk


def _close_levels(scan: Scan, pattern: PatternSignal, side: Side):
    group = scan.candles[pattern.start_index : pattern.end_index + 1]
    signal = group[-1]
    if side is Side.LONG:
        return _levels(
            scan,
            pattern,
            side,
            entry=signal.close,
            stop_anchor=min(candle.low for candle in group),
            break_level=max(candle.high for candle in group),
        )
    return _levels(
        scan,
        pattern,
        side,
        entry=signal.close,
        stop_anchor=max(candle.high for candle in group),
        break_level=min(candle.low for candle in group),
    )


def _inside_levels(scan: Scan, pattern: PatternSignal, side: Side):
    mother = scan.candles[pattern.start_index]
    if side is Side.LONG:
        return _levels(
            scan,
            pattern,
            side,
            entry=mother.high,
            stop_anchor=mother.low,
            break_level=mother.high,
        )
    return _levels(
        scan,
        pattern,
        side,
        entry=mother.low,
        stop_anchor=mother.high,
        break_level=mother.low,
    )


def _faded(side: Side, entry: float, stop: float, last_close: float) -> bool:
    """True when the latest close has already given back more than half the original risk."""

    midpoint = (entry + stop) / 2
    if side is Side.LONG:
        return last_close < midpoint
    return last_close > midpoint


def _path_after(scan: Scan, end_index: int, side: Side, entry: float, stop: float, armed: bool) -> str:
    """What later candles did to the plan. `open` means the plan is untouched."""

    state = "open"
    for candle in scan.candles[end_index + 1 :]:
        if side is Side.LONG:
            hit_stop = candle.low <= stop
            hit_entry = candle.high >= entry
        else:
            hit_stop = candle.high >= stop
            hit_entry = candle.low <= entry
        if armed and hit_stop and hit_entry:
            return "ambiguous"
        if hit_stop:
            return "invalidated"
        if armed and hit_entry:
            state = "triggered"
    return state


def _status_for(end_index: int, last_index: int, armed: bool, path: str) -> SetupStatus | None:
    if path in ("invalidated", "ambiguous"):
        return None
    if armed and path == "triggered":
        return SetupStatus.TRIGGERED
    if armed:
        return SetupStatus.ARMED
    if end_index == last_index:
        return SetupStatus.SIGNAL_CLOSED
    return SetupStatus.STILL_VALID


def _grade_sentence(grade: Grade, htf_bias: Trend) -> str:
    if grade is Grade.C and htf_bias in (Trend.UP, Trend.DOWN):
        return "This side fights the higher timeframe, so it is the countertrend read."
    if grade is Grade.A and htf_bias in (Trend.UP, Trend.DOWN):
        return "This side agrees with the higher timeframe."
    if grade is Grade.A:
        return "The group is strong enough on this timeframe to stand as an A setup."
    return "The setup is valid on this timeframe."


def _rationale(
    scan: Scan,
    pattern: PatternSignal,
    side: Side,
    status: SetupStatus,
    htf_bias: Trend,
    grade: Grade,
) -> str:
    names = [
        scan.reads[index].candle_type.value.replace("_", " ")
        for index in range(pattern.start_index, pattern.end_index + 1)
    ]
    trend = scan.trends[pattern.end_index]
    trend_sentence = {
        Trend.UP: "The swing into the signal was up.",
        Trend.DOWN: "The swing into the signal was down.",
        Trend.RANGE: "The swing into the signal was sideways.",
        Trend.UNKNOWN: "There are not enough candles yet to call the swing.",
    }[trend]
    htf_sentence = {
        Trend.UP: "The next higher timeframe is in an uptrend.",
        Trend.DOWN: "The next higher timeframe is in a downtrend.",
        Trend.RANGE: "The next higher timeframe is sideways.",
        Trend.UNKNOWN: "No higher timeframe was supplied.",
    }[htf_bias]
    if status is SetupStatus.ARMED:
        entry_sentence = (
            "The entry is a break of the mother candle. The plan stays armed until that break, "
            "or until the stop is traded."
        )
    elif status is SetupStatus.TRIGGERED:
        entry_sentence = (
            "Price has already broken the mother candle, and no later candle has traded the stop."
        )
    elif status is SetupStatus.STILL_VALID:
        entry_sentence = (
            "The signal closed on an earlier candle, and later candles have stayed on the safe side of the stop."
        )
    else:
        entry_sentence = (
            "The entry is the close of the signal candle. A stricter trigger is a break of the signal extreme."
        )
    side_sentence = (
        "The group is bullish, so the plan is long."
        if side is Side.LONG
        else "The group is bearish, so the plan is short."
    )
    return " ".join(
        (
            pattern.meaning,
            f"Candles in the group: {', '.join(names)}.",
            trend_sentence,
            htf_sentence,
            side_sentence,
            entry_sentence,
            "The stop is the farther of the pattern extreme and half an ATR, so a normal wick does not take it. "
            "The 1R and 2R targets are measured from that risk.",
            _grade_sentence(grade, htf_bias),
        )
    )


def _build_opportunity(
    scan: Scan,
    pattern: PatternSignal,
    alternates: tuple[PatternName, ...],
    *,
    timeframe: str,
    htf_bias: Trend,
    last_index: int,
    status_override: SetupStatus | None = None,
) -> Opportunity | None:
    armed = pattern.name is PatternName.INSIDE_BAR
    if armed:
        side = _trend_side(scan.trends[pattern.end_index])
        if side is None:
            return None
        levels = _inside_levels(scan, pattern, side)
    else:
        side = _side_of(pattern)
        if side is None:
            return None
        levels = _close_levels(scan, pattern, side)
    if levels is None:
        return None
    entry, stop, target_1r, target_2r, break_level, risk = levels
    if pattern.end_index < last_index and _faded(side, entry, stop, scan.candles[-1].close):
        return None
    path = _path_after(scan, pattern.end_index, side, entry, stop, armed)
    status = status_override or _status_for(pattern.end_index, last_index, armed, path)
    if status is None:
        return None
    grade = grade_setup(side, pattern.quality, htf_bias, pattern.candles_involved)
    types = tuple(
        scan.reads[index].candle_type.value
        for index in range(pattern.start_index, pattern.end_index + 1)
    )
    return Opportunity(
        timeframe=timeframe,
        time=scan.candles[pattern.end_index].time,
        side=side,
        pattern=pattern.name,
        also_matched=alternates,
        bias=pattern.bias,
        grade=grade,
        status=status,
        quality=pattern.quality,
        entry=entry,
        stop=stop,
        target_1r=target_1r,
        target_2r=target_2r,
        break_level=break_level,
        risk=risk,
        candle_types=types,
        rationale=_rationale(scan, pattern, side, status, htf_bias, grade),
    )


def _watch(scan: Scan, pattern: PatternSignal, timeframe: str) -> Opportunity:
    types = tuple(
        scan.reads[index].candle_type.value
        for index in range(pattern.start_index, pattern.end_index + 1)
    )
    return Opportunity(
        timeframe=timeframe,
        time=scan.candles[pattern.end_index].time,
        side=_side_of(pattern),
        pattern=pattern.name,
        also_matched=(),
        bias=pattern.bias,
        grade=None,
        status=SetupStatus.WATCH,
        quality=pattern.quality,
        entry=None,
        stop=None,
        target_1r=None,
        target_2r=None,
        break_level=None,
        risk=None,
        candle_types=types,
        rationale=(
            f"{pattern.meaning} Quality is {pattern.quality:.2f}, under the level that earns a trade plan, "
            "so this stays a watch."
        ),
    )


def _ranked(patterns: list[PatternSignal]) -> list[PatternSignal]:
    return sorted(patterns, key=lambda pattern: (pattern.quality, pattern.candles_involved), reverse=True)


def _alternates(patterns: list[PatternSignal], primary: PatternSignal) -> tuple[PatternName, ...]:
    names = [
        pattern.name
        for pattern in _ranked(patterns)
        if pattern.end_index == primary.end_index and pattern.name is not primary.name
    ]
    return tuple(dict.fromkeys(names))


def build_board(
    scan: Scan,
    patterns: list[PatternSignal],
    *,
    timeframe: str,
    htf_bias: Trend,
    lookback: int,
) -> SetupBoard:
    if not scan.candles:
        return SetupBoard(primary=None, watches=())
    last_index = len(scan.candles) - 1
    recent = [pattern for pattern in patterns if 0 <= last_index - pattern.end_index <= lookback]
    strong = [
        pattern
        for pattern in recent
        if pattern.bias is not Bias.INDECISION
        and pattern.quality >= MIN_TRADE_QUALITY
        and pattern.name is not PatternName.INSIDE_BAR
    ]
    for end_index in sorted({pattern.end_index for pattern in strong}, reverse=True):
        pool = [pattern for pattern in strong if pattern.end_index == end_index]
        bull = _ranked([pattern for pattern in pool if pattern.bias is Bias.BULLISH])
        bear = _ranked([pattern for pattern in pool if pattern.bias is Bias.BEARISH])
        bull_groups = [pattern for pattern in bull if pattern.candles_involved >= 2]
        bear_groups = [pattern for pattern in bear if pattern.candles_involved >= 2]
        if bull_groups and bear_groups:
            bull_plan = _first_live(scan, bull_groups, timeframe, htf_bias, last_index, recent)
            bear_plan = _first_live(scan, bear_groups, timeframe, htf_bias, last_index, recent)
            if bull_plan and bear_plan:
                note = (
                    f"The last group is split: {bull_plan.pattern.value.replace('_', ' ')} leans long "
                    f"and {bear_plan.pattern.value.replace('_', ' ')} leans short. Stand aside until "
                    "one side fails."
                )
                return SetupBoard(primary=None, watches=(), conflict_note=note)
            winner = bull_plan or bear_plan
            if winner is not None:
                return SetupBoard(primary=winner, watches=())
            continue
        if bull and bear and not bull_groups and not bear_groups:
            note = (
                "Two single-candle reads on this bar disagree. One leans long and the other leans short. "
                "Stand aside until a group of candles picks a side."
            )
            return SetupBoard(primary=None, watches=(), conflict_note=note)
        side_pool = bull_groups or bear_groups or bull or bear
        winner = _first_live(scan, side_pool, timeframe, htf_bias, last_index, recent)
        if winner is not None:
            return SetupBoard(primary=winner, watches=())

    insides = [pattern for pattern in recent if pattern.name is PatternName.INSIDE_BAR]
    for end_index in sorted({pattern.end_index for pattern in insides}, reverse=True):
        winner = _first_live(
            scan,
            [pattern for pattern in insides if pattern.end_index == end_index],
            timeframe,
            htf_bias,
            last_index,
            recent,
        )
        if winner is not None:
            return SetupBoard(primary=winner, watches=())

    weak = [
        pattern
        for pattern in recent
        if pattern.bias is not Bias.INDECISION and pattern.quality < MIN_TRADE_QUALITY
    ]
    if not weak and insides:
        weak = insides
    watches = tuple(_watch(scan, pattern, timeframe) for pattern in _ranked(weak)[:3])
    return SetupBoard(primary=None, watches=watches)


def _first_live(
    scan: Scan,
    pool: list[PatternSignal],
    timeframe: str,
    htf_bias: Trend,
    last_index: int,
    recent: list[PatternSignal],
) -> Opportunity | None:
    for pattern in _ranked(pool):
        opportunity = _build_opportunity(
            scan,
            pattern,
            _alternates(recent, pattern),
            timeframe=timeframe,
            htf_bias=htf_bias,
            last_index=last_index,
        )
        if opportunity is not None:
            return opportunity
    return None
