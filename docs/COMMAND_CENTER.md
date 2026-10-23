# AA AT Trading Command Center

The command center is a local, authenticated DEMO operations application at `http://127.0.0.1:8765/`. It reads the live campaign status and broker-reconciled SQLite ledger, streams updates with Server-Sent Events, and displays all S01–S18 workers. The Windows task `AAATCommandCenter` starts it at interactive user logon and restarts its process after failures. It does not need a Codex session. It is deliberately bound to loopback; there is no public listener, remote tunnel, or broker credential in the browser.

## Data and control flow

`MetaTrader DEMO → campaign service → broker reconciliation → local SQLite/evidence/status → authenticated command-center API → browser`. A separate `AAATGitHubSync4h` task validates source, runs offline tests and secret scanning, then pushes to a review branch; it never deploys trading code. Graphify is a development graph, not a runtime broker health source.

The 18 workers are independent `asyncio` tasks with separate IDs, queues, cursors, evidence and performance, but share one Python process, MT5 terminal, portfolio risk supervisor and order router. They have no individually measurable CPU/RAM process; those values are shown as unavailable. Configured S06–S18 are not represented as running trading implementations. A blocked worker cannot be started from the dashboard.

The service-side control bridge is `research/demo-live-20261021/worker_control.py`. Commands and audit records persist in a separate local SQLite database. `PAUSE` and `STOP` commit a new-order disable mode before API acknowledgment. `START`, `RESUME`, and `RESTART` are requests that the campaign applies only after fresh DEMO identity, broker exposure, ownership, reconciliation, equity and risk checks. `RESTART` additionally requires no outstanding intent for that worker, cancels only that task, drains its old queue and preserves its durable cursor and ledger. The portfolio-wide emergency latch disables new-order admission without liquidating positions; broker-native protective orders and global reconciliation continue. An admission transaction serializes control changes with the single order route, so a successful stop response cannot be overtaken by a later admission in this process. No UI action changes the frozen strategy signal rules or risk caps.

The command API is a **prepared integration until the running campaign reports `control_bridge_version: 1`**. The server rejects control requests while the bridge is absent or its status heartbeat is stale. Do not treat a visible control button as proof of execution; inspect its durable `PENDING`, `APPLIED`, or `REJECTED` command status and the current broker snapshot. The review branch may contain code that has not been deployed to the live campaign.

## Authentication and browser safety

The installer creates random viewer, operator and administrator bearer tokens under the local `AA-AT-command-center-state` directory. `access_keys.txt` is the one-time local token handoff; `auth_hashes.json` stores only hashes. The installer restricts that directory ACL to the current Windows user and SYSTEM. Enter a token in the dashboard login screen; the browser keeps it in session storage and sends it only in the Authorization header. Viewer can read data; operator can submit worker commands; administrator can also latch emergency stop. Mutating endpoints enforce JSON bodies, a same-origin check, idempotency keys, rate limits and server-side role checks. There are no cookies, so a cross-site request cannot automatically carry authority. Keep tokens and the local evidence directory out of Git. Rotate access by replacing the local auth files while the server is stopped; never commit or paste a token into a URL.

## Telemetry semantics

The status heartbeat is fresh for 15 seconds. Balance, equity, unrealized PnL, open positions and risk utilization are shown only when the broker status is `HEALTHY`, DEMO is verified and the snapshot is fresh. A suspended or stale snapshot masks those fields instead of displaying an unverified zero. Historical equity before the command center was not recorded; its equity chart persists new verified broker snapshots once per UTC minute, without filling gaps. The separate PnL chart is a **closed-trade realized PnL** curve. Win rate and closed-trade totals come from the local broker-reconciled ledger. Per-strategy profit factor and expectancy come from the matching performance report; mismatched versions are omitted. Spread is embedded in broker fills but is not independently valued in the closed ledger. The first 100 closes per strategy are a research milestone, never an automatic stop.

The Graphify HTML shown in the architecture panel is account-free source evidence. Static edges describe references and implementation; they do not prove that the service or control bridge is running. Raw broker order and deal evidence stays in the original local workspace.

## Startup and recovery boundary

Install with `tools/install_command_center_task.ps1 -StartNow` from a PowerShell session under the same interactive Windows user. The installer fails if it cannot restrict the secret directory ACL. Verify `http://127.0.0.1:8765/health`, then log in at the dashboard URL. The dashboard survives a Codex session ending. Like the MT5 and Git tasks, it is scheduled at user logon; pre-login operation after a machine reboot is **not verified**.

As of 2026-10-23, the command-center web service is running, but the trading campaign is under a local `EMERGENCY_STOP` maintenance file and its Task Scheduler task is disabled. The previous trading `service.py` source was restored from the pre-deployment backup. Automatic approval review rejected removal of the stop file, so no alternative file operation was used to clear it. A human operator must review the stopped state, confirm there are no open or pending broker positions and no unresolved intents, then use an authorized path to clear the stop and restart the DEMO task. The new bridge must then undergo live read-only verification before dashboard controls are considered operational. No order was submitted for command-center testing.

The incident and exact narrow approval request are in
[`INCIDENT_2026-10-23.md`](INCIDENT_2026-10-23.md) and
[`SAFETY_STOP_APPROVAL_REQUEST.md`](SAFETY_STOP_APPROVAL_REQUEST.md). The
recovery branch keeps dashboard changes in a separate worktree. Its web
process imports the reviewed control protocol from its own release and writes
command requests only under `AA-AT-command-center-state`; it reads the
campaign ledger in SQLite read-only mode. A stale status is displayed as stale,
with zero workers described as currently active. The stored 227 closes remain
historical broker evidence, not proof of present broker connectivity. These
recovery-branch changes are staged and must not be mistaken for deployed
trading-service code.
