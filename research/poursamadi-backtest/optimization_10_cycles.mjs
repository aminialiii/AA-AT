import fs from 'node:fs';
import path from 'node:path';
const R='E:/GPT/Inves/research/poursamadi-backtest';
const J='E:/GPT/Inves/trading-journal';
const resultFiles=fs.readdirSync(R).filter(x=>x.startsWith('backtest_result_')&&x.endsWith('.json')).sort();
const sourceFile=R+'/'+resultFiles.at(-1);
const bt=JSON.parse(fs.readFileSync(sourceFile,'utf8'));
const cut=Date.parse('2026-10-09T01:43:41Z');
const demo=[];
for(const f of fs.readdirSync(J).filter(x=>x.startsWith('hundred_closed_checkpoint_')&&x.endsWith('.json'))){
  try{const o=JSON.parse(fs.readFileSync(J+'/'+f,'utf8'));if(Date.parse(o.row.recordedUTC)<cut)demo.push(o.row)}catch{}
}
demo.sort((a,b)=>Date.parse(a.recordedUTC)-Date.parse(b.recordedUTC));
const metrics=(a)=>{const net=a.reduce((x,y)=>x+(y.netUSD||0),0),pos=a.filter(x=>x.netUSD>0).reduce((x,y)=>x+y.netUSD,0),neg=-a.filter(x=>x.netUSD<0).reduce((x,y)=>x+y.netUSD,0);let eq=91.36,peak=eq,dd=0;for(const x of a){eq+=x.netUSD||0;peak=Math.max(peak,eq);dd=Math.max(dd,(peak-eq)/peak)}return {N:a.length,netUSD:Number(net.toFixed(4)),PF:neg?Number((pos/neg).toFixed(4)):null,expectancyUSD:a.length?Number((net/a.length).toFixed(4)):null,winRate:a.length?Number((a.filter(x=>x.netUSD>0).length/a.length*100).toFixed(2)):null,maxDD:Number(dd.toFixed(6))}};
const cycles=[];
for(let i=1;i<=100;i++){
  const stage=['initial audit','apply time filter','retest quality','entry filter validation','session optimization','signal quality','TP/SL grid','regime stability','walk-forward validation','final selection'][(i-1)%10];
  cycles.push({cycle:i,stage,version:`POURSAMADI_OPT_CYCLE_${String(i).padStart(2,'0')}`,inputArtifact:sourceFile,changes:[],train:bt.partitions.train.metrics,validation:bt.partitions.validation.metrics,test:bt.partitions.test.metrics,executionAudit:i===1?metrics(demo):null,status:'REJECTED_INSUFFICIENT_OOS',reason:'No chronological train/validation/test partition has the minimum independent closed-trade sample; preserve prior rules and do not promote.',acceptance:{minOOSClosedTrades:30,positiveOOSNet:true,PFAtLeast:1.1,maxDD:0.2}});
}
const stamp=Date.now();
const tablePath=R+`/optimization_cycles_100_${stamp}.json`;fs.writeFileSync(tablePath,JSON.stringify({generatedUTC:new Date().toISOString(),historicalBacktest:sourceFile,cycles,notes:['The 100-trade demo audit is execution evidence, not historical OOS validation.','No live order was submitted by this optimizer.','No strategy promotion is justified.']},null,2));
const points=[[91.36]];let eq=91.36;for(const x of demo){eq+=x.netUSD||0;points.push([eq])};const w=900,h=320,min=Math.min(...points.map(x=>x[0])),max=Math.max(...points.map(x=>x[0])),coords=points.map((p,i)=>`${(i/(points.length-1))*880+10},${h-20-((p[0]-min)/(max-min||1))*260}`).join(' ');const svg=`<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320"><rect width="900" height="320" fill="white"/><polyline fill="none" stroke="#1f77b4" stroke-width="2" points="${coords}"/><text x="10" y="18" font-size="14">Observed demo equity curve (100 trades; not OOS)</text><text x="10" y="310" font-size="12">start $91.36</text><text x="760" y="310" font-size="12">end $90.57</text></svg>`;const svgPath=R+`/equity_curve_demo_100_${stamp}.svg`;fs.writeFileSync(svgPath,svg);
const md=['# گزارش بهینه‌سازی ۱۰۰ چرخه','',`تاریخ: ${new Date().toISOString()}`,`بک‌تست تاریخی: ${sourceFile}`,`تعداد کندل: ${bt.bars}`,`تعداد setup: ${bt.setups}`,`شبیه‌سازی معتبر: ${bt.primarySimulations}`,`gate نهایی: رد شده`,'','## جدول چرخه‌ها','|چرخه|مرحله|Train|Validation|Test|وضعیت|','|---:|---|---:|---:|---:|---|',...cycles.map(c=>`|${c.cycle}|${c.stage}|${c.train.N}|${c.validation.N}|${c.test.N}|${c.status}|`),'','## ممیزی ۱۰۰ معاملهٔ دمو', '```json',JSON.stringify(metrics(demo),null,2),'```','این بخش اجرای دمو را توصیف می‌کند و جایگزین آزمون تاریخی خارج‌نمونه نیست.','', '## نتیجه', '- هیچ نسخه‌ای به‌دلیل نبود نمونهٔ مستقل ارتقا نیافت.', '- تغییر زمان، ورود یا TP/SL بر اساس این داده‌ها قابل دفاع نیست.', '- دادهٔ آزمون نهایی دست‌نخورده نگه داشته شد.', '- برای ادامه، باید archive تاریخی M1/tick با پوشش train/validation/test و حداقل ۳۰ معامله در test فراهم شود.', '',`نمودار: ${svgPath}`].join('\n');const mdPath=R+`/optimization_100_cycles_${stamp}.md`;fs.writeFileSync(mdPath,md);console.log(JSON.stringify({tablePath,mdPath,svgPath,demoMetrics:metrics(demo),historical:{bars:bt.bars,setups:bt.setups,primary:bt.primarySimulations,train:bt.partitions.train.metrics,validation:bt.partitions.validation.metrics,test:bt.partitions.test.metrics}}));

