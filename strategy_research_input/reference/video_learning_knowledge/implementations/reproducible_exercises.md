# Reproducible Practical Exercises & Mastery Criteria (`reproducible_exercises.md`)

Per **Phase 5 (Items 11 & 12: Practical Exercises & Measurable Mastery Criteria)** and **Phase 8 (Automated Verification)**, this document provides 5 progressive, reproducible exercises directly derived from Videos 01–06.

---

## Exercise 1: The 200-Toss & 32-Trade Random Walk Verification (From Video 06)
- **Source Reference**: `VIDEO_06:00:03:25–00:23:48`
- **Objective**: Empirically verify why `1%–1.5%` capital management makes account liquidation (`کال مارجین`) mathematically impossible even under a 50/50 random walk, and observe the uniform distribution of `1-point` spread near-misses.
- **Procedure**:
  1. Run a 200-trial random integer simulation ($N \in [1, 100000]$, Odd = Sell, Even = Buy) and plot streak lengths (verify occurrence of 4-loss and 8-win streaks).
  2. On a Demo (or `$0.10`-risk Cent) account, execute 16 sequential `1:1` R/R trades (`Risk = 1.5%`) accounting for a `20%` spread-to-stop ratio (`$3` spread on `$15` stop).
  3. Record every trade where price comes within `1–2 points` of `TP` or `SL` without triggering.
- **Measurable Mastery Criteria**:
  - Zero instances of Stop-Loss widening or lot-size doubling (`x2`).
  - Cumulative drawdown remains strictly `< 15%` across all 32 trades.
  - Verified observation that `TP` near-misses (where `Bid` touches Short TP but `Ask` does not) and `SL` near-miss saves occur with approximately equal frequency.

---

## Exercise 2: `SP2L` Candle-by-Candle Counting & `P-Gap` Audit (From Video 04)
- **Source Reference**: `VIDEO_04:00:06:38–01:08:25`
- **Objective**: Master candle-by-candle counting (`کندل‌شماری`) inside Market Cycles and distinguish valid Spikes (with `P-Gap`) from invalid overlapping moves.
- **Procedure**:
  1. Load `M5` and `M1` historical charts of `XAUUSD` and `US30` across 20 trading days.
  2. Identify 50 sharp directional moves. For each move, measure $L_{i+1} - H_{i-1}$ (bullish) or $L_{i-1} - H_{i+1}$ (bearish). Reject any move with `P-Gap <= 0`.
  3. On valid Spikes, mark the exact bar $t$ that sweeps the prior candle's Low/High ($L_t < L_{t-1}$ or $H_t > H_{t-1}$), mark Primary Entry ($P_1$), Origin SL ($S$), `50%` Scale-In ($P_2 = 0.5(P_1+S)$), and `1:1` / `1:2` TP.
- **Measurable Mastery Criteria**:
  - `100%` accuracy in rejecting non-`P-Gap` impulses.
  - Zero instances of placing `SL` mid-spike instead of behind the Spike origin candle.
  - Achieve positive net expectancy ($\ge +0.25R$ per trade) over 50 logged `SP2L` trades.

---

## Exercise 3: `PRO BTB` 6-Mode Retest Execution with `Map Manager` (From Video 03)
- **Source Reference**: `VIDEO_03:00:02:56–01:18:24`
- **Objective**: Master all 6 `PRO BTB` entry modes (`Limit on BE`, `Stop after return close`, `Market after return close`, `Limit on broken level`, `Stop on breakout extreme`, `Market with candle confirmation`) and `Map Manager` execution.
- **Procedure**:
  1. Install `Map Manager` in MT4/MT5 (`File -> Open Data Folder -> MQL4/Experts`), delete default `MACD`/`RSI` EAs, set `Risk = 0.5%`, and enable `Auto Trading`.
  2. Across 30 historical and live-replay `Breakout -> Return to Breakeven` structures on `M5`/`M15`, log the difference in fill rate and R/R across Modes 1 through 6 and the 3 SL anchor modes.
- **Measurable Mastery Criteria**:
  - Execute `Add Line` / `Add Pend Line` -> `Set Pending` in `< 5 seconds` without manual lot calculation.
  - Maintain average realized winner $\ge 2.0R$ across filled `PRO BTB` trades.
  - Execute 20 consecutive trades in pure **Set and Forget (`ست اند فورگت`)** mode at `0.5%` risk with zero mid-trade tampering (`انگولک کردن`).

---

## Exercise 4: `MicroMap` Chained `1-2-3` & `H2/H3` Confirmation Drill (From Video 02)
- **Source Reference**: `VIDEO_02:00:21:48–01:05:37`
- **Objective**: Master trailing `Buy Stop`/`Sell Stop` down a counter-trend micro-channel, executing `Entry 1 -> Entry 2 -> Entry 3` and `Opt 1 (H2)` / `Opt 2 (H3)` inside an `SP2L` or `PRO BTB` context zone while obeying the 3-Strike Invalidation Rule and the 180-second hold-time floor.
- **Procedure**:
  1. Screen-record 5 live New York sessions (`16:30–18:00` GMT+3) on `M1`/`M5` `XAUUSD` and `US30` (per Video 06 `00:21:16` Live Video Replay method).
  2. Replay the recorded video and identify 30 `SP2L` / `PRO BTB` pullback zones where a counter-trend micro-channel or `Inside Bar` forms.
  3. Compare the win rate and R/R of `Entry 1` (`H1`), `Entry 2`, `Entry 3`, `Opt 1 (H2)`, and `Opt 2 (H3 on Candle #4)`.
  4. Apply Doji SL buffering (`behind prior close/low + 1.5 * Spread`) on all Doji trigger candles.
- **Measurable Mastery Criteria**:
  - `100%` compliance with the **3-Strike Hard Invalidation Rule** (zero 4th attempts).
  - `100%` compliance with the **2–4 minute (`180s`) minimum hold duration** on all winning trades.
  - Demonstrate at least 3 nested `SP2L/PRO BTB + MicroMap` trades achieving $\ge 5.0R$ to $10.0R$.

---

## Exercise 5: Personal Time Plan & 100-Trade Triad Journal (From Video 01)
- **Source Reference**: `VIDEO_01:00:20:41–01:17:35`
- **Objective**: Construct a personalized multi-window trading plan using the 4 Discovery Rules, `Session Windows Pro`, `Weekly Map`, and the `Time + Level + Price Action` Signal Prioritization Triad.
- **Procedure**:
  1. Install `Session Windows Pro` and `Weekly Map` on MT4/MT5. Verify `New York start` aligns with `16:30` GMT+3.
  2. Select 2 to 3 personal Time Windows (e.g., `10:00–13:00`, `15:30–16:30`, `16:30–18:00` for `XAUUSD`, or `16:30–18:00` and `18:00–21:00` for `US30`).
  3. Log **100 trades** recording: `Trade_ID`, `Broker_Timestamp_GMT3`, `Window_ID & Grade`, `Horizontal_Level_ID` (`Weekly Map 2x/1.5x/50%`, `PDH/PDL`, `US30 Session HL`, `Round Level`), `Trigger_Variant`, `Priority_Tier (1, 2, or 3)`, `Half_Close_Executed (2R/3R)`, and `Net_R_Multiple`.
- **Measurable Mastery Criteria**:
  - Zero trades opened within `5 minutes` prior to a Master Time Point.
  - `100%` of intraday positions closed before the daily **Temporal Stop-Loss (`NY Close`)**.
  - Verified positive net expectancy across the 100-trade journal with Tier-1 (`Time + Level + PA`) trades outperforming Tier-3 (`PA only`) trades.
