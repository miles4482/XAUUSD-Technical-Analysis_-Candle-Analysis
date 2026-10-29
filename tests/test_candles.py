"""Candle types, groups, and the trade plans they create."""

from __future__ import annotations

import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from io import StringIO
from pathlib import Path

from xau_candles.analyze import analyze, analyze_many
from xau_candles.classify import CANDLE_BIAS, CANDLE_MEANINGS, classify_candle
from xau_candles.cli import main
from xau_candles.constants import normalize_timeframe
from xau_candles.data import load_csv, resample
from xau_candles.demo import GALLERY, SCENARIOS, make_series
from xau_candles.models import Bias, Candle, CandleType, Direction, Grade, PatternName, SetupStatus, Side, Trend
from xau_candles.opportunities import grade_setup
from xau_candles.patterns import PATTERN_MEANINGS
from xau_candles.report import render_analysis, render_glossary


class ClassifyTests(unittest.TestCase):
    def test_gallery_names_every_shape(self) -> None:
        seen = set()
        for item in GALLERY:
            read = classify_candle(item.candle, trend=item.trend, average_body=item.average_body)
            self.assertEqual(read.candle_type, item.expected, item.title)
            self.assertEqual(read.bias, CANDLE_BIAS[item.expected])
            seen.add(item.expected)
        self.assertEqual(seen, set(CandleType))

    def test_same_shape_changes_name_with_the_trend(self) -> None:
        candle = GALLERY[0].candle
        hammer = next(item.candle for item in GALLERY if item.expected is CandleType.HAMMER)
        down = classify_candle(hammer, trend=Trend.DOWN)
        up = classify_candle(hammer, trend=Trend.UP)
        sideways = classify_candle(hammer, trend=Trend.RANGE)
        self.assertEqual(down.candle_type, CandleType.HAMMER)
        self.assertEqual(down.bias, Bias.BULLISH)
        self.assertEqual(up.candle_type, CandleType.HANGING_MAN)
        self.assertEqual(up.bias, Bias.BEARISH)
        self.assertEqual(sideways.candle_type, CandleType.BULLISH_PIN_BAR)
        self.assertIsNotNone(candle)

    def test_color_and_bias_can_disagree(self) -> None:
        gravestone = next(item for item in GALLERY if item.expected is CandleType.GRAVESTONE_DOJI)
        dragonfly = next(item for item in GALLERY if item.expected is CandleType.DRAGONFLY_DOJI)
        grave_read = classify_candle(gravestone.candle, trend=gravestone.trend)
        fly_read = classify_candle(dragonfly.candle, trend=dragonfly.trend)
        self.assertEqual(grave_read.direction, Direction.BULLISH)
        self.assertEqual(grave_read.bias, Bias.BEARISH)
        self.assertEqual(fly_read.direction, Direction.BEARISH)
        self.assertEqual(fly_read.bias, Bias.BULLISH)
        doji = classify_candle(
            next(item.candle for item in GALLERY if item.expected is CandleType.DOJI),
            trend=Trend.RANGE,
        )
        self.assertEqual(doji.direction, Direction.BULLISH)
        self.assertEqual(doji.bias, Bias.INDECISION)

    def test_every_type_and_group_has_a_meaning(self) -> None:
        for candle_type in CandleType:
            self.assertTrue(CANDLE_MEANINGS[candle_type].strip())
            self.assertIn(candle_type, CANDLE_BIAS)
        for name in PatternName:
            self.assertTrue(PATTERN_MEANINGS[name].strip())
        glossary = render_glossary()
        for candle_type in CandleType:
            self.assertIn(candle_type.value, glossary)
        for name in PatternName:
            self.assertIn(name.value, glossary)

    def test_candle_rejects_a_price_outside_the_range(self) -> None:
        with self.assertRaises(ValueError):
            Candle(datetime(2026, 1, 1, tzinfo=timezone.utc), 10, 9, 8, 11)


class ScenarioTests(unittest.TestCase):
    def test_each_group_offers_the_expected_side(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario.title):
                analysis = analyze(list(scenario.candles), "H1", lookback=0)
                primary = analysis.board.primary
                self.assertIsNotNone(primary, scenario.title)
                assert primary is not None
                self.assertEqual(primary.pattern, scenario.expected_pattern)
                self.assertEqual(primary.side, scenario.expected_side)
                self.assertGreaterEqual(primary.quality, 0.55)
                self._assert_levels(primary)

    def test_engulfing_is_a_grade_a_group_and_also_an_outside_bar(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_ENGULFING)
        analysis = analyze(list(scenario.candles), "1h", lookback=0)
        primary = analysis.board.primary
        assert primary is not None
        self.assertGreaterEqual(primary.quality, 0.85)
        self.assertEqual(primary.grade, Grade.A)
        self.assertIn(PatternName.BULLISH_OUTSIDE_BAR, primary.also_matched)
        self.assertEqual(primary.status, SetupStatus.SIGNAL_CLOSED)

    def test_hammer_grades_follow_the_higher_timeframe(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.HAMMER)
        candles = list(scenario.candles)
        alone = analyze(candles, "1h", lookback=0)
        with_trend = analyze(candles, "1h", htf_bias=Trend.UP, lookback=0)
        against = analyze(candles, "1h", htf_bias=Trend.DOWN, lookback=0)
        assert alone.board.primary and with_trend.board.primary and against.board.primary
        self.assertEqual(alone.board.primary.grade, Grade.B)
        self.assertEqual(with_trend.board.primary.grade, Grade.A)
        self.assertEqual(against.board.primary.grade, Grade.C)
        self.assertLess(alone.board.primary.stop, candles[-1].low)

    def test_bearish_engulfing_is_countertrend_when_the_daily_is_up(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BEARISH_ENGULFING)
        analysis = analyze(list(scenario.candles), "1h", htf_bias=Trend.UP, lookback=0)
        primary = analysis.board.primary
        assert primary is not None
        self.assertEqual(primary.side, Side.SHORT)
        self.assertEqual(primary.grade, Grade.C)

    def test_a_later_quiet_candle_keeps_the_plan_alive(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_ENGULFING)
        candles = list(scenario.candles)
        fresh = analyze(candles, "1h", lookback=0)
        assert fresh.board.primary is not None
        last = candles[-1]
        quiet = Candle(
            time=last.time + timedelta(hours=1),
            open=last.close,
            high=last.close + 1.0,
            low=last.close - 0.4,
            close=last.close + 0.5,
        )
        held = analyze(candles + [quiet], "1h", lookback=2)
        assert held.board.primary is not None
        self.assertEqual(held.board.primary.pattern, PatternName.BULLISH_ENGULFING)
        self.assertEqual(held.board.primary.status, SetupStatus.STILL_VALID)
        self.assertGreater(quiet.low, fresh.board.primary.stop)

    def test_a_deep_retrace_retires_the_plan(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_ENGULFING)
        candles = list(scenario.candles)
        fresh = analyze(candles, "1h", lookback=0)
        assert fresh.board.primary and fresh.board.primary.stop is not None
        entry = fresh.board.primary.entry
        stop = fresh.board.primary.stop
        assert entry is not None
        midpoint = (entry + stop) / 2
        close = (midpoint + stop) / 2
        last = candles[-1]
        retrace = Candle(
            time=last.time + timedelta(hours=1),
            open=midpoint,
            high=midpoint + 1,
            low=close - 1,
            close=close,
        )
        faded = analyze(candles + [retrace], "1h", lookback=2)
        primary = faded.board.primary
        self.assertTrue(primary is None or primary.pattern is not PatternName.BULLISH_ENGULFING)

    def test_a_tiny_wick_stop_is_pushed_out_to_half_an_atr(self) -> None:
        candles = make_series(
            "down",
            [(2312, 2330, 2305.5, 2306)],
            step=8,
        )
        analysis = analyze(candles, "1h", lookback=0)
        primary = analysis.board.primary
        assert primary is not None and primary.risk is not None and primary.stop is not None
        self.assertEqual(primary.pattern, PatternName.INVERTED_HAMMER)
        self.assertGreater(primary.risk, 4)
        self.assertLess(primary.stop, 2305.5)

    def test_a_pin_bar_does_not_count_as_engulfing(self) -> None:
        candles = make_series("down", [(2312, 2314, 2308, 2309), (2308.5, 2330, 2306, 2312)])
        analysis = analyze(candles, "1h", lookback=0)
        names = {pattern.name for pattern in analysis.patterns if pattern.end_index == len(candles) - 1}
        self.assertNotIn(PatternName.BULLISH_ENGULFING, names)
        primary = analysis.board.primary
        assert primary is not None
        self.assertEqual(primary.pattern, PatternName.INVERTED_HAMMER)

    def test_a_stop_trade_retires_the_plan(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_ENGULFING)
        candles = list(scenario.candles)
        fresh = analyze(candles, "1h", lookback=0)
        assert fresh.board.primary and fresh.board.primary.stop is not None
        last = candles[-1]
        stop = fresh.board.primary.stop
        pierced = Candle(
            time=last.time + timedelta(hours=1),
            open=last.close,
            high=last.close + 1,
            low=stop - 2,
            close=stop - 1,
        )
        retired = analyze(candles + [pierced], "1h", lookback=2)
        primary = retired.board.primary
        if primary is not None:
            self.assertNotEqual(primary.pattern, PatternName.BULLISH_ENGULFING)

    def test_inside_bar_arms_a_break_of_the_mother_candle(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.INSIDE_BAR)
        analysis = analyze(list(scenario.candles), "1h", lookback=0)
        primary = analysis.board.primary
        assert primary is not None
        mother = scenario.candles[-2]
        self.assertEqual(primary.status, SetupStatus.ARMED)
        self.assertEqual(primary.entry, mother.high)
        self.assertLess(primary.stop, mother.low)
        self.assertEqual(analysis.trend, Trend.UP)

    def test_plain_uptrend_has_no_trade(self) -> None:
        candles = make_series("up", [])
        analysis = analyze(candles, "1h", lookback=0)
        self.assertIsNone(analysis.board.primary)
        self.assertEqual(analysis.trend, Trend.UP)
        self.assertEqual(analysis.reads[-1].candle_type, CandleType.BULLISH)

    def test_harami_also_reports_the_inside_bar(self) -> None:
        scenario = next(item for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_HARAMI)
        analysis = analyze(list(scenario.candles), "1h", lookback=0)
        primary = analysis.board.primary
        assert primary is not None
        self.assertIn(PatternName.INSIDE_BAR, primary.also_matched)

    def test_higher_timeframe_trend_is_passed_down(self) -> None:
        daily = make_series("up", [])
        hourly = next(item.candles for item in SCENARIOS if item.expected_pattern is PatternName.BULLISH_ENGULFING)
        combined = analyze_many({"1d": daily, "H1": list(hourly)}, symbol="XAUUSD")
        self.assertEqual(combined.order, ("1d", "1h"))
        self.assertEqual(combined.analyses["1d"].trend, Trend.UP)
        self.assertEqual(combined.analyses["1h"].htf_bias, Trend.UP)
        primary = combined.analyses["1h"].board.primary
        assert primary is not None
        self.assertEqual(primary.grade, Grade.A)

    def test_empty_series(self) -> None:
        analysis = analyze([], "15m")
        self.assertEqual(analysis.trend, Trend.UNKNOWN)
        self.assertIsNone(analysis.board.primary)

    def _assert_levels(self, primary) -> None:
        assert primary.entry is not None and primary.stop is not None
        assert primary.target_1r is not None and primary.target_2r is not None
        if primary.side is Side.LONG:
            self.assertLess(primary.stop, primary.entry)
            self.assertGreater(primary.target_1r, primary.entry)
            self.assertGreater(primary.target_2r, primary.target_1r)
        else:
            self.assertGreater(primary.stop, primary.entry)
            self.assertLess(primary.target_1r, primary.entry)
            self.assertLess(primary.target_2r, primary.target_1r)
        risk = abs(primary.entry - primary.stop)
        self.assertAlmostEqual(primary.risk, risk)
        self.assertAlmostEqual(abs(primary.target_1r - primary.entry), risk)
        self.assertAlmostEqual(abs(primary.target_2r - primary.entry), risk * 2)


class GradeTests(unittest.TestCase):
    def test_named_grades(self) -> None:
        self.assertEqual(grade_setup(Side.LONG, 0.90, Trend.UP, 2), Grade.A)
        self.assertEqual(grade_setup(Side.LONG, 0.90, Trend.DOWN, 2), Grade.C)
        self.assertEqual(grade_setup(Side.LONG, 0.90, Trend.UNKNOWN, 2), Grade.A)
        self.assertEqual(grade_setup(Side.LONG, 0.70, Trend.UNKNOWN, 1), Grade.B)
        self.assertEqual(grade_setup(Side.SHORT, 0.58, Trend.DOWN, 2), Grade.B)


class DataAndReportTests(unittest.TestCase):
    def test_timeframe_aliases(self) -> None:
        self.assertEqual(normalize_timeframe("M15"), "15m")
        self.assertEqual(normalize_timeframe("H4"), "4h")
        self.assertEqual(normalize_timeframe("D1"), "1d")
        with self.assertRaises(ValueError):
            normalize_timeframe("2h")

    def test_resample_builds_a_utc_bucket_and_drops_the_open_one(self) -> None:
        start = datetime(2026, 1, 5, tzinfo=timezone.utc)
        epoch = int(start.timestamp())
        epoch -= epoch % 14400
        candles = []
        for step, close in enumerate((10, 12, 11, 14, 15)):
            open_ = 10 if step == 0 else candles[-1].close
            high = max(open_, close) + 1
            low = min(open_, close) - 1
            moment = datetime.fromtimestamp(epoch + step * 3600, tz=timezone.utc)
            candles.append(Candle(moment, open_, high, low, close))
        frozen_now = datetime.fromtimestamp(epoch + 5 * 3600, tz=timezone.utc)
        grouped = resample(candles, "4h", now=frozen_now)
        self.assertEqual(len(grouped), 1)
        self.assertEqual(grouped[0].open, 10)
        self.assertEqual(grouped[0].close, 14)
        self.assertEqual(grouped[0].high, 15)
        self.assertEqual(grouped[0].low, 9)
        self.assertEqual(grouped[0].time, datetime.fromtimestamp(epoch, tz=timezone.utc))

    def test_csv_round_trip(self) -> None:
        moment = datetime(2026, 10, 29, 18, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "gold.csv"
            path.write_text(
                "time,open,high,low,close,volume\n"
                "2026-10-29T18:00:00Z,2300,2310,2290,2305,12\n",
                encoding="utf-8",
            )
            candles = load_csv(path)
        self.assertEqual(len(candles), 1)
        self.assertEqual(candles[0].time, moment)
        self.assertEqual(candles[0].close, 2305)
        self.assertEqual(candles[0].volume, 12)

    def test_report_and_cli(self) -> None:
        scenario = SCENARIOS[0]
        combined = analyze_many({"1h": list(scenario.candles)}, symbol="XAUUSD", lookback=0)
        text = render_analysis(combined, last=3)
        self.assertIn("LONG", text)
        self.assertIn("bullish engulfing", text)
        self.assertIn("Asia/Dhaka", text)
        self.assertIn("stop", text)
        glossary = StringIO()
        with redirect_stdout(glossary):
            self.assertEqual(main(["--glossary"]), 0)
        self.assertIn("hammer", glossary.getvalue())
        with redirect_stdout(StringIO()):
            self.assertEqual(main(["--demo"]), 0)

    def test_pin_without_a_trend_stays_a_watch(self) -> None:
        candle = next(item.candle for item in GALLERY if item.expected is CandleType.BULLISH_PIN_BAR)
        candles = make_series("down", [])
        # Replace the swing with a flat history so the last shape has no trend name.
        flat = []
        start = datetime(2026, 10, 1, tzinfo=timezone.utc)
        price = 2300.0
        for index in range(30):
            flat.append(
                Candle(
                    time=start + timedelta(hours=index),
                    open=price,
                    high=price + 2,
                    low=price - 2,
                    close=price + (0.4 if index % 2 == 0 else -0.4),
                )
            )
        flat.append(
            Candle(
                time=start + timedelta(hours=30),
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
            )
        )
        analysis = analyze(flat, "1h", lookback=0)
        self.assertTrue(analysis.trend in (Trend.RANGE, Trend.UNKNOWN))
        self.assertTrue(analysis.board.primary is None or analysis.board.primary.pattern is not PatternName.HAMMER)
        self.assertTrue(any(watch.pattern is PatternName.BULLISH_PIN_BAR for watch in analysis.board.watches))


class ConflictTests(unittest.TestCase):
    def test_opposing_groups_stand_aside(self) -> None:
        from xau_candles.models import PatternSignal
        from xau_candles.opportunities import build_board
        from xau_candles.patterns import find_patterns, prepare_scan

        candles = make_series("down", [(2320, 2322, 2298, 2300), (2296, 2326, 2294, 2324)])
        scan = prepare_scan(candles)
        bull = next(
            pattern
            for pattern in find_patterns(candles, scan)
            if pattern.name is PatternName.BULLISH_ENGULFING
        )
        opposing = PatternSignal(
            name=PatternName.BEARISH_ENGULFING,
            bias=Bias.BEARISH,
            start_index=bull.start_index,
            end_index=bull.end_index,
            quality=0.8,
            candles_involved=2,
            meaning="opposing group",
        )
        board = build_board(scan, [bull, opposing], timeframe="1h", htf_bias=Trend.UNKNOWN, lookback=0)
        self.assertIsNone(board.primary)
        self.assertIn("Stand aside", board.conflict_note or "")


if __name__ == "__main__":
    unittest.main()
