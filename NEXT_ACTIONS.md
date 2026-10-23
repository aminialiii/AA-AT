# Next actions

Recovery gate as of 2026-10-23: use
[`docs/SAFETY_STOP_APPROVAL_REQUEST.md`](docs/SAFETY_STOP_APPROVAL_REQUEST.md)
for the exact official review of the denied stop-marker operation. Before any
task restart, repeat live DEMO and broker exposure checks, verify zero
ambiguous intents, and apply/test a minimal persistent guard for S04's
`filled_price_risk_exceeds_cap` breaker. The restored service would otherwise
lose that in-memory breaker on restart. Keep S04 and S06–S18 blocked. Do not
remove or bypass the stop marker during dashboard development.

The recovery-branch dashboard passed offline tests and a separate-port smoke
check; it remains staged. Review its read-only telemetry, private command-store
path, stale-state labels, and rollback procedure before an independent
dashboard-only deployment. Do not modify the trading task from a dashboard
release operation.

Critical 2026-10-23 status: the dashboard service is running locally, but the DEMO campaign Task Scheduler task is disabled and its `EMERGENCY_STOP` maintenance file remains. Automatic approval review rejected removing that safety file. The prior `service.py` was restored from the pre-deployment backup. The dashboard control bridge is not operational in the running trading service. Do not imply that worker buttons can route commands or that trading has continued after the last verified close.

1. A human operator must review the stopped campaign, broker positions and pending orders, local outstanding intents, and the restored source version. Resolve the safety stop through an authorized path; do not bypass the rejected file operation. Recheck DEMO identity and current risk before enabling the trading task. The new control bridge can be deployed only in a separate verified maintenance window.
2. Keep the loopback dashboard task healthy, inspect its authenticated feed and test results, and review the draft PR. No code in that PR is automatically deployed to MetaTrader.

1. Review the automation-branch pull request. The four-hour task, no-change behavior, and first scheduled changed synchronization are verified; the PR remains unmerged and undeployed.
2. Monitor the newly deployed five-slot, 2% aggregate DEMO policy across subsequent real signals. Confirm the 1% daily and 2% peak-equity halts, one-position-per-strategy rule, broker ownership, and per-order margin gate remain effective. Record real closed trades only after broker deal and position verification; do not force signals.
   Investigate repeated quote/clock freshness suspensions with broker timestamps and terminal health; preserve the current fail-closed routing behavior.
3. Investigate blocked S06–S18 individually. Implement adapters only where original rules are sufficiently specified; freeze each new executable version before forward testing.
   Examine a supported, credential-safe operating model if pre-login recovery after reboot is required; current tasks resume at user logon.
4. Update the dashboard and Graphify from verified operational state without publishing account numbers or trade-level evidence to Git.
5. At 100 genuine closed trades per strategy, inspect the immutable performance snapshot and continue valid DEMO execution. Repeat at 200, 500, 1,000, and every subsequent 500 trades. Do not interpret any milestone as proof of an edge.

Continuation command for a later Codex session: `Resume AA AT from E:\GPT\Inves\AA-AT\CHECKPOINT.json; verify current broker state and service health before making changes.`
