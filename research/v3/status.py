"""Source-labeled, read-only V3 research status for the staged dashboard."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, PERIOD_END_EXCLUSIVE, PERIOD_START
from .market_status import assess

WORKTREE = Path(r"E:\GPT\Inves\AA-AT-recovery-20261023")
STATE = Path(r"E:\GPT\Inves\AA-AT-research-state\v3")


def build_status(catalog: Path = DEFAULT_CATALOG, state: Path = STATE) -> dict:
    inventory = json.loads((WORKTREE / "research_outputs" / "inventory.json").read_text(encoding="utf-8"))
    sources = [json.loads(path.read_text(encoding="utf-8"))
               for path in sorted((catalog / "sources").glob("*.json"))]
    builds = [json.loads(path.read_text(encoding="utf-8"))
              for path in sorted((state / "builds").glob("*.json"),
                                 key=lambda path: path.stat().st_mtime_ns)]
    inputs = [json.loads(path.read_text(encoding="utf-8"))
              for path in sorted((catalog / "parity_inputs").glob("*.json"))]
    parity = [json.loads(path.read_text(encoding="utf-8"))
              for path in sorted((state / "parity").glob("*.json"))]
    latest_parity = next((row for row in reversed(parity)
                          if row.get("strategy_id") == "S04" and row.get("passed")), None)
    probe_path = state / "tester-probe.json"
    probe = json.loads(probe_path.read_text(encoding="utf-8")) if probe_path.is_file() else None
    probe_analysis_path = state / "tester-probe-analysis.json"
    probe_analysis = json.loads(probe_analysis_path.read_text(encoding="utf-8")) if probe_analysis_path.is_file() else None
    provider_state = DEFAULT_VAULT / "provider-state" / "dukascopy.json"
    provider = json.loads(provider_state.read_text(encoding="utf-8")) if provider_state.is_file() else None
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
                        "runtime_comparator": "IMPLEMENTED_AWAITING_TESTER_TRACE",
                        "verified_parity_input_sets": sum(bool(x.get("tester_clock_verified")) for x in inputs),
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
    observed = datetime.now(timezone.utc)
    market_symbols = sorted({row["symbol"] for row in sources} | {"XAUUSD"})
    markets = [assess(symbol=symbol, now_utc=observed,
                      schedule_timezone=None, sessions=(), schedule_source=None,
                      last_quote_utc=None, quote_max_age=timedelta(minutes=5))
               for symbol in market_symbols]
    return {"schema_version": 1, "observed_utc": observed.isoformat(),
            "evidence_class": "RESEARCH_STATUS_ONLY",
            "research_period_utc": [PERIOD_START, PERIOD_END_EXCLUSIVE],
            "historical_backtest_runs": 0, "simulated_trades": 0,
            "broker_confirmed_demo_trades_included": 0,
            "source_count": len(sources), "source_rows": sum(r["row_count"] for r in sources),
            "parity_input_sets": len(inputs),
            "historical_provider": {"next_request_utc": provider.get("next_request_utc") if provider else None,
                                    "last_status": provider.get("last_status") if provider else None},
            "coverage": coverage, "strategies": strategies,
            "market_status": markets,
            "economic_calendar": {"status": "SOURCE_NOT_CONNECTED", "verified_events": 0},
            "isolated_tester": {"terminal_probe": "LAUNCHED_AND_EXITED" if probe and probe.get("process_exited") else "NOT_VERIFIED",
                                "strategy_tester": probe_analysis.get("tester_outcome") if probe_analysis else "NOT_TESTED",
                                "test_runs": 0},
            "portfolio_backtest": "NOT_STARTED", "gold_demo_activation": "NOT_AUTHORIZED"}
