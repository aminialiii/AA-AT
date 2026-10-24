"""One-shot daily analytics job independent of trading and dashboard services."""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .priority3 import run

DEFAULT_STATE = Path(r"E:\GPT\Inves\AA-AT-research-state")
DEFAULT_BACKUPS = Path(r"D:\AA-AT-Backups")


def daily(state: Path, backups: Path, git_commit: str) -> dict:
    status_path = state / "analytics" / "daily-status.json"
    backup = json.loads((backups / "backup-status.json").read_text(encoding="utf-8"))
    if backup.get("status") != "SUCCESS" or not backup.get("sha256"):
        raise RuntimeError("last_backup_not_verified")
    result = run(state, git_commit=git_commit, backup_sha256=backup["sha256"])
    update = {"status": "SUCCESS", "observed_utc": datetime.now(timezone.utc).isoformat(),
              "analysis_run_id": result["analysis_run_id"],
              "cutoff": result["cutoff"],
              "market_data_gate": not result["data_quality"]["market_ticks"]}
    temporary = status_path.with_name(".daily-status." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(update, indent=2), encoding="utf-8")
    os.replace(temporary, status_path)
    return update


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--backups", type=Path, default=DEFAULT_BACKUPS)
    parser.add_argument("--git-commit", required=True)
    args = parser.parse_args()
    import msvcrt
    lock_path = args.state / "analytics" / "daily.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise RuntimeError("daily_analytics_already_running") from exc
        try:
            result = daily(args.state, args.backups, args.git_commit)
        except Exception as exc:
            failure = {"status": "FAILED",
                       "observed_utc": datetime.now(timezone.utc).isoformat(),
                       "error": str(exc)[:240], "trading_execution_unaffected": True}
            target = args.state / "analytics" / "daily-status.json"
            temporary = target.with_name(".daily-status." + uuid.uuid4().hex)
            temporary.write_text(json.dumps(failure, indent=2), encoding="utf-8")
            os.replace(temporary, target)
            raise
        finally:
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
    if sys.stdout is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
