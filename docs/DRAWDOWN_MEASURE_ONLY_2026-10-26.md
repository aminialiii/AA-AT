# DEMO drawdown measurement-only policy — 2026-10-26

The user authorized disabling the **daily equity-loss halt** at 5% and the **peak-equity drawdown halt** at 10%. Both percentages remain measured and visible in the broker-reconciled runtime status. Neither threshold blocks new orders under policy v5. This does not remove protective stop-loss orders from individual trades.

The rollout began after a verified V1 backup (526 broker-confirmed closes), a DEMO and hedging account preflight, zero open positions or pending orders, zero unresolved intents, and fresh quotes for all six approved FX symbols. The task was suspended on `daily_equity_loss_halt`; it was stopped while flat, policy files were replaced with rollback copies retained outside this repository, and the existing task was restarted. No manual order was submitted.

At the first verified post-restart heartbeat, broker status was HEALTHY, five eligible workers were ACTIVE, 526 closes remained, no position or pending order existed, and both halt flags were false. The observed daily loss was about 5.04%; peak drawdown was about 5.38%. These are timestamped observations, not a guarantee of future service uptime.

Unchanged controls: verified DEMO identity and permissions, six-symbol FX allowlist (new XAUUSD orders denied), protective SL/TP, per-trade cap of 0.25% of allocated equity for FX, five global open/pending slots, 10% aggregate open/pending planned-risk cap, margin/quote/clock checks, emergency stop, and strategy-specific breakers. S06–S18 remain blocked.

Offline repository checks passed: ten portfolio-policy tests and six repository-safety tests. An older live-only `test_safety.py` has two outdated `Broker.send` signatures and fails before reaching the mocked safety guard; this is a test-maintenance defect, not an observed broker order. The policy-specific offline test and direct read-only DEMO preflight passed.

Files mirrored in the repository: `research/demo-live-20261021/{portfolio_policy.py,service.py,risk_policy.json}` and `tests/test_portfolio_policy.py`. The frozen strategy source and campaign configuration were not edited. The V1 backup archive hash matched its success manifest. The deployment rollback copies are outside Git.
