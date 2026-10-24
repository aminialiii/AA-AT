# Next actions

Current DEMO status, 2026-10-23: the trading task is running. Its broker-
reconciled heartbeat reports DEMO verified and HEALTHY; S01–S05 are active and
S06–S18 remain blocked. S04's recorded fill-risk breach was reviewed, a more
conservative admission guard was deployed, and an event-bound release was
appended without deleting the original safety event. After the controlled
restart, all 230 prior closes were preserved. S04 then placed a genuine,
broker-confirmed protected USDCAD order; a later dashboard verification showed
233 closed trades and one open position. These counts and positions are time-dependent.
The prior maintenance-stop marker is absent. The user reported that an
administrator approved its clearance, but an approval decision ID was not
independently available.

1. Monitor service heartbeat, DEMO guard, broker positions and pending orders,
   ownership, risk utilization, order intents, and safety events. Stop or
   suspend routing on any reconciliation or risk failure; do not force signals.
2. Monitor S04's new fills against the 0.25% allocated-equity cap, including
   full cost reserve. Any new fill-risk breach must re-block S04; retain the
   original breach and reviewed-release evidence.
3. Keep S06–S18 blocked until executable rules, adapters, and safety dependencies
   are independently verified. Preserve frozen S01–S05 strategy definitions.
4. Keep the dashboard's reviewed-breaker projection aligned with the service.
   Its read-only fix was deployed with a dashboard-only restart and now displays
   S04 as active. Review the control bridge candidate separately; management
   commands remain unavailable because the bridge is not deployed. Do not
   couple a dashboard release to a trading-service restart.
5. Keep the four-hour Git sync task active and the recovery PR unmerged pending
   review. Verify the admin stop-clearance decision record if it becomes
   available; retain the maintenance-stop incident evidence.

Continuation command: `Resume AA AT from E:\GPT\Inves\AA-AT\CHECKPOINT.json; verify current DEMO broker state and safety events before any execution change.`
