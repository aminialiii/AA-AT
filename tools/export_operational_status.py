"""Export a small account-free, broker-ledger-checked status snapshot."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT.parent / "research/demo-live-20261021/runtime"
OUT = ROOT / "docs/operational_status.json"
VOLATILE_KEYS = {"source_observed_utc", "safety_event_count",
                 "risk_utilization_fraction", "peak_equity_drawdown_fraction"}


def meaningful_equal(left, right):
    return ({k: v for k, v in left.items() if k not in VOLATILE_KEYS}
            == {k: v for k, v in right.items() if k not in VOLATILE_KEYS})


def main():
    source = json.loads((RUNTIME / "status.json").read_text(encoding="utf-8"))
    uri = (RUNTIME / "campaign.sqlite3").resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=5) as db:
        closed = db.execute("SELECT COUNT(*) FROM closed").fetchone()[0]
    if closed != source["completed_trades"]:
        raise RuntimeError("status_and_broker_ledger_disagree")
    workers = {x["id"]: {"status": x["status"], "closed": x["closed_trades"],
                         "net_demo_pnl": x["net_demo_pnl"], "expectancy_R": x["expectancy_R"],
                         "max_closed_drawdown_R": x["max_closed_drawdown_R"]}
               for x in source["workers"]}
    if len(workers) != 18 or sum(x["closed"] for x in workers.values()) != closed:
        raise RuntimeError("worker_counts_inconsistent")
    report_path = RUNTIME / "performance_report.json"
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        if report.get("total_completed_trades") == closed and report.get("evidence_kind") == "BROKER_RECONCILED_DEMO_ONLY":
            for sid, metrics in report["strategies"].items():
                workers[sid]["profit_factor"] = metrics.get("profit_factor_usd")
    data = {
        "source_kind": "BROKER_RECONCILED_DEMO_STATUS_SNAPSHOT",
        "source_observed_utc": source["observed_utc"],
        "broker_status": source["broker_status"],
        "demo_verified_at_observation": bool(source["demo_verified"]),
        "total_strategies": source["total_strategies"],
        "active_strategies": source["active_strategies"],
        "blocked_strategies": source["blocked_strategies"],
        "active_positions": source["active_positions"],
        "completed_trades": closed,
        "target_per_strategy": source["target_per_strategy"],
        "overall_target": source["overall_target"],
        "eligible_target": source["eligible_target"],
        "realized_demo_pnl": source["realized_demo_pnl"],
        "risk_utilization_fraction": source["risk_utilization_fraction"],
        "peak_equity_drawdown_fraction": source["peak_equity_drawdown_fraction"],
        "safety_event_count": source["safety_events"],
        "workers": workers,
        "worker_graph_evidence": [f"{sid}:{value['status']}:{value['closed']}" for sid, value in workers.items()],
        "limitations": "Snapshot only. Raw order/deal evidence stays local; account identity and credentials are omitted."
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    old = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else None
    # Floating equity marks move on every tick. Keep those values in the live
    # local dashboard, but do not create Git commits solely for tiny mark noise.
    if old is not None and meaningful_equal(old, data):
        print(json.dumps({"changed": False, "closed": closed}))
        return
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"changed": True, "closed": closed}))


if __name__ == "__main__":
    main()
