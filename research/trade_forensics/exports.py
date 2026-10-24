"""Portable, redacted research export. Never publishes to Git."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sqlite3
import tempfile
import uuid
import zipfile
from pathlib import Path

from .store import Warehouse, utc

SECRET_KEYS = {"login", "account_login", "password", "token", "secret",
               "account_login_local", "account_number", "name"}
DATA_DICTIONARY = """# AA-AT research dataset

All timestamps ending in `_utc` are ISO-8601 UTC. Empty values mean unavailable,
not zero. One trade is one fully closed, broker-reconciled position lifecycle.
Partial fills and closes remain events inside that lifecycle.

- `journal/trades.csv`: stable trade ID, strategy/version, symbol, side, fill
  timestamps, original SL/TP, broker costs, net realized PnL and R.
- `broker_events/orders.jsonl`, `deals.jsonl`, `positions.jsonl`:
  recorded broker payloads with immutable source hashes.
- `signals/signals.jsonl`: logged executed and skipped signals, kept separate.
- `risk_events/events.jsonl`: recorded safety events.
- `market_data/*.csv`: only imported, provenance-tagged observed data.
- `trade_charts/`: charts only for trades with recorded covering candles.
- `reports/performance.json`: descriptive results and uncertainty estimates.
- `reports/data_quality.json`: missing fields, attribution and market coverage.

Broker account identifiers and local source paths are redacted in this export.
Source SHA-256 hashes link rows to the private immutable local warehouse.
Historical research data, if imported, is tagged separately from broker DEMO
executions and is never counted as a campaign trade.
"""
LOAD_GUIDE = """# Load the AA-AT research export

Extract the ZIP into a private folder. The archive contains redacted account
identifiers and genuine broker-confirmed DEMO trade lifecycles. Missing values
are unavailable evidence, not zero. Do not combine it with simulated trades.

```python
import pandas as pd
trades = pd.read_parquet("journal/trades.parquet")
quality = pd.read_json("reports/data_quality.json", typ="series")
print(trades.groupby("strategy_id")["net_pnl"].count())
```

Without pandas, use Python's `csv.DictReader` on `journal/trades.csv` or
`json.loads` line by line on `journal/trades.jsonl`. Join records using
`trade_id`; inspect `manifest.json` and `DATA_DICTIONARY.md` first.
"""


def scrub(value):
    if isinstance(value, dict):
        return {key: ("REDACTED" if key.lower() in SECRET_KEYS else
                      scrub(json.loads(item)) if key == "raw_json" and isinstance(item, str)
                      else scrub(item))
                for key, item in value.items()
                if key not in {"broker_evidence", "local_path", "source_path"}}
    if isinstance(value, list):
        return [scrub(item) for item in value]
    return value


def json_lines(rows) -> bytes:
    return ("".join(json.dumps(scrub(dict(row)), sort_keys=True, default=str) + "\n"
                    for row in rows)).encode("utf-8")


def csv_bytes(rows) -> bytes:
    rows = [dict(row) for row in rows]
    if not rows:
        return b""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode("utf-8")


def export(state: Path, destination: Path | None = None) -> dict:
    destination = destination or state / "exports" / "AA-AT-RESEARCH-DATASET.zip"
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + "." + uuid.uuid4().hex)
    database = state / "research.sqlite3"
    with tempfile.TemporaryDirectory(prefix="aaat-export-", dir=destination.parent) as scratch:
        snapshot = Path(scratch) / "research.sqlite3"
        source = sqlite3.connect("file:" + database.as_posix() + "?mode=ro", uri=True, timeout=2)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target, pages=256, sleep=0.02)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("research_snapshot_integrity_failed")
        finally:
            target.close()
            source.close()
        data = sqlite3.connect(snapshot)
        data.row_factory = sqlite3.Row
        try:
            source_backup = data.execute(
                "SELECT value FROM meta WHERE key='bootstrap_archive_sha256'").fetchone()
            trades = [dict(row) for row in data.execute(
                """SELECT trade_id,campaign_id,account_fingerprint,broker_position_id,
                   strategy_id,config_sha256,signal_key,symbol,direction,entry_utc,
                   exit_utc,initial_sl,initial_tp,opened_volume,closed_volume,
                   gross_pnl,commission,swap,fees,net_pnl,initial_risk,realized_r,
                   holding_seconds,attribution_status,source_sha256
                   FROM trades ORDER BY exit_utc,trade_id""")]
            account_logins = {
                row["fingerprint"]: row["account_login_local"]
                for row in data.execute("SELECT fingerprint,account_login_local FROM accounts")
            }
            for trade in trades:
                login = account_logins.get(trade["account_fingerprint"])
                if login:
                    for field in ("campaign_id", "signal_key"):
                        if trade[field]:
                            trade[field] = trade[field].replace(
                                login, trade["account_fingerprint"])
            events = {kind: [dict(row) for row in data.execute(
                "SELECT event_sha256,ticket,order_ticket,position_id,strategy_id,event_time_msc,raw_json "
                "FROM broker_events WHERE kind=? ORDER BY event_time_msc,event_sha256", (kind,))]
                for kind in ("BROKER_ORDER", "BROKER_DEAL", "BROKER_POSITION_OPEN")}
            signals = [dict(row) for row in data.execute(
                "SELECT event_sha256,strategy_id,kind,symbol,signal_key,bar_utc_s,raw_json FROM signals")]
            risks = [dict(row) for row in data.execute(
                "SELECT id,strategy_id,event_utc,reason,source_sha256,raw_json FROM risk_events")]
            metrics = [dict(row) for row in data.execute("SELECT * FROM trade_metrics")]
            hypotheses = [dict(row) for row in data.execute("SELECT * FROM hypotheses")]
            bars = [dict(row) for row in data.execute("SELECT * FROM market_bars")]
            ticks = [dict(row) for row in data.execute("SELECT * FROM market_ticks")]
            sources = [dict(row) for row in data.execute(
                "SELECT sha256,source_type,symbol,timeframe,row_count,derived_from FROM market_sources")]
            issues = [dict(row) for row in data.execute("SELECT * FROM quality_issues")]
        finally:
            data.close()
        report_path = state / "reports" / "performance.json"
        report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
        quality = {
            "generated_utc": utc(), "total_trades": len(trades),
            "verified_attribution": sum(row["attribution_status"] == "VERIFIED" for row in trades),
            "issue_count": len(issues),
            "issues_by_code": {code: sum(row["code"] == code for row in issues)
                               for code in sorted({row["code"] for row in issues})},
            "market_bar_rows": len(bars), "market_tick_rows": len(ticks),
            "charts_available": len(list((state / "trade_charts").glob("*.html")))
                                if (state / "trade_charts").exists() else 0,
        }
        quality_path = state / "reports" / "data_quality.json"
        if quality_path.exists():
            quality = json.loads(quality_path.read_text(encoding="utf-8"))
        manifest = {
            "schema_version": 1, "created_utc": utc(),
            "dataset_kind": "REAL_TIME_DEMO_BROKER_RESEARCH_EXPORT",
            "trade_definition": "One fully closed, broker-reconciled position lifecycle.",
            "trades": len(trades), "broker_orders": len(events["BROKER_ORDER"]),
            "broker_deals": len(events["BROKER_DEAL"]),
            "signal_events": len(signals), "risk_events": len(risks),
            "market_bars": len(bars), "market_ticks": len(ticks),
            "account_identifiers_redacted": True,
            "source_backup_sha256": source_backup[0] if source_backup else None,
        }
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as package:
            package.writestr("manifest.json", json.dumps(manifest, indent=2))
            package.writestr("DATA_DICTIONARY.md", DATA_DICTIONARY)
            package.writestr("LOAD_DATASET.md", LOAD_GUIDE)
            package.writestr("journal/trades.csv", csv_bytes(trades))
            package.writestr("journal/trades.jsonl", json_lines(trades))
            package.writestr("journal/trade_metrics.csv", csv_bytes(metrics))
            package.writestr("journal/quality_issues.csv", csv_bytes(issues))
            for kind, rows in events.items():
                package.writestr(f"broker_events/{kind.lower()}.jsonl", json_lines(rows))
            package.writestr("signals/signals.jsonl", json_lines(signals))
            package.writestr("risk_events/events.jsonl", json_lines(risks))
            package.writestr("market_data/bars.csv", csv_bytes(bars))
            package.writestr("market_data/ticks.csv", csv_bytes(ticks))
            package.writestr("market_data/sources.csv", csv_bytes(sources))
            package.writestr("hypotheses/hypotheses.jsonl", json_lines(hypotheses))
            package.writestr("reports/performance.json", json.dumps(report, indent=2))
            package.writestr("reports/data_quality.json", json.dumps(quality, indent=2))
            try:
                import pyarrow as pa
                import pyarrow.parquet as pq
                for name, rows in (("journal/trades.parquet", trades),
                                   ("market_data/bars.parquet", bars),
                                   ("market_data/ticks.parquet", ticks)):
                    if rows:
                        buffer = io.BytesIO()
                        pq.write_table(pa.Table.from_pylist(rows), buffer, compression="zstd")
                        package.writestr(name, buffer.getvalue())
            except ImportError:
                package.writestr("market_data/PARQUET_UNAVAILABLE.md",
                                 "The exporter environment lacks pyarrow; CSV/JSON remain complete.\n")
            charts = state / "trade_charts"
            if charts.exists():
                for path in charts.iterdir():
                    if path.is_file() and path.suffix in {".html", ".png", ".json", ".js"}:
                        package.write(path, "trade_charts/" + path.name)
            else:
                package.writestr("trade_charts/README.md",
                                 "No verified market-data coverage is available for these trades.\n")
        with zipfile.ZipFile(temporary) as package:
            if package.testzip() is not None:
                raise RuntimeError("research_export_zip_crc_failed")
            if json.loads(package.read("manifest.json"))["trades"] != len(trades):
                raise RuntimeError("research_export_manifest_mismatch")
        os.replace(temporary, destination)
        hash_value = hashlib.sha256()
        with destination.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                hash_value.update(block)
        checksum = hash_value.hexdigest()
        destination.with_suffix(".sha256").write_text(
            checksum + "  " + destination.name + "\n", encoding="ascii")
        return {"archive": str(destination), "sha256": checksum,
                "bytes": destination.stat().st_size, **manifest}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path,
                        default=Path(r"E:\GPT\Inves\AA-AT-research-state"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.state, args.output)))


if __name__ == "__main__":
    main()
