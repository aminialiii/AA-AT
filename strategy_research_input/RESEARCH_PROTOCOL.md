# Offline Research Protocol

## Evidence and specification
Every rule must include source file, section/timestamp when present, evidence class, formal trigger, entry, stop, exit, invalidation, symbol/timeframe, assumptions and deterministic unit tests. Incomplete MicroMap, PRO BTB and exact SP2L definitions must remain SPEC_GAP until independently specified; proxies must retain separate names.

## Baselines and fair comparisons
Freeze code commit, symbol universe, account denomination, data source, timezone, tick size/value, leverage/margin assumptions, spreads, commissions, swaps, slippage, session calendars and corporate/data adjustments where relevant. Match datasets and execution model between baseline and candidate. Separate M1/M5/tick/S5/S15 paths and include timeframe in every identity and artifact key.

## Testing
Chronological train/validation/untouched-test partitions; purging/embargo for overlapping labels; walk-forward by market regime; no tuning on holdout. Model ambiguous OHLC stop/target collisions conservatively. Explicitly simulate pending order cancellation, GTC behavior, latency and 45-second manager timeouts. Validate rollover and anchor changes across sessions. Run negative tests, property tests, replay determinism, and no-lookahead tests. Test cost stress and parameter neighborhoods, and disclose number of attempted variants.

## Decision metrics
Report trade count, net expectancy (R/trade), net profit, max drawdown, drawdown duration, profit factor, win rate, turnover, exposure, median holding period, out-of-sample deterioration, cost sensitivity, confidence intervals and regime consistency. Use portfolio correlation and aggregate risk before suggesting combinations. Do not use Sharpe alone; treat tiny samples as inconclusive. No guarantee of future profitability.

## Gates
G0 inventory verified; G1 baseline reproduced; G2 rules specified; G3 offline evaluation reproducible; G4 shortlist prepared; G5 explicit user choice. G5 is a HARD STOP before demo/paper/live trading or production deployment.

## Output contract
`research_outputs/README.md`, `inventory.json`, `defect_audit.md`, `source_rule_map.csv`, `strategy_dossiers/Sxx.md`, `candidate_registry.csv`, `baseline_results.csv`, `candidate_results.csv`, `comparison.md`, `selection_shortlist.md`, `reproducibility_manifest.json`, `test_report.md`, `graph_before_after.md`. Each result must identify RUN / NOT_RUN / FAILED and provenance. Use explicit blockers instead of speculative performance numbers.
