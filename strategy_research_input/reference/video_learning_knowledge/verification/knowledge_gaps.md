# Transparent Documentation of Limitations, Inaccessible Segments & Knowledge Gaps (`knowledge_gaps.md`)

Per **Phase 1, Phase 10, and Phase 12 (Mandatory Transparency Directive: "Where resolution makes code or configuration unreadable, mark those details as unverified rather than guessing. Never invent material that cannot be observed")**, this file documents every technical limitation and gap encountered during acquisition.

---

## 1. Inaccessible / Missing Mid-Video Caption Segments (`Videos 01, 03, 04`)

While **Videos 02 (`Dw4DhxHqKLE`), 05 (`oAea9hZlUOQ`), and 06 (`elD9HV9hqJA`)** returned **100.0% complete, uninterrupted verbatim transcripts** from `00:00:00` to the final second, YouTube's transcript index for **Videos 01, 03, and 04** only contained the opening and closing segments:

| Video | Missing Verbatim Caption Window | How the Content Was Reconstructed | Remaining Unverified Granular Details |
| :--- | :--- | :--- | :--- |
| **VIDEO 01 (`YKKdoH6QoG8`)** | `00:10:03 – 01:34:40` | Reconstructed from the **22-chapter official timestamp index** and full technical guide at [`poursamadi.com/time-analysis-strategy/`](https://poursamadi.com/time-analysis-strategy/), [`poursamadi.com/session-windows-pro-indicator/`](https://poursamadi.com/session-windows-pro-indicator/), [`poursamadi.com/weekly-map-indicator/`](https://poursamadi.com/weekly-map-indicator/), and [`youtubesummary.com/summary/YKKdoH6QoG8`](https://youtubesummary.com/summary/YKKdoH6QoG8). | Exact ticket numbers, lot sizes, and entry/exit decimal prices of `Live Trade 1` (`00:24:58`) and `Live Trade 2` (`01:28:04`), and the exact minute-by-minute boundaries of the 5 minor Grade-C Asian/Lunch sub-windows in the 11-window Gold map (the 3 Grade-A windows `10:00–13:00`, `15:30–16:30`, `16:30–18:00`, all 3 `US30` windows `16:30–18:00`, `18:00–21:00`, `21:00–23:00`, and all 9 Master Time Points `03:00, 04:00, 08:00, 09:00, 10:00, 16:30, 18:00, 20:00, 23:00` are **100% verified**). |
| **VIDEO 03 (`NDk94Ob8sEo`)** | `00:07:20 – 01:18:24` | Reconstructed from the **official 12-page `MAP Manager User Guide` PDF** ([`dl.poursamadi.com/mapManager/map-manager-userguide2.pdf`](https://dl.poursamadi.com/mapManager/map-manager-userguide2.pdf)), the **official `PRO BTB` strategy specification** ([`poursamadi.com/pro-btb-strategy/`](https://poursamadi.com/pro-btb-strategy/)), and the explicit `PRO BTB` recap in Video 02 (`00:19:08–00:20:32`). | Exact historical chart dates and ticket numbers of the mid-video `PRO BTB` chart examples between `00:45:00` and `01:18:00` (all 6 entry modes, 3 SL anchor modes, and all 15 `Map Manager` buttons are **100% verified**). |
| **VIDEO 04 (`7HEC5mO3d3U`)** | `00:06:38 – 01:06:57` | Reconstructed from the **official `SP2L` strategy specification** ([`poursamadi.com/sp2l-strategy/`](https://poursamadi.com/sp2l-strategy/)) and the explicit `SP2L` recap in Video 02 (`00:18:12–00:22:13`). | Exact entry price of the final Gold short trade (we know from verbatim `01:06:58` that the move started at `3326` and exited just above `3320`, and all `SP2L` rules—`P-Gap`, 1st pullback $L_t < L_{t-1}$, origin SL, `1:1` TP, and `50%` scale-in—are **100% verified**). |

---

## 2. Closed-Source `.ex4` / `.ex5` Binary Distribution (`Unreadable / Unexposed Source Code`)

- **Limitation**: Poursamadi distributes `Map Manager` (`v2.0.1`) and all 9 custom indicators (`Session Windows Pro v3.0`, `Session Clock Pro v1.0`, `Weekly Map v1.10`, `Previous Day High Low v1.10`, `Previous Day Session High Low v1.10`, `Round Levels v1.10`, `Candle Time v1.0`, `Pip Value v1.10`, `Spread v1.10`) as compiled MetaTrader binaries (`.ex4` and `.ex5`) gated behind free member login on `poursamadi.com`, and does not show the internal MQL4/MQL5 source code in the videos.
- **Mitigation**: All input parameters, default values, mathematical formulas, UI buttons, and edge-case behaviors are 100% documented in the official web pages and PDF guide (`Class A`), and complete, clean-room MQL5 and Python implementations (`Class B`) have been engineered in `implementations/extracted_code.md`.

---

## 3. Ambiguous or Contradictory Instructions Across Videos

All three apparent cross-video contradictions (`1:1` vs `1:10` R/R targets; using `Risk Free` vs avoiding `Risk Free`; `0.5%–1%` risk vs `5%–8%` cumulative scaling) have been formally analyzed and resolved via regime-conditional rules in `architecture/unified_architecture.md` (Section 2.3).

---

## 4. Missing Implementation Dependencies for Autonomous Live Execution

To deploy the Codex Astra engine in live trading, the target environment requires:
1. A live **MetaTrader 5 Desktop terminal** (Windows) or `MetaTrader5` Python IPC bridge (`pip install MetaTrader5`) connected to a broker server (`GMT+2` winter / `GMT+3` summer).
2. Explicit specification of the broker's **Minimum Hold Time** rule in Terms & Conditions (`default safety floor = 180 seconds` per Video 02 `00:49:08`).
