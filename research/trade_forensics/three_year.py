"""Read-only three-year backtest readiness audit in the existing research store.

No broker API, trading module, or historical simulation is imported. A blocked
assessment is never represented as a backtest run or a simulated trade.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .store import utc

PERIOD_START = "2023-10-24T00:00:00+00:00"
PERIOD_END = "2026-10-24T00:00:00+00:00"  # exclusive; Oct 23 is the last full day
ASSESSMENT_VERSION = "three-year-readiness-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _source_path(workspace: Path, relative: str) -> Path | None:
    candidate = (workspace / relative).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError:
        return None
    return candidate


def strategy_inventory(workspace: Path) -> list[dict]:
    inventory = json.loads((workspace / "research_outputs" / "inventory.json").read_text(
        encoding="utf-8"))
    rows = []
    for item in inventory["strategies"]:
        path = _source_path(workspace, item["source_file"])
        valid = bool(path and path.is_file() and sha256(path) == item["sourceSHA256"])
        strategy_id = item["strategy_id"]
        if strategy_id in {f"S{i:02d}" for i in range(1, 6)}:
            status = "DATA_GATED" if valid else "NOT_EXECUTABLE"
            blocker = ("Three-year M1/Bid-Ask coverage, UTC offset history, and cost/contract "
                       "specifications are not verified" if valid else "Frozen source hash mismatch")
        else:
            status = "NOT_EXECUTABLE"
            blocker = item.get("blocker") or "No faithful isolated historical implementation"
            if not valid:
                blocker += "; frozen source unavailable or hash mismatch"
        rows.append({"strategy_id": strategy_id, "name": item["name"],
                     "source_file": item["source_file"],
                     "source_sha256": item["sourceSHA256"],
                     "source_hash_verified": valid, "status": status,
                     "blocker": blocker})
    if [row["strategy_id"] for row in rows] != [f"S{i:02d}" for i in range(1, 19)]:
        raise RuntimeError("strategy_inventory_not_s01_through_s18")
    return rows


def _utc_from_server_epoch(seconds: int, offset_minutes: int) -> str:
    return datetime.fromtimestamp(int(seconds) - offset_minutes * 60,
                                  timezone.utc).isoformat()


def audit_legacy_m1(workspace: Path) -> list[dict]:
    pointer = json.loads((workspace / "research" / "overnight-20261010" /
                          "history_pointer.json").read_text(encoding="utf-8"))
    manifest_path = Path(pointer["path"])
    if not manifest_path.is_file() or sha256(manifest_path) != pointer["sha256"]:
        raise RuntimeError("legacy_history_manifest_hash_mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    offset = int(manifest["brokerOffsetMinutes"])
    rows = []
    for symbol, record in sorted(manifest["symbols"].items()):
        path = Path(record["path"])
        base = {"symbol": symbol, "provider": "legacy_native_MT5_archive",
                "timeframe": "M1", "source_sha256": record["sha256"],
                "timezone_status": "UNVERIFIED_FIXED_BROKER_OFFSET",
                "broker_offset_minutes_assumed": offset,
                "bid_ask_ticks_covered": False}
        if record.get("status") != "AVAILABLE" or not path.is_file():
            rows.append({**base, "status": "SOURCE_UNAVAILABLE", "rows": 0})
            continue
        if sha256(path) != record["sha256"]:
            rows.append({**base, "status": "SOURCE_HASH_MISMATCH", "rows": 0})
            continue
        with np.load(path, allow_pickle=False) as package:
            rates = package["rates"]
        if not len(rates) or not {"time", "open", "high", "low", "close", "spread"}.issubset(
                rates.dtype.names or ()):
            rows.append({**base, "status": "INVALID_RATE_SCHEMA", "rows": len(rates)})
            continue
        times = rates["time"].astype(np.int64)
        gaps = np.diff(times)
        prices_valid = all(np.all(np.isfinite(rates[field])) for field in
                           ("open", "high", "low", "close"))
        prices_valid &= bool(np.all(rates["high"] >= rates["low"]))
        prices_valid &= bool(np.all(rates["spread"] >= 0))
        first = _utc_from_server_epoch(times[0], offset)
        last = _utc_from_server_epoch(times[-1], offset)
        shape_valid = bool(np.all(gaps > 0) and prices_valid and
                           len(rates) == record["bars"] and
                           first == record["firstUTC"].replace("Z", "+00:00") and
                           last == record["lastUTC"].replace("Z", "+00:00"))
        rows.append({**base, "status": "PARTIAL_ARCHIVE_OFFSET_UNVERIFIED" if shape_valid
                     else "INVALID_ARCHIVE_OR_MANIFEST", "rows": len(rates),
                     "first_utc_assuming_fixed_offset": first,
                     "last_utc_assuming_fixed_offset": last,
                     "non_60_second_intervals": int(np.count_nonzero(gaps != 60)),
                     "continuous_three_year_coverage": False,
                     "note": "Weekend/session gaps need market-calendar review; fixed historical offset is unverified"})
    return rows


def assess(workspace: Path, state: Path, backup_status: Path) -> dict:
    backup = json.loads(backup_status.read_text(encoding="utf-8"))
    if backup.get("status") != "SUCCESS" or not backup.get("sha256"):
        raise RuntimeError("verified_prebacktest_backup_required")
    inventory = strategy_inventory(workspace)
    sources = audit_legacy_m1(workspace)
    connection = sqlite3.connect("file:" + (state / "research.sqlite3").as_posix() +
                                 "?mode=ro", uri=True, timeout=2)
    try:
        market_counts = {
            "bars": connection.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0],
            "ticks": connection.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0],
            "sources": connection.execute("SELECT COUNT(*) FROM market_sources").fetchone()[0],
            "broker_demo_trades": connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0],
        }
    finally:
        connection.close()
    identity = {"version": ASSESSMENT_VERSION, "start": PERIOD_START,
                "end_exclusive": PERIOD_END, "strategies": inventory,
                "sources": sources, "market_counts": market_counts,
                "backup_sha256": backup["sha256"]}
    assessment_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()[:20]
    return {"assessment_id": assessment_id, "generated_utc": utc(),
            "evidence_class": "RESEARCH_READINESS_ASSESSMENT",
            "historical_backtest_runs": 0, "simulated_trades": 0,
            "target_period_utc": {"start": PERIOD_START, "end_exclusive": PERIOD_END,
                                  "status": "PLANNED_NOT_COVERED"},
            "backup_sha256": backup["sha256"], "market_warehouse": market_counts,
            "strategies": inventory, "legacy_market_sources": sources,
            "overall_status": "BLOCKED_NO_VERIFIED_THREE_YEAR_MARKET_DATA",
            "requirements_before_execution": [
                "Complete source-verified 36-month bars and broker-side ticks for relevant symbols",
                "Historical UTC and DST mapping validated against the source calendar",
                "Versioned symbol contract, commission, swap, spread and stop-level specifications",
                "Separate faithful execution harness with chronological and intrabar tests",
            ],
            "source_type_separation": {"historical": "HISTORICAL_BACKTEST",
                                       "forward": "BROKER_CONFIRMED_DEMO"}}


def publish(state: Path, report: dict) -> Path:
    """Persist metadata in the existing research SQLite and versioned analytics tree."""
    path = state / "analytics" / "historical" / "assessments" / report["assessment_id"] / "assessment.json"
    connection = sqlite3.connect(state / "research.sqlite3", timeout=5)
    try:
        connection.execute("PRAGMA busy_timeout=5000")
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("""CREATE TABLE IF NOT EXISTS historical_assessments(
            id TEXT PRIMARY KEY, generated_utc TEXT NOT NULL,
            period_start_utc TEXT NOT NULL, period_end_exclusive_utc TEXT NOT NULL,
            status TEXT NOT NULL, backup_sha256 TEXT NOT NULL,
            report_path TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS historical_backtest_runs(
            run_id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL,
            strategy_version_sha256 TEXT NOT NULL, source_type TEXT NOT NULL
                CHECK(source_type='HISTORICAL_BACKTEST'),
            period_start_utc TEXT NOT NULL, period_end_exclusive_utc TEXT NOT NULL,
            market_snapshot_sha256 TEXT NOT NULL, config_sha256 TEXT NOT NULL,
            engine_sha256 TEXT NOT NULL, git_commit TEXT NOT NULL,
            status TEXT NOT NULL, created_utc TEXT NOT NULL)""")
        connection.execute("""CREATE TABLE IF NOT EXISTS historical_backtest_trades(
            trade_id TEXT PRIMARY KEY, run_id TEXT NOT NULL
                REFERENCES historical_backtest_runs(run_id),
            source_type TEXT NOT NULL CHECK(source_type='HISTORICAL_BACKTEST'),
            strategy_id TEXT NOT NULL, symbol TEXT NOT NULL,
            signal_utc TEXT NOT NULL, entry_utc TEXT, exit_utc TEXT,
            source_market_sha256 TEXT NOT NULL, record_json TEXT NOT NULL)""")
        connection.execute("""INSERT OR IGNORE INTO historical_assessments
            VALUES (?,?,?,?,?,?,?)""",
            (report["assessment_id"], report["generated_utc"],
             PERIOD_START, PERIOD_END, report["overall_status"],
             report["backup_sha256"], str(path)))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
    if path.is_file():
        previous = json.loads(path.read_text(encoding="utf-8"))
        if previous["assessment_id"] != report["assessment_id"]:
            raise RuntimeError("assessment_identity_collision")
    else:
        _atomic_json(path, report)
    _atomic_json(state / "analytics" / "historical" / "latest.json",
                 {"assessment_id": report["assessment_id"], "report": str(path),
                  "overall_status": report["overall_status"]})
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(r"E:\GPT\Inves"))
    parser.add_argument("--state", type=Path,
                        default=Path(r"E:\GPT\Inves\AA-AT-research-state"))
    parser.add_argument("--backup-status", type=Path,
                        default=Path(r"D:\AA-AT-Backups\backup-status.json"))
    args = parser.parse_args()
    report = assess(args.workspace, args.state, args.backup_status)
    path = publish(args.state, report)
    print(json.dumps({"assessment_id": report["assessment_id"],
                      "status": report["overall_status"],
                      "historical_backtest_runs": 0, "simulated_trades": 0,
                      "report": str(path)}))


if __name__ == "__main__":
    main()
