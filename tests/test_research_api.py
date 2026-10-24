"""Research and backup HTTP projections use isolated test stores only."""
import json
import hashlib
import tempfile
import threading
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

from command_center import research_api
from command_center.server import App, Handler
from research.trade_forensics.store import Warehouse


class ResearchApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / "research"
        self.store = Warehouse(self.state)
        self.addCleanup(self.store.close)

    def test_empty_warehouse_does_not_invent_trades_or_market_data(self):
        self.assertEqual(research_api.list_trades("limit=10", self.state)["total"], 0)
        quality = research_api.quality(self.state)
        self.assertEqual((quality["trades"], quality["market_bars"],
                          quality["market_ticks"]), (0, 0, 0))
        self.assertTrue(research_api.research_status(self.state)["stale"])

    def test_invalid_filters_and_trade_ids_fail_closed(self):
        for query in ("strategy=S99", "limit=1001", "symbol=EURUSD%27",
                      "start_utc=2026-10-23", "unknown=x"):
            with self.subTest(query=query), self.assertRaises(ValueError):
                research_api.list_trades(query, self.state)
        with self.assertRaises(ValueError):
            research_api.trade_detail("../secrets", self.state)
        with self.assertRaises(RuntimeError):
            research_api.priority3_analysis(self.state)

    def test_versioned_analysis_pointer_stays_within_research_state(self):
        directory = self.state / "analytics" / "runs" / ("a" * 20)
        directory.mkdir(parents=True)
        (directory / "priority3.json").write_text(json.dumps({
            "analysis_run_id": "a" * 20, "evidence_class": "BROKER_ACTUAL"}))
        (self.state / "analytics" / "latest.json").write_text(json.dumps({
            "analysis_run_id": "a" * 20}))
        self.assertEqual(research_api.priority3_analysis(self.state)["evidence_class"],
                         "BROKER_ACTUAL")
        (self.state / "analytics" / "latest.json").write_text(json.dumps({
            "analysis_run_id": "../../bad"}))
        with self.assertRaises(RuntimeError):
            research_api.priority3_analysis(self.state)

    def test_backup_request_is_idempotent_and_status_marks_stale_worker(self):
        backups = self.root / "backups"
        backups.mkdir()
        first = research_api.request_backup("backup-test-0001", "admin", backups)
        second = research_api.request_backup("backup-test-0001", "admin", backups)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(first["state"], "PENDING")
        status = research_api.backup_status(backups)
        self.assertTrue(status["worker_stale"])
        self.assertFalse(status["restore_from_dashboard_allowed"])
        (backups / "backup-heartbeat.json").write_text(json.dumps({
            "observed_utc": datetime.now(timezone.utc).isoformat()}))
        self.assertFalse(research_api.backup_status(backups)["worker_stale"])

    def test_http_research_auth_and_admin_backup_queue(self):
        auth = self.root / "auth"
        auth.mkdir()
        (auth / "auth_hashes.json").write_text(json.dumps({
            "viewer": hashlib.sha256(b"fixture-viewer").hexdigest(),
            "admin": hashlib.sha256(b"fixture-admin").hexdigest(),
        }))
        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        server.daemon_threads = True
        server.app = App(self.root, self.root / "runtime", auth)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        opener = build_opener(ProxyHandler({}))
        base = f"http://127.0.0.1:{server.server_port}"

        def request(path, token=None, body=None):
            headers = {"Authorization": f"Bearer {token}"} if token else {}
            if body is not None:
                headers.update({"Content-Type": "application/json",
                                "X-Idempotency-Key": "backup-test-0001"})
            value = Request(base + path, headers=headers,
                            data=json.dumps(body).encode() if body is not None else None)
            try:
                with opener.open(value, timeout=3) as response:
                    return response.status, json.load(response)
            except HTTPError as exc:
                with exc:
                    return exc.code, json.load(exc)

        with patch.object(research_api, "quality", return_value={"trades": 0}), \
             patch.object(research_api, "priority3_analysis",
                          return_value={"analysis_run_id": "fixture"}), \
             patch.object(research_api, "request_backup",
                          return_value={"id": "backup-test-0001", "state": "PENDING"}) as queue:
            self.assertEqual(request("/api/research/quality")[0], 401)
            self.assertEqual(request("/api/research/quality", "fixture-viewer"),
                             (200, {"trades": 0}))
            self.assertEqual(request("/api/research/analysis")[0], 401)
            self.assertEqual(request("/api/research/analysis", "fixture-viewer"),
                             (200, {"analysis_run_id": "fixture"}))
            self.assertEqual(request("/api/backups/requests", "fixture-viewer", {})[0], 403)
            self.assertEqual(request("/api/backups/requests", "fixture-admin", {})[0], 202)
            queue.assert_called_once_with("backup-test-0001", "admin")


if __name__ == "__main__":
    unittest.main()
