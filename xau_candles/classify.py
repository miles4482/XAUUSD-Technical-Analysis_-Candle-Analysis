"""Read one gold candle: color, type, bias, and what that type means."""

from __future__ import annotations

from xau_candles.constants import (
    BELT_MAX_OPEN_WICK,
    BELT_MIN_BODY,
    DOJI_BODY_RATIO,
    LONG_BODY_VS_AVG,
    LONG_MIN_BODY_RATIO,
    MARUBOZU_BODY_RATIO,
    PIN_MAX_BODY,
    PIN_MAX_OTHER_WICK,
    PIN_WICK_RATIO,
    SPINNING_MAX_BODY,
    SPINNING_MIN_WICK,
)
from xau_candles.metrics import Metrics, measure
from xau_candles.models import Bias, Candle, CandleRead, CandleType, Direction, Trend

CANDLE_MEANINGS: dict[CandleType, str] = {
    CandleType.FLAT: (
        "High and low are equal, so this candle has no range. It carries no directional information."
    ),
    CandleType.BULLISH: (
        "Close is above the open, so buyers won the candle. The body is how far they pushed, "
        "and the wicks are prices that were rejected before the close."
    ),
    CandleType.BEARISH: (
        "Close is below the open, so sellers won the candle. A close near the low means they "
        "kept control into the end of the bar."
    ),
    CandleType.LONG_BULLISH: (
        "A bullish candle with a body that is large versus recent candles. Buyers expanded the "
        "range and closed with momentum."
    ),
    CandleType.LONG_BEARISH: (
        "A bearish candle with a body that is large versus recent candles. Sellers expanded the "
        "range and closed with momentum."
    ),
    CandleType.BULLISH_MARUBOZU: (
        "Almost the entire range is a bullish body, with little or no wick. Buyers controlled "
        "the candle from open to close."
    ),
    CandleType.BEARISH_MARUBOZU: (
        "Almost the entire range is a bearish body, with little or no wick. Sellers controlled "
        "the candle from open to close."
    ),
    CandleType.DOJI: (
        "Open and close are nearly the same. Buyers and sellers finished in balance, so this "
        "candle has no winner. It is a pause, and the candles after it give it meaning."
    ),
    CandleType.DRAGONFLY_DOJI: (
        "Open and close sit near the high after a long lower wick. Sellers drove price down and "
        "buyers took the loss back by the close. The lean is bullish, and it is stronger after a decline."
    ),
    CandleType.GRAVESTONE_DOJI: (
        "Open and close sit near the low after a long upper wick. Buyers drove price up and sellers "
        "took the rally back. The lean is bearish, and it is stronger after a rally."
    ),
    CandleType.LONG_LEGGED_DOJI: (
        "A very small body with long wicks on both sides. Price explored higher and lower and "
        "closed back in the middle. This is indecision with a wide range."
    ),
    CandleType.HAMMER: (
        "A small body near the high and a long lower wick, after a decline. Sellers pushed the "
        "candle down and failed to hold it there. The reading is a bullish rejection. A later "
        "candle that holds above this low confirms it."
    ),
    CandleType.HANGING_MAN: (
        "The same shape as a hammer, a small body near the high and a long lower wick, printed "
        "after a rally. The lower wick shows selling appeared into strength. The lean is bearish, "
        "and it wants a later close under this body."
    ),
    CandleType.INVERTED_HAMMER: (
        "A small body near the low and a long upper wick, after a decline. Buyers tried to lift "
        "price and the close gave much of that lift back. It is only a possible bullish reversal "
        "until a later bullish candle confirms it."
    ),
    CandleType.SHOOTING_STAR: (
        "A small body near the low and a long upper wick, after a rally. Buyers pushed up and "
        "sellers rejected that high. The reading is bearish. A later candle that holds under "
        "this high confirms it."
    ),
    CandleType.BULLISH_PIN_BAR: (
        "A long lower wick and a small body near the high. The shape rejects lower prices and "
        "leans bullish. The swing into it is not a clear trend, so this is the hammer shape "
        "without hammer context."
    ),
    CandleType.BEARISH_PIN_BAR: (
        "A long upper wick and a small body near the low. The shape rejects higher prices and "
        "leans bearish. The swing into it is not a clear trend, so this is the shooting-star "
        "shape without shooting-star context."
    ),
    CandleType.BULLISH_SPINNING_TOP: (
        "A small bullish body with wicks on both sides. The close is only slightly above the "
        "open, so the bullish color is weak. The candle is indecision."
    ),
    CandleType.BEARISH_SPINNING_TOP: (
        "A small bearish body with wicks on both sides. The close is only slightly below the "
        "open, so the bearish color is weak. The candle is indecision."
    ),
    CandleType.BULLISH_BELT_HOLD: (
        "The candle opens at the low and closes well above it, with almost no lower wick. "
        "Buyers took control from the open."
    ),
    CandleType.BEARISH_BELT_HOLD: (
        "The candle opens at the high and closes well below it, with almost no upper wick. "
        "Sellers took control from the open."
    ),
}

CANDLE_BIAS: dict[CandleType, Bias] = {
    CandleType.FLAT: Bias.INDECISION,
    CandleType.BULLISH: Bias.BULLISH,
    CandleType.BEARISH: Bias.BEARISH,
    CandleType.LONG_BULLISH: Bias.BULLISH,
    CandleType.LONG_BEARISH: Bias.BEARISH,
    CandleType.BULLISH_MARUBOZU: Bias.BULLISH,
    CandleType.BEARISH_MARUBOZU: Bias.BEARISH,
    CandleType.DOJI: Bias.INDECISION,
    CandleType.DRAGONFLY_DOJI: Bias.BULLISH,
    CandleType.GRAVESTONE_DOJI: Bias.BEARISH,
    CandleType.LONG_LEGGED_DOJI: Bias.INDECISION,
    CandleType.HAMMER: Bias.BULLISH,
    CandleType.HANGING_MAN: Bias.BEARISH,
    CandleType.INVERTED_HAMMER: Bias.BULLISH,
    CandleType.SHOOTING_STAR: Bias.BEARISH,
    CandleType.BULLISH_PIN_BAR: Bias.BULLISH,
    CandleType.BEARISH_PIN_BAR: Bias.BEARISH,
    CandleType.BULLISH_SPINNING_TOP: Bias.INDECISION,
    CandleType.BEARISH_SPINNING_TOP: Bias.INDECISION,
    CandleType.BULLISH_BELT_HOLD: Bias.BULLISH,
    CandleType.BEARISH_BELT_HOLD: Bias.BEARISH,
}


def direction_of(candle: Candle) -> Direction:
    if candle.close > candle.open:
        return Direction.BULLISH
    if candle.close < candle.open:
        return Direction.BEARISH
    return Direction.NEUTRAL


def _lower_rejection(metrics: Metrics) -> bool:
    if metrics.range <= 0:
        return False
    long_tail = metrics.lower_wick >= 2 * metrics.body
    return (
        long_tail
        and metrics.lower_ratio >= PIN_WICK_RATIO
        and metrics.upper_ratio <= PIN_MAX_OTHER_WICK
        and metrics.body_ratio <= PIN_MAX_BODY
    )


def _upper_rejection(metrics: Metrics) -> bool:
    if metrics.range <= 0:
        return False
    long_tail = metrics.upper_wick >= 2 * metrics.body
    return (
        long_tail
        and metrics.upper_ratio >= PIN_WICK_RATIO
        and metrics.lower_ratio <= PIN_MAX_OTHER_WICK
        and metrics.body_ratio <= PIN_MAX_BODY
    )


def _tags(metrics: Metrics, average_range: float) -> tuple[str, ...]:
    tags: list[str] = []
    if metrics.range > 0 and metrics.upper_ratio <= 0.05:
        tags.append("shaven_head")
    if metrics.range > 0 and metrics.lower_ratio <= 0.05:
        tags.append("shaven_bottom")
    if average_range > 0 and metrics.range >= 1.5 * average_range:
        tags.append("wide_range")
    if average_range > 0 and metrics.range <= 0.5 * average_range:
        tags.append("narrow_range")
    return tuple(tags)


def classify_candle(
    candle: Candle,
    *,
    index: int = 0,
    trend: Trend = Trend.UNKNOWN,
    average_body: float = 0.0,
    average_range: float = 0.0,
) -> CandleRead:
    """Name the candle and separate its color from the bias of that name.

    A gravestone doji can close a tick above the open (bullish color) while the
    long upper wick still leans bearish. Hammer and hanging man share a shape;
    the trend into the candle decides which name applies.
    """

    metrics = measure(candle)
    direction = direction_of(candle)
    bullish = direction is Direction.BULLISH
    bearish = direction is Direction.BEARISH

    if metrics.range <= 0:
        kind = CandleType.FLAT
    elif metrics.body_ratio >= MARUBOZU_BODY_RATIO and bullish:
        kind = CandleType.BULLISH_MARUBOZU
    elif metrics.body_ratio >= MARUBOZU_BODY_RATIO and bearish:
        kind = CandleType.BEARISH_MARUBOZU
    elif _lower_rejection(metrics):
        if metrics.body_ratio <= DOJI_BODY_RATIO:
            kind = CandleType.DRAGONFLY_DOJI
        elif trend is Trend.DOWN:
            kind = CandleType.HAMMER
        elif trend is Trend.UP:
            kind = CandleType.HANGING_MAN
        else:
            kind = CandleType.BULLISH_PIN_BAR
    elif _upper_rejection(metrics):
        if metrics.body_ratio <= DOJI_BODY_RATIO:
            kind = CandleType.GRAVESTONE_DOJI
        elif trend is Trend.UP:
            kind = CandleType.SHOOTING_STAR
        elif trend is Trend.DOWN:
            kind = CandleType.INVERTED_HAMMER
        else:
            kind = CandleType.BEARISH_PIN_BAR
    elif metrics.body_ratio <= DOJI_BODY_RATIO:
        if metrics.upper_ratio >= 0.30 and metrics.lower_ratio >= 0.30:
            kind = CandleType.LONG_LEGGED_DOJI
        else:
            kind = CandleType.DOJI
    elif (
        metrics.body_ratio <= SPINNING_MAX_BODY
        and metrics.upper_ratio >= SPINNING_MIN_WICK
        and metrics.lower_ratio >= SPINNING_MIN_WICK
    ):
        kind = CandleType.BULLISH_SPINNING_TOP if bullish else CandleType.BEARISH_SPINNING_TOP
    elif (
        bullish
        and metrics.lower_ratio <= BELT_MAX_OPEN_WICK
        and metrics.body_ratio >= BELT_MIN_BODY
    ):
        kind = CandleType.BULLISH_BELT_HOLD
    elif (
        bearish
        and metrics.upper_ratio <= BELT_MAX_OPEN_WICK
        and metrics.body_ratio >= BELT_MIN_BODY
    ):
        kind = CandleType.BEARISH_BELT_HOLD
    elif (
        average_body > 0
        and metrics.body >= LONG_BODY_VS_AVG * average_body
        and metrics.body_ratio >= LONG_MIN_BODY_RATIO
    ):
        kind = CandleType.LONG_BULLISH if bullish else CandleType.LONG_BEARISH
    elif bullish:
        kind = CandleType.BULLISH
    elif bearish:
        kind = CandleType.BEARISH
    else:
        kind = CandleType.DOJI

    return CandleRead(
        index=index,
        time=candle.time,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        direction=direction,
        bias=CANDLE_BIAS[kind],
        candle_type=kind,
        body_ratio=metrics.body_ratio,
        upper_wick_ratio=metrics.upper_ratio,
        lower_wick_ratio=metrics.lower_ratio,
        meaning=CANDLE_MEANINGS[kind],
        tags=_tags(metrics, average_range),
    )
