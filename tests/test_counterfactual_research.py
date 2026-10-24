"""Synthetic quote fixtures test research arithmetic; never campaign trades."""
import unittest

from research.trade_forensics.scenarios import evaluate


class ScenarioTest(unittest.TestCase):
    def setUp(self):
        self.trade = {"direction": "BUY", "entry_utc": "2026-10-21T10:00:00+00:00",
                      "entry_price": 1.0000, "initial_sl": 0.9900,
                      "initial_tp": 1.0200, "volume": 1,
                      "initial_risk_currency": 10}
        self.cost = {"account_currency_value_per_price_unit_per_lot": 1000,
                     "commission_round_trip_currency": 1,
                     "adverse_exit_slippage_price": 0.001,
                     "financing_per_day_currency": 0,
                     "contract_spec_sha256": "b" * 64}
        self.ticks = [
            {"time_utc": f"2026-10-21T10:00:{second:02d}+00:00",
             "bid": bid, "ask": bid + 0.002,
             "source_type": "BROKER_EXPORT", "source_sha256": "a" * 64}
            for second, bid in ((0, 1.001), (10, 1.006), (20, 1.011),
                                (30, 1.000), (40, 0.989))]

    def test_break_even_can_still_lose_after_costs(self):
        result = evaluate(self.trade, self.ticks,
                          {"max_holding_seconds": 40,
                           "break_even_trigger_r": 1}, self.cost)
        self.assertEqual(result["exit_reason"], "STOP")
        self.assertEqual(result["status"], "COUNTERFACTUAL")
        self.assertAlmostEqual(result["net_pnl_currency"], -2)
        self.assertAlmostEqual(result["realized_r"], -0.2)

    def test_broker_bid_ask_is_mandatory(self):
        ticks = [dict(row, source_type="EXTERNAL_CONTEXT") for row in self.ticks]
        result = evaluate(self.trade, ticks, {"max_holding_seconds": 40}, self.cost)
        self.assertEqual(result["status"], "INSUFFICIENT_EVIDENCE")

    def test_gap_blocks_apparent_outcome(self):
        result = evaluate(self.trade, [self.ticks[0], self.ticks[-1]],
                          {"max_holding_seconds": 40}, self.cost,
                          max_gap_seconds=20)
        self.assertEqual(result["reason"], "tick_gap")

    def test_combined_partial_and_target_is_evaluated_directly(self):
        result = evaluate(self.trade, self.ticks,
                          {"max_holding_seconds": 40, "partial_target_r": 0.5,
                           "partial_fraction": 0.5, "target_r": 1}, self.cost)
        self.assertEqual(result["exit_reason"], "TARGET")
        self.assertEqual(len(result["partial_exits"]), 1)
        # Partial and remaining fills each include adverse slippage.
        self.assertAlmostEqual(result["net_pnl_currency"], 5.5)


if __name__ == "__main__":
    unittest.main()
