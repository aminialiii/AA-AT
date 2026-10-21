import fs from 'node:fs';
const W='E:/GPT/Inves';
const s=JSON.parse(fs.readFileSync(W+'/Trading_Manager_State.json','utf8'));
const r=s.hundred.results;
const sum=a=>a.reduce((x,y)=>x+(Number(y.netUSD)||0),0);
const avg=a=>a.length?sum(a)/a.length:0;
const group=key=>Object.fromEntries([...new Set(r.map(x=>x[key]))].map(k=>{
  const a=r.filter(x=>x[key]===k);
  return [k,{n:a.length,netUSD:Number(sum(a).toFixed(4)),avgUSD:Number(avg(a).toFixed(4)),wins:a.filter(x=>x.netUSD>0).length,losses:a.filter(x=>x.netUSD<0).length,avgR:Number(avg(a.map(x=>({netUSD:x.netR}))).toFixed(4))}];
}));
const forward=r.filter(x=>x.partition==='forward_comparison');
const report={
  version:s.version,generatedUTC:new Date().toISOString(),target:100,closed:r.length,
  baselineUSD:s.hundred.baselineBalanceUSD,endingUSD:s.hundred.baselineBalanceUSD+sum(r),
  netUSD:Number(sum(r).toFixed(4)),returnPct:Number((sum(r)/s.hundred.baselineBalanceUSD*100).toFixed(4)),
  wins:r.filter(x=>x.netUSD>0).length,losses:r.filter(x=>x.netUSD<0).length,flats:r.filter(x=>x.netUSD===0).length,
  winRate:Number((r.filter(x=>x.netUSD>0).length/r.length*100).toFixed(2)),avgNetUSD:Number(avg(r).toFixed(4)),
  avgNetR:Number(avg(r.map(x=>({netUSD:x.netR}))).toFixed(4)),
  commissionUSD:sum(r.map(x=>({netUSD:x.commissionUSD||0}))),swapUSD:sum(r.map(x=>({netUSD:x.swapUSD||0}))),feesUSD:sum(r.map(x=>({netUSD:x.feesUSD||0}))),
  bySymbol:group('symbol'),byArm:group('arm'),byHold:group('holdSeconds'),
  byPartition:{development:{n:r.filter(x=>x.partition==='development').length,netUSD:sum(r.filter(x=>x.partition==='development'))},forward_comparison:{n:forward.length,netUSD:sum(forward)}},
  maeObservedCount:r.filter(x=>x.MAEPriceObserved!=null).length,mfeObservedCount:r.filter(x=>x.MFEPriceObserved!=null).length,
  limitations:['Minimum broker volume and short holding times; not a profitability proof','No commission/swap/fee was charged in observed reconciliations','Strategy is prospective and unvalidated; slippage and latency remain material','Forward segment is observational, not an untouched OOS market regime']
};
const stamp=Date.now();
const jpath=W+'/trading-journal/hundred_analysis_100_'+stamp+'.json';
const mpath=W+'/trading-journal/hundred_analysis_100_'+stamp+'.md';
fs.writeFileSync(jpath,JSON.stringify(report,null,2));
const md=['# گزارش ۱۰۰ معامله DEMO_100_ROUNDTRIPS_1','',`زمان تولید UTC: ${report.generatedUTC}`,`تعداد: ${report.closed}`,`موجودی پایه: $${report.baselineUSD.toFixed(2)}`,`موجودی پایان: $${report.endingUSD.toFixed(2)}`,`سود/زیان خالص: $${report.netUSD.toFixed(2)} (${report.returnPct}%)`,`برد/باخت/خنثی: ${report.wins}/${report.losses}/${report.flats}`,`نرخ برد: ${report.winRate}%`,`میانگین معامله: $${report.avgNetUSD}`,`میانگین R: ${report.avgNetR}`,`هزینه ثبت‌شده commission/swap/fees: $${(report.commissionUSD+report.swapUSD+report.feesUSD).toFixed(2)}`,'','## بر اساس نماد','```json',JSON.stringify(report.bySymbol,null,2),'```','## بر اساس بازو','```json',JSON.stringify(report.byArm,null,2),'```','## توسعه و forward','```json',JSON.stringify(report.byPartition,null,2),'```','','## محدودیت‌ها',...report.limitations.map(x=>'- '+x)].join('\n');
fs.writeFileSync(mpath,md);
s.last_analysis_path=mpath;s.last_review_utc=new Date().toISOString();
s.next_action='Review 100-trade report, then run a new frozen comparison cycle with only pre-registered changes';
fs.writeFileSync(W+'/Trading_Manager_State.json',JSON.stringify(s,null,2));
console.log(JSON.stringify({jpath,mpath,netUSD:report.netUSD,endingUSD:report.endingUSD,winRate:report.winRate,bySymbol:report.bySymbol,byArm:report.byArm,byPartition:report.byPartition}));
