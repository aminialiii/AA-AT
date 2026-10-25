"""Only generated parser fixtures; no synthetic prices enter campaign or research results."""
import hashlib
import json
import lzma
import struct
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from research.v3.dukascopy_hourly import ingest, source_url
from research.v3.parity_dataset import build

SCRATCH = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\tmp")


class ParityDatasetTests(unittest.TestCase):
    def test_contiguous_source_checks_and_repeatable_inputs(self):
        SCRATCH.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=SCRATCH) as folder:
            root = Path(folder)
            vault, catalog = root / "vault", root / "catalog"
            source_paths = []
            initial = datetime(2024, 1, 15, 12, tzinfo=timezone.utc)
            for number in range(5):
                hour = initial + timedelta(hours=number)
                raw = lzma.compress(b"".join(
                    struct.pack(">IIIff", minute * 60_000 + 100,
                                109455 + minute, 109453 + minute, 1.0, 1.0)
                    for minute in range(60)), format=lzma.FORMAT_ALONE)
                checksum = hashlib.sha256(raw).hexdigest()
                path = (vault / "raw" / "DukascopyHourly" / "EURUSD" /
                        hour.strftime("%Y-%m-%d") / (checksum + ".bi5"))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(raw)
                source = {"source_url": source_url("EURUSD", hour),
                          "archive_path": str(path), "source_sha256": checksum}
                record = ingest(source, "EURUSD", hour, 100000, "fixture scale",
                                vault=vault, catalog=catalog)
                source_paths.append(Path(record["catalog_path"]))
            result = build(source_paths, point=0.00001, vault=vault, catalog=catalog)
            self.assertEqual(result["bar_count"], 300)
            self.assertEqual(result["tick_count"], 300)
            self.assertFalse(result["backtest_eligible"])
            manifest = json.loads(Path(result["record"]).read_text(encoding="utf-8"))
            self.assertFalse(manifest["tester_clock_verified"])
            self.assertEqual(len(manifest["raw_sources"]), 5)
            self.assertEqual(build(source_paths, point=0.00001,
                                   vault=vault, catalog=catalog)["record"], result["record"])
            with self.assertRaisesRegex(ValueError, "insufficient_contiguous"):
                build(source_paths[:1], point=0.00001, vault=vault, catalog=catalog)


if __name__ == "__main__":
    unittest.main()
