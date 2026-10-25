"""Parser fixtures only; these prices never enter a research or DEMO ledger."""
import hashlib
import lzma
import struct
import tempfile
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from research.v3.dukascopy_hourly import decode, ingest as ingest_hour, source_url
from research.v3.histdata import ingest as ingest_histdata, parse_est_millis

SCRATCH = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\tmp")


class ExternalImportTests(unittest.TestCase):
    def setUp(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        temp = tempfile.TemporaryDirectory(prefix="external-import-", dir=SCRATCH)
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.vault = self.root / "vault"
        self.catalog = self.root / "catalog"

    def test_legacy_hour_decoding_and_hash_catalog(self):
        hour = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)
        self.assertEqual(source_url("EURUSD", hour),
            "https://datafeed.dukascopy.com/datafeed/EURUSD/2024/00/15/12h_ticks.bi5")
        packed = struct.pack(">IIIff", 96, 109455, 109453, 1.0, 2.0)
        raw = lzma.compress(packed, format=lzma.FORMAT_ALONE)
        ticks = decode(raw, hour, 100000)
        self.assertEqual(len(ticks), 1)
        self.assertAlmostEqual(ticks[0]["bid"], 1.09453)
        self.assertEqual(ticks[0]["time_ms_utc"], int(hour.timestamp()*1000)+96)
        sha = hashlib.sha256(raw).hexdigest()
        path = self.vault / "raw" / "DukascopyHourly" / "EURUSD" / "2024-01-15" / (sha + ".bi5")
        path.parent.mkdir(parents=True)
        path.write_bytes(raw)
        acquired = {"source_url": source_url("EURUSD", hour),
                    "archive_path": str(path), "source_sha256": sha}
        record = ingest_hour(acquired, "EURUSD", hour, 100000, "fixture scale",
                             vault=self.vault, catalog=self.catalog)
        self.assertEqual(record["row_count"], 1)
        self.assertFalse(record["broker_matched"])
        self.assertFalse(record["eligible_for_three_year_backtest"])

    def test_hour_rejects_wrong_timestamp_base(self):
        hour = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)
        raw = lzma.compress(struct.pack(">IIIff", 3_600_000, 109455, 109453, 1, 2),
                            format=lzma.FORMAT_ALONE)
        with self.assertRaisesRegex(ValueError, "invalid_hour_ticks"):
            decode(raw, hour, 100000)

    def test_histdata_fixed_est_conversion_and_fixture_archive(self):
        self.assertEqual(parse_est_millis("20250115 120000096"),
                         int(datetime(2025, 1, 15, 17, tzinfo=timezone.utc).timestamp()*1000)+96)
        body = ("20250115 120000096,1.09453,1.09455,0\n"
                "20250115 120059541,1.09538,1.09540,0\n")
        directory = self.vault / "raw" / "HistData" / "EURUSD" / "2025-01"
        directory.mkdir(parents=True)
        seed = directory / "seed.zip"
        with zipfile.ZipFile(seed, "w") as archive:
            archive.writestr("DAT_ASCII_EURUSD_T_202501.csv", body)
        sha = hashlib.sha256(seed.read_bytes()).hexdigest()
        path = directory / (sha + ".zip")
        seed.rename(path)
        acquired = {"archive_path": str(path), "source_sha256": sha,
                    "source_page": "test-fixture"}
        record = ingest_histdata(acquired, "EURUSD", 2025, 1,
                                 vault=self.vault, catalog=self.catalog)
        self.assertEqual(record["row_count"], 2)
        self.assertTrue(record["utc_mapping_verified"])
        self.assertFalse(record["broker_matched"])


if __name__ == "__main__":
    unittest.main()
