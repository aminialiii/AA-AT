"""Build an account-free Graphify version for the development repository."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import networkx as nx
from graphify.extract import extract
from graphify.exporters.html import to_html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "graphify-out"
STATUS = ROOT / "docs/operational_status.json"


def evidence(path, location):
    lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
    return lines[int(location[1:]) - 1].strip()


def main():
    inputs = sorted((ROOT / "research/demo-live-20261021").glob("*.py"))
    inputs += sorted((ROOT / "research/project-review").glob("*.py"))
    inputs += [ROOT / "research/overnight-20261010/engine.py",
               ROOT / "research/demo-forward-20261021/forward_core.py"]
    OUT.mkdir(parents=True, exist_ok=True)
    extracted = extract(inputs, cache_root=OUT, root=ROOT)
    nodes = {n["id"]: n for n in extracted["nodes"]}
    edges = []
    for edge in extracted["edges"]:
        if edge["target"] not in nodes:
            nodes[edge["target"]] = {"id": edge["target"], "label": edge["target"],
                                     "file_type": "external_reference", "source_file": None,
                                     "source_location": None, "_origin": "external_reference"}
        edges.append({**edge, "confidence": "EXTRACTED", "evidence": evidence(edge["source_file"], edge["source_location"]),
                      "description": "Static reference only; it does not establish runtime execution."})
    policy_path = "research/demo-live-20261021/risk_policy.json"
    policy_id = "demo_live_versioned_risk_policy"
    nodes[policy_id] = {"id": policy_id, "label": "Versioned DEMO risk policy",
                        "file_type": "configuration", "source_file": policy_path,
                        "source_location": "L1", "_origin": "project_configuration"}
    loader = next(n["id"] for n in nodes.values()
                  if n.get("source_file") == "research/demo-live-20261021/service.py"
                  and n.get("label") == "load_config()")
    service_path = "research/demo-live-20261021/service.py"
    service_lines = (ROOT / service_path).read_text(encoding="utf-8").splitlines()
    load_line = next(i for i, line in enumerate(service_lines, 1)
                     if 'load_policy(POLICY_PATH, config["risk"])' in line)
    edges.append({"source": loader, "target": policy_id,
                  "relation": "loads_configuration", "confidence": "EXTRACTED",
                  "evidence": service_lines[load_line - 1].strip(),
                  "source_file": service_path, "source_location": f"L{load_line}",
                  "description": "Static configuration dependency; operational activation requires separate broker evidence."})
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status_path = "docs/operational_status.json"
    lines = STATUS.read_text(encoding="utf-8").splitlines()
    nodes["demo_campaign_observation"] = {"id": "demo_campaign_observation", "label": "DEMO campaign observation",
                                           "file_type": "runtime_snapshot", "source_file": status_path,
                                           "source_location": "L1", "_origin": "observed"}
    for sid, worker in status["workers"].items():
        node_id = f"strategy_{sid}"
        nodes[node_id] = {"id": node_id, "label": sid, "file_type": "strategy_worker",
                          "source_file": status_path, "source_location": "L1", "_origin": "observed"}
        marker = f'"{sid}:{worker["status"]}:{worker["closed"]}"'
        line_no = next(i for i, text in enumerate(lines, 1) if marker in text)
        edges.append({"source": "demo_campaign_observation", "target": node_id,
                      "relation": "observed_worker_status", "status": worker["status"],
                      "confidence": "EXTRACTED", "evidence": lines[line_no - 1].strip(),
                      "source_file": status_path, "source_location": f"L{line_no}",
                      "description": "Timestamped status export checked against the local closed-trade ledger; not inferred from registration."})
    identifiers = set(nodes)
    if len(identifiers) != len(nodes) or any(e["source"] not in identifiers or e["target"] not in identifiers for e in edges):
        raise RuntimeError("duplicate_identity_or_missing_endpoint")
    if any(e["confidence"] not in {"EXTRACTED", "INFERRED", "AMBIGUOUS"} for e in edges):
        raise RuntimeError("invalid_confidence")
    if any(evidence(e["source_file"], e["source_location"]) != e["evidence"] for e in edges):
        raise RuntimeError("invalid_edge_source_evidence")
    graph = {"directed": True, "multigraph": True, "nodes": list(nodes.values()), "links": edges,
             "scope": "sanitized development source and status snapshot; complete operational graph retained locally"}
    (OUT / "graph.json").write_text(json.dumps(graph, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    G = nx.MultiDiGraph()
    for node in nodes.values():
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], **{k: v for k, v in edge.items() if k not in {"source", "target"}})
    to_html(G, {99: list(nodes)}, str(OUT / "graph.html"), node_limit=max(2000, len(nodes) + 1))
    confidence = Counter(e["confidence"] for e in edges)
    validation = {"status": "PASS", "nodes": len(nodes), "links": len(edges), "duplicate_identities": 0,
                  "missing_endpoints": 0, "invalid_source_evidence": 0, "confidence": dict(confidence),
                  "observed_closed_trades": status["completed_trades"], "observed_utc": status["source_observed_utc"]}
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    report = ["# Graphify development graph", "", "This is a new, account-free development graph version. The full prior and live operational graph versions remain local in the original workspace. The graph covers selected Python implementation files and a broker-ledger-checked status snapshot; it does not claim complete repository coverage.", "", 
              f"Nodes: {len(nodes)}. Directed relationships: {len(edges)}. EXTRACTED {confidence['EXTRACTED']}, INFERRED {confidence['INFERRED']}, AMBIGUOUS {confidence['AMBIGUOUS']}.",
              "Validation: no duplicate identities, missing endpoints, or unmatched source-line evidence.",
              "Static imports and calls are references, not proof of runtime calls or data flow. Status edges are timestamped observations only. JSON preserves direction and parallel relationship types; HTML may visually overlap edges.",
              "Broker order/deal records remain outside Git. No trade is inferred from strategy registration or source code."]
    (OUT / "GRAPH_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
