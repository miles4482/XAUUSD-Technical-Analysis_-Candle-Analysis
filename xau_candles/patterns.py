"""Groups of gold candles that form a bullish or bearish reading."""

from __future__ import annotations

from dataclasses import dataclass

from xau_candles.classify import CANDLE_MEANINGS, classify_candle
from xau_candles.constants import (
    DOJI_BODY_RATIO,
    HARAMI_MIN_PRIOR_BODY,
    SOLDIER_MAX_WICK_VS_BODY,
    SOLDIER_MIN_BODY,
    STAR_MAX_MIDDLE_BODY_RATIO,
    STAR_MAX_MIDDLE_VS_FIRST,
    STAR_MIN_FIRST_BODY,
    TWEEZER_MIN_WICK,
)
from xau_candles.metrics import (
    atr_at,
    average_body_before,
    average_range_before,
    body_bottom,
    body_size,
    body_top,
    measure,
    trend_into,
)
from xau_candles.models import Bias, Candle, CandleRead, CandleType, PatternName, PatternSignal, Trend


PATTERN_MEANINGS: dict[PatternName, str] = {
    PatternName.BULLISH_ENGULFING: (
        "A bearish candle is followed by a bullish candle whose body covers the prior body. "
        "Buyers took back the whole prior decline and closed beyond where that decline began."
    ),
    PatternName.BEARISH_ENGULFING: (
        "A bullish candle is followed by a bearish candle whose body covers the prior body. "
        "Sellers took back the whole prior rally and closed beyond where that rally began."
    ),
    PatternName.BULLISH_HARAMI: (
        "A large bearish candle is followed by a smaller bullish candle sitting inside that body. "
        "The decline paused. This is a warning of a bullish turn, and it is stronger when the "
        "next candle closes through the first candle's high."
    ),
    PatternName.BEARISH_HARAMI: (
        "A large bullish candle is followed by a smaller bearish candle sitting inside that body. "
        "The rally paused. This is a warning of a bearish turn, and it is stronger when the "
        "next candle closes through the first candle's low."
    ),
    PatternName.BULLISH_HARAMI_CROSS: (
        "A large bearish candle is followed by a doji inside its body. The decline lost follow-through. "
        "The doji is balance, so the bullish lean stays weak until a later candle confirms it."
    ),
    PatternName.BEARISH_HARAMI_CROSS: (
        "A large bullish candle is followed by a doji inside its body. The rally lost follow-through. "
        "The doji is balance, so the bearish lean stays weak until a later candle confirms it."
    ),
    PatternName.PIERCING_LINE: (
        "After a bearish candle, a bullish candle opens at or below that close and finishes above "
        "the midpoint of the bearish body, without covering the whole body. Buyers recovered more "
        "than half of the prior loss. On gold this does not require a gap, because the market "
        "usually trades through the session."
    ),
    PatternName.DARK_CLOUD_COVER: (
        "After a bullish candle, a bearish candle opens at or above that close and finishes below "
        "the midpoint of the bullish body, without covering the whole body. Sellers took back more "
        "than half of the prior gain."
    ),
    PatternName.TWEEZER_BOTTOM: (
        "Two candles share a low, the first bearish and the second bullish, with a lower wick "
        "rejecting that price. The market tested the same floor twice and the second candle closed up."
    ),
    PatternName.TWEEZER_TOP: (
        "Two candles share a high, the first bullish and the second bearish, with an upper wick "
        "rejecting that price. The market tested the same ceiling twice and the second candle closed down."
    ),
    PatternName.MORNING_STAR: (
        "A long bearish candle, a small candle near the lows, then a bullish candle that closes "
        "back above the midpoint of the first body. Selling exhausted, and the third candle shows "
        "buyers taking control."
    ),
    PatternName.EVENING_STAR: (
        "A long bullish candle, a small candle near the highs, then a bearish candle that closes "
        "back below the midpoint of the first body. Buying exhausted, and the third candle shows "
        "sellers taking control."
    ),
    PatternName.MORNING_DOJI_STAR: (
        "A morning star whose middle candle is a doji. The low printed balance after a decline, "
        "and the third candle closed back through the midpoint of the decline."
    ),
    PatternName.EVENING_DOJI_STAR: (
        "An evening star whose middle candle is a doji. The high printed balance after a rally, "
        "and the third candle closed back through the midpoint of the rally."
    ),
    PatternName.THREE_WHITE_SOLDIERS: (
        "Three bullish candles in a row, each closing higher and each opening inside the prior body, "
        "with small upper wicks. The group is steady buying, not a single spike."
    ),
    PatternName.THREE_BLACK_CROWS: (
        "Three bearish candles in a row, each closing lower and each opening inside the prior body, "
        "with small lower wicks. The group is steady selling, not a single spike."
    ),
    PatternName.THREE_INSIDE_UP: (
        "A bullish harami followed by a bullish candle that closes above the first candle's high. "
        "The pause inside the decline was confirmed by a break higher."
    ),
    PatternName.THREE_INSIDE_DOWN: (
        "A bearish harami followed by a bearish candle that closes below the first candle's low. "
        "The pause inside the rally was confirmed by a break lower."
    ),
    PatternName.RISING_THREE_METHODS: (
        "A long bullish candle, three small candles that stay inside its range, then a bullish "
        "candle that closes above the first close. The group is a pause inside an advance."
    ),
    PatternName.FALLING_THREE_METHODS: (
        "A long bearish candle, three small candles that stay inside its range, then a bearish "
        "candle that closes below the first close. The group is a pause inside a decline."
    ),
    PatternName.INSIDE_BAR: (
        "The candle's entire high-low range sits inside the previous candle. Price compressed. "
        "The group has no direction until price breaks the mother candle."
    ),
    PatternName.BULLISH_OUTSIDE_BAR: (
        "The candle trades above the prior high and below the prior low, then closes bullish. "
        "Both sides were run, and the close shows buyers kept the bar."
    ),
    PatternName.BEARISH_OUTSIDE_BAR: (
        "The candle trades above the prior high and below the prior low, then closes bearish. "
        "Both sides were run, and the close shows sellers kept the bar."
    ),
    PatternName.BULLISH_KICKER: (
        "A bearish candle is followed by a bullish candle that gaps above the prior high with no "
        "overlap. Control flipped and left a gap. On gold this is most often the Sunday reopen."
    ),
    PatternName.BEARISH_KICKER: (
        "A bullish candle is followed by a bearish candle that gaps below the prior low with no "
        "overlap. Control flipped and left a gap. On gold this is most often the Sunday reopen."
    ),
    PatternName.HAMMER: CANDLE_MEANINGS[CandleType.HAMMER],
    PatternName.HANGING_MAN: CANDLE_MEANINGS[CandleType.HANGING_MAN],
    PatternName.INVERTED_HAMMER: CANDLE_MEANINGS[CandleType.INVERTED_HAMMER],
    PatternName.SHOOTING_STAR: CANDLE_MEANINGS[CandleType.SHOOTING_STAR],
    PatternName.DRAGONFLY_DOJI: CANDLE_MEANINGS[CandleType.DRAGONFLY_DOJI],
    PatternName.GRAVESTONE_DOJI: CANDLE_MEANINGS[CandleType.GRAVESTONE_DOJI],
    PatternName.BULLISH_PIN_BAR: CANDLE_MEANINGS[CandleType.BULLISH_PIN_BAR],
    PatternName.BEARISH_PIN_BAR: CANDLE_MEANINGS[CandleType.BEARISH_PIN_BAR],
}


@dataclass(frozen=True)
class Scan:
    candles: list[Candle]
    reads: list[CandleRead]
    trends: list[Trend]
    atr: list[float]


def prepare_scan(candles: list[Candle]) -> Scan:
    trends = [trend_into(candles, index) for index in range(len(candles))]
    reads = [
        classify_candle(
            candle,
            index=index,
            trend=trends[index],
            average_body=average_body_before(candles, index),
            average_range=average_range_before(candles, index),
        )
        for index, candle in enumerate(candles)
    ]
    atr = [atr_at(candles, index) for index in range(len(candles))]
    return Scan(candles=list(candles), reads=reads, trends=trends, atr=atr)


def _is_bull(candle: Candle) -> bool:
    return candle.close > candle.open


def _is_bear(candle: Candle) -> bool:
    return candle.close < candle.open


def _score(base: float, *adjustments: float) -> float:
    value = base + sum(adjustments)
    return max(0.0, min(1.0, value))


def _signal(
    name: PatternName,
    bias: Bias,
    start: int,
    end: int,
    quality: float,
) -> PatternSignal:
    return PatternSignal(
        name=name,
        bias=bias,
        start_index=start,
        end_index=end,
        quality=quality,
        candles_involved=end - start + 1,
        meaning=PATTERN_MEANINGS[name],
    )


def _body_inside(inner: Candle, outer: Candle) -> bool:
    return body_top(inner) <= body_top(outer) and body_bottom(inner) >= body_bottom(outer)


def _near(left: float, right: float, atr: float) -> bool:
    tolerance = max(0.15 * atr, 0.01)
    return abs(left - right) <= tolerance


def _engulfing(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    prev_body = body_size(previous)
    cur_body = body_size(current)
    if prev_body <= 0 or cur_body <= prev_body:
        return []
    # A pin-bar wick can cover a small prior body without buyers or sellers actually
    # taking control. Engulfing needs both bodies to be a real share of their candles.
    if scan.reads[index].body_ratio < 0.40 or scan.reads[index - 1].body_ratio < 0.30:
        return []
    trend = scan.trends[index]
    current_ratio = scan.reads[index].body_ratio
    tiny_penalty = -0.15 if prev_body < 0.35 * cur_body else 0.0
    wick_bonus = 0.05 if current.low <= previous.low and current.high >= previous.high else 0.0
    body_bonus = 0.08 if current_ratio >= 0.60 else 0.0

    if (
        _is_bear(previous)
        and _is_bull(current)
        and body_bottom(current) <= body_bottom(previous)
        and body_top(current) >= body_top(previous)
    ):
        quality = _score(
            0.62,
            0.15 if trend is Trend.DOWN else 0.0,
            body_bonus,
            wick_bonus,
            tiny_penalty,
        )
        return [_signal(PatternName.BULLISH_ENGULFING, Bias.BULLISH, index - 1, index, quality)]

    if (
        _is_bull(previous)
        and _is_bear(current)
        and body_bottom(current) <= body_bottom(previous)
        and body_top(current) >= body_top(previous)
    ):
        quality = _score(
            0.62,
            0.15 if trend is Trend.UP else 0.0,
            body_bonus,
            wick_bonus,
            tiny_penalty,
        )
        return [_signal(PatternName.BEARISH_ENGULFING, Bias.BEARISH, index - 1, index, quality)]
    return []


def _harami(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    if scan.reads[index - 1].body_ratio < HARAMI_MIN_PRIOR_BODY:
        return []
    if body_size(current) >= body_size(previous) or not _body_inside(current, previous):
        return []
    doji = scan.reads[index].body_ratio <= DOJI_BODY_RATIO
    trend = scan.trends[index]
    if _is_bear(previous) and not _is_bear(current):
        name = PatternName.BULLISH_HARAMI_CROSS if doji else PatternName.BULLISH_HARAMI
        quality = _score(0.44 if doji else 0.46, 0.12 if trend is Trend.DOWN else 0.0)
        return [_signal(name, Bias.BULLISH, index - 1, index, quality)]
    if _is_bull(previous) and not _is_bull(current):
        name = PatternName.BEARISH_HARAMI_CROSS if doji else PatternName.BEARISH_HARAMI
        quality = _score(0.44 if doji else 0.46, 0.12 if trend is Trend.UP else 0.0)
        return [_signal(name, Bias.BEARISH, index - 1, index, quality)]
    return []


def _piercing_and_cloud(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    if body_size(previous) <= 0:
        return []
    midpoint = (previous.open + previous.close) / 2
    # Gold often has no gap, so the open may sit on the prior close. The close still
    # has to travel a real distance through the prior body, not just tick the midpoint.
    min_push = 0.15 * body_size(previous)
    trend = scan.trends[index]
    # A full body engulf is classified as engulfing, so these stop short of the prior open.
    if (
        _is_bear(previous)
        and _is_bull(current)
        and current.open <= previous.close
        and midpoint + min_push < current.close < previous.open
    ):
        gap_bonus = 0.06 if current.open < previous.low else 0.0
        quality = _score(0.60, 0.12 if trend is Trend.DOWN else 0.0, gap_bonus)
        return [_signal(PatternName.PIERCING_LINE, Bias.BULLISH, index - 1, index, quality)]
    if (
        _is_bull(previous)
        and _is_bear(current)
        and current.open >= previous.close
        and previous.open < current.close < midpoint - min_push
    ):
        gap_bonus = 0.06 if current.open > previous.high else 0.0
        quality = _score(0.60, 0.12 if trend is Trend.UP else 0.0, gap_bonus)
        return [_signal(PatternName.DARK_CLOUD_COVER, Bias.BEARISH, index - 1, index, quality)]
    return []


def _tweezer(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    atr = scan.atr[index]
    prev_read = scan.reads[index - 1]
    cur_read = scan.reads[index]
    trend = scan.trends[index]
    if _is_bear(previous) and _is_bull(current) and _near(previous.low, current.low, atr):
        if max(prev_read.lower_wick_ratio, cur_read.lower_wick_ratio) < TWEEZER_MIN_WICK:
            return []
        quality = _score(0.58, 0.10 if trend is Trend.DOWN else 0.0)
        return [_signal(PatternName.TWEEZER_BOTTOM, Bias.BULLISH, index - 1, index, quality)]
    if _is_bull(previous) and _is_bear(current) and _near(previous.high, current.high, atr):
        if max(prev_read.upper_wick_ratio, cur_read.upper_wick_ratio) < TWEEZER_MIN_WICK:
            return []
        quality = _score(0.58, 0.10 if trend is Trend.UP else 0.0)
        return [_signal(PatternName.TWEEZER_TOP, Bias.BEARISH, index - 1, index, quality)]
    return []


def _star(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 2:
        return []
    first, middle, last = scan.candles[index - 2], scan.candles[index - 1], scan.candles[index]
    first_body = body_size(first)
    middle_body = body_size(middle)
    if first_body <= 0 or middle_body > STAR_MAX_MIDDLE_VS_FIRST * first_body:
        return []
    first_read = scan.reads[index - 2]
    middle_read = scan.reads[index - 1]
    last_read = scan.reads[index]
    if first_read.body_ratio < STAR_MIN_FIRST_BODY or middle_read.body_ratio > STAR_MAX_MIDDLE_BODY_RATIO:
        return []
    if last_read.body_ratio < 0.35:
        return []
    midpoint = (first.open + first.close) / 2
    middle_mid = (middle.open + middle.close) / 2
    doji_star = middle_read.body_ratio <= DOJI_BODY_RATIO
    trend = scan.trends[index]
    if _is_bear(first) and _is_bull(last) and middle_mid < midpoint and last.close > midpoint:
        name = PatternName.MORNING_DOJI_STAR if doji_star else PatternName.MORNING_STAR
        quality = _score(0.72 if doji_star else 0.70, 0.12 if trend is Trend.DOWN else 0.0)
        return [_signal(name, Bias.BULLISH, index - 2, index, quality)]
    if _is_bull(first) and _is_bear(last) and middle_mid > midpoint and last.close < midpoint:
        name = PatternName.EVENING_DOJI_STAR if doji_star else PatternName.EVENING_STAR
        quality = _score(0.72 if doji_star else 0.70, 0.12 if trend is Trend.UP else 0.0)
        return [_signal(name, Bias.BEARISH, index - 2, index, quality)]
    return []


def _small_upper_wick(candle: Candle) -> bool:
    metrics = measure(candle)
    return metrics.body > 0 and metrics.upper_wick <= SOLDIER_MAX_WICK_VS_BODY * metrics.body


def _small_lower_wick(candle: Candle) -> bool:
    metrics = measure(candle)
    return metrics.body > 0 and metrics.lower_wick <= SOLDIER_MAX_WICK_VS_BODY * metrics.body


def _soldiers_and_crows(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 2:
        return []
    group = scan.candles[index - 2 : index + 1]
    reads = scan.reads[index - 2 : index + 1]
    if any(read.body_ratio < SOLDIER_MIN_BODY for read in reads):
        return []
    trend = scan.trends[index]
    if all(_is_bull(candle) for candle in group) and all(_small_upper_wick(candle) for candle in group):
        opens_inside = all(
            group[cursor - 1].open <= group[cursor].open <= group[cursor - 1].close
            for cursor in (1, 2)
        )
        closes_higher = group[1].close > group[0].close and group[2].close > group[1].close
        bodies_hold = body_size(group[1]) >= 0.5 * body_size(group[0]) and body_size(group[2]) >= 0.5 * body_size(group[1])
        if opens_inside and closes_higher and bodies_hold:
            quality = _score(0.78, 0.06 if trend is Trend.DOWN else 0.0)
            return [_signal(PatternName.THREE_WHITE_SOLDIERS, Bias.BULLISH, index - 2, index, quality)]
    if all(_is_bear(candle) for candle in group) and all(_small_lower_wick(candle) for candle in group):
        opens_inside = all(
            group[cursor - 1].close <= group[cursor].open <= group[cursor - 1].open
            for cursor in (1, 2)
        )
        closes_lower = group[1].close < group[0].close and group[2].close < group[1].close
        bodies_hold = body_size(group[1]) >= 0.5 * body_size(group[0]) and body_size(group[2]) >= 0.5 * body_size(group[1])
        if opens_inside and closes_lower and bodies_hold:
            quality = _score(0.78, 0.06 if trend is Trend.UP else 0.0)
            return [_signal(PatternName.THREE_BLACK_CROWS, Bias.BEARISH, index - 2, index, quality)]
    return []


def _three_inside(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 2:
        return []
    first, middle, last = scan.candles[index - 2], scan.candles[index - 1], scan.candles[index]
    if scan.reads[index - 2].body_ratio < HARAMI_MIN_PRIOR_BODY:
        return []
    if body_size(middle) >= body_size(first) or not _body_inside(middle, first):
        return []
    trend = scan.trends[index]
    if _is_bear(first) and _is_bull(middle) and _is_bull(last) and last.close > first.high:
        quality = _score(0.74, 0.08 if trend is Trend.DOWN else 0.0)
        return [_signal(PatternName.THREE_INSIDE_UP, Bias.BULLISH, index - 2, index, quality)]
    if _is_bull(first) and _is_bear(middle) and _is_bear(last) and last.close < first.low:
        quality = _score(0.74, 0.08 if trend is Trend.UP else 0.0)
        return [_signal(PatternName.THREE_INSIDE_DOWN, Bias.BEARISH, index - 2, index, quality)]
    return []


def _holds_inside_range(inner: Candle, outer: Candle) -> bool:
    return inner.high <= outer.high and inner.low >= outer.low and body_size(inner) <= 0.6 * body_size(outer)


def _three_methods(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 4:
        return []
    first = scan.candles[index - 4]
    middle = scan.candles[index - 3 : index]
    last = scan.candles[index]
    if scan.reads[index - 4].body_ratio < 0.55 or body_size(first) <= 0:
        return []
    if not all(_holds_inside_range(candle, first) for candle in middle):
        return []
    trend = scan.trends[index]
    if _is_bull(first) and _is_bull(last) and last.close > first.close and sum(_is_bear(candle) for candle in middle) >= 2:
        quality = _score(0.74, 0.06 if trend is Trend.UP else 0.0)
        return [_signal(PatternName.RISING_THREE_METHODS, Bias.BULLISH, index - 4, index, quality)]
    if _is_bear(first) and _is_bear(last) and last.close < first.close and sum(_is_bull(candle) for candle in middle) >= 2:
        quality = _score(0.74, 0.06 if trend is Trend.DOWN else 0.0)
        return [_signal(PatternName.FALLING_THREE_METHODS, Bias.BEARISH, index - 4, index, quality)]
    return []


def _inside_outside(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    prev_span = previous.high - previous.low
    cur_span = current.high - current.low
    found: list[PatternSignal] = []
    if prev_span > 0 and cur_span < prev_span and current.high <= previous.high and current.low >= previous.low:
        found.append(_signal(PatternName.INSIDE_BAR, Bias.INDECISION, index - 1, index, 0.58))
    # A pin-bar wick often runs both sides of the prior candle. That is a rejection,
    # not an outside bar. An outside bar needs a real body that closes with the break.
    if (
        current.high > previous.high
        and current.low < previous.low
        and scan.reads[index].body_ratio >= 0.45
    ):
        midpoint = (current.high + current.low) / 2
        trend = scan.trends[index]
        if _is_bull(current) and current.close >= midpoint:
            quality = _score(0.60, 0.08 if trend is Trend.UP else 0.0)
            found.append(_signal(PatternName.BULLISH_OUTSIDE_BAR, Bias.BULLISH, index - 1, index, quality))
        elif _is_bear(current) and current.close <= midpoint:
            quality = _score(0.60, 0.08 if trend is Trend.DOWN else 0.0)
            found.append(_signal(PatternName.BEARISH_OUTSIDE_BAR, Bias.BEARISH, index - 1, index, quality))
    return found


def _kicker(scan: Scan, index: int) -> list[PatternSignal]:
    if index < 1:
        return []
    previous = scan.candles[index - 1]
    current = scan.candles[index]
    trend = scan.trends[index]
    if _is_bear(previous) and _is_bull(current) and current.low > previous.high:
        quality = _score(0.80, 0.08 if trend is Trend.DOWN else 0.0)
        return [_signal(PatternName.BULLISH_KICKER, Bias.BULLISH, index - 1, index, quality)]
    if _is_bull(previous) and _is_bear(current) and current.high < previous.low:
        quality = _score(0.80, 0.08 if trend is Trend.UP else 0.0)
        return [_signal(PatternName.BEARISH_KICKER, Bias.BEARISH, index - 1, index, quality)]
    return []


_SINGLE_TYPES: dict[CandleType, tuple[PatternName, float]] = {
    CandleType.HAMMER: (PatternName.HAMMER, 0.70),
    CandleType.HANGING_MAN: (PatternName.HANGING_MAN, 0.66),
    CandleType.INVERTED_HAMMER: (PatternName.INVERTED_HAMMER, 0.62),
    CandleType.SHOOTING_STAR: (PatternName.SHOOTING_STAR, 0.70),
    CandleType.BULLISH_PIN_BAR: (PatternName.BULLISH_PIN_BAR, 0.44),
    CandleType.BEARISH_PIN_BAR: (PatternName.BEARISH_PIN_BAR, 0.44),
}


def _single_rejection(scan: Scan, index: int) -> list[PatternSignal]:
    read = scan.reads[index]
    trend = scan.trends[index]
    if read.candle_type in _SINGLE_TYPES:
        name, quality = _SINGLE_TYPES[read.candle_type]
        return [_signal(name, read.bias, index, index, quality)]
    if read.candle_type is CandleType.DRAGONFLY_DOJI:
        quality = 0.64 if trend is Trend.DOWN else 0.42
        return [_signal(PatternName.DRAGONFLY_DOJI, Bias.BULLISH, index, index, quality)]
    if read.candle_type is CandleType.GRAVESTONE_DOJI:
        quality = 0.64 if trend is Trend.UP else 0.42
        return [_signal(PatternName.GRAVESTONE_DOJI, Bias.BEARISH, index, index, quality)]
    return []


DETECTORS = (
    _engulfing,
    _harami,
    _piercing_and_cloud,
    _tweezer,
    _star,
    _soldiers_and_crows,
    _three_inside,
    _three_methods,
    _inside_outside,
    _kicker,
    _single_rejection,
)


def find_patterns(candles: list[Candle], scan: Scan | None = None) -> list[PatternSignal]:
    active = scan if scan is not None else prepare_scan(candles)
    found: list[PatternSignal] = []
    for index in range(len(active.candles)):
        for detector in DETECTORS:
            found.extend(detector(active, index))
    return found
