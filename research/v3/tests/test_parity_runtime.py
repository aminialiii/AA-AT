"""Control-path fixtures only; never campaign trades or claimed MQL observations."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from research.v3.parity_runtime import compare, python_reference, read_tester_trace

SCRATCH = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\tmp")


class RuntimeParityTests(unittest.TestCase):
    def test_trace_parser_and_structured_mismatch(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as name:
            log = Path(name) / "tester.log"
            log.write_text("AAAT_V3_TRACE,S04,EURUSD,2024.01.15 12:01:00,1,0.000123456789,0.000020000000,0.000010000000,1\n", encoding="utf-16")
            rows = read_tester_trace(log)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["signal_bar_utc"], "2024-01-15T12:01:00+00:00")
            self.assertAlmostEqual(rows[0]["live_spread"], 0.00001)
            self.assertEqual(read_tester_trace(log, server_offset_seconds=3600)[0]["signal_bar_utc"],
                             "2024-01-15T11:01:00+00:00")
            self.assertTrue(compare(rows, rows)["signal_parity_passed"])
            altered = [{**rows[0], "side": -1}]
            report = compare(rows, altered)
            self.assertFalse(report["signal_parity_passed"])
            self.assertEqual(report["mismatch_examples"][0]["kind"], "SIDE_MISMATCH")
            self.assertEqual(compare(rows, [*rows, *rows])["duplicate_mql_keys"], 1)

    def test_reference_requires_contiguous_verified_spread_bars(self):
        dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"),
                 ("low", "f8"), ("close", "f8"), ("spread", "i4")]
        bars = np.zeros(261, dtype=dtype)
        bars["time"] = 1705320000 + np.arange(261) * 60
        bars["open"] = 1.1
        bars["high"] = 1.1002
        bars["low"] = 1.0998
        bars["close"] = 1.1001
        bars["spread"] = 2
        quotes = np.zeros(261, dtype=[("time_ms_utc", "i8"), ("bid", "f8"), ("ask", "f8")])
        quotes["time_ms_utc"] = bars["time"] * 1000 + 100
        quotes["bid"] = 1.1001
        quotes["ask"] = 1.10011
        rows = python_reference(bars, quotes, tick_size=0.00001, point=0.00001,
                                symbol="EURUSD")
        self.assertEqual(len(rows), 2)  # bars 258 and 259 have a following bar
        self.assertAlmostEqual(rows[0]["live_spread"], 0.00001)
        self.assertEqual(python_reference(bars[:259], quotes, tick_size=0.00001,
                                          point=0.00001, symbol="EURUSD"), [])
        bars["time"][1] = bars["time"][0]
        with self.assertRaises(ValueError):
            python_reference(bars, quotes, tick_size=0.00001, point=0.00001,
                             symbol="EURUSD")


if __name__ == "__main__":
    unittest.main()
