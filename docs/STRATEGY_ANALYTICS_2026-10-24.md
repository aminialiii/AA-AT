# AA AT research analysis — 2026-10-24 UTC cutoff

This is descriptive research over **395 broker-reconciled, fully closed DEMO position lifecycles**, not a strategy change or a trading recommendation. The last recorded close is `2026-10-23T20:57:53.681Z`. The versioned machine-readable result is the local-only `E:\GPT\Inves\AA-AT-research-state\analytics\runs\0ec11d928ebb1283f1bb\priority3.json` (analysis run `0ec11d928ebb1283f1bb`). It freezes the verified research warehouse and records its SHA-256, source digest, backup hash, Git commit, analysis-engine hash, evidence class, definitions, and cutoff.

The immediate prerequisite backup succeeded in `D:\AA-AT-Backups\AA-AT-Backup-V1.zip`, SHA-256 `1dcfa46cf37f572cea2fbe72bbc337f8b5a353ea145e6340069eee2b4c7fd9fe`. All 25,154 archive entries passed hash/CRC validation; eight SQLite images passed isolated `PRAGMA integrity_check`. The archive contains the 395 closed lifecycles and 8,317 research artifacts. V2 and V3 remain present and verified. No worker was stopped for the backup.

## Broker-actual baseline

The 395 closes occurred on only **three UTC exit dates**. Combined broker gross profit was 49.64 account-currency units, gross loss was −46.39, recorded commission/swap/fee effect was −0.04, and net PnL was **+3.21**. This excludes unobservable historical spread and slippage decomposition; they may already be embedded in executed fill prices. Portfolio net profit factor was 1.069. The largest cumulative closed-trade PnL decline was 3.33 account-currency units. This is **not** maximum mark-to-market equity drawdown. Only five dashboard equity observations exist, insufficient to establish a true equity peak and trough.

| Strategy | Closes | Win rate | Net PnL | Mean realized R | Net PF | Closed-PnL DD | Exit days |
|---|---:|---:|---:|---:|---:|---:|---:|
| S01 | 51 | 33.3% | +1.12 | +0.017 | 1.229 | 1.48 | 2 |
| S02 | 115 | 35.7% | +1.31 | +0.032 | 1.099 | 1.79 | 3 |
| S03 | 76 | 35.5% | +0.57 | +0.029 | 1.063 | 2.32 | 3 |
| S04 | 152 | 32.9% | −0.19 | −0.003 | 0.990 | 2.50 | 3 |
| S05 | 1 | 100.0% | +0.40 | +0.976 | unavailable | 0.00 | 1 |

The five-strategy comparison is **exploratory**, despite S02 and S04 exceeding 100 closes. Trade clustering into three days prevents a defensible day-block expectancy interval or durable edge claim. The JSON contains Wilson win-rate intervals, direction, strategy-symbol, session, UTC hour, weekday, month, streak, duration, cost, and closed-PnL drawdown breakdowns. London, New York and Tokyo sessions are DST-aware and may overlap. None of the best-looking small groups is a validated schedule restriction.

## Configuration versions

Strategy IDs alone conceal different configuration hashes. These rows remain separate in the report:

| Strategy | Config SHA prefix | Closes | Net PnL | Mean R |
|---|---|---:|---:|---:|
| S01 | `090df890` | 51 | +1.12 | +0.017 |
| S02 | `090df890` | 113 | +1.07 | +0.027 |
| S02 | `c75ac362` | 2 | +0.24 | +0.324 |
| S03 | `090df890` | 75 | +0.31 | +0.019 |
| S03 | `c75ac362` | 1 | +0.26 | +0.812 |
| S04 | `090df890` | 136 | +0.90 | +0.017 |
| S04 | `c75ac362` | 16 | −1.09 | −0.169 |
| S05 | `090df890` | 1 | +0.40 | +0.976 |

The S04 difference is an observation, not evidence that one version is better: the samples are nonconcurrent and small. Exact full hashes and trade IDs stay in the local report and journal. No strategy version was altered.

## Market evidence and research gates

The warehouse has zero imported campaign bars and zero imported Bid/Ask ticks. All 395 trades have explicit quality flags for missing market context, entry and exit Bid/Ask, entry equity, and full SL/TP modification history. The recorded original SL/TP and broker fills remain available. The local MT5 October cache snapshot copied 12 opaque files (160,784,913 bytes) for AUDUSD, EURUSD, GBPUSD, USDCAD, USDCHF and USDJPY under `E:\GPT\Inves\AA-AT-research-state\broker_cache_snapshots\20261024T142108Z-2839173a`. Every copied file hash was verified. **Cache filenames and file bytes do not prove date, tick-side, timezone, or gap coverage**; no supported offline exporter was verified, and the active terminal was not queried.

Consequently, factual trade charts, MFE/MAE, entry-to-extreme distances, spread/slippage decomposition, stop-out-and-recovery patterns, and scenario performance are **unavailable**. No external-provider prices were substituted. The pure research counterfactual module accepts broker-sourced Bid/Ask ticks, a finite horizon, a recorded stop, provenance-backed contract valuation, and explicit commission/slippage/financing; it returns `INSUFFICIENT_EVIDENCE` when these inputs are absent. Break-even may still lose money after costs. Fixed stop/target, break-even, trailing, partial target, and time-exit rules can be evaluated individually or together after the data gate, but no current improvement estimate is reported. `TP = 5` is excluded until its unit is documented.

The source adapter reads completed M1 candles and rejects forming or stale candles (`research/demo-live-20261021/live_signals.py`); the frozen strategy rules are in `research/overnight-20261010/engine.py`. There are 396 logged live signals, 713 skipped signals, and 54 data/policy skips in the warehouse. Signal counts are **not** equivalent to closed trades or independent rejected opportunities. Without synchronized quote history and a proven signal-to-order join, entry quality and delayed/pullback alternatives cannot be quantified.

The proposed one-year historical window is `[2025-10-21, 2026-10-21)` UTC with six months training, three months validation, and three untouched months testing. No one-year backtest was run: broker-matched market coverage, timezone conversion, contract valuation, and realistic costs are not established. Any later simulated outcomes must remain outside the DEMO ledger and use registered acceptance criteria, chronological validation, cost sensitivity, ambiguity bounds, and multiple-testing adjustment.

## Operational boundary observed during research

The most recent local trading status file is from `2026-10-24T07:36:27.812588Z` and says `SUSPENDED` with `broker_clock_or_quotes_inconsistent`. A current Task Scheduler check found `CodexDemoForward20261021` in `Ready` state and no trading-service process; its last task result was `3221225786`. The file is stale and does not prove current broker positions or account state. The research task did **not** restart trading or clear a safety gate. The collector, backup worker, and dashboard are separate running tasks.

## Reproduction and next evidence

From the isolated source worktree, run `E:\GPT\Inves\AA-AT-research-venv\Scripts\python.exe -m research.trade_forensics.daily_analytics --git-commit <40-character SHA>`. It uses an online SQLite snapshot of the independent warehouse, checks the latest verified backup status, and publishes an immutable run plus `strategy_versions.csv` under `AA-AT-research-state\analytics\runs`. Rerunning unchanged evidence gives the same run ID. No trading module or MT5 API is imported.

The next research prerequisite is a supported **offline broker-matched export** of campaign Bid/Ask ticks and complete bars, with verified UTC mapping and per-trade gap coverage. Until then, research recommendations have no estimated Win Rate, expectancy, drawdown or PnL impact, and the hypothesis registry remains empty. Current task and broker safety status need an independent operational investigation under the trading recovery procedure, outside this read-only mission.

Portable local exports are `E:\GPT\Inves\AA-AT-research-state\exports\AA-AT-RESEARCH-DATASET.zip` (395 trades, 790 order records, 790 deal records, 1,163 signal events, 3,988 risk events; SHA-256 `830db0348303e125692b2463e5d3b3d4bbeeaa72cc12684ba9a9d77c0d92832e`) and `E:\GPT\Inves\AA-AT-research-state\exports\AA-AT-STRATEGY-ANALYTICS.zip` (versioned aggregates and redacted cache metadata; SHA-256 `cdbad1b67a1aa9b64966e37715511a121800a93b43690b06000cac14c3131e8f`). Both ZIPs are outside Git; the second contains neither the broker login nor the local Windows username. Their manifests and load guides explain the evidence split.
