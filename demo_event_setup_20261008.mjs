/**
 * Pure evaluator for the prospective US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1,
 * prospective/unvalidated. This 20261008 entry point is the operational
 * evaluator selected by the current cycle policy. The dynamic version still
 * requires a caller-supplied fresh eventAnchor; no legacy event window is
 * reused for a dynamic decision.
 * No I/O, orders, account mutations, dynamic parameter search or timers.
 * input = {nowUTC,dataAsOfUTC(request-start UTC before all history retrievals),
 * actualServerOffsetMinutes,symbol:MT5SymbolMetadata,quote:
 * {bid,ask,timestampUTC? or update_time(server-naive)},M5,M1,H1,state?,
 * account:{isDemo,connected,readOnly,equity,observedPeakEquity,currency,
 * openPositionCount,openOrderCount,newEntriesThisSession,closedLosses,
 * marginSufficient,unknownExecutionOutcome?}}.
 * Bars: {time(server-naive),open,high,low,close} or {timeUTC,...}.
 * Caller must persist returned state before execution and add immutableSignalKey
 * to state.filledKeys after confirmed execution, or rejectedKeys after rejection.
 */
export const FROZEN_RULES = Object.freeze({
 version:"US_FOMC_RANGE_RETEST_DEMO_1",mode:"controlled_demo_experiment",
 researchGatePassed:false,prespecifiedUTC:"2026-10-07T17:58:35Z",
 symbols:["EURUSD","GBPUSD","XAUUSD"],volume:.01,
 releaseUTC:"2026-10-07T18:00:00Z",windowStartUTC:"2026-10-07T18:15:00Z",
 windowEndUTC:"2026-10-07T20:15:00Z",entryCutoffUTC:"2026-10-07T20:29:31Z",
 deadlineUTC:"2026-10-07T20:59:31Z",
 blocks:[["2026-10-07T17:45:00Z","2026-10-07T18:15:00Z"],
 ["2026-10-07T18:45:00Z","2026-10-07T19:15:00Z"]]
});
// Prospective follow-on version. The entry pattern and gates stay frozen;
// only the risk budget and volume calculation are made contract-aware.
export const DYNAMIC_RULES = Object.freeze({
 ...FROZEN_RULES,
 version:"US_FOMC_RANGE_RETEST_DYNAMIC_RISK_1",
 dynamicVolume:true,
 maxNewEntries:4,
 maxSimultaneousPositions:1,
 activeRiskFraction:.01,
 hardRiskFraction:.05,
 drawdownHeadroomFraction:.02
});
export const REQUIRED_DYNAMIC_EVENT_ANCHOR_FIELDS = Object.freeze([
  "releaseUTC", "windowStartUTC", "windowEndUTC", "entryCutoffUTC", "blocksUTC"
]);
const BASE_RULES=FROZEN_RULES;
const MIN=60000, M5=5*MIN;
const iso=t=>new Date(t).toISOString();
const finite=x=>typeof x==="number"&&Number.isFinite(x);
function absolute(s){const t=Date.parse(s);return Number.isFinite(t)?t:null;}
function serverTime(s,offset){
 if(typeof s!=="string")return null;
 const m=/^(\d{4})[.-](\d{2})[.-](\d{2})[ T](\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z?$/.exec(s);
 if(!m)return null;
 const y=+m[1],mo=+m[2]-1,d=+m[3],h=+m[4],mi=+m[5],se=+m[6];
 const t=Date.UTC(y,mo,d,h,mi,se),v=new Date(t);
 if(v.getUTCFullYear()!==y||v.getUTCMonth()!==mo||v.getUTCDate()!==d||
 v.getUTCHours()!==h||v.getUTCMinutes()!==mi||v.getUTCSeconds()!==se)return null;
 return t-offset*MIN;
}
function normalize(bars,duration,offset,now,name){
 if(!Array.isArray(bars))return {error:name+"_missing"};
 const out=[];
 for(const b of bars){
  const t=b.timeUTC?absolute(b.timeUTC):serverTime(b.time,offset);
  if(t===null||!["open","high","low","close"].every(k=>finite(b[k]))||
   b.low>b.high||b.low>Math.min(b.open,b.close)||b.high<Math.max(b.open,b.close))
   return {error:name+"_malformed"};
  if(out.length&&t<=out.at(-1).t)return {error:name+"_out_of_order_or_duplicate"};
  if(t%duration!==0)return {error:name+"_misaligned_bar"};
  out.push({...b,t,end:t+duration,closed:t+duration<=now});
 }
 return {all:out,closed:out.filter(b=>b.closed)};
}
function atrSeries(bars){
 const map=new Map();let count=0,seed=0,atr=null,prev=null;
 for(const b of bars){
  if(!prev||b.t-prev.t!==M5){count=0;seed=0;atr=null;prev=null;}
  const tr=prev?Math.max(b.high-b.low,Math.abs(b.high-prev.close),Math.abs(b.low-prev.close)):b.high-b.low;
  count++;
  if(count<=14){seed+=tr;if(count===14)atr=seed/14;}
  else atr=(atr*13+tr)/14;
  map.set(b.t,{atr,count,tr});prev=b;
 }
 return map;
}
function contextH1(bars){
 if(bars.length<50)return {status:"unknown",reason:"H1_context_requires_50_closed_bars"};
 let e20=bars[0].close,e50=e20;
 for(let i=1;i<bars.length;i++){e20+=(bars[i].close-e20)*2/21;e50+=(bars[i].close-e50)*2/51;}
 const b=bars.at(-1);
 return {status:"recorded_only",lastClosedOpenUTC:iso(b.t),close:b.close,
 ema20:e20,ema50:e50,structure:e20>e50?"up":e20<e50?"down":"flat",directionOverride:false};
}
export function evaluateEventSetup(input){
 // Callers must opt in explicitly; legacy inputs remain byte-for-byte governed
 // by the original fixed-volume rules.
 const FROZEN_RULES=input.rulesVersion===DYNAMIC_RULES.version?DYNAMIC_RULES:BASE_RULES;
 const state=JSON.parse(JSON.stringify(input.state||{})),checks=[];
 let dataAsOf=null,sourceCutoff=null;
 state.filledKeys=Array.isArray(state.filledKeys)?state.filledKeys:[];
 state.rejectedKeys=Array.isArray(state.rejectedKeys)?state.rejectedKeys:[];
 state.invalidatedBreakouts=Array.isArray(state.invalidatedBreakouts)?state.invalidatedBreakouts:[];
 if(FROZEN_RULES.dynamicVolume&&state.strategyVersion!==FROZEN_RULES.version){
  state.previousStrategyVersion=state.strategyVersion||BASE_RULES.version;
  state.strategyVersion=FROZEN_RULES.version;
  state.range=null;state.active=null;state.lastProcessedM5OpenUTC=null;
  state.lastNewsResetStartUTC=null;state.requiredFreshBreakoutAfterUTC=null;
  state.invalidatedBreakouts=[];
 }
 let context={status:"unknown",reason:"not_evaluated"};
 function done(status,code,detail,proposal=null){
  checks.push({status,code,...(detail===undefined?{}:{detail})});
  if(now!==null)state.lastEvaluatedUTC=iso(now);
  return {status,version:FROZEN_RULES.version,executionMode:FROZEN_RULES.mode,
   researchGatePassed:false,prospectiveUnvalidated:true,
   dataAsOfUTC:dataAsOf===null?null:iso(dataAsOf),
   sourceCutoffUTC:sourceCutoff===null?null:iso(sourceCutoff),
   state,reasons:checks,context,proposal};
 }
 const now=absolute(input.nowUTC);
 if(now===null)return done("unknown","invalid_nowUTC");
 dataAsOf=absolute(input.dataAsOfUTC);
 if(dataAsOf===null)return done("unknown","missing_or_invalid_dataAsOfUTC");
 if(dataAsOf>now)return done("unknown","dataAsOfUTC_in_future");
 sourceCutoff=Math.min(now,dataAsOf);
 state.dataAsOfUTC=iso(dataAsOf);state.sourceCutoffUTC=iso(sourceCutoff);
 const eventAnchor=FROZEN_RULES.dynamicVolume?input.eventAnchor:null;
 if(FROZEN_RULES.dynamicVolume&&(!eventAnchor||
  !absolute(eventAnchor.releaseUTC)||!absolute(eventAnchor.windowStartUTC)||
  !absolute(eventAnchor.windowEndUTC)||!absolute(eventAnchor.entryCutoffUTC)||
  !Array.isArray(eventAnchor.blocksUTC)))
  return done("unknown","dynamic_version_requires_fresh_event_anchor");
 if(!finite(input.actualServerOffsetMinutes)||Math.abs(input.actualServerOffsetMinutes)>840)
  return done("unknown","missing_or_invalid_actual_server_offset");
 const offset=input.actualServerOffsetMinutes;
 const meta=input.symbol||{},symbol=meta.symbol||meta.name;
 if(!FROZEN_RULES.symbols.includes(symbol))return done("fail","symbol_not_allowed");
 if(state.symbol&&state.symbol!==symbol)return done("unknown","state_symbol_mismatch");
 state.symbol=symbol;
 const arrays={};
 for(const [name,duration]of [["M5",M5],["M1",MIN],["H1",60*MIN]]){
  const n=normalize(input[name],duration,offset,sourceCutoff,name);
  if(n.error)return done("unknown",n.error);arrays[name]=n.closed;
 }
 context={...contextH1(arrays.H1),dataAsOfUTC:iso(dataAsOf),sourceCutoffUTC:iso(sourceCutoff),
  closedM5Count:arrays.M5.length,closedM1Count:arrays.M1.length,
  lastClosedM5OpenUTC:arrays.M5.length?iso(arrays.M5.at(-1).t):null,
  lastClosedM1OpenUTC:arrays.M1.length?iso(arrays.M1.at(-1).t):null};
 const release=absolute(eventAnchor?.releaseUTC??FROZEN_RULES.releaseUTC),
  start=absolute(eventAnchor?.windowStartUTC??FROZEN_RULES.windowStartUTC),
  end=absolute(eventAnchor?.windowEndUTC??FROZEN_RULES.windowEndUTC),
  entryCutoff=absolute(eventAnchor?.entryCutoffUTC??FROZEN_RULES.entryCutoffUTC),
  activeBlocks=eventAnchor?.blocksUTC??FROZEN_RULES.blocks;
 if(FROZEN_RULES.dynamicVolume&&(
  [release,start,end,entryCutoff].some(t=>t===null)||
  !(release<start&&start<end&&end<=entryCutoff)||
  activeBlocks.some(pair=>!Array.isArray(pair)||pair.length!==2||
   absolute(pair[0])===null||absolute(pair[1])===null||absolute(pair[0])>=absolute(pair[1]))
 ))return done("unknown","dynamic_event_anchor_order_or_block_invalid");
 // Detect missed blocks too: an active setup can never survive crossing a block.
 const lastBlock=activeBlocks.map(([a,b])=>({start:absolute(a),end:absolute(b)}))
  .filter(b=>b.start<=now).at(-1);
 if(lastBlock&&state.lastNewsResetStartUTC!==iso(lastBlock.start)){
  if(state.active){
   const a=state.active;
   state.invalidatedBreakouts.push(a.breakoutOpenUTC);
   if(a.signalKey)state.rejectedKeys.push(a.signalKey);
  }
  state.active=null;state.lastNewsResetStartUTC=iso(lastBlock.start);
  state.requiredFreshBreakoutAfterUTC=iso(lastBlock.end);
 }
 const rangeBars=[0,1,2].map(i=>arrays.M5.find(b=>b.t===release+i*M5));
 if(!state.range&&now>=start){
  if(rangeBars.some(b=>!b))return done("unknown","three_closed_release_M5_bars_missing");
  state.range={high:Math.max(...rangeBars.map(b=>b.high)),low:Math.min(...rangeBars.map(b=>b.low)),
   frozenAtUTC:iso(now),opensUTC:rangeBars.map(b=>iso(b.t))};
 }
 if(!state.range)return done("unknown","immutable_range_not_closed");
 if(!(finite(state.range.high)&&finite(state.range.low)&&state.range.high>state.range.low))
  return done("unknown","invalid_frozen_range");
 if(lastBlock&&now>=lastBlock.start&&now<lastBlock.end)return done("fail","news_block_active");
 if(now<start||now>=end||now>=entryCutoff)
  return done("fail","outside_frozen_entry_window");
 const quote=input.quote||{};
 const quoteTime=quote.timestampUTC?absolute(quote.timestampUTC):
  serverTime(quote.update_time||quote.time,offset);
 if(!finite(quote.bid)||!finite(quote.ask)||quote.ask<quote.bid||quote.bid<=0||
 quoteTime===null)return done("unknown","fresh_quote_missing_or_malformed");
 if(now-quoteTime>30000||quoteTime-now>1000)return done("unknown","quote_stale_or_future");
 const spread=quote.ask-quote.bid;
 const atrs=atrSeries(arrays.M5),range=state.range;
 const freshAfter=Math.max(start,absolute(state.requiredFreshBreakoutAfterUTC)||start);
 const lastProcessed=state.lastProcessedM5OpenUTC?absolute(state.lastProcessedM5OpenUTC):-Infinity;
 // Root reconciles fills/rejections between calls; a consumed setup must not
 // obstruct later fresh bars or be recreated from its original breakout.
 if(state.active?.signalKey&&(state.filledKeys.includes(state.active.signalKey)||
  state.rejectedKeys.includes(state.active.signalKey))){
  if(!state.invalidatedBreakouts.includes(state.active.breakoutOpenUTC))
   state.invalidatedBreakouts.push(state.active.breakoutOpenUTC);
  state.active=null;checks.push({status:"fail",code:"signal_key_already_consumed"});
 }
 function rejectActive(reason){
  if(state.active){
   state.invalidatedBreakouts.push(state.active.breakoutOpenUTC);
   if(state.active.signalKey&&!state.rejectedKeys.includes(state.active.signalKey))
    state.rejectedKeys.push(state.active.signalKey);
  }
  state.active=null;checks.push({status:"fail",code:reason});
 }
 function confirmActive(){
  const a=state.active;if(!a?.retest)return;
  const t=absolute(a.retest.openUTC)+M5;
  if(now<t+MIN)return;
  const c=arrays.M1.find(b=>b.t===t),p=arrays.M1.find(b=>b.t===t-MIN);
  if(!c||!p){checks.push({status:"unknown",code:"first_confirmation_M1_or_previous_missing"});return;}
  if(a.side==="buy"?(c.close>p.high&&c.close>c.open):(c.close<p.low&&c.close<c.open)){
   a.confirmation={openUTC:iso(c.t),closeUTC:iso(c.end),close:c.close};
  }else rejectActive("first_confirmation_M1_failed");
 }
 // Never backfill a later confirmation after the prescribed first M1 fails.
 confirmActive();
 for(const b of arrays.M5){
  if(b.t<freshAfter||b.t<=lastProcessed||b.t>=end)continue;
  const stat=atrs.get(b.t);
  if(!stat||stat.count<100||!finite(stat.atr)||stat.atr<=0){
   checks.push({status:"unknown",code:"M5_ATR_requires_100_consecutive_bars",detail:iso(b.t)});continue;
  }
  state.lastProcessedM5OpenUTC=iso(b.t);
  const hadActive=!!state.active;
  if(state.active){
   const a=state.active,bt=absolute(a.breakoutOpenUTC);
   if(b.t<=bt)continue;
   if(b.close>=range.low&&b.close<=range.high){rejectActive("breakout_closed_back_inside_range");}
   else if(!a.retest){
    const number=(b.t-bt)/M5;
    if(number>3)rejectActive("retest_three_bar_window_expired");
    else if(!Number.isInteger(number)||number<1)rejectActive("retest_sequence_invalid");
    else {
     // A missing M5 between breakout and retest is never silently ignored.
     const missing=Array.from({length:number},(_,i)=>bt+(i+1)*M5)
      .some(t=>!arrays.M5.some(x=>x.t===t));
     if(missing){rejectActive("breakout_retest_M5_gap");}
     else {
      const ok=a.side==="buy"?
       b.low<=range.high+a.buffer&&b.low>=range.low&&b.high>=range.high-a.buffer&&
       b.close>range.high+a.buffer&&b.close>b.open:
       b.high>=range.low-a.buffer&&b.high<=range.high&&b.low<=range.low+a.buffer&&
       b.close<range.low-a.buffer&&b.close<b.open;
      if(ok){
       a.retest={openUTC:iso(b.t),closeUTC:iso(b.end),low:b.low,high:b.high,close:b.close};
       a.signalKey=symbol+"|"+a.side+"|"+a.breakoutOpenUTC+"|"+a.retest.openUTC;
       confirmActive();
      }else if(number===3)rejectActive("no_qualifying_retest_in_three_bars");
     }
    }
   }
  }
  if(!state.active&&!hadActive){
   const buffer=Math.max(2*spread,.1*stat.atr);
   const side=b.close>range.high+buffer?"buy":b.close<range.low-buffer?"sell":null;
   if(side&&!state.invalidatedBreakouts.includes(iso(b.t))){
    state.active={side,breakoutOpenUTC:iso(b.t),atr:stat.atr,buffer,frozenSpread:spread,
     frozenAtUTC:iso(now),observedQuoteUTC:iso(quoteTime),retest:null,confirmation:null};
   }
  }
 }
 confirmActive();
 const active=state.active;
 if(!active)return done(checks.some(c=>c.status==="unknown")?"unknown":"fail","no_active_breakout");
 if(!active.retest)return done("fail","awaiting_separate_qualifying_retest");
 if(!active.confirmation)return done("unknown","awaiting_prescribed_first_closed_M1_confirmation");
 const key=active.signalKey;
 if(state.filledKeys.includes(key)||state.rejectedKeys.includes(key))return done("fail","signal_key_already_consumed");
 function rejectCandidate(code,detail){
  if(!state.rejectedKeys.includes(key))state.rejectedKeys.push(key);
  if(!state.invalidatedBreakouts.includes(active.breakoutOpenUTC))
   state.invalidatedBreakouts.push(active.breakoutOpenUTC);
  state.active=null;
  return done("fail",code,detail);
 }
 const confirmationEnd=absolute(active.confirmation.closeUTC);
 if(now-confirmationEnd>5*MIN||confirmationEnd>now)return rejectCandidate("confirmation_not_fresh");
 const side=active.side,entry=side==="buy"?quote.ask:quote.bid;
 if(side==="buy"?(entry<=range.high+active.buffer||entry>active.confirmation.close+.25*active.atr):
  (entry>=range.low-active.buffer||entry<active.confirmation.close-.25*active.atr))
  return rejectCandidate("price_no_longer_supports_breakout_or_chase");
 const lastThree=arrays.M5.slice(-3);
 if(lastThree.length!==3||lastThree.some((b,i)=>i&&b.t-lastThree[i-1].t!==M5))
  return done("unknown","last_three_M5_missing_or_gapped");
 for(const b of lastThree){
  const a=atrs.get(b.t);
  if(!a||a.count<100||!finite(a.atr))return done("unknown","last_three_M5_ATR_warmup_missing");
  if(a.tr>3*a.atr)return rejectCandidate("exceptional_last_three_M5_true_range");
 }
 const account=input.account||{};
 for(const k of ["isDemo","connected","readOnly","marginSufficient"])
  if(typeof account[k]!=="boolean")return done("unknown","account_check_missing",k);
 if(!account.isDemo||!account.connected||account.readOnly)return rejectCandidate("account_not_connected_writable_demo");
 if(account.currency!=="USD")return done("unknown","account_currency_must_be_USD");
 for(const k of ["equity","observedPeakEquity","openPositionCount","openOrderCount","newEntriesThisSession","closedLosses"])
  if(!finite(account[k]))return done("unknown","account_numeric_check_missing",k);
 if(account.equity<=0||account.observedPeakEquity<account.equity)return done("unknown","invalid_account_equity_peak");
 if(account.unknownExecutionOutcome)return done("unknown","execution_reconciliation_required");
 if(account.openPositionCount>0||account.openOrderCount>0)return rejectCandidate("position_or_order_already_open");
 const entryCap=FROZEN_RULES.maxNewEntries??2;
 if(account.newEntriesThisSession>=entryCap||account.closedLosses>=2)return rejectCandidate("entry_or_loss_halt");
 const drawdownHeadroom=FROZEN_RULES.drawdownHeadroomFraction??.02;
 if(1-account.equity/account.observedPeakEquity>=drawdownHeadroom)return rejectCandidate("observed_drawdown_halt");
 if(!account.marginSufficient)return rejectCandidate("margin_not_sufficient");
 const point=meta.point,contract=meta.contract_size??meta.contractSize,
 currency=meta.currency_profit??meta.currencyProfit,volumeMin=meta.volume_min??meta.volumeMin,
 volumeMax=meta.volume_max??meta.volumeMax,step=meta.volume_step??meta.volumeStep;
 if(currency!=="USD"||![point,contract,volumeMin,volumeMax,step].every(x=>finite(x)&&x>0))
  return done("unknown","symbol_contract_currency_point_or_volume_missing");
 const tradeMode=meta.trade_mode??meta.tradeMode;
 if(!finite(tradeMode))return done("unknown","symbol_trade_mode_missing");
 if(!(tradeMode===4||side==="buy"&&tradeMode===1||side==="sell"&&tradeMode===2))
  return rejectCandidate("symbol_trade_mode_disallows_side");
 const dynamicVolume=FROZEN_RULES.dynamicVolume===true;
 if(!dynamicVolume&&(.01<volumeMin-1e-9||.01>volumeMax+1e-9||Math.abs(.01/step-Math.round(.01/step))>1e-7))
 return rejectCandidate("fixed_001_volume_not_allowed");
 const digits=meta.digits,tick=(meta.tick_size??meta.tickSize)>0?(meta.tick_size??meta.tickSize):point;
 if(!Number.isInteger(digits)||digits<0||digits>10)return done("unknown","symbol_digits_missing");
 const rawSL=side==="buy"?active.retest.low-active.buffer:
  active.retest.high+Math.max(active.frozenSpread,spread)+active.buffer;
 // Round outward to preserve the complete structural extreme; budget is checked after rounding.
 const sl=+(side==="buy"?Math.floor((rawSL+1e-12)/tick)*tick:
  Math.ceil((rawSL-1e-12)/tick)*tick).toFixed(digits);
 const distance=side==="buy"?entry-sl:sl-entry;
 if(!(distance>0))return rejectCandidate("structural_stop_not_on_loss_side");
 if(spread>.2*distance)return rejectCandidate("spread_exceeds_20_percent_stop_distance");
 const tp=+(side==="buy"?entry+2*distance:entry-2*distance).toFixed(digits);
 const stops=meta.trade_stops_level??meta.tradeStopsLevel,freeze=meta.trade_freeze_level??meta.tradeFreezeLevel;
 if(!finite(stops)||!finite(freeze))return done("unknown","broker_stop_freeze_levels_missing");
 const level=Math.max(stops,freeze)*point;
 if(side==="buy"?(quote.bid-sl<level-1e-10||tp-quote.bid<level-1e-10):
  (sl-quote.ask<level-1e-10||quote.ask-tp<level-1e-10))
  return rejectCandidate("broker_stop_or_freeze_distance_failed");
 const activeRiskFraction=FROZEN_RULES.activeRiskFraction??.01,
  hardRiskFraction=FROZEN_RULES.hardRiskFraction??activeRiskFraction,
  reserveAt=v=>Math.max(.07,spread*contract*v)+.05,
  budget=Math.min(activeRiskFraction*account.equity,
   hardRiskFraction*account.equity,
   account.equity-(1-drawdownHeadroom)*account.observedPeakEquity-.10);
 if(budget<=0)return rejectCandidate("risk_budget_exceeded",{budget});
 let volume=.01;
 if(dynamicVolume){
  let candidate=Math.floor((budget-.05)/(distance*contract)/step+1e-9)*step;
  candidate=Math.min(volumeMax,candidate);
  candidate=+candidate.toFixed(8);
  while(candidate>=volumeMin-1e-9&&distance*contract*candidate+reserveAt(candidate)>budget+1e-10)
   candidate=+(candidate-step).toFixed(8);
  if(candidate<volumeMin-1e-9)return rejectCandidate("dynamic_volume_below_symbol_minimum",{distance,budget,volumeMin,step});
  volume=candidate;
 }
 const nominalPriceRisk=distance*contract*volume,
  reserve=reserveAt(volume),totalRisk=nominalPriceRisk+reserve;
 if(totalRisk>budget+1e-10)return rejectCandidate("risk_budget_exceeded",{nominalPriceRisk,reserve,totalRisk,budget,volume});
 const proposal={symbol,side,volume,entry,sl,tp,nominalPriceRisk,reserve,totalRisk,budget,
 riskFraction:activeRiskFraction,hardRiskFraction,dynamicVolume,
 immutableSignalKey:key,version:FROZEN_RULES.version,prospectiveUnvalidated:true,
 range:{...range},breakoutM5OpenUTC:active.breakoutOpenUTC,retest:{...active.retest},
 confirmation:{...active.confirmation},atr:active.atr,frozenBuffer:active.buffer,
 frozenSpread:active.frozenSpread,currentSpread:spread,quoteUTC:iso(quoteTime),
 observedPeakEquity:account.observedPeakEquity,context};
 checks.push({status:"pass",code:"frozen_pattern_quote_volume_margin_stop_and_risk_checks_passed"});
 return done("pass","entry_proposal_only_not_execution",undefined,proposal);
}
