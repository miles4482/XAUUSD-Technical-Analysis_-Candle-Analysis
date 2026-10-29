"""Textbook gold candles so every type can be read without a live feed."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from xau_candles.models import Candle, CandleType, PatternName, Side, Trend

START = datetime(2026, 10, 1, tzinfo=timezone.utc)


def _at(index: int, open_: float, high: float, low: float, close: float) -> Candle:
    return Candle(
        time=START + timedelta(hours=index),
        open=open_,
        high=high,
        low=low,
        close=close,
    )


def make_series(
    direction: str,
    extra: list[tuple[float, float, float, float]],
    *,
    count: int = 30,
    start: float = 2400.0,
    step: float = 3.0,
) -> list[Candle]:
    """Build a clean swing, then append the candles that form the pattern.

    Prefix candles carry a wick large enough that they are not three soldiers
    or three crows by themselves.
    """

    candles: list[Candle] = []
    price = start
    for index in range(count):
        if direction == "down":
            open_, close = price, price - step
        elif direction == "up":
            open_, close = price, price + step
        else:
            raise ValueError("direction must be up or down")
        candles.append(
            _at(index, open_, max(open_, close) + 1.6, min(open_, close) - 1.6, close)
        )
        price = close
    for offset, (open_, high, low, close) in enumerate(extra):
        candles.append(_at(count + offset, open_, high, low, close))
    return candles


@dataclass(frozen=True)
class GalleryItem:
    title: str
    candle: Candle
    trend: Trend
    expected: CandleType
    average_body: float = 0.0


def _gallery_candle(open_: float, high: float, low: float, close: float) -> Candle:
    return _at(0, open_, high, low, close)


GALLERY: tuple[GalleryItem, ...] = (
    GalleryItem("Bullish", _gallery_candle(100, 103, 99, 102), Trend.UNKNOWN, CandleType.BULLISH),
    GalleryItem("Bearish", _gallery_candle(102, 103, 99, 100), Trend.UNKNOWN, CandleType.BEARISH),
    GalleryItem(
        "Long bullish",
        _gallery_candle(100, 111, 99, 110),
        Trend.UP,
        CandleType.LONG_BULLISH,
        average_body=4,
    ),
    GalleryItem(
        "Long bearish",
        _gallery_candle(110, 111, 99, 100),
        Trend.DOWN,
        CandleType.LONG_BEARISH,
        average_body=4,
    ),
    GalleryItem(
        "Bullish marubozu",
        _gallery_candle(100, 110.2, 99.9, 110),
        Trend.UP,
        CandleType.BULLISH_MARUBOZU,
    ),
    GalleryItem(
        "Bearish marubozu",
        _gallery_candle(110, 110.1, 99.8, 100),
        Trend.DOWN,
        CandleType.BEARISH_MARUBOZU,
    ),
    GalleryItem("Doji", _gallery_candle(100, 134, 34, 109), Trend.RANGE, CandleType.DOJI),
    GalleryItem(
        "Dragonfly doji",
        _gallery_candle(200.4, 200.6, 180, 200),
        Trend.DOWN,
        CandleType.DRAGONFLY_DOJI,
    ),
    GalleryItem(
        "Gravestone doji",
        _gallery_candle(100, 112, 99.8, 100.3),
        Trend.UP,
        CandleType.GRAVESTONE_DOJI,
    ),
    GalleryItem(
        "Long-legged doji",
        _gallery_candle(100, 110, 90, 100.4),
        Trend.RANGE,
        CandleType.LONG_LEGGED_DOJI,
    ),
    GalleryItem(
        "Hammer",
        _gallery_candle(2311, 2318, 2286, 2316),
        Trend.DOWN,
        CandleType.HAMMER,
    ),
    GalleryItem(
        "Hanging man",
        _gallery_candle(2311, 2318, 2286, 2316),
        Trend.UP,
        CandleType.HANGING_MAN,
    ),
    GalleryItem(
        "Inverted hammer",
        _gallery_candle(2308, 2330, 2300, 2302),
        Trend.DOWN,
        CandleType.INVERTED_HAMMER,
    ),
    GalleryItem(
        "Shooting star",
        _gallery_candle(2493, 2522, 2487, 2489),
        Trend.UP,
        CandleType.SHOOTING_STAR,
    ),
    GalleryItem(
        "Bullish pin bar",
        _gallery_candle(2311, 2318, 2286, 2316),
        Trend.RANGE,
        CandleType.BULLISH_PIN_BAR,
    ),
    GalleryItem(
        "Bearish pin bar",
        _gallery_candle(2493, 2522, 2487, 2489),
        Trend.RANGE,
        CandleType.BEARISH_PIN_BAR,
    ),
    GalleryItem(
        "Bullish spinning top",
        _gallery_candle(100, 106, 96, 102),
        Trend.RANGE,
        CandleType.BULLISH_SPINNING_TOP,
    ),
    GalleryItem(
        "Bearish spinning top",
        _gallery_candle(102, 106, 96, 100),
        Trend.RANGE,
        CandleType.BEARISH_SPINNING_TOP,
    ),
    GalleryItem(
        "Bullish belt hold",
        _gallery_candle(100, 112, 100, 110),
        Trend.UP,
        CandleType.BULLISH_BELT_HOLD,
    ),
    GalleryItem(
        "Bearish belt hold",
        _gallery_candle(112, 112, 100, 102),
        Trend.DOWN,
        CandleType.BEARISH_BELT_HOLD,
    ),
    GalleryItem("Flat", _gallery_candle(100, 100, 100, 100), Trend.UNKNOWN, CandleType.FLAT),
)


@dataclass(frozen=True)
class Scenario:
    title: str
    candles: tuple[Candle, ...]
    expected_pattern: PatternName
    expected_side: Side


def _scenario(
    title: str,
    direction: str,
    extra: list[tuple[float, float, float, float]],
    pattern: PatternName,
    side: Side,
) -> Scenario:
    return Scenario(title, tuple(make_series(direction, extra)), pattern, side)


SCENARIOS: tuple[Scenario, ...] = (
    _scenario(
        "Bullish engulfing after a decline",
        "down",
        [(2320, 2322, 2298, 2300), (2296, 2326, 2294, 2324)],
        PatternName.BULLISH_ENGULFING,
        Side.LONG,
    ),
    _scenario(
        "Bearish engulfing after a rally",
        "up",
        [(2470, 2504, 2466, 2500), (2506, 2508, 2462, 2464)],
        PatternName.BEARISH_ENGULFING,
        Side.SHORT,
    ),
    _scenario(
        "Hammer after a decline",
        "down",
        [(2311, 2318, 2286, 2316)],
        PatternName.HAMMER,
        Side.LONG,
    ),
    _scenario(
        "Shooting star after a rally",
        "up",
        [(2493, 2522, 2487, 2489)],
        PatternName.SHOOTING_STAR,
        Side.SHORT,
    ),
    _scenario(
        "Hanging man after a rally",
        "up",
        [(2492, 2498, 2468, 2496)],
        PatternName.HANGING_MAN,
        Side.SHORT,
    ),
    _scenario(
        "Inverted hammer after a decline",
        "down",
        [(2308, 2330, 2300, 2302)],
        PatternName.INVERTED_HAMMER,
        Side.LONG,
    ),
    _scenario(
        "Morning star",
        "down",
        [
            (2330, 2332, 2298, 2300),
            (2296, 2300, 2292, 2298),
            (2299, 2324, 2297, 2322),
        ],
        PatternName.MORNING_STAR,
        Side.LONG,
    ),
    _scenario(
        "Evening star",
        "up",
        [
            (2470, 2512, 2468, 2510),
            (2512, 2516, 2504, 2508),
            (2506, 2508, 2478, 2480),
        ],
        PatternName.EVENING_STAR,
        Side.SHORT,
    ),
    _scenario(
        "Three white soldiers",
        "down",
        [
            (2308, 2327, 2306, 2326),
            (2318, 2339, 2316, 2338),
            (2330, 2351, 2328, 2350),
        ],
        PatternName.THREE_WHITE_SOLDIERS,
        Side.LONG,
    ),
    _scenario(
        "Three black crows",
        "up",
        [
            (2500, 2502, 2481, 2482),
            (2490, 2492, 2469, 2470),
            (2478, 2480, 2457, 2458),
        ],
        PatternName.THREE_BLACK_CROWS,
        Side.SHORT,
    ),
    _scenario(
        "Piercing line",
        "down",
        [(2340, 2342, 2298, 2300), (2299, 2330, 2290, 2328)],
        PatternName.PIERCING_LINE,
        Side.LONG,
    ),
    _scenario(
        "Dark cloud cover",
        "up",
        [(2470, 2502, 2468, 2500), (2502, 2510, 2476, 2478)],
        PatternName.DARK_CLOUD_COVER,
        Side.SHORT,
    ),
    _scenario(
        "Tweezer bottom",
        "down",
        [(2320, 2322, 2288, 2300), (2294, 2308, 2288, 2306)],
        PatternName.TWEEZER_BOTTOM,
        Side.LONG,
    ),
    _scenario(
        "Tweezer top",
        "up",
        [(2470, 2520, 2468, 2490), (2500, 2520, 2476, 2484)],
        PatternName.TWEEZER_TOP,
        Side.SHORT,
    ),
    _scenario(
        "Three inside up",
        "down",
        [
            (2340, 2342, 2296, 2300),
            (2310, 2324, 2308, 2320),
            (2322, 2348, 2320, 2346),
        ],
        PatternName.THREE_INSIDE_UP,
        Side.LONG,
    ),
    _scenario(
        "Three inside down",
        "up",
        [
            (2460, 2504, 2458, 2500),
            (2490, 2494, 2476, 2480),
            (2478, 2482, 2450, 2454),
        ],
        PatternName.THREE_INSIDE_DOWN,
        Side.SHORT,
    ),
    _scenario(
        "Inside bar in an uptrend",
        "up",
        [(2488, 2510, 2476, 2506), (2492, 2502, 2484, 2499)],
        PatternName.INSIDE_BAR,
        Side.LONG,
    ),
    _scenario(
        "Bullish kicker",
        "down",
        [(2320, 2322, 2298, 2300), (2324, 2342, 2323, 2340)],
        PatternName.BULLISH_KICKER,
        Side.LONG,
    ),
    _scenario(
        "Bearish kicker",
        "up",
        [(2480, 2508, 2478, 2505), (2470, 2476, 2452, 2455)],
        PatternName.BEARISH_KICKER,
        Side.SHORT,
    ),
    _scenario(
        "Bullish harami",
        "down",
        [(2340, 2344, 2296, 2300), (2312, 2332, 2308, 2328)],
        PatternName.BULLISH_HARAMI,
        Side.LONG,
    ),
    _scenario(
        "Rising three methods",
        "down",
        [
            (2300, 2362, 2298, 2360),
            (2350, 2352, 2320, 2330),
            (2332, 2336, 2310, 2318),
            (2330, 2334, 2316, 2322),
            (2332, 2374, 2330, 2372),
        ],
        PatternName.RISING_THREE_METHODS,
        Side.LONG,
    ),
    _scenario(
        "Falling three methods",
        "up",
        [
            (2520, 2522, 2458, 2460),
            (2470, 2494, 2468, 2490),
            (2488, 2504, 2484, 2500),
            (2496, 2500, 2480, 2484),
            (2482, 2484, 2446, 2448),
        ],
        PatternName.FALLING_THREE_METHODS,
        Side.SHORT,
    ),
    _scenario(
        "Morning doji star",
        "down",
        [
            (2330, 2332, 2298, 2300),
            (2297, 2299, 2293, 2297.2),
            (2299, 2324, 2297, 2322),
        ],
        PatternName.MORNING_DOJI_STAR,
        Side.LONG,
    ),
    _scenario(
        "Evening doji star",
        "up",
        [
            (2470, 2512, 2468, 2510),
            (2511, 2514, 2508, 2511.2),
            (2509, 2510, 2478, 2480),
        ],
        PatternName.EVENING_DOJI_STAR,
        Side.SHORT,
    ),
    _scenario(
        "Bullish harami cross",
        "down",
        [(2340, 2344, 2296, 2300), (2316, 2322, 2310, 2316.3)],
        PatternName.BULLISH_HARAMI_CROSS,
        Side.LONG,
    ),
    _scenario(
        "Bearish harami",
        "up",
        [(2460, 2504, 2458, 2500), (2488, 2496, 2478, 2484)],
        PatternName.BEARISH_HARAMI,
        Side.SHORT,
    ),
    _scenario(
        "Dragonfly doji after a decline",
        "down",
        [(2310.4, 2310.8, 2284, 2310)],
        PatternName.DRAGONFLY_DOJI,
        Side.LONG,
    ),
    _scenario(
        "Gravestone doji after a rally",
        "up",
        [(2490, 2520, 2489.6, 2490.3)],
        PatternName.GRAVESTONE_DOJI,
        Side.SHORT,
    ),
)
