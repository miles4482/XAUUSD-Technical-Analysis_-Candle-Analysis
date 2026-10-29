"""Thresholds shared by the candle reader and the group scanner.

Gold trades nearly 24 hours, so two-candle reversals such as the piercing
line do not require a gap. A true gap is still required for a kicker, which
on gold usually means the Sunday reopen.
"""

from __future__ import annotations

DOJI_BODY_RATIO = 0.10
MARUBOZU_BODY_RATIO = 0.90
PIN_WICK_RATIO = 0.60
PIN_MAX_OTHER_WICK = 0.15
PIN_MAX_BODY = 0.35
SPINNING_MAX_BODY = 0.30
SPINNING_MIN_WICK = 0.25
BELT_MIN_BODY = 0.60
BELT_MAX_OPEN_WICK = 0.05
LONG_BODY_VS_AVG = 1.5
LONG_MIN_BODY_RATIO = 0.55
STAR_MIN_FIRST_BODY = 0.50
STAR_MAX_MIDDLE_BODY_RATIO = 0.35
STAR_MAX_MIDDLE_VS_FIRST = 0.50
HARAMI_MIN_PRIOR_BODY = 0.45
SOLDIER_MIN_BODY = 0.50
SOLDIER_MAX_WICK_VS_BODY = 0.35
TWEEZER_MIN_WICK = 0.30
AVG_LOOKBACK = 14
FAST_SMA = 8
SLOW_SMA = 21
ATR_PERIOD = 14
STOP_ATR_BUFFER = 0.05
MIN_RISK_ATR = 0.50
MIN_TRADE_QUALITY = 0.55
HTF_AGREE_GRADE_A = 0.64
SOLO_GROUP_GRADE_A = 0.75
ACTIVE_LOOKBACK = 2

TF_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
    "1w": 604800,
}

TF_ALIASES: dict[str, str] = {
    "m1": "1m",
    "1m": "1m",
    "m5": "5m",
    "5m": "5m",
    "m15": "15m",
    "15m": "15m",
    "m30": "30m",
    "30m": "30m",
    "h1": "1h",
    "1h": "1h",
    "60m": "1h",
    "h4": "4h",
    "4h": "4h",
    "240m": "4h",
    "d": "1d",
    "d1": "1d",
    "1d": "1d",
    "daily": "1d",
    "w": "1w",
    "w1": "1w",
    "1w": "1w",
    "weekly": "1w",
}


def normalize_timeframe(value: str) -> str:
    key = value.strip().lower()
    if key not in TF_ALIASES:
        known = ", ".join(sorted(set(TF_ALIASES.values())))
        raise ValueError(f"Unknown timeframe {value!r}. Use one of: {known}")
    return TF_ALIASES[key]
