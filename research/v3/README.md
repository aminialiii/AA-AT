# AA-AT V3 isolated historical research

This directory is a research-only addition on `research/v3-isolated-backtest`. No
production strategy, campaign configuration, worker, broker order, or live
dashboard file is edited. The fixed target is `[2023-10-24T00:00:00Z,
2026-10-24T00:00:00Z)`. A source that covers less of that window is not a
three-year dataset.

## Boundaries and current evidence

| Component | Location | Access and status |
|---|---|---|
| Frozen source | `E:\GPT\Inves\research\overnight-20261010\engine.py` | Read-only; SHA-256 `7858325bc531382b52bdb9e5fdc910b44cf7ebfe6bea19934e24faafd618ebfb` |
| Research code | this directory | Separate Git branch; new files only |
| Small warehouse catalog | `E:\GPT\Inves\AA-AT-research-state\v3` | Additive JSON reports; active `research.sqlite3` untouched |
| Large market vault | `E:\GPT\Inves\AA-AT-v3-market-vault` | Immutable raw files and Parquet, outside daily ZIP rotation |
| Research MT5 | vault `mt5-portable` directory | Signed binary copy, separate `/portable` data, no account file; startup verified, tester blocked by missing independent account |
| Staged research dashboard | `http://127.0.0.1:8775/` | Separate authenticated read-only task; no worker controls |

The fresh pre-implementation backup is
`D:\AA-AT-Backups\AA-AT-Backup-V3.zip`, SHA-256
`c6a6e715c4cf4d635fcfc80376472abc30718615712fd7a939555491e49540b5`.
It passed all 25,294 member checks and 12 isolated SQLite restores. The
existing V1/V2/V3 rotation remains active. **Security limitation:** the
archive is unencrypted while containing account-bound configuration and a
campaign database. Do not store new research credentials in the backed-up
research-state tree. Encryption or access-control changes to the production
backup worker require separate authorization under the production-protection
directive.

Seven genuine, source-hashed legacy broker NPZ archives were copied into the
vault and indexed as 665,000 M1 bars. The saved fixed 180-minute broker offset
is not verified over history. They do not provide continuous three-year
coverage or Bid/Ask ticks. The catalog explicitly sets
`eligible_for_three_year_backtest=false` for each. The read-only signal-rule
check compares S04 against the frozen Python function on all seven archives:
zero mismatches. That is **not MQL5 runtime or fill parity**. The S04 EA
compiled with 0 errors and 0 warnings in the isolated MetaEditor. No
historical backtest or simulated trade has been produced by V3.

The official MT5 installer host was unreachable from this machine. The
separate signed portable copy created its own `MQL5`, `Tester`, `config`, and
`logs` folders on a bounded launch, with no `accounts.dat`. A tester-configured
probe on 2026-10-25 started and exited cleanly; its UTF-16 tester log says
"tester not started because the account is not specified." The original log
hash and outcome are in `tester-probe-analysis.json`. This verifies terminal
startup and tester invocation, but no tester execution or backtest. The
production integrity comparison found no unexpected changes.
The portable probe also created a research-specific MetaQuotes metadata folder
at `C:\Users\SOC-Peyman\AppData\Roaming\MetaQuotes\Terminal\A7806C9494F93E37A61F4174F2E3283B`.
Its `origin.txt` names the separate vault terminal; it contains no account
file. This exact folder is a research-only write exception outside the vault.
The shared `Terminal\Common` directory has no files. The research terminal is
stopped and must not be relaunched if its origin or account-file guard fails.
The production terminal may update its own `terminal.ini` while running; the
integrity audit records its timestamp and digest but compares only stable
terminal identity files, task configuration/state, frozen code/configuration,
the stop marker and ledger continuity.

## Reproduction

Use `E:\GPT\Inves\AA-AT-research-venv\Scripts\python.exe` from the research
worktree:

```powershell
python -m research.v3.safety --output E:\GPT\Inves\AA-AT-research-state\v3\audit\before.json
python -m research.v3.market_import --legacy-pointer E:\GPT\Inves\research\overnight-20261010\history_pointer.json
python -m research.v3.parity
pwsh -NoProfile -NonInteractive -File research\v3\compile_ea.ps1
python -m unittest discover -s research\v3\tests -v
python -m research.v3.safety --before E:\GPT\Inves\AA-AT-research-state\v3\audit\before.json --output E:\GPT\Inves\AA-AT-research-state\v3\audit\after.json
```

The staged dashboard task is `AAATV3ResearchDashboard`. Its access token is
stored only at `E:\GPT\Inves\AA-AT-v3-market-vault\secrets\dashboard-token.txt`
with a restricted ACL; it is not in Git, the dashboard HTML, or the daily ZIP.
The API is `GET /api/status` with `Authorization: Bearer <local token>`.
There is no trading-control endpoint. The task starts at user logon, so it
does not promise operation before an interactive logon.

## Data acquisition gate

The independent provider attempts were bounded. Dukascopy's documented legacy
hourly endpoint supplied **one genuine EURUSD hour**: 2024-01-15 12:00–13:00
UTC, 4,214 ordered Bid/Ask ticks. Raw BI5 SHA-256:
`5a25514433c36b778ab087b4fa070d277b76ca4f41057889e588c0d4397b4d2c`.
Raw and Parquet files are in the vault and indexed in the source catalog. The
external quotes are not broker-matched. At most 60 M1 bars are available from
this file, below S04's 100-contiguous-bar warm-up. Another hour received HTTP
429, so acquisition stopped without retries. The newer S3 path returned 403.
The public HistData monthly form returned an empty response; no HistData file
was accepted. `dukascopy_hourly.py` and `histdata.py` provide bounded,
source-hashed import paths. A complete broker export or independent research
access remains necessary for full-period coverage and broker contract/cost
history; XAUUSD's price scale and specifications require source evidence.
Imports refuse a write that would leave under 5 GiB free in the vault.

The S04 EA now has an optional tester-only `InpParityTrace`. The strict
`parity_runtime.py` comparator checks actual warmed-up MQL bar traces against
the frozen Python rule on the same UTC-verified M1 source, reporting missing
bars, duplicate timestamps, ATR, spread, signal and eligibility mismatches.
No actual MQL trace exists yet. Entry quote, size, SL/TP, exit and fill parity
remain unverified; the frozen Python replay uses a next-bar M1 approximation,
whereas the EA uses tester quotes and `OrderCalcProfit`. The frozen S04 replay
has no break-even or trailing transition to validate. The EA was recompiled
with 0 errors and 0 warnings after the trace addition.

The research-only Market Status Engine distinguishes market closures from
stale quotes when a sourced schedule exists. Current configured symbols,
including XAUUSD, return `UNKNOWN` because no broker schedule or fresh quote
source is connected. The offline economic-calendar importer preserves UTC
publication times and explicit missing values, but no verified event archive
has been imported. Neither component controls trading.

An inherited MCP API key and production endpoints were found in the research
MT5 copy's `assistant.ini`. The key and endpoints were removed from that
research file, both MCP sections disabled, and the probe now fails closed if
an enabled endpoint or key reappears. Production configuration was untouched.

The first data-dependent next step is a complete, independently acquired
market partition with verified UTC mapping and source provenance. Only then
may the S04 EA be run inside the isolated tester, its outputs compared to the
frozen Python reference, and a baseline trade journal accepted. S01–S03 and
S05 follow after the first full parity and accounting gate. S06–S18 remain
blocked where their executable rules or inputs are incomplete. The live
dashboard, gold trading, and production services remain outside this workflow.

## Provenance and recovery

The vault is **outside** the daily ZIP's source roots to protect the three-slot
rotation from large tick datasets. Its catalog and hashes are in the existing
warehouse tree, but the market files are not yet independently backed up.
Pause acquisition before exceeding recoverable storage; do not claim a fully
recoverable three-year dataset until separate backup capacity is provisioned.
No historical results are written to `BROKER_CONFIRMED_DEMO` tables. Future
tester trades must be stored with `source_type=HISTORICAL_BACKTEST` and their
own run, source, EA, execution-model, cost and configuration hashes.
