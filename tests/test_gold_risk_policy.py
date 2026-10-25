"""Gold admission checks are pure/offline; this suite never imports MT5."""
import ast
import asyncio
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "research" / "demo-live-20261021"
sys.path.insert(0, str(LIVE))

from portfolio_policy import (Exposure, PortfolioSupervisor, load_policy,
                              trade_risk_budget)


class GoldRiskPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        baseline = json.loads((LIVE / "campaign_config.example.json").read_text())["risk"]
        cls.policy, cls.policy_hash = load_policy(LIVE / "risk_policy.json", baseline)

    def test_gold_authorization_is_bounded_and_fx_cap_unchanged(self):
        self.assertEqual(self.policy["gold_max_trade_risk_usd"], 10)
        self.assertEqual(self.policy["gold_max_trade_fraction_account"], 0.01)
        self.assertEqual(self.policy["max_trade_fraction"], 0.0025)
        self.assertEqual(self.policy["max_open_fraction"], 0.10)
        self.assertEqual(self.policy["peak_equity_drawdown_fraction"], 0.10)
        self.assertEqual(self.policy["daily_equity_loss_fraction"], 0.05)
        self.assertAlmostEqual(trade_risk_budget("EURUSD", 1003.21, 201.12,
                                                self.policy, 1003.21, 1003.21), 0.5028)
        self.assertAlmostEqual(trade_risk_budget("XAUUSD", 1003.21, 201.12,
                                                self.policy, 1003.21, 1003.21), 10)

    def test_minimum_lot_is_not_a_risk_target(self):
        budget = trade_risk_budget("XAUUSD", 1003.21, 201.12,
                                   self.policy, 1003.21, 1003.21)
        self.assertLess(1.74, budget)  # observed minimum skipped gold request
        self.assertGreater(15.64, budget)  # observed high-risk request stays blocked

    def test_gold_cannot_consume_daily_or_peak_headroom(self):
        self.assertAlmostEqual(trade_risk_budget("XAUUSD", 956, 200, self.policy,
                                                1000, 1000), 6)
        self.assertAlmostEqual(trade_risk_budget("XAUUSD", 905, 200, self.policy,
                                                900, 1000), 5)
        self.assertEqual(trade_risk_budget("XAUUSD", 899, 200, self.policy,
                                           900, 1000), 0)

    def test_gold_still_consumes_global_slots_and_risk(self):
        supervisor = PortfolioSupervisor(self.policy["max_positions_account"],
                                         self.policy["max_open_fraction"])
        positions = [Exposure("POSITION", 10, symbol="XAUUSD", strategy="S01")]
        # The separate same-symbol gate in service.py prevents another gold
        # order. The global supervisor independently counts its risk and slot.
        decision = supervisor.admit(1000, positions, [], [], 10)
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.committed_risk, 10)
        self.assertFalse(supervisor.admit(1000, positions, [], [], 90.01).allowed)
        self.assertFalse(supervisor.admit(1000, [], [Exposure("PENDING", 95)],
                                          [], 6).allowed)
        self.assertFalse(supervisor.admit(1000,
                                          positions + [Exposure("POSITION", 1)] * 4,
                                          [], [], 1).allowed)

    def test_parallel_reservations_respect_ten_percent_and_five_slots(self):
        async def race():
            supervisor = PortfolioSupervisor(5, self.policy["max_open_fraction"])
            reserved = []

            async def contender(n):
                async with supervisor.lock:
                    decision = supervisor.admit(1000, [], [], reserved, 30)
                    await asyncio.sleep(0)
                    if decision.allowed:
                        reserved.append(Exposure("RESERVED", 30, strategy=f"S{n:02d}"))
                    return decision.allowed

            return reserved, await asyncio.gather(*(contender(n) for n in range(1, 19)))

        reserved, admitted = asyncio.run(race())
        self.assertEqual(len(reserved), 3)
        self.assertEqual(sum(admitted), 3)
        self.assertLessEqual(sum(item.risk for item in reserved), 100)

    def test_policy_rejects_escalation_beyond_explicit_authorization(self):
        baseline = json.loads((LIVE / "campaign_config.example.json").read_text())["risk"]
        raw = json.loads((LIVE / "risk_policy.json").read_text())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "risk_policy.json"
            for key, invalid in (("gold_max_trade_risk_usd", 10.01),
                                 ("gold_max_trade_fraction_account", 0.0101),
                                 ("daily_equity_loss_fraction", 0.051),
                                 ("peak_equity_drawdown_fraction", 0.101),
                                 ("max_open_fraction", 0.101)):
                candidate = dict(raw, **{key: invalid})
                path.write_text(json.dumps(candidate), encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    load_policy(path, baseline)

    def test_legacy_policy_does_not_enable_gold_exception(self):
        baseline = json.loads((LIVE / "campaign_config.example.json").read_text())["risk"]
        raw = json.loads((LIVE / "risk_policy.json").read_text())
        raw["policy_version"] = 2
        raw["max_open_fraction"] = 0.02
        raw.pop("peak_equity_drawdown_fraction")
        raw.pop("daily_equity_loss_fraction")
        raw.pop("gold_max_trade_risk_usd")
        raw.pop("gold_max_trade_fraction_account")
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "risk_policy.json"
            path.write_text(json.dumps(raw), encoding="utf-8")
            policy, _ = load_policy(path, baseline)
        self.assertAlmostEqual(trade_risk_budget("XAUUSD", 1003.21, 201.12,
                                                policy, 1003.21, 1003.21), 0.5028)

    def test_all_three_admission_stages_use_same_gold_budget(self):
        tree = ast.parse((LIVE / "service.py").read_text(encoding="utf-8"))
        source = ast.unparse(tree)
        self.assertGreaterEqual(source.count("trade_risk_budget("), 3)
        self.assertIn("per_trade_risk_cap_changed_before_order_submission", source)
        self.assertIn("filled_price_risk_exceeds_cap", source)
        self.assertIn("self.supervisor.admit(", source)
        self.assertIn("if any((x.symbol == symbol", source)


if __name__ == "__main__":
    unittest.main()
