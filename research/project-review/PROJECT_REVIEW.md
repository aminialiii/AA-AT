# Trading project review and Graphify repair

Date: 2026-10-21 (user timezone Asia/Tehran). Scope: static source/configuration/result review and knowledge-graph repair only. No strategy logic or effective trading configuration was changed. No terminal connection, account inspection, order submission/management, service launch, backtest, optimization, paper trading or scheduler action was performed.

## Architecture and scope

Root is E:/GPT/Inves. It is a local workspace collection, not a Git checkout: git status reports “not a git repository”; recursive discovery found no nested .git or AGENTS.md, and no AGENTS.md at E:/ or E:/GPT/. Consequently there is no Git working-tree diff/commit baseline. Existing artifacts and unrelated work were preserved; all changes are new graph/review files. EcoSystem is empty. No package.json/pyproject project manifest or conventional application/test framework was found in first-party scope.

Languages: Python (NumPy and MetaTrader5 native package, JSON/gzip/CSV), JavaScript ES modules and host-evaluated async wrappers (Node file utilities plus host tools/load/store), MQL5 risk probe, PowerShell launch helpers, JSON configuration, Markdown reports and archived HTML/SVG/media. `.skill-tools` mixes first-party runtime helpers with vendored NumPy/MetaTrader5/PyYAML; excluding that directory wholesale would miss the current strategy.

Two distinct paths:

1. **Configured demo path, presently disabled:** Trading_Manager_Config selects rr2-parallel.js and rr2-native.py. Native helper reads ticks/M1/contract/account data, computes five-second momentum and closed-M1 agreement, validates cost/stop/margin gates, sizes minimum broker volume and writes intent. Host JavaScript sends a pending order through terminal MCP only under an explicit execution context; hundred-state and universe-position-native verify/reconcile ownership, bracket protection and actual deals. Managed-expiry GTC orders require the wrapper to cancel them. Journals are immutable evidence shards; Trading_Manager_State is a mutable checkpoint. rr2-review reports saved evidence. Nothing in a static invocation graph proves a cycle ran or currently runs.
2. **Offline research path:** broker history archives/manifests → load_data normalization and M5 aggregation → ATR/EMA/prior ranges → signals family branches → replay stop/cost/size/exit simulation → metrics → per-family selection, combined selection, reports. backtest-only/cycle and dispatch_active select hash-pinned registered stages. “Offline” is not synonymous with safe to run during this review: these entry points launch backtests. Native collection/backtest scripts also initialize the terminal at module scope.

Earlier paths coexist: event-range evaluator/CLI; installed rolling M5/M1 skill; gold S5/S15 evaluator; buy-only MicroMAP; bounded momentum/reversal exploration; older implicit-global continuation/RSI simulation. They are not all enabled together. Strategy IDs and exact entry/exit rules are in [STRATEGY_CATALOG.md](E:/GPT/Inves/research/project-review/STRATEGY_CATALOG.md). [STRATEGY_TEST_PLAN.md](E:/GPT/Inves/research/project-review/STRATEGY_TEST_PLAN.md) is proposed work awaiting selection.

Configuration precedence is path-specific. Current rr2-native reads manager config plus experiment_protocol_path; it does not consume model_path, so the lingering MicroMAP JSON pointer does not implement the active RR2 entry rule. Event evaluator uses its module constants and explicit rulesVersion/eventAnchor; similarly named JSON rule documents do not override it automatically. Offline engines use their R/request, plan, manifest and replay arguments, not manager risk fields. Installed skill prose is older than current config. Host execution context and enabled/run-status gates remain independent from a strategy's registration.

Integrations: `.codex/config.toml` names localhost metaeditor:22345 and terminal:22346 plus metatrader.com marketdata MCP. Authorization is referenced through environment variable names; no credentials were printed. Python points at installed Windows MT5 terminal and local vendored package. `research/lse-scalping-20261010/lse_api.py` is research/API tooling; downloaded evidence scripts were excluded. No connector availability, broker history completeness, current account balance/positions or active automation was checked. None was necessary or authorized for this static task.

## Inspection coverage

|Area|Coverage and limits|
|---|---|
|Repository instructions|No applicable AGENTS found; read installed Graphify skill/workflow, manager skill/operating contract, market-analysis skill, project research README/rules and operational overrides. Skill operating instructions were evidence, not authorization to trade.|
|First-party code|100 files inventoried and SHA256 frozen; structural extraction on99 supported files;50 Python files parsed without execution. Direct detailed reading concentrated on all identified signal implementations, active execution/config wiring, offline engines/selection and dangerous entry points. Other collectors/reporters/registration utilities received structural/invocation review, not line-by-line behavioral audit.|
|Documentation/config|23 selected files semantically extracted; manager config, protocol, model JSON, plans, runbooks and archived result summaries inspected. Additional installed evaluator/risk/CLI read to resolve external dependency. No claim that all journal JSON was read.|
|Graph|No pre-existing graph.json anywhere under root. Fresh AST extraction audited before final build; retained raw extraction, corrections, source evidence and diagnostics.|
|Tests|Synthetic event test exists for20261007; validation/causality code and saved artifacts exist. No project backtest/unit tests executed. Review-owned graph assertions and Python parsing passed. MQL5 not compiled; JavaScript trading wrappers not evaluated.|
|Results/data|Saved summary/config/provenance inspected; plan IDs compared without simulation. NPZ/tick archives and gzip trade journals were not exhaustively decompressed or re-accounted; historical performance remains reported, not independently validated.|
|Excluded|Vendored packages, binaries, caches, bulk tick/state/journal datasets, archived attachments, raw video/image media and downloaded third-party JS/Python evidence. Source dependencies were represented as external nodes. No videos/webpages were fetched; exact teacher-source verification is out of this review's evidence.|
|Working state|No Git baseline exists. Review assertions confirm all100 inventoried original source files retain their recorded hashes. Config/state/journals were only read; no source edits were made.|

Full indexed paths: [source_manifest.json](E:/GPT/Inves/graphify-out/source_manifest.json). Detailed documentation/provenance coverage: [SEMANTIC_REVIEW.md](E:/GPT/Inves/research/project-review/SEMANTIC_REVIEW.md). The graph is a navigational aid, not proof of complete code coverage.

## Prioritized findings and proposed fixes

### F01 — High: research plan regeneration does not reproduce registered M5 identities

[M1 plan builder](E:/GPT/Inves/research/overnight-20261010/engine.py:39) and [M5 plan builder](E:/GPT/Inves/research/overnight-20261010/m5/engine.py:39) both hash family/body/stop/session/target with OR1 prefix and omit timeframe. Actual saved [M5 plan](E:/GPT/Inves/research/overnight-20261010/m5/plan.json:89) contains timeframe=M5 and OR2M5 IDs. [combined.all_groups](E:/GPT/Inves/research/overnight-20261010/combined.py:17) merges dictionaries keyed only by symbol/modelId, so fresh plans generated by both current builders can overwrite M1 groups with M5 groups for shared presets. This can misattribute subsequent diagnostics/report rows. The saved plans were explicitly checked: **zero shared IDs**, so this review does NOT assert corruption of existing results. Combined final() separately selects the proper engine, also limiting the claim.

Proposed fix: include timeframe/source-version in model identity and group keys; reject duplicates on merge; test fresh registration and report lineage. Preserve immutable existing plan IDs and results. Not applied. Ready strategies can reproduce saved plans, but clean regeneration requires this fix.

### F02 — High: event anchor rollover can reuse a prior event's range

[evaluateEventSetup state reset](E:/GPT/Inves/demo_event_setup_20261008.mjs:101) clears range only on strategy-version change; [range initialization](E:/GPT/Inves/demo_event_setup_20261008.mjs:167) occurs only when state.range is absent. Supplying a new valid eventAnchor with the same dynamic version and old state retains the previous event range/processed timestamps. Fresh-anchor validation alone does not prevent stale-range decisions. This is a conditional defect, not an assertion that a trade was affected.

Proposed fix: key persistent event state by anchor release/window identity and reset or reject mismatch before processing; fixture covering two anchors with same rulesVersion. Until then independent state per event is necessary. Not applied.

### F03 — High operational limitation: managed-expiry GTC orders outlive local45second intention

[rr2-native request construction](E:/GPT/Inves/.skill-tools/rr2-native.py:153) changes managed-limit expiry to gtc; [manager cancellation](E:/GPT/Inves/.skill-tools/rr2-parallel.js:24) handles elapsed expiry on a later wakeup. This is documented design, not a broker-enforced deadline. A delayed/stopped manager can allow late fills; historical OHLC/touch tests cannot establish intended execution. Current manager is disabled; no live order status was inspected.

Proposed test/fix: model acceptance/cancel/fill races and manager outages; explicitly reconcile late fills; consider broker expiry only where contract supports it and with separately authorized execution changes. No order or policy changes applied.

### F04 — Medium: configuration and installed instructions describe different strategies/risk regimes

[current config](E:/GPT/Inves/Trading_Manager_Config.json:41) has null percentage/drawdown/count caps and minimum volume; [model_path](E:/GPT/Inves/Trading_Manager_Config.json:54) points to old buy-only MicroMAP while [helper](E:/GPT/Inves/Trading_Manager_Config.json:81) points to RR2 momentum. [news_filter_enabled](E:/GPT/Inves/Trading_Manager_Config.json:218) is false. Old installed contract describes1%/10%/2%, one global position and calendar blocks; current protocol has one owned exposure per symbol and report-only cost reserve. Older workflow launch narratives conflict with disabled/suspended flags. No single global default can be safely inferred.

Proposed fix: version-specific schemas and validated helper/model/policy mapping; mark unused fields as historical; update runbook with canonical suspension and effective thresholds. Preserve policies pending a separate user decision. Not applied. These mismatches are documented without treating past waiver prose as current authorization.

### F05 — Medium: legacy rolling evaluator does not implement promised gap validation

[external evaluator](%USERPROFILE%/.codex/skills/mt5-trading-manager/scripts/evaluate.mjs:7) checks sorted times/latest M5 and exact M1 trigger but not continuous20bar/ATR history. Its [installed analysis instructions](%USERPROFILE%/.codex/skills/mt5-market-analysis/SKILL.md:10) require gaps/context checks. A discontinuous M5 sequence can define a nominal20bar range spanning missing history. External evaluator also receives no H1, despite prose describing H1 context.

Proposed fix: reject/reset gaps and separate documented context from actual inputs; archive external source for a reproducible test. Not applied.

### F06 — Medium: partial legacy harnesses and native module side effects block safe testing

[continuation/RSI](E:/GPT/Inves/Intraday_Continuation_Simulation_Functions_20261007.js:1) depends on an undefined global prepared and externally generated indicators; RSI period/smoothing is not specified there. [MicroMAP native](E:/GPT/Inves/.skill-tools/micromap-native.py:16) executes a text slice of backtest.py; that source's layout is an implicit API. [native backtest](E:/GPT/Inves/research/poursamadi-backtest/backtest.py:1) performs reads/output/native initialization at module scope. [dispatch](E:/GPT/Inves/research/backtest-only-20261010/dispatch_active.py:66) executes another registered helper. Importing/running these is not a harmless smoke test.

Proposed fix: pure versioned signal modules, explicit inputs, __main__ guards and isolated adapters with no terminal/order capabilities. Not applied. No such code was imported during this review.

### F07 — Medium: historical evidence is exposed, selected, and not a capital portfolio

[optimization_10_cycles.mjs](E:/GPT/Inves/research/poursamadi-backtest/optimization_10_cycles.mjs:16) creates100 records by copying the same saved partition metrics with changes=[]; these are not100 independent optimizations. [offline metrics](E:/GPT/Inves/research/overnight-20261010/engine.py:154) explicitly uses fixed1R equity, not broker margin/capital feasibility. [final summary](E:/GPT/Inves/research/overnight-20261010/FINAL_SUMMARY_20261010T052334635887Z.md:27) says no candidate passed;448 model-symbol searches and incomplete tick/cost coverage limit inference. Later historical blocks are also already exposed. Preserved artifacts have not been re-simulated or exhaustively reconciled in this review.

Proposed fix: label repeated records as repeated summaries, reserve new OOS before observation, test capital/margin separately, retain missing-cost and small-sample uncertainty. Do not promote a strategy on these files alone.

### F08 — Low/medium: M5 copied metadata and actual simulation differ

[M5 request](E:/GPT/Inves/research/overnight-20261010/m5/request.json:53) retains M1 spread/entry prose while [load_data](E:/GPT/Inves/research/overnight-20261010/m5/engine.py:53) aggregates to M5 and uses five prior M5 spreads. Stress scenario text says one_minute_late_entry but delay_bars=1 represents5minutes there. targetR config is metadata: rr_tp hardcodes2. This can mislabel experiment meaning without changing the executed formula.

Proposed fix: derive descriptive metadata from barSeconds and assert declared targetR equals effective2R; do not silently alter historic simulations. Not applied.

## Graph audit, repair and validation

No existing graph, extraction config or project-owned Graphify mapping was found. This is recovery of a missing graph, followed by correction of a fresh extraction; counts must not be represented as deletion of stale prior work. There were no obsolete graph paths or deleted-symbol nodes to compare against a prior graph. Renames/history cannot be established without Git or older graph.

|Measure|Raw structural extraction|Repaired result|
|---|---:|---:|
|Nodes|690|846|
|Relationships|1,722|1,924|
|Edges without an explicit endpoint node|570|0|
|Duplicate node IDs|0|0|
|Invalid existing source references / line positions|Not a complete pre-repair measure|0|
|Exact duplicate edge records removed|—|0|
|Directed endpoint pairs|—|1,852|
|Preserved relationships beyond simple projection|—|72|

Raw missing endpoints mostly denote external imports/module-member references, not570 broken local calls. Repairs:

- Canonicalized23 references to the excluded vendored MetaTrader5 package to one external package identity.
- Corrected178 `calls` edges whose targets were modules into `uses_module_member`, retaining original caller/source lines; a module namespace is not a callable function.
- Added file nodes for supported-but-unmodeled wrappers and the MQL5 file, plus20initial and4additional source-checked wiring/config/state mappings. Added109 lexical host API references; they explicitly do not assert invocation or connector availability.
- Merged84 semantic nodes/65 document-claim relationships across23files. Documentation confidence EXTRACTED means explicit text, not implemented behavior. Added4 INFERRED data-propagation links with caller evidence distinct from direct function calls.
- Preserved separate imports/calls/contains/rationale/config reads/state writes/data-flow and conceptual relationships; no legitimate edge was removed for visual tidiness. Repeated call sites and different relationships between the same pair survive export.
- All corrections are repeatable in new project-owned [repair_graph.py](E:/GPT/Inves/research/project-review/repair_graph.py) and [graph_mappings.json](E:/GPT/Inves/research/project-review/graph_mappings.json); mappings fail if evidence text/target files disappear. [extract_graph.py](E:/GPT/Inves/research/project-review/extract_graph.py) explicitly selects first-party source and excludes vendored/generated directories. It never imports application modules.

Final confidence counts: EXTRACTED1,894; INFERRED29; AMBIGUOUS1. Ambiguous import resolution is retained, not guessed. External nodes intentionally have no in-repository source location; their incoming reference evidence is attached to source code. Two installed external skill files are explicit absolute-path dependencies; portability is documented, not hidden. Static Python/JS extraction cannot resolve all dynamic module loading, source slicing, generated strings, host eval, or anonymous-wrapper internals. Capturing a lexical API name is not a runtime trace.

Graphify uses a DiGraph for clustering/report centrality. Its diagnostic warns that72additional relationships would collapse under that representation. Export uses supported original_links to preserve all1,924 links and sets multigraph=true; assertions verify exact edge count, direction and endpoints. HTML is generated from this same JSON. Graph report discloses projection counts; centrality/cohesion use1,852 endpoint pairs rather than all evidence records. No promise of per-edge distinguishability at every zoom level of the visualizer. Token usage for semantic extraction is unavailable; zeros required by Graphify are placeholders, not a claim of zero model cost.

Artifacts:

- [Interactive graph](E:/GPT/Inves/graphify-out/graph.html)
- [Graph JSON](E:/GPT/Inves/graphify-out/graph.json)
- [Graph report](E:/GPT/Inves/graphify-out/GRAPH_REPORT.md)
- [Evidence-complete extraction](E:/GPT/Inves/graphify-out/extraction_repaired.json)
- [Correction log](E:/GPT/Inves/graphify-out/repair_log.json)
- [Counts / validation](E:/GPT/Inves/graphify-out/validation.json), [assertion results](E:/GPT/Inves/graphify-out/checks.json), [Graphify projection diagnostics](E:/GPT/Inves/graphify-out/diagnostics.json)

Rebuild workflow: use interpreter recorded in graphify-out/.graphify_python; run research/project-review/extract_graph.py, refresh semantic evidence if its source documents changed, run repair_graph.py, run `graphify export html`, run validate_review.py. Do not use generic graphify update alone, because it does not apply these project mappings or curated exclusions. Source hashes must be reviewed on future rebuild, not treated as permanent proof. Raw extraction/semantic sidecars are retained intentionally for audit/reproducibility. Newly written graphify-out files are normal workspace files; no Git ignore policy was changed.

### Implemented relationship trace

Offline: archive pointer→load_data (offset/OHLC and optional M5 aggregation)→ATR/EMA/prior-range arrays→signals→replay (spread/risk/size/exits)→metrics→choose/combined.select→report. Selection is performed after independent historical simulations; it is not a live execution risk gate. No broker order edge is added to offline replay.

Native: configured rr2 helper→copy_rates/copy_ticks data inside candidate→ATR and5second mid-return→M1 agreement→symbol/exposure/cost/profit/margin gates→minimum volume and limit/brackets→immutable intent/lock→host pending-order API→universe-position verification/hundred-state reconciliation→journal/review. Multiple phases live inside candidate rather than separate functions; graph does not invent callable “risk stage” functions. Disabled config and runtime guards condition reachability. No graph edge asserts a completed order.

Event: saved screen input+anchor→CLI evaluateEventSetup→normalize/ATR/stateful range/retest/confirmation→risk/volume proposal→screen output. That path ends at a proposal; no nonexistent evaluator-to-broker-send call is invented.

## Checks actually performed

- Recursive instruction/root/graph discovery and Git status attempt; no Git checkout/old graph found.
- Graphify installed interpreter and API inspection, deterministic static extraction of100file corpus (99supported;13supported JS files yielded no symbols; MQL5 only supplemented as file identity).
- Graph repair/build and HTML export completed; graph assertions passed: unique IDs, existing endpoints, permitted confidence values, per-edge evidence, source-file existence, line positions and lossless parallel export.
- HTML embedded data checked against JSON:846node identities and1,924directed edge endpoints match.161document links/source line references checked. The generated visualizer was not browser-rendered in this review; its vis-network library loads from a pinned external CDN.
- Source SHA256 assertions passed for all100original inventoried files;50Python source files parsed with ast.parse, never imported. Review tooling also parsed.
- Compared saved M1/M5 model IDs: zero overlap. This disconfirmed corruption of existing plans and scoped F01 to fresh regeneration risk.
- Identity validation includes source location, preserving the legitimate separate nested close() functions in the two legacy simulators rather than merging them by label.
- Graphify query smoke test succeeded; its700token output was explicitly truncated (23of239matched nodes), not used as complete evidence for strategy logic.
- No strategy unit/synthetic tests, historical simulations, optimizations, native terminal probes or order calls executed. Existing verification logs were not re-certified.

## Changed files and remaining work

New deliverables are this report, STRATEGY_CATALOG.md, STRATEGY_TEST_PLAN.md, SEMANTIC_REVIEW.md, extract_graph.py, repair_graph.py, validate_review.py and graph_mappings.json under research/project-review; graphify-out contains generated graph/report/HTML, extraction/semantic/detection/interpreter/root/label sidecars, extraction caches, source manifest and audit/check JSON. Existing trading sources, configs, state, journals, results and installed skills were not edited.

Remaining limitations: dynamic runtime paths and external host APIs cannot be fully proven statically; unsupported MQL5 symbols and anonymous JS internals have only partial graph coverage; external skill code is outside the portable workspace; no complete historical data/account reconciliation or current service/account inspection; no established full source-video review. These limits do not prevent selecting a reproducible offline candidate, but they prevent claims of complete runtime assurance or profitability.

Suggested first candidates: S01 and S02, with S03/S04 next, because of explicit rules, common offline replay, frozen parameters and existing artifacts. S05 is fully numerical but more complex; native/legacy families need the stated isolation/preparation fixes. The ranking reflects testability, not expected returns. Stop here for user selection.
