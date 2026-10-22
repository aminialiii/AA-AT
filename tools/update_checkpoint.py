"""Persist campaign progress only when the broker-ledger snapshot changes."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    path = ROOT / "CHECKPOINT.json"
    current = json.loads(path.read_text(encoding="utf-8"))
    status = json.loads((ROOT / "docs/operational_status.json").read_text(encoding="utf-8"))
    progress = {"verified_closed": status["completed_trades"],
                "per_strategy_target": status["target_per_strategy"],
                "nominal_target": status["overall_target"],
                "currently_eligible_target": status["eligible_target"],
                "minimum_not_maximum": status.get("continuous_after_milestone", False)}
    risk_policy = {"sha256": status.get("risk_policy_sha256"),
                   "max_positions_portfolio": status.get("max_positions_portfolio"),
                   "max_open_risk_fraction": status.get("max_open_risk_fraction")}
    worker_status = {sid: {"status": row["status"], "closed": row["closed"]}
                     for sid, row in status["workers"].items()}
    halted = bool(status.get("routing_halted_by_local_stop"))
    if halted:
        for row in worker_status.values():
            if row["status"] not in {"BLOCKED", "STOPPED"}:
                row["status"] = "HALTED_BY_SAFETY_STOP"
    operational_control = {"routing_halted": halted,
                           "snapshot_stale": bool(status.get("service_snapshot_stale")),
                           "command_center_url": "http://127.0.0.1:8765/",
                           "control_bridge_runtime_verified": bool(
                               status.get("control_bridge_version_at_observation") == 1
                               and not status.get("service_snapshot_stale") and not halted)}
    if (current.get("campaign_progress") == progress and current.get("worker_status") == worker_status
            and current.get("risk_policy") == risk_policy
            and current.get("operational_control") == operational_control):
        print("checkpoint_unchanged")
        return
    current["campaign_progress"] = progress
    current["worker_status"] = worker_status
    current["risk_policy"] = risk_policy
    current["operational_control"] = operational_control
    if halted:
        current["phase"] = "dashboard_operational_trading_safety_stop_pending_manual_review"
        current["last_successful_operation"] = "Authenticated loopback dashboard running; trading source rolled back; safety stop remains set"
        current["next_recommended_action"] = "Review and explicitly clear the local safety stop, then reverify DEMO exposure before restarting the trading task"
        if "trading_safety_stop_requires_manual_review" not in current["blockers"]:
            current["blockers"].append("trading_safety_stop_requires_manual_review")
    elif current.get("phase") == "dashboard_operational_trading_safety_stop_pending_manual_review":
        current["phase"] = "continuous_demo_campaign_with_versioned_portfolio_policy"
        current["blockers"] = [x for x in current["blockers"] if x != "trading_safety_stop_requires_manual_review"]
    current["git_commit_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not halted:
        current["last_successful_operation"] = f"Broker ledger reconciled {progress['verified_closed']} closed DEMO trades"
    current["updated_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print("checkpoint_updated")


if __name__ == "__main__":
    main()
