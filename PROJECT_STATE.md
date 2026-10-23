# Project state

Recovery investigation on 2026-10-23: the trading stop was a deliberate
command-center bridge maintenance stop, not a broker or portfolio-risk halt.
The prior service source was restored and remains disabled behind the intact
stop marker. A fresh, read-only DEMO terminal check found zero open/pending
exposure; all 454 broker deal IDs and net PnL supporting the 227 local closes
matched. This is a point-in-time result, not permission to resume. S04's
fill-risk breaker is not rehydrated by the restored service on restart, so a
minimal persistent admission guard is an additional restart gate. See
[the incident record](docs/INCIDENT_2026-10-23.md).

Dashboard recovery is isolated in Git worktree/branch
`recovery/incident-20261023`. Dashboard-only release `a5a338e` is running
independently on loopback. It keeps its command store outside the trading
runtime, marks stale broker and worker data explicitly, and blocks controls
while the bridge or stop state is unresolved. It passed 24 offline tests,
a separate-port smoke check, and post-release authenticated data checks.
The candidate trading bridge was not deployed. The trading task, stop marker,
service source, and 227-trade ledger remained unchanged.

Operational change on 2026-10-23: `AAATCommandCenter` is running on loopback with authenticated live telemetry and all 18 worker views. The campaign was stopped during a zero-exposure maintenance window to deploy the command bridge. Automatic approval review rejected removal of the local `EMERGENCY_STOP` file, so the campaign task remains disabled. The previous trading `service.py` was restored from `AA-AT-command-center-state/rollback/20261023T0135/service.py`; no orders were submitted for dashboard testing. The account-free repository contains the tested bridge candidate, but the running campaign has **not** activated it. A local human safety review and authorized stop clearance are required before trading resumes. The local ledger held 227 reconciled closes at the stop.

Checkpoint: 2026-10-22 Asia/Tehran. Source of truth for operational facts is the local DEMO service ledger and broker reconciliation, not this static document.

- Private GitHub repository: `aminialiii/AA-AT`; initial screened source snapshot pushed to `main`. Four-hour synchronization task installed; its first no-change run and first scheduled changed run passed validation, secret scanning, and push to the review branch.
- Original workspace: `E:\GPT\Inves`; it had no `.git` directory at migration. Original research files and current runtime remain in place.
- DEMO campaign: Task Scheduler `CodexDemoForward20261021`; five historically executable M1 workers (S01–S05). S04 is now independently blocked by a fill-risk breaker, and S06–S18 lack verified executable paths. S01–S03 and S05 are stopped by the global maintenance marker. One hundred verified closed trades per strategy is an initial evaluation minimum, with no automatic trade-count stop. The nominal initial milestone is 1,800; the four currently eligible workers have a combined initial minimum of 400.
- Frozen strategy implementation: `research/overnight-20261010/engine.py` with a recorded SHA-256 and registration manifest. The account-bound campaign configuration and broker evidence are local-only.
- DEMO trade progress and current protected positions are in [CHECKPOINT.json](CHECKPOINT.json) and [the timestamped status snapshot](docs/operational_status.json). Counts change as genuine signals close; the broker ledger remains the local source of truth.
- Graphify: full prior versions remain in the original workspace. A separate account-free development graph has 304 nodes and 814 directed relationships with line-matched source evidence and zero duplicate identities or missing endpoints. It covers selected code, the versioned policy dependency, and a timestamped broker-ledger-checked status snapshot, not the entire project or current trading activity.
- Draft review PR: `https://github.com/aminialiii/AA-AT/pull/1` on `automation/source-sync`. It has not been merged or deployed.
- An official Codex heartbeat is scheduled for checkpoint follow-up. It is subject to app availability and usage limits; it is not a guaranteed quota-reset wakeup. Trading, reconciliation, and Git synchronization do not depend on it or on remaining Codex quota.
- No live-money order is authorized or expected. No backtest, replay, or synthetic execution is part of this campaign.

The current service uses a separate versioned [continuous DEMO risk policy](docs/CONTINUOUS_DEMO_POLICY.md): 0.25% planned risk per trade (including cost reserve), 2% aggregate open/pending risk, 1% daily equity-loss halt, 2% peak-equity drawdown halt, one position per strategy, five global open-or-pending slots, and one same-symbol exposure unless independently verified safe. The original strategy/campaign configuration hash remains frozen. The policy became operational after read-only DEMO hedging, permission, quote, native-margin, ownership, and open-risk checks; the local ledger records its policy version. It fails closed on account or reconciliation uncertainty.

Operational limitation: the broker feed has intermittently failed the quote/clock freshness gate. The service suspends all new routing on each failure and recovers automatically. A stale quote during the first policy restart briefly halted the process; the recovery path now keeps an already verified campaign running in SUSPENDED state until fresh quotes and exposure checks pass. New or unverified campaigns still fail startup. This reduces campaign availability and merits investigation without relaxing the fail-closed check.

MCP limitation: the terminal bridge listens locally but returns HTTP 401 Bearer authentication; the MetaEditor bridge is not listening. The required MCP authorization is not available in this chat. Direct terminal Python access is verified and used by the service, so this does not block the five eligible workers.

Persistence boundary: the DEMO and Git synchronization tasks run as the interactive Windows user. They survive the Codex session and restart after that user logs on, but operation before login after a reboot is not verified because MetaTrader and Git Credential Manager rely on the user session. No credential was embedded in a service or repository to bypass that boundary.
