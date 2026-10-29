# Versioned research graph — before/after

Original graphify-out/graph.json remains unchanged (SHA256 `1669b4f79718fca94b6036ab6574a3fef78bf6a3dbcb138d71b4bfbf6e7b11d7`). New artifacts live only under research_outputs/graphify-out/.

|Measure|Original|Research v20261021|
|---|---:|---:|
|Nodes|846|1060|
|Directed relationships|1924|2322|
|Missing endpoints|0|0|
|Duplicate identities|0|0|
|Invalid source references|0|0|

All32canonical documents were ingested;73source-rule records distinguish supplied direct captions, companion claims, reconstructions, hypotheses and unverified claims. New first-party research/test code is structurally indexed. The research graph links educational motivations to candidate hypotheses and implementation without asserting teacher-exact fidelity or profitability. Evidence lines and EXTRACTED/INFERRED/AMBIGUOUS distinctions are retained.

A document basename collision between knowledge_graph.json and knowledge_graph.mmd was corrected using source-specific IDs; both files survive. See identity_repairs.json. Direction and all parallel relations survive JSON/HTML export. Clustering centrality uses 2243directed pairs; 79additional source/relation records remain in multigraph JSON. Final HTML contains the same1060node identities/2322links; embedded data validation passed. Browser rendering was not tested; the Graphify HTML loads vis-network from its pinned CDN. The comparison dashboard is self-contained and has no remote dependencies.

- [JSON](graphify-out/graph.json)
- [Interactive graph](graphify-out/graph.html)
- [Report](graphify-out/GRAPH_REPORT.md)
- [Validation](graphify-out/validation.json)

Rebuild: use the existing Graphify interpreter and research/educational-32-20261021/build_graph.py, then run graphify export html with cwd=research_outputs. This leaves original graphify-out intact. Source semantic token usage was not exposed by tools and remains unknown.
