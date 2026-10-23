"""Authenticated dashboard projections of the separate research/backup stores."""
from __future__ import annotations

import json
import re
import shutil
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs

RESEARCH = Path(r"E:\GPT\Inves\AA-AT-research-state")
BACKUPS = Path(r"D:\AA-AT-Backups")
TRADE_ID = re.compile(r"[0-9a-f]{32}\Z")
STRATEGY = re.compile(r"S(?:0[1-9]|1[0-8])\Z")
SYMBOL = re.compile(r"[A-Za-z0-9._-]{1,32}\Z")


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def connect(state: Path = RESEARCH) -> sqlite3.Connection:
    path = state / "research.sqlite3"
    if not path.is_file():
        raise RuntimeError("research_database_unavailable")
    connection = sqlite3.connect("file:" + path.as_posix() + "?mode=ro",
                                 uri=True, timeout=2)
    connection.row_factory = sqlite3.Row
    return connection


def research_status(state: Path = RESEARCH) -> dict:
    collector = read_json(state / "collector-status.json")
    observed = collector.get("observed_utc")
    try:
        age = (datetime.now(timezone.utc) -
               datetime.fromisoformat(observed)).total_seconds()
    except (TypeError, ValueError):
        age = None
    return {
        "collector": collector, "age_seconds": age,
        "stale": age is None or age > 900,
        "data_source": "independent_research_warehouse",
        "execution_controls_separate": True,
    }


def list_trades(query: str, state: Path = RESEARCH) -> dict:
    params = parse_qs(query, keep_blank_values=False)
    allowed = {"strategy", "symbol", "direction", "start_utc", "end_utc", "limit", "offset"}
    if set(params) - allowed:
        raise ValueError("unsupported_trade_filter")
    where = []
    values = []
    for name, column, pattern in (
        ("strategy", "strategy_id", STRATEGY),
        ("symbol", "symbol", SYMBOL),
        ("direction", "direction", re.compile(r"BUY|SELL\Z")),
    ):
        if name in params:
            value = params[name][0]
            if not pattern.fullmatch(value):
                raise ValueError("invalid_" + name)
            where.append(column + "=?")
            values.append(value)
    for name, operator in (("start_utc", ">="), ("end_utc", "<=")):
        if name in params:
            value = params[name][0]
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if parsed.tzinfo is None:
                    raise ValueError()
            except ValueError as exc:
                raise ValueError("invalid_utc_filter") from exc
            where.append("exit_utc" + operator + "?")
            values.append(parsed.astimezone(timezone.utc).isoformat())
    try:
        limit = int(params.get("limit", ["50"])[0])
        offset = int(params.get("offset", ["0"])[0])
    except ValueError as exc:
        raise ValueError("invalid_pagination") from exc
    if not 1 <= limit <= 100 or not 0 <= offset <= 100000:
        raise ValueError("invalid_pagination")
    predicate = " WHERE " + " AND ".join(where) if where else ""
    with closing(connect(state)) as connection:
        total = connection.execute("SELECT COUNT(*) FROM trades" + predicate, values).fetchone()[0]
        rows = connection.execute(
            """SELECT trade_id,strategy_id,config_sha256,symbol,direction,
               entry_utc,exit_utc,net_pnl,realized_r,holding_seconds,
               attribution_status FROM trades""" + predicate +
            " ORDER BY exit_utc DESC,trade_id DESC LIMIT ? OFFSET ?",
            [*values, limit, offset]).fetchall()
    return {"total": total, "limit": limit, "offset": offset,
            "trades": [dict(row) for row in rows]}


def trade_detail(trade_id: str, state: Path = RESEARCH) -> dict:
    if not TRADE_ID.fullmatch(trade_id):
        raise ValueError("invalid_trade_id")
    with closing(connect(state)) as connection:
        trade = connection.execute(
            """SELECT trade_id,campaign_id,account_fingerprint,broker_position_id,
               strategy_id,config_sha256,signal_key,symbol,direction,entry_utc,
               exit_utc,initial_sl,initial_tp,opened_volume,closed_volume,
               gross_pnl,commission,swap,fees,net_pnl,initial_risk,realized_r,
               holding_seconds,attribution_status,source_sha256
               FROM trades WHERE trade_id=?""", (trade_id,)).fetchone()
        if trade is None:
            raise KeyError("trade_not_found")
        # Campaign and signal keys can embed the local account login, so the
        # browser receives only stable pseudonymous trade/strategy IDs.
        data = dict(trade)
        data.pop("campaign_id", None)
        data.pop("signal_key", None)
        events = connection.execute(
            """SELECT kind,event_utc,volume,price,detail_json FROM position_events
               WHERE trade_id=? ORDER BY event_utc,id""", (trade_id,)).fetchall()
        issues = connection.execute(
            "SELECT code,detail FROM quality_issues WHERE trade_id=? ORDER BY code",
            (trade_id,)).fetchall()
        metrics = connection.execute(
            "SELECT * FROM trade_metrics WHERE trade_id=?", (trade_id,)).fetchone()
    data["position_events"] = [
        {"kind": row["kind"], "event_utc": row["event_utc"],
         "volume": row["volume"], "price": row["price"]}
        for row in events]
    data["quality_issues"] = [dict(row) for row in issues]
    data["metrics"] = dict(metrics) if metrics else None
    data["chart_available"] = (state / "trade_charts" / (trade_id + ".json")).is_file()
    return data


def performance(state: Path = RESEARCH) -> dict:
    value = read_json(state / "reports" / "performance.json")
    if not value:
        raise RuntimeError("research_report_unavailable")
    return value


def quality(state: Path = RESEARCH) -> dict:
    with closing(connect(state)) as connection:
        issues = connection.execute(
            "SELECT code,COUNT(*) count FROM quality_issues GROUP BY code ORDER BY count DESC"
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        unresolved = connection.execute(
            "SELECT COUNT(*) FROM trades WHERE attribution_status!='VERIFIED'").fetchone()[0]
        bars = connection.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0]
        ticks = connection.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0]
    return {"trades": total, "unresolved_attribution": unresolved,
            "market_bars": bars, "market_ticks": ticks,
            "issues": [dict(row) for row in issues], "generated_utc": datetime.now(timezone.utc).isoformat()}


def hypotheses(state: Path = RESEARCH) -> list[dict]:
    with closing(connect(state)) as connection:
        rows = connection.execute(
            """SELECT id,strategy_id,observed_issue,supporting_trade_ids_json,
               proposed_change,mechanism,downsides,sample_size,confidence,
               validation_plan,status,created_utc FROM hypotheses ORDER BY created_utc DESC"""
        ).fetchall()
    return [dict(row) for row in rows]


def backup_status(destination: Path = BACKUPS) -> dict:
    heartbeat = read_json(destination / "backup-heartbeat.json")
    status = read_json(destination / "backup-status.json")
    slots = []
    for slot in (1, 2, 3):
        archive = destination / f"AA-AT-Backup-V{slot}.zip"
        manifest = read_json(destination / f"AA-AT-Backup-V{slot}.manifest.json")
        slots.append({"slot": f"V{slot}", "exists": archive.is_file(),
                      "bytes": archive.stat().st_size if archive.is_file() else None,
                      "verified_utc": manifest.get("verified_utc"),
                      "sha256": manifest.get("sha256"),
                      "verification_status": manifest.get("status")})
    try:
        free = shutil.disk_usage(destination).free
    except OSError:
        free = None
    try:
        age = (datetime.now(timezone.utc) -
               datetime.fromisoformat(heartbeat["observed_utc"])).total_seconds()
    except (KeyError, ValueError):
        age = None
    return {"heartbeat": heartbeat, "status": status, "slots": slots,
            "worker_stale": age is None or age > 180,
            "heartbeat_age_seconds": age, "available_bytes": free,
            "restore_from_dashboard_allowed": False}


def request_backup(key: str, actor: str, destination: Path = BACKUPS) -> dict:
    if not 8 <= len(key) <= 128 or not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError("invalid_idempotency_key")
    if not destination.is_dir():
        raise RuntimeError("backup_storage_unavailable")
    connection = sqlite3.connect(destination / "backup-requests.sqlite3", timeout=2)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS requests(
            id TEXT PRIMARY KEY, actor TEXT NOT NULL, requested_utc TEXT NOT NULL,
            state TEXT NOT NULL, finished_utc TEXT, detail TEXT)""")
        connection.execute(
            "INSERT OR IGNORE INTO requests(id,actor,requested_utc,state) VALUES (?,?,?,'PENDING')",
            (key, actor, datetime.now(timezone.utc).isoformat()))
        connection.commit()
        row = connection.execute(
            "SELECT id,requested_utc,state,finished_utc,detail FROM requests WHERE id=?",
            (key,)).fetchone()
        return dict(zip(("id", "requested_utc", "state", "finished_utc", "detail"), row))
    finally:
        connection.close()
