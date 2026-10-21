# Demo operational repair — 2026-10-08

## Changes applied

- Added `demo_event_setup_20261008.mjs` as the evaluator entry point for `US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1`.
- Updated `Demo_Cycle_Policy_20261008.json` to use that evaluator and the registered event-anchor file.
- Registered a prospective `FOMC_2026-10-28` anchor from the official Federal Reserve calendar. The anchor is future-only and cannot reopen the expired 2026-10-07 window.
- Recorded the repair and future-anchor status in the MT5 monitor state file.
- Created `Demo_Monitor_State_20261008.json` as the canonical state and retained the 20261007 file as legacy history.
- Cleared old `event_ranges` and `pending_signals` from the canonical state; they are preserved only under legacy fields and cannot be consumed by the next run.

## Safety invariants retained

- `research_gate_passed=false` and active risk remains 1%; 5% remains only a hard ceiling.
- No forced order is enabled. The evaluator still requires fresh bars, a fresh quote, margin evidence, contract metadata, spread/cost gates, the structural stop, deduplication, one open position maximum, the two-loss halt and the 2% observed peak drawdown halt.
- The next anchor is only eligible during `2026-10-28T18:15:00Z` through `2026-10-28T20:15:00Z`, with entry cutoff `2026-10-28T20:29:31Z`.

## Verification

- Static syntax check of the new evaluator and screen CLI: passed.
- Dynamic evaluator smoke check: a missing anchor is rejected, while the registered future anchor reaches the normal `immutable_range_not_closed` gate instead of the anchor error.
- Current account snapshot at `2026-10-08T11:24:03Z`: connected, demo, USD, writable; balance/equity 99.90 USD; no open positions or orders.
- Terminal journal review through `14:25` local time showed successful preflights and no trading or connectivity error records.
- Existing sample remains one connectivity test only (`-0.10 USD`); it is not profitability evidence.

## Acceptance status

The operational path is repaired and ready for the next fresh event. Profitability is still unvalidated; the acceptance gate remains 20 out-of-sample closed trades, positive net after costs, profit factor at least 1.1 and peak drawdown at most 2%.
