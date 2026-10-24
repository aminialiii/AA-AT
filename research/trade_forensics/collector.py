"""Low-impact journal collector. Never imports the trading service or MT5."""
from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .store import Warehouse, import_backup, import_live
from .analytics import write_report
from .quality import write_report as write_quality_report

DEFAULT_STATE = Path(r"E:\GPT\Inves\AA-AT-research-state")
DEFAULT_WORKSPACE = Path(r"E:\GPT\Inves")
DEFAULT_BOOTSTRAP = Path(r"D:\AA-AT-Backups\AA-AT-Backup-V1.zip")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def status_file(root: Path, value: dict) -> None:
    target = root / "collector-status.json"
    temporary = target.with_name("." + target.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, target)


def collect_once(state: Path, workspace: Path,
                 bootstrap: Path | None = DEFAULT_BOOTSTRAP) -> dict:
    warehouse = Warehouse(state)
    try:
        first = warehouse.db.execute("SELECT COUNT(*) FROM trades").fetchone()[0] == 0
        bootstrap_result = None
        if first and bootstrap is not None:
            if not bootstrap.is_file():
                raise RuntimeError("verified_bootstrap_archive_missing")
            bootstrap_result = import_backup(warehouse, bootstrap, workspace)
        live_result = import_live(warehouse, workspace)
        if ((bootstrap_result and bootstrap_result["new_trades"] > 0) or
                live_result["new_trades"] > 0 or
                not (state / "reports" / "performance.json").is_file()):
            write_report(warehouse)
        if (live_result["new_trades"] > 0 or
                not (state / "reports" / "data_quality.json").is_file()):
            write_quality_report(warehouse)
        result = {
            "status": "HEALTHY", "observed_utc": now(),
            "bootstrap": bootstrap_result, "live": live_result,
            "research_closed_trades": warehouse.db.execute(
                "SELECT COUNT(*) FROM trades").fetchone()[0],
            "unresolved_attribution": warehouse.db.execute(
                "SELECT COUNT(*) FROM trades WHERE attribution_status!='VERIFIED'").fetchone()[0],
            "source_artifacts": warehouse.db.execute(
                "SELECT COUNT(*) FROM source_artifacts").fetchone()[0],
            "market_bars": warehouse.db.execute(
                "SELECT COUNT(*) FROM market_bars").fetchone()[0],
            "market_ticks": warehouse.db.execute(
                "SELECT COUNT(*) FROM market_ticks").fetchone()[0],
        }
        status_file(state, result)
        return result
    finally:
        warehouse.close()


def serve(state: Path, workspace: Path, bootstrap: Path | None, interval: int) -> None:
    import msvcrt
    state.mkdir(parents=True, exist_ok=True)
    lock = (state / "collector.lock").open("a+b")
    try:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        lock.close()
        raise RuntimeError("collector_already_running") from exc
    failures = 0
    while True:
        try:
            collect_once(state, workspace, bootstrap)
            failures = 0
            time.sleep(interval)
        except Exception as exc:
            failures += 1
            status_file(state, {
                "status": "FAILED", "observed_utc": now(),
                "error": str(exc)[:240], "attempt": failures,
                "trading_execution_unaffected": True,
            })
            time.sleep(min(interval * 2 ** min(failures - 1, 4), 3600))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--workspace", type=Path, default=DEFAULT_WORKSPACE)
    parser.add_argument("--bootstrap", type=Path, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--interval", type=int, default=300)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.once == args.serve or not 60 <= args.interval <= 3600:
        parser.error("choose --once or --serve and interval 60..3600 seconds")
    if args.once:
        print(json.dumps(collect_once(args.state, args.workspace, args.bootstrap)))
    else:
        serve(args.state, args.workspace, args.bootstrap, args.interval)


if __name__ == "__main__":
    main()
