"""Analyze one gold series, and align several timeframes."""

from __future__ import annotations

from xau_candles.constants import ACTIVE_LOOKBACK, TF_SECONDS, normalize_timeframe
from xau_candles.models import Candle, MultiTimeframeAnalysis, TimeframeAnalysis, Trend
from xau_candles.opportunities import build_board
from xau_candles.patterns import find_patterns, prepare_scan


def analyze(
    candles: list[Candle],
    timeframe: str,
    *,
    htf_bias: Trend = Trend.UNKNOWN,
    lookback: int = ACTIVE_LOOKBACK,
) -> TimeframeAnalysis:
    """Read every candle, find groups, and build the active trade plan for this timeframe."""

    label = normalize_timeframe(timeframe)
    if lookback < 0:
        raise ValueError("lookback must be zero or more")
    scan = prepare_scan(candles)
    patterns = find_patterns(candles, scan)
    board = build_board(
        scan,
        patterns,
        timeframe=label,
        htf_bias=htf_bias,
        lookback=lookback,
    )
    trend = scan.trends[-1] if scan.trends else Trend.UNKNOWN
    return TimeframeAnalysis(
        timeframe=label,
        trend=trend,
        htf_bias=htf_bias,
        reads=tuple(scan.reads),
        patterns=tuple(patterns),
        board=board,
    )


def analyze_many(
    series: dict[str, list[Candle]],
    *,
    symbol: str = "XAUUSD",
    source_note: str = "",
    lookback: int = ACTIVE_LOOKBACK,
) -> MultiTimeframeAnalysis:
    """Analyze each timeframe and pass the next-higher trend down as context.

    The returned order runs from the highest timeframe to the lowest.
    """

    if not series:
        raise ValueError("at least one timeframe is required")
    labels = {name: normalize_timeframe(name) for name in series}
    order = tuple(sorted(series, key=lambda name: TF_SECONDS[labels[name]], reverse=True))
    analyses: dict[str, TimeframeAnalysis] = {}
    for position, name in enumerate(order):
        higher = Trend.UNKNOWN
        if position:
            higher = analyses[order[position - 1]].trend
        analysis = analyze(series[name], labels[name], htf_bias=higher, lookback=lookback)
        analyses[labels[name]] = analysis
    return MultiTimeframeAnalysis(
        order=tuple(labels[name] for name in order),
        analyses=analyses,
        symbol=symbol,
        source_note=source_note,
    )
