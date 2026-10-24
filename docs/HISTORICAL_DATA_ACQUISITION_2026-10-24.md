# Three-year historical data acquisition — 2026-10-24

The verified V2 pre-backtest archive remains at `D:\AA-AT-Backups\AA-AT-Backup-V2.zip`. An independent repeat check on October 24 verified its SHA-256 (`7a3df6f5c193f8c9822e1d3e372f25133c5541574cd96745b81e0178a0ed35a5`), all 25,248 ZIP members and 12 isolated SQLite restores. The existing `aa-at-backup-worker` task is Running; V1, V2 and V3 ZIP slots remain present. No trading task, MT5 terminal, strategy configuration or broker order was touched.

## Required source data

The fixed target is `[2023-10-24T00:00:00Z, 2026-10-24T00:00:00Z)`. Warm-up must extend before the start. These are implementation requirements from the [strategy catalog](../research/project-review/STRATEGY_CATALOG.md), not proof that the data exists.

| Strategies | Required symbols | Native signal data | Additional dependency |
|---|---|---|---|
| S01–S03 | XAUUSD, EURUSD, GBPUSD, USDJPY, USDCHF, USDCAD, AUDUSD | M1; registered M5 variants for S01–S03 | Bid/Ask ticks or a justified intrabar bound, 100-bar warm-up, broker timezone and historical contract/cost rules |
| S04–S05 | Same seven symbols | M1 | Bid/Ask execution path, contract/cost rules; S05 remains a numerical SP2L proxy |
| S06 | Same seven symbols | M1 plus 5-second tick momentum | Ordered Bid/Ask ticks, managed-limit acceptance/fill/cancel model |
| S07–S08 | XAUUSD (S07 all-broker variant also exists) | M1 and ticks; S08 S5/S15 short bars | Frozen native configuration, tick aggregation and broker execution model |
| S09 | EURUSD, GBPUSD, XAUUSD | M1, M5, H1 | Historical event anchors and state-reset logic |
| S10–S12 | EURUSD, GBPUSD | M5, prepared indicators | Missing prepared EMA/ATR or RSI pipeline and exact source provenance |
| S13–S14 | Protocol-selected contracts | Ticks and M1 | Frozen protocol schedule, native 5-second and exit rules |
| S15 | Config-selected symbols | M1, M5 | Installed evaluator/risk version and compatible frozen policy |
| S16–S18 | Proposal only | Intended H1 context, M5 setup, M1 trigger | No executable mechanical strategy definition; H1 in S18's H1/H2/H3 discussion means *attempt number*, not an H1 price bar |

Broker-matched acquisition requires a **separate research terminal or an offline export** for all relevant symbols: M1 and ordered Bid/Ask ticks across the target plus warm-up; timestamps with a verified broker UTC/DST mapping; symbol contract/tick/point/stop-level and margin specifications over time; historical commission and swap schedules; spread history; and source identity/checksums. The production terminal must not be used. MetaTrader's documented GUI path is *Market Watch → Symbols → Bars/Ticks → Request → Export*, but a separate terminal with broker access or an already-created export is required. A saved login is not a historical-data export or proof of three-year coverage.

## Independent provider investigation

HistData's public catalog lists all seven priority symbols and publishes year or month ASCII ZIP selections. Its documented M1 bars are **Bid-only**; its generic ASCII ticks include Bid and Ask. All timestamps use fixed EST (UTC−05:00) **without daylight-saving adjustment**, so they can be converted to UTC deterministically. This does **not** establish the DEMO broker's own timezone or quote equivalence. The provider warns that its free data has no accuracy warranty. On October 24 its site reported files last updated **2026-10-18 22:40:40**, leaving the target's final trading days unavailable from that catalog at that time. [Provider FAQ](https://www.histdata.com/f-a-q/), [file specification](https://www.histdata.com/f-a-q/data-files-detailed-specification/), [download catalog](https://www.histdata.com/download-free-forex-data/).

A bounded EURUSD M1 2023 form download from the host returned HTTP 200 with `Content-Length: 0`; the normal in-app browser click did not yield an inspectable ZIP. The zero-byte response at `E:\GPT\Inves\AA-AT-research-state\market_data\incoming\HistData\EURUSD_M1_2023.download` is **rejected**, not market data. A single direct Dukascopy data-host HEAD check ended in a connection reset. Dukascopy's official [historical export page](https://www.dukascopy.com/api/data/get/historical-data-export) describes Bid/Ask data, but no independently accessible, verified archive was obtained. No automated retry loop was started. Public provider prices, if later acquired, must carry `EXTERNAL_HISTDATA_CONTEXT` provenance; they cannot silently replace broker execution quotes. [MetaTrader history export documentation](https://www.metatrader5.com/en/terminal/help/trading/market_watch).

## Validated import path

Import validates file structure, not external provenance. A supplied archive is marked `UNVERIFIED_INPUT_ARCHIVE` until its acquisition trail is independently checked; a matching filename alone never proves provider origin.

`research.trade_forensics.historical_import` accepts an authentic provider ASCII ZIP **one year or month at a time**. It checks ZIP CRC and flat member identity; hashes and preserves the raw archive; parses fixed-EST M1 or millisecond Bid/Ask ticks to UTC; rejects bad or reversed prices and out-of-order timestamps; counts M1 discontinuities and exact duplicate tick rows; writes bounded Parquet batches; and indexes source, coverage, quality and file hash in the **existing** `AA-AT-research-state\research.sqlite3` warehouse. Re-importing the same source is idempotent. It never queries MT5, imports trading code or writes simulated trades. Gaps require calendar review; a provider archive and structural checks alone do not authorize a backtest.

Example **only after a real archive is obtained and its origin verified**:

```powershell
& 'E:\GPT\Inves\AA-AT-research-venv\Scripts\python.exe' -m research.trade_forensics.historical_import 'E:\path\to\HISTDATA_COM_ASCII_EURUSD_M1_2023.zip' --symbol EURUSD --kind M1 --period 2023
```

The importer is intentionally limited to the seven currently identified priority symbols; expansion for a verified S09–S15 source should follow its frozen configuration. The provider format must be checked against a real archive before bulk import. The 65 offline tests include fixture-only importer cases and create **no** campaign or historical trade rows. Current accepted external archives: **0**. Current imported market bars/ticks: **0**. Current three-year baseline and portfolio runs: **0**. The first data-dependent next step is an actual broker export from an isolated research terminal, or authentic provider ZIP files; the exact broker contract/cost history remains separately necessary for faithful execution modelling.
