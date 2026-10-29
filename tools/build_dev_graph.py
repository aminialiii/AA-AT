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
    previous = None
    if (OUT / "graph.json").is_file():
        previous = json.loads((OUT / "graph.json").read_text(encoding="utf-8"))
    inputs = sorted((ROOT / "research/demo-live-20261021").glob("*.py"))
    inputs += sorted((ROOT / "research/project-review").glob("*.py"))
    inputs += sorted((ROOT / "command_center").glob("*.py"))
    inputs += [ROOT / "tools/build_dashboard.py"]
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
    repository_policy = json.loads((ROOT / policy_path).read_text(encoding="utf-8"))
    nodes[policy_id] = {"id": policy_id, "label": f"Repository DEMO risk policy v{repository_policy['policy_version']}",
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
    ui_id = "aa_at_command_center_ui"
    nodes[ui_id] = {"id": ui_id, "label": "Trading Command Center UI",
                    "file_type": "html_application", "source_file": "docs/dashboard.html",
                    "source_location": "L1", "_origin": "project_source"}
    server_node = next(n["id"] for n in nodes.values()
                       if n.get("source_file") == "command_center/server.py"
                       and n.get("label") == "server.py")
    server_path = "command_center/server.py"
    server_lines = (ROOT / server_path).read_text(encoding="utf-8").splitlines()
    serve_line = next(i for i, line in enumerate(server_lines, 1)
                      if 'self.app.repo / "docs/dashboard.html"' in line)
    edges.append({"source": server_node, "target": ui_id,
                  "relation": "serves_ui", "confidence": "EXTRACTED",
                  "evidence": server_lines[serve_line - 1].strip(),
                  "source_file": server_path, "source_location": f"L{serve_line}",
                  "description": "Local HTTP handler serves the dashboard shell; this static edge does not prove the service is running."})
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    status_path = "docs/operational_status.json"
    lines = STATUS.read_text(encoding="utf-8").splitlines()
    nodes["demo_campaign_observation"] = {"id": "demo_campaign_observation", "label": "DEMO campaign observation",
                                           "file_type": "runtime_snapshot", "source_file": status_path,
                                           "source_location": "L1", "_origin": "observed"}
    # The checked-in policy can lag behind the separately deployed DEMO runtime.
    # Keep the static configuration dependency distinct from observed effective policy.
    observed_policy_id = "observed_demo_risk_policy"
    risk_line = next(i for i, line in enumerate(lines, 1)
                     if '"max_open_risk_fraction"' in line)
    nodes[observed_policy_id] = {
        "id": observed_policy_id,
        "label": f"Observed DEMO portfolio cap {100 * status['max_open_risk_fraction']:g}%",
        "file_type": "runtime_snapshot", "source_file": status_path,
        "source_location": f"L{risk_line}", "_origin": "observed",
        "description": "Timestamped, account-free status export; not a source-code configuration claim.",
    }
    edges.append({
        "source": "demo_campaign_observation", "target": observed_policy_id,
        "relation": "observed_effective_risk_policy", "confidence": "EXTRACTED",
        "evidence": lines[risk_line - 1].strip(), "source_file": status_path,
        "source_location": f"L{risk_line}",
        "description": "Observed runtime limit at the status timestamp; static repository policy may differ.",
    })
    for field, label in (
        ("daily_equity_halt_enabled", "Daily loss measured; halt disabled"),
        ("peak_equity_halt_enabled", "Peak drawdown measured; halt disabled"),
    ):
        if status.get(field) is not False:
            continue
        line_no = next(i for i, line in enumerate(lines, 1) if f'"{field}"' in line)
        node_id = f"observed_{field}"
        nodes[node_id] = {
            "id": node_id, "label": label, "file_type": "runtime_snapshot",
            "source_file": status_path, "source_location": f"L{line_no}",
            "_origin": "observed",
            "description": "Timestamped broker-reconciled status; other order and safety gates remain separate.",
        }
        edges.append({
            "source": "demo_campaign_observation", "target": node_id,
            "relation": "observed_drawdown_halt_setting", "confidence": "EXTRACTED",
            "evidence": lines[line_no - 1].strip(), "source_file": status_path,
            "source_location": f"L{line_no}",
            "description": "This threshold is measured without halting orders at the observation timestamp.",
        })
    def source_node(path, label):
        return next(n["id"] for n in nodes.values()
                    if n.get("source_file") == path and n.get("label") == label)

    features_path = "research/demo-live-20261021/live_signals.py"
    signals_path = "research/overnight-20261010/engine.py"
    features_lines = (ROOT / features_path).read_text(encoding="utf-8").splitlines()
    original_lines = (ROOT / signals_path).read_text(encoding="utf-8").splitlines()
    gap_line = next(i for i, line in enumerate(features_lines, 1)
                    if "valid[j+1:min(n, j+101)] = False" in line)
    invalid_line = next(i for i, line in enumerate(original_lines, 1)
                        if "out[~d['valid']]=0" in line)
    gap_id = "completed_m1_gap_warmup_100_bars"
    nodes[gap_id] = {
        "id": gap_id, "label": "100 completed M1 bars after a gap",
        "file_type": "signal_validity_rule", "source_file": features_path,
        "source_location": f"L{gap_line}", "_origin": "project_source",
        "description": "A data-gap validity rule; it does not establish that a strategy signal occurred.",
    }
    edges.extend([
        {"source": source_node(features_path, "completed_features()"), "target": gap_id,
         "relation": "applies_data_validity_rule", "confidence": "EXTRACTED",
         "evidence": features_lines[gap_line - 1].strip(), "source_file": features_path,
         "source_location": f"L{gap_line}",
         "description": "The first 100 M1 bars after a non-contiguous timestamp are marked invalid."},
        {"source": gap_id, "target": source_node(signals_path, "signals()"),
         "relation": "suppresses_invalid_bar_signals", "confidence": "INFERRED",
         "evidence": original_lines[invalid_line - 1].strip(), "source_file": signals_path,
         "source_location": f"L{invalid_line}",
         "description": "Cross-file data flow: the frozen signal function zeros the adapter validity mask; no runtime signal is inferred."},
    ])
    diagnosis_path = "docs/NO_POSITION_DIAGNOSIS_2026-10-26.md"
    diagnosis_lines = (ROOT / diagnosis_path).read_text(encoding="utf-8").splitlines()
    diagnosis_line = next(i for i, line in enumerate(diagnosis_lines, 1)
                          if "79 completed post-gap M1 bars" in line)
    diagnosis_id = "weekend_no_position_diagnosis_20261026"
    nodes[diagnosis_id] = {
        "id": diagnosis_id, "label": "Observed weekend signal warm-up",
        "file_type": "timestamped_diagnosis", "source_file": diagnosis_path,
        "source_location": f"L{diagnosis_line}", "_origin": "observed",
        "description": "Read-only, time-bounded diagnosis; no future trade is implied.",
    }
    edges.append({
        "source": diagnosis_id, "target": gap_id,
        "relation": "documents_observed_warmup", "confidence": "EXTRACTED",
        "evidence": diagnosis_lines[diagnosis_line - 1].strip(),
        "source_file": diagnosis_path, "source_location": f"L{diagnosis_line}",
        "description": "The diagnosis documents a read-only rate observation and the code rule; it is not a broker order record.",
    })
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
    for node in nodes.values():
        path, location = node.get("source_file"), node.get("source_location")
        if path and (not (ROOT / path).is_file() or
                     (location and location.startswith("L") and
                      int(location[1:]) > len((ROOT / path).read_text(encoding="utf-8").splitlines()))):
            raise RuntimeError("invalid_node_source_reference")
    graph = {"directed": True, "multigraph": True, "nodes": list(nodes.values()), "links": edges,
             "scope": "sanitized development source, command center, and status snapshot; complete operational graph retained locally"}
    (OUT / "graph.json").write_text(json.dumps(graph, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    G = nx.MultiDiGraph()
    for node in nodes.values():
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})
    for edge in edges:
        G.add_edge(edge["source"], edge["target"], **{k: v for k, v in edge.items() if k not in {"source", "target"}})
    to_html(G, {99: list(nodes)}, str(OUT / "graph.html"), node_limit=max(2000, len(nodes) + 1))
    confidence = Counter(e["confidence"] for e in edges)
    validation = {"status": "PASS", "nodes": len(nodes), "links": len(edges),
                  "before_nodes": None if previous is None else len(previous["nodes"]),
                  "before_links": None if previous is None else len(previous["links"]),
                  "duplicate_identities": 0,
                  "missing_endpoints": 0, "invalid_source_evidence": 0, "confidence": dict(confidence),
                  "observed_closed_trades": status["completed_trades"], "observed_utc": status["source_observed_utc"]}
    (OUT / "validation.json").write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    report = ["# Graphify development graph", "", "This is an account-free development graph version. The full prior and live operational graph versions remain local in the original workspace. The graph covers selected trading, control-plane, and reporting Python files, the dashboard shell, and a broker-ledger-checked status snapshot; it does not claim complete repository coverage.", "", 
              f"Nodes: {len(nodes)}. Directed relationships: {len(edges)}. EXTRACTED {confidence['EXTRACTED']}, INFERRED {confidence['INFERRED']}, AMBIGUOUS {confidence['AMBIGUOUS']}.",
              "Validation: no duplicate identities, missing endpoints, or unmatched source-line evidence.",
              "Static imports and calls are references, not proof of runtime calls or data flow. Status edges are timestamped observations only. JSON preserves direction and parallel relationship types; HTML may visually overlap edges.",
              "Broker order/deal records remain outside Git. No trade is inferred from strategy registration or source code.",
              "The local command center serves a live authenticated telemetry projection. An API or control edge in this graph is not evidence that the runtime bridge is deployed or healthy; consult the timestamped local status and control audit.",
              f"The repository policy file is v{repository_policy['policy_version']} with a {100 * repository_policy['max_open_fraction']:g}% aggregate cap; the separate timestamped runtime snapshot reports {100 * status['max_open_risk_fraction']:g}%. This graph preserves both facts and does not treat the checked-in copy as effective runtime configuration.",
              "The completed-candle adapter invalidates 100 M1 bars after a data gap. The frozen signal function zeros these invalid bars. This includes the weekend reopening gap and is a signal-validity rule, not a broker or portfolio-risk rejection."]
    (OUT / "GRAPH_REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(validation))


if __name__ == "__main__":
    main()
