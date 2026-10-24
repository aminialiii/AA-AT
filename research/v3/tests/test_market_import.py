"""Isolated fixture checks; never imports a trading or broker module."""
from __future__ import annotations

import hashlib
import json
import lzma
import struct
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from research.v3.market_import import (decode_dukascopy_day, import_dukascopy_day,
                                       import_legacy_m1, require_capacity,
                                       MIN_FREE_AFTER_IMPORT)
from research.v3.safety import compare

TEST_SCRATCH = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\tmp")


class MarketImportTests(unittest.TestCase):
    def setUp(self):
        TEST_SCRATCH.mkdir(parents=True, exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(prefix="v3-test-", dir=TEST_SCRATCH)
        self.addCleanup(self.scratch.cleanup)
        self.root = Path(self.scratch.name)
        self.vault = self.root / "vault"
        self.catalog = self.root / "catalog"

    def test_legacy_import_keeps_offset_unverified_and_is_idempotent(self):
        path = self.root / "rates.npz"
        dtype = [("time", "i8"), ("open", "f8"), ("high", "f8"),
                 ("low", "f8"), ("close", "f8"), ("spread", "i4")]
        rates = np.array([(1_700_000_000 + i * 60, 1.1, 1.2, 1.0, 1.15, 12)
                          for i in range(110)], dtype=dtype)
        np.savez(path, rates=rates)
        manifest = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "symbol": "EURUSD", "assumed_broker_offset_minutes": 180}
        first = import_legacy_m1(path, manifest, vault=self.vault, catalog=self.catalog)
        second = import_legacy_m1(path, manifest, vault=self.vault, catalog=self.catalog)
        self.assertEqual(first, second)
        self.assertFalse(first["utc_mapping_verified"])
        self.assertFalse(first["eligible_for_three_year_backtest"])
        self.assertEqual(first["row_count"], 110)
        self.assertEqual(hashlib.sha256(Path(first["raw_path"]).read_bytes()).hexdigest(),
                         manifest["sha256"])

    def test_bid_ask_decoder_and_catalog(self):
        day = datetime(2024, 1, 15, tzinfo=timezone.utc)
        raw = b"".join((struct.pack(">IIIff", 1000, 110010, 110000, 1.0, 2.0),
                        struct.pack(">IIIff", 2000, 110020, 110005, 1.0, 2.0)))
        bi5 = lzma.compress(raw, format=lzma.FORMAT_ALONE)
        path = self.root / "15_ticks.bi5"
        path.write_bytes(bi5)
        ticks = decode_dukascopy_day(bi5, day=day, price_scale=100000)
        self.assertEqual(len(ticks), 2)
        self.assertAlmostEqual(ticks[0]["bid"], 1.1)
        self.assertAlmostEqual(ticks[0]["ask"], 1.1001)
        row = import_dukascopy_day(path, symbol="EURUSD", day=day,
                  price_scale=100000, scale_evidence="fixture scale",
                  vault=self.vault, catalog=self.catalog)
        self.assertEqual(row["row_count"], 2)
        self.assertFalse(row["origin_verified"])
        self.assertFalse(row["eligible_for_three_year_backtest"])
        self.assertEqual(json.loads(Path(row["catalog_path"]).read_text())["source_sha256"],
                         row["source_sha256"])

    def test_bad_ask_and_oversize_are_rejected(self):
        day = datetime(2024, 1, 15, tzinfo=timezone.utc)
        bad = struct.pack(">IIIff", 1000, 100000, 110000, 1.0, 1.0)
        with self.assertRaises(ValueError):
            decode_dukascopy_day(lzma.compress(bad, format=lzma.FORMAT_ALONE),
                                  day=day, price_scale=100000)

    def test_capacity_guard_refuses_to_consume_reserve(self):
        with patch("research.v3.market_import.shutil.disk_usage") as usage:
            usage.return_value.free = MIN_FREE_AFTER_IMPORT + 99
            with self.assertRaisesRegex(RuntimeError, "research_vault_capacity_guard"):
                require_capacity(self.vault, 100)
            require_capacity(self.vault, 99)

    def test_integrity_comparison_allows_new_closes_not_source_changes(self):
        base = {"strategy_sources": {"S04": {"sha256": "x"}},
                "protected_files": {"risk": {"sha256": "y"}},
                "emergency_stop": {"present": False, "sha256": None},
                "tasks": {"CodexDemoForward20261021": {"xml_sha256": "z", "enabled": True,
                                                          "state": "Ready"}},
                "terminal_processes": [{"id": 1, "path": "research-free"}],
                "ledger": {"integrity": "ok", "closed_count": 10}}
        import research.v3.safety as safety
        old = safety.TASKS
        try:
            safety.TASKS = ("CodexDemoForward20261021",)
            after = json.loads(json.dumps(base))
            after["ledger"]["closed_count"] = 11
            self.assertEqual(compare(base, after), [])
            after["protected_files"]["risk"]["sha256"] = "changed"
            self.assertIn("protected_files_changed", compare(base, after))
        finally:
            safety.TASKS = old


if __name__ == "__main__":
    unittest.main()
