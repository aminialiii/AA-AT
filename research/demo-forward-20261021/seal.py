"""Seal preparation artifacts after static checks; no broker access."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    result = json.loads((ROOT / "static_validation.json").read_text(encoding="utf-8"))
    graph = json.loads((ROOT / "graphify-out/validation.json").read_text(encoding="utf-8"))
    if result["status"] != "PASS" or graph["status"] != "PASS":
        raise RuntimeError("static checks must pass before seal")
    now = datetime.now(timezone.utc).isoformat()
    entries = [
        {"utc": now, "stage": "INVENTORY", "strategies": 18, "operational": 0,
         "evidence": "strategy_inventory.json", "production_modified": False},
        {"utc": now, "stage": "BROKER_PREFLIGHT", "status": "UNVERIFIED",
         "reason": "terminal MCP not reachable; saved config is not account proof",
         "orders_submitted": 0, "evidence": "preflight_static.json"},
        {"utc": now, "stage": "RISK_PROPOSAL", "approved": False,
         "evidence": "risk_proposal.json"},
        {"utc": now, "stage": "GRAPH_VERSION", "nodes": graph["nodes"],
         "links": graph["links"], "observed_order_executions_added": 0,
         "evidence": "graphify-out/validation.json"},
        {"utc": now, "stage": "STATIC_VALIDATION", "status": "PASS",
         "checks": result["checks"], "evidence": "static_validation.json"},
        {"utc": now, "stage": "FIRST_ORDER_GATE", "status": "WAITING_FOR_VERIFIED_DEMO_ACCOUNT_AND_EXPLICIT_APPROVAL",
         "campaign_service_started": False, "demo_trades": 0},
    ]
    with (ROOT / "audit.jsonl").open("x", encoding="utf-8") as stream:
        for entry in entries:
            stream.write(json.dumps(entry, sort_keys=True) + "\n")
    artifacts = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.name == "preparation_manifest.json":
            continue
        relative = path.relative_to(ROOT).as_posix()
        if "__pycache__" in path.parts or "cache" in path.parts or path.suffix == ".pyc":
            continue
        artifacts.append({"path": relative, "sha256": sha(path), "bytes": path.stat().st_size})
    manifest = {"kind": "STATIC_DEMO_CAMPAIGN_PREPARATION", "sealed_utc": now,
                "artifact_count": len(artifacts), "artifacts": artifacts,
                "broker_contacted": False, "orders_submitted": 0,
                "strategy_backtests_or_synthetic_trades": 0,
                "account_verification": "UNVERIFIED",
                "first_order_approval": False}
    with (ROOT / "preparation_manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    for item in artifacts:
        if sha(ROOT / item["path"]) != item["sha256"]:
            raise RuntimeError("artifact changed during seal")
    print(json.dumps({"sealed_artifacts": len(artifacts), "orders_submitted": 0}))


if __name__ == "__main__":
    main()
