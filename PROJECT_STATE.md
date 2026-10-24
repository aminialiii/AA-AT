# Project state

Research/backup update, 2026-10-23 21:32 UTC: a separate `aa-at-research-collector`
task is healthy and has imported 395 broker-reconciled closed position lifecycles
with zero unresolved strategy attributions. The immutable local warehouse and
redacted export are outside Git. The dataset has no verified candle or tick
coverage for those positions, so trade charts, Bid/Ask execution analysis,
and MFE/MAE are unavailable rather than estimated. The separate dashboard
release `AA-AT-dashboard-release-research-v1` serves authenticated journal
and backup views at `http://127.0.0.1:8765/`. The three-slot backup worker is
running; V1, V2, and V3 are verified. V3 includes the research warehouse and
deployed dashboard release, with 8,302 raw research artifacts reconciled.
Eight V3 SQLite images passed an isolated restore drill. Both scheduled
research/backup tasks start at user sign-in, not before login. See
[trade forensics](docs/TRADE_FORENSICS.md) and
[backup recovery](docs/BACKUP_RECOVERY.md). The latest trading-service
heartbeat reports broker `SUSPENDED` on inconsistent quote/clock freshness;
new routing remains fail-closed, while the trading task itself remains running.
No trading workers, signal rules, risk limits, positions, or pending orders
were changed by this research work.
The four-hour Git sync task remains separate. Its expected remote branch SHA
was recovered from its append-only audit record and checked against the remote
tip. The sync worker now preserves that value across retries. On 2026-10-24
03:01 UTC, a normal quiet-source cycle passed 25 offline tests and secret
scanning, then pushed 19 changed files to the review branch at
`300d81b6c7cf78892aade575fd4f512b72b6b22c` (PR #1). No force push or
automated deployment occurred. The original checkout's dashboard projection
and isolated test fixtures were brought into line with the separately tested
dashboard source to restore this validation; no trading service files or
workers were changed for that repair.

Current operational update, 2026-10-23: the administrator reportedly approved
clearing the maintenance stop; the marker was found absent. A minimal risk-only
hotfix now reloads S04's existing fill-risk breaker from durable safety events
before workers start. After a fresh read-only DEMO preflight and reconciliation
of all 454 deal IDs for 227 closes, the trading task was enabled and started.
Its fresh broker-reconciled status reports S01–S03 and S05 `ACTIVE`, S04
`BLOCKED`, S06–S18 `BLOCKED`, and the unchanged five-slot/2% portfolio policy.
Two genuine broker-owned, SL/TP-protected positions were reconciled to durable
intents after restart. A subsequent S02 close was matched to broker deals,
raising verified closes from 227 to 228. This is a point-in-time check;
positions may change as market signals occur. An independent approval decision
ID was not available. See [the incident record](docs/INCIDENT_2026-10-23.md).

Dashboard recovery is isolated in Git worktree/branch
`recovery/incident-20261023`. Dashboard-only release `a5a338e` is running
independently on loopback. It keeps its command store outside the trading
runtime, marks stale broker and worker data explicitly, and blocks controls
while the bridge or stop state is unresolved. It passed 24 offline tests,
a separate-port smoke check, and post-release authenticated data checks.
The candidate trading bridge was not deployed. The dashboard does not directly
control the running trading service. Its separate release did not alter the
trading task or ledger; the later risk-only runtime hotfix is documented
separately in the incident record.

Incident history: command-bridge maintenance originally stopped trading, and
automatic approval review denied the agent's attempt to remove the stop
marker. The pre-deployment service version was restored. The marker later
disappeared outside this agent's file operations. The user reported an admin
choice approving clearance; no decision record was independently located.

Checkpoint: 2026-10-22 Asia/Tehran. Source of truth for operational facts is the local DEMO service ledger and broker reconciliation, not this static document.

- Private GitHub repository: `aminialiii/AA-AT`; initial screened source snapshot pushed to `main`. Four-hour synchronization task installed; its first no-change run and first scheduled changed run passed validation, secret scanning, and push to the review branch.
- Original workspace: `E:\GPT\Inves`; it had no `.git` directory at migration. Original research files and current runtime remain in place.
- DEMO campaign: Task Scheduler `CodexDemoForward20261021` is running. Four M1 workers (S01–S03 and S05) are active; S04 is independently blocked by a persisted fill-risk breaker, and S06–S18 lack verified executable paths. One hundred verified closed trades per strategy is an initial evaluation minimum, with no automatic trade-count stop. The nominal initial milestone is 1,800; the four currently eligible workers have a combined initial minimum of 400.
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
