# AA AT

Autonomous AI Trading Research & DEMO Forward Testing Platform.

This private repository is the development copy of the existing `E:\GPT\Inves` research workspace. It preserves source and documentation without publishing broker identifiers, credentials, runtime logs, or trade evidence. The original workspace was not a Git repository at migration, so there was no original Git history to import. The operational service remains in the original workspace until a reviewed deployment explicitly promotes code from here.

The connected MetaTrader campaign is DEMO-only. Five of eighteen strategy workers have a frozen executable M1 path; thirteen lack a verified independent path. Runtime safety events can temporarily block additional workers. One hundred genuine, broker-reconciled closed trades per strategy is an initial evaluation minimum, not a trading stop. The nominal 1,800-trade milestone assumes all eighteen eventually become eligible; valid DEMO trading continues beyond it. Historical research is separate from forward evidence.

Start with [PROJECT_STATE.md](PROJECT_STATE.md), [NEXT_ACTIONS.md](NEXT_ACTIONS.md), [strategy catalog](research/project-review/STRATEGY_CATALOG.md), [continuous DEMO policy](docs/CONTINUOUS_DEMO_POLICY.md), and [operations plan](research/demo-forward-20261021/OPERATIONS_PLAN.md). The local campaign requires account-bound `campaign_config.json`, kept outside Git. The committed `campaign_config.example.json` is deliberately unroutable. A separate account-free risk-policy overlay changes portfolio limits without changing the frozen strategy definition.

The [current strategy inventory](docs/CURRENT_STRATEGY_STATUS.md), [Trading Command Center](docs/COMMAND_CENTER.md), and [Graphify report](graphify-out/GRAPH_REPORT.md) describe the current development architecture. The authenticated dashboard at `http://127.0.0.1:8765/` reads local broker-ledger-checked telemetry; raw order and deal evidence stays local. Dashboard controls remain unavailable until the live service reports a fresh, verified control bridge. The four-hour Task Scheduler sync uses `automation/source-sync` and a draft pull request; it never deploys running services.

The original environment had no Docker files or Docker deployment to migrate. A Windows Task Scheduler task runs the current campaign; service installation and order routing must pass the local DEMO guard and reconciliation checks. Nothing in this repository automatically deploys to MetaTrader.

For a separate local deployment, set the three environment inputs in [`.env.example`](.env.example) through your local environment or secret store, then run `tools/prepare_local_config.py`. It creates an ignored, account-bound config once and never overwrites a frozen campaign. Preparing that file does not prove account type or activate trading; the live preflight must verify broker DEMO identity and permissions. The current running campaign keeps its existing versioned local config.

The `.skill-tools` folder contains only screened legacy strategy and adapter source files needed by the S06–S15 dossiers; generated data, installed dependencies, and account-bound scripts were excluded. It is research provenance, not an activated execution path.
