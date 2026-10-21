"""Durable intent journal and append-only broker evidence for the DEMO campaign."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path


def utc():
    return datetime.now(timezone.utc).isoformat()


class State:
    def __init__(self, base: Path, config_hash: str):
        self.base = base
        self.base.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(base / "campaign.sqlite3", isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS cursor(strategy TEXT NOT NULL, symbol TEXT NOT NULL,
                bar INTEGER NOT NULL, PRIMARY KEY(strategy,symbol));
            CREATE TABLE IF NOT EXISTS intents(
                signal_key TEXT PRIMARY KEY, strategy TEXT NOT NULL, symbol TEXT NOT NULL,
                magic INTEGER NOT NULL, bar INTEGER NOT NULL, request_json TEXT NOT NULL,
                planned_risk REAL NOT NULL, state TEXT NOT NULL, created_utc TEXT NOT NULL,
                broker_order INTEGER, broker_deal INTEGER, position_id INTEGER, result_json TEXT);
            CREATE TABLE IF NOT EXISTS closed(
                position_id INTEGER PRIMARY KEY, strategy TEXT NOT NULL, signal_key TEXT NOT NULL,
                record_json TEXT NOT NULL, closed_utc TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS safety_events(
                id TEXT PRIMARY KEY, observed_utc TEXT NOT NULL, scope TEXT NOT NULL,
                reason TEXT NOT NULL);
        """)
        old = self.get("config_sha256")
        if old is not None and old != config_hash:
            self.db.close()
            raise RuntimeError("frozen_campaign_config_changed")
        self.put("config_sha256", config_hash)

    def get(self, key, default=None):
        row = self.db.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self, key, value):
        self.db.execute("INSERT INTO meta(k,v) VALUES (?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (key, json.dumps(value)))

    def cursor(self, strategy, symbol):
        row = self.db.execute("SELECT bar FROM cursor WHERE strategy=? AND symbol=?", (strategy,symbol)).fetchone()
        return int(row[0]) if row else None

    def advance(self, strategy, symbol, bar):
        self.db.execute("INSERT INTO cursor(strategy,symbol,bar) VALUES (?,?,?) ON CONFLICT(strategy,symbol) DO UPDATE SET bar=MAX(cursor.bar,excluded.bar)", (strategy,symbol,bar))

    def evidence(self, strategy, kind, payload):
        if strategy not in {f"S{i:02d}" for i in range(1,19)} and strategy != "SYSTEM":
            raise ValueError("unknown evidence owner")
        folder = self.base / "evidence" / strategy
        folder.mkdir(parents=True, exist_ok=True)
        record = {"utc": utc(), "strategy": strategy, "kind": kind,
                  "config_sha256": self.get("config_sha256"), "payload": payload}
        raw = (json.dumps(record, sort_keys=True, separators=(",", ":"), default=str) + "\n").encode()
        name = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S%fZ}_{uuid.uuid4().hex}.json"
        path = folder / name
        with path.open("xb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest()}

    def event(self, scope, reason):
        event_id = uuid.uuid4().hex
        self.db.execute("INSERT INTO safety_events VALUES (?,?,?,?)", (event_id, utc(), scope, reason))
        self.evidence("SYSTEM", "SAFETY_EVENT", {"id":event_id,"scope":scope,"reason":reason})

    def prepare(self, key, strategy, symbol, magic, bar, request, planned_risk):
        self.db.execute("INSERT INTO intents(signal_key,strategy,symbol,magic,bar,request_json,planned_risk,state,created_utc) VALUES (?,?,?,?,?,?,?,?,?)",
                        (key,strategy,symbol,magic,bar,json.dumps(request,sort_keys=True),planned_risk,"PREPARED",utc()))
        self.evidence(strategy, "INTENT_PREPARED", {"signal_key":key,"request":request,"planned_risk":planned_risk})

    def mark_sent(self, key, result, position_id):
        self.db.execute("UPDATE intents SET state='OPEN',broker_order=?,broker_deal=?,position_id=?,result_json=? WHERE signal_key=? AND state='PREPARED'",
                        (int(result.order),int(result.deal),int(position_id),json.dumps(result._asdict(),default=str),key))

    def mark_closed(self, position_id, strategy, key, record):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute("INSERT INTO closed VALUES (?,?,?,?,?)", (position_id,strategy,key,json.dumps(record,sort_keys=True),utc()))
            self.db.execute("UPDATE intents SET state='CLOSED' WHERE signal_key=?", (key,))
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def outstanding(self):
        return self.db.execute("SELECT * FROM intents WHERE state!='CLOSED'").fetchall()

    def open_for_position(self, ticket):
        return self.db.execute("SELECT * FROM intents WHERE position_id=? AND state='OPEN'", (int(ticket),)).fetchone()

    def open_for_strategy(self, strategy):
        return self.db.execute("SELECT * FROM intents WHERE strategy=? AND state IN ('PREPARED','OPEN')", (strategy,)).fetchall()

    def count_closed(self, strategy):
        return self.db.execute("SELECT COUNT(*) FROM closed WHERE strategy=?", (strategy,)).fetchone()[0]
