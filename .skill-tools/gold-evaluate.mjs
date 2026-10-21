import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
export function evaluateGold({ticks,symbol,utc,offsetMinutes,config}){
 const now=Date.parse(utc),skip=code=>({symbol:'XAUUSD',status:'skip',code});
 if(!['XAU_M1_S15_BREAK_RETEST_1','XAU_M1_S15_BREAK_RETEST_MICRO_2','XAU_M1_S5_BREAK_RETEST_2'].includes(config.version)||config.symbols.join(',')!=='XAUUSD')return skip('version_gate');
 const signalMs=(config.signal_bar_seconds??15)*1000;
 if(now<Date.parse(config.session_start_utc)||now>=Date.parse(config.session_end_utc))return skip('outside_session');
 if(!Array.isArray(ticks)||ticks.length<100)return skip('ticks_missing');
 const points=ticks.map(x=>({t:Date.parse(x.time_ms+'Z')-offsetMinutes*60000,bid:x.bid,ask:x.ask}));
 if(points.some((x,i)=>!Number.isFinite(x.t)||!(x.bid>0)||x.ask<x.bid||i&&x.t<points[i-1].t))return skip('ticks_invalid');
 const first=points[0].t,last=points.at(-1).t;
 if(now-last>30000)return skip('stale_ticks');
 const cutoff=Math.min(now,last);
 const bars=dur=>{
  const map=new Map();
  for(const x of points){const t=Math.floor(x.t/dur)*dur;if(t<=Math.floor(first/dur)*dur||t+dur>cutoff)continue;let b=map.get(t);if(!b){b={t,open:x.bid,high:x.bid,low:x.bid,close:x.bid,askHigh:x.ask,askLow:x.ask,count:0,first:x.t,last:x.t,maxGap:0};map.set(t,b);}b.high=Math.max(b.high,x.bid);b.low=Math.min(b.low,x.bid);b.close=x.bid;b.askHigh=Math.max(b.askHigh,x.ask);b.askLow=Math.min(b.askLow,x.ask);b.maxGap=Math.max(b.maxGap,x.t-b.last);b.last=x.t;b.count++;}
  const gap=dur===5000?2500:10000;
  return [...map.values()].map(b=>({...b,complete:b.count>=config.minimum_ticks_per_S15&&b.first-b.t<=gap&&b.t+dur-b.last<=gap&&b.maxGap<=gap}));
 };
 const minute=bars(60000),short=bars(signalMs);
 if(minute.length<21||minute.at(-1).t!==Math.floor(cutoff/60000)*60000-60000)return skip('latest_M1_missing');
 if(minute.slice(-21).some((x,i,a)=>!x.complete||i&&x.t-a[i-1].t!==60000))return skip('M1_gap');
 if(short.length<40||short.at(-1).t!==Math.floor(cutoff/signalMs)*signalMs-signalMs)return skip('latest_signal_bar_missing');
 if(short.slice(-25).some((x,i,a)=>!x.complete||i&&x.t-a[i-1].t!==signalMs))return skip('signal_bar_gap');
 const ma=minute.slice(-10).reduce((s,x)=>s+x.close,0)/10,close=minute.at(-1).close;
 const candidates=[],start=Date.parse(config.session_start_utc);
 const retainedTriggerBars=Math.ceil(config.max_trigger_age_seconds/(signalMs/1000));
 for(let i=Math.max(21,short.length-5-retainedTriggerBars);i<short.length-2;i++){
  const br=short[i];if(br.t<start)continue;
  const prev=short.slice(i-(config.range_lookback_S15??20),i),upper=Math.max(...prev.map(x=>x.high)),lower=Math.min(...prev.map(x=>x.low));
  const atr=short.slice(i-14,i).reduce((sum,x,j)=>sum+Math.max(x.high-x.low,Math.abs(x.high-short[i-15+j].close),Math.abs(x.low-short[i-15+j].close)),0)/14;
  const buffer=Math.max(2*symbol.point,.1*atr);
  if(!(atr>0)||br.high-br.low>2.5*atr)continue;
  const side=br.close>upper+buffer&&br.close>br.open&&close>ma?'buy':br.close<lower-buffer&&br.close<br.open&&close<ma?'sell':null;if(!side)continue;
  const level=side==='buy'?upper:lower;
  for(let j=i+1;j<=Math.min(i+3,short.length-2);j++){
   const rt=short[j],tr=short[j+1];
   if(side==='buy'?rt.close<level-buffer:rt.close>level+buffer)break;
   if(!(side==='buy'?rt.low<=level+buffer&&rt.close>=level:rt.high>=level-buffer&&rt.close<=level))continue;
   if(tr.t!==rt.t+signalMs||now-(tr.t+signalMs)>config.max_trigger_age_seconds*1000)continue;
   if(!(side==='buy'?tr.close>tr.open&&tr.close>rt.high:tr.close<tr.open&&tr.close<rt.low))break;
   const sl=side==='buy'?Math.min(rt.low,tr.low)-buffer:Math.max(rt.askHigh,tr.askHigh)+buffer;
   const entry=side==='buy'?symbol.ask:symbol.bid,d=Math.abs(entry-sl);
   if(d<.5*atr||d>3*atr)break;
   candidates.push({symbol:'XAUUSD',status:'analysis_ready',version:config.version,side,entry,structuralSL:sl,atr,buffer,level,setupUTC:new Date(br.t).toISOString(),retestUTC:new Date(rt.t).toISOString(),triggerUTC:new Date(tr.t).toISOString(),expiresUTC:new Date(tr.t+signalMs+config.max_trigger_age_seconds*1000).toISOString(),dedupKey:[config.version,side,br.t,tr.t].join('|')});break;
  }
 }
 return candidates.at(-1)??skip('no_fresh_S15_break_retest_confirm');
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href&&process.argv[2]){const x=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));const c=JSON.parse(fs.readFileSync('E:/GPT/Inves/Trading_Manager_Config.json','utf8'));console.log(JSON.stringify(evaluateGold({...x,config:c})));}
