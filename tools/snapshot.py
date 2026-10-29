"""Copy an explicit, reviewed source surface from the original workspace.

This never imports live configuration, broker evidence, or order records. A
secret finding aborts before replacing the destination file.
"""
from __future__ import annotations

import shutil
import json
import sys
from pathlib import Path

from secret_scan import scan

DEST = Path(__file__).resolve().parents[1]
SOURCE = DEST.parent
EXTENSIONS = {".py", ".js", ".mjs", ".mq5", ".md"}
ROOT_EXCLUDE = {"Trading_Workflow_Overrides.md"}
DEMO_LIVE = {"broker.py", "live_signals.py", "portfolio_policy.py", "state.py", "service.py", "report.py", "validate_live_adapter.py"}
DEMO_FORWARD = {"forward_core.py", "dashboard.py", "prepare.py", "seal.py", "write_inventory.py", "check_static.py", "README.md", "OPERATIONS_PLAN.md", "EVALUATION_PROTOCOL.md", "STRATEGY_INVENTORY.md"}
OUTPUT_FILES = {"README.md", "inventory.json", "registration_baseline.json", "original_baseline_manifest.json", "specification_gaps.md", "selection_shortlist.md", "test_report.md", "source_integrity.json", "source_ingestion_coverage.json", "reproducibility_manifest.json", "selection_frozen.json", "shortlist_assessment.json", "comparison.md", "graph_before_after.md"}
EDU_FILES = {"SOURCE_SHA256_MANIFEST.json", "START_HERE.md", "CODEX_MASTER_PROMPT.md", "RESEARCH_PROTOCOL.md"}


def selected():
    for path in SOURCE.iterdir():
        if path.is_file() and path.suffix.lower() in EXTENSIONS and path.name not in ROOT_EXCLUDE:
            yield path
    for group in ("research/project-review", "research/educational-32-20261021", "research/overnight-20261010", "research/backtest-only-20261010", "research/poursamadi-v0.9", "research/poursamadi-backtest", "research/lse-scalping-20261010"):
        folder = SOURCE / group
        if folder.exists():
            for path in folder.iterdir():
                if path.is_file() and path.suffix.lower() in EXTENSIONS:
                    yield path
    for name in DEMO_LIVE:
        path = SOURCE / "research/demo-live-20261021" / name
        if path.exists():
            yield path
    for name in DEMO_FORWARD:
        path = SOURCE / "research/demo-forward-20261021" / name
        if path.exists():
            yield path
    for name in OUTPUT_FILES:
        path = SOURCE / "research_outputs" / name
        if path.exists():
            yield path
    yield SOURCE / "research/educational-32-20261021/extraction_audit.json"
    for path in (SOURCE / "research_outputs/strategy_dossiers").glob("*.md"):
        yield path
    for path in (SOURCE / "strategy_research_input").rglob("*.md"):
        yield path
    manifest = json.loads((SOURCE / "strategy_research_input/SOURCE_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("invalid_educational_manifest_path")
        yield SOURCE / "strategy_research_input" / relative
    for path in (SOURCE / ".skill-tools").iterdir():
        if path.is_file() and path.suffix.lower() in EXTENSIONS:
            yield path
    for name in EDU_FILES:
        path = SOURCE / "strategy_research_input" / name
        if path.exists():
            yield path
    for name in ("mcp.json", "plugin.json", "skills/metatrader-mcp/SKILL.md"):
        path = SOURCE / "meta-trader-mcp" / name
        if path.exists():
            yield path


def main():
    paths = sorted(set(selected()))
    rejected = scan(paths)
    blocked = {path for path, _ in rejected}
    copied = 0
    for path in paths:
        if path in blocked:
            continue
        target = DEST / path.relative_to(SOURCE)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        copied += 1
    print(f"copied={copied} rejected={len(blocked)}")
    for path, reason in rejected:
        print(f"REJECT {path.relative_to(SOURCE)}: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
