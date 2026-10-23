# Independent trade forensics

The research collector runs as the separate Windows task `aa-at-research-collector` in `E:\GPT\Inves\AA-AT-research-release-v1`. It reads a verified backup once and then reads only new rows from the campaign SQLite ledger and new immutable evidence files every five minutes. It does not import MetaTrader, poll the broker, submit orders, or manage workers. Its output is under `E:\GPT\Inves\AA-AT-research-state`, outside Git and the execution runtime. Collector failure does not stop trading.

## Source and identity rules

Primary evidence is the campaign's broker-reconciled `closed` rows and referenced broker order/deal JSON. A research trade is **one fully closed broker position lifecycle**, regardless of partial fills or multiple close deals. Imports verify every evidence SHA-256 and reconcile deal IDs, order IDs, gross profit, commission, swap, fees, and net PnL. Broker account login is stored only in local raw evidence; the warehouse uses a salted fingerprint, and portable exports replace account-bound campaign/signal keys. Magic Number alone is not used for attribution. An ownership mismatch is `UNRESOLVED`, not reassigned.

The source manifest for the initial backup is at `D:\AA-AT-Backups\AA-AT-Backup-V1.manifest.json`. The collector's current read checkpoint and counts are in `collector-status.json`. Research data is versioned by schema in `research/trade_forensics/store.py`; `raw/` copies original artifacts, while `research.sqlite3` contains indexed event and derived tables. The market importer accepts only provenance-tagged recorded CSV (`BROKER_EXPORT` or `ARCHIVED_RESEARCH`), with timezone-aware UTC timestamps. M3 bars are derived only from three contiguous M1 bars. No live broker polling is enabled.

## Current coverage and limits

At the initial verified extraction, 395 closed positions produced 395 strategy-attributed trade rows, 790 broker order events, 790 broker deal events, and no unresolved attributions. The independent market archive contained **zero** candles or ticks for those positions. Thus no factual price-path, spread, Bid/Ask, entry-quality, MFE/MAE, or trade chart can be generated for them yet. The original SL/TP is recorded; a complete historical modification stream was not found. The warehouse flags these gaps per trade. Broker net PnL and R multiples are supported where initial risk is recorded. Drawdown is over closed trades only; it is not intratrade equity drawdown. Session labels use timezone-aware London, New York, and Tokyo wall time, but campaign-specific broker timezone conversion still needs validation.

Charts are generated only after recorded candles cover a trade window. `python -m research.trade_forensics.charts TRADE_ID --state E:\GPT\Inves\AA-AT-research-state` writes Plotly HTML/JSON and PNG; OHLC excursions are labeled approximate because intrabar order is unknown. `python -m research.trade_forensics.market --help` shows the explicit market CSV import interface. A separate broker export or archive is needed before chart coverage can grow safely.

The current `trade_metrics.mfe_points` and `mae_points` column names are legacy names for **quote-price distance**, not broker points or pips. Their R values divide that distance by the recorded initial entry-to-stop quote-price distance. A broker point-size conversion is deliberately unavailable until symbol specifications are captured with provenance. Whole boundary candles overlap the holding interval, so an OHLC excursion can still include movement just before entry or after exit within those candles; tick-based Bid/Ask is required for exact excursion timing.

## Outputs and reproducibility

- `reports/performance.json`: strategy, strategy/symbol, strategy/session, and strategy/direction statistics with Wilson win-rate intervals and deterministic bootstrap expectancy intervals. They are descriptive; no profitability claim is made.
- `exports/AA-AT-RESEARCH-DATASET.zip`: redacted CSV, JSONL, Parquet, dictionary, and source/provenance manifest. Its adjacent `.sha256` protects portability. The embedded load guide gives pandas/Jupyter examples.
- `research.sqlite3`: accounts, strategies and versions, signals, broker events, position events, risk events, trades, quality issues, market sources, bars, ticks, metrics, hypotheses, and restart checkpoints. Position events are facts from deals; missing SL/TP modification events are not inferred.
- `trade_charts/`: per-trade HTML/JSON/PNG only when real recorded market data exists.

Use `E:\GPT\Inves\AA-AT-research-venv\Scripts\python.exe -m research.trade_forensics.exports --state E:\GPT\Inves\AA-AT-research-state` from the isolated research release to regenerate the portable package. Run `python -m unittest discover -s tests -p 'test_*.py'` from the source worktree for offline validation. Tests use isolated fixtures and never write campaign records.

Research hypotheses belong in the `hypotheses` table with supporting trade IDs, charts, mechanism, downside, sample size, and a time-ordered validation plan. None is created merely from a losing trade, and no hypothesis changes the frozen DEMO workers.
