"""Independent research warehouse and provenance-preserving importer."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

CAMPAIGN_DB = Path("research/demo-live-20261021/runtime/campaign.sqlite3")
EVIDENCE_ROOT = Path("research/demo-live-20261021/runtime/evidence")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def number(value) -> Decimal | None:
    try:
        return Decimal(str(value)) if value is not None else None
    except (InvalidOperation, ValueError):
        return None


def epoch(value: str | None) -> float | None:
    try:
        timestamp = datetime.fromisoformat(value)
        return timestamp.timestamp() if timestamp.tzinfo else None
    except (TypeError, ValueError):
        return None


class Warehouse:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.raw = self.root / "raw"
        self.raw.mkdir(exist_ok=True)
        self.db = sqlite3.connect(self.root / "research.sqlite3", timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS import_batches(
            id TEXT PRIMARY KEY, source TEXT NOT NULL, started_utc TEXT NOT NULL,
            finished_utc TEXT, state TEXT NOT NULL, record_count INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS source_artifacts(
            sha256 TEXT PRIMARY KEY, source_path TEXT NOT NULL, kind TEXT NOT NULL,
            strategy_id TEXT, event_utc TEXT, imported_utc TEXT NOT NULL,
            local_path TEXT NOT NULL, bytes INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS accounts(
            fingerprint TEXT PRIMARY KEY, broker_server TEXT, currency TEXT,
            account_login_local TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS strategies(
            strategy_id TEXT NOT NULL, config_sha256 TEXT NOT NULL,
            name TEXT, PRIMARY KEY(strategy_id,config_sha256));
        CREATE TABLE IF NOT EXISTS signals(
            event_sha256 TEXT PRIMARY KEY REFERENCES source_artifacts(sha256),
            strategy_id TEXT, kind TEXT NOT NULL, symbol TEXT, signal_key TEXT,
            bar_utc_s INTEGER, raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS broker_events(
            event_sha256 TEXT PRIMARY KEY REFERENCES source_artifacts(sha256),
            kind TEXT NOT NULL, ticket INTEGER, order_ticket INTEGER,
            position_id INTEGER, strategy_id TEXT, event_time_msc INTEGER,
            raw_json TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS broker_events_position ON broker_events(position_id);
        CREATE TABLE IF NOT EXISTS position_events(
            id TEXT PRIMARY KEY, trade_id TEXT, kind TEXT NOT NULL,
            event_utc TEXT, volume TEXT, price TEXT, source_sha256 TEXT,
            detail_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS risk_events(
            id TEXT PRIMARY KEY, strategy_id TEXT, event_utc TEXT,
            reason TEXT, source_sha256 TEXT, raw_json TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS trades(
            trade_id TEXT PRIMARY KEY, campaign_id TEXT NOT NULL,
            account_fingerprint TEXT NOT NULL REFERENCES accounts(fingerprint),
            broker_position_id INTEGER NOT NULL, strategy_id TEXT,
            config_sha256 TEXT, signal_key TEXT, symbol TEXT,
            direction TEXT, entry_utc TEXT, exit_utc TEXT,
            initial_sl TEXT, initial_tp TEXT, opened_volume TEXT,
            closed_volume TEXT, gross_pnl TEXT, commission TEXT, swap TEXT,
            fees TEXT, net_pnl TEXT, initial_risk TEXT, realized_r TEXT,
            holding_seconds REAL, attribution_status TEXT NOT NULL,
            source_rowid INTEGER NOT NULL, source_sha256 TEXT NOT NULL,
            record_json TEXT NOT NULL,
            UNIQUE(campaign_id,account_fingerprint,broker_position_id));
        CREATE INDEX IF NOT EXISTS trades_strategy_exit ON trades(strategy_id,exit_utc);
        CREATE TABLE IF NOT EXISTS quality_issues(
            trade_id TEXT NOT NULL, code TEXT NOT NULL, detail TEXT,
            PRIMARY KEY(trade_id,code));
        CREATE TABLE IF NOT EXISTS market_bars(
            source_sha256 TEXT NOT NULL, symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL, open_utc TEXT NOT NULL,
            open REAL, high REAL, low REAL, close REAL,
            tick_volume REAL, real_volume REAL, spread_points REAL,
            PRIMARY KEY(source_sha256,symbol,timeframe,open_utc));
        CREATE TABLE IF NOT EXISTS market_ticks(
            source_sha256 TEXT NOT NULL, symbol TEXT NOT NULL,
            time_utc TEXT NOT NULL, bid REAL, ask REAL, volume REAL,
            PRIMARY KEY(source_sha256,symbol,time_utc,bid,ask));
        CREATE TABLE IF NOT EXISTS market_sources(
            sha256 TEXT PRIMARY KEY, source_type TEXT NOT NULL,
            source_path TEXT NOT NULL, imported_utc TEXT NOT NULL,
            symbol TEXT NOT NULL, timeframe TEXT,
            row_count INTEGER NOT NULL, derived_from TEXT);
        CREATE TABLE IF NOT EXISTS trade_metrics(
            trade_id TEXT PRIMARY KEY REFERENCES trades(trade_id),
            mfe_points REAL, mae_points REAL, mfe_r REAL, mae_r REAL,
            excursion_quality TEXT, updated_utc TEXT);
        CREATE TABLE IF NOT EXISTS hypotheses(
            id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL,
            observed_issue TEXT NOT NULL, supporting_trade_ids_json TEXT NOT NULL,
            proposed_change TEXT, mechanism TEXT, downsides TEXT,
            sample_size INTEGER, confidence TEXT, validation_plan TEXT,
            status TEXT NOT NULL DEFAULT 'PROPOSED', created_utc TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS collector_state(
            source_id TEXT PRIMARY KEY, last_rowid INTEGER NOT NULL,
            source_count INTEGER NOT NULL, updated_utc TEXT NOT NULL);
        """)
        if self.get_meta("account_salt") is None:
            self.set_meta("account_salt", os.urandom(32).hex())
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def get_meta(self, key: str) -> str | None:
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None

    def set_meta(self, key: str, value: str) -> None:
        self.db.execute("INSERT INTO meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        (key, value))

    def account_fingerprint(self, server: str, login) -> str:
        salt = bytes.fromhex(self.get_meta("account_salt"))
        return hashlib.sha256(salt + f"{server}|{login}".encode()).hexdigest()[:24]

    def store_artifact(self, raw: bytes, source_path: str) -> str:
        sha = digest(raw)
        try:
            event = json.loads(raw)
            kind = event.get("kind", "UNKNOWN")
            owner = event.get("strategy")
            when = event.get("utc")
            payload = event.get("payload") or {}
        except (ValueError, TypeError):
            kind, owner, when, payload = "UNPARSEABLE", None, None, {}
        location = self.raw / sha[:2] / (sha + ".json")
        location.parent.mkdir(exist_ok=True)
        if not location.exists():
            temporary = location.with_suffix(".tmp")
            temporary.write_bytes(raw)
            os.replace(temporary, location)
        elif digest(location.read_bytes()) != sha:
            raise RuntimeError("research_raw_hash_mismatch")
        self.db.execute(
            """INSERT OR IGNORE INTO source_artifacts
               VALUES (?,?,?,?,?,?,?,?)""",
            (sha, source_path, kind, owner, when, utc(), str(location), len(raw)))
        if kind in {"LIVE_SIGNAL", "SIGNAL_SKIPPED", "DATA_OR_POLICY_SKIP"}:
            self.db.execute(
                "INSERT OR IGNORE INTO signals VALUES (?,?,?,?,?,?,?)",
                (sha, owner, kind, payload.get("symbol"), payload.get("signal_key"),
                 payload.get("bar"), json.dumps(payload, sort_keys=True)))
        elif kind in {"BROKER_ORDER", "BROKER_DEAL", "BROKER_POSITION_OPEN"}:
            self.db.execute(
                "INSERT OR IGNORE INTO broker_events VALUES (?,?,?,?,?,?,?,?)",
                (sha, kind, payload.get("ticket"), payload.get("order"),
                 payload.get("position_id") or payload.get("identifier"), owner,
                 payload.get("time_msc") or payload.get("time_done_msc"),
                 json.dumps(payload, sort_keys=True)))
        elif kind == "SAFETY_EVENT":
            identifier = str(payload.get("id") or sha)
            self.db.execute(
                "INSERT OR IGNORE INTO risk_events VALUES (?,?,?,?,?,?)",
                (identifier, owner, when, payload.get("reason"), sha,
                 json.dumps(payload, sort_keys=True)))
        elif kind == "CAMPAIGN_ACTIVATED":
            account = payload.get("account") or {}
            if account.get("login") is not None and account.get("server"):
                fingerprint = self.account_fingerprint(
                    str(account["server"]), account["login"])
                self.db.execute(
                    """UPDATE accounts SET currency=? WHERE fingerprint=? AND
                       (currency IS NULL OR currency=?)""",
                    (account.get("currency"), fingerprint, account.get("currency")))
        return sha

    def import_trade(self, row: sqlite3.Row, evidence_reader) -> str:
        record = json.loads(row["record_json"])
        strategy = row["strategy"]
        server = str(record.get("account_server") or "")
        login = record.get("account_login")
        account = self.account_fingerprint(server, login)
        campaign = str(record.get("campaign_id") or "")
        position = int(row["position_id"])
        trade_id = digest(f"{campaign}|{account}|{position}".encode())[:32]
        self.db.execute(
            "INSERT OR IGNORE INTO accounts VALUES (?,?,?,?)",
            (account, server, None, str(login)))
        config = str(record.get("config_sha256") or "")
        self.db.execute(
            "INSERT OR IGNORE INTO strategies(strategy_id,config_sha256) VALUES (?,?)",
            (strategy, config))
        issues = set()
        if (record.get("execution_kind") != "REAL_TIME_DEMO_BROKER" or
                record.get("account_trade_mode") != "DEMO" or
                record.get("fully_closed") is not True):
            issues.add("not_verified_demo_close")
        if strategy != record.get("strategy_id") or row["signal_key"] == "":
            issues.add("strategy_or_signal_mismatch")
        if number(record.get("opened_volume")) != number(record.get("closed_volume")):
            issues.add("volume_not_fully_closed")
        if epoch(record.get("entry_utc")) is None or epoch(record.get("exit_utc")) is None:
            issues.add("timestamp_unverified")
        elif epoch(record["exit_utc"]) <= epoch(record["entry_utc"]):
            issues.add("nonchronological_trade")
        events = []
        for ref in record.get("broker_evidence", []):
            raw = evidence_reader(ref["path"])
            if digest(raw) != ref["sha256"]:
                raise RuntimeError(f"broker_evidence_hash_mismatch:{ref['path']}")
            sha = self.store_artifact(raw, ref["path"])
            events.append((sha, json.loads(raw)))
        deals = [event["payload"] for _, event in events if event.get("kind") == "BROKER_DEAL"]
        orders = [event["payload"] for _, event in events if event.get("kind") == "BROKER_ORDER"]
        expected = set(map(int, record.get("opening_deal_ids", []) + record.get("closing_deal_ids", [])))
        actual = {int(deal["ticket"]) for deal in deals}
        if expected != actual:
            issues.add("deal_id_mismatch")
        expected_orders = {int(record["opening_order_id"])} | set(map(int, record.get("closing_order_ids", [])))
        if not expected_orders.issubset({int(order["ticket"]) for order in orders}):
            issues.add("order_id_mismatch")
        sums = [sum((number(deal.get(field)) or Decimal(0) for deal in deals), Decimal(0))
                for field in ("profit", "commission", "swap", "fee")]
        values = [number(record.get(field)) for field in
                  ("broker_gross_profit", "broker_commission", "broker_swap",
                   "broker_fees", "broker_net_profit")]
        if (any(value is None for value in values) or
                any(abs(left - right) > Decimal("0.000001")
                    for left, right in zip(sums, values[:4])) or
                abs(sum(sums) - values[4]) > Decimal("0.000001")):
            issues.add("broker_pnl_mismatch")
        if not deals or not orders:
            issues.add("broker_history_incomplete")
        first_deal = next((deal for deal in deals if int(deal.get("ticket", -1)) in
                           record.get("opening_deal_ids", [])), None)
        direction = {0: "BUY", 1: "SELL"}.get(first_deal.get("type") if first_deal else None)
        if direction is None:
            issues.add("direction_unverified")
        if not record.get("stop_loss") or not record.get("take_profit"):
            issues.add("initial_sl_tp_missing")
        risk = number(record.get("initial_risk_account_currency"))
        net = values[4]
        realized_r = net / risk if net is not None and risk is not None and risk > 0 else None
        if realized_r is None:
            issues.add("r_multiple_unavailable")
        for field in ("entry_bid_ask_missing", "exit_bid_ask_missing",
                      "sl_tp_modification_history_unavailable",
                      "entry_equity_unavailable", "market_context_unavailable"):
            issues.add(field)
        attribution = "VERIFIED" if not issues.intersection({
            "not_verified_demo_close", "strategy_or_signal_mismatch", "deal_id_mismatch",
            "order_id_mismatch", "broker_history_incomplete",
        }) else "UNRESOLVED"
        duration = (epoch(record["exit_utc"]) - epoch(record["entry_utc"])
                    if epoch(record.get("entry_utc")) is not None and
                    epoch(record.get("exit_utc")) is not None else None)
        self.db.execute(
            """INSERT INTO trades VALUES
               (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(trade_id) DO NOTHING""",
            (trade_id, campaign, account, position, strategy, config,
             row["signal_key"], record.get("symbol"), direction,
             record.get("entry_utc"), record.get("exit_utc"),
             str(record.get("stop_loss")), str(record.get("take_profit")),
             str(record.get("opened_volume")), str(record.get("closed_volume")),
             str(values[0]) if values[0] is not None else None,
             str(values[1]) if values[1] is not None else None,
             str(values[2]) if values[2] is not None else None,
             str(values[3]) if values[3] is not None else None,
             str(net) if net is not None else None,
             str(risk) if risk is not None else None,
             str(realized_r) if realized_r is not None else None,
             duration, attribution, row["source_rowid"], digest(row["record_json"].encode()),
             row["record_json"]))
        for code in sorted(issues):
            self.db.execute("INSERT OR IGNORE INTO quality_issues VALUES (?,?,?)",
                            (trade_id, code, None))
        for deal in deals:
            kind = ("PARTIAL_OR_FINAL_CLOSE" if int(deal.get("ticket", -1)) in
                    record.get("closing_deal_ids", []) else "ENTRY_FILL")
            identifier = digest(f"{trade_id}|deal|{deal['ticket']}".encode())[:32]
            millis = deal.get("time_msc")
            event_utc = datetime.fromtimestamp(int(millis) / 1000, timezone.utc).isoformat() if millis else None
            self.db.execute(
                "INSERT OR IGNORE INTO position_events VALUES (?,?,?,?,?,?,?,?)",
                (identifier, trade_id, kind, event_utc, str(deal.get("volume")),
                 str(deal.get("price")), None, json.dumps(deal, sort_keys=True)))
        return trade_id


def import_from_connection(warehouse: Warehouse, source: sqlite3.Connection,
                           evidence_reader, source_id: str, minimum_rowid: int = 0) -> dict:
    source.row_factory = sqlite3.Row
    batch_id = digest(f"{source_id}|{utc()}".encode())[:32]
    warehouse.db.execute("INSERT INTO import_batches VALUES (?,?,?,NULL,'RUNNING',0)",
                         (batch_id, source_id, utc()))
    rows = source.execute(
        """SELECT rowid AS source_rowid, position_id, strategy, signal_key, record_json
           FROM closed WHERE rowid>? ORDER BY rowid""", (minimum_rowid,)).fetchall()
    before_count = warehouse.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    processed = 0
    try:
        for row in rows:
            warehouse.import_trade(row, evidence_reader)
            processed += 1
        source_count = source.execute("SELECT COUNT(*) FROM closed").fetchone()[0]
        last_rowid = max([minimum_rowid] + [int(row["source_rowid"]) for row in rows])
        warehouse.db.execute(
            """INSERT INTO collector_state VALUES (?,?,?,?)
               ON CONFLICT(source_id) DO UPDATE SET
               last_rowid=excluded.last_rowid,source_count=excluded.source_count,
               updated_utc=excluded.updated_utc""",
            (source_id, last_rowid, source_count, utc()))
        warehouse.db.execute(
            "UPDATE import_batches SET finished_utc=?,state='SUCCESS',record_count=? WHERE id=?",
            (utc(), processed, batch_id))
        warehouse.db.commit()
    except Exception:
        warehouse.db.rollback()
        raise
    total = warehouse.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    return {"source": source_id, "processed": processed, "new_trades": total - before_count,
            "source_count": source_count, "warehouse_count": total}


def import_safety_rows(warehouse: Warehouse, source: sqlite3.Connection) -> int:
    rows = source.execute("SELECT id,observed_utc,scope,reason FROM safety_events").fetchall()
    for row in rows:
        warehouse.db.execute(
            "INSERT OR IGNORE INTO risk_events VALUES (?,?,?,?,?,?)",
            (row["id"], row["scope"], row["observed_utc"], row["reason"], None,
             json.dumps({"id": row["id"], "scope": row["scope"],
                         "observed_utc": row["observed_utc"], "reason": row["reason"]})))
    warehouse.db.commit()
    return len(rows)


def import_archive_evidence(warehouse: Warehouse, package: zipfile.ZipFile,
                            workspace: Path) -> int:
    prefix = "source/" + EVIDENCE_ROOT.as_posix() + "/"
    imported = 0
    existing = {row[0] for row in
                warehouse.db.execute("SELECT source_path FROM source_artifacts")}
    for member in package.namelist():
        if not member.startswith(prefix) or not member.endswith(".json"):
            continue
        original = str(workspace / Path(member.removeprefix("source/")))
        if original in existing:
            continue
        warehouse.store_artifact(package.read(member), original)
        imported += 1
    warehouse.db.commit()
    return imported


def import_live_evidence(warehouse: Warehouse, workspace: Path) -> int:
    root = workspace / EVIDENCE_ROOT
    existing = {row[0] for row in
                warehouse.db.execute("SELECT source_path FROM source_artifacts")}
    imported = 0
    for path in root.rglob("*.json"):
        if str(path) in existing:
            continue
        warehouse.store_artifact(path.read_bytes(), str(path))
        imported += 1
    warehouse.db.commit()
    return imported


def reconcile_local_metadata(warehouse: Warehouse, workspace: Path) -> None:
    for row in warehouse.db.execute(
        "SELECT source_path,local_path FROM source_artifacts WHERE kind='CAMPAIGN_ACTIVATED'"
    ):
        warehouse.store_artifact(Path(row["local_path"]).read_bytes(), row["source_path"])
    config_path = workspace / "research" / "demo-live-20261021" / "campaign_config.json"
    if config_path.is_file():
        raw = config_path.read_bytes()
        config = json.loads(raw)
        warehouse.set_meta("campaign_config_sha256", digest(raw))
        for worker in config.get("workers", []):
            warehouse.db.execute(
                "UPDATE strategies SET name=? WHERE strategy_id=? AND name IS NULL",
                (worker.get("name"), worker.get("id")))
    warehouse.db.commit()


def import_backup(warehouse: Warehouse, archive: Path, workspace: Path) -> dict:
    with zipfile.ZipFile(archive) as package:
        manifest = json.loads(package.read("manifest.json"))
        member = "source/" + CAMPAIGN_DB.as_posix()
        with tempfile.TemporaryDirectory(prefix="aaat-research-") as temporary:
            database = Path(temporary) / "campaign.sqlite3"
            database.write_bytes(package.read(member))
            source = sqlite3.connect("file:" + database.as_posix() + "?mode=ro", uri=True)
            try:
                def reader(path):
                    relative = Path(path).relative_to(workspace)
                    return package.read("source/" + relative.as_posix())
                result = import_from_connection(
                    warehouse, source, reader, "backup:" + manifest["created_utc"])
                result["other_evidence_imported"] = import_archive_evidence(
                    warehouse, package, workspace)
                result["safety_rows_seen"] = import_safety_rows(warehouse, source)
                reconcile_local_metadata(warehouse, workspace)
                checksum = hashlib.sha256()
                with archive.open("rb") as handle:
                    for block in iter(lambda: handle.read(1024 * 1024), b""):
                        checksum.update(block)
                warehouse.set_meta("bootstrap_archive_sha256", checksum.hexdigest())
                warehouse.db.commit()
                return result
            finally:
                source.close()


def import_live(warehouse: Warehouse, workspace: Path) -> dict:
    database = workspace / CAMPAIGN_DB
    source = sqlite3.connect("file:" + database.as_posix() + "?mode=ro", uri=True, timeout=2)
    try:
        state = warehouse.db.execute(
            "SELECT last_rowid,source_count FROM collector_state WHERE source_id='live'"
        ).fetchone()
        minimum = int(state[0]) if state else 0
        maximum, count = source.execute("SELECT COALESCE(MAX(rowid),0),COUNT(*) FROM closed").fetchone()
        if maximum < minimum or (state and count < int(state[1])):
            minimum = 0
        def reader(path):
            absolute = Path(path).resolve()
            if not absolute.is_relative_to(workspace.resolve()):
                raise RuntimeError("evidence_outside_workspace")
            return absolute.read_bytes()
        result = import_from_connection(warehouse, source, reader, "live", minimum)
        result["other_evidence_imported"] = import_live_evidence(warehouse, workspace)
        result["safety_rows_seen"] = import_safety_rows(warehouse, source)
        reconcile_local_metadata(warehouse, workspace)
        return result
    finally:
        source.close()
