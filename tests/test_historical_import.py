"""Fixture-only tests; no terminal, broker query, or historical trade generation."""
import sqlite3
import tempfile
import unittest
import zipfile
from contextlib import closing
from pathlib import Path

import pyarrow.parquet as pq

from research.trade_forensics.historical_import import import_archive
from research.trade_forensics.store import Warehouse


class HistoricalImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        warehouse = Warehouse(self.root / "state")
        warehouse.close()

    def tearDown(self):
        self.temporary.cleanup()

    def archive(self, rows, name="DAT_ASCII_EURUSD_M1_202403.csv"):
        path = self.root / "sample.zip"
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as package:
            package.writestr(name, "\n".join(rows) + "\n")
        return path

    def test_fixed_est_to_utc_and_idempotent_existing_warehouse(self):
        path = self.archive([
            "20240310 015900;1.1000;1.1002;1.0998;1.1001;0",
            "20240310 020000;1.1001;1.1003;1.0999;1.1002;0",
        ])
        first = import_archive(self.root / "state", path, symbol="EURUSD",
                               kind="M1", period="2024-03")
        self.assertEqual(first["rows"], 2)
        self.assertEqual(first["first_utc"], "2024-03-10T06:59:00+00:00")
        self.assertEqual(first["last_utc"], "2024-03-10T07:00:00+00:00")
        self.assertEqual(pq.ParquetFile(first["parquet_path"]).metadata.num_rows, 2)
        again = import_archive(self.root / "state", path, symbol="EURUSD",
                               kind="M1", period="2024-03")
        self.assertEqual(again["status"], "ALREADY_IMPORTED")
        with closing(sqlite3.connect(self.root / "state" / "research.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM trades").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0], 0)
            self.assertEqual(db.execute("SELECT COUNT(*) FROM market_sources").fetchone()[0], 1)

    def test_invalid_prices_do_not_create_accepted_source(self):
        path = self.archive(["20240310 015900;1.1000;1.0990;1.1000;1.1000;0"])
        with self.assertRaisesRegex(ValueError, "invalid_market_row"):
            import_archive(self.root / "state", path, symbol="EURUSD",
                           kind="M1", period="2024-03")
        with closing(sqlite3.connect(self.root / "state" / "research.sqlite3")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM market_sources").fetchone()[0], 0)

    def test_tick_bid_ask_and_duplicate_flag(self):
        path = self.archive([
            "20240310 015900123,1.1000,1.1002,0",
            "20240310 015900123,1.1000,1.1002,0",
        ], name="DAT_ASCII_EURUSD_T_202403.csv")
        row = import_archive(self.root / "state", path, symbol="EURUSD",
                             kind="T", period="2024-03")
        self.assertEqual(row["duplicate_rows"], 1)
        self.assertEqual(row["status"], "REVIEW_GAPS_OR_DUPLICATES")

    def test_archive_path_and_period_mismatch_rejected(self):
        path = self.archive(["20240310 015900;1.1;1.2;1.0;1.1;0"],
                            name="../DAT_ASCII_EURUSD_M1_202403.csv")
        with self.assertRaisesRegex(ValueError, "archive_member_path_not_flat"):
            import_archive(self.root / "state", path, symbol="EURUSD",
                           kind="M1", period="2024-03")


if __name__ == "__main__":
    unittest.main()
