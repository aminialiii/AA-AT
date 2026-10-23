"""Authenticated, loopback-only AA AT DEMO command center.

Run ``python -m command_center.server --init-auth`` once, then ``--serve``.
The dashboard never imports MetaTrader or submits orders. Worker commands are
durable requests handled by the campaign's broker-verified control bridge.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from command_center.telemetry import snapshot, worker_logs
from command_center.history import sample as equity_sample

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT.parent / "research/demo-live-20261021"
# The web process uses the reviewed protocol code from its own release.  It
# never imports Python modules from the mutable trading runtime.
sys.path.insert(0, str(ROOT / "research/demo-live-20261021"))
from worker_control import ACTIONS, ControlError, ControlStore, WORKER_IDS  # noqa: E402

STATE = ROOT.parent / "AA-AT-command-center-state"
RUNTIME = ORIGINAL / "runtime"
PORT = 8765


def initialize_auth(state: Path) -> dict:
    state.mkdir(parents=True, exist_ok=True)
    path = state / "auth_hashes.json"
    keys = state / "access_keys.txt"
    if path.exists() or keys.exists():
        raise RuntimeError("authentication_already_initialized")
    tokens = {role: secrets.token_urlsafe(36) for role in ("viewer", "operator", "admin")}
    path.write_text(json.dumps({role: hashlib.sha256(token.encode()).hexdigest()
                                for role, token in tokens.items()}, indent=2), encoding="utf-8")
    keys.write_text("AA AT local dashboard tokens. Keep private.\n" +
                    "\n".join(f"{role}: {token}" for role, token in tokens.items()) + "\n",
                    encoding="utf-8")
    os.chmod(path, 0o600)
    os.chmod(keys, 0o600)
    return {"auth_file": str(path), "access_key_file": str(keys)}


class Auth:
    def __init__(self, state: Path):
        self.hashes = json.loads((state / "auth_hashes.json").read_text(encoding="utf-8"))

    def role(self, header: str | None) -> str | None:
        if not header or not header.startswith("Bearer "):
            return None
        token = header[7:]
        if len(token) > 256:
            return None
        digest = hashlib.sha256(token.encode()).hexdigest()
        for role, expected in self.hashes.items():
            if hmac.compare_digest(digest, expected):
                return role
        return None


class RateLimiter:
    def __init__(self):
        self._lock = threading.Lock()
        self._events = defaultdict(deque)

    def allow(self, principal: str, *, limit: int = 30, window: int = 60) -> bool:
        with self._lock:
            q = self._events[principal]
            now = time.monotonic()
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True


class App:
    def __init__(self, repo: Path = ROOT, runtime: Path = RUNTIME, state: Path = STATE):
        self.repo, self.runtime, self.state = repo, runtime, state
        self.auth = Auth(state)
        self.rate = RateLimiter()

    def store(self):
        # Commands are separate from the broker ledger and trading runtime.
        return ControlStore(self.state / "commands.sqlite3")

    def telemetry(self):
        store = self.store()
        try:
            data = snapshot(self.runtime, self.repo, store)
            data["equity_curve"] = equity_sample(
                self.state / "equity_samples.sqlite3", data["observed_utc"],
                data["portfolio"]["equity"], data["demo_verified"])
            return data
        finally:
            store.db.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "AAATCommandCenter/1"

    @property
    def app(self) -> App:
        return self.server.app

    def log_message(self, fmt, *args):
        # Do not log bearer tokens or request bodies. Structured command audit is
        # stored separately in SQLite; ordinary polling remains quiet.
        pass

    def send_json(self, code: int, value: dict | list):
        data = json.dumps(value, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _role(self, minimum="viewer"):
        role = self.app.auth.role(self.headers.get("Authorization"))
        ranks = {"viewer": 1, "operator": 2, "admin": 3}
        if ranks.get(role, 0) < ranks[minimum]:
            self.send_json(403 if role else 401, {"error": "access_denied"})
            return None
        return role

    def _host_ok(self):
        host = self.headers.get("Host", "")
        return host in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

    def _origin_ok(self):
        origin = self.headers.get("Origin")
        return not origin or origin in {f"http://127.0.0.1:{self.server.server_port}",
                                        f"http://localhost:{self.server.server_port}"}

    def _static(self, path: Path, content_type: str):
        if not path.is_file():
            return self.send_json(404, {"error": "not_found"})
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if not self._host_ok():
            return self.send_json(400, {"error": "invalid_host"})
        path = urlparse(self.path).path
        if path == "/health":
            return self.send_json(200, {"service": "AA-AT-command-center", "status": "RUNNING",
                                        "utc": datetime.now(timezone.utc).isoformat()})
        if path in {"/", "/index.html"}:
            return self._static(self.app.repo / "docs/dashboard.html", "text/html; charset=utf-8")
        if path == "/assets/app.css":
            return self._static(self.app.repo / "docs/assets/app.css", "text/css; charset=utf-8")
        if path == "/assets/app.js":
            return self._static(self.app.repo / "docs/assets/app.js", "application/javascript; charset=utf-8")
        if path == "/graph.html":
            return self._static(self.app.repo / "graphify-out/graph.html", "text/html; charset=utf-8")
        if path == "/api/status":
            role = self._role()
            if not role:
                return
            try:
                data = self.app.telemetry()
                data["auth_role"] = role
                return self.send_json(200, data)
            except (OSError, ValueError, RuntimeError, sqlite3.DatabaseError) as exc:
                return self.send_json(503, {"error": "telemetry_unavailable", "detail": str(exc)[:160]})
        match = re.fullmatch(r"/api/workers/(S(?:0[1-9]|1[0-8]))/logs", path)
        if match:
            if not self._role():
                return
            return self.send_json(200, {"worker": match.group(1),
                                        "logs": worker_logs(self.app.runtime, match.group(1))})
        if path == "/api/events":
            role = self._role()
            if not role:
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            for _ in range(60):
                try:
                    data = self.app.telemetry()
                    data["auth_role"] = role
                    data = json.dumps(data, separators=(",", ":"), default=str)
                    self.wfile.write(f"event: snapshot\ndata: {data}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(5)
                except (BrokenPipeError, ConnectionResetError):
                    break
                except Exception as exc:
                    try:
                        self.wfile.write(f"event: error\ndata: {json.dumps({'error': str(exc)[:120]})}\n\n".encode())
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    time.sleep(5)
            return
        return self.send_json(404, {"error": "not_found"})

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            return self.send_json(403, {"error": "invalid_origin_or_host"})
        path = urlparse(self.path).path
        required = "admin" if path == "/api/emergency-stop" else "operator"
        role = self._role(required)
        if not role:
            return
        if not self.app.rate.allow(self.headers.get("Authorization", "")):
            return self.send_json(429, {"error": "rate_limited"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send_json(415, {"error": "json_required"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 <= size <= 4096:
                raise ValueError("body_too_large")
            body = json.loads(self.rfile.read(size) or b"{}")
            key = self.headers.get("X-Idempotency-Key", "")
            current = self.app.telemetry()
            if not current["control_bridge"]:
                return self.send_json(503, {"error": "control_bridge_not_operational"})
            if current["emergency_stop"] and path != "/api/emergency-stop":
                return self.send_json(423, {"error": "emergency_stop_active"})
            store = self.app.store()
            try:
                if path == "/api/emergency-stop":
                    response = store.stop_emergency(role, key)
                elif path == "/api/bulk":
                    action = body.get("action", "").upper()
                    ids = body.get("workers", [])
                    if not isinstance(ids, list):
                        raise ControlError("invalid_bulk_selection")
                    if action not in {"PAUSE", "STOP", "START", "RESUME", "RESTART"}:
                        raise ControlError("invalid_action")
                    if action not in {"PAUSE", "STOP"} and not current["demo_verified"]:
                        raise ControlError("broker_demo_not_verified")
                    blocked = {w["id"] for w in current["workers"] if w["status"] == "BLOCKED"}
                    response = store.submit_bulk(role, ids, action, key, blocked)
                else:
                    parts = path.split("/")
                    if len(parts) != 5 or parts[:3] != ["", "api", "workers"]:
                        return self.send_json(404, {"error": "not_found"})
                    sid, action = parts[3], parts[4].upper()
                    if sid not in WORKER_IDS or action not in ACTIONS:
                        raise ControlError("invalid_command")
                    if action not in {"PAUSE", "STOP"} and not current["demo_verified"]:
                        raise ControlError("broker_demo_not_verified")
                    blocked = next((w["status"] == "BLOCKED" for w in current["workers"] if w["id"] == sid), True)
                    response = store.submit(role, sid, action, key, blocked)
            finally:
                store.db.close()
            return self.send_json(202, {"command": response})
        except (ValueError, ControlError, KeyError, TypeError) as exc:
            return self.send_json(400, {"error": str(exc)[:160]})
        except sqlite3.DatabaseError as exc:
            return self.send_json(503, {"error": "control_store_unavailable", "detail": str(exc)[:120]})


def serve(port: int = PORT):
    app = App()
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    server.app = app
    server.serve_forever(poll_interval=0.5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--init-auth", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    if args.init_auth:
        print(json.dumps(initialize_auth(STATE)))
        return
    if not args.serve or not 1024 <= args.port <= 65535:
        parser.error("use --serve [--port PORT] or --init-auth")
    serve(args.port)


if __name__ == "__main__":
    main()
