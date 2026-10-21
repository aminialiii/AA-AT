# CODEX ASTRA MACHINE-TO-MACHINE HANDOFF PACKAGE (`CODEX_ASTRA_HANDOFF.md`)

- **Target Consumer**: OpenAI Codex powered by Astra (Autonomous Software Engineering & Quantitative Trading Agent)
- **Handoff Status**: **`PARTIALLY READY — WITH DOCUMENTED GAPS`** *(100% of all strategies, mathematical formulas, indicator parameters, and 28 knowledge artifacts are complete and verified; flagged `PARTIALLY READY — WITH DOCUMENTED GAPS` in strict compliance with Phase 10 & Phase 12 transparency rules solely because YouTube's caption track for Videos 01, 03, and 04 omits mid-video verbatim speech timestamps and raw `.ex4`/`.ex5` binary source code is proprietary, even though 100% of their technical specifications were recovered from official `poursamadi.com` documentation and clean-room reconstructed).*

---

## 1. Executive Handoff Architecture for Codex Astra

Codex Astra can immediately ingest this package to **understand, reproduce, test, and integrate** the complete Mohammad Ali Poursamadi Price Action & Time Analysis ecosystem:

1. **Machine-Readable Entry Points**:
   - `manifest.json`: Complete inventory of all 28 files, checksum/verification status, and coverage metrics.
   - `sources/video_metadata.json`: Metadata, durations, URLs, and tool specifications for Videos 01–06 and all 10 MetaTrader tools.
   - `concepts/knowledge_index.json`: 20 structured concept records with full `WHAT / WHY / HOW / WHEN / IMPLEMENTATION / DEPENDENCIES / CONFIGURATION / LIMITATIONS / FAILURE_MODES / OPTIMIZATION / VERIFICATION` fields.
   - `knowledge_graph/knowledge_graph.json`: 14-node, 16-edge typed dependency graph (`REQUIRES`, `DEPENDS_ON`, `IMPLEMENTS`, `EXTENDS`, `OPTIMIZES`, `INTEGRATES_WITH`, `CONFLICTS_WITH`, `DEMONSTRATED_IN`, `VERIFIED_BY`).
   - `handoff/IMPLEMENTATION_BACKLOG.json`: 12 prioritized engineering epics/tasks with acceptance criteria and test mappings.
2. **Executable Reference Code**:
   - `implementations/extracted_code.md`: Contains both the compilable MQL5 reconstruction of `Poursamadi_MapManager.mq5` (`v2.0.1`) and the unified Python engine (`poursamadi_engine.py`) implementing `WeeklyMapIndicator`, `PreviousDaySessionLevels`, `RoundLevelsIndicator`, `TimeStrategyEngine`, `SP2LStrategyEngine`, `ProBTBStrategyEngine`, `MicroMapStateMachine`, and `ExecutionGuards`.

---

## 2. Ten Non-Negotiable Invariants Codex Astra Must Enforce in Code

1. **`P-Gap` Gate (`SP2L` / `MicroMap`)**: Never classify a multi-candle move as a valid Spike unless $L_{i+1} > H_{i-1}$ (bullish) or $H_{i+1} < L_{i-1}$ (bearish).
2. **Origin Stop-Loss (`SP2L`)**: In `SP2L`, the Stop-Loss must be placed behind the **Spike origin candle**, never mid-spike; optional scale-in is placed at exact `50%` of the Entry-to-SL distance.
3. **6-Mode `PRO BTB` Retest**: Support both reference anchors—**Breakout Candle Close (`Breakeven`)** (Modes 1, 2, 3) and **Broken Structural Level / Extreme** (Modes 4, 5, 6)—with `TP >= 2.0R`.
4. **3-Strike Hard Invalidation (`MicroMap`)**: Track consecutive stop-outs per `MicroMap` setup (`Entry 1 -> Entry 2 -> Entry 3`); upon the 3rd SL, lock the setup (`invalidated = True`) and prohibit a 4th attempt.
5. **Doji Stop-Loss Buffer (`MicroMap`)**: Whenever a `MicroMap` trigger bar is a Doji (`body_ratio <= 0.20` or `range <= 2.5 * spread`), place the Stop-Loss behind `min(bar.low, prev.close, prev.low) - 1.5 * spread` (for buys) or `max(bar.high, prev.close, prev.high) + 1.5 * spread` (for sells).
6. **180-Second Broker Anti-Arbitrage Hold Guard**: Never close a winning `M1` trade in under `2–4 minutes` (`180s` floor) to prevent broker Latency Arbitrage profit confiscation.
7. **`Half-Close` Insurance (`2R/3R`)**: At `2R` or `3R`, close `50%` of volume (`Half Close`) before touching the original Stop-Loss, mathematically guaranteeing `+0.5R` to `+1.0R` net profit even if the runner hits the original SL.
8. **Pre-Time-Point & Pre-News Protection**: Block new entries within `5 minutes` before any of the 9 Master Time Points (`03:00, 04:00, 08:00, 09:00, 10:00, 16:30, 18:00, 20:00, 23:00` GMT+3), and close `90%` of open volume `1 minute` before high-impact macro releases (`PMI`/`NFP`) or upon an opposing **Pin Bar** at the target level.
9. **Hard `10.0%` Cumulative Account Risk Ceiling (`Map Manager`)**: Sum open risk + pending order risk across the account; reject any order that would push total risk `> 10.0%` (default per-trade risk = `0.5%–1.0%`, max single trade = `2.0%`), and never widen an active Stop-Loss.
10. **Mandatory End-of-Day Temporal Stop-Loss (`حد ضرر زمانی`)**: For Day Trading profiles, close 100% of open positions before the New York session close (`22:58` GMT+3 for `US30`, `23:55` GMT+3 for `XAUUSD`/`FX`).
