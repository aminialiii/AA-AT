"""Offline checks only: no terminal initialization, broker calls, or replay."""
import ast
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "research/demo-live-20261021"


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


if __name__ == "__main__":
    unittest.main()
