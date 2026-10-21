"""Offline validation only: no account connection, signals, orders, or trades."""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

from forward_core import ROOT, RiskLimits, broker_gate, create_workers, load_inventory, require_execution_ready

PROJECT = ROOT.parent.parent


def main() -> None:
    checks = []
    rows = load_inventory()
    workers = create_workers(rows)
    assert len(rows) == len(workers) == 18 and all(w.state == "BLOCKED" for w in workers.values())
    checks.append("18 unique blocked workers and source hashes")

    preflight = json.loads((ROOT / "preflight_static.json").read_text(encoding="utf-8"))
    assert preflight["account_verification"] == "UNVERIFIED"
    assert preflight["new_order_submissions"] == 0 and preflight["first_order_approval"] is False
    assert preflight["manager_run_status"] == "STOPPED" and preflight["manager_enabled"] is False
    checks.append("saved manager disabled and broker unverified")

    limits = RiskLimits.proposed()
    assert limits.per_strategy_fraction < limits.portfolio_fraction
    assert limits.max_positions_per_strategy == 1 and limits.max_positions_shared_account == 2
    assert broker_gate({}, {"login": preflight["configured_login"], "server": preflight["configured_server"], "currency": "USD"}, limits)
    for approval in (None, {"first_order_approved": True}):
        try:
            require_execution_ready(preflight, approval)
        except RuntimeError:
            pass
        else:
            raise AssertionError("execution gate opened before broker integration")
    checks.append("unverified broker and first-order gate fail closed")

    production = json.loads((PROJECT / "Trading_Manager_Config.json").read_text(encoding="utf-8"))
    assert production["enabled"] is False and production["automation_execution_allowed"] is False
    original = json.loads((PROJECT / "research_outputs/original_baseline_manifest.json").read_text(encoding="utf-8"))["files"]
    for item in original:
        p = PROJECT / item["path"]
        assert p.is_file() and p.stat().st_size == item["bytes"]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == item["sha256"]
    checks.append(f"{len(original)} original source/config files unchanged")

    prior = PROJECT / "research_outputs/graphify-out/graph.json"
    sealed = json.loads((PROJECT / "research_outputs/reproducibility_manifest.json").read_text(encoding="utf-8"))["artifacts"]
    expected = next(item["sha256"] for item in sealed if item["path"] == "research_outputs/graphify-out/graph.json")
    assert hashlib.sha256(prior.read_bytes()).hexdigest() == expected
    graph = json.loads((ROOT / "graphify-out/graph.json").read_text(encoding="utf-8"))
    node_ids = [n["id"] for n in graph["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    assert all(e["source"] in node_ids and e["target"] in node_ids for e in graph["links"])
    assert all(e.get("confidence") in {"EXTRACTED", "INFERRED", "AMBIGUOUS"} for e in graph["links"])
    assert len([n for n in graph["nodes"] if n.get("file_type") == "planned_worker"]) == 18
    assert len(graph["nodes"]) > 1060 and len(graph["links"]) > 2322
    for edge in graph["links"][2322:]:
        path = PROJECT / edge["source_file"]
        assert path.is_file() and edge.get("evidence")
        line = int(edge["source_location"].removeprefix("L"))
        assert 1 <= line <= len(path.read_text(encoding="utf-8").splitlines())
    markup = (ROOT / "graphify-out/graph.html").read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    visual_nodes = decoder.raw_decode(markup[markup.index("const RAW_NODES = ") + len("const RAW_NODES = "):])[0]
    visual_edges = decoder.raw_decode(markup[markup.index("const RAW_EDGES = ") + len("const RAW_EDGES = "):])[0]
    assert len(visual_nodes) == len(graph["nodes"]) and len(visual_edges) == len(graph["links"])
    checks.append(f"Graphify version {len(graph['nodes'])} nodes/{len(graph['links'])} links; prior graph seal unchanged")

    dashboard = (ROOT / "demo_dashboard.html").read_text(encoding="utf-8")
    assert dashboard.count("<tr><td>S") == 18
    assert "0/360 target" in dashboard and "UNVERIFIED" in dashboard and "ORDERS DISABLED" in dashboard
    checks.append("dashboard shows all 18 blocked, zero verified trades, unknown broker state")

    for path in ROOT.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        compile(source, str(path), "exec")
        tree = ast.parse(source)
        assert not any(isinstance(n, ast.Import) and any(a.name == "MetaTrader5" for a in n.names)
                       or isinstance(n, ast.ImportFrom) and n.module == "MetaTrader5"
                       or isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "order_send"
                       for n in ast.walk(tree))
    checks.append("all preparation Python compiles and contains no broker order call")

    result = {"status": "PASS", "checks": checks, "broker_contacted": False,
              "trades_submitted": 0, "historical_replay": False, "synthetic_trades": False}
    (ROOT / "static_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
