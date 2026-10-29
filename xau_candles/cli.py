"""Command line for the gold candle section."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from xau_candles.analyze import analyze, analyze_many
from xau_candles.classify import classify_candle
from xau_candles.constants import normalize_timeframe
from xau_candles.data import MarketDataError, load_csv, load_timeframes
from xau_candles.demo import GALLERY, SCENARIOS
from xau_candles.models import MultiTimeframeAnalysis
from xau_candles.report import (
    analysis_to_dict,
    ascii_candle,
    render_analysis,
    render_glossary,
    render_timeframe,
)


def _demo_text(lookback: int, last: int) -> str:
    lines = [
        "XAUUSD candle section — textbook scenarios",
        "These prices are teaching examples around a gold-like level. They show how to read a candle,",
        "how a group becomes bullish or bearish, and the plan that follows.",
        "",
        "Color is close versus open. Bias is what the candle type means.",
        "A dragonfly doji can close red and still lean bullish. A hanging man can close green and lean bearish.",
        "",
        "Single candles",
    ]
    for item in GALLERY:
        read = classify_candle(
            item.candle,
            trend=item.trend,
            average_body=item.average_body,
        )
        lines.append(
            f"{ascii_candle(read)}  {item.title:<22} color {read.direction.value:<8} "
            f"bias {read.bias.value:<12} {read.meaning}"
        )
    lines.extend(["", "Groups and the trade they offer", ""])
    for scenario in SCENARIOS:
        analysis = analyze(list(scenario.candles), "1h", lookback=lookback)
        lines.append(scenario.title)
        lines.append(render_timeframe(analysis, last=last))
        lines.append("")
    lines.append(
        "Educational read of candle structure. It is not an order to buy or sell."
    )
    return "\n".join(lines) + "\n"


def _live_source_note(symbol: str, timeframes: list[str]) -> str:
    labels = [normalize_timeframe(timeframe) for timeframe in timeframes]
    note = (
        f"Source: {symbol} via Yahoo Finance. "
        "GC=F is COMEX gold futures. Its candle shape tracks spot XAUUSD, and the price can differ by the futures basis."
    )
    if "4h" in labels:
        note += " 4h candles are grouped on UTC boundaries (00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC)."
    return note


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="xau_candles",
        description="Read gold candles on one or many timeframes and mark the trade the candles offer.",
    )
    parser.add_argument("--demo", action="store_true", help="Read textbook candles, with no market feed")
    parser.add_argument("--glossary", action="store_true", help="List every candle type and every group")
    parser.add_argument("--csv", help="Read OHLC from a CSV file")
    parser.add_argument("--timeframe", default="1h", help="Timeframe for --csv (default 1h)")
    parser.add_argument(
        "--timeframes",
        default="15m,1h,4h,1d",
        help="Comma-separated timeframes for the live feed. Aliases: M15, H1, H4, D1",
    )
    parser.add_argument("--symbol", default="GC=F", help="Yahoo symbol, default GC=F")
    parser.add_argument("--last", type=int, default=8, help="How many recent candles to print")
    parser.add_argument(
        "--lookback",
        type=int,
        default=2,
        help="How many closed candles back an unfilled setup can still be active",
    )
    parser.add_argument("--json", action="store_true", help="Print the read as JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.glossary:
        sys.stdout.write(render_glossary())
        return 0
    if args.demo:
        sys.stdout.write(_demo_text(lookback=0, last=min(args.last, 5)))
        return 0
    try:
        if args.csv:
            candles = load_csv(args.csv)
            analysis = analyze_many(
                {args.timeframe: candles},
                symbol=args.csv,
                source_note=f"Source: {args.csv}",
                lookback=args.lookback,
            )
        else:
            labels = [part.strip() for part in args.timeframes.split(",") if part.strip()]
            series = load_timeframes(args.symbol, labels)
            analysis = analyze_many(
                series,
                symbol=args.symbol,
                source_note=_live_source_note(args.symbol, labels),
                lookback=args.lookback,
            )
    except MarketDataError as exc:
        sys.stderr.write(f"{exc}\n")
        sys.stderr.write("Run with --demo to read the candle catalog, or pass --csv.\n")
        return 1
    return _emit(analysis, as_json=args.json, last=args.last)


def _emit(analysis: MultiTimeframeAnalysis, *, as_json: bool, last: int) -> int:
    if as_json:
        payload = analysis_to_dict(analysis, last=last)
        payload["generated_at"] = datetime.now(timezone.utc).isoformat()
        sys.stdout.write(json.dumps(payload, indent=2) + "\n")
        return 0
    sys.stdout.write(render_analysis(analysis, last=last))
    return 0
