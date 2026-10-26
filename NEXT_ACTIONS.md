# Next actions

Gold entry disabled in the DEMO live campaign at 2026-10-26 16:35 Asia/Tehran by user request. New XAUUSD signals are excluded from the dispatch list, and the final broker-send gate rejects symbols outside the six approved FX pairs. The frozen S01-S18 signal source, account-bound campaign configuration, and risk policy remain unchanged. A verified V3 backup covered 473 closes before deployment. The restarted task has a fresh broker-reconciled HEALTHY heartbeat with five active workers and 475 closes; S06-S18 remain blocked. No manual order was submitted. The earlier task interruption returned 0xC000013A; its initiator remains unknown. See [the deployment record](docs/GOLD_DEMO_ENTRY_DISABLED_2026-10-26.md). This paragraph is a timestamped observation, not a guarantee of future uptime.

Current deployment, 2026-10-26: DEMO policy v4 is loaded and the five workers are HEALTHY. Monitor genuine XAUUSD signal admissions/fills against the USD 10 cap, current-equity and headroom limits; reconcile every broker fill and retain protective SL/TP. Raising the 2% limits did not address the separate quote/clock interruptions. No gold fill or historical validation is claimed yet.


Current verified recovery, 2026-10-26 Asia/Tehran: the existing DEMO task was
started after a fresh broker, ledger, risk, and backup check. Its heartbeat is
`HEALTHY` and DEMO verified; S01–S05 are `ACTIVE`, S06–S18 remain `BLOCKED`, and
395 broker-reconciled closes were preserved. There were no open or pending
broker orders at the verification time. See
[the interruption record](docs/INCIDENT_2026-10-26_DEMO_TASK_INTERRUPTION.md).

1. Monitor fresh service heartbeats, broker reconciliation, the emergency latch,
   quote/clock consistency, and S04 fill risk. Do not infer a new trade from an
   active worker without broker order/deal evidence.
2. Investigate the un-attributed `0xC000013A` task interruption. Task Scheduler
   Operational logging was disabled, and a user-logon trigger did not recover
   the service. Review any watchdog or trigger change separately with a
   fail-closed safety design.
3. Keep S06–S18 blocked until independently executable rules and controls are
   verified. Keep existing portfolio and per-trade risk constraints unchanged.

The older 2026-10-23 note below is retained as incident history, not current
broker status.

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

Operational update, 2026-10-26: user-authorized policy v5 measures daily equity loss and peak drawdown without halting new DEMO entries at the prior 5% and 10% thresholds. The post-restart broker-reconciled heartbeat was HEALTHY with S01-S05 active and 526 closes preserved. FX per-trade risk, 10% aggregate open/pending risk, five slots, DEMO guard, FX-only entry, emergency stop, and other safety gates remain. See docs/DRAWDOWN_MEASURE_ONLY_2026-10-26.md. This is a timestamped observation.
