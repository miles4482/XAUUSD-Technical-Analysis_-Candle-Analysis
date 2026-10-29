# XAUUSD candle analysis

This section reads gold candles on any timeframe and answers three questions.

1. What type of candle is this, and what does that type mean?
2. When does a group of candles turn bullish or bearish?
3. Where is the trade, if the candles offer one?

Color and bias are different things. Color is the close versus the open. Bias is the reading of the shape. A gravestone doji can close one tick up and still lean bearish, because the upper wick was rejected. A hammer and a hanging man are the same shape. After a decline the shape is a bullish hammer. After a rally it is a bearish hanging man.

## How to read one candle

A candle has four prices: open, high, low, close.

- The **body** is the distance from open to close. It shows who won the candle.
- The **upper wick** is the high that was rejected before the close.
- The **lower wick** is the low that was rejected before the close.
- A **bullish** color means close above open. A **bearish** color means close below open. Equal prices are neutral.
- A **doji** or **spinning top** is indecision. The next candles give it a direction.
- A **marubozu** is a body with almost no wick. One side controlled the whole candle.
- A **pin bar** (hammer, hanging man, shooting star, inverted hammer, dragonfly, gravestone) is a rejection. One wick is most of the range.

Run `python -m xau_candles --glossary` for every type and every group, with the meaning of each.

## How a group becomes a trade

One candle is a clue. Two or three candles are a story.

A bullish engulfing is the clearest example. A bearish candle runs from 2320 down to 2300. The next candle opens at 2296 and closes at 2324. The second body covers the whole first body. Separately, the first candle is bearish and the second is bullish. Together, buyers took back the entire decline. That group is bullish.

The plan from that close:

- Side: long
- Entry: the signal close (2324 in the example)
- Stop: beyond the lowest wick of the group. If that wick is closer than half an ATR, the stop is pushed out to half an ATR so a normal gold wick does not take it
- Targets: 1R and 2R, measured from that risk
- A stricter trigger is a break of the signal high, for traders who want extra confirmation

An inside bar is different. The candle has no direction of its own. In an uptrend the plan arms a buy at the mother candle's high, with the stop under the mother candle's low. Nothing is filled until that break.

The engine looks back two closed candles. If a later candle trades the stop, the plan is retired. If price has not touched the stop, the plan is still valid.

## Timeframes

The default live read is 15m, 1h, 4h, and 1d. Aliases such as `M15`, `H1`, `H4`, and `D1` work too.

The trend on each timeframe is the 8 and 21 simple moving averages of the closes **before** the signal candle. It describes the swing the candle was born into. It lags a fresh turn. The candle group is what catches the turn.

Grades use the next higher timeframe:

- **A** — the side agrees with the higher timeframe, or the group is strong on its own
- **B** — a valid setup that does not earn A. A hammer with no higher timeframe is a B
- **C** — the side fights the higher timeframe. It is the countertrend read

A daily uptrend and a 1h bullish engulfing after a dip is the A long. The same engulfing against a daily downtrend is a C long.

4h candles are built from 1h bars on UTC boundaries: 00:00, 04:00, 08:00, 12:00, 16:00, and 20:00 UTC. In Asia/Dhaka (UTC+6) those buckets open at 06:00, 10:00, 14:00, 18:00, 22:00, and 02:00.

## Run

```bash
python -m xau_candles --demo
python -m xau_candles --glossary
python -m xau_candles --timeframes M15,H1,H4,D1
python -m xau_candles --csv candles.csv --timeframe 1h
python -m xau_candles --json
```

Live data uses Yahoo Finance symbol `GC=F` (COMEX gold futures). The candle shapes track spot XAUUSD. The price level can differ by the futures basis. Install the optional feed with:

```bash
pip install -r requirements.txt
```

CSV columns are `time,open,high,low,close` and an optional `volume`. A time with no timezone is read as UTC. The report prints times in Asia/Dhaka.

The candle engine itself uses only the Python standard library.

```bash
python -m unittest discover -s tests
```

## What this is

An educational read of candle structure. It is not an order to buy or sell. Gold gaps most often on the Sunday reopen, and a stop beyond a wick can still be skipped on a fast bar.
