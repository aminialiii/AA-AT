"""Read-only projection of broker-reconciled DEMO evidence for the UI."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def timestamp(value: str | None) -> float | None:
    try:
        return datetime.fromisoformat(value).timestamp() if value else None
    except (ValueError, TypeError):
        return None


def ledger(runtime: Path, max_trades: int = 5000) -> dict:
    path = runtime / "campaign.sqlite3"
    result = {"closed_count": 0, "win_rate": None, "daily_closed_pnl": None,
              "trades": [], "curve": [], "events": [], "open_intents": None}
    if not path.exists():
        return result
    con = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=2)
    try:
        con.row_factory = sqlite3.Row
        count, wins = con.execute("SELECT COUNT(*),SUM(CASE WHEN json_extract(record_json,'$.broker_net_profit')>0 THEN 1 ELSE 0 END) FROM closed").fetchone()
        result["closed_count"] = count
        result["win_rate"] = wins / count if count else None
        result["open_intents"] = con.execute(
            "SELECT COUNT(*) FROM intents WHERE state IN ('OPEN','PENDING','PREPARED')").fetchone()[0]
        rows = con.execute("SELECT strategy,record_json,closed_utc FROM closed "
                           "ORDER BY closed_utc DESC,position_id DESC LIMIT ?", (max_trades,)).fetchall()
        today = datetime.now(timezone.utc).date().isoformat()
        daily = 0.0
        cumulative = 0.0
        for row in reversed(rows):
            r = json.loads(row["record_json"])
            if (r.get("execution_kind") != "REAL_TIME_DEMO_BROKER" or
                    r.get("account_trade_mode") != "DEMO" or not r.get("fully_closed")):
                raise RuntimeError("ineligible_record_in_demo_ledger")
            net = float(r["broker_net_profit"])
            cumulative += net
            result["curve"].append({"time": r["exit_utc"], "value": round(cumulative, 4)})
            if r["exit_utc"][:10] == today:
                daily += net
            result["trades"].append({"strategy": row["strategy"], "symbol": r["symbol"],
                                     "entry_utc": r["entry_utc"], "exit_utc": r["exit_utc"],
                                     "net_usd": net, "risk_r": net / float(r["initial_risk_account_currency"]),
                                     "opening_order_id": r.get("opening_order_id"),
                                     "closing_deal_ids": r.get("closing_deal_ids", [])})
        result["trades"] = result["trades"][-100:][::-1]
        result["daily_closed_pnl"] = round(daily, 4)
        result["events"] = [dict(x) for x in con.execute(
            "SELECT observed_utc,scope,reason FROM safety_events "
            "ORDER BY observed_utc DESC LIMIT 40")]
    finally:
        con.close()
    return result


def worker_logs(runtime: Path, worker_id: str, limit: int = 40) -> list[dict]:
    if worker_id not in {f"S{i:02d}" for i in range(1, 19)}:
        raise ValueError("invalid_worker")
    folder = runtime / "evidence" / worker_id
    if not folder.is_dir():
        return []
    result = []
    for path in sorted(folder.glob("*.json"), reverse=True)[:min(100, limit)]:
        row = read_json(path)
        if row.get("strategy") != worker_id:
            continue
        payload = row.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        # Never expose raw broker records, account identifiers, or signal keys.
        summary = payload.get("reason") or payload.get("symbol") or row.get("kind")
        result.append({"utc": row.get("utc"), "kind": row.get("kind"),
                       "summary": str(summary)[:240]})
    return result


def snapshot(runtime: Path, repo: Path, control_store, *, now: float | None = None) -> dict:
    now = datetime.now(timezone.utc).timestamp() if now is None else now
    st = read_json(runtime / "status.json")
    perf = read_json(runtime / "performance_report.json")
    sync = read_json(repo.parent / "AA-AT-sync-state" / "status.json")
    checkpoint = read_json(repo / "CHECKPOINT.json")
    observed = timestamp(st.get("observed_utc"))
    age = None if observed is None else max(0, now - observed)
    fresh = age is not None and age <= 15
    verified = bool(fresh and st.get("broker_status") == "HEALTHY" and st.get("demo_verified"))
    local = ledger(runtime)
    performance_valid = (perf.get("evidence_kind") == "BROKER_RECONCILED_DEMO_ONLY" and
                         perf.get("total_completed_trades") == local["closed_count"])
    perf_workers = perf.get("strategies", {}) if performance_valid else {}
    workers = []
    for w in st.get("workers", []):
        sid = w["id"]
        m = perf_workers.get(sid, {})
        workers.append({
            "id": sid, "name": w.get("name", sid), "status": w.get("status", "UNKNOWN"),
            "blocker": w.get("reason"), "mode": control_store.mode(sid),
            "trading_enabled": bool(verified and w.get("status") == "ACTIVE" and
                                    control_store.mode(sid) == "RUNNING" and not control_store.emergency()),
            "closed_trades": w.get("closed_trades", 0), "milestone": 100,
            "win_rate": m.get("win_rate"), "net_pnl": w.get("net_demo_pnl"),
            "expectancy_r": m.get("expectancy_R", w.get("expectancy_R")),
            "profit_factor": m.get("profit_factor_usd"),
            "drawdown_r": m.get("max_closed_trade_drawdown_R"),
            "average_risk_reward": None, "unrealized_pnl": w.get("unrealized_pnl") if verified else None,
            "open_positions": w.get("open_positions") if verified else None,
            "risk_exposure": w.get("risk_exposure") if verified else None,
            "last_signal": w.get("last_signal"), "last_execution": w.get("last_execution"),
            "heartbeat": w.get("heartbeat"), "uptime_s": w.get("uptime_s"),
            "cpu_percent": None, "memory_bytes": None,
            "resource_note": "Logical asyncio task in a shared Python process",
        })
    errors = {e["scope"]: e for e in reversed(local["events"]) if e["scope"].startswith("S")}
    for w in workers:
        w["recent_error"] = errors.get(w["id"], {}).get("reason")
    balance = st.get("account_balance") if verified else None
    equity = st.get("account_equity") if verified else None
    unrealized = st.get("account_profit") if verified else None
    exposure_verified = verified
    return {
        "observed_utc": st.get("observed_utc"), "server_utc": datetime.now(timezone.utc).isoformat(),
        "age_s": age, "stale": not fresh, "broker_status": st.get("broker_status", "UNKNOWN"),
        "broker_issue": st.get("broker_issue"), "demo_verified": verified,
        "control_bridge": st.get("control_bridge_version") == 1 and fresh,
        "emergency_stop": (control_store.emergency() or (runtime / "EMERGENCY_STOP").exists()
                           or bool(st.get("emergency_stop"))),
        "portfolio": {
            "balance": balance, "equity": equity, "realized_pnl": st.get("realized_demo_pnl"),
            "unrealized_pnl": unrealized,
            "total_pnl": None if unrealized is None else float(st.get("realized_demo_pnl", 0)) + unrealized,
            "daily_closed_pnl": local["daily_closed_pnl"], "win_rate": local["win_rate"],
            "peak_equity_drawdown": st.get("peak_equity_drawdown_fraction") if verified else None,
            "risk_utilization": st.get("risk_utilization_fraction") if verified else None,
            "open_positions": st.get("active_positions") if verified else None,
            "pending_orders": st.get("pending_orders") if verified else None,
            "local_open_intents": local["open_intents"], "exposure_verified": exposure_verified,
            "max_positions": st.get("max_positions_portfolio", 5),
            "max_open_risk_fraction": st.get("max_open_risk_fraction", .02),
            "max_trade_fraction": .0025, "daily_loss_halt": .01, "peak_drawdown_halt": .02,
            "closed_trades": local["closed_count"], "active_workers": sum(w["status"] == "ACTIVE" for w in workers),
            "blocked_workers": sum(w["status"] == "BLOCKED" for w in workers),
            "total_workers": len(workers),
        },
        "workers": workers, "closed_pnl_curve": local["curve"], "recent_trades": local["trades"],
        "activity": local["events"], "commands": control_store.recent(),
        "control_audit": control_store.audit_recent(),
        "git_sync": {"state": sync.get("state"), "last_check_utc": sync.get("last_check_utc"),
                     "pull_request": (sync.get("pull_request") or {}).get("url")},
        "checkpoint": {"updated_utc": checkpoint.get("updated_utc"), "phase": checkpoint.get("phase")},
        "limitations": ["Historical equity curve is not recorded; chart shows realized closed-trade PnL.",
                        "Logical workers do not have separately measurable CPU or memory.",
                        "Open exposure is unavailable when the broker snapshot is not verified."],
    }
