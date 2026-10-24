# Current strategy status

Account-free broker-ledger snapshot observed 2026-10-24T07:36:27.812588+00:00. This replaces the operational status in the earlier preapproval inventory; that document remains as historical provenance. Original rules and limitations are in the linked dossiers.

0 active and 14 blocked. 395 verified closed DEMO trades. The current eligible initial minimum is 400; the nominal all-strategy initial minimum is 1800. Neither is a maximum trade count.

|ID|Strategy|Current worker|Closed (initial minimum 100)|Implementation or blocker|Original-rule dossier|
|---|---|---|---:|---|---|
|S01|Range rejection|WAITING_BROKER|51|Blocker under review|[rules](../research_outputs/strategy_dossiers/S01.md)|
|S02|Trend pullback|WAITING_BROKER|115|Blocker under review|[rules](../research_outputs/strategy_dossiers/S02.md)|
|S03|Break/retest|WAITING_BROKER|76|Blocker under review|[rules](../research_outputs/strategy_dossiers/S03.md)|
|S04|Momentum proxy|BLOCKED|152|Blocker under review|[rules](../research_outputs/strategy_dossiers/S04.md)|
|S05|SP2L numerical proxy|WAITING_BROKER|1|Blocker under review|[rules](../research_outputs/strategy_dossiers/S05.md)|
|S06|Aligned tick momentum RR2|BLOCKED|0|Current native path is disabled/stopped; managed GTC expiry depends on manager cancellation; new parallel isolation/risk policy unverified.|[rules](../research_outputs/strategy_dossiers/S06.md)|
|S07|MicroMAP buy interpretation|BLOCKED|0|Prior terminal-dependent version is incompatible with current manager; independent live adapter and frozen version needed.|[rules](../research_outputs/strategy_dossiers/S07.md)|
|S08|Gold short-bar break/retest|BLOCKED|0|Archived short-bar configuration and independent execution path are unavailable.|[rules](../research_outputs/strategy_dossiers/S08.md)|
|S09|Event-range retest|BLOCKED|0|Stored anchor expired; same-version anchor rollover can reuse prior range; no independently verified broker execution path.|[rules](../research_outputs/strategy_dossiers/S09.md)|
|S10|EMA continuation pullback|BLOCKED|0|Implicit prepared-data and indicator pipeline missing; simulation function is not a live worker.|[rules](../research_outputs/strategy_dossiers/S10.md)|
|S11|EMA continuation breakout|BLOCKED|0|Same missing prepared-data and indicator pipeline as S10.|[rules](../research_outputs/strategy_dossiers/S11.md)|
|S12|Frozen RSI reversal|BLOCKED|0|RSI period/smoothing and prepared input generation unspecified.|[rules](../research_outputs/strategy_dossiers/S12.md)|
|S13|Five-second exploration momentum|BLOCKED|0|Old version/protocol has changing exit policy and no isolated current live worker.|[rules](../research_outputs/strategy_dossiers/S13.md)|
|S14|Five-second exploration reversal|BLOCKED|0|Old reversal arm needs distinct frozen protocol/exit rule and isolated worker.|[rules](../research_outputs/strategy_dossiers/S14.md)|
|S15|Rolling M5/M1 retest|BLOCKED|0|Installed external evaluator/risk gate requires frozen dependency and gap-validation fix; current config incompatible.|[rules](../research_outputs/strategy_dossiers/S15.md)|
|S16|Exact SP2L|BLOCKED|0|Spike/P-Gap validity, entry timing and full short rule not mechanically specified.|[rules](../research_outputs/strategy_dossiers/S16.md)|
|S17|Exact Pro BTB|BLOCKED|0|Important-level definition and six-mode causal arbitration not implemented.|[rules](../research_outputs/strategy_dossiers/S17.md)|
|S18|Exact MicroMAP|BLOCKED|0|Spike/channel, attempt expiry, exceptions and final TP/short mechanics unresolved.|[rules](../research_outputs/strategy_dossiers/S18.md)|

An `ACTIVE` status is an observed worker state, not a claim that every market/session currently has a signal. S04 and S05 are numerical/proxy implementations and must not be conflated with exact educational rules. Broker orders and deals remain in local evidence storage.
