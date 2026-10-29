"""Candle measurements, average range, and the swing trend into a bar."""

from __future__ import annotations

from dataclasses import dataclass

from xau_candles.constants import ATR_PERIOD, AVG_LOOKBACK, FAST_SMA, SLOW_SMA
from xau_candles.models import Candle, Trend


@dataclass(frozen=True)
class Metrics:
    body: float
    range: float
    upper_wick: float
    lower_wick: float
    body_ratio: float
    upper_ratio: float
    lower_ratio: float


def body_size(candle: Candle) -> float:
    return abs(candle.close - candle.open)


def body_top(candle: Candle) -> float:
    return max(candle.open, candle.close)


def body_bottom(candle: Candle) -> float:
    return min(candle.open, candle.close)


def measure(candle: Candle) -> Metrics:
    span = candle.high - candle.low
    body = body_size(candle)
    upper = candle.high - body_top(candle)
    lower = body_bottom(candle) - candle.low
    if span <= 0:
        return Metrics(body, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    return Metrics(
        body=body,
        range=span,
        upper_wick=upper,
        lower_wick=lower,
        body_ratio=body / span,
        upper_ratio=upper / span,
        lower_ratio=lower / span,
    )


def average_body_before(candles: list[Candle], index: int, lookback: int = AVG_LOOKBACK) -> float:
    window = candles[max(0, index - lookback) : index]
    if not window:
        return 0.0
    return sum(body_size(candle) for candle in window) / len(window)


def average_range_before(candles: list[Candle], index: int, lookback: int = AVG_LOOKBACK) -> float:
    window = candles[max(0, index - lookback) : index]
    if not window:
        return 0.0
    return sum(candle.high - candle.low for candle in window) / len(window)


def true_range(candle: Candle, previous_close: float | None) -> float:
    span = candle.high - candle.low
    if previous_close is None:
        return span
    return max(span, abs(candle.high - previous_close), abs(candle.low - previous_close))


def atr_at(candles: list[Candle], index: int, period: int = ATR_PERIOD) -> float:
    """Simple average true range through `index`, using only candles up to that bar."""

    if not candles:
        return 0.0
    start = max(0, index - period + 1)
    total = 0.0
    count = 0
    for cursor in range(start, index + 1):
        previous = candles[cursor - 1].close if cursor else None
        total += true_range(candles[cursor], previous)
        count += 1
    return total / count if count else 0.0


def trend_into(candles: list[Candle], index: int, fast: int = FAST_SMA, slow: int = SLOW_SMA) -> Trend:
    """Trend that was already in place before the candle at `index`.

    Fast and slow averages are simple closes. Up means the fast average is
    above the slow average and the last close sits above the fast average.
    Down is the mirror. Anything in between is a range. Short history is unknown.
    """

    if index < slow:
        return Trend.UNKNOWN
    closes = [candle.close for candle in candles[index - slow : index]]
    fast_average = sum(closes[-fast:]) / fast
    slow_average = sum(closes) / slow
    last = closes[-1]
    if fast_average > slow_average and last > fast_average:
        return Trend.UP
    if fast_average < slow_average and last < fast_average:
        return Trend.DOWN
    return Trend.RANGE
