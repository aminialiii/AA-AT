# Offline educational research — 2026-10-21

**Decision: no confirmed improvement; production remains unchanged.** Package extracted to workspace root;32/32canonical SHA256+size checks passed. Baselines reproduced before candidate evaluation. All18strategies assessed at their evidence tier; S01-S05 backtested, others explicitly NOT_RUN/SPEC_GAP.

- [Measured comparison](comparison.md)
- [Provisional shortlist and user decision gate](selection_shortlist.md)
- [Baseline results](baseline_results.csv), [candidate results](candidate_results.csv), [all results](all_results.csv)
- [Candidate registry](candidate_registry.csv), [per-strategy dossiers](strategy_dossiers/S01.md)
- [Source/rule provenance](source_rule_map.csv), [source integrity](source_integrity.json), [coverage](source_ingestion_coverage.json)
- [Defect audit](defect_audit.md), [actual tests](test_report.md), [specification gaps](specification_gaps.md)
- [Reproducibility manifest](reproducibility_manifest.json), [baseline snapshot](original_baseline_manifest.json)
- [Research dashboard](comparison_dashboard.html), [versioned graph](graphify-out/graph.html), [graph before/after](graph_before_after.md)

Critical interpretation: all measured prices are already-exposed Jul–Sep2026historical data. There is no fresh untouched OOS. Costs, financing and minimum-volume cash curves are scenarios, not observed historical broker execution. Equal-weight R metrics can disagree with dollar PnL; consult dollar_accounting.csv. Direct supplied captions are distinguished from companion claims/reconstructions; no independent video authenticity check was performed.

For a safe executable repeat check, run `python research/educational-32-20261021/reproduce.py --output research_outputs/reproduction_check_02.json` with the recorded Python interpreter. The new output path must not exist. Default repeats sixS01baseline/candidate partition runs; `--all` repeats all840primary runs. It verifies canonical decompressed trade records and numerical metrics without replacing current results or production files. The default six-run check already passed in reproduction_verification.json.

Reproduction: use the recorded existing Python3.14.7 with local .skill-tools/NumPy2.5.3; no dependency installation/network required. Baseline/candidate registration and outputs are exclusive-create: use a NEW output workspace/study ID before repeating full commands, preserve all current artifacts. Source `research/educational-32-20261021/experiment.py` documents whitelisted functions. Stage order: register_baseline → baseline → register_candidates → candidates, then assess.py select → robustness → walkforward → aggregate_risk, semantic graph ingestion/build, finalize.py. Synthetic checks: test_research.py and node test_event_adapter.mjs. Source transcripts contain code; it was never executed. Do not run original stage dispatchers/native scripts to reproduce this isolated study.

**USER_DECISION_GATE:** choose a strategy ID + candidate ID for further offline work. Deployment, production integration or demo/paper/live activation require explicit separate authorization.
