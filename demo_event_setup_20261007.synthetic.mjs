import assert from "node:assert/strict";
import {evaluateEventSetup,FROZEN_RULES} from "./demo_event_setup_20261007.mjs";
const utc=s=>Date.parse(s),stamp=t=>new Date(t).toISOString();
const bar=(t,o,h,l,c)=>({timeUTC:stamp(t),open:o,high:h,low:l,close:c});
const release=utc("2026-10-07T18:00:00Z"),m5=[];
for(let i=-130;i<0;i++)m5.push(bar(release+i*300000,1.1003,1.1006,1.1001,1.1003));
for(let i=0;i<3;i++)m5.push(bar(release+i*300000,1.1003,1.1010,1.1000,1.1005));
m5.push(bar(release+900000,1.1011,1.1017,1.1010,1.1016));
m5.push(bar(release+1200000,1.1014,1.10175,1.10102,1.10165));
m5.push(bar(release+1500000,1.10165,1.102,1.1008,1.1018)); // still forming
const m1=[];
for(let i=0;i<=25;i++)m1.push(bar(release+i*60000,1.1014,1.1016,1.1011,1.1015));
m1[25]=bar(release+1500000,1.1015,1.10175,1.1014,1.10165);
const h1=[];for(let i=-60;i<0;i++)h1.push(bar(release+i*3600000,1.10,1.11,1.09,1.10));
const base={nowUTC:"2026-10-07T18:26:10Z",dataAsOfUTC:"2026-10-07T18:26:10Z",actualServerOffsetMinutes:180,
 symbol:{symbol:"EURUSD",digits:5,point:.00001,tick_size:0,contract_size:100000,
 currency_profit:"USD",volume_min:.01,volume_max:500,volume_step:.01,trade_mode:4,
 trade_stops_level:0,trade_freeze_level:0},
 quote:{bid:1.10167,ask:1.10168,timestampUTC:"2026-10-07T18:26:00Z"},
 M5:m5,M1:m1,H1:h1,state:{},
 account:{isDemo:true,connected:true,readOnly:false,equity:99.90,observedPeakEquity:100,
 currency:"USD",openPositionCount:0,openOrderCount:0,newEntriesThisSession:0,
 closedLosses:1,marginSufficient:true}};
const clone=()=>JSON.parse(JSON.stringify(base));
const result=evaluateEventSetup(clone());
assert.equal(result.status,"pass",JSON.stringify(result.reasons));
assert.equal(result.proposal.side,"buy");
assert.equal(result.proposal.retest.openUTC,"2026-10-07T18:20:00.000Z");
assert.equal(result.proposal.confirmation.openUTC,"2026-10-07T18:25:00.000Z");
assert(result.proposal.totalRisk<=result.proposal.budget);
assert.equal(result.state.range.high,1.101);
assert.equal(result.proposal.prospectiveUnvalidated,true);
assert.equal(FROZEN_RULES.researchGatePassed,false);
assert.deepEqual(base.state,{});
function check(name,mutate,status,code){
 const x=clone();mutate(x);const r=evaluateEventSetup(x);
 assert.equal(r.status,status,name+": "+JSON.stringify(r.reasons));
 assert(r.reasons.some(a=>a.code===code),name+":missing "+code);
}
check("blocked time",x=>{x.nowUTC="2026-10-07T18:50:00Z";},"fail","news_block_active");
check("out of order",x=>{[x.M5[0],x.M5[1]]=[x.M5[1],x.M5[0]];},"unknown","M5_out_of_order_or_duplicate");
check("missing range bar",x=>{x.M5=x.M5.filter(b=>b.timeUTC!=="2026-10-07T18:05:00.000Z");},"unknown","three_closed_release_M5_bars_missing");
check("ATR warmup gap",x=>{x.M5.splice(120,1);},"unknown","M5_ATR_requires_100_consecutive_bars");
check("missing first M1",x=>{x.M1=x.M1.filter(b=>b.timeUTC!=="2026-10-07T18:25:00.000Z");},"unknown","first_confirmation_M1_or_previous_missing");
check("first M1 fails",x=>{x.M1[25].close=1.10145;},"fail","first_confirmation_M1_failed");
check("stale quote",x=>{x.quote.timestampUTC="2026-10-07T18:25:00Z";},"unknown","quote_stale_or_future");
check("missing margin",x=>{delete x.account.marginSufficient;},"unknown","account_check_missing");
check("account live",x=>{x.account.isDemo=false;},"fail","account_not_connected_writable_demo");
check("loss halt",x=>{x.account.closedLosses=2;},"fail","entry_or_loss_halt");
check("risk headroom",x=>{x.account.equity=98.5;},"fail","risk_budget_exceeded");
check("dedup",x=>{x.state=result.state;x.state.filledKeys.push(result.proposal.immutableSignalKey);},"fail","signal_key_already_consumed");
const naive=clone();const serverStamp=s=>new Date(Date.parse(s)+180*60000).toISOString().slice(0,19).replace(/-/g,".").replace("T"," ");
for(const k of ["M5","M1","H1"])naive[k]=naive[k].map(b=>({...b,time:serverStamp(b.timeUTC),timeUTC:undefined}));
naive.quote.update_time=serverStamp(naive.quote.timestampUTC);delete naive.quote.timestampUTC;
assert.equal(evaluateEventSetup(naive).status,"pass","server-naive conversion");
const short=clone();
for(const k of ["M5","M1","H1"])short[k]=short[k].map(b=>({...b,open:2.202-b.open,
 high:2.202-b.low,low:2.202-b.high,close:2.202-b.close}));
short.quote.bid=2.202-base.quote.ask;short.quote.ask=2.202-base.quote.bid;
const sr=evaluateEventSetup(short);assert.equal(sr.status,"pass",JSON.stringify(sr.reasons));
assert.equal(sr.proposal.side,"sell");
assert(sr.proposal.sl>=sr.proposal.retest.high+sr.proposal.frozenBuffer+
 Math.max(sr.proposal.frozenSpread,sr.proposal.currentSpread)-1e-10);
const gold=clone();
for(const k of ["M5","M1","H1"])gold[k]=gold[k].map(b=>({...b,open:b.open*1000,
 high:b.high*1000,low:b.low*1000,close:b.close*1000}));
gold.symbol={...gold.symbol,symbol:"XAUUSD",digits:2,point:.01,tick_size:.01,contract_size:100};
gold.quote.bid*=1000;gold.quote.ask*=1000;
const gr=evaluateEventSetup(gold);assert.equal(gr.status,"pass",JSON.stringify(gr.reasons));
assert(Math.abs(gr.proposal.nominalPriceRisk-(gr.proposal.entry-gr.proposal.sl))<1e-9);
const failed=clone();failed.account.equity=98.5;
const failedResult=evaluateEventSetup(failed);
assert.equal(failedResult.status,"fail");assert.equal(failedResult.state.active,null);
assert(failedResult.state.invalidatedBreakouts.includes(result.proposal.breakoutM5OpenUTC));
function later(state){
 const x=clone();x.state=JSON.parse(JSON.stringify(state));
 x.nowUTC="2026-10-07T18:36:10Z";x.quote.timestampUTC="2026-10-07T18:36:00Z";
 x.dataAsOfUTC=x.nowUTC;
 x.M5=x.M5.slice(0,-1);
 x.M5.push({...x.M5.at(-2),timeUTC:"2026-10-07T18:25:00.000Z"});
 x.M5.push({...x.M5.at(-2),timeUTC:"2026-10-07T18:30:00.000Z"});
 for(let i=26;i<=35;i++)x.M1.push(bar(release+i*60000,1.1014,1.1016,1.1011,1.1015));
 x.M1[35]=bar(release+35*60000,1.1015,1.10175,1.1014,1.10165);
 return x;
}
const afterFailed=evaluateEventSetup(later(failedResult.state));
assert.equal(afterFailed.status,"pass",JSON.stringify(afterFailed.reasons));
assert.notEqual(afterFailed.proposal.immutableSignalKey,result.proposal.immutableSignalKey);
const filledState=JSON.parse(JSON.stringify(result.state));
filledState.filledKeys.push(result.proposal.immutableSignalKey);
const consumed=clone();consumed.state=filledState;
const consumedResult=evaluateEventSetup(consumed);
assert.equal(consumedResult.status,"fail");assert.equal(consumedResult.state.active,null);
assert.equal(consumedResult.state.lastProcessedM5OpenUTC,result.state.lastProcessedM5OpenUTC);
const afterFilled=evaluateEventSetup(later(filledState));
assert.equal(afterFilled.status,"pass",JSON.stringify(afterFilled.reasons));
assert.notEqual(afterFilled.proposal.immutableSignalKey,result.proposal.immutableSignalKey);
check("missing dataAsOf",x=>{delete x.dataAsOfUTC;},"unknown","missing_or_invalid_dataAsOfUTC");
check("future dataAsOf",x=>{x.dataAsOfUTC="2026-10-07T18:27:00Z";},"unknown","dataAsOfUTC_in_future");
const cached=clone();cached.nowUTC="2026-10-07T18:26:10Z";
cached.dataAsOfUTC="2026-10-07T18:25:49Z";
const cachedResult=evaluateEventSetup(cached);
assert.equal(cachedResult.status,"unknown",JSON.stringify(cachedResult.reasons));
assert.equal(cachedResult.proposal,null);
assert(cachedResult.reasons.some(r=>r.code==="awaiting_prescribed_first_closed_M1_confirmation"));
assert.equal(cachedResult.sourceCutoffUTC,"2026-10-07T18:25:49.000Z");
assert.equal(cachedResult.state.active.confirmation,null);
assert.equal(cachedResult.state.lastProcessedM5OpenUTC,"2026-10-07T18:20:00.000Z");
const realCutoff=clone();realCutoff.nowUTC="2026-10-07T18:11:00Z";
realCutoff.dataAsOfUTC="2026-10-07T18:09:49Z";
realCutoff.M5=realCutoff.M5.filter(b=>Date.parse(b.timeUTC)<=release+5*60000);
realCutoff.M1=realCutoff.M1.filter(b=>Date.parse(b.timeUTC)<=release+9*60000);
const realCutoffResult=evaluateEventSetup(realCutoff);
assert.equal(realCutoffResult.context.lastClosedM5OpenUTC,"2026-10-07T18:00:00.000Z");
assert.notEqual(realCutoffResult.context.lastClosedM5OpenUTC,"2026-10-07T18:05:00.000Z");
console.log("PASS: 22 synthetic safety/pattern cases, including request-start18:09:49 with partialM5 opening18:05 excluded at evaluation18:11; no profitability test.");
