# Cross-Video Intelligence Synthesis & Unified Architecture (`unified_architecture.md`)

Per **Phase 5 (Deep Conceptual Understanding)** and **Phase 6 (Cross-Video Intelligence Synthesis)**, this document synthesizes all six videos (`YKKdoH6QoG8`, `Dw4DhxHqKLE`, `NDk94Ob8sEo`, `7HEC5mO3d3U`, `oAea9hZlUOQ`, `elD9HV9hqJA`) and the official [poursamadi.com](https://poursamadi.com/en/) technical specifications into a single unified software and quantitative trading architecture.

---

## 1. The Four-Gear Unified Architecture (`چرخ‌دنده‌های یکپارچه`)

In **Video 01 (`00:00:40–00:00:48`)** and **Video 02 (`00:19:40–00:20:45`, `00:29:04–00:30:35`)**, Mohammad Ali Poursamadi explicitly defines how the four strategy videos interlock like mechanical gears (`چرخ‌دنده‌ها`) atop the foundational risk and mathematical axioms established in **Videos 05 and 06**:

| Architectural Layer | Component Name | Primary Video Source | Core Function in the Unified Engine |
| :--- | :--- | :--- | :--- |
| **Layer 0: Axiomatic & Psychological Kernel** | **Rationality Domain, Capital Management Invariance (`0.5%–2%` risk, `10%` cap) & Temporal Stop-Loss (`EOD Close`)** | `VIDEO_05` (`oAea9hZlUOQ`)<br>`VIDEO_06` (`elD9HV9hqJA`) | Guarantees `0.00%` probability of rapid account ruin (`کال مارجین`) even under a 50/50 random walk (`32-trade` RNG proof), enforces mandatory End-of-Day flat book (`حد ضرر زمانی`), and bounds dollar risk within the operator's **Psychological Tolerance Ceiling (`سطح تحمل روانی`)**. |
| **Layer 1: Temporal Filter ("WHEN?" / `کِی؟`)** | **Time Analysis Strategy (`Session Windows Pro` v3.0 & `Session Clock Pro` v1.0)** | `VIDEO_01` (`YKKdoH6QoG8`) | Divides the `GMT+3` day into **11 graded Time Windows (`A, B, C`)** and **9 Master Time Points (`03:00, 04:00, 08:00, 09:00, 10:00, 16:30, 18:00, 20:00, 23:00`)**; restricts `US30` to `16:30–23:00` (3 acts); prioritizes `10:00–13:00` and `15:30–18:00` on `XAUUSD`; blocks new entries $\le 5$ minutes before a Time Point. |
| **Layer 2: Spatial Memory Filter ("WHERE?" / `کجا؟`)** | **Horizontal Memory Levels (`Weekly Map`, `PDH/PDL`, `US30 Session HL`, `Round Levels`)** | `VIDEO_01` (`00:12:27–00:14:42`)<br>`VIDEO_04` (`01:06:58`) | Computes **13 Weekly Map levels** (`Low..High`, `±1.25x..±2.0x`) + **Weekend Gap**, `PDH/PDL/Mid/Open/Close` (`16:30–23:00` NY Session HL for `US30`), and `0.5%` auto-step **Round Levels**. Identifies high-priority confluence zones and `2.0x` Exhaustion reversal zones. |
| **Layer 3: Structural Price-Action Trigger ("HOW?" / `چطور؟`)** | **The Spike Strategy Triangle: `SP2L` (Amateur) + `PRO BTB` (Pro) + `MicroMap` (Legend)** | `VIDEO_04` (`7HEC5mO3d3U`)<br>`VIDEO_03` (`NDk94Ob8sEo`)<br>`VIDEO_02` (`Dw4DhxHqKLE`) | Reads price **Candle-by-Candle (`کندل‌شماری`)** inside Market Cycles (`Spike -> Channel -> Trading Range`):
- **`SP2L`**: Hunts Leg 2 on first pullback ($L_t < L_{t-1}$) of a valid `P-Gap` Spike (`1:1–1:2` R/R + `50%` scale-in).
- **`PRO BTB`**: Enters on the retest of the Breakout Candle Close (`Breakeven`) or Broken Level via **6 modes** (`>= 1:2` R/R).
- **`MicroMap`**: Trails stop-entry down the counter-trend micro-channel (`Entry 1/2/3`, `Inside Bar`, `Opt 1 H2`, `Opt 2 H3`) with single-candle SL (`1:7–1:10+` R/R) and a hard **3-Strike Invalidation Lock**. |
| **Layer 4: Execution & Active Management Layer** | **`Map Manager` EA (v2.0.1), `Half-Close` Insurance (`2R/3R`), & `180s` Hold Guard** | `VIDEO_03` (`00:02:56–00:07:19`)<br>`VIDEO_02` (`00:49:08`, `00:59:25`)<br>`VIDEO_01` (`00:24:58`) | Automates lot sizing, enforces the `10%` total risk ceiling, executes **`Half Close` at `2R/3R`** (issuing self-insurance so worst-case outcome is `+0.5R` to `+1.0R`), enforces the **2–4 minute (`180s`) minimum hold duration** to prevent broker latency-arbitrage flags, and closes `90%` ahead of PMI/macro news or opposing target-zone Pin Bars. |

---

## 2. Cross-Video Synthesis: Shared Concepts, Complementary Techniques & Apparent Contradictions Resolved

### 2.1 Shared & Repeated Core Principles Across All 6 Videos
1. **Spikes Are the Origin (`مبدأ همیشه اسپایک‌هاست`)**: Emphasized in Video 05 (`00:06:26`), Video 04 (`SP2L`), Video 03 (`PRO BTB`), and Video 02 (`00:17:31`: every Channel and Trading Range contains internal Spikes).
2. **Candle-by-Candle Reading vs. Wave Reading (`کندل به کندل نه موج به موج`)**: Introduced as the "ultimate secret sauce" (`فوت کوزه‌گری`) in Video 04 (`01:08:05`) and operationalized in Video 02 (`00:26:11`: reading `1-2-3` Falling Wedges at the individual candle level rather than macro waves).
3. **Strict Stop-Loss Immutability & Temporal Stop-Loss**: Demonstrated in Video 06 (32 random trades cannot blow up an account if SL/TP are obeyed), Video 05 (`00:37:20`: Temporal Stop-Loss at NY Close), Video 04 (`01:07:23`: widening SL turns a `-2%` stop into a `-20%` disaster), and Video 01 (`00:05:16`: `90%` of margin calls occur when a Day Trader removes SL and drifts into Multi-Day Trading to "buy hope").
4. **Philanthropic Profit Sharing (`برکت حساب`)**: Observed across Video 05 (`$299` symbolic withdrawal), Video 02 (`$2,530` / `300M Tomans` donated to EB patients, prisoners release, Sistan school, and a cancer patient), and Video 01 (`50%` EB patients / `50%` prisoners release).

### 2.2 Complementary Nested Composition (`مثلث استراتژی‌های اسپایک + زمان`)
Instead of treating `SP2L`, `PRO BTB`, `MicroMap`, and `Time Strategy` as four isolated strategies, Video 02 (`00:29:04–00:30:35`) and Video 01 (`00:00:40`) demonstrate **Nested Multi-Strategy Composition**:
- **Macro Context (`Time + Level`)**: Wait for an active **Grade-A Time Window** (e.g., `16:30–18:00` GMT+3) when price interacts with a key **Weekly Map** (`2.0x` or `50%`) or **Daily/Session High-Low** level.
- **Setup Zone (`SP2L` or `PRO BTB`)**: Wait for a valid Spike with `P-Gap` (`SP2L` pullback zone) or a structural Breakout returning to `Back to Breakeven` (`PRO BTB` zone).
- **Precision Trigger (`MicroMap`)**: Instead of entering blindly with a wide `SP2L` stop loss behind the spike origin, drop into **`MicroMap` (`Entry 2`, `Entry 3`, or `Opt 1 H2 Confirmation`)** *inside* the `SP2L`/`PRO BTB` zone! This compresses the Stop-Loss down to a single micro-candle (plus Doji spread buffer), transforming a standard `1:2` `SP2L` setup into a **`1:7` to `1:12` high-asymmetry trade**!

### 2.3 Apparent Contradictions Identified & Formally Reconciled (Phase 6 Mandate)

| Apparent Conflict Across Videos | Source A Claim | Source B Claim | Formal Technical Resolution (Regime-Conditional Synthesis) |
| :--- | :--- | :--- | :--- |
| **Conflict 1: Optimal Risk-to-Reward Target (`1:1 / 1:2` vs. `1:7 / 1:10+`)** | **Video 05 (`00:49:55–00:54:09`) & Video 04**: Critiques `1:10` / `1:20` R/R marketing hype; demonstrates that failing to exit at `1:1` R/R (`TP1`) during the Oceania session turned two winning trades into `-1R` stop-outs. | **Video 02 (`00:00:15`, `00:23:36`, `01:02:12`)**: Explicitly teaches `MicroMap` to capture **`1:7` to `1:10` (`and 12R–800R`)** reward-to-risk ratios! | **Resolved via Time-Window Liquidity & Stop-Width Geometry**:
1. In **off-peak/low-liquidity windows** (e.g., Oceania/Tokyo in Video 05 where `Spread/Range` is high) or when using wide `SP2L` origin stops, **`1:1` to `1:2` R/R** is mandatory (bank `50%` at `1R`).
2. In **Grade-A/B expansion windows** (London/NY in Video 02) when using **single-candle `MicroMap` stops** nested inside an `M5`/`M15` `SP2L`/`PRO BTB` leg, the *exact same price displacement* that equals `1R–2R` on `SP2L` mathematically equals **`7R–10R` on `MicroMap`** (`Video 02 00:48:43–00:48:58`)! Furthermore, executing `Half Close` at `2R/3R` (`Video 01`) bridges both regimes safely. |
| **Conflict 2: Using `Risk Free` (Moving SL to Breakeven) vs. Not Using `Risk Free`** | **Video 03 (`00:04:25`) & Video 05 (`00:57:30`)**: Uses `Map Manager`'s `Risk Free` button to move SL to `Entry + Spread` once in profit. | **Video 06 (`00:28:42`) & Video 02 (`00:39:03`)**: States *"I don't use Risk Free much because it ruins system efficiency (`راندمان کار رو می‌ریزه به هم`); I use `Half Close` instead."* | **Resolved via Milestone Sequencing**:
- Moving SL to `Risk Free` **prematurely** (before `TP1` / `2R` is reached) destroys expectancy because normal `PRO BTB` retests wick out the breakeven stop before running.
- **Correct Protocol**: First execute **`Half Close` at `2R` or `3R`** while keeping the original structural SL intact (`Video 01 & 02`). Only move the remaining runner's SL to `Risk Free` (`Entry + Spread`) *after* `Position 1` / `TP1` (`4R` in Video 06 `00:32:09`, or `1R` in dead Oceania session in Video 05 `00:57:30`) has already been banked! |
| **Conflict 3: Single-Trade Risk `0.5%–1%` vs. Multi-Position Cumulative Risk `5%–10%`** | **Video 03 (`01:18:50`) & Video 05 (`01:01:31`)**: Recommends `0.5%–1.0%` Set-and-Forget risk per trade (and caps total risk on the `$100K` account at `1.3%`). | **Video 02 (`00:13:00` & `00:55:55`)**: Risks `5%` cumulative across 4 scaled positions in Trade Session 1 (`+20%` gain) and scales up toward `6%–8%` (out of banked profit) in Trade Session 3. | **Resolved via Trader Tier & Banked-Profit Buffer**:
- **Standard / Amateur / Pro Baseline**: `0.5% to 1.0%` risk per trade (`2%` max single trade).
- **Legend-Tier Multi-Entry Scaling (`Video 02`)**: Only permitted when (a) dollar risk is well below the trader's verified `Psychological Tolerance Ceiling`, (b) total open + pending risk is strictly capped at `<= 10.0%` by `Map Manager`, and (c) risk above `2%` is financed out of **already banked session profits** (`$1,300` banked profit financing `$600` risk, `Video 02 00:55:55`). |
