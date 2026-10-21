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
                "currently_eligible_target": status["eligible_target"]}
    worker_status = {sid: {"status": row["status"], "closed": row["closed"]}
                     for sid, row in status["workers"].items()}
    if current.get("campaign_progress") == progress and current.get("worker_status") == worker_status:
        print("checkpoint_unchanged")
        return
    current["campaign_progress"] = progress
    current["worker_status"] = worker_status
    current["git_commit_sha"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    current["last_successful_operation"] = f"Broker ledger reconciled {progress['verified_closed']} closed DEMO trades"
    current["updated_utc"] = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
    print("checkpoint_updated")


if __name__ == "__main__":
    main()
