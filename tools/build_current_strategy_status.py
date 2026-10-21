"""Account-free current S01-S18 implementation and campaign inventory."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATUS = json.loads((ROOT / "docs/operational_status.json").read_text(encoding="utf-8"))
CONFIG = json.loads((ROOT / "research/demo-live-20261021/campaign_config.example.json").read_text(encoding="utf-8"))


def safe(value):
    return str(value).replace("|", "/").replace("\n", " ")


def main():
    lines = ["# Current strategy status", "",
             f"Account-free broker-ledger snapshot observed {STATUS['source_observed_utc']}. This replaces the operational status in the earlier preapproval inventory; that document remains as historical provenance. Original rules and limitations are in the linked dossiers.", "",
             f"{STATUS['active_strategies']} active and {STATUS['blocked_strategies']} blocked. {STATUS['completed_trades']} verified closed DEMO trades of {STATUS['eligible_target']} currently eligible target; nominal all-strategy target {STATUS['overall_target']}.", "",
             "|ID|Strategy|Current worker|Closed / 100|Implementation or blocker|Original-rule dossier|",
             "|---|---|---|---:|---|---|"]
    for row in CONFIG["workers"]:
        sid = row["id"]
        observed = STATUS["workers"][sid]
        explanation = ("Frozen original M1 proxy/implementation; live adapter operating with DEMO guard"
                       if observed["status"] == "ACTIVE" else row["blocker"] or "Blocker under review")
        lines.append(f"|{sid}|{safe(row['name'])}|{safe(observed['status'])}|{observed['closed']}/100|{safe(explanation)}|[rules](../research_outputs/strategy_dossiers/{sid}.md)|")
    lines += ["", "An `ACTIVE` status is an observed worker state, not a claim that every market/session currently has a signal. S04 and S05 are numerical/proxy implementations and must not be conflated with exact educational rules. Broker orders and deals remain in local evidence storage."]
    target = ROOT / "docs/CURRENT_STRATEGY_STATUS.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"strategies={len(CONFIG['workers'])} active={STATUS['active_strategies']} blocked={STATUS['blocked_strategies']}")


if __name__ == "__main__":
    main()
