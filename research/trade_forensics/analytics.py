"""Verified-trade analytics; hypothetical improvements remain separate."""
from __future__ import annotations

import json
import math
import os
import random
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from statistics import mean, pstdev
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .store import Warehouse, number, utc


def session_labels(when: str | None) -> list[str]:
    if not when:
        return ["UNKNOWN"]
    moment = datetime.fromisoformat(when)
    if moment.tzinfo is None:
        return ["UNKNOWN"]
    try:
        london = moment.astimezone(ZoneInfo("Europe/London"))
        new_york = moment.astimezone(ZoneInfo("America/New_York"))
        tokyo = moment.astimezone(ZoneInfo("Asia/Tokyo"))
    except ZoneInfoNotFoundError:
        return ["TIMEZONE_DATA_UNAVAILABLE"]
    labels = []
    if london.weekday() < 5 and 8 <= london.hour < 17:
        labels.append("LONDON")
    if new_york.weekday() < 5 and 8 <= new_york.hour < 17:
        labels.append("NEW_YORK")
    if tokyo.weekday() < 5 and 9 <= tokyo.hour < 18:
        labels.append("ASIA")
    return labels or ["OTHER"]


def wilson(wins: int, count: int) -> list[float] | None:
    if not count:
        return None
    z = 1.95996398454
    p = wins / count
    denom = 1 + z * z / count
    centre = (p + z * z / (2 * count)) / denom
    half = z * math.sqrt((p * (1 - p) + z * z / (4 * count)) / count) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def bootstrap_mean(values: list[float], seed: int) -> list[float] | None:
    if len(values) < 2:
        return None
    rng = random.Random(seed)
    count = len(values)
    samples = sorted(mean(rng.choices(values, k=count)) for _ in range(2000))
    return [samples[49], samples[1949]]


def statistics(rows: list[dict], seed: int = 0) -> dict:
    pnl = [float(number(row["net_pnl"]) or Decimal(0)) for row in rows]
    r_values = [float(number(row["realized_r"])) for row in rows
                if number(row["realized_r"]) is not None]
    positive = sum(value for value in pnl if value > 0)
    negative = -sum(value for value in pnl if value < 0)
    wins = sum(value > 0 for value in pnl)
    equity = peak = drawdown = 0.0
    for value in pnl:
        equity += value
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)
    durations = [float(row["holding_seconds"]) for row in rows
                 if row["holding_seconds"] is not None]
    costs = [sum(float(number(row[field]) or 0)
                 for field in ("commission", "swap", "fees")) for row in rows]
    return {
        "closed_trades": len(rows), "wins": wins,
        "win_rate": wins / len(rows) if rows else None,
        "win_rate_wilson_95": wilson(wins, len(rows)),
        "gross_profit": round(positive, 8), "gross_loss": round(negative, 8),
        "net_pnl": round(sum(pnl), 8),
        "profit_factor": positive / negative if negative > 0 else None,
        "expectancy_r": mean(r_values) if r_values else None,
        "expectancy_r_bootstrap_95": bootstrap_mean(r_values, seed),
        "max_closed_trade_drawdown_currency": round(drawdown, 8),
        "average_holding_seconds": mean(durations) if durations else None,
        "average_broker_cost_currency": mean(costs) if costs else None,
        "trade_r_mean_over_std": (mean(r_values) / pstdev(r_values)
                                  if len(r_values) > 1 and pstdev(r_values) > 0 else None),
        "risk_adjusted_note": "Per-trade R ratio, not an annualized Sharpe ratio.",
        "sample_warning": "Small sample; no edge claim." if len(rows) < 100 else
                          "100 trades is an initial screen, not proof of an edge.",
    }


def report(warehouse: Warehouse) -> dict:
    rows = [dict(row) for row in warehouse.db.execute(
        """SELECT strategy_id,symbol,direction,entry_utc,exit_utc,net_pnl,
           realized_r,holding_seconds,commission,swap,fees FROM trades
           WHERE attribution_status='VERIFIED' ORDER BY exit_utc,trade_id""")]
    by_strategy = defaultdict(list)
    by_symbol = defaultdict(list)
    by_session = defaultdict(list)
    by_direction = defaultdict(list)
    for row in rows:
        sid = row["strategy_id"]
        by_strategy[sid].append(row)
        by_symbol[(sid, row["symbol"])].append(row)
        by_direction[(sid, row["direction"])].append(row)
        for label in session_labels(row["entry_utc"]):
            by_session[(sid, label)].append(row)
    issue_counts = {
        row[0]: row[1] for row in warehouse.db.execute(
            "SELECT code,COUNT(*) FROM quality_issues GROUP BY code")
    }
    total = warehouse.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    return {
        "generated_utc": utc(), "definition": "One fully closed broker-reconciled position lifecycle, not each deal.",
        "total_research_trades": total, "verified_attribution_trades": len(rows),
        "strategy": {key: statistics(value, sum(map(ord, key)))
                     for key, value in sorted(by_strategy.items())},
        "strategy_symbol": {f"{sid}|{symbol}": statistics(value, sum(map(ord, sid+symbol)))
                            for (sid, symbol), value in sorted(by_symbol.items())},
        "strategy_session": {f"{sid}|{session}": statistics(value, sum(map(ord, sid+session)))
                             for (sid, session), value in sorted(by_session.items())},
        "strategy_direction": {f"{sid}|{direction}": statistics(value, sum(map(ord, sid+direction)))
                               for (sid, direction), value in sorted(by_direction.items())},
        "data_quality": {
            "issue_counts": issue_counts,
            "unresolved_attribution": total - len(rows),
            "market_bars": warehouse.db.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0],
            "market_ticks": warehouse.db.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0],
            "source_artifacts": warehouse.db.execute("SELECT COUNT(*) FROM source_artifacts").fetchone()[0],
        },
        "limits": [
            "No entry/exit Bid/Ask archive or campaign market-history archive is presently verified.",
            "SL/TP modification history is unavailable unless an explicit source event is found.",
            "Broker offsets and daylight-saving conversion require per-trade validation.",
            "Closed-trade drawdown excludes intratrade equity movements.",
            "Multiple strategy and symbol comparisons require selection-bias caution.",
        ],
    }


def write_report(warehouse: Warehouse) -> Path:
    destination = warehouse.root / "reports"
    destination.mkdir(exist_ok=True)
    data = report(warehouse)
    final = destination / "performance.json"
    temporary = destination / ("." + final.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, final)
    return final
