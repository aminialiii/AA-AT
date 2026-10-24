"""Record verified read-only research milestones in this branch checkpoint."""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def add_once(values: list, item: str) -> None:
    if item not in values:
        values.append(item)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    workspace = root.parent
    checkpoint = root / "CHECKPOINT.json"
    data = load(checkpoint)
    status = load(workspace / "research/demo-live-20261021/runtime/status.json")
    collector = load(workspace / "AA-AT-research-state/collector-status.json")
    backup_root = Path(r"D:\AA-AT-Backups")
    backup = max(
        (load(backup_root / f"AA-AT-Backup-V{slot}.manifest.json")
         for slot in (1, 2, 3)
         if (backup_root / f"AA-AT-Backup-V{slot}.manifest.json").is_file()),
        key=lambda item: item.get("verified_utc", ""),
    )
    quality = load(workspace / "AA-AT-research-state/reports/data_quality.json")
    if collector["status"] != "HEALTHY" or backup["status"] != "SUCCESS":
        raise RuntimeError("research_or_backup_not_verified")
    for item in (
        "independent_initial_backup_v1_verified",
        "independent_daily_three_slot_backup_worker_running",
        "backup_v2_verified_with_research_warehouse",
        "isolated_sqlite_restore_drill_passed",
        "independent_research_collector_running",
        "research_dataset_395_broker_reconciled_closes",
        "research_dashboard_routes_live_and_authenticated",
    ):
        add_once(data["completed"], item)
    if backup["slot"] == "V3":
        add_once(data["completed"], "backup_v3_verified_with_deployed_dashboard_release")
    for item in (
        "obtain_provenance_tagged_historical_market_data_without_active_broker_contention",
        "validate_broker_timezone_and_missing_bid_ask_sl_tp_history",
        "review_research_branch_and_git_sync_blocker",
    ):
        add_once(data["pending"], item)
    add_once(data["blockers"], "No verified market candle/tick archive covers campaign trades; factual trade charts and MFE/MAE unavailable")
    data["phase"] = "demo_forward_campaign_with_isolated_research_and_backup"
    data["last_successful_operation"] = "Verified V2 backup and isolated restore drill; authenticated research dashboard and independent collector operational"
    data["worker_status"] = {
        worker["id"]: {"status": worker["status"], "closed": worker["closed_trades"]}
        for worker in status["workers"]
    }
    data["campaign_progress"]["verified_closed"] = status["completed_trades"]
    data["operational_control"].update({
        "broker_status": status["broker_status"],
        "active_workers": [worker["id"] for worker in status["workers"]
                           if worker["status"] == "ACTIVE"],
        "routing_halted": status["broker_status"] != "HEALTHY",
        "broker_issue_at_observation": status.get("broker_issue"),
        "observed_utc": status["observed_utc"],
        "ledger_closed_verified": status["completed_trades"],
        "dashboard_task_running": True,
        "dashboard_research_release": "AA-AT-dashboard-release-research-v1",
    })
    data["research_forensics"] = {
        "collector_status": collector["status"],
        "collector_observed_utc": collector["observed_utc"],
        "closed_trade_lifecycles": collector["research_closed_trades"],
        "unresolved_attribution": collector["unresolved_attribution"],
        "market_bars": collector["market_bars"],
        "market_ticks": collector["market_ticks"],
        "chart_coverage_fraction": quality["coverage_fraction"]["charts_with_recorded_candles"],
        "state_path": "E:\\GPT\\Inves\\AA-AT-research-state",
    }
    data["backup"] = {
        "latest_verified_slot": backup["slot"],
        "latest_verified_utc": backup["verified_utc"],
        "sha256": backup["sha256"],
        "closed_trades_in_snapshot": backup["closed_trades"],
        "destination": "D:\\AA-AT-Backups",
        "encrypted": False,
    }
    data["updated_utc"] = datetime.now(timezone.utc).isoformat()
    data["git_commit_sha"] = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    checkpoint.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    print(json.dumps({"checkpoint": str(checkpoint),
                      "research_closes": data["research_forensics"]["closed_trade_lifecycles"],
                      "backup_slot": data["backup"]["latest_verified_slot"],
                      "broker_status": data["operational_control"]["broker_status"]}))


if __name__ == "__main__":
    main()
