"""Offline research tests; fixtures cannot reach a broker or campaign ledger."""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from research.trade_forensics.cache_snapshot import snapshot
from research.trade_forensics.daily_analytics import daily
from research.trade_forensics.priority3 import analyze_snapshot, run, summarize


class Priority3ResearchTest(unittest.TestCase):
    def test_closed_drawdown_costs_and_streaks_are_labeled(self):
        rows = []
        for index, pnl in enumerate((4, -2, -3, 2)):
            rows.append({"trade_id": f"t{index}", "exit_utc":
                         f"2026-10-2{index}T12:00:00+00:00",
                         "net_pnl": str(pnl), "gross_pnl": str(pnl + 1),
                         "commission": "-1", "swap": "0", "fees": "0",
                         "realized_r": str(pnl / 2), "holding_seconds": 60})
        result = summarize(rows)
        self.assertEqual(result["max_closed_trade_drawdown_currency"], 5)
        self.assertEqual(result["max_consecutive_losses"], 2)
        self.assertEqual(result["broker_cost_effect_currency"], -4)
        self.assertEqual(result["gross_profit_currency"], 8)
        self.assertEqual(result["drawdown_kind"], "CLOSED_TRADE_PNL_PROXY_NOT_EQUITY")
        self.assertIsNone(result["expectancy_r_day_block_95"])

    def test_versions_remain_separate_and_missing_data_stays_blocked(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            db = sqlite3.connect(state / "research.sqlite3")
            db.executescript("""
                CREATE TABLE trades(trade_id TEXT,strategy_id TEXT,config_sha256 TEXT,
                    symbol TEXT,direction TEXT,entry_utc TEXT,exit_utc TEXT,
                    gross_pnl TEXT,commission TEXT,swap TEXT,fees TEXT,net_pnl TEXT,
                    realized_r TEXT,holding_seconds REAL,source_sha256 TEXT,
                    attribution_status TEXT);
                CREATE TABLE market_bars(id INTEGER);
                CREATE TABLE market_ticks(id INTEGER);
                CREATE TABLE market_sources(sha256 TEXT,source_type TEXT,symbol TEXT,
                    timeframe TEXT,row_count INTEGER);
                CREATE TABLE quality_issues(code TEXT);
                CREATE TABLE signals(strategy_id TEXT,kind TEXT);
            """)
            for index, version in enumerate(("v1", "v2")):
                db.execute("INSERT INTO trades VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (f"t{index}", "S02", version, "EURUSD", "BUY",
                            "2026-10-21T10:00:00+00:00",
                            f"2026-10-2{index+1}T11:00:00+00:00",
                            "2", "-1", "0", "0", "1", "0.5", 60,
                            f"source{index}", "VERIFIED"))
            db.commit()
            db.close()
            report = analyze_snapshot(state / "research.sqlite3", git_commit="abc",
                                      backup_sha256="verified")
            self.assertEqual(report["cutoff"]["broker_reconciled_lifecycles"], 2)
            self.assertEqual(set(report["groups"]["strategy_version"]),
                             {"S02|v1", "S02|v2"})
            self.assertTrue(report["groups"]["strategy"]["S02"]
                            ["mixed_configuration_versions"])
            self.assertIsNone(report["data_quality"]["true_equity_drawdown"])
            self.assertEqual(report["research_gates"]["fill_sensitive_counterfactuals"],
                             "BLOCKED_NO_BROKER_BID_ASK")
            result = run(state, git_commit="abc", backup_sha256="verified")
            saved = json.loads(Path(result["report"]).read_text())
            self.assertEqual(saved["analysis_run_id"], result["analysis_run_id"])
            self.assertTrue((state / "analytics" / "latest.json").is_file())

    def test_cache_snapshot_is_opaque_and_does_not_claim_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cache = root / "cache"
            for kind, filename in (("ticks", "202610.tkc"),
                                   ("history", "2026.hcc")):
                path = cache / kind / "EURUSD" / filename
                path.parent.mkdir(parents=True)
                path.write_bytes(b"opaque-test-bytes")
            result = snapshot(cache, root / "state", symbols=("EURUSD",))
            manifest = json.loads((Path(result["snapshot"]) / "manifest.json").read_text())
            self.assertEqual(result["copied"], 2)
            self.assertFalse(manifest["terminal_queried"])
            self.assertEqual(manifest["historical_coverage"], "UNVERIFIED")

    def test_daily_job_refuses_failed_backup_before_touching_warehouse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            backups = root / "backups"
            backups.mkdir()
            (backups / "backup-status.json").write_text(json.dumps({
                "status": "FAILED", "sha256": "stale"}))
            with self.assertRaisesRegex(RuntimeError, "last_backup_not_verified"):
                daily(root / "research", backups, "a" * 40)
            self.assertFalse((root / "research").exists())


if __name__ == "__main__":
    unittest.main()
