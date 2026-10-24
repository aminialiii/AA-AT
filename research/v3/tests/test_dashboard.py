from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

from research.v3.dashboard import handler_factory
from research.v3.status import build_status


class DashboardTests(unittest.TestCase):
    def test_read_only_status_is_separate_from_demo(self):
        report = build_status()
        self.assertEqual(report["historical_backtest_runs"], 0)
        self.assertEqual(report["broker_confirmed_demo_trades_included"], 0)
        self.assertEqual(len(report["strategies"]), 18)
        self.assertEqual(report["gold_demo_activation"], "NOT_AUTHORIZED")
        self.assertTrue(all(not row["full_period_eligible"] for row in report["coverage"]))

    def test_api_requires_token_and_exposes_no_controls(self):
        token = "research-test-token-1234567890-abcdef"
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(token))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
            connection.request("GET", "/api/status")
            self.assertEqual(connection.getresponse().status, 401)
            connection.request("POST", "/api/status")
            self.assertEqual(connection.getresponse().status, 501)
            connection.request("GET", "/api/status",
                               headers={"Authorization": "Bearer " + token})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertEqual(json.loads(response.read())["simulated_trades"], 0)
            connection.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_ea_source_has_multiple_tester_gates(self):
        source = (Path(__file__).parents[1] / "ea" / "S04_MomentumProxy_v1.mq5").read_text()
        self.assertIn("MQLInfoInteger(MQL_TESTER)", source)
        self.assertGreaterEqual(source.count("if(!TesterOnly())"), 3)
        self.assertIn("InpSignalOnly = true", source)
        self.assertIn("OrderSend(request,result)", source)


if __name__ == "__main__":
    unittest.main()
