# Next actions

Research checkpoint, 2026-10-23 21:32 UTC: continue the independent five-minute
collector and 24-hour three-slot backup worker. V2 and its SQLite restore drill
passed; the authenticated research dashboard is live. The portable dataset
contains 395 verified closed lifecycles but zero recorded candle/tick rows.
Acquire a provenance-tagged broker export or existing archive through a source
that does not contend with the active terminal before producing factual trade
charts or excursions. Validate broker timezone and missing Bid/Ask/SL/TP-event
coverage; never infer the absent events. Review this isolated research branch,
the blocked Git sync state, and the fresh broker safety heartbeat before any
subsequent operational change. Do not clear the quote freshness gate or S04
breaker for research convenience.

Current DEMO status, 2026-10-23: the trading task is running. Its broker-
reconciled heartbeat reports DEMO verified and HEALTHY; S01, S02, S03, and S05
are active, S04 remains blocked by the persistent fill-risk event, and S06–S18
remain blocked. The ledger had 227 closed trades and 454 matching broker deal
IDs at restart; a subsequent S02 close raised the verified total to 228. Two
open intents matched broker-owned, SL/TP-protected positions at the last check.
The prior maintenance
stop marker is absent. The user reported that an administrator approved its
clearance, but an approval decision ID was not independently available.

1. Monitor service heartbeat, DEMO guard, broker positions and pending orders,
   ownership, risk utilization, order intents, and safety events. Stop or
   suspend routing on any reconciliation or risk failure; do not force signals.
2. Keep S04 blocked until its fill-risk event is reviewed through the risk
   process. Its breaker now reloads from the persistent safety-event ledger on
   restart. Do not reset it merely to enable the worker.
3. Keep S06–S18 blocked until executable rules, adapters, and safety dependencies
   are independently verified. Preserve frozen S01–S05 strategy definitions.
4. Review the dashboard control bridge candidate separately. The running
   dashboard monitors live broker-reconciled service status, but management
   commands remain unavailable because the bridge is not deployed. Do not
   couple a dashboard release to a trading-service restart.
5. Keep the four-hour Git sync task active and the recovery PR unmerged pending
   review. Verify the admin stop-clearance decision record if it becomes
   available; retain the maintenance-stop incident evidence.

Continuation command: `Resume AA AT from E:\GPT\Inves\AA-AT\CHECKPOINT.json; verify current DEMO broker state and safety events before any execution change.`
