# Project state

Checkpoint: 2026-10-22 UTC. Source of truth for operational facts is the local DEMO service ledger and broker reconciliation, not this static document.

- Private GitHub repository: `aminialiii/AA-AT`, created; initial secure source snapshot and synchronization are being installed.
- Original workspace: `E:\GPT\Inves`; it had no `.git` directory at migration. Original research files and current runtime remain in place.
- DEMO campaign: Task Scheduler `CodexDemoForward20261021`; five eligible M1 workers (S01–S05), thirteen blocked (S06–S18). Current target is 100 verified closed trades per strategy. The nominal total is 1,800; current eligible total is 500.
- Frozen strategy implementation: `research/overnight-20261010/engine.py` with a recorded SHA-256 and registration manifest. The account-bound campaign configuration and broker evidence are local-only.
- Last checked broker report: 19 reconciled closed DEMO trades and two protected open positions; account verified DEMO and service reported healthy. This number will change as genuine signals occur.
- Existing Graphify: source and prior versions remain in the original workspace. The development graph in this repository must exclude sensitive account/runtime data.
- No live-money order is authorized or expected. No backtest, replay, or synthetic execution is part of this campaign.

The current service uses the previously authorized limits: 0.25% planned risk per trade (including cost reserve), 1% aggregate open/pending risk, 1% daily equity-loss halt, 2% peak-equity drawdown halt, one position per strategy, two positions per shared account, and one same-symbol exposure unless independently verified safe. It fails closed on account or reconciliation uncertainty.
