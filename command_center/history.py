"""Persist actual broker-observed equity samples outside Git."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def sample(path: Path, observed_utc: str | None, equity: float | None,
           verified: bool, limit: int = 1440) -> list[dict]:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=3)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS equity_samples (minute TEXT PRIMARY KEY, observed_utc TEXT NOT NULL, equity REAL NOT NULL)")
        if verified and observed_utc and equity is not None:
            # Sampling is timestamped from the service snapshot, not this HTTP
            # request. One observation per UTC minute; no interpolation.
            minute = datetime.fromisoformat(observed_utc).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M")
            db.execute("INSERT OR IGNORE INTO equity_samples VALUES (?,?,?)",
                       (minute, observed_utc, float(equity)))
            db.commit()
        rows = db.execute("SELECT observed_utc,equity FROM equity_samples ORDER BY minute DESC LIMIT ?",
                          (min(max(limit, 1), 10000),)).fetchall()
        return [{"time": t, "value": v} for t, v in reversed(rows)]
    finally:
        db.close()
