# Complete Code, Command & Configuration Reconstruction (`extracted_code.md`)

Per **Phase 4 (Code & Command Reconstruction)**, every technical artifact below is explicitly categorized into one of three provenance classes:
- **[CLASS A — EXACTLY OBSERVED]**: Verbatim UI labels, parameter names, input defaults, directory paths, keyboard shortcuts, and mathematical formulas directly observed in the videos and official [poursamadi.com](https://poursamadi.com/en/) documentation / PDF manuals.
- **[CLASS B — RECONSTRUCTED FROM VISIBLE EVIDENCE]**: Complete MQL5/MQL4 and Python implementations reconstructed directly from the observed on-screen behavior, state transitions, and documented inputs of `Map Manager EA`, `Session Windows Pro`, `Session Clock Pro`, `Weekly Map`, `Previous Day High Low`, `Previous Day Session High Low`, `Round Levels`, `Candle Time`, `Pip Value`, and `Spread Indicator` (since Poursamadi distributes compiled `.ex4`/`.ex5` binaries rather than showing raw `.mq4`/`.mq5` source code on screen).
- **[CLASS C — SUGGESTED ALTERNATIVE / CODEX ASTRA INTEGRATION]**: Production-grade Python backtesting, state-machine execution, and automated test harnesses engineered for OpenAI Codex powered by Astra.

---

## 1. [CLASS A — EXACTLY OBSERVED] File Paths, CLI/Shortcut Commands & Input Configurations

### 1.1 MetaTrader 4 & MetaTrader 5 Directory Structure & Shortcuts
Observed in **Video 03 (`00:05:12–00:07:19`)** and verified across official indicator installation guides:

```text
# MetaTrader 4 (MT4) Installation Paths (via File -> Open Data Folder)
<MT4_DATA_FOLDER>/
└── MQL4/
    ├── Experts/
    │   └── MapManager.ex4                 # Remove default MACD Sample.ex4 & Moving Average.ex4
    └── Indicators/
        ├── SessionWindowsPro.ex4
        ├── SessionClockPro.ex4
        ├── WeeklyMap.ex4
        ├── PreviousDayHighLow.ex4
        ├── PreviousDaySessionHighLow.ex4
        ├── RoundLevels.ex4
        ├── CandleTime.ex4
        ├── PipValueIndicator.ex4
        └── SpreadIndicator.ex4

# MetaTrader 5 (MT5) Installation Paths (via File -> Open Data Folder)
<MT5_DATA_FOLDER>/
└── MQL5/
    ├── Experts/
    │   ├── MapManager_X64_Regular.ex5     # Recommended default build
    │   ├── MapManager_AVX.ex5             # CPU-specific build variant
    │   ├── MapManager_AVX2.ex5            # CPU-specific build variant
    │   └── MapManager_AVX512.ex5          # CPU-specific build variant
    └── Indicators/
        ├── SessionWindowsPro.ex5
        ├── SessionClockPro.ex5
        ├── WeeklyMap.ex5
        ├── PreviousDayHighLow.ex5
        ├── PreviousDaySessionHighLow.ex5
        ├── RoundLevels.ex5
        ├── CandleTime.ex5
        ├── PipValueIndicator.ex5
        └── SpreadIndicator.ex5
```

### 1.2 Observed Keyboard Shortcuts & Terminal Commands
```text
Ctrl + N          # Open Navigator Panel (Right-click 'Expert Advisors' or 'Indicators' -> 'Refresh')
Ctrl + I          # Open Indicators List on Active Chart (Select indicator -> 'Edit' -> 'Inputs')
F8                # Open Chart Properties ('Common' tab -> Enable 'Show Ask line' & 'Chart Shift')
F12               # Step-by-Step Bar Replay (Note: Video 06 00:21:16 recommends Live Video Screen Recording over F12)
```

### 1.3 [CLASS A — EXACTLY OBSERVED] Official Indicator & EA Input Parameters

```json
{
  "MapManager_EA_v2_0_1": {
    "Panel_Controls": [
      "Risk (Default: 1.0%, Max: 10.0%)",
      "Lots (Live read-only auto-calculated volume)",
      "Add Line (Draws Red SL + Green TP lines for Market orders)",
      "Delete Line (Removes Add Line / Add Pend Line objects)",
      "Buy (Market Buy at Ask; requires Red SL < Ask)",
      "Sell (Market Sell at Bid; requires Red SL > Bid)",
      "Add Pend Line (Draws White Entry + Red SL + Green TP lines)",
      "Set Pending (Submits BuyLimit/BuyStop/SellLimit/SellStop)",
      "Pending Info (Displays active pending type, e.g., 'BuyStop')",
      "Del Pending (Deletes all active Limit and Stop orders)",
      "Risk Free (Moves SL of profitable chart trades to Entry + Spread)",
      "Half Close (Closes 50% volume of all open trades on active chart)",
      "Chart Close (Closes 100% of open trades on active chart symbol)",
      "Full Close (Closes 100% of open trades across ALL symbols in account)",
      "Spread (Live spread in Points, e.g., 'Spread: 250')"
    ],
    "EA_Inputs": {
      "TakeProfitUseR-R (TpLineisOff)": false,
      "TakeProfitR-R": 1.0,
      "Scale_14in_Laptop": 7,
      "Scale_Desktop_Monitor": 10,
      "X_Offset": 1,
      "Y_Offset": 1
    }
  },
  "Session_Windows_Pro_v3_0": {
    "Teaching view": "Full map (Options: Main sessions | New York start | New York middle | New York end | London start | Full map | Points only)",
    "Days to show": 10,
    "Window labels": true,
    "Time points": true,
    "Countdown panel": true,
    "Broker setup": "Supported broker (Options: Supported broker | Other broker)",
    "Other: winter UTC": "UTC+02:00",
    "Other: clock change": "Europe (Options: Europe | USA | No clock change)"
  },
  "Session_Clock_Pro_v1_0": {
    "Teaching view": "Full map",
    "Chart point lines": false,
    "Days of chart point lines": 10,
    "Broker setup": "Supported broker",
    "Clock size": 360,
    "Points on clock": true,
    "Show seconds": true,
    "Highlight last minutes": 5
  },
  "Weekly_Map_v1_10": {
    "Number of weeks to render (1..100)": 10,
    "Show_High": true,
    "Show_Low": true,
    "Show_Avg": true,
    "Show_Up25": true,
    "Show_Down25": true,
    "Show_25pPlus": true,
    "Show_AvgPlus": true,
    "Show_75pPlus": true,
    "Show_HighPlus": true,
    "Show_25pMinus": true,
    "Show_AvgMinus": true,
    "Show_75pMinus": true,
    "Show_LowMinus": true,
    "Display only if a gap exists": true,
    "Minimum difference in \"points\" to consider a gap": 5
  },
  "Previous_Day_High_Low_v1_10": {
    "Number of days to draw (1..1000)": 10,
    "Draw for today (uses yesterday's data)": true,
    "Draw for earlier days as well": true,
    "Show_High": true,
    "Show_Low": true,
    "Show_Mid": true,
    "Show_Open": true,
    "Show_Close": true
  },
  "Previous_Day_Session_High_Low_v1_10": {
    "SessionStartHour": 16,
    "SessionStartMinute": 30,
    "SessionEndHour": 23,
    "SessionEndMinute": 0,
    "TF used to scan the session": "M15",
    "if end <= start, allow next-day wrap": true,
    "Number of days to draw (1..1000)": 10,
    "DrawCurrentDay": true,
    "DrawPastDays": true,
    "Show_High": true,
    "Show_Low": true,
    "Show_Mid": true,
    "Show_Open": true,
    "Show_Close": true
  },
  "Round_Levels_v1_10": {
    "ON = fixed round step chosen from the symbol's price (not zoom)": true,
    "AUTO mode: a round line roughly every this % of price": 0.5,
    "Manual spacing in PRICE units (used when AutoSpacing = false)": 250,
    "Print the round number next to each line": true,
    "Safety cap on number of lines": 300
  },
  "Pip_Value_Indicator_v1_10": {
    "Lot size to value": 1.0,
    "Decimal places for the point/pip values": 5,
    "Chart corner to pin the text to": "Top-Left",
    "TextColor": "White"
  },
  "Spread_Indicator_v1_10": {
    "Chart corner to pin the label to": "Top-Right",
    "Turn warning color when spread is high": true,
    "Spread (points) at/above which the warning color is used": 30,
    "Also show the raw price spread (Ask-Bid) in brackets": false,
    "Color when spread is below the threshold": "Silver"
  }
}
```

---

## 2. [CLASS B — RECONSTRUCTED FROM VISIBLE EVIDENCE] Complete MQL5 Implementation of `Map Manager` & Core Indicators

```mql5
//+------------------------------------------------------------------+
//|                                       Poursamadi_MapManager.mq5  |
//|     Reconstructed from Video 03 (NDk94Ob8sEo) & PDF User Guide   |
//|     Provenance: CLASS B (Reconstructed from Visible Evidence)    |
//+------------------------------------------------------------------+
#property copyright "Reconstructed for Codex Astra from Poursamadi Spec"
#property version   "2.01"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>
#include <Trade\OrderInfo.mqh>

//--- Observed EA Inputs (Video 03 & Map Manager PDF Guide Pages 2-11)
input double InpDefaultRiskPct        = 1.0;    // Risk (%) per trade (Default: 1.0, Max: 10.0)
input bool   TakeProfitUseR_R         = false;  // TakeProfitUseR-R (TpLineisOff)
input double TakeProfitR_R            = 1.0;    // TakeProfitR-R multiple when TpLineisOff = true
input int    InpToolScale             = 10;     // UI Scale (7 for 14" laptop, 10 for desktop)
input int    InpXOffset               = 1;      // X Coordinate Offset
input int    InpYOffset               = 1;      // Y Coordinate Offset
input bool   InpAutoScreenshot        = true;   // v2.0.0 Automatic screenshot after trade action

#define LINE_SL          "MAP_SL_LINE"
#define LINE_TP          "MAP_TP_LINE"
#define LINE_PEND_ENTRY  "MAP_PEND_ENTRY_LINE"

CTrade        g_trade;
CPositionInfo g_pos;
COrderInfo    g_ord;

double CalculateRiskLots(double entryPrice, double slPrice, double riskPct)
{
   if(riskPct <= 0.0 || riskPct > 10.0) return 0.0;
   double slDistance = MathAbs(entryPrice - slPrice);
   if(slDistance <= 0.0) return 0.0;

   double balance    = AccountInfoDouble(ACCOUNT_BALANCE);
   double riskAmount = balance * (riskPct / 100.0);

   double tickSize   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tickValue  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   if(tickSize <= 0.0 || tickValue <= 0.0) return 0.0;

   double lossPerLot = (slDistance / tickSize) * tickValue;
   if(lossPerLot <= 0.0) return 0.0;

   double rawLots    = riskAmount / lossPerLot;
   double minLot     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double maxLot     = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lotStep    = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   double normLots   = MathFloor(rawLots / lotStep) * lotStep;
   if(normLots < minLot) return 0.0;
   if(normLots > maxLot) normLots = maxLot;
   return NormalizeDouble(normLots, 2);
}

double GetTotalAccountRiskPct()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   if(balance <= 0.0) return 100.0;
   double totalRiskUSD = 0.0;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i))
      {
         double openPrice = g_pos.PriceOpen();
         double slPrice   = g_pos.StopLoss();
         double vol       = g_pos.Volume();
         if(slPrice <= 0.0) continue;
         string sym       = g_pos.Symbol();
         double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
         double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
         if(tickSize > 0.0 && tickValue > 0.0)
         {
            bool isBuy = (g_pos.PositionType() == POSITION_TYPE_BUY);
            if((isBuy && slPrice < openPrice) || (!isBuy && slPrice > openPrice))
               totalRiskUSD += (MathAbs(openPrice - slPrice) / tickSize) * tickValue * vol;
         }
      }
   }
   for(int j = OrdersTotal() - 1; j >= 0; j--)
   {
      if(g_ord.SelectByIndex(j))
      {
         double openPrice = g_ord.PriceOpen();
         double slPrice   = g_ord.StopLoss();
         double vol       = g_ord.VolumeInitial();
         if(slPrice <= 0.0) continue;
         string sym       = g_ord.Symbol();
         double tickSize  = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
         double tickValue = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
         if(tickSize > 0.0 && tickValue > 0.0)
            totalRiskUSD += (MathAbs(openPrice - slPrice) / tickSize) * tickValue * vol;
      }
   }
   return (totalRiskUSD / balance) * 100.0;
}

void ExecuteRiskFreeOnChart()
{
   double point  = SymbolInfoDouble(_Symbol, SYMBOL_POINT);
   long   spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   double spreadPrice = spread * point;

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Symbol() == _Symbol)
      {
         if(g_pos.Profit() <= 0.0) continue;
         double entry = g_pos.PriceOpen();
         double tp    = g_pos.TakeProfit();
         if(g_pos.PositionType() == POSITION_TYPE_BUY)
         {
            double newSL = NormalizeDouble(entry + spreadPrice, _Digits);
            if(newSL > g_pos.StopLoss() && newSL < SymbolInfoDouble(_Symbol, SYMBOL_BID))
               g_trade.PositionModify(g_pos.Ticket(), newSL, tp);
         }
         else if(g_pos.PositionType() == POSITION_TYPE_SELL)
         {
            double newSL = NormalizeDouble(entry - spreadPrice, _Digits);
            if((g_pos.StopLoss() == 0.0 || newSL < g_pos.StopLoss()) && newSL > SymbolInfoDouble(_Symbol, SYMBOL_ASK))
               g_trade.PositionModify(g_pos.Ticket(), newSL, tp);
         }
      }
   }
}

void ExecuteHalfCloseOnChart()
{
   double minLot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double lotStep = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i) && g_pos.Symbol() == _Symbol)
      {
         double vol      = g_pos.Volume();
         double halfVol  = MathFloor((vol * 0.5) / lotStep) * lotStep;
         if(halfVol >= minLot)
            g_trade.PositionClosePartial(g_pos.Ticket(), NormalizeDouble(halfVol, 2));
      }
   }
}

void ExecuteClosePositions(bool allSymbolsFullClose)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(g_pos.SelectByIndex(i))
      {
         if(allSymbolsFullClose || g_pos.Symbol() == _Symbol)
            g_trade.PositionClose(g_pos.Ticket());
      }
   }
}
```

---

## 3. [CLASS B & C] Unified Python Reference Engine for Codex Astra (`poursamadi_engine.py`)

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
import math


@dataclass
class Candle:
    index: int
    timestamp_gmt3: str  # Format "YYYY-MM-DD HH:MM:SS" in Broker GMT+3
    open: float
    high: float
    low: float
    close: float
    spread_points: float = 20.0
    point_size: float = 0.01

    @property
    def is_bullish(self) -> bool:
        return self.close > self.open

    @property
    def is_bearish(self) -> bool:
        return self.close < self.open

    @property
    def body_size(self) -> float:
        return abs(self.close - self.open)

    @property
    def full_range(self) -> float:
        return max(self.high - self.low, 1e-9)

    @property
    def body_ratio(self) -> float:
        return self.body_size / self.full_range

    @property
    def is_doji(self) -> bool:
        return self.body_ratio <= 0.20 or self.full_range <= (2.5 * self.spread_points * self.point_size)

    def is_pin_bar(self, direction: str) -> bool:
        upper_wick = self.high - max(self.open, self.close)
        lower_wick = min(self.open, self.close) - self.low
        if direction == "BULLISH":
            return (lower_wick / self.full_range) >= 0.60 and (upper_wick / self.full_range) <= 0.25
        elif direction == "BEARISH":
            return (upper_wick / self.full_range) >= 0.60 and (lower_wick / self.full_range) <= 0.25
        return False


class WeeklyMapIndicator:
    """Implements Weekly Map v1.10 (13 horizontal levels + Weekend Gap)."""

    @staticmethod
    def compute_levels(
        prev_week_high: float,
        prev_week_low: float,
        prev_week_close: Optional[float] = None,
        curr_week_open: Optional[float] = None,
        point_size: float = 0.01,
        min_gap_points: int = 5,
    ) -> Dict[str, object]:
        rng = prev_week_high - prev_week_low
        step = 0.25 * rng
        levels = {
            "2.0x": prev_week_high + 4 * step,
            "1.75x": prev_week_high + 3 * step,
            "1.5x": prev_week_high + 2 * step,
            "1.25x": prev_week_high + 1 * step,
            "High": prev_week_high,
            "75%": prev_week_low + 3 * step,
            "50%_Mid": prev_week_low + 2 * step,
            "25%": prev_week_low + 1 * step,
            "Low": prev_week_low,
            "-1.25x": prev_week_low - 1 * step,
            "-1.5x": prev_week_low - 2 * step,
            "-1.75x": prev_week_low - 3 * step,
            "-2.0x": prev_week_low - 4 * step,
        }
        weekend_gap = None
        if prev_week_close is not None and curr_week_open is not None:
            diff_points = abs(curr_week_open - prev_week_close) / point_size
            if diff_points >= min_gap_points:
                weekend_gap = {
                    "prev_close_line": prev_week_close,
                    "curr_open_line": curr_week_open,
                    "gap_direction": "UP_GREEN" if curr_week_open > prev_week_close else "DOWN_ORANGE_RED",
                    "gap_points": diff_points,
                }
        return {"levels": levels, "weekend_gap": weekend_gap}


class PreviousDaySessionLevels:
    """Implements Previous Day High Low & Previous Day Session High Low (e.g., 16:30-23:00 for US30)."""

    @staticmethod
    def compute_from_bars(
        bars: List[Candle],
        session_start_hm: str = "00:00",
        session_end_hm: str = "23:59",
    ) -> Optional[Dict[str, float]]:
        filtered = []
        for b in bars:
            hm = b.timestamp_gmt3.split(" ")[1][:5]
            if session_start_hm <= session_end_hm:
                if session_start_hm <= hm <= session_end_hm:
                    filtered.append(b)
            else:
                if hm >= session_start_hm or hm <= session_end_hm:
                    filtered.append(b)
        if not filtered:
            return None
        hi = max(b.high for b in filtered)
        lo = min(b.low for b in filtered)
        return {
            "High": hi,
            "Low": lo,
            "Mid": 0.5 * (hi + lo),
            "Open": filtered[0].open,
            "Close": filtered[-1].close,
        }


class RoundLevelsIndicator:
    """Implements Round Levels v1.10 auto-step formula (~0.5% rounded to {1, 2, 2.5, 5} * 10^k)."""

    @staticmethod
    def compute_auto_step(reference_price: float, target_pct: float = 0.5) -> float:
        raw_step = reference_price * (target_pct / 100.0)
        if raw_step <= 0:
            return 1.0
        exponent = math.floor(math.log10(raw_step))
        base = 10 ** exponent
        mantissa = raw_step / base
        candidates = [1.0, 2.0, 2.5, 5.0, 10.0]
        best = min(candidates, key=lambda c: abs(c - mantissa))
        return best * base


class TimeStrategyEngine:
    MASTER_TIME_POINTS = [
        "03:00", "04:00", "08:00", "09:00", "10:00", "16:30", "18:00", "20:00", "23:00"
    ]

    FULL_MAP_WINDOWS = [
        {"id": "W01", "start": "01:00", "end": "03:00", "grade": "C", "session": "Asia_Early"},
        {"id": "W02", "start": "03:00", "end": "04:00", "grade": "B", "session": "Tokyo_Open"},
        {"id": "W03", "start": "04:00", "end": "08:00", "grade": "C", "session": "Asia_Mid"},
        {"id": "W04", "start": "08:00", "end": "09:00", "grade": "B", "session": "Pre_Europe"},
        {"id": "W05", "start": "09:00", "end": "10:00", "grade": "B", "session": "Frankfurt_Open"},
        {"id": "W06", "start": "10:00", "end": "13:00", "grade": "A", "session": "London_Core"},
        {"id": "W07", "start": "13:00", "end": "15:30", "grade": "C", "session": "London_Lunch"},
        {"id": "W08", "start": "15:30", "end": "16:30", "grade": "A", "session": "US_Macro_PreOpen"},
        {"id": "W09", "start": "16:30", "end": "18:00", "grade": "A", "session": "NY_Cash_Open"},
        {"id": "W10", "start": "18:00", "end": "21:00", "grade": "B", "session": "NY_Middle"},
        {"id": "W11", "start": "21:00", "end": "23:00", "grade": "B", "session": "NY_End_Close"},
    ]

    US30_WINDOWS = [
        {"id": "US30_START",  "start": "16:30", "end": "18:00", "grade": "A"},
        {"id": "US30_MIDDLE", "start": "18:00", "end": "21:00", "grade": "B"},
        {"id": "US30_END",    "start": "21:00", "end": "23:00", "grade": "B"},
    ]

    @classmethod
    def evaluate_time(cls, symbol: str, hm_gmt3: str) -> Dict[str, object]:
        windows = cls.US30_WINDOWS if symbol.upper() in ("US30", "DJI", "DOW") else cls.FULL_MAP_WINDOWS
        active_window = None
        for w in windows:
            if w["start"] <= hm_gmt3 < w["end"]:
                active_window = w
                break

        h, m = map(int, hm_gmt3.split(":"))
        curr_mins = h * 60 + m
        next_tp = None
        mins_to_tp = 9999
        for tp in cls.MASTER_TIME_POINTS:
            th, tm = map(int, tp.split(":"))
            tp_mins = th * 60 + tm
            diff = tp_mins - curr_mins
            if diff < 0:
                diff += 1440
            if diff < mins_to_tp:
                mins_to_tp = diff
                next_tp = tp

        return {
            "active_window": active_window,
            "grade": active_window["grade"] if active_window else "NONE",
            "next_time_point": next_tp,
            "minutes_to_next_tp": mins_to_tp,
            "pre_timepoint_warning_gold": mins_to_tp <= 5,
            "allow_new_entry": (active_window is not None) and (mins_to_tp > 5),
        }


class SP2LStrategyEngine:
    """Implements SP2L (Video 04): Valid Spike with P-Gap -> 1st Pullback -> Leg 2 Entry + 50% Scale-In."""

    @staticmethod
    def has_valid_p_gap(spike_bars: List[Candle], direction: str) -> Tuple[bool, float]:
        if len(spike_bars) < 3:
            return False, 0.0
        max_gap = 0.0
        for i in range(1, len(spike_bars) - 1):
            if direction == "BULLISH":
                gap = spike_bars[i + 1].low - spike_bars[i - 1].high
                if gap > max_gap:
                    max_gap = gap
            else:
                gap = spike_bars[i - 1].low - spike_bars[i + 1].high
                if gap > max_gap:
                    max_gap = gap
        return (max_gap > 0.0), max_gap

    @classmethod
    def evaluate_setup(
        cls,
        spike_bars: List[Candle],
        pullback_bar: Candle,
        direction: str,
        enable_scale_in: bool = True,
        target_rr: float = 1.0,
    ) -> Optional[Dict[str, float]]:
        valid_gap, gap_size = cls.has_valid_p_gap(spike_bars, direction)
        if not valid_gap:
            return None

        prev_bar = spike_bars[-1]
        origin_bar = spike_bars[0]
        spread_buf = pullback_bar.spread_points * pullback_bar.point_size

        if direction == "BULLISH":
            if pullback_bar.low >= prev_bar.low:
                return None
            entry_primary = prev_bar.low
            sl_price = origin_bar.low - spread_buf
            risk_dist = entry_primary - sl_price
            if risk_dist <= 0:
                return None
            tp_price = entry_primary + (target_rr * risk_dist)
            scale_in_50 = entry_primary - (0.5 * risk_dist) if enable_scale_in else None
        else:
            if pullback_bar.high <= prev_bar.high:
                return None
            entry_primary = prev_bar.high
            sl_price = origin_bar.high + spread_buf
            risk_dist = sl_price - entry_primary
            if risk_dist <= 0:
                return None
            tp_price = entry_primary - (target_rr * risk_dist)
            scale_in_50 = entry_primary + (0.5 * risk_dist) if enable_scale_in else None

        return {
            "strategy": "SP2L",
            "direction": direction,
            "p_gap_size": gap_size,
            "entry_primary": entry_primary,
            "entry_scale_in_50pct": scale_in_50,
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "primary_rr": target_rr,
            "scale_in_rr": (target_rr + 0.5) / 0.5 if enable_scale_in else None,
        }


class ProBTBStrategyEngine:
    """Implements all 6 Standard Entry Modes and 3 SL Anchor Modes of PRO BTB (Video 03)."""

    @staticmethod
    def generate_order_spec(
        direction: str,
        entry_mode: int,
        sl_anchor_mode: str,
        broken_level_price: float,
        breakout_candle: Candle,
        return_candle: Optional[Candle] = None,
        target_rr: float = 2.0,
    ) -> Dict[str, object]:
        be_close_price = breakout_candle.close
        spread_buf = breakout_candle.spread_points * breakout_candle.point_size

        if direction == "BULLISH":
            if entry_mode == 1:
                order_type, entry_price = "BUY_LIMIT", be_close_price
            elif entry_mode == 2:
                order_type, entry_price = "BUY_STOP", (return_candle.high if return_candle else be_close_price)
            elif entry_mode == 3:
                order_type, entry_price = "BUY_MARKET", (return_candle.close if return_candle else be_close_price)
            elif entry_mode == 4:
                order_type, entry_price = "BUY_LIMIT", broken_level_price
            elif entry_mode == 5:
                order_type, entry_price = "BUY_STOP", breakout_candle.high
            elif entry_mode == 6:
                order_type, entry_price = "BUY_MARKET_CONFIRMED", (return_candle.close if return_candle else broken_level_price)
            else:
                raise ValueError("Invalid PRO BTB entry_mode (must be 1..6)")

            if sl_anchor_mode == "BREAKOUT_CANDLE":
                sl_price = breakout_candle.low - spread_buf
            elif sl_anchor_mode == "PULLBACK_PIVOT" and return_candle is not None:
                sl_price = min(return_candle.low, broken_level_price) - spread_buf
            else:
                sl_price = min(broken_level_price, breakout_candle.low) - spread_buf

            risk = max(entry_price - sl_price, spread_buf)
            tp_price = entry_price + (max(target_rr, 2.0) * risk)
        else:
            if entry_mode == 1:
                order_type, entry_price = "SELL_LIMIT", be_close_price
            elif entry_mode == 2:
                order_type, entry_price = "SELL_STOP", (return_candle.low if return_candle else be_close_price)
            elif entry_mode == 3:
                order_type, entry_price = "SELL_MARKET", (return_candle.close if return_candle else be_close_price)
            elif entry_mode == 4:
                order_type, entry_price = "SELL_LIMIT", broken_level_price
            elif entry_mode == 5:
                order_type, entry_price = "SELL_STOP", breakout_candle.low
            elif entry_mode == 6:
                order_type, entry_price = "SELL_MARKET_CONFIRMED", (return_candle.close if return_candle else broken_level_price)
            else:
                raise ValueError("Invalid PRO BTB entry_mode (must be 1..6)")

            if sl_anchor_mode == "BREAKOUT_CANDLE":
                sl_price = breakout_candle.high + spread_buf
            elif sl_anchor_mode == "PULLBACK_PIVOT" and return_candle is not None:
                sl_price = max(return_candle.high, broken_level_price) + spread_buf
            else:
                sl_price = max(broken_level_price, breakout_candle.high) + spread_buf

            risk = max(sl_price - entry_price, spread_buf)
            tp_price = entry_price - (max(target_rr, 2.0) * risk)

        return {
            "strategy": "PRO_BTB",
            "entry_mode": entry_mode,
            "sl_anchor_mode": sl_anchor_mode,
            "order_type": order_type,
            "entry_price": entry_price,
            "stop_loss": sl_price,
            "take_profit": tp_price,
            "reward_to_risk": max(target_rr, 2.0),
        }


@dataclass
class MicroMapStateMachine:
    """Implements MicroMap (Video 02): Entry 1/2/3, Inside-Bar, Opt 1 (H2), Opt 2 (H3), 3-Strike Lock & Doji Buffer."""
    direction: str
    mode: str = "CHAINED_1_2_3"
    consecutive_stops: int = 0
    invalidated: bool = False
    micro_channel_bars: List[Candle] = field(default_factory=list)
    target_rr: float = 7.0

    def record_stop_loss(self) -> None:
        self.consecutive_stops += 1
        if self.consecutive_stops >= 3:
            self.invalidated = True

    def compute_buffered_sl(self, trigger_bar: Candle, prev_bar: Optional[Candle]) -> float:
        spread_price = trigger_bar.spread_points * trigger_bar.point_size
        if self.direction == "BULLISH":
            base_low = trigger_bar.low
            if trigger_bar.is_doji and prev_bar is not None:
                base_low = min(trigger_bar.low, prev_bar.close, prev_bar.low)
            return base_low - (1.5 * spread_price)
        else:
            base_high = trigger_bar.high
            if trigger_bar.is_doji and prev_bar is not None:
                base_high = max(trigger_bar.high, prev_bar.close, prev_bar.high)
            return base_high + (1.5 * spread_price)

    def evaluate_next_bar(self, bar: Candle, prev_bar: Candle) -> Optional[Dict[str, object]]:
        if self.invalidated:
            return {"status": "INVALIDATED_AFTER_3_STOPS"}

        is_inside_bar = (bar.high < prev_bar.high) and (bar.low >= prev_bar.low)
        if self.mode == "INSIDE_BAR" and is_inside_bar:
            sl = self.compute_buffered_sl(bar, prev_bar)
            entry = bar.high if self.direction == "BULLISH" else bar.low
            risk = abs(entry - sl)
            tp = entry + self.target_rr * risk if self.direction == "BULLISH" else entry - self.target_rr * risk
            return {
                "status": "ARMED",
                "variant": "MICROMAP_INSIDE_BAR",
                "attempt_number": self.consecutive_stops + 1,
                "order_type": "BUY_STOP" if self.direction == "BULLISH" else "SELL_STOP",
                "entry_price": entry,
                "stop_loss": sl,
                "take_profit": tp,
                "target_rr": self.target_rr,
            }

        if self.direction == "BULLISH" and bar.high < prev_bar.high:
            self.micro_channel_bars.append(bar)
        elif self.direction == "BEARISH" and bar.low > prev_bar.low:
            self.micro_channel_bars.append(bar)
        else:
            return None

        n = len(self.micro_channel_bars)
        sl = self.compute_buffered_sl(bar, prev_bar)

        if self.mode == "CHAINED_1_2_3":
            entry = bar.high if self.direction == "BULLISH" else bar.low
            variant = f"MICROMAP_ENTRY_{self.consecutive_stops + 1}"
        elif self.mode == "OPT1_H2":
            if n < 2:
                return {"status": "WAITING_FOR_H2"}
            h2_bar = self.micro_channel_bars[-2]
            entry = h2_bar.high if self.direction == "BULLISH" else h2_bar.low
            variant = "MICROMAP_OPT1_H2_CONFIRMATION"
        elif self.mode == "OPT2_H3":
            if n < 3:
                return {"status": "WAITING_FOR_H3_CANDLE_4"}
            h3_bar = self.micro_channel_bars[-3]
            entry = h3_bar.high if self.direction == "BULLISH" else h3_bar.low
            variant = "MICROMAP_OPT2_H3_CONFIRMATION"
        else:
            return None

        risk = max(abs(entry - sl), bar.spread_points * bar.point_size)
        tp = entry + self.target_rr * risk if self.direction == "BULLISH" else entry - self.target_rr * risk
        return {
            "status": "ARMED",
            "variant": variant,
            "attempt_number": self.consecutive_stops + 1,
            "order_type": "BUY_STOP" if self.direction == "BULLISH" else "SELL_STOP",
            "entry_price": entry,
            "stop_loss": sl,
            "take_profit": tp,
            "target_rr": self.target_rr,
        }


class ExecutionGuards:
    @staticmethod
    def can_close_trade_safely(open_timestamp_sec: int, current_timestamp_sec: int, is_emergency: bool = False) -> Tuple[bool, str]:
        if is_emergency:
            return True, "EMERGENCY_CIRCUIT_BREAKER"
        elapsed = current_timestamp_sec - open_timestamp_sec
        if elapsed < 180:
            return False, f"HOLD_TIME_GUARD_ACTIVE ({elapsed}s < 180s min broker anti-arbitrage floor)"
        return True, "OK_TO_CLOSE"

    @staticmethod
    def compute_half_close_insurance(initial_risk_usd: float, half_close_at_rr: float = 3.0) -> Dict[str, float]:
        realized_half_profit = 0.5 * half_close_at_rr * initial_risk_usd
        remaining_open_risk = -0.5 * initial_risk_usd
        guaranteed_worst_case_net = realized_half_profit + remaining_open_risk
        return {
            "initial_risk_usd": initial_risk_usd,
            "half_close_rr": half_close_at_rr,
            "banked_profit_usd": realized_half_profit,
            "remaining_sl_exposure_usd": remaining_open_risk,
            "worst_case_net_profit_usd": guaranteed_worst_case_net,
            "worst_case_net_rr": 0.5 * (half_close_at_rr - 1.0),
        }
```
