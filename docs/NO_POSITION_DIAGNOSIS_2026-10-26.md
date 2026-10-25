# Why no DEMO position opened after the weekend

Read-only observation at 2026-10-25 23:18–23:20 UTC. This is a timestamped diagnosis, not a claim about later broker state.

The campaign heartbeat was fresh and `HEALTHY`, the pinned account passed the DEMO/permission guard, S01–S05 were active, the emergency-stop marker was absent, and the broker-reconciled status showed zero open positions and pending orders. The immutable campaign index contained 395 previously closed trades and no unresolved send intent. Seven symbols had current M1 bars; the live service advanced all 35 strategy/symbol cursors to 23:17 UTC. This proves the service was processing market data, but does not prove that any eligible strategy signal occurred.

The immediate reason for no new position was the frozen signal adapter's gap warm-up. `research/demo-live-20261021/live_signals.py` marks the first 100 M1 bars after **any** non-contiguous timestamp invalid (`valid[j+1:min(n, j+101)] = False`). The frozen signal function in `research/overnight-20261010/engine.py` zeros signals on invalid bars (`out[~d['valid']]=0`). A read-only MT5 rate check found the weekend gap in all seven configured symbols, 79 completed post-gap M1 bars at 23:18 UTC, and 21 invalid warm-up bars remaining. The first potentially valid bar is 23:40 UTC, evaluated after it closes around 23:41 UTC (03:11 Asia/Tehran), assuming continuous bars and fresh quotes. A valid bar is **not** itself a trade signal; entry and broker/risk gates still apply.

No strategy rule, broker order, risk limit, emergency stop, scheduled task, or live service was changed for this diagnosis. We did not generate or force a signal. The status label `ACTIVE` means the worker is running, not that it is currently allowed to emit a post-gap signal. That distinction is now recorded in the Graphify graph and report.

The checked-in `research/demo-live-20261021/risk_policy.json` is version 2 with a 2% aggregate cap; the separate deployed runtime reported policy version 4 and a 10% cap at this observation. The graph keeps static configuration and timestamped effective runtime policy as distinct nodes. The deployed policy hash and account-bound configuration are intentionally omitted here.

Evidence sources: timestamped local `runtime/status.json`, read-only `runtime/campaign.sqlite3` cursor/intent/closed tables, read-only MT5 DEMO account/rate query, and the cited source lines. Raw account identifiers, broker tickets, credentials, and trade records remain outside Git.
