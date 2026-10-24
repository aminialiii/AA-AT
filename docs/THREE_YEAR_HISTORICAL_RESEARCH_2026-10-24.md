# Three-year historical research readiness — 2026-10-24

The follow-up [historical data acquisition record](HISTORICAL_DATA_ACQUISITION_2026-10-24.md) documents the independent provider check, its empty download response, exact broker export requirements, and a bounded ZIP-to-Parquet importer. No provider archive was accepted; the blocked counts below remain unchanged.

**No three-year backtest has run.** The existing research warehouse contains 395 broker-confirmed DEMO closes, but zero imported market bars, zero imported ticks, zero historical backtest runs, and zero simulated historical trades. Missing backtest metrics are unavailable, not zero. The machine-readable assessment is `E:\GPT\Inves\AA-AT-research-state\analytics\historical\assessments\b8e35c7173789ea121b0\assessment.json`.

## Safety and reproducibility gate

The pre-backtest backup was queued through the existing independent backup worker. The worker reported V2 success at `2026-10-24T15:18:51.157865Z` with SHA-256 `7a3df6f5c193f8c9822e1d3e372f25133c5541574cd96745b81e0178a0ed35a5`, 25,248 files, 395 closed broker positions, and 8,317 research artifacts. Independent verification checked the archive SHA-256, ZIP CRC, every member digest, and 12 isolated SQLite restores. V1 and V3 were preserved by rotation. No trading task or broker terminal was restarted or queried for the backup.

The intended half-open UTC research window is **[2023-10-24 00:00, 2026-10-24 00:00)**, covering 36 calendar months through the latest complete calendar trading day, 2026-10-23. This is a *target*, not a claim that market data covers it. The archive's last recorded M1 bar is 2026-10-09 20:59 UTC under an unverified fixed broker offset. The actual backtest period must be frozen against a verified source calendar before any run. Chronological development, validation, and untouched holdout partitions will be registered before examining outcomes.

The existing research database `E:\GPT\Inves\AA-AT-research-state\research.sqlite3` now indexes the blocked assessment in `historical_assessments`. It also has empty `historical_backtest_runs` and `historical_backtest_trades` tables; the latter requires `source_type='HISTORICAL_BACKTEST'` and cannot be confused with the existing broker-confirmed `trades` table. No historical outcome was inserted. The assessment lives under the existing `analytics\historical` tree. The dashboard reads it through an authenticated endpoint and keeps live DEMO PnL separate.

## Strategy inventory and execution readiness

The frozen source hashes in the previous S01–S18 inventory were rechecked against the current local source files. All 18 matched. Source verification proves file identity, not three-year execution fidelity.

| IDs | Historical status | Reason |
|---|---|---|
| S01–S05 | DATA_GATED | Original offline M1 signal/replay implementation exists. The 36-month M1/Bid-Ask path, historical timezone/DST map, broker contract and transaction-cost history, and faithful portfolio execution model are unverified. S05 is a numerical proxy, not exact source SP2L. |
| S06–S08 | NOT_EXECUTABLE | Tick/short-bar data, native terminal dependencies, archived version-specific rules or fill events are insufficient for a faithful isolated replay. |
| S09 | NOT_EXECUTABLE | Event anchors, multi-event history, and a faithful historical state/execution harness are absent. |
| S10–S12 | NOT_EXECUTABLE | Prepared EMA/ATR or RSI pipeline and provenance are missing; RSI period/smoothing must not be guessed. |
| S13–S15 | NOT_EXECUTABLE | Protocol-specific tick, exit, and installed-skill dependencies are not frozen into a comparable historical harness. |
| S16–S18 | NOT_EXECUTABLE | These remain documentation-only proposals with unresolved mechanical rules. |

Individual source references and the exact blockers appear in the assessment JSON and [strategy catalog](../research/project-review/STRATEGY_CATALOG.md). None of the 18 has a completed three-year baseline, so no combined portfolio simulation can be responsibly computed.

## Historical market coverage

The seven hashed legacy broker M1 NPZ files each contain 95,000 bars: **665,000 bars total**. Their structure, row counts, strictly increasing timestamps, nonnegative recorded spread, source hashes, and manifest start/end points were checked. Under the manifest's assumed fixed 180-minute broker offset, XAUUSD begins 2026-07-01; the six FX series begin around 2026-07-09. The FX files end 2026-10-09 20:59 UTC; XAUUSD ends 19:59 UTC. These roughly three-month archives do not cover the target start, most of the final month, or a three-year holdout. The 12 copied MT5 `.hcc`/`.tkc` cache files remain opaque: filenames cannot establish symbol, UTC, Bid/Ask, or gap coverage. Saved narrow tick windows do not provide continuous three-year tick history.

The manifest's single 180-minute offset is **not verified across historical daylight-saving transitions**. Non-60-second bar intervals range from 15 to 74 by symbol; weekend and session closures require a trading-calendar audit before they are called missing observations. The existing warehouse imports none of these archives as verified market observations. No provider was silently substituted, and no synthetic prices filled gaps.

## Conditions for a real baseline run

1. Acquire genuine, licensed historical bars and, for fill-sensitive work, ordered Bid/Ask ticks for every relevant strategy-symbol pair. Record provider, retrieval time, source hash, timezone/DST map, symbol specification history, and calendar; import once into the existing warehouse using bounded chunks and source-partitioned storage.
2. Prove interval and warm-up coverage, duplicate/gap rules, price integrity, and exact completed-candle timing. Keep invalid intervals out of the eligible sample. Obtain contract size, tick value/currency conversion, stop levels, commission, swap, spread, and explicit slippage sensitivity.
3. Freeze S01–S05 baseline model/config hashes and reproduce their signals from the original source in an isolated executor. Preserve the M1 approximation label if ticks are unavailable. Test same-candle SL/TP ambiguity, position sizing, exits, partial fills, and accounting before creating any historical run row.
4. Run standalone strategies chronologically. Build the combined portfolio through a single event queue applying five slots, 2% aggregate risk, 0.25% trade risk, daily-loss and drawdown gates, and a deterministic signal priority. Do not sum independent PnL curves.
5. Register the train/validation/untouched-holdout boundaries and acceptance criteria before viewing holdout results. Store immutable source hashes, engine/config versions, run checkpoints, historical trade journal, uncertainty, and quality flags under the existing research namespace. Never write simulated rows to the DEMO ledger.

The read-only readiness script is `python -m research.trade_forensics.three_year`. Reruns with unchanged evidence are idempotent. A newer verified backup changes the assessment identity while preserving prior reports. The authenticated dashboard's **3-Year Historical Research** tab at `http://127.0.0.1:8765/` shows the explicit blockers instead of fabricated equity curves or rankings. The isolated dashboard release `E:\GPT\Inves\AA-AT-dashboard-release-historical-v1` passed 13 read-only route checks, unauthorized-access rejection, and stale-status validation before the dashboard task alone switched to it. The previous analytics-v2 release remains available for rollback. Trading service and risk-policy hashes, task state, stop-marker state, and the 395-close broker ledger were unchanged across that switch. Current trading state needs its own safety recovery review; this research did not clear or bypass its stale broker-status gate.
