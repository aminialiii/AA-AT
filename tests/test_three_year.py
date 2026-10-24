"""Isolated historical-readiness tests; no broker or trading service imports."""
from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import numpy as np

from research.trade_forensics import three_year


class ThreeYearAuditTests(unittest.TestCase):
    def test_legacy_archive_is_partial_and_offset_unverified(self):
        with tempfile.TemporaryDirectory() as root:
            workspace = Path(root)
            location = workspace / "research" / "overnight-20261010"
            location.mkdir(parents=True)
            rates = np.array([
                (180 * 60, 1.0, 1.2, 0.9, 1.1, 2),
                (181 * 60, 1.1, 1.3, 1.0, 1.2, 3),
            ], dtype=[("time", "i8"), ("open", "f8"), ("high", "f8"),
                      ("low", "f8"), ("close", "f8"), ("spread", "i4")])
            source = location / "EURUSD.npz"
            np.savez_compressed(source, rates=rates)
            source_hash = three_year.sha256(source)
            manifest = location / "manifest.json"
            manifest.write_text(json.dumps({"brokerOffsetMinutes": 180,
                "symbols": {"EURUSD": {"path": str(source), "sha256": source_hash,
                    "status": "AVAILABLE", "bars": 2,
                    "firstUTC": "1970-01-01T00:00:00+00:00",
                    "lastUTC": "1970-01-01T00:01:00+00:00"}}}), encoding="utf-8")
            (location / "history_pointer.json").write_text(json.dumps({
                "path": str(manifest), "sha256": three_year.sha256(manifest)}),
                encoding="utf-8")
            result = three_year.audit_legacy_m1(workspace)
            self.assertEqual(result[0]["status"], "PARTIAL_ARCHIVE_OFFSET_UNVERIFIED")
            self.assertFalse(result[0]["continuous_three_year_coverage"])
            self.assertFalse(result[0]["bid_ask_ticks_covered"])

    def test_publish_is_idempotent_and_separate_from_forward_trades(self):
        with tempfile.TemporaryDirectory() as root:
            state = Path(root)
            connection = sqlite3.connect(state / "research.sqlite3")
            connection.execute("CREATE TABLE trades(trade_id TEXT PRIMARY KEY)")
            connection.execute("INSERT INTO trades VALUES ('forward-evidence')")
            connection.commit()
            connection.close()
            report = {"assessment_id": "a" * 20, "generated_utc": three_year.utc(),
                      "overall_status": "BLOCKED_NO_VERIFIED_THREE_YEAR_MARKET_DATA",
                      "backup_sha256": "b" * 64, "historical_backtest_runs": 0,
                      "simulated_trades": 0}
            first = three_year.publish(state, report)
            second = three_year.publish(state, report)
            self.assertEqual(first, second)
            connection = sqlite3.connect(state / "research.sqlite3")
            try:
                self.assertEqual(connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0], 1)
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM historical_backtest_trades").fetchone()[0], 0)
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM historical_assessments").fetchone()[0], 1)
            finally:
                connection.close()

    def test_failed_backup_blocks_assessment(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "backup.json"
            path.write_text('{"status":"FAILED"}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "verified_prebacktest_backup_required"):
                three_year.assess(Path(root), Path(root), path)


if __name__ == "__main__":
    unittest.main()
