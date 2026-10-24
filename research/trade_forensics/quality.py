"""Data-completeness report; missing observations are never estimated."""
from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

from .store import Warehouse, utc


def report(warehouse: Warehouse) -> dict:
    db = warehouse.db
    total = db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    verified = db.execute(
        "SELECT COUNT(*) FROM trades WHERE attribution_status='VERIFIED'").fetchone()[0]
    issues = {row[0]: row[1] for row in db.execute(
        "SELECT code,COUNT(*) FROM quality_issues GROUP BY code ORDER BY code")}
    broker = {row[0]: row[1] for row in db.execute(
        "SELECT kind,COUNT(*) FROM broker_events GROUP BY kind")}
    sources = {row[0]: row[1] for row in db.execute(
        "SELECT source_type,COUNT(*) FROM market_sources GROUP BY source_type")}
    chart_dir = warehouse.root / "trade_charts"
    charts = len(list(chart_dir.glob("[0-9a-f]*.json"))) if chart_dir.exists() else 0
    coverage = {"attribution_verified": verified,
                "broker_pnl_reconciled": total - issues.get("broker_pnl_mismatch", 0),
                "order_deal_ids_reconciled": total - len(set(row[0] for row in db.execute(
                    "SELECT trade_id FROM quality_issues WHERE code IN "
                    "('deal_id_mismatch','order_id_mismatch','broker_history_incomplete')"))),
                "charts_with_recorded_candles": charts}
    return {
        "generated_utc": utc(), "trade_definition": "one fully closed broker position lifecycle",
        "total_trades": total, "verified_attribution": verified,
        "partially_verified_or_unresolved": total - verified,
        "coverage_counts": coverage,
        "coverage_fraction": {key: count / total if total else None
                              for key, count in coverage.items()},
        "issues_by_code": issues, "broker_events_by_kind": broker,
        "market_sources_by_type": sources,
        "market_bar_rows": db.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0],
        "market_tick_rows": db.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0],
        "notes": [
            "Broker-verified close does not imply complete Bid/Ask or intrabar coverage.",
            "Missing SL/TP modification history is recorded as unavailable, not reconstructed.",
            "Strategy attribution and price-path coverage are independent quality dimensions.",
        ],
    }


def write_report(warehouse: Warehouse) -> Path:
    destination = warehouse.root / "reports"
    destination.mkdir(exist_ok=True)
    path = destination / "data_quality.json"
    temporary = destination / ("." + path.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(report(warehouse), indent=2, sort_keys=True),
                         encoding="utf-8")
    os.replace(temporary, path)
    return path
