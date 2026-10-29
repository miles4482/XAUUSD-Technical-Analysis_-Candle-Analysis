"""Shared types for gold candle reads, groups, and trade setups."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Direction(str, Enum):
    """Which side won the candle: close versus open."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Bias(str, Enum):
    """What the candle or group leans toward, which can differ from its color."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    INDECISION = "indecision"


class Trend(str, Enum):
    """Swing state from the 8 and 21 simple moving averages into a candle."""

    UP = "up"
    DOWN = "down"
    RANGE = "range"
    UNKNOWN = "unknown"


class CandleType(str, Enum):
    FLAT = "flat"
    BULLISH = "bullish"
    BEARISH = "bearish"
    LONG_BULLISH = "long_bullish"
    LONG_BEARISH = "long_bearish"
    BULLISH_MARUBOZU = "bullish_marubozu"
    BEARISH_MARUBOZU = "bearish_marubozu"
    DOJI = "doji"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    LONG_LEGGED_DOJI = "long_legged_doji"
    HAMMER = "hammer"
    HANGING_MAN = "hanging_man"
    INVERTED_HAMMER = "inverted_hammer"
    SHOOTING_STAR = "shooting_star"
    BULLISH_PIN_BAR = "bullish_pin_bar"
    BEARISH_PIN_BAR = "bearish_pin_bar"
    BULLISH_SPINNING_TOP = "bullish_spinning_top"
    BEARISH_SPINNING_TOP = "bearish_spinning_top"
    BULLISH_BELT_HOLD = "bullish_belt_hold"
    BEARISH_BELT_HOLD = "bearish_belt_hold"


class PatternName(str, Enum):
    BULLISH_ENGULFING = "bullish_engulfing"
    BEARISH_ENGULFING = "bearish_engulfing"
    BULLISH_HARAMI = "bullish_harami"
    BEARISH_HARAMI = "bearish_harami"
    BULLISH_HARAMI_CROSS = "bullish_harami_cross"
    BEARISH_HARAMI_CROSS = "bearish_harami_cross"
    PIERCING_LINE = "piercing_line"
    DARK_CLOUD_COVER = "dark_cloud_cover"
    TWEEZER_BOTTOM = "tweezer_bottom"
    TWEEZER_TOP = "tweezer_top"
    MORNING_STAR = "morning_star"
    EVENING_STAR = "evening_star"
    MORNING_DOJI_STAR = "morning_doji_star"
    EVENING_DOJI_STAR = "evening_doji_star"
    THREE_WHITE_SOLDIERS = "three_white_soldiers"
    THREE_BLACK_CROWS = "three_black_crows"
    THREE_INSIDE_UP = "three_inside_up"
    THREE_INSIDE_DOWN = "three_inside_down"
    RISING_THREE_METHODS = "rising_three_methods"
    FALLING_THREE_METHODS = "falling_three_methods"
    INSIDE_BAR = "inside_bar"
    BULLISH_OUTSIDE_BAR = "bullish_outside_bar"
    BEARISH_OUTSIDE_BAR = "bearish_outside_bar"
    BULLISH_KICKER = "bullish_kicker"
    BEARISH_KICKER = "bearish_kicker"
    HAMMER = "hammer"
    HANGING_MAN = "hanging_man"
    INVERTED_HAMMER = "inverted_hammer"
    SHOOTING_STAR = "shooting_star"
    DRAGONFLY_DOJI = "dragonfly_doji"
    GRAVESTONE_DOJI = "gravestone_doji"
    BULLISH_PIN_BAR = "bullish_pin_bar"
    BEARISH_PIN_BAR = "bearish_pin_bar"


class Grade(str, Enum):
    A = "A"
    B = "B"
    C = "C"


class SetupStatus(str, Enum):
    """Where the setup stands on the last closed candle."""

    SIGNAL_CLOSED = "signal_closed"
    STILL_VALID = "still_valid"
    ARMED = "armed"
    TRIGGERED = "triggered"
    WATCH = "watch"


class Side(str, Enum):
    LONG = "long"
    SHORT = "short"


@dataclass(frozen=True)
class Candle:
    """One OHLC bar. High and low must contain the open and the close."""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError("high is below low")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("open or close is outside the high-low range")
        if self.volume < 0:
            raise ValueError("volume is negative")


@dataclass(frozen=True)
class CandleRead:
    index: int
    time: datetime
    open: float
    high: float
    low: float
    close: float
    direction: Direction
    bias: Bias
    candle_type: CandleType
    body_ratio: float
    upper_wick_ratio: float
    lower_wick_ratio: float
    meaning: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class PatternSignal:
    name: PatternName
    bias: Bias
    start_index: int
    end_index: int
    quality: float
    candles_involved: int
    meaning: str


@dataclass(frozen=True)
class Opportunity:
    timeframe: str
    time: datetime
    side: Side | None
    pattern: PatternName
    also_matched: tuple[PatternName, ...]
    bias: Bias
    grade: Grade | None
    status: SetupStatus
    quality: float
    entry: float | None
    stop: float | None
    target_1r: float | None
    target_2r: float | None
    break_level: float | None
    risk: float | None
    candle_types: tuple[str, ...]
    rationale: str


@dataclass(frozen=True)
class SetupBoard:
    primary: Opportunity | None
    watches: tuple[Opportunity, ...]
    conflict_note: str | None = None


@dataclass(frozen=True)
class TimeframeAnalysis:
    timeframe: str
    trend: Trend
    htf_bias: Trend
    reads: tuple[CandleRead, ...]
    patterns: tuple[PatternSignal, ...]
    board: SetupBoard


@dataclass(frozen=True)
class MultiTimeframeAnalysis:
    """Higher timeframes are listed first."""

    order: tuple[str, ...]
    analyses: dict[str, TimeframeAnalysis]
    symbol: str = "XAUUSD"
    source_note: str = ""
