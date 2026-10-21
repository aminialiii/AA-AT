// Research only. No trading APIs. Define prepared={EURUSD:[{t,open,high,low,close,e20,e50,atr,rsi,spreadPx,serverHour}],GBPUSD:[...]}. t is UTC milliseconds; spreads in price units.
function simulateContinuation(config,start,end,guard=true) {
 const startT=Date.parse(start),endT=Date.parse(end);
 const times=new Map();
 for(const[s,bars]of Object.entries(prepared)) for(let i=201;i<bars.length;i++) {
  const b=bars[i]; if(b.t<startT||b.t>=endT) continue;
  if(!times.has(b.t)) times.set(b.t,[]); times.get(b.t).push({symbol:s,bars,i});
 }
 let balance=100,peak=100,maxDD=0,maxMarkDD=0,p=null,stop=false,cooldown=0;
 let day="",dailyCount=0,dayStart=100;
 const trades=[];const rejected={risk:0,spread:0,guard:0};
 const chronology=[...times.keys()].sort((a,b)=>a-b);
 function close(bar,price,reason,t){
  const pnl=(price-p.entry)*p.side*1000-.07;
  balance+=pnl;peak=Math.max(peak,balance);maxDD=Math.max(maxDD,(peak-balance)/peak*100);
  trades.push({...p,bars:undefined,entryI:undefined,exitTime:t,exitPrice:price,net:pnl,R:pnl/p.risk,reason});
  p=null;cooldown=t+15*60000;
  if(guard&&maxMarkDD>=2)stop=true;
 }
 for(const t of chronology) {
  const rows=times.get(t);
  const dt=new Date(t).toISOString().slice(0,10);if(dt!==day){day=dt;dailyCount=0;dayStart=balance;}
  if(p){
   const row=rows.find(x=>x.symbol===p.symbol);
   if(row){
    const b=row.bars[row.i],sp=b.spreadPx;
    const lo=p.side===1?b.low:b.low+sp,hi=p.side===1?b.high:b.high+sp,op=p.side===1?b.open:b.open+sp;
    const adverse=(p.side===1?Math.max(lo,Math.min(p.sl,op)):Math.min(hi,Math.max(p.sl,op)));const loweq=balance+(adverse-p.entry)*p.side*1000-.07;
    maxMarkDD=Math.max(maxMarkDD,(peak-loweq)/peak*100);
    const slHit=p.side===1?lo<=p.sl:hi>=p.sl;
    const tpHit=p.side===1?hi>=p.tp:lo<=p.tp;
    if(slHit)close(b,p.side===1?Math.min(p.sl,op):Math.max(p.sl,op),tpHit?"SL_both_hit_pessimistic":"SL",t);
    else if(tpHit)close(b,p.tp,"TP",t);
    else if(row.i-p.entryI>=12||b.serverHour>=22)close(b,p.side===1?b.close:b.close+sp,"time_exit",t+5*60000);
    else {const eq=balance+((p.side===1?b.close:b.close+sp)-p.entry)*p.side*1000-.07;peak=Math.max(peak,eq);}
   }
  }
  if(p||stop||t<cooldown||dailyCount>=2)continue;
  if(guard&&((peak-balance)/peak>=.02||balance<=dayStart*.98)){rejected.guard++;stop=true;continue;}
  const ordered=rows.slice().sort((a,b)=>a.symbol.localeCompare(b.symbol));
  for(const row of ordered){
   const {symbol,bars,i}=row,b=bars[i],a=bars[i-1],old=bars[i-4];
   // Signal uses closed bar i-1; execute at open i. No gaps or session spillover.
   if(i<220||b.t-a.t!==300000||b.serverHour<11||b.serverHour>=22||+b.time.slice(14,16)>40&&b.serverHour===21)continue;
   const trend=a.e20>a.e50&&a.e50>old.e50?1:a.e20<a.e50&&a.e50<old.e50?-1:0;
   if(!trend)continue;
   let signal=false;
   if(config.family==="pullback"){
    const prev=bars[i-2];
    signal=trend===1?prev.low<=prev.e20&&a.close>prev.high&&a.close>a.open:a.close<prev.low&&prev.high>=prev.e20&&a.close<a.open;
   }else{
    const prior=bars.slice(i-13,i-1),rh=Math.max(...prior.map(x=>x.high)),rl=Math.min(...prior.map(x=>x.low));
    signal=trend===1?a.close>rh&&a.close>a.open:a.close<rl&&a.close<a.open;
   }
   if(!signal)continue;
   const spread=a.spreadPx,entry=b.open+(trend===1?spread:0);
   const swing=bars.slice(i-4,i);
   const structural=trend===1?Math.min(...swing.map(x=>x.low))-.1*a.atr:Math.max(...swing.map(x=>x.high))+.1*a.atr+spread;
   const distance=Math.max(Math.abs(entry-structural),config.minATR*a.atr);
   const risk=distance*1000+.07;
   if(risk>balance*.01||risk<.15){rejected.risk++;continue;}
   if(spread>distance*.2){rejected.spread++;continue;}
   p={symbol,entryTime:t,entry,side:trend,sl:entry-trend*distance,tp:entry+trend*distance*config.targetR,risk,entryI:i};
   dailyCount++;
   // Process first fill candle once; prevents skipped same-candle SL/TP.
   const lo=trend===1?b.low:b.low+spread,hi=trend===1?b.high:b.high+spread;
   const adverse=trend===1?Math.max(lo,p.sl):Math.min(hi,p.sl);
   maxMarkDD=Math.max(maxMarkDD,(peak-(balance+(adverse-entry)*trend*1000-.07))/peak*100);
   const slHit=trend===1?lo<=p.sl:hi>=p.sl,tpHit=trend===1?hi>=p.tp:lo<=p.tp;
   if(slHit)close(b,p.sl,tpHit?"SL_both_hit_pessimistic":"SL",t);
   else if(tpHit)close(b,p.tp,"TP",t);
   break;
  }
 }
 if(p){
  const bars=prepared[p.symbol],b=bars.filter(x=>x.t<endT).at(-1);
  close(b,p.side===1?b.close:b.close+b.spreadPx,"period_end",b.t+5*60000);
 }
 const win=trades.filter(x=>x.net>0).reduce((s,x)=>s+x.net,0);
 const loss=-trades.filter(x=>x.net<=0).reduce((s,x)=>s+x.net,0);
 return {config:config.id,start,end,guard,count:trades.length,net:balance-100,pf:loss?win/loss:null,maxBalanceDD:maxDD,maxAdverseMarkDD:maxMarkDD,halted:stop,winRate:trades.filter(x=>x.net>0).length/trades.length,rejected,trades};
}

function simulateFrozenRSI(config,start,end,guard=true) {
 const startT=Date.parse(start),endT=Date.parse(end);
 const times=new Map();
 for(const[s,bars]of Object.entries(prepared)) for(let i=201;i<bars.length;i++) {
  const b=bars[i]; if(b.t<startT||b.t>=endT) continue;
  if(!times.has(b.t)) times.set(b.t,[]); times.get(b.t).push({symbol:s,bars,i});
 }
 let balance=100,peak=100,maxDD=0,maxMarkDD=0,p=null,stop=false,cooldown=0;
 let day="",dailyCount=0,dayStart=100;
 const trades=[];const rejected={risk:0,spread:0,guard:0};
 const chronology=[...times.keys()].sort((a,b)=>a-b);
 function close(bar,price,reason,t){
  const pnl=(price-p.entry)*p.side*1000-.07;
  balance+=pnl;peak=Math.max(peak,balance);maxDD=Math.max(maxDD,(peak-balance)/peak*100);
  trades.push({...p,bars:undefined,entryI:undefined,exitTime:t,exitPrice:price,net:pnl,R:pnl/p.risk,reason});
  p=null;cooldown=t+15*60000;
  if(guard&&maxMarkDD>=2)stop=true;
 }
 for(const t of chronology) {
  const rows=times.get(t);
  const dt=new Date(t).toISOString().slice(0,10);if(dt!==day){day=dt;dailyCount=0;dayStart=balance;}
  if(p){
   const row=rows.find(x=>x.symbol===p.symbol);
   if(row){
    const b=row.bars[row.i],sp=b.spreadPx;
    const lo=p.side===1?b.low:b.low+sp,hi=p.side===1?b.high:b.high+sp,op=p.side===1?b.open:b.open+sp;
    const adverse=(p.side===1?Math.max(lo,Math.min(p.sl,op)):Math.min(hi,Math.max(p.sl,op)));const loweq=balance+(adverse-p.entry)*p.side*1000-.07;
    maxMarkDD=Math.max(maxMarkDD,(peak-loweq)/peak*100);
    const slHit=p.side===1?lo<=p.sl:hi>=p.sl;
    const tpHit=p.side===1?hi>=p.tp:lo<=p.tp;
    if(slHit)close(b,p.side===1?Math.min(p.sl,op):Math.max(p.sl,op),tpHit?"SL_both_hit_pessimistic":"SL",t);
    else if(tpHit)close(b,p.tp,"TP",t);
    else if(row.i-p.entryI>=12||new Date(b.t).getUTCHours()>=20)close(b,p.side===1?b.close:b.close+sp,"time_exit",t+5*60000);
    else {const eq=balance+((p.side===1?b.close:b.close+sp)-p.entry)*p.side*1000-.07;peak=Math.max(peak,eq);}
   }
  }
  if(p||stop||t<cooldown||dailyCount>=2)continue;
  if(guard&&((peak-balance)/peak>=.02||balance<=dayStart*.98)){rejected.guard++;stop=true;continue;}
  const ordered=rows.slice().sort((a,b)=>a.symbol.localeCompare(b.symbol));
  for(const row of ordered){
   const {symbol,bars,i}=row,b=bars[i],a=bars[i-1],old=bars[i-4];
   // Signal uses closed bar i-1; execute at open i. No gaps or session spillover.
   if(i<220||b.t-a.t!==300000||new Date(b.t).getUTCHours()<7||new Date(b.t).getUTCHours()>=20||new Date(b.t).getUTCHours()===19&&+b.time.slice(14,16)>40)continue;
   const prev=bars[i-2]; const trend=a.rsi<25&&a.close>a.open&&a.close>prev.close?1:a.rsi>65&&a.close<a.open&&a.close<prev.close?-1:0;
   if(!trend)continue;
   const signal=true;
   const spread=a.spreadPx,entry=b.open+(trend===1?spread:0);
   const swing=bars.slice(i-4,i);
   const structural=trend===1?Math.min(...swing.map(x=>x.low))-.1*a.atr:Math.max(...swing.map(x=>x.high))+.1*a.atr+spread;
   const distance=2*a.atr;
   const risk=distance*1000+.07;
   if(risk>balance*.01||risk<.15){rejected.risk++;continue;}
   if(spread>distance*.2){rejected.spread++;continue;}
   p={symbol,entryTime:t,entry,side:trend,sl:entry-trend*distance,tp:entry+trend*distance*config.targetR,risk,entryI:i};
   dailyCount++;
   // Process first fill candle once; prevents skipped same-candle SL/TP.
   const lo=trend===1?b.low:b.low+spread,hi=trend===1?b.high:b.high+spread;
   const adverse=trend===1?Math.max(lo,p.sl):Math.min(hi,p.sl);
   maxMarkDD=Math.max(maxMarkDD,(peak-(balance+(adverse-entry)*trend*1000-.07))/peak*100);
   const slHit=trend===1?lo<=p.sl:hi>=p.sl,tpHit=trend===1?hi>=p.tp:lo<=p.tp;
   if(slHit)close(b,p.sl,tpHit?"SL_both_hit_pessimistic":"SL",t);
   else if(tpHit)close(b,p.tp,"TP",t);
   break;
  }
 }
 if(p){
  const bars=prepared[p.symbol],b=bars.filter(x=>x.t<endT).at(-1);
  close(b,p.side===1?b.close:b.close+b.spreadPx,"period_end",b.t+5*60000);
 }
 const win=trades.filter(x=>x.net>0).reduce((s,x)=>s+x.net,0);
 const loss=-trades.filter(x=>x.net<=0).reduce((s,x)=>s+x.net,0);
 return {config:config.id,start,end,guard,count:trades.length,net:balance-100,pf:loss?win/loss:null,maxBalanceDD:maxDD,maxAdverseMarkDD:maxMarkDD,halted:stop,winRate:trades.filter(x=>x.net>0).length/trades.length,rejected,trades};
}

