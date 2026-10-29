"""Load gold candles from CSV or from Yahoo Finance, and build 4h bars."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from xau_candles.constants import TF_SECONDS, normalize_timeframe
from xau_candles.models import Candle

# Yahoo interval and period for each analysis timeframe.
# 4h is built by grouping 1h bars on UTC boundaries.
YAHOO_REQUESTS: dict[str, tuple[str, str]] = {
    "1m": ("1m", "1d"),
    "5m": ("5m", "5d"),
    "15m": ("15m", "60d"),
    "30m": ("30m", "60d"),
    "1h": ("1h", "180d"),
    "1d": ("1d", "5y"),
    "1w": ("1wk", "10y"),
}


class MarketDataError(RuntimeError):
    """The candle file or the live feed could not be read."""


def make_candle(
    moment: datetime,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: float = 0.0,
) -> Candle | None:
    """Build a candle, repairing a high/low that does not contain the open and close."""

    values = (open_, high, low, close)
    if any(value is None or value != value for value in values):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    safe_volume = 0.0 if volume is None or volume != volume or volume < 0 else float(volume)
    return Candle(
        time=moment,
        open=float(open_),
        high=max(values),
        low=min(values),
        close=float(close),
        volume=safe_volume,
    )


def parse_time(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    moment = datetime.fromisoformat(text)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment


def load_csv(path: str | Path) -> list[Candle]:
    """Read time,open,high,low,close[,volume]. Times without a zone are treated as UTC."""

    file_path = Path(path)
    if not file_path.is_file():
        raise MarketDataError(f"CSV not found: {file_path}")
    with file_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise MarketDataError("CSV has no header row")
        fields = {name.strip().lower(): name for name in reader.fieldnames}

        def column(*options: str) -> str:
            for option in options:
                if option in fields:
                    return fields[option]
            joined = ", ".join(options)
            raise MarketDataError(f"CSV is missing a column. Expected one of: {joined}")

        time_key = column("time", "timestamp", "date", "datetime")
        open_key = column("open")
        high_key = column("high")
        low_key = column("low")
        close_key = column("close")
        volume_key = fields.get("volume")
        candles: list[Candle] = []
        for row_number, row in enumerate(reader, start=2):
            try:
                moment = parse_time(row[time_key])
                volume = float(row[volume_key]) if volume_key and row[volume_key] else 0.0
                candle = make_candle(
                    moment,
                    float(row[open_key]),
                    float(row[high_key]),
                    float(row[low_key]),
                    float(row[close_key]),
                    volume,
                )
            except (TypeError, ValueError) as exc:
                raise MarketDataError(f"CSV row {row_number} could not be read") from exc
            if candle is not None:
                candles.append(candle)
    if not candles:
        raise MarketDataError("CSV has no candles")
    candles.sort(key=lambda candle: candle.time)
    return candles


def resample(candles: list[Candle], timeframe: str, *, now: datetime | None = None) -> list[Candle]:
    """Group candles into a higher timeframe. The current unfinished bucket is dropped.

    4h buckets are aligned to UTC: 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00.
    """

    label = normalize_timeframe(timeframe)
    seconds = TF_SECONDS[label]
    clock = now or datetime.now(timezone.utc)
    if clock.tzinfo is None:
        clock = clock.replace(tzinfo=timezone.utc)
    now_ts = clock.timestamp()
    buckets: dict[int, list[Candle]] = {}
    for candle in candles:
        moment = candle.time if candle.time.tzinfo else candle.time.replace(tzinfo=timezone.utc)
        epoch = int(moment.timestamp())
        key = epoch - (epoch % seconds)
        buckets.setdefault(key, []).append(candle)
    grouped: list[Candle] = []
    for key in sorted(buckets):
        if key + seconds > now_ts:
            continue
        group = buckets[key]
        grouped.append(
            Candle(
                time=datetime.fromtimestamp(key, tz=timezone.utc),
                open=group[0].open,
                high=max(candle.high for candle in group),
                low=min(candle.low for candle in group),
                close=group[-1].close,
                volume=sum(candle.volume for candle in group),
            )
        )
    return grouped


def _flatten_columns(frame):
    columns = frame.columns
    if getattr(columns, "nlevels", 1) > 1:
        level0 = [str(value).lower() for value in columns.get_level_values(0)]
        if "open" in level0:
            frame = frame.copy()
            frame.columns = [str(value) for value in columns.get_level_values(0)]
        else:
            frame = frame.copy()
            frame.columns = [str(value) for value in columns.get_level_values(-1)]
    return frame.rename(columns=lambda name: str(name).strip().lower())


def fetch_yahoo(symbol: str, interval: str, period: str) -> list[Candle]:
    """Download OHLC from Yahoo Finance. Requires the optional yfinance package."""

    try:
        import yfinance as yf
    except ImportError as exc:
        raise MarketDataError(
            "yfinance is not installed. Run `pip install -r requirements.txt`, "
            "or use --demo / --csv."
        ) from exc
    import warnings

    warnings.filterwarnings("ignore", module="yfinance")
    frame = yf.download(
        symbol,
        interval=interval,
        period=period,
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if frame is None or frame.empty:
        raise MarketDataError(f"No candles returned for {symbol} {interval} {period}")
    frame = _flatten_columns(frame)
    for required in ("open", "high", "low", "close"):
        if required not in frame.columns:
            raise MarketDataError(f"Yahoo data for {symbol} has no {required} column")
    index = frame.index
    aware = getattr(index, "tz", None) is not None
    candles: list[Candle] = []
    for stamp, row in frame.iterrows():
        moment = stamp.to_pydatetime()
        if aware:
            moment = moment.astimezone(timezone.utc)
        elif moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        volume = row["volume"] if "volume" in frame.columns else 0.0
        try:
            candle = make_candle(
                moment,
                float(row["open"]),
                float(row["high"]),
                float(row["low"]),
                float(row["close"]),
                float(volume) if volume == volume else 0.0,
            )
        except (TypeError, ValueError):
            continue
        if candle is not None:
            candles.append(candle)
    if not candles:
        raise MarketDataError(f"Yahoo data for {symbol} had no usable OHLC rows")
    candles.sort(key=lambda candle: candle.time)
    deduped: dict[datetime, Candle] = {}
    for candle in candles:
        deduped[candle.time] = candle
    return [deduped[key] for key in sorted(deduped)]


def load_timeframes(symbol: str, timeframes: list[str]) -> dict[str, list[Candle]]:
    """Fetch each timeframe. 4h is resampled from 1h so the buckets stay explicit."""

    labels = [normalize_timeframe(timeframe) for timeframe in timeframes]
    jobs: dict[str, tuple[str, str]] = {}
    for label in labels:
        if label == "4h":
            jobs.setdefault("1h", YAHOO_REQUESTS["1h"])
        else:
            jobs[label] = YAHOO_REQUESTS[label]
    fetched = {label: fetch_yahoo(symbol, interval, period) for label, (interval, period) in jobs.items()}
    series: dict[str, list[Candle]] = {}
    for label in labels:
        if label == "4h":
            series["4h"] = resample(fetched["1h"], "4h")
        else:
            series[label] = fetched[label]
        if not series[label]:
            raise MarketDataError(f"No candles left for {label}")
    return series
