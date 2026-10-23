"""Offline checks only: no terminal initialization, broker calls, or replay."""
import ast
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "research/demo-live-20261021"
sys.path.insert(0, str(ROOT / "tools"))
from export_operational_status import meaningful_equal  # noqa: E402
from secret_scan import scan  # noqa: E402


class RepositorySafetyTests(unittest.TestCase):
    def test_demo_guard_precedes_order_send(self):
        source = (LIVE / "broker.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        calls = [(n.func.attr, n.lineno) for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                 and n.func.attr in {"order_send", "login", "copy_rates_from"}]
        self.assertEqual([name for name, _ in calls], ["order_send"])
        self.assertIn("DEMO_ACCOUNT_GUARD_FAILED", source)
        self.assertIn("ACCOUNT_TRADE_MODE_DEMO", source)

    def test_example_is_not_routable(self):
        config = json.loads((LIVE / "campaign_config.example.json").read_text(encoding="utf-8"))
        self.assertEqual(config["account"]["login"], 0)
        self.assertEqual(config["account"]["server"], "")
        self.assertEqual(config["risk"]["target_trades_per_strategy"], 100)
        self.assertEqual(len(config["workers"]), 18)
        self.assertEqual(len({x["magic"] for x in config["workers"]}), 18)

    def test_runtime_is_ignored(self):
        ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for fragment in ("**/runtime/", "**/campaign_config.json", "*.sqlite3*"):
            self.assertIn(fragment, ignore)

    def test_clean_checkout_has_secret_scanner_and_private_account_denylist(self):
        self.assertTrue((ROOT / "tools/secret_scan.py").is_file())
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            account = "".join(str(i % 10) for i in range(10))
            denylist = base / "protected_ids.txt"
            denylist.write_text(account + "\n", encoding="ascii")
            sample = base / "sample.txt"
            sample.write_text("reference " + account, encoding="ascii")
            with patch.dict("os.environ", {"AAAT_SECRET_SCAN_DENYLIST": str(denylist)}):
                self.assertIn("protected_account_id", [kind for _, kind in scan([sample])])

    def test_published_snapshot_and_graph_are_account_free_and_consistent(self):
        status = json.loads((ROOT / "docs/operational_status.json").read_text(encoding="utf-8"))
        graph = json.loads((ROOT / "graphify-out/graph.json").read_text(encoding="utf-8"))
        validation = json.loads((ROOT / "graphify-out/validation.json").read_text(encoding="utf-8"))
        self.assertNotIn("account_login", status)
        self.assertEqual(sum(x["closed"] for x in status["workers"].values()), status["completed_trades"])
        ids = {x["id"] for x in graph["nodes"]}
        self.assertEqual(len(ids), len(graph["nodes"]))
        self.assertTrue(all(x["source"] in ids and x["target"] in ids for x in graph["links"]))
        self.assertEqual(validation["links"], len(graph["links"]))

    def test_tick_mark_noise_does_not_trigger_git_snapshot(self):
        status = json.loads((ROOT / "docs/operational_status.json").read_text(encoding="utf-8"))
        changed = copy.deepcopy(status)
        changed["source_observed_utc"] = "later"
        changed["risk_utilization_fraction"] += 0.000001
        changed["peak_equity_drawdown_fraction"] += 0.000001
        changed["safety_event_count"] += 1
        self.assertTrue(meaningful_equal(status, changed))
        changed["completed_trades"] += 1
        self.assertFalse(meaningful_equal(status, changed))


if __name__ == "__main__":
    unittest.main()
