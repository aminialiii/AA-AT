# Objective Verification & Automated Testing Plan (`verification_plan.md`)

Per **Phase 3 (`VERIFICATION`)**, **Phase 8 (Item 6 & 10: Automated Tests & Source Validation)**, and **Phase 12 (Final QA)**, this document defines the automated verification suite that validates the Codex Astra implementation against the source material.

---

## 1. Automated Verification Matrix (`12 Deterministic Assertions`)

| Test ID | Target Module | Source Traceability | Verification Assertion | Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| `TEST_01` | `WeeklyMapIndicator` | `VIDEO_01:00:13:40`, `weekly-map-indicator` | Given $H_{w-1}=2640.0, L_{w-1}=2600.0$ ($\Delta_w=40$), compute all 13 levels and Weekend Gap ($C_{w-1}=2630.0, O_w=2632.0$). | `1.25x == 2650.0`, `2.0x == 2680.0`, `50%_Mid == 2620.0`, `-2.0x == 2560.0`, `gap_points == 200 >= 5`. |
| `TEST_02` | `PreviousDaySessionLevels` | `VIDEO_01:00:14:26`, `previous-day-session-indicator` | Given `US30` `M15` bars across 24 hours where pre-market high is `44500` at `09:00` and NY session (`16:30–23:00`) high/low are `44300`/`44000`. | Indicator ignores `09:00` high and returns `High == 44300.0`, `Low == 44000.0`, `Mid == 44150.0`. |
| `TEST_03` | `RoundLevelsIndicator` | `round-levels-indicator` | Compute automatic round step (`0.5%` rule) for Gold at `4000`, `EURUSD` at `1.1000`, and `US30` at `46000`. | Returns `20.0` for Gold, `0.0050` for `EURUSD`, and `250.0` for `US30`. |
| `TEST_04` | `TimeStrategyEngine` | `VIDEO_01:00:14:42–00:22:40` | Evaluate `XAUUSD` at `10:15`, `US30` at `14:00` (outside NY), and `XAUUSD` at `16:26` (`4 mins` before `16:30` Time Point). | `10:15 XAUUSD -> Grade A (allow=True)`; `14:00 US30 -> NONE (allow=False)`; `16:26 -> pre_timepoint_warning_gold=True (allow=False)`. |
| `TEST_05` | `SP2LStrategyEngine` | `VIDEO_04:00:06:38–00:38:00` | Test impulse **without** `P-Gap` vs. impulse **with** `P-Gap` ($L_2 > H_0$) followed by pullback bar $L_3 < L_2$. | Impulse without `P-Gap` returns `None`; valid `SP2L` returns primary entry at $L_2$, SL behind $L_0$, `1:1` TP, and `50%` scale-in with `3.0R` payoff. |
| `TEST_06` | `ProBTBStrategyEngine` | `VIDEO_03:00:25:00–00:48:00` | Generate orders for all **6 Entry Modes (`1..6`)** and **3 SL Anchor Modes** on a bullish breakout. | Modes 1 & 4 emit `BUY_LIMIT` (on BE Close vs Broken Level); Modes 2 & 5 emit `BUY_STOP`; Modes 3 & 6 emit `BUY_MARKET`; all enforce `R/R >= 2.0`. |
| `TEST_07` | `MicroMapStateMachine` | `VIDEO_02:00:21:48–00:29:03` | Simulate 3 consecutive stop-outs (`Entry 1 -> SL`, `Entry 2 -> SL`, `Entry 3 -> SL`) and attempt a 4th bar evaluation. | After 3rd SL, `invalidated == True` and 4th evaluation returns `INVALIDATED_AFTER_3_STOPS`. |
| `TEST_08` | `MicroMapStateMachine` (Doji Buffer & Inside Bar) | `VIDEO_02:00:24:17`, `00:50:27` | Feed a single `Inside Bar` and a tiny `Doji` trigger bar to `MicroMapStateMachine`. | `Inside Bar` arms immediately; `Doji` SL is buffered behind `min(bar.low, prev.close, prev.low) - 1.5 * spread`. |
| `TEST_09` | `ExecutionGuards` (180s Hold Rule) | `VIDEO_02:00:49:08`, `00:59:25` | Attempt to close a winning `M1` trade at `elapsed = 60s` vs `elapsed = 185s`. | At `60s`, returns `(False, "HOLD_TIME_GUARD_ACTIVE")`; at `185s`, returns `(True, "OK_TO_CLOSE")`. |
| `TEST_10` | `ExecutionGuards` (`Half-Close` Insurance) | `VIDEO_01:00:24:58` (`فرمول هاف‌کلوز`) | Execute `Half Close` (`50%`) at `3.0R` on a `$100` initial risk trade, then simulate price reversing all the way to hit the original SL. | Realized half = `+$150`, remaining half SL = `-$50`, guaranteed worst-case net profit = **`+$100.00` (`+1.0R`)**. |
