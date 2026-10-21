# Project state

Checkpoint: 2026-10-22 Asia/Tehran. Source of truth for operational facts is the local DEMO service ledger and broker reconciliation, not this static document.

- Private GitHub repository: `aminialiii/AA-AT`; initial screened source snapshot pushed to `main`. Four-hour synchronization task installed and its first no-change run passed.
- Original workspace: `E:\GPT\Inves`; it had no `.git` directory at migration. Original research files and current runtime remain in place.
- DEMO campaign: Task Scheduler `CodexDemoForward20261021`; five eligible M1 workers (S01–S05), thirteen blocked (S06–S18). Current target is 100 verified closed trades per strategy. The nominal total is 1,800; current eligible total is 500.
- Frozen strategy implementation: `research/overnight-20261010/engine.py` with a recorded SHA-256 and registration manifest. The account-bound campaign configuration and broker evidence are local-only.
- DEMO trade progress and current protected positions are in [CHECKPOINT.json](CHECKPOINT.json) and [the timestamped status snapshot](docs/operational_status.json). Counts change as genuine signals close; the broker ledger remains the local source of truth.
- Graphify: full prior versions remain in the original workspace. A separate account-free development graph has 194 nodes and 516 directed relationships with line-matched source evidence and zero duplicate identities or missing endpoints. It covers selected code and a broker-ledger-checked status snapshot, not the entire project.
- Draft review PR: `https://github.com/aminialiii/AA-AT/pull/1` on `automation/source-sync`. It has not been merged or deployed.
- An official Codex heartbeat is scheduled for checkpoint follow-up. Trading, reconciliation, and Git synchronization do not depend on it or on remaining Codex quota.
- No live-money order is authorized or expected. No backtest, replay, or synthetic execution is part of this campaign.

The current service uses the previously authorized limits: 0.25% planned risk per trade (including cost reserve), 1% aggregate open/pending risk, 1% daily equity-loss halt, 2% peak-equity drawdown halt, one position per strategy, two positions per shared account, and one same-symbol exposure unless independently verified safe. It fails closed on account or reconciliation uncertainty.

Operational limitation: the broker feed has intermittently failed the quote/clock freshness gate. The service suspends all new routing on each failure and has recovered automatically. This reduces campaign availability and merits investigation without relaxing the fail-closed check.

MCP limitation: the terminal bridge listens locally but returns HTTP 401 Bearer authentication; the MetaEditor bridge is not listening. The required MCP authorization is not available in this chat. Direct terminal Python access is verified and used by the service, so this does not block the five eligible workers.

Persistence boundary: the DEMO and Git synchronization tasks run as the interactive Windows user. They survive the Codex session and restart after that user logs on, but operation before login after a reboot is not verified because MetaTrader and Git Credential Manager rely on the user session. No credential was embedded in a service or repository to bypass that boundary.
