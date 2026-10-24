"""Source-labeled, read-only V3 research status for the staged dashboard."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .market_import import DEFAULT_CATALOG, PERIOD_END_EXCLUSIVE, PERIOD_START

WORKTREE = Path(r"E:\GPT\Inves\AA-AT-recovery-20261023")
STATE = Path(r"E:\GPT\Inves\AA-AT-research-state\v3")


def build_status(catalog: Path = DEFAULT_CATALOG, state: Path = STATE) -> dict:
    inventory = json.loads((WORKTREE / "research_outputs" / "inventory.json").read_text(encoding="utf-8"))
    sources = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted((catalog / "sources").glob("*.json"))]
    builds = [json.loads(path.read_text(encoding="utf-8"))
              for path in sorted((state / "builds").glob("*.json"))]
    parity = [json.loads(path.read_text(encoding="utf-8"))
              for path in sorted((state / "parity").glob("*.json"))]
    latest_parity = next((row for row in reversed(parity)
                          if row.get("strategy_id") == "S04" and row.get("passed")), None)
    strategies = []
    for item in inventory["strategies"]:
        sid = item["strategy_id"]
        row = {"id": sid, "name": item["name"],
               "frozen_source_sha256": item["sourceSHA256"],
               "status": "DATA_BLOCKED" if sid in {f"S{i:02d}" for i in range(1,6)}
                         else "IMPLEMENTATION_BLOCKED",
               "historical_run_count": 0, "simulated_trades": 0,
               "blocker": ("No complete, source-verified 36-month market and cost dataset"
                           if sid in {f"S{i:02d}" for i in range(1,6)}
                           else item.get("blocker") or "No faithful isolated historical implementation")}
        if sid == "S04":
            row.update({"ea_compiled": bool(builds),
                        "python_rule_parity": "PASS" if latest_parity else "NOT_TESTED",
                        "ea_runtime_parity": "NOT_TESTED",
                        "ea_binary_sha256": builds[-1]["binary_sha256"] if builds else None})
        strategies.append(row)
    coverage = [{"symbol": row["symbol"], "source_type": row["source_type"],
                 "rows": row["row_count"],
                 "first_utc": row.get("first_utc", row.get("first_utc_assuming_fixed_offset")),
                 "last_utc": row.get("last_utc", row.get("last_utc_assuming_fixed_offset")),
                 "utc_verified": row["utc_mapping_verified"],
                 "full_period_eligible": row["eligible_for_three_year_backtest"],
                 "source_sha256": row["source_sha256"]}
                for row in sources]
    return {"schema_version": 1, "observed_utc": datetime.now(timezone.utc).isoformat(),
            "evidence_class": "RESEARCH_STATUS_ONLY",
            "research_period_utc": [PERIOD_START, PERIOD_END_EXCLUSIVE],
            "historical_backtest_runs": 0, "simulated_trades": 0,
            "broker_confirmed_demo_trades_included": 0,
            "source_count": len(sources), "source_rows": sum(r["row_count"] for r in sources),
            "coverage": coverage, "strategies": strategies,
            "portfolio_backtest": "NOT_STARTED", "gold_demo_activation": "NOT_AUTHORIZED"}
