# DEMO campaign task interruption and recovery — 2026-10-26

This is a sanitized operational record. Broker identifiers, order/deal records, account values, and runtime logs remain outside Git.

## Observed failure

The campaign's last status heartbeat was 2026-10-24T07:36:27Z. It reported `SUSPENDED` with `broker_clock_or_quotes_inconsistent`; S01–S03 and S05 were waiting for the broker, while S04 had a transient stale-quote worker suspension. The task `CodexDemoForward20261021` was enabled but `Ready`, with no campaign Python process. Its last result was `0xC000013A`, an interrupted-process exit. The Task Scheduler Operational log was disabled, so the actor or event that interrupted the process cannot be attributed from that log. The host had not rebooted. The task has a user-logon trigger and had not relaunched the campaign after the interruption.

The quote/clock safety gate is a separate availability issue. The service code is designed to stay alive in `SUSPENDED` while an already activated campaign awaits fresh, consistent prices. The stale quote alone does not explain the missing process. No frozen signal rule or risk-policy change was made to recover service.

## Pre-restart safety evidence

- The current broker preflight confirmed the pinned DEMO identity, hedging mode, trading permissions, and fresh quotes for all seven configured symbols. It submitted zero orders.
- The broker reported no open positions or pending orders and no deals since 2026-10-24 UTC.
- The campaign SQLite integrity check passed. It held 395 reconciled closes, no `PREPARED`, `OPEN`, or `PENDING` intents, and the same activated policy hash.
- The durable dashboard emergency latch and `EMERGENCY_STOP` file were absent. S04's recorded fill-risk breach retained its matching reviewed, event-bound release; it was not erased.
- The current equity passed the unchanged peak-drawdown gate. Frozen strategy and registration source hashes matched their pinned configuration values. The policy hash and the five-position/two-percent aggregate limits matched the prior checkpoint.
- The latest V1 backup had `SUCCESS` status; its SHA-256 matched its manifest, the ZIP opened with the expected member count, and it contained the campaign database. V2 and V3 remained present.

## Recovery and verification

At approximately 2026-10-25T22:41:52Z, the existing enabled Task Scheduler task was started without changing its definition. Subsequent fresh heartbeats reported `HEALTHY`, DEMO verified, five `ACTIVE` workers (S01–S05), thirteen blocked workers (S06–S18), 395 preserved closed trades, no open or pending broker exposure, no emergency stop, five portfolio slots, and a 2% aggregate open-risk limit. The task remained `Running` through a second check about 25 seconds later. The separate command-center `/health` endpoint returned HTTP 200.

No test order, backtest, strategy-rule edit, policy relaxation, emergency-stop bypass, or production code deployment was performed. Genuine signals may produce new DEMO orders under the existing admission gates.

## Remaining uncertainty

The exact initiator of the interrupted-process exit is unknown because task event logging was disabled. The task's user-logon trigger did not provide automatic recovery from this interruption. Monitor heartbeat age and broker reconciliation; review a separate, safety-aware watchdog or task-trigger change before deploying one. Broker quote/clock inconsistencies may still suspend new order admission. A live `ACTIVE` worker means its execution path is available, not that a valid signal is present.
