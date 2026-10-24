# Next actions

Historical acquisition checkpoint, 2026-10-24: V2 was independently reverified
with 25,248 archive members and 12 isolated SQLite restores; all three rotating
slots and the backup worker remain present. The HistData catalog documents
seven priority symbols, fixed-EST M1 Bid bars and Bid/Ask ticks, but its last
listed update was October 18 and a bounded EURUSD download returned an empty
body. No archive was accepted. A research-only ZIP-to-Parquet importer is now
fixture-tested in the existing warehouse (65 offline tests passed). Obtain a
real archive or broker-matched export from a **separate** research terminal,
plus historical contract/cost specifications, then validate coverage before
running any baseline. See `docs/HISTORICAL_DATA_ACQUISITION_2026-10-24.md`.
No trading service, frozen rule, DEMO ledger or portfolio limit was changed.

Three-year historical research checkpoint, 2026-10-24 19:57 UTC: the new
pre-backtest V2 ZIP passed SHA-256, CRC, 25,248 member hashes, and 12 isolated
SQLite restores. The research warehouse now has assessment
`b8e35c7173789ea121b0`: all 18 frozen source hashes matched; S01–S05 are
data-gated and S06–S18 are not faithfully executable for this run. The seven
legacy M1 archives total 665,000 bars but cover only roughly July–October 2026
under an unverified fixed broker offset. The warehouse still has zero imported
market bars/ticks and zero historical runs or simulated trades. Obtain genuine
three-year source data, a verified timezone/DST map, contract and cost histories,
then validate an isolated execution engine before any baseline or portfolio
backtest. Keep simulated data outside the broker DEMO tables. The collector
remains healthy at 395 closes; the trading task is Ready with no detected
service process and a stale SUSPENDED status. Investigate that separately under
the authorized broker safety recovery procedure. See
`docs/THREE_YEAR_HISTORICAL_RESEARCH_2026-10-24.md`. The authenticated
dashboard-only historical release is live on loopback; retain analytics-v2 as
rollback. Its switch did not change trading source/risk hashes, task state,
stop marker, or broker ledger count.

Research analytics checkpoint, 2026-10-24 14:46 UTC: V1 backup and isolated
restore passed; 395-trade versioned analysis, redacted exports, daily analytics
task, and dashboard-only release are operational. The daily analytics task now
uses the frozen `AA-AT-analytics-release-v2` source and completed a fresh run;
its bounded chart job correctly reports `BLOCKED_NO_RECORDED_M1`. The research
commit `18c4616d2c832affd906d53e5418e122ef822116` was pushed to the
existing private review branch without a trading deployment. Current trading task check
found `CodexDemoForward20261021` Ready with no trading-service process; the
broker status file is stale and SUSPENDED. Under the read-only research mission,
do not restart workers or clear quote/clock safety gates. Investigate the
trading outage separately through authorized broker reconciliation and safety
recovery. For research, obtain a supported offline export of broker-matched
Bid/Ask ticks and candles and verify UTC coverage before charts, MFE/MAE,
counterfactual outcomes, or one-year backtesting. Keep TP=5 excluded pending
a unit definition. Retain the old dashboard release for rollback; do not merge
the draft research PR or deploy any strategy changes automatically.

Research checkpoint, 2026-10-24 03:01 UTC: continue the independent five-minute
collector and 24-hour three-slot backup worker. V1–V3 and the V3 SQLite
restore drill passed; the authenticated research dashboard is live. The portable dataset
contains 395 verified closed lifecycles but zero recorded candle/tick rows.
Acquire a provenance-tagged broker export or existing archive through a source
that does not contend with the active terminal before producing factual trade
charts or excursions. Validate broker timezone and missing Bid/Ask/SL/TP-event
coverage; never infer the absent events. Review this isolated research branch
and the fresh broker safety heartbeat before any
subsequent operational change. Do not clear the quote freshness gate or S04
breaker for research convenience.

The four-hour Git sync task passed a normal quiet-source cycle, offline tests,
and secret scanning on 2026-10-24 03:01 UTC. It pushed 19 changed files to
`automation/source-sync` at `300d81b6c7cf78892aade575fd4f512b72b6b22c`
for review in PR #1, without deployment. Keep the remote-tip guard in place.

The trading task is currently Ready with no detected trading-service process, and its latest broker status file is `SUSPENDED`
with `broker_clock_or_quotes_inconsistent`; DEMO verification and new order
routing remain fail-closed. The 395 closed trades are prior broker-reconciled
records, not a claim that trading is presently active.

Earlier recovery on 2026-10-23 verified 227 closes and 454 deal IDs at restart,
and two protected broker positions at a subsequent point-in-time check. Those
observations are historical; do not treat them as the current account state.
The maintenance stop marker was found absent after the user reported an
administrator's approval, but no approval decision ID was independently available.

1. Monitor service heartbeat, DEMO guard, broker positions and pending orders,
   ownership, risk utilization, order intents, and safety events. Stop or
   suspend routing on any reconciliation or risk failure; do not force signals.
2. Keep S04 blocked until its fill-risk event is reviewed through the risk
   process. Its breaker now reloads from the persistent safety-event ledger on
   restart. Do not reset it merely to enable the worker.
3. Keep S06–S18 blocked until executable rules, adapters, and safety dependencies
   are independently verified. Preserve frozen S01–S05 strategy definitions.
4. Review the dashboard control bridge candidate separately. The running
   dashboard monitors live broker-reconciled service status, but management
   commands remain unavailable because the bridge is not deployed. Do not
   couple a dashboard release to a trading-service restart.
5. Keep the four-hour Git sync task active and the recovery PR unmerged pending
   review. Verify the admin stop-clearance decision record if it becomes
   available; retain the maintenance-stop incident evidence.

Continuation command: `Resume AA AT from E:\GPT\Inves\AA-AT\CHECKPOINT.json; verify current DEMO broker state and safety events before any execution change.`
