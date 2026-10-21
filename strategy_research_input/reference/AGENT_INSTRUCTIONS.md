# Operational Instructions for Codex Astra (`AGENT_INSTRUCTIONS.md`)

## Step 1: Ingestion & Context Initialization
1. Parse `manifest.json` and `sources/video_metadata.json` to load video identifiers (`VIDEO_01`..`VIDEO_06`) and tool metadata.
2. Load `concepts/knowledge_index.json` and `knowledge_graph/knowledge_graph.json` into memory to establish the dependency DAG.
3. Verify all 10 invariants listed in `handoff/CODEX_ASTRA_HANDOFF.md`.

## Step 2: Module Generation & Integration Workflow
Execute the tasks in `handoff/IMPLEMENTATION_BACKLOG.json` in strict topological order of their dependencies:
1. **`BACKLOG_01` (`LevelEngine`)**: Implement `WeeklyMapIndicator`, `PreviousDaySessionLevels`, and `RoundLevelsIndicator`.
2. **`BACKLOG_02` (`TimeEngine`)**: Implement `TimeStrategyEngine` (`GMT+3` normalization, 11 graded windows, 3 `US30` windows, 9 Master Time Points, 5-min warning, and EOD Temporal Stop-Loss).
3. **`BACKLOG_03` (`SpikeCycleEngine`)**: Implement `SP2LStrategyEngine`, `ProBTBStrategyEngine`, and `MicroMapStateMachine` (including nested `SP2L/BTB + MicroMap` mode).
4. **`BACKLOG_04` (`SignalScoringTriad`)**: Implement the 3-Witness Scorer (`Time + Level + Price Action`) and `ExhaustionGap / MTR` reversal override at `Weekly Map 2.0x` / Range Ceiling.
5. **`BACKLOG_05` (`RiskAndExecutionEngine`)**: Implement `MapManager` lot sizing, `10%` risk cap, `Risk Free` (`Entry + Spread`), `Half Close` (`50%` at `2R/3R`), `180s` hold-time guard, and `90%` pre-news/Pin-Bar exit.
6. **`BACKLOG_06` (`MQL5_Deployment`)**: Compile `Poursamadi_MapManager.mq5` and indicator modules for MetaTrader 5 Desktop (`X64 Regular` / `AVX2`).

## Step 3: Automated Verification Gate
Run the 10-test verification suite defined in `verification/verification_plan.md`. Do NOT mark integration complete unless all 10 deterministic tests pass with 0 errors.
