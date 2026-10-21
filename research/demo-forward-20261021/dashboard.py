"""Render only broker-reconciled DEMO evidence for a prospective campaign."""

from __future__ import annotations

import html
import hashlib
import json
import math
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from forward_core import ROOT, load_inventory


def eligible_trade(record: dict) -> bool:
    required = (
        "strategy_id", "account_login", "account_server", "account_trade_mode",
        "opening_order_id", "closing_order_id", "position_id", "opening_deal_ids",
        "closing_deal_ids", "signal_utc", "entry_utc", "exit_utc",
        "broker_gross_profit", "broker_net_profit", "broker_commission", "broker_swap", "broker_fees",
        "initial_risk_account_currency", "closed_volume", "opened_volume",
    )
    if record.get("execution_kind") != "REAL_TIME_DEMO_BROKER" or not record.get("fully_closed"):
        return False
    if record.get("account_trade_mode") != "DEMO" or any(record.get(k) is None for k in required):
        return False
    if not record["opening_deal_ids"] or not record["closing_deal_ids"]:
        return False
    refs = record.get("broker_evidence")
    if not isinstance(refs, list) or len(refs) < 2:
        return False
    base = (ROOT / "campaign_evidence").resolve()
    raw_ids: dict[str, set[str]] = {"order": set(), "deal": set()}
    for ref in refs:
        try:
            path = Path(ref["path"]).resolve()
            if not path.is_relative_to(base) or not path.is_file():
                return False
            if hashlib.sha256(path.read_bytes()).hexdigest() != ref["sha256"]:
                return False
            wrapper = json.loads(path.read_text(encoding="utf-8"))
            kind = wrapper["kind"]
            if wrapper["strategy_id"] != record["strategy_id"] or kind not in raw_ids:
                return False
            raw_ids[kind].add(str(wrapper["record"]["broker_record_id"]))
        except (KeyError, TypeError, OSError, ValueError):
            return False
    if not ({str(record["opening_order_id"]), str(record["closing_order_id"])} <= raw_ids["order"]):
        return False
    if not ({str(x) for x in record["opening_deal_ids"] + record["closing_deal_ids"]} <= raw_ids["deal"]):
        return False
    try:
        if not (datetime.fromisoformat(record["signal_utc"]) <= datetime.fromisoformat(record["entry_utc"]) < datetime.fromisoformat(record["exit_utc"])):
            return False
        if abs(float(record["closed_volume"]) - float(record["opened_volume"])) > 1e-9:
            return False
        if float(record["initial_risk_account_currency"]) <= 0:
            return False
        if not all(math.isfinite(float(record[k])) for k in ("broker_gross_profit", "broker_net_profit", "broker_commission", "broker_swap", "broker_fees")):
            return False
        net = sum(float(record[k]) for k in ("broker_gross_profit", "broker_commission", "broker_swap", "broker_fees"))
        if abs(net - float(record["broker_net_profit"])) > 0.01:
            return False
    except (ValueError, TypeError, KeyError):
        return False
    return True


def read_verified_reconciliations() -> tuple[dict[str, list[dict]], int]:
    ledger = ROOT / "campaign_evidence" / "index.sqlite3"
    results: dict[str, list[dict]] = defaultdict(list)
    invalid = 0
    if not ledger.exists():
        return results, invalid
    current = ROOT / "broker_preflight_verified.json"
    if not current.exists():
        return results, invalid
    gate = json.loads(current.read_text(encoding="utf-8"))
    if gate.get("account_verification") != "VERIFIED_DEMO" or gate.get("order_routing") != "VERIFIED":
        return results, invalid
    seen = set()
    with sqlite3.connect(ledger) as db:
        rows = db.execute("SELECT strategy_id,path FROM evidence WHERE kind='reconciliation' ORDER BY utc,id")
        for strategy_id, path in rows:
            try:
                wrapper = json.loads(Path(path).read_text(encoding="utf-8"))
                record = wrapper["record"]
                key = (record.get("account_login"), record.get("position_id"),
                       record.get("opening_order_id"), record.get("closing_order_id"))
                if (eligible_trade(record) and record["strategy_id"] == strategy_id
                        and str(record["account_login"]) == str(gate.get("login"))
                        and record["account_server"] == gate.get("server") and key not in seen):
                    seen.add(key)
                    results[strategy_id].append(record)
                else:
                    invalid += 1
            except (OSError, ValueError, KeyError, TypeError):
                invalid += 1
    return results, invalid


def fmt(value: float | None, places: int = 2) -> str:
    return "—" if value is None else f"{value:.{places}f}"


def render() -> Path:
    inventory = load_inventory()
    preflight = json.loads((ROOT / "preflight_static.json").read_text(encoding="utf-8"))
    trades, invalid = read_verified_reconciliations()
    cards = []
    total = 0
    for row in inventory:
        records = trades.get(row["id"], [])
        total += len(records)
        net = sum(float(r["broker_net_profit"]) for r in records) if records else None
        er = (sum(float(r["broker_net_profit"]) / float(r["initial_risk_account_currency"]) for r in records) / len(records)) if records else None
        cards.append(f"<tr><td>{row['id']}</td><td>{html.escape(row['name'])}</td><td>{html.escape(row['implementation_status'])}</td><td>{len(records)}/20</td><td>{fmt(net)}</td><td>{fmt(er,3)}</td><td>—</td><td>{html.escape(row['blocker'])}</td></tr>")
    css = "body{font:14px system-ui;background:#101820;color:#e6edf3;margin:2rem}a{color:#7dd3fc}table{border-collapse:collapse;width:100%}td,th{padding:.55rem;border-bottom:1px solid #30404b;text-align:left;vertical-align:top}tr:hover{background:#1a2a36}.bad{color:#fca5a5}.cards{display:flex;gap:1rem;flex-wrap:wrap}.card{background:#1a2a36;padding:1rem;border-radius:.6rem;min-width:12rem}small{color:#a8b7c3}"
    body = f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>DEMO forward campaign — preflight</title><style>{css}</style><main><h1>DEMO forward campaign</h1><p class="bad">PRE-APPROVAL • broker account and routing unverified • no campaign service running</p><div class="cards"><div class="card">Strategies discovered<br><strong>18</strong></div><div class="card">Operational now<br><strong>0</strong></div><div class="card">Blocked<br><strong>18</strong></div><div class="card">Verified closed DEMO trades<br><strong>{total}/360 target</strong></div><div class="card">Broker connectivity<br><strong>UNVERIFIED</strong></div><div class="card">Active positions<br><strong>UNKNOWN</strong></div><div class="card">Safety<br><strong>ORDERS DISABLED</strong></div></div><p>Realized PnL and expectancy appear only after complete broker reconciliation. Drawdown, ranking, slippage, and live position status remain unavailable until a verified broker feed is connected. Rejected/incomplete reconciliation records: {invalid}.</p><table><thead><tr><th>ID</th><th>Strategy</th><th>Implementation</th><th>Progress</th><th>Net account currency</th><th>Expectancy R</th><th>Drawdown</th><th>Current blocker</th></tr></thead><tbody>{''.join(cards)}</tbody></table><p><small>Saved manager: {html.escape(str(preflight['manager_run_status']))}; enabled={str(preflight['manager_enabled']).lower()}. The separate <a href="../../research_outputs/comparison_dashboard.html">historical research dashboard</a> contains offline results and is excluded from every forward metric.</small></p></main></html>"""
    path = ROOT / "demo_dashboard.html"
    path.write_text(body, encoding="utf-8")
    return path


if __name__ == "__main__":
    print(render())
