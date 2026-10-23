"""Offline admission and race tests; no MT5 import or test orders."""
import asyncio
import ast
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "research/demo-live-20261021"
sys.path.insert(0, str(LIVE))
from portfolio_policy import (Exposure, PortfolioSupervisor, SharedExposureBlocked,
                              load_policy, may_wait_for_startup_quotes, worst_fill_risk)
from report import milestones
from state import State


class PortfolioPolicyTests(unittest.TestCase):
    def test_worst_fill_gate_rejects_recorded_s04_breach_before_submission(self):
        # Broker-observed GBPUSD request/fill/SL distances; pure arithmetic,
        # with no market connection or campaign ledger mutation.
        def native_loss(side, symbol, volume, entry, stop):
            self.assertEqual((side, symbol, volume), (-1, "GBPUSD", 0.01))
            return round((stop - entry) * 1000, 8)

        total, price = worst_fill_risk(native_loss, -1, "GBPUSD", 0.01,
                                       1.34032, 1.34061, 5, 0.00001, 0.19)
        self.assertAlmostEqual(price, 0.34)
        self.assertAlmostEqual(total, 0.53)
        self.assertGreater(total, 201.46 * 0.0025)
        self.assertAlmostEqual(native_loss(-1, "GBPUSD", 0.01,
                                           1.34028, 1.34061) + 0.19, 0.52)

    def test_worst_fill_gate_uses_adverse_direction_for_buy_and_sell(self):
        def native_loss(side, symbol, volume, entry, stop):
            return abs(entry - stop) * 1000

        buy, _ = worst_fill_risk(native_loss, 1, "EURUSD", 0.01,
                                 1.1, 1.0997, 5, 0.00001, 0.1)
        sell, _ = worst_fill_risk(native_loss, -1, "EURUSD", 0.01,
                                  1.1, 1.1003, 5, 0.00001, 0.1)
        self.assertAlmostEqual(buy, 0.45)
        self.assertAlmostEqual(sell, 0.45)

    def test_authorized_policy_preserves_other_risk_limits(self):
        baseline = json.loads((LIVE / "campaign_config.example.json").read_text())["risk"]
        effective, digest = load_policy(LIVE / "risk_policy.json", baseline)
        self.assertEqual((effective["max_positions_account"], effective["max_open_fraction"]),
                         (5, 0.02))
        self.assertEqual(len(digest), 64)
        for key in ("max_trade_fraction", "daily_equity_loss_fraction",
                    "peak_equity_drawdown_fraction", "max_positions_strategy",
                    "max_positions_symbol", "max_margin_fraction_of_free"):
            self.assertEqual(effective[key], baseline[key])
        self.assertEqual(effective["max_trade_fraction"], 0.0025)
        self.assertEqual(effective["daily_equity_loss_fraction"], 0.01)
        self.assertEqual(effective["peak_equity_drawdown_fraction"], 0.02)

    def test_concurrent_slot_reservations_never_exceed_five(self):
        async def race():
            supervisor = PortfolioSupervisor(5, 0.02)
            reserved = []

            async def contender(n):
                async with supervisor.lock:
                    decision = supervisor.admit(1000, [], [], reserved, 4)
                    await asyncio.sleep(0)
                    if decision.allowed:
                        reserved.append(Exposure("RESERVED", 4, strategy=f"S{n:02d}"))
                    return decision.allowed

            outcomes = await asyncio.gather(*(contender(n) for n in range(1, 19)))
            return reserved, outcomes

        reserved, outcomes = asyncio.run(race())
        self.assertEqual(len(reserved), 5)
        self.assertEqual(sum(outcomes), 5)
        self.assertEqual(sum(x.risk for x in reserved), 20)

    def test_risk_cap_is_global_across_parallel_workers(self):
        async def race():
            supervisor = PortfolioSupervisor(5, 0.02)
            reserved = []

            async def contender(n):
                async with supervisor.lock:
                    decision = supervisor.admit(1000, [], [], reserved, 7)
                    await asyncio.sleep(0)
                    if decision.allowed:
                        reserved.append(Exposure("RESERVED", 7, strategy=f"S{n:02d}"))
                    return decision

            return reserved, await asyncio.gather(*(contender(n) for n in range(1, 19)))

        reserved, decisions = asyncio.run(race())
        self.assertEqual(len(reserved), 2)
        self.assertTrue(any(x.reason == "portfolio_open_and_pending_risk_cap" for x in decisions))
        self.assertLessEqual(sum(x.risk for x in reserved), 20)

    def test_pending_orders_consume_slots_and_risk(self):
        supervisor = PortfolioSupervisor(5, 0.02)
        positions = [Exposure("POSITION", 1) for _ in range(4)]
        pending = [Exposure("PENDING", 1)]
        self.assertEqual(supervisor.admit(1000, positions, pending, [], 1).reason,
                         "portfolio_position_slots_full")
        self.assertEqual(supervisor.admit(1000, [], [Exposure("PENDING", 12)], [], 9).reason,
                         "portfolio_open_and_pending_risk_cap")
        with self.assertRaises(SharedExposureBlocked):
            supervisor.admit(1000, [], [Exposure("PENDING", None)], [], 1)

    def test_startup_quote_wait_requires_existing_verified_policy(self):
        self.assertTrue(may_wait_for_startup_quotes("stale_or_future_quote:AUDUSD:5.9", True, True))
        self.assertFalse(may_wait_for_startup_quotes("stale_or_future_quote:AUDUSD:5.9", False, True))
        self.assertFalse(may_wait_for_startup_quotes("stale_or_future_quote:AUDUSD:5.9", True, False))
        self.assertFalse(may_wait_for_startup_quotes("DEMO_ACCOUNT_GUARD_FAILED", True, True))
        self.assertFalse(may_wait_for_startup_quotes("unowned_or_unreconciled_position", True, True))

    def test_milestones_continue_without_a_trade_ceiling(self):
        self.assertEqual(milestones(99), [])
        self.assertEqual(milestones(100), [100])
        self.assertEqual(milestones(1001), [100, 200, 500, 1000])
        self.assertEqual(milestones(2100), [100, 200, 500, 1000, 1500, 2000])
        source = (LIVE / "service.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        route = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
                     and n.name == "route")
        self.assertNotIn("count_closed", ast.unparse(route))
        self.assertNotIn("SCREEN_COMPLETE", source)
        router_scope = next(n for n in route.body if isinstance(n, ast.AsyncWith))
        locked_source = ast.unparse(router_scope)
        self.assertIn("self.controls.admission()", locked_source)
        self.assertIn("self._route_locked(", locked_source)
        locked_route = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
                            and n.name == "_route_locked")
        locked_body = ast.unparse(locked_route)
        self.assertIn("self.state.prepare(", locked_body)
        self.assertIn("self.broker.send(", locked_body)
        self.assertIn("self.supervisor.admit(", locked_body)
        self.assertIn("pre_send_gate", locked_body)
        self.assertIn("signal_expired_before_order_submission", locked_body)
        supervisor_run = next(n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef)
                              and n.name == "run")
        locked_monitor = [ast.unparse(n) for n in ast.walk(supervisor_run)
                          if isinstance(n, ast.AsyncWith) and "self.router" in ast.unparse(n.items[0].context_expr)]
        self.assertTrue(any("self.check_ownership(" in text and "self.reconcile(" in text
                            and "self.write_status(" in text for text in locked_monitor))

    def test_policy_migration_keeps_frozen_campaign_identity(self):
        with tempfile.TemporaryDirectory(prefix="aa-at-policy-test-") as folder:
            db_path = Path(folder) / "campaign.sqlite3"
            db = sqlite3.connect(db_path)
            try:
                db.execute("CREATE TABLE intents(signal_key TEXT PRIMARY KEY, strategy TEXT NOT NULL, "
                           "symbol TEXT NOT NULL, magic INTEGER NOT NULL, bar INTEGER NOT NULL, "
                           "request_json TEXT NOT NULL, planned_risk REAL NOT NULL, state TEXT NOT NULL, "
                           "created_utc TEXT NOT NULL, broker_order INTEGER, broker_deal INTEGER, "
                           "position_id INTEGER, result_json TEXT)")
                db.commit()
            finally:
                db.close()
            state = State(Path(folder), "frozen-hash")
            state.record_policy("policy-hash", {"max_positions_account": 5,
                                                "max_open_fraction": 0.02})
            columns = {row[1] for row in state.db.execute("PRAGMA table_info(intents)")}
            self.assertIn("policy_sha256", columns)
            self.assertEqual(state.get("config_sha256"), "frozen-hash")
            state.db.close()
            reopened = State(Path(folder), "frozen-hash")
            self.assertEqual(reopened.get("risk_policy_sha256"), "policy-hash")
            self.assertEqual(reopened.db.execute("SELECT COUNT(*) FROM risk_policy_versions").fetchone()[0], 1)
            reopened.db.close()


if __name__ == "__main__":
    unittest.main()
