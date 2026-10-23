# Dashboard-only staged release

The Trading Command Center is a different Windows task from
`CodexDemoForward20261021`. A dashboard release may change only
`AAATCommandCenter` and an immutable dashboard checkout. It must not copy
`service.py` into the original trading workspace, edit account-bound campaign
configuration, alter the broker ledger or risk policy, remove the safety-stop
marker, or start/stop the trading task.

Before a release, record the trading task state, SHA-256 of its `service.py`
and `EMERGENCY_STOP`, and the closed/outstanding ledger counts. Run the full
offline unit suite, JavaScript syntax check, secret scan, and Graphify
validation. Create an immutable release checkout at a reviewed commit. Run it
on a separate loopback port and verify authenticated status, static assets,
SSE, stale-data presentation, blocked-worker controls, and the current safety
stop. A health response alone does not verify the data feed.

Export the existing dashboard task definition into the restricted local
rollback directory. Switch only the dashboard task's working directory to the
new release checkout, then restart only that dashboard task. Verify the live
loopback URL and compare the trading task state, stop-marker hash, service
hash, and broker ledger counts to the pre-release values. If the dashboard
fails, restore only its saved task definition and previous checkout. Neither
the forward campaign nor broker terminal is part of this rollback.

The Worker Management API is a separate logical control plane backed by
`AA-AT-command-center-state/commands.sqlite3`. The dashboard release reads
the broker-reconciled campaign ledger in SQLite read-only mode and never
imports Python from the mutable trading runtime. The trading service owns
final account, broker, ownership, risk, and order-admission checks. Until its
matching bridge is safely deployed and verified after official stop clearance,
the API must return `control_bridge_not_operational` and the UI must not claim
that a worker control is active. Bridge version 2 includes a digest of the
resolved command-store path; the dashboard requires that digest to match its
private store before accepting any enable/restart request. The candidate
trading bridge is source-only and must not be copied into the active runtime
as part of a dashboard release.
