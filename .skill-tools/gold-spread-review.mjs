import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {evaluateGold} from './gold-evaluate.mjs';
const ROOT='E:/GPT/Inves',journal=path.resolve(ROOT+'/trading-journal');
function journalRead(p){const full=path.resolve(p),rel=path.relative(journal,full);if(rel.startsWith('..')||path.isAbsolute(rel))throw Error('research_path_rejected');return JSON.parse(fs.readFileSync(full,'utf8'));}
export function observeSpreadResearch(snapshotPath){
 const state=JSON.parse(fs.readFileSync(ROOT+'/Trading_Manager_State.json','utf8')),queued=state.research_queue.find(q=>q.proposal_version==='GOLD_CONDITIONAL_SPREAD_FEASIBILITY_1');
 if(!queued)return {status:'skip',code:'no_registered_research'};
 const proposal=journalRead(queued.proposal_path),correction=journalRead(queued.registration_correction_path),x=journalRead(snapshotPath),cfg=JSON.parse(fs.readFileSync(ROOT+'/Trading_Manager_Config.json','utf8'));
 if(cfg.version!==proposal.activeTradingVersion)return {status:'skip',code:'research_version_changed'};
 const start=Date.parse(correction.holdout.startUTC),end=Date.parse(correction.holdout.endUTC),asof=Date.parse(x.observedUTC);
 if(asof<start)return {status:'skip',code:'before_registered_window'};
 const stamp=t=>Date.parse(t.time_ms+'Z')-x.offsetMinutes*60000,selected=x.ticks.filter(t=>stamp(t)>=start&&stamp(t)<end&&stamp(t)<=asof);
 if(!selected.length)return {status:'skip',code:'no_holdout_ticks'};
 const bands=proposal.frozenComparison.spreadUpperPriceBands,spreads=selected.map(t=>t.ask-t.bid).sort((a,b)=>a-b),signals=new Map();let screens=0,skips={};
 const step=15000,limit=Math.min(asof,end,stamp(x.ticks.at(-1))),replayStart=Math.max(start,Math.ceil(stamp(x.ticks[0])/60000)*60000+21*60000);
 const reference=journalRead(proposal.brokerEvidencePath),fixedBudget=reference.activeBudgetUSD;
 for(let now=Math.ceil(replayStart/step)*step;now<=limit;now+=step){const i=x.ticks.findIndex(t=>stamp(t)>=now);if(i<0||stamp(x.ticks[i])>=end)break;const tail=x.ticks[i],candidate=evaluateGold({ticks:x.ticks.slice(0,i+1),symbol:{...x.symbol,bid:tail.bid,ask:tail.ask},utc:new Date(stamp(tail)).toISOString(),offsetMinutes:x.offsetMinutes,config:cfg});screens++;
  if(candidate.status!=='analysis_ready'){skips[candidate.code]=(skips[candidate.code]??0)+1;continue;}
  if(Date.parse(candidate.setupUTC)<start||Date.parse(candidate.triggerUTC)>=end||signals.has(candidate.dedupKey))continue;
  const reserve=(cfg.slippage_reserve_price+cfg.spread_widening_reserve_price)*x.symbol.trade_contract_size*x.symbol.volume_min+cfg.round_trip_commission_per_lot*x.symbol.volume_min;
  const priceRisk=Math.abs(candidate.entry-candidate.structuralSL)*x.symbol.trade_contract_size*x.symbol.volume_min;
  const budget=fixedBudget;
  signals.set(candidate.dedupKey,{...candidate,spread:tail.ask-tail.bid,minimumVolumeEstimatedPriceRiskUSD:priceRisk,reserveAssumptionUSD:reserve,budgetUSD:budget,estimatedFits:priceRisk+reserve<=budget,exactNativeRiskAndMarginChecked:false});
 }
 const report={recordedUTC:new Date().toISOString(),proposalVersion:proposal.proposalVersion,proposalPath:queued.proposal_path,registrationCorrectionPath:queued.registration_correction_path,sourceSnapshot:snapshotPath,window:correction.holdout,replayStartUTC:new Date(replayStart).toISOString(),referenceBudgetUSD:fixedBudget,referenceBudgetSource:proposal.brokerEvidencePath,observedAsOfUTC:x.observedUTC,holdoutTicks:selected.length,spreadMedian:spreads[Math.floor((spreads.length-1)/2)],spreadP90:spreads[Math.floor((spreads.length-1)*.9)],bands:bands.map(upper=>({upperPrice:upper,tickShareAtOrBelow:spreads.filter(s=>s<=upper+1e-8).length/spreads.length,uniqueSignalCount:[...signals.values()].filter(s=>s.spread<=upper+1e-8).length,estimatedRiskFitCount:[...signals.values()].filter(s=>s.spread<=upper+1e-8&&s.estimatedFits).length})),screens,skipCounts:skips,uniqueSignals:[...signals.values()],exactNativeEligibilityCount:null,profitabilityTest:false,limitations:'Overlapping snapshot windows must be unioned by tick identity and dedupKey. Screens/ticks are serially correlated. Approximate linear risk uses the frozen pre-window account budget; actual historical per-tick equity and margin are not reconstructed. It is not native execution eligibility. Research uses only registered future-window ticks and setups with sufficient historical context; no active rule changes.'};
 const out=path.join(journal,'gold_spread_observation_'+path.basename(snapshotPath));
 try{fs.writeFileSync(out,JSON.stringify(report),{flag:'wx'});}catch(e){if(e.code==='EEXIST')return {status:'already_recorded',observationPath:out};throw e;}
 return {status:'recorded',observationPath:out,observedAsOfUTC:x.observedUTC,holdoutTicks:selected.length,uniqueSignals:signals.size,bands:report.bands};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)console.log(JSON.stringify(observeSpreadResearch(process.argv[2])));
