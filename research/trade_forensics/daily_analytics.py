"""One-shot daily analytics job independent of trading and dashboard services."""
from __future__ import annotations

import argparse
import json
import os
import hashlib
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .priority3 import run
from .charts import MarketDataUnavailable, chart
from .store import Warehouse

DEFAULT_STATE = Path(r"E:\GPT\Inves\AA-AT-research-state")
DEFAULT_BACKUPS = Path(r"D:\AA-AT-Backups")


def build_pending_charts(state: Path, max_charts: int = 10) -> dict:
    """Bounded, source-change-aware chart work; never touches broker execution."""
    connection = sqlite3.connect("file:" + (state / "research.sqlite3").as_posix() +
                                 "?mode=ro", uri=True, timeout=2)
    try:
        source_rows = connection.execute(
            "SELECT symbol,sha256,timeframe FROM market_sources "
            "WHERE timeframe='M1' OR timeframe IS NULL ORDER BY symbol,sha256").fetchall()
        if not any(row[2] == "M1" for row in source_rows):
            return {"generated": 0, "attempted": 0,
                    "status": "BLOCKED_NO_RECORDED_M1"}
        by_symbol = {}
        for symbol, digest, timeframe in source_rows:
            current = by_symbol.setdefault(symbol, {"hashes": [], "m1": False})
            current["hashes"].append(digest)
            current["m1"] |= timeframe == "M1"
        trades = connection.execute(
            "SELECT trade_id,symbol FROM trades WHERE attribution_status='VERIFIED' "
            "ORDER BY exit_utc,trade_id").fetchall()
    finally:
        connection.close()
    attempts_path = state / "analytics" / "chart-attempts.json"
    attempts_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        attempts = json.loads(attempts_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        attempts = {}
    warehouse = Warehouse(state)
    generated = attempted = 0
    try:
        for trade_id, symbol in trades:
            if attempted >= max_charts:
                break
            source = by_symbol.get(symbol)
            if not source or not source["m1"]:
                continue
            source_digest = hashlib.sha256("\n".join(source["hashes"]).encode()).hexdigest()
            if attempts.get(trade_id) == source_digest:
                continue
            attempted += 1
            try:
                chart(warehouse, trade_id)
                generated += 1
            except MarketDataUnavailable:
                pass
            attempts[trade_id] = source_digest
    finally:
        warehouse.close()
    temporary = attempts_path.with_name(".chart-attempts." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(attempts, sort_keys=True), encoding="utf-8")
    os.replace(temporary, attempts_path)
    return {"generated": generated, "attempted": attempted,
            "status": "COMPLETE" if generated else "NO_COMPLETE_TRADE_WINDOWS"}


def daily(state: Path, backups: Path, git_commit: str) -> dict:
    status_path = state / "analytics" / "daily-status.json"
    backup = json.loads((backups / "backup-status.json").read_text(encoding="utf-8"))
    if backup.get("status") != "SUCCESS" or not backup.get("sha256"):
        raise RuntimeError("last_backup_not_verified")
    result = run(state, git_commit=git_commit, backup_sha256=backup["sha256"])
    chart_job = build_pending_charts(state)
    update = {"status": "SUCCESS", "observed_utc": datetime.now(timezone.utc).isoformat(),
              "analysis_run_id": result["analysis_run_id"],
              "cutoff": result["cutoff"],
              "market_data_gate": not result["data_quality"]["market_ticks"],
              "chart_job": chart_job}
    temporary = status_path.with_name(".daily-status." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(update, indent=2), encoding="utf-8")
    os.replace(temporary, status_path)
    return update


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--backups", type=Path, default=DEFAULT_BACKUPS)
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args()
    import msvcrt
    lock_path = args.state / "analytics" / "daily.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("daily_analytics_already_running") from exc
        try:
            result = daily(args.state, args.backups, args.git_commit)
        except Exception as exc:
            failure = {"status": "FAILED",
                       "observed_utc": datetime.now(timezone.utc).isoformat(),
                       "error": str(exc)[:240], "trading_execution_unaffected": True}
            target = args.state / "analytics" / "daily-status.json"
            temporary = target.with_name(".daily-status." + uuid.uuid4().hex)
            temporary.write_text(json.dumps(failure, indent=2), encoding="utf-8")
            os.replace(temporary, target)
            raise
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    if sys.stdout is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
