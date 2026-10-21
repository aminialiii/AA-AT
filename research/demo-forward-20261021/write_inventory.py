"""Render the reviewed strategy registry without touching trading state."""

from pathlib import Path

from forward_core import ROOT, load_inventory


def main() -> None:
    rows = load_inventory()
    text = [
        "# S01–S18 DEMO forward strategy inventory",
        "",
        "Source identities were checked against current files. Implementation status describes code availability, not verified broker operability. All 18 workers are blocked at this preapproval stage; no forward results exist. Entry, exit, sizing, symbol/timeframe, and baseline details remain in the linked source catalog and dossiers. The proposed Magic Numbers are unverified for collision with broker activity.",
        "",
        "|ID|Strategy|Implementation|Source and rule dossier|Proposed Magic|Operational blocker|",
        "|---|---|---|---|---:|---|",
    ]
    for row in rows:
        source = f"../../{row['source_file']}" if not row['source_file'].startswith("research/") else f"../{row['source_file'].split('research/',1)[1]}"
        dossier = f"../../{row['dossier']}"
        text.append(
            f"|{row['id']}|{row['name']}|{row['implementation_status']}|"
            f"[code]({source}#L{row['source_line']}) · [rules]({dossier})|"
            f"{row['magic_proposal']}|{row['blocker']}|"
        )
    text += [
        "",
        "The exact source file hash for every row is stored in [strategy_inventory.json](strategy_inventory.json). The prior [catalog](../project-review/STRATEGY_CATALOG.md) separates original rules from presets, filters and educational proposals. S05 is a numerical proxy distinct from S16's source-exact proposal; S07 is a one-sided interpretation distinct from S18; S04 is an M1 proxy distinct from S06's 5-second native signal.",
        "",
        "No strategy is currently `PROMISING` or `UNDERPERFORMING` from this campaign: there are zero verified closed DEMO trades. Operational state is `BLOCKED` for all 18, with distinct reasons above. Historical performance is kept in separate research artifacts and must not be used as forward evidence.",
    ]
    (ROOT / "STRATEGY_INVENTORY.md").write_text("\n".join(text) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
