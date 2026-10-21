# Documentation and configuration evidence review

Reviewed 2026-10-21. This is a semantic/document review, not executable behavior verification. No trading scripts, backtests, optimization, services, market-data collection, or order tools were executed. Static file reads and generation of this report/graph fragment only.

## Scope and limitations

23 selected first-party documents/configurations were read for semantic extraction. Raw ticks, NPZ datasets, trade archives, live account state, external websites and full videos were not inspected. Historical results below are saved claims, not independently reproduced results. Source code review belongs to the parent review; configuration references alone cannot prove actual execution or enforcement. All graph edges below describe explicit references/claims, never imports, calls, runtime data flow, or actual service status.

## Distinct documentation-only methods

- Exact teacher SP2L: directional spike + verified P-Gap + correction + second leg; source summary says SL behind spike-origin candle, default1R and optional addition halfway to stop. P-Gap, spike boundary, final trigger/order type and invalidation are unresolved. An agent gap interpretation at2R is a different numerical hypothesis, not source replication.
- Exact teacher Pro BTB: important-level breakout and return to breakout close/broken level, six buy-mode descriptions B1-B6, stop behind structure, minimum2R. Key-level validity, breakout validity, distinctions B2/B3/B6, and sell mirror remain unquantified. BREAK_RETEST code is not automatically this exact method.
- Exact teacher MicroMAP: spike/countertrend microchannel, last-bar H1 break; up to3attempts with invalidation after3stops; separate H2/H3 and inside-bar descriptions. Numeric spike/channel, counting, timing, TP and sell mirror remain unresolved. Registered buy-only numerical MicroMAP is a separate agent interpretation with one attempt and2R.
- Time analysis is a contextual filter, not independent entry strategy: reference UTC+03, gold10-13/15:30-16:30/16:30-18, US30 16:30-18/18-21/21-23, EURUSD after10. It cannot be counted as an implemented buy/sell strategy. H1 in MicroMAP entry naming means first high-break attempt, not necessarily H1 chart timeframe.
- Coin-toss/risk, correct-trading psychology, capital-allocation videos and Map Manager are themes/utilities, not implemented strategies. No complete seven-video viewing is established. Research skill README explicitly says it is not a live engine.
- Fast-scalp proposal JSON bundles SP2L_FAST, PRO_BTB_RETEST and MICROMAP_CONFIRM; implementation cannot be established from these descriptions or enabled=true alone. Preserve these as proposal variants unless code review establishes matching reachable implementations.

## Material contradictions requiring code-path verification

1. **High: canonical suspension versus legacy launch narratives.** Trading_Manager_Config.json is enabled=false, automation_execution_allowed=false, current_turn_bounded_demo_execution_authorized=false, and has active direct_user_demo_suspension/all_work_suspension. Trading_Workflow_Overrides.md still says recurring automation was approved. ACTIVE_RESEARCH.md still asks to keep a research heartbeat active. Latest user request permits this static review only. No operational resumption was performed.
2. **High: model-path/version mismatch.** Canonical config version is seven-symbol RR2 no-news momentum with .skill-tools/rr2-parallel.js, but model_path points to buy-only MicroMAP all-symbol model. Its60second hold and all-broker-symbol universe conflict with current exact seven symbols and broker SL/TP-only/no timed-close policy. Determine effective helper use before freezing tests; do not silently merge these into one strategy.
3. **Medium: stale risk policy.** Installed manager operating contract describes1%active/10%hard/2%DD/one-position controls. Current config records demo waiver and null financial caps, broker-minimum volume, one position/order per symbol. Earlier event JSON has1%active/5%hard/2%DD and max4entries. These are version-specific policies, not one reliable default.
4. **Medium: news mismatch.** Workflow override narrative requires relevant fresh calendar; config has news_filter_enabled=false. Legacy event evaluator news blocks are another independent policy. A configured value is not proof a helper enforces it.
5. **Medium: quote-side error in proposal.** Fast-scalp JSON risk_and_execution.quote says ask for sell risk and bid for buy risk. Executable market entry is sell bid/buy ask; liquidation/stop side differs. Verify implementation before treating this prose as actual bug.
6. **Medium: source-method attribution.** SP2L source summary1R versus experimental2R; unresolved P-Gap versus explicit real-gap numeric proxy; original MicroMAP3attempts versus numerical one-attempt buy-only implementation. Catalog separately rather than implying teacher-exact behavior.
7. **Medium: stale research runbook.** ACTIVE_RESEARCH.md describes first extension stage completed and next stage pending, while extension state lists all35stages complete. State paths/results must be checked, not inferred from old prose.
8. **Medium: historical timezone assumption.** Overnight plan states measured180minute broker offset applied to July-September archive without independently proving historic consistency. Session claims remain conditional. This differs from Asia/Tehran UTC+03:30 blackout.

## Existing research provenance and limitations

- Intraday continuation artifact saved REJECT across8training parameter presets; selected pullback_a1_r2 validation130trades, net-12.3774, PF0.7390; guarded8trades and2.5444balance drawdown. Holdout marked untouched in that old artifact, but do not claim it remains untouched across later research. Saved results were read, not recomputed.
- RSI frozen artifact saved REJECT: Jan1-Apr1 2026 training40trades, net-1.7845, PF0.8793; validation not computed due negative training. Guarded sample9trades. Not fresh evidence of any current configuration.
- MicroMAP source-method decision artifact says6historical setups/0risk-eligible trades under old rules; source methods indeterminate. Later all-symbol model explicitly warns earlier2gold simulated losses and technical calibration are not multiasset OOS validation.
- Overnight registered initial280configurations:5families ×8parameter/session presets ×7symbols. Final narrative says448comparisons after M5 research additions; do not mislabel280/448 as distinct strategies. Jul9-Aug14train, Aug14-26validation, Aug26-Sep8holdout2026. Frozen combined selection chooses models using development-only gate/score, with n>=50 and M1 tie preference.
- Final overnight summary reports no candidate passed registered acceptance. XAUUSD RANGE_REJECTION M1:67closes,40.3%wins,E0.168R,PF1.268,DD7.060R; bootstrap expectancy interval approx[-0.084,0.393]includes0 and train expectancy negative. Other selected results: EURUSD14closes14.3%wins E-0.842R; GBPUSD79/21.5%/-0.678R;USDJPY50/26%/-0.503R;USDCHF183/27.9%/-0.488R;USDCAD56/41.1%/-0.169R;AUDUSD54/29.6%/-0.438R. These are saved simulated outputs, not live fills or validated profits.
- Fixed1R aggregate is explicitly not actual equity or capital-feasible portfolio. EURUSD only14exits over3independent days; two censored trades excluded from win rate; incomplete tick coverage and hypothetical costs limit execution realism.
- Backtest-only program01 releases Sep9-Oct7 for the same seven frozen model choices, five cost scenarios, no new search. Its state lists35completed stages. Extension Oct8 00UTC-Oct9 20UTC repeats fixed choices; only2entry dates partly exposed to prior demo observations, thus retrospective diagnostic. Five cost scenarios on same data are not five independent samples. Extension state also lists35completed stages. No hash reconciliation of those result receipts was performed in this subreview.
- Registered live broker-only exits and sampled native-tick momentum are not the same event process as offline next-bar OHLC signals. Neither old backtest result nor calibration trades prove live-model profitability.

## Semantic graph audit

84nodes,65edges across23source files. Every edge EXTRACTED with score1.0 means the reference/claim is explicit in the document, **not runtime truth**. All nodes/edges stamped _origin=semantic and claim_scope=documented_intent_or_saved_artifact_not_runtime_verification. Evidence text and L-line references are attached. No invented calls, imports or inferred live order flow. IDs are deterministic path-and-label names. Token counts0 are placeholders because tool did not expose measured agent usage; this does not claim zero LLM cost. The parent build should report token usage unknown.

## Evidence index

- [Canonical trading manager configuration](E:/GPT/Inves/Trading_Manager_Config.json:1)
- [MicroMAP all-symbol agent model registration](E:/GPT/Inves/research/poursamadi-backtest/model-all-symbols-v1.json:1)
- [Workflow override narrative](E:/GPT/Inves/Trading_Workflow_Overrides.md:1)
- [Legacy event range rules](E:/GPT/Inves/Demo_Entry_Rules_20261007.json:1)
- [Dynamic risk event preset](E:/GPT/Inves/Demo_Entry_Rules_20261008_DYNAMIC.json:1)
- [Fast scalp proposal bundle](E:/GPT/Inves/Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json:1)
- [Source-method MicroMAP description](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/04-micromap.md:1)
- [Source-method SP2L description](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/05-sp2l.md:1)
- [Source-method Pro BTB description](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/06-pro-btb.md:1)
- [Time analysis contextual filter](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/02-time-analysis.md:1)
- [Supplemental risk guidance](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/08-risk-and-execution.md:1)
- [Research skill package status](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/README.md:1)
- [Unvalidated SP2L research proposal](E:/GPT/Inves/Poursamadi_Candidate_Research_1.json:1)
- [Gold MicroMAP numerical model](E:/GPT/Inves/research/poursamadi-backtest/model-v1.json:1)
- [Teacher replication decision artifact](E:/GPT/Inves/research/poursamadi-backtest/source-method-decision-v1.json:1)
- [Registered overnight research grid](E:/GPT/Inves/research/overnight-20261010/plan.json:1)
- [Frozen combined M1 M5 selection](E:/GPT/Inves/research/overnight-20261010/frozen_combined_selection_20261009T224018184056Z.json:1)
- [Overnight historical result summary](E:/GPT/Inves/research/overnight-20261010/FINAL_SUMMARY_20261010T052334635887Z.md:1)
- [Fixed Sep9 Oct7 diagnostic registration](E:/GPT/Inves/research/backtest-only-20261010/plan.json:1)
- [Offline research runbook](E:/GPT/Inves/research/backtest-only-20261010/ACTIVE_RESEARCH.md:1)
- [Active program pointer](E:/GPT/Inves/research/backtest-only-20261010/active_program.json:1)
- [Continuation historical diagnostic](E:/GPT/Inves/Intraday_Continuation_Research_20261007.json:1)
- [RSI historical diagnostic](E:/GPT/Inves/Intraday_RSI_Frozen_Research_20261007.json:1)

## Specific corrected claim evidence

- [Seven symbol RR2 configuration](E:/GPT/Inves/Trading_Manager_Config.json:2): Version DEMO_7_SYMBOLS_RR2_NO_NEWS_5; configuration is disabled.
- [Demo disabled](E:/GPT/Inves/Trading_Manager_Config.json:3): Configured false; not evidence of every standalone helper enforcing this.
- [Risk waiver null caps](E:/GPT/Inves/Trading_Manager_Config.json:41): Percentage risk, drawdown, entries and position financial caps are null.
- [Configured MicroMAP model path](E:/GPT/Inves/Trading_Manager_Config.json:54): Model path names old all-symbol buy-only MicroMAP interpretation; helper wiring must decide actual behavior.
- [RR2 execution helper reference](E:/GPT/Inves/Trading_Manager_Config.json:81): References .skill-tools/rr2-parallel.js.
- [Broker only exits](E:/GPT/Inves/Trading_Manager_Config.json:196): BROKER_SL_TP_ONLY; manual close false; no trailing/time close intended.
- [Managed limit expiry](E:/GPT/Inves/Trading_Manager_Config.json:212): 45 second application-managed limit validity.
- [News disabled](E:/GPT/Inves/Trading_Manager_Config.json:216): Current config disables news filter despite older text requiring it.
- [Automation disabled](E:/GPT/Inves/Trading_Manager_Config.json:202): No recurring order authorization in current canonical config.
- [All work suspended](E:/GPT/Inves/Trading_Manager_Config.json:252): Historical suspension flag remains; current review request permits static review only.
- [Tehran entry blackout](E:/GPT/Inves/Trading_Manager_Config.json:234): 23:00 inclusive to01:30 exclusive Asia/Tehran intended new-entry block.
- [Buy-only MicroMAP interpretation](E:/GPT/Inves/research/poursamadi-backtest/model-all-symbols-v1.json:11): Buy only M1 model, native ticks entry; not teacher exact rules.
- [Normalized buffers](E:/GPT/Inves/research/poursamadi-backtest/model-all-symbols-v1.json:28): Two native ticks entry/SL buffer; replaces gold dollar units.
- [Old sixty-second hold limit](E:/GPT/Inves/research/poursamadi-backtest/model-all-symbols-v1.json:41): 60 sec old model definition conflicts with current broker SL/TP-only config.
- [Unvalidated all-symbol claim](E:/GPT/Inves/research/poursamadi-backtest/model-all-symbols-v1.json:4): Prospective unvalidated; old gold evidence does not validate all markets.
- [Outdated news narrative](E:/GPT/Inves/Trading_Workflow_Overrides.md:14): Narrative says fresh calendar required; JSON says news disabled.
- [Outdated automation narrative](E:/GPT/Inves/Trading_Workflow_Overrides.md:17): Historical approval statement; newer current JSON disabled and suspended.
- [Frozen FOMC range](E:/GPT/Inves/Demo_Entry_Rules_20261007.json:30): Three completed M5 bars after release; freeze high/low.
- [Separate breakout retest confirmation](E:/GPT/Inves/Demo_Entry_Rules_20261007.json:34): First closed M1 after retest must break previous M1 high/low directionally.
- [Event management rules](E:/GPT/Inves/Demo_Entry_Rules_20261007.json:40): 1R breakeven;1.7R lock1R;60min/event end/news exits intended.
- [Legacy fixed size](E:/GPT/Inves/Demo_Entry_Rules_20261007.json:14): 0.01lot; max2entries;1position;1%risk;2%DD;2losses.
- [Dynamic sizing proposal](E:/GPT/Inves/Demo_Entry_Rules_20261008_DYNAMIC.json:17): Preserves event signal but uses contract-aware flooring and4entry cap.
- [Prospective event anchor](E:/GPT/Inves/Demo_Entry_Rules_20261008_DYNAMIC.json:41): FOMC2026-10-28 prospective anchor stored; event not independently verified in this review.
- [SP2L fast proposal](E:/GPT/Inves/Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json:34): Numeric three-bar real gap interpretation differs from unresolved source P-Gap.
- [Pro BTB proposal](E:/GPT/Inves/Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json:41): Six styles described but mutual exclusivity and level definitions need executable verification.
- [MicroMAP tiers proposal](E:/GPT/Inves/Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json:48): H1/H2/H3 tiers plus inside bar described; do not infer implementation.
- [Reversed quote risk prose](E:/GPT/Inves/Demo_Entry_Rules_20261008_POURSAMADI_FAST_SCALP_1.json:29): Text says ask for sell risk and bid for buy risk; executable entry should use sell bid/buy ask.
- [MicroMAP incomplete definitions](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/04-micromap.md:34): Numeric spike, channel, H2/H3, TP and sell mirror unresolved.
- [MicroMAP three attempts](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/04-micromap.md:31): Source-method description invalidates after3stops; not same as one-attempt agent model.
- [Unresolved P-Gap](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/05-sp2l.md:26): P-Gap not executable; do not identify as classical/FVG gap silently.
- [Source SP2L target](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/05-sp2l.md:16): Source default1R, unlike RR2 agent research interpretation.
- [Pro BTB six modes](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/06-pro-btb.md:17): B1-B6 examples buy only; level/breakout validity unresolved.
- [Unverified Pro BTB sell mirror](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/06-pro-btb.md:27): Sell mirror is interpretation/unverified, not exact source replication.
- [Time context not signal](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/02-time-analysis.md:40): Time windows contextual, not standalone buy/sell strategy.
- [Fixed UTC3 reference](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/02-time-analysis.md:13): Separate documented reference offset from historical broker offset and Tehran timezone.
- [Unspecified financial defaults](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/08-risk-and-execution.md:19): Risk parameters listed without numerical defaults; not implemented portfolio policy.
- [Map Manager utility](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/references/08-risk-and-execution.md:23): Execution-management utility described, not autonomous signal strategy.
- [Not a live engine](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/README.md:3): Research skill package only; copying files does not install/activate trading.
- [Videos not fully reviewed](E:/GPT/Inves/research/poursamadi-v0.9/poursamadi-trading-agent-skill/README.md:7): Written source summaries and metadata; no full seven-video viewing claim.
- [SP2L disabled incomplete](E:/GPT/Inves/Poursamadi_Candidate_Research_1.json:5): Research-only proposal explicitly disabled and mechanical definitions unresolved.
- [Numerical agent hypotheses](E:/GPT/Inves/research/poursamadi-backtest/model-v1.json:5): False teacher-exact claim;2spike candles body>=.65 close>=.75 total>=2ATR;2-5channel bars;2R.
- [Gold research splits](E:/GPT/Inves/research/poursamadi-backtest/model-v1.json:77): Sep8-22train,Sep22-Oct1validation,Oct1-8test2026; saved historical split, not fresh holdout.
- [Teacher methods indeterminate](E:/GPT/Inves/research/poursamadi-backtest/source-method-decision-v1.json:46): SP2L/ProBTB/MicroMAP/TIME unresolved; no exact source-method execution validation.
- [M1_MOMENTUM_PROXY](E:/GPT/Inves/research/overnight-20261010/plan.json:91): Registered family; eight parameter/session presets per family, seven symbols; implementation requires engine inspection.
- [BREAK_RETEST](E:/GPT/Inves/research/overnight-20261010/plan.json:155): Registered family; eight parameter/session presets per family, seven symbols; implementation requires engine inspection.
- [TREND_PULLBACK](E:/GPT/Inves/research/overnight-20261010/plan.json:219): Registered family; eight parameter/session presets per family, seven symbols; implementation requires engine inspection.
- [RANGE_REJECTION](E:/GPT/Inves/research/overnight-20261010/plan.json:283): Registered family; eight parameter/session presets per family, seven symbols; implementation requires engine inspection.
- [SP2L_AGENT_INTERPRETATION](E:/GPT/Inves/research/overnight-20261010/plan.json:347): Registered family; eight parameter/session presets per family, seven symbols; implementation requires engine inspection.
- [Chronological research partitions](E:/GPT/Inves/research/overnight-20261010/plan.json:75): Jul9-Aug14train;Aug14-26validation;Aug26-Sep8holdout2026.
- [Historical offset assumption](E:/GPT/Inves/research/overnight-20261010/plan.json:425): Measured180min offset extrapolated to historical archive without independent validation.
- [Development-only model ranking](E:/GPT/Inves/research/overnight-20261010/frozen_combined_selection_20261009T224018184056Z.json:4): Registered gate otherwise validation expectancy-.15DD/n with n>=50; ties M1.
- [Normalized R not portfolio](E:/GPT/Inves/research/overnight-20261010/frozen_combined_selection_20261009T224018184056Z.json:57): Fixed1R per trade, not actual equity or capital-feasible portfolio.
- [No candidate passed acceptance](E:/GPT/Inves/research/overnight-20261010/FINAL_SUMMARY_20261010T052334635887Z.md:27): Summary reports no candidate passed; not independently recomputed.
- [Gold positive uncertain point estimate](E:/GPT/Inves/research/overnight-20261010/FINAL_SUMMARY_20261010T052334635887Z.md:32): XAU67closes40.3%win;E.168R;bootstrap includes0; not proven profitability.
- [Fixed prior model choices](E:/GPT/Inves/research/backtest-only-20261010/plan.json:13): Seven prior choices reused with cost scenarios; no new model search.
- [Released prior quarantine](E:/GPT/Inves/research/backtest-only-20261010/plan.json:12): Sep9-Oct7 separate historical block; now exposed, not fresh untouched OOS.
- [Retrospective extension limitations](E:/GPT/Inves/research/backtest-only-20261010/ACTIVE_RESEARCH.md:25): Oct8-9 only2entry dates partly seen in demo; hypothetical costs and unverified tick path.
- [Old launchers prohibited](E:/GPT/Inves/research/backtest-only-20261010/ACTIVE_RESEARCH.md:27): Runbook warns old overnight cycle.js/release.py must not resume demo.
- [Offline extension helper reference](E:/GPT/Inves/research/backtest-only-20261010/active_program.json:6): Pointer identifies extension cycle.py; static reference is not evidence currently running.
- [Rejected continuation trials](E:/GPT/Inves/Intraday_Continuation_Research_20261007.json:3): Saved decision REJECT; eight training presets, selected pullback validation negative; not recomputed.
- [Rejected RSI training](E:/GPT/Inves/Intraday_RSI_Frozen_Research_20261007.json:2): Saved REJECT;40training trades PF.8793 net-1.7845;validation not computed;not recomputed.
