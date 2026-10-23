"""Offline command-path tests; never import MetaTrader or touch the campaign ledger."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "research/demo-live-20261021"))
from worker_control import ControlError, ControlStore, persistent_risk_breakers
from command_center.server import App, Handler, RateLimiter
from command_center.history import sample
from command_center.telemetry import ledger, snapshot


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "controls.sqlite3"
        self.store = ControlStore(self.path)
        self.addCleanup(self.store.db.close)

    def test_pause_stop_start_resume_and_idempotency(self):
        paused = self.store.submit("operator", "S01", "PAUSE", "pause-command-001")
        self.assertEqual(self.store.mode("S01"), "PAUSED")
        self.assertEqual(self.store.submit("operator", "S01", "PAUSE", "pause-command-001")["id"], paused["id"])
        self.store.complete(paused["id"], "APPLIED", "admission_disabled")
        self.store.submit("operator", "S01", "RESUME", "resume-command-001")
        self.assertEqual(self.store.mode("S01"), "PAUSED")  # service must verify before enabling
        self.store.set_mode("S01", "RUNNING")  # service acknowledgment after mocked checks
        self.store.submit("operator", "S01", "STOP", "stop-command-001")
        self.assertEqual(self.store.mode("S01"), "STOPPED")
        self.store.submit("operator", "S01", "START", "start-command-001")
        self.assertEqual(self.store.mode("S01"), "STOPPED")

    def test_blocked_and_bulk_rollback(self):
        with self.assertRaises(ControlError):
            self.store.submit("operator", "S06", "RESTART", "blocked-command-001", blocked=True)
        self.store.set_mode("S02", "STOPPED")
        with self.assertRaises(ControlError):
            self.store.submit_bulk("operator", ["S01", "S02"], "PAUSE", "bulk-command-001", set())
        self.assertEqual(self.store.mode("S01"), "RUNNING")
        self.assertEqual(len(self.store.recent()), 0)

    def test_emergency_waits_for_inflight_admission(self):
        entered, release, finished = threading.Event(), threading.Event(), threading.Event()
        def route():
            store = ControlStore(self.path)
            with store.admission():
                self.assertFalse(store.emergency())
                entered.set()
                self.assertTrue(release.wait(3))
            store.db.close()
        def halt():
            store = ControlStore(self.path)
            store.stop_emergency("admin", "emergency-command-001")
            finished.set()
            store.db.close()
        a = threading.Thread(target=route); b = threading.Thread(target=halt)
        a.start(); self.assertTrue(entered.wait(3)); b.start()
        time.sleep(.1)
        self.assertFalse(finished.is_set())
        release.set(); a.join(3); b.join(3)
        self.assertTrue(finished.is_set())
        self.assertTrue(self.store.emergency())
        with self.assertRaises(ControlError):
            self.store.submit("operator", "S01", "RESTART", "post-stop-command-001")

    def test_rate_limit(self):
        rate = RateLimiter()
        self.assertTrue(rate.allow("x", limit=2))
        self.assertTrue(rate.allow("x", limit=2))
        self.assertFalse(rate.allow("x", limit=2))

    def test_filled_risk_breach_remains_blocked_after_restart(self):
        db = sqlite3.connect(":memory:")
        db.execute("CREATE TABLE safety_events(scope TEXT, reason TEXT, observed_utc TEXT)")
        db.execute("INSERT INTO safety_events VALUES ('S02','worker_suspended:temporary','2026-10-22T00:00:00Z')")
        db.execute("INSERT INTO safety_events VALUES ('S04','filled_price_risk_exceeds_cap; protective broker SL/TP retained','2026-10-22T01:00:00Z')")
        self.assertEqual(persistent_risk_breakers(db, {"S02", "S04"}),
                         {"S04": "filled_price_risk_exceeds_cap; protective broker SL/TP retained"})
        db.close()

    def test_reconciled_win_rate_and_pnl_curve(self):
        runtime = Path(self.temp.name)
        db = sqlite3.connect(runtime / "campaign.sqlite3")
        db.execute("CREATE TABLE closed(position_id INTEGER,strategy TEXT,record_json TEXT,closed_utc TEXT)")
        db.execute("CREATE TABLE intents(state TEXT)")
        db.execute("CREATE TABLE safety_events(observed_utc TEXT,scope TEXT,reason TEXT)")
        today = datetime.now(timezone.utc).date().isoformat()
        for number, pnl in enumerate((2.0, -1.0), start=1):
            record = {"execution_kind": "REAL_TIME_DEMO_BROKER", "account_trade_mode": "DEMO",
                      "fully_closed": True, "broker_net_profit": pnl, "initial_risk_account_currency": 1.0,
                      "symbol": "EURUSD", "entry_utc": f"{today}T00:00:00+00:00",
                      "exit_utc": f"{today}T00:0{number}:00+00:00"}
            db.execute("INSERT INTO closed VALUES (?,?,?,?)", (number, "S01", json.dumps(record), record["exit_utc"]))
        db.commit(); db.close()
        result = ledger(runtime)
        self.assertEqual(result["closed_count"], 2)
        self.assertEqual(result["win_rate"], .5)
        self.assertEqual(result["daily_closed_pnl"], 1.0)
        self.assertEqual(result["curve"][-1]["value"], 1.0)
        self.assertEqual(result["realized_pnl"], 1.0)
        self.assertEqual(result["by_strategy"]["S01"]["closed"], 2)

    def test_equity_history_uses_only_verified_observations(self):
        path = Path(self.temp.name) / "equity.sqlite3"
        observed = datetime.now(timezone.utc).isoformat()
        self.assertEqual(sample(path, observed, 101.0, False), [])
        self.assertEqual(len(sample(path, observed, 101.0, True)), 1)
        self.assertEqual(len(sample(path, observed, 102.0, True)), 1)  # same minute: no fabricated sample


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.repo, self.runtime, self.state = base / "AA-AT", base / "runtime", base / "auth"
        for path in (self.repo, self.runtime, self.state): path.mkdir()
        now = datetime.now(timezone.utc).isoformat()
        self.status = {"observed_utc": now, "broker_status": "HEALTHY", "demo_verified": True,
                       "control_bridge_version": 1, "active_positions": 0, "pending_orders": 0,
                       "max_positions_portfolio": 5, "max_open_risk_fraction": .02,
                       "realized_demo_pnl": 0, "workers": [
                           {"id": "S01", "name": "One", "status": "ACTIVE", "closed_trades": 0},
                           {"id": "S06", "name": "Six", "status": "BLOCKED", "closed_trades": 0,
                            "reason": "unverified adapter"}]}
        (self.runtime / "status.json").write_text(json.dumps(self.status))
        db = sqlite3.connect(self.runtime / "campaign.sqlite3")
        db.execute("CREATE TABLE closed(position_id INTEGER,strategy TEXT,record_json TEXT,closed_utc TEXT)")
        db.execute("CREATE TABLE intents(state TEXT)")
        db.execute("CREATE TABLE safety_events(observed_utc TEXT,scope TEXT,reason TEXT)")
        db.commit(); db.close()
        self.tokens = {"viewer": "view-test-token", "operator": "operator-test-token", "admin": "admin-test-token"}
        (self.state / "auth_hashes.json").write_text(json.dumps(
            {k: hashlib.sha256(v.encode()).hexdigest() for k, v in self.tokens.items()}))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.server.app = App(self.repo, self.runtime, self.state)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.base_url = f"http://127.0.0.1:{self.server.server_port}"
        self.opener = build_opener(ProxyHandler({}))

    def request(self, path, role=None, body=None, key="api-command-001", origin=None):
        headers = {}
        if role: headers["Authorization"] = f"Bearer {self.tokens[role]}"
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["X-Idempotency-Key"] = key
            if origin: headers["Origin"] = origin
        req = Request(self.base_url + path, data=json.dumps(body).encode() if body is not None else None,
                      headers=headers, method="POST" if body is not None else "GET")
        try:
            with self.opener.open(req, timeout=3) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            with exc:
                return exc.code, json.load(exc)

    def test_auth_controls_blocked_and_duplicate(self):
        self.assertEqual(self.request("/api/status")[0], 401)
        self.assertEqual(self.request("/api/status", "viewer")[0], 200)
        self.assertEqual(self.request("/api/workers/S01/logs", "viewer")[0], 200)
        self.assertEqual(self.request("/api/workers/S01/pause", "viewer", {})[0], 403)
        self.assertEqual(self.request("/api/workers/S01/pause", "operator", {}, origin="http://evil.invalid")[0], 403)
        status, first = self.request("/api/workers/S01/pause", "operator", {})
        self.assertEqual(status, 202)
        self.assertTrue((self.state / "commands.sqlite3").exists())
        self.assertFalse((self.runtime / "command_center.sqlite3").exists())
        status, second = self.request("/api/workers/S01/pause", "operator", {})
        self.assertEqual(status, 202)
        self.assertEqual(first["command"]["id"], second["command"]["id"])
        self.assertEqual(self.request("/api/workers/S06/restart", "operator", {}, key="api-command-002")[0], 400)
        self.assertEqual(self.request("/api/emergency-stop", "operator", {}, key="api-command-003")[0], 403)
        self.assertEqual(self.request("/api/emergency-stop", "admin", {}, key="api-command-004")[0], 202)
        self.assertTrue(self.request("/api/status", "viewer")[1]["emergency_stop"])

    def test_stale_feed_disables_control_and_exposure(self):
        self.status["observed_utc"] = "2020-01-01T00:00:00+00:00"
        self.status["active_positions"] = 3
        (self.runtime / "status.json").write_text(json.dumps(self.status))
        d = self.request("/api/status", "viewer")[1]
        self.assertTrue(d["stale"])
        self.assertEqual(d["broker_status"], "STALE")
        self.assertEqual(d["portfolio"]["active_workers"], 0)
        self.assertEqual(d["workers"][0]["status"], "STALE")
        self.assertIsNone(d["portfolio"]["open_positions"])
        self.assertEqual(self.request("/api/workers/S01/pause", "operator", {})[0], 503)

    def test_local_stop_and_persistent_fill_risk_breaker_fail_closed(self):
        self.status["workers"].insert(1, {"id": "S04", "name": "Four",
                                             "status": "ACTIVE", "closed_trades": 97})
        (self.runtime / "status.json").write_text(json.dumps(self.status))
        db = sqlite3.connect(self.runtime / "campaign.sqlite3")
        db.execute("INSERT INTO safety_events VALUES (?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), "S04",
                    "filled_price_risk_exceeds_cap; protective broker SL/TP retained"))
        db.commit(); db.close()
        d = self.request("/api/status", "viewer")[1]
        self.assertEqual(next(w for w in d["workers"] if w["id"] == "S04")["status"], "BLOCKED")
        self.assertEqual(self.request("/api/workers/S04/restart", "operator", {})[0], 400)
        (self.runtime / "EMERGENCY_STOP").write_text("maintenance\n")
        d = self.request("/api/status", "viewer")[1]
        self.assertTrue(d["emergency_stop"])
        self.assertFalse(d["control_bridge"])
        self.assertEqual(d["portfolio"]["active_workers"], 0)
        self.assertEqual(next(w for w in d["workers"] if w["id"] == "S01")["status"],
                         "HALTED_BY_SAFETY_STOP")
        self.assertEqual(self.request("/api/workers/S01/start", "operator", {})[0], 503)


if __name__ == "__main__":
    unittest.main()
