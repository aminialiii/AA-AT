"""Static, read-only inventory and preflight preparation. Never contacts a broker."""

from __future__ import annotations

import hashlib
import json
import socket
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent.parent

# Names and paths come from the reviewed source catalog, not educational proposals.
DEFINITIONS = [
    ("Range rejection", "research/overnight-20261010/engine.py", 77, "OFFLINE_ONLY", "Saved M1/M5 signal implementation; live market-data, order, and reconciliation adapter absent; M5 plan identity repair required."),
    ("Trend pullback", "research/overnight-20261010/engine.py", 74, "OFFLINE_ONLY", "Saved M1/M5 signal implementation; live adapter absent; M5 plan identity repair required."),
    ("Break/retest", "research/overnight-20261010/engine.py", 80, "OFFLINE_ONLY", "Stateful M1/M5 setup requires continuous real-time state, live adapter, and M5 identity repair."),
    ("Momentum proxy", "research/overnight-20261010/engine.py", 71, "OFFLINE_ONLY", "M1 proxy is not native 5-second strategy; live signal and broker adapter absent."),
    ("SP2L numerical proxy", "research/overnight-20261010/engine.py", 92, "OFFLINE_ONLY", "M1 numerical proxy is not source-exact SP2L; live adapter absent."),
    ("Aligned tick momentum RR2", ".skill-tools/rr2-native.py", 58, "SUSPENDED_NATIVE", "Current native path is disabled/stopped; managed GTC expiry depends on manager cancellation; new parallel isolation/risk policy unverified."),
    ("MicroMAP buy interpretation", ".skill-tools/universe-native.py", 90, "SUPERSEDED_NATIVE", "Prior terminal-dependent version is incompatible with current manager; independent live adapter and frozen version needed."),
    ("Gold short-bar break/retest", ".skill-tools/gold-evaluate.mjs", 3, "SUPERSEDED_NATIVE", "Archived short-bar configuration and independent execution path are unavailable."),
    ("Event-range retest", "demo_event_setup_20261008.mjs", 92, "EVALUATOR_ONLY", "Stored anchor expired; same-version anchor rollover can reuse prior range; no independently verified broker execution path."),
    ("EMA continuation pullback", "Intraday_Continuation_Simulation_Functions_20261007.js", 2, "PARTIAL", "Implicit prepared-data and indicator pipeline missing; simulation function is not a live worker."),
    ("EMA continuation breakout", "Intraday_Continuation_Simulation_Functions_20261007.js", 2, "PARTIAL", "Same missing prepared-data and indicator pipeline as S10."),
    ("Frozen RSI reversal", "Intraday_Continuation_Simulation_Functions_20261007.js", 84, "PARTIAL", "RSI period/smoothing and prepared input generation unspecified."),
    ("Five-second exploration momentum", ".skill-tools/hundred-native.py", 15, "SUPERSEDED_NATIVE", "Old version/protocol has changing exit policy and no isolated current live worker."),
    ("Five-second exploration reversal", ".skill-tools/hundred-native.py", 15, "SUPERSEDED_NATIVE", "Old reversal arm needs distinct frozen protocol/exit rule and isolated worker."),
    ("Rolling M5/M1 retest", ".skill-tools/cycle-refreshed.js", 64, "EXTERNAL_SKILL", "Installed external evaluator/risk gate requires frozen dependency and gap-validation fix; current config incompatible."),
    ("Exact SP2L", "Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json", 35, "DOCUMENTATION_ONLY", "Spike/P-Gap validity, entry timing and full short rule not mechanically specified."),
    ("Exact Pro BTB", "Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json", 42, "DOCUMENTATION_ONLY", "Important-level definition and six-mode causal arbitration not implemented."),
    ("Exact MicroMAP", "Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json", 49, "DOCUMENTATION_ONLY", "Spike/channel, attempt expiry, exceptions and final TP/short mechanics unresolved."),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.25):
            return True
    except OSError:
        return False


def write_new(path: Path, obj: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(obj, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main() -> None:
    inventory = []
    for index, (name, rel, line, status, blocker) in enumerate(DEFINITIONS, start=1):
        source = PROJECT / rel
        if not source.is_file():
            raise FileNotFoundError(source)
        inventory.append({
            "id": f"S{index:02d}", "name": name, "source_file": rel,
            "source_line": line, "source_sha256": sha(source),
            "implementation_status": status, "demo_operational": False,
            "worker_id": f"demo-forward-S{index:02d}",
            "magic_proposal": 426100 + index,
            "blocker": blocker,
            "dossier": f"research_outputs/strategy_dossiers/S{index:02d}.md",
        })
    write_new(ROOT / "strategy_inventory.json", inventory)
    write_new(ROOT / "risk_proposal.json", {
        "status": "PROPOSED_NOT_APPROVED", "capital_basis": "Current broker equity and independently allocated strategy capital, both verified at entry",
        "limits": {
            "per_strategy_fraction": 0.0025,
            "portfolio_fraction": 0.01,
            "daily_loss_fraction": 0.01,
            "peak_drawdown_fraction": 0.02,
            "free_margin_fraction": 0.25,
            "max_positions_per_strategy": 1,
            "max_positions_shared_account": 2,
            "max_quote_age_seconds": 5,
        },
        "rules": [
            "No trade if broker minimum volume exceeds either risk budget; never round volume upward.",
            "Reserve current open price risk plus worst plausible execution cost; include pending orders.",
            "Verify account trade mode DEMO, login, server, currency, routing permission and fresh quote before each intent.",
            "One global symbol lock prevents conflicting same-symbol exposure on a shared account; unknown netting/hedging mode blocks shared execution.",
            "Unknown margin, cost, fills, positions, or order status blocks new entries and triggers reconciliation.",
            "Daily loss includes realized and floating PnL; peak drawdown uses preserved high-water mark.",
            "Never submit a second order after an ambiguous response; reconcile order/deal/position IDs first.",
            "Circuit breaker suspends the affected worker; common account/feed/risk failure suspends all workers.",
            "Emergency stop cancels owned pending orders and stops new entries; open positions require broker-verified protective handling under a separately frozen rule.",
        ],
    })
    config = json.loads((PROJECT / "Trading_Manager_Config.json").read_text(encoding="utf-8"))
    state = json.loads((PROJECT / "Trading_Manager_State.json").read_text(encoding="utf-8"))
    write_new(ROOT / "preflight_static.json", {
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "kind": "STATIC_LOCAL_CHECK_NOT_BROKER_VERIFICATION",
        "configured_login": config.get("account_login"),
        "configured_server": config.get("account_server"),
        "manager_enabled": config.get("enabled"),
        "automation_execution_allowed": config.get("automation_execution_allowed"),
        "manager_run_status": state.get("run_status"),
        "manager_stage": state.get("stage"),
        "prior_direct_suspension_recorded": bool(config.get("direct_user_demo_suspension", {}).get("active")),
        "terminal_mcp_loopback_reachable": local_port_open(22346),
        "metaeditor_mcp_loopback_reachable": local_port_open(22345),
        "account_verification": "UNVERIFIED",
        "order_routing": "UNVERIFIED",
        "live_demo_trades_this_campaign": 0,
        "first_order_approval": False,
        "new_order_submissions": 0,
        "limitations": "Saved config names a prior demo login/server but does not prove the current broker account or permissions. No terminal process was launched; no broker tool was available in this session.",
    })


if __name__ == "__main__":
    main()
