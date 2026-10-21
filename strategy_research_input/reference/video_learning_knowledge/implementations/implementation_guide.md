# Step-by-Step Implementation Guide for Codex Astra (`implementation_guide.md`)

This implementation guide translates all educational concepts across Videos 01–06 into **explicit, deterministic, machine-actionable implementation modules** for OpenAI Codex powered by Astra, following the mandatory Phase 8 schema (`Objective`, `Source References`, `Prerequisites`, `Architecture`, `Step-by-Step Implementation`, `Code or Commands`, `Configuration`, `Validation Procedure`, `Expected Behavior`, `Failure Handling`, `Completion Criteria`).

---

## Module `IMPL_01`: Horizontal Memory Level Engine (`Weekly Map`, `PDH/PDL`, `Session HL`, `Round Levels`)

- **Objective**: Deterministically compute all objective horizontal support/resistance levels ("Memory of the Market") prior to each trading session.
- **Source References**: `VIDEO_01:00:12:27–00:14:42`, `VIDEO_01:01:34:41–01:35:57`, `VIDEO_04:01:06:58`, [poursamadi.com/weekly-map-indicator/](https://poursamadi.com/weekly-map-indicator/), [poursamadi.com/previous-day/](https://poursamadi.com/previous-day/), [poursamadi.com/previous-day-session-indicator/](https://poursamadi.com/previous-day-session-indicator/), [poursamadi.com/en/round-levels-indicator/](https://poursamadi.com/en/round-levels-indicator/).
- **Prerequisites**: Historical Weekly (`W1`), Daily (`D1`), and `M15` OHLC data feeds synchronized to Broker Server Time (`GMT+3`).
- **Architecture**: Stateless level generator executed at weekly rollover (`Sunday/Monday 00:00`) and daily rollover (`00:00` and `23:00` GMT+3).
- **Step-by-Step Implementation**:
  1. Fetch previous completed week's High ($H_{w-1}$), Low ($L_{w-1}$), Close ($C_{w-1}$), and current week's Open ($O_w$).
  2. Compute Weekly Range $\Delta_w = H_{w-1} - L_{w-1}$ and quarter-step $q = 0.25 \Delta_w$.
  3. Generate the **13 Weekly Map Levels**:
     - Internal: `Low` ($L_{w-1}$), `25%` ($L_{w-1}+q$), `50% Mid` ($L_{w-1}+2q$), `75%` ($L_{w-1}+3q$), `High` ($H_{w-1}$).
     - Upper Extensions: `1.25x` ($H_{w-1}+q$), `1.5x` ($H_{w-1}+2q$), `1.75x` ($H_{w-1}+3q$), `2.0x` ($H_{w-1}+4q$).
     - Lower Extensions: `-1.25x` ($L_{w-1}-q$), `-1.5x` ($L_{w-1}-2q$), `-1.75x` ($L_{w-1}-3q$), `-2.0x` ($L_{w-1}-4q$).
  4. If $|O_w - C_{w-1}| / 	ext{Point} \ge 5$, emit two **Weekend Gap** lines (`C_{w-1}` and `O_w`).
  5. For `XAUUSD` and `EURUSD`, compute full-day `PDH`, `PDL`, `Mid = 0.5*(PDH+PDL)`, `Open`, and `Close` from yesterday's `D1` bar.
  6. For `US30` (Dow Jones), scan yesterday's `M15` bars strictly within **`16:30–23:00` GMT+3** (`Previous Day Session High Low`) to extract `NY_High`, `NY_Low`, `NY_Mid`, `NY_Open`, and `NY_Close`.
  7. Generate **Round Levels** around current price $P$ using auto-step $\Delta_{	ext{round}} = 	ext{RoundTo}_{\{1, 2, 2.5, 5\}	imes 10^k}(0.005 \cdot P)$, capped at `300` lines.
- **Code or Commands**: Execute `WeeklyMapIndicator`, `PreviousDaySessionLevels`, and `RoundLevelsIndicator` in `extracted_code.md`.
- **Configuration**: `weekly_map_min_gap_points = 5`, `us30_session_window = "16:30-23:00"`, `us30_scan_tf = "M15"`, `round_level_auto_pct = 0.5`, `max_round_lines = 300`.
- **Validation Procedure**: Input $H_{w-1}=2640, L_{w-1}=2600$ and assert `1.25x == 2650.0`, `2.0x == 2680.0`, `50%_Mid == 2620.0`, `-2.0x == 2560.0`. Input $P=4000$ on Gold and assert $\Delta_{	ext{round}} = 20.0$; input $P=46000$ on `US30` and assert $\Delta_{	ext{round}} = 250.0$.
- **Expected Behavior**: Returns a unified dictionary of active horizontal levels for any timestamp and symbol.
- **Failure Handling**:
  - If Monday `D1` data includes a short Sunday bar (`candlestick count == 6 per week`), skip Sunday and read Friday's `D1` bar for Monday's `PDH/PDL`.
  - Never use `H1` bars to scan a `16:30` session start (`16:30` falls mid-bar on `H1`); enforce `scan_tf in {"M1", "M5", "M15", "M30"}`.
- **Completion Criteria**: 100% unit-test pass on level coordinates across `XAUUSD`, `US30`, and `EURUSD`.

---

## Module `IMPL_02`: Temporal Filter & Session Clock Engine (`Time Strategy`)

- **Objective**: Filter candidate trade setups by the 11 graded Time Windows (`A, B, C`), enforce the 9 Master Time Points (`GMT+3`), and trigger pre-Time-Point / EOD position management.
- **Source References**: `VIDEO_01:00:14:42–01:17:35`, `VIDEO_05:00:37:15–00:40:15`, [poursamadi.com/time-analysis-strategy/](https://poursamadi.com/time-analysis-strategy/), [poursamadi.com/session-windows-pro-indicator/](https://poursamadi.com/session-windows-pro-indicator/).
- **Prerequisites**: Broker Server Time offset (`winter UTC` + `clock change` rule `USA | Europe | No clock change`).
- **Architecture**: Real-time 1-second clock evaluator (`TimeStrategyEngine`).
- **Step-by-Step Implementation**:
  1. Normalize incoming broker timestamp to `GMT+3` equivalent (`Shift_Minutes`).
  2. Lookup active window from the 11-window table (for `XAUUSD`/`EURUSD`) or the 3-act NY table (`16:30–18:00`, `18:00–21:00`, `21:00–23:00` for `US30`).
  3. Compute `minutes_to_next_tp` against the 9 Master Time Points (`03:00, 04:00, 08:00, 09:00, 10:00, 16:30, 18:00, 20:00, 23:00`).
  4. If `minutes_to_next_tp <= 5`: set `pre_timepoint_warning = True`, block new trade entries, and trigger pre-window-transition evaluation (`Half Close` or tightening on open trades).
  5. If `current_time >= EOD_Cutoff` (`22:58` for `US30`, `23:55` for `XAUUSD`/`FX` on Day Trader profile): trigger mandatory **Temporal Stop-Loss (`Full Close`)**.
- **Code or Commands**: See `TimeStrategyEngine` in `extracted_code.md`.
- **Configuration**: `reference_tz = "GMT+3"`, `warning_buffer_min = 5`, `us30_eod = "22:58"`, `fx_gold_eod = "23:55"`.
- **Validation Procedure**: Test timestamps across all 24 hours; verify `16:30` matches NYSE cash open (`17:00` Iran DST / `18:00` Iran standard time).
- **Expected Behavior**: Accurately grades every minute of the 24h cycle (`A`, `B`, `C`, or `NONE`) and blocks late-window FOMO entries.
- **Failure Handling**: If broker server connection is lost or unverified at weekend open, display `!` fallback warning and block automated order dispatch until first live tick arrives (`status -> i`).
- **Completion Criteria**: Verified alignment of all 11 windows, 9 Time Points, and DST transition rules.

---

## Module `IMPL_03`: Unified Spike-Cycle Trigger Engine (`SP2L` + `PRO BTB` + `MicroMap`)

- **Objective**: Implement the complete 3-tier Spike Cycle entry state machine (`SP2L`, `PRO BTB`, and `MicroMap`) with nested composition (`MicroMap` inside `SP2L`/`PRO BTB`).
- **Source References**: `VIDEO_04:00:06:38–01:08:25`, `VIDEO_03:00:07:20–01:18:24`, `VIDEO_02:00:16:55–01:05:37`, [poursamadi.com/sp2l-strategy/](https://poursamadi.com/sp2l-strategy/), [poursamadi.com/pro-btb-strategy/](https://poursamadi.com/pro-btb-strategy/), [poursamadi.com/micromap/](https://poursamadi.com/micromap/).
- **Prerequisites**: Modules `IMPL_01` and `IMPL_02` active; bar-by-bar OHLC stream on `M1`, `M5`, `M15`, or `M30`.
- **Architecture**: Hierarchical Finite State Machine (`SP2LStrategyEngine`, `ProBTBStrategyEngine`, `MicroMapStateMachine`).
- **Step-by-Step Implementation**:
  1. **Spike & `P-Gap` Detection**: Scan for a momentum impulse of $\ge 3$ bars where $L_{i+1} > H_{i-1}$ (bullish) or $H_{i+1} < L_{i-1}$ (bearish). Reject any impulse lacking a `P-Gap`.
  2. **Tier 1 — `SP2L` Execution**:
     - On first bar $t$ where $L_t < L_{t-1}$ (bullish) or $H_t > H_{t-1}$ (bearish), arm primary entry in Spike direction, `SL` behind Spike origin candle $k_0$, `TP = 1:1` (or `1:2`), and optional `50%` scale-in limit at $0.5 	imes (P_{	ext{entry}} + P_{	ext{SL}})$.
  3. **Tier 2 — `PRO BTB` Execution**:
     - When a valid Breakout closes beyond a structural level, record `P_BE = breakout_candle.close`, `P_Level = broken_level`, and `P_Extreme = breakout_candle.high/low`.
     - Upon pullback to `P_BE` or `P_Level`, execute the configured mode (`Modes 1..6`) with the configured SL anchor (`Breakout Candle Extreme`, `Broken Level Buffer`, or `Pullback Pivot`) and `TP >= 2.0R`.
  4. **Tier 3 — `MicroMap` Execution**:
     - Inside the Spike pullback (or nested inside an `SP2L`/`PRO BTB` zone), detect counter-trend micro-channel bars (`H[t] < H[t-1]` in bullish spike) or a single `Inside Bar` (`H[t] < H[t-1] and L[t] >= L[t-1]`).
     - Trail `Buy Stop` / `Sell Stop` onto `H1` (Entry 1), `H2` after 1st SL (Entry 2), or `H3` after 2nd SL (Entry 3), or use `Opt 1 (H2 Confirmation)` / `Opt 2 (H3 Confirmation on Candle #4)`.
     - Buffer `SL` behind prior candle close/low + `1.5 * Spread` whenever trigger bar is a Doji.
     - Enforce **Hard 3-Strike Lock**: if `consecutive_stops == 3`, permanently invalidate the setup.
- **Code or Commands**: See `SP2LStrategyEngine`, `ProBTBStrategyEngine`, and `MicroMapStateMachine` in `extracted_code.md`.
- **Configuration**: Selectable tier (`SP2L`, `PRO_BTB`, `MICROMAP`, or `NESTED_ALL_THREE`).
- **Validation Procedure**: Replay historical setups from Videos 01, 02, 03, and 04; verify exact entry, SL, TP, and 3-strike lock behavior.
- **Expected Behavior**: Generates deterministic order specifications with full traceability to the triggering bar and strategy variant.
- **Failure Handling**: Abort continuation triggers immediately when price reaches the opposing Trading Range ceiling/floor (`Video 01 01:35:13`) or prints an `Exhaustion Gap` into `Weekly Map 2.0x`.
- **Completion Criteria**: All 20+ strategy variants (`SP2L` + `50% scale-in`, `6 PRO BTB modes`, `6 MicroMap modes`) verified in automated unit tests.

---

## Module `IMPL_04`: Risk Sizing, `Half-Close` Insurance & Microstructure Guard (`Map Manager Core`)

- **Objective**: Enforce exact percentage risk sizing (`0.5%–2.0%`), the `10.0%` cumulative open+pending risk ceiling, the `Half-Close` Insurance protocol (`50%` at `2R/3R`), `Risk Free` with spread offset, and the `180-second` broker anti-arbitrage hold-time floor.
- **Source References**: `VIDEO_03:00:02:56–00:07:19`, `VIDEO_02:00:49:08–00:59:51`, `VIDEO_01:00:24:58–01:04:32`, `VIDEO_05:00:57:19–01:01:45`, `VIDEO_06:00:09:50–00:33:05`.
- **Prerequisites**: Broker contract specification (`TickSize`, `TickValue`, `MinLot`, `LotStep`, `Spread`).
- **Architecture**: Pre-trade and post-trade risk gatekeeper (`MapManagerEA` / `ExecutionGuards`).
- **Step-by-Step Implementation**:
  1. Compute `Lots = NormalizeLot((Balance * RiskPct / 100) / ((|Entry - SL| / TickSize) * TickValue))`.
  2. Check `GetTotalAccountRiskPct() + RiskPct <= 10.0%` and `DollarRisk <= TraderComfortCeilingUSD`. If violated, reject order.
  3. While trade is open, block non-emergency profit closes while `elapsed_time < 180 seconds` (`3 minutes`) to prevent broker latency-arbitrage flags.
  4. When floating profit reaches `3.0R` (or `2.0R` conservative / `1.0R` Oceania session), execute **`Half Close` (`50%` volume closed)** to lock in guaranteed net positive equity (`+1.0R` worst-case at `3R` half-close) while keeping original SL intact.
  5. One minute before high-impact macro news (`PMI` / `NFP` / `FOMC`) or upon an opposing **Pin Bar** forming at the target zone (`NY Close` / `Range Floor`), close `90%` of total volume and leave a `10%` runner with positive open equity (`تراز باز مثبت`).
  6. Never widen `SL` (`Allow_SL_Widening = False`).
- **Code or Commands**: See `Poursamadi_MapManager.mq5` and `ExecutionGuards` in `extracted_code.md`.
- **Configuration**: `Default_Risk_Pct = 1.0`, `Max_Total_Risk_Pct = 10.0`, `Min_Hold_Seconds = 180`, `Half_Close_RR = 3.0`.
- **Validation Procedure**: Run unit tests verifying lot calculation, 10% cap rejection, 180s hold guard, and `Half Close` worst-case payoff math.
- **Expected Behavior**: Zero risk of margin call, zero broker arbitrage flags, and guaranteed positive net return on every trade reaching `2R/3R`.
- **Failure Handling**: If `Lots < MinLot` (`0.01`), abort order and alert user of insufficient account balance for the requested risk/SL distance.
- **Completion Criteria**: 100% pass rate on all risk-guard assertions.
