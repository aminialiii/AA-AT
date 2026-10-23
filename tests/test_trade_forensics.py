import hashlib
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from research.trade_forensics.store import Warehouse, import_live
from research.trade_forensics.analytics import session_labels, statistics
from research.trade_forensics.market import import_csv, derive_m3
from research.trade_forensics.charts import chart, MarketDataUnavailable, _excursion
from research.trade_forensics.quality import report as quality_report
from research.trade_forensics.exports import export


class TradeForensicsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "workspace"
        runtime = self.workspace / "research" / "demo-live-20261021" / "runtime"
        evidence = runtime / "evidence" / "S01"
        evidence.mkdir(parents=True)
        broker = [
            ("BROKER_DEAL", {"ticket": 11, "order": 101, "position_id": 1,
                             "type": 0, "volume": 0.1, "price": 1.0, "profit": 0,
                             "commission": -0.1, "swap": 0, "fee": 0,
                             "time_msc": 1_700_000_000_000}),
            ("BROKER_DEAL", {"ticket": 12, "order": 102, "position_id": 1,
                             "type": 1, "volume": 0.1, "price": 1.1, "profit": 10,
                             "commission": -0.1, "swap": 0, "fee": 0,
                             "time_msc": 1_700_000_060_000}),
            ("BROKER_ORDER", {"ticket": 101, "position_id": 1}),
            ("BROKER_ORDER", {"ticket": 102, "position_id": 1}),
        ]
        refs = []
        for index, (kind, payload) in enumerate(broker):
            source = evidence / f"{index}.json"
            raw = json.dumps({"utc": "2023-11-14T22:13:20+00:00",
                              "strategy": "S01", "kind": kind,
                              "payload": payload}).encode()
            source.write_bytes(raw)
            refs.append({"path": str(source), "sha256": hashlib.sha256(raw).hexdigest()})
        record = {
            "execution_kind": "REAL_TIME_DEMO_BROKER", "account_trade_mode": "DEMO",
            "fully_closed": True, "campaign_id": "fixture-42", "account_login": 42,
            "account_server": "Fixture-Demo", "strategy_id": "S01",
            "config_sha256": "fixture-version", "symbol": "EURUSD",
            "opening_deal_ids": [11], "closing_deal_ids": [12],
            "opening_order_id": 101, "closing_order_ids": [102],
            "opened_volume": 0.1, "closed_volume": 0.1,
            "entry_price": 1.0, "exit_price": 1.1,
            "entry_utc": "2023-11-14T22:13:20+00:00",
            "exit_utc": "2023-11-14T22:14:20+00:00",
            "stop_loss": 0.99, "take_profit": 1.1,
            "initial_risk_account_currency": 5,
            "broker_gross_profit": 10, "broker_commission": -0.2,
            "broker_swap": 0, "broker_fees": 0, "broker_net_profit": 9.8,
            "broker_evidence": refs,
        }
        connection = sqlite3.connect(runtime / "campaign.sqlite3")
        connection.execute("CREATE TABLE closed(position_id INTEGER PRIMARY KEY, strategy TEXT, signal_key TEXT, record_json TEXT)")
        connection.execute("CREATE TABLE safety_events(id TEXT,observed_utc TEXT,scope TEXT,reason TEXT)")
        connection.execute("INSERT INTO closed VALUES (?,?,?,?)", (1, "S01", "signal-42", json.dumps(record)))
        connection.commit()
        connection.close()
        self.warehouse = Warehouse(Path(self.temp.name) / "research-state")
        self.addCleanup(self.warehouse.close)

    def test_import_is_idempotent_and_account_is_pseudonymous(self):
        first = import_live(self.warehouse, self.workspace)
        second = import_live(self.warehouse, self.workspace)
        self.assertEqual(first["processed"], 1)
        self.assertEqual(first["new_trades"], 1)
        self.assertEqual(second["processed"], 0)
        row = self.warehouse.db.execute(
            "SELECT strategy_id,direction,realized_r,attribution_status FROM trades"
        ).fetchone()
        self.assertEqual((row["strategy_id"], row["direction"], row["realized_r"],
                          row["attribution_status"]), ("S01", "BUY", "1.96", "VERIFIED"))
        self.assertEqual(self.warehouse.db.execute(
            "SELECT COUNT(*) FROM broker_events").fetchone()[0], 4)
        self.assertEqual(self.warehouse.db.execute(
            "SELECT COUNT(*) FROM trades").fetchone()[0], 1)
        quality = quality_report(self.warehouse)
        self.assertEqual(quality["coverage_counts"]["attribution_verified"], 1)
        self.assertEqual(quality["market_bar_rows"], 0)
        self.assertEqual(quality["issues_by_code"]["market_context_unavailable"], 1)

    def test_analysis_keeps_small_sample_uncertainty(self):
        rows = [
            {"net_pnl": "10", "realized_r": "1", "holding_seconds": 60,
             "commission": "-1", "swap": "0", "fees": "0"},
            {"net_pnl": "-5", "realized_r": "-0.5", "holding_seconds": 120,
             "commission": "-1", "swap": "0", "fees": "0"},
        ]
        result = statistics(rows, seed=1)
        self.assertEqual(result["closed_trades"], 2)
        self.assertEqual(result["profit_factor"], 2)
        self.assertEqual(result["max_closed_trade_drawdown_currency"], 5)
        self.assertIsNotNone(result["win_rate_wilson_95"])
        self.assertIn("Small sample", result["sample_warning"])

    def test_partial_close_deals_remain_one_reconciled_lifecycle(self):
        runtime = self.workspace / "research" / "demo-live-20261021" / "runtime"
        connection = sqlite3.connect(runtime / "campaign.sqlite3")
        record = json.loads(connection.execute("SELECT record_json FROM closed").fetchone()[0])
        record["closing_deal_ids"] = [12, 13]
        record["closing_order_ids"] = [102, 103]
        first = Path(record["broker_evidence"][1]["path"])
        payload = json.loads(first.read_text())
        payload["payload"].update({"volume": 0.06, "profit": 6, "commission": -0.06})
        raw = json.dumps(payload).encode()
        first.write_bytes(raw)
        record["broker_evidence"][1]["sha256"] = hashlib.sha256(raw).hexdigest()
        for index, kind, content in (
            (4, "BROKER_DEAL", {"ticket": 13, "order": 103, "position_id": 1,
                                 "type": 1, "volume": 0.04, "price": 1.1,
                                 "profit": 4, "commission": -0.04, "swap": 0,
                                 "fee": 0, "time_msc": 1_700_000_060_000}),
            (5, "BROKER_ORDER", {"ticket": 103, "position_id": 1}),
        ):
            path = first.with_name(f"{index}.json")
            raw = json.dumps({"utc": record["exit_utc"], "strategy": "S01",
                              "kind": kind, "payload": content}).encode()
            path.write_bytes(raw)
            record["broker_evidence"].append({
                "path": str(path), "sha256": hashlib.sha256(raw).hexdigest()})
        connection.execute("UPDATE closed SET record_json=?", (json.dumps(record),))
        connection.commit()
        connection.close()
        result = import_live(self.warehouse, self.workspace)
        self.assertEqual(result["new_trades"], 1)
        self.assertEqual(self.warehouse.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0], 1)
        self.assertEqual(self.warehouse.db.execute(
            "SELECT COUNT(*) FROM position_events WHERE kind='PARTIAL_OR_FINAL_CLOSE'").fetchone()[0], 2)
        self.assertEqual(self.warehouse.db.execute(
            "SELECT COUNT(*) FROM quality_issues WHERE code='broker_pnl_mismatch'").fetchone()[0], 0)

    def test_session_timezone_uses_dst(self):
        winter = session_labels("2026-01-05T08:30:00+00:00")
        summer = session_labels("2026-07-06T07:30:00+00:00")
        self.assertIn("LONDON", winter)
        self.assertIn("LONDON", summer)

    def test_market_import_and_complete_m3_only(self):
        source = Path(self.temp.name) / "m1.csv"
        source.write_text(
            "time_utc,open,high,low,close,tick_volume,real_volume,spread_points\n"
            "2026-10-22T10:00:00+00:00,1.0,1.2,0.9,1.1,10,0,2\n"
            "2026-10-22T10:01:00+00:00,1.1,1.3,1.0,1.2,11,0,3\n"
            "2026-10-22T10:02:00+00:00,1.2,1.4,1.1,1.3,12,0,2\n"
            "2026-10-22T10:04:00+00:00,1.3,1.4,1.2,1.3,13,0,2\n",
            encoding="utf-8")
        result = import_csv(self.warehouse, source, kind="bars", symbol="EURUSD",
                            timeframe="M1", source_type="BROKER_EXPORT")
        self.assertEqual(result["new_rows"], 4)
        self.assertEqual(import_csv(
            self.warehouse, source, kind="bars", symbol="EURUSD",
            timeframe="M1", source_type="BROKER_EXPORT")["new_rows"], 0)
        derived = derive_m3(self.warehouse, result["source_sha256"], "EURUSD")
        self.assertEqual(derived["new_rows"], 1)

    def test_chart_requires_recorded_market_data(self):
        trade_id = self.warehouse.db.execute("SELECT trade_id FROM trades").fetchone()
        if trade_id is None:
            import_live(self.warehouse, self.workspace)
            trade_id = self.warehouse.db.execute("SELECT trade_id FROM trades").fetchone()
        with self.assertRaises(MarketDataUnavailable):
            chart(self.warehouse, trade_id[0], pre_minutes=0, post_minutes=0)

    def test_ohlc_excursion_excludes_wholly_pre_entry_and_post_exit_bars(self):
        row = {"record_json": json.dumps({"entry_price": 1.0}),
               "initial_sl": "0.99", "direction": "BUY",
               "entry_utc": "2023-11-14T22:13:00+00:00",
               "exit_utc": "2023-11-14T22:14:00+00:00"}
        bars = [
            {"timeframe": "M1", "open_utc": f"2023-11-14T22:{minute}:00+00:00",
             "high": high, "low": low}
            for minute, high, low in (("12", 2.0, 0.1), ("13", 1.05, 0.98),
                                      ("14", 2.0, 0.1))]
        result = _excursion(self.warehouse, row, bars, [])
        self.assertAlmostEqual(result["mfe_r"], 5)
        self.assertAlmostEqual(result["mae_r"], 2)

    def test_chart_exports_real_recorded_candles(self):
        import_live(self.warehouse, self.workspace)
        source = Path(self.temp.name) / "recorded.csv"
        source.write_text(
            "time_utc,open,high,low,close,tick_volume\n"
            "2023-11-14T22:12:00+00:00,1.0,1.01,0.99,1.0,10\n"
            "2023-11-14T22:13:00+00:00,1.0,1.05,0.98,1.02,12\n"
            "2023-11-14T22:14:00+00:00,1.02,1.12,1.01,1.1,13\n",
            encoding="utf-8")
        import_csv(self.warehouse, source, kind="bars", symbol="EURUSD",
                   timeframe="M1", source_type="BROKER_EXPORT")
        trade_id = self.warehouse.db.execute("SELECT trade_id FROM trades").fetchone()[0]
        result = chart(self.warehouse, trade_id, pre_minutes=2, post_minutes=0)
        self.assertTrue(Path(result["html"]).is_file())
        self.assertTrue(Path(result["json"]).is_file())
        self.assertTrue(Path(result["png"]).is_file())
        self.assertEqual(result["excursion"]["quality"],
                         "OHLC_APPROX_INTRABAR_AND_SPREAD_UNKNOWN")
        self.assertGreater(result["excursion"]["mfe_r"], 0)
        self.assertGreater(result["excursion"]["mae_r"], 0)

    def test_portable_export_redacts_account_login(self):
        import_live(self.warehouse, self.workspace)
        result = export(self.warehouse.root)
        with zipfile.ZipFile(result["archive"]) as package:
            trades = package.read("journal/trades.csv").decode()
            self.assertNotIn("account_login", trades)
            self.assertNotIn("fixture-42", trades)
            self.assertNotIn("signal-42", trades)
            self.assertIn("trade_id", trades)
            self.assertTrue(json.loads(package.read("manifest.json"))[
                "account_identifiers_redacted"])


if __name__ == "__main__":
    unittest.main()
