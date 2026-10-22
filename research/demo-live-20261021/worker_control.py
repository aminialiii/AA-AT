"""Local, durable control channel for the DEMO campaign.

No broker API is imported here. The same SQLite write transaction serializes a
control change with an in-flight order admission. A successful emergency-stop
response therefore means no later admission can pass the latch.
"""
from __future__ import annotations

import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

WORKER_IDS = frozenset(f"S{i:02d}" for i in range(1, 19))
ACTIONS = frozenset({"START", "PAUSE", "RESUME", "RESTART", "STOP"})
DISABLE_ACTIONS = frozenset({"PAUSE", "STOP"})
KEY_RE = re.compile(r"^[A-Za-z0-9_.:-]{12,128}$")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def persistent_risk_breakers(campaign_db: sqlite3.Connection, worker_ids) -> dict[str, str]:
    """Restore fill-risk breaches that require explicit review after restart."""
    result = {}
    for scope, reason in campaign_db.execute(
            "SELECT scope,reason FROM safety_events "
            "WHERE reason LIKE 'filled_price_risk_exceeds_cap%' ORDER BY observed_utc"):
        if scope in worker_ids:
            result[scope] = reason
    return result


class ControlError(ValueError):
    pass


class ControlStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA busy_timeout=10000")
        self.db.execute("PRAGMA synchronous=FULL")
        initialized = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='commands'").fetchone()
        if not initialized:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.executescript("""
        CREATE TABLE IF NOT EXISTS commands (
          id TEXT PRIMARY KEY, idempotency_key TEXT NOT NULL UNIQUE,
          actor TEXT NOT NULL, worker_id TEXT, action TEXT NOT NULL,
          status TEXT NOT NULL, result TEXT, created_utc TEXT NOT NULL,
          updated_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS worker_modes (
          worker_id TEXT PRIMARY KEY, mode TEXT NOT NULL, updated_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS flags (
          key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS audit (
          id TEXT PRIMARY KEY, utc TEXT NOT NULL, actor TEXT NOT NULL,
          action TEXT NOT NULL, worker_id TEXT, detail TEXT NOT NULL);
            """)

    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    @contextmanager
    def admission(self):
        """Hold across a single route and its broker submission."""
        with self.transaction():
            yield

    def mode(self, worker_id: str) -> str:
        row = self.db.execute("SELECT mode FROM worker_modes WHERE worker_id=?", (worker_id,)).fetchone()
        return row[0] if row else "RUNNING"

    def emergency(self) -> bool:
        row = self.db.execute("SELECT value FROM flags WHERE key='emergency_stop'").fetchone()
        return bool(row and row[0] == "1")

    def _audit(self, actor: str, action: str, worker_id: str | None, detail: str):
        self.db.execute("INSERT INTO audit VALUES (?,?,?,?,?,?)",
                        (uuid.uuid4().hex, utc(), actor, action, worker_id, detail))

    def _submit_locked(self, actor: str, worker_id: str, action: str, key: str,
                       blocked: bool = False) -> dict:
        if worker_id not in WORKER_IDS or action not in ACTIONS or not KEY_RE.fullmatch(key):
            raise ControlError("invalid_command")
        prior = self.db.execute("SELECT * FROM commands WHERE idempotency_key=?", (key,)).fetchone()
        if prior:
            if prior["worker_id"] != worker_id or prior["action"] != action:
                raise ControlError("idempotency_key_reused_for_different_command")
            return dict(prior)
        if blocked and action not in DISABLE_ACTIONS:
            raise ControlError("worker_blocked")
        if self.emergency() and action not in DISABLE_ACTIONS:
            raise ControlError("emergency_stop_active")
        current = self.mode(worker_id)
        if action == "START" and current != "STOPPED":
            raise ControlError("start_requires_stopped_worker")
        if action == "RESUME" and current != "PAUSED":
            raise ControlError("resume_requires_paused_worker")
        if action == "PAUSE" and current == "STOPPED":
            raise ControlError("worker_already_stopped")
        command_id = uuid.uuid4().hex
        now = utc()
        self.db.execute("INSERT INTO commands VALUES (?,?,?,?,?,?,?,?,?)",
                        (command_id, key, actor, worker_id, action, "PENDING", None, now, now))
        if action in DISABLE_ACTIONS:
            mode = "PAUSED" if action == "PAUSE" else "STOPPED"
            self.db.execute("INSERT INTO worker_modes VALUES (?,?,?) ON CONFLICT(worker_id) "
                            "DO UPDATE SET mode=excluded.mode,updated_utc=excluded.updated_utc",
                            (worker_id, mode, now))
        self._audit(actor, "REQUEST_" + action, worker_id, command_id)
        return dict(self.db.execute("SELECT * FROM commands WHERE id=?", (command_id,)).fetchone())

    def submit(self, actor: str, worker_id: str, action: str, key: str,
               blocked: bool = False) -> dict:
        with self.transaction():
            return self._submit_locked(actor, worker_id, action, key, blocked)

    def submit_bulk(self, actor: str, worker_ids: list[str], action: str, key: str,
                    blocked_ids: set[str]) -> list[dict]:
        if not worker_ids or len(worker_ids) > 18 or len(set(worker_ids)) != len(worker_ids):
            raise ControlError("invalid_bulk_selection")
        if not KEY_RE.fullmatch(key):
            raise ControlError("invalid_idempotency_key")
        # Validate the full batch before committing any command.
        for sid in worker_ids:
            if sid not in WORKER_IDS or (sid in blocked_ids and action not in DISABLE_ACTIONS):
                raise ControlError("invalid_or_blocked_worker_in_batch")
        with self.transaction():
            return [self._submit_locked(actor, sid, action, f"{key}:{sid}", sid in blocked_ids)
                    for sid in worker_ids]

    def stop_emergency(self, actor: str, key: str) -> dict:
        if not KEY_RE.fullmatch(key):
            raise ControlError("invalid_idempotency_key")
        with self.transaction():
            prior = self.db.execute("SELECT * FROM commands WHERE idempotency_key=?", (key,)).fetchone()
            if prior:
                if prior["action"] != "EMERGENCY_STOP":
                    raise ControlError("idempotency_key_reused_for_different_command")
                return dict(prior)
            now = utc()
            command_id = uuid.uuid4().hex
            self.db.execute("INSERT INTO flags VALUES ('emergency_stop','1',?) ON CONFLICT(key) "
                            "DO UPDATE SET value='1',updated_utc=excluded.updated_utc", (now,))
            self.db.execute("INSERT INTO commands VALUES (?,?,?,?,?,?,?,?,?)",
                            (command_id, key, actor, None, "EMERGENCY_STOP", "PENDING", None, now, now))
            self._audit(actor, "REQUEST_EMERGENCY_STOP", None, command_id)
            return dict(self.db.execute("SELECT * FROM commands WHERE id=?", (command_id,)).fetchone())

    def pending(self) -> list[dict]:
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM commands WHERE status='PENDING' ORDER BY created_utc,id LIMIT 50")]

    def complete(self, command_id: str, status: str, result: str):
        if status not in {"APPLIED", "REJECTED"}:
            raise ValueError("invalid_command_status")
        with self.transaction():
            row = self.db.execute("SELECT * FROM commands WHERE id=?", (command_id,)).fetchone()
            if not row or row["status"] != "PENDING":
                return
            self.db.execute("UPDATE commands SET status=?,result=?,updated_utc=? WHERE id=?",
                            (status, result[:500], utc(), command_id))
            self._audit("service", status + "_" + row["action"], row["worker_id"], result[:500])

    def set_mode(self, worker_id: str, mode: str):
        if worker_id not in WORKER_IDS or mode not in {"RUNNING", "PAUSED", "STOPPED"}:
            raise ValueError("invalid_mode")
        with self.transaction():
            self.db.execute("INSERT INTO worker_modes VALUES (?,?,?) ON CONFLICT(worker_id) "
                            "DO UPDATE SET mode=excluded.mode,updated_utc=excluded.updated_utc",
                            (worker_id, mode, utc()))

    def recent(self, limit: int = 30) -> list[dict]:
        return [dict(row) for row in self.db.execute(
            "SELECT * FROM commands ORDER BY created_utc DESC,id DESC LIMIT ?", (min(100, limit),))]

    def audit_recent(self, limit: int = 30) -> list[dict]:
        return [dict(row) for row in self.db.execute(
            "SELECT utc,actor,action,worker_id,detail FROM audit ORDER BY utc DESC,id DESC LIMIT ?",
            (min(100, limit),))]
