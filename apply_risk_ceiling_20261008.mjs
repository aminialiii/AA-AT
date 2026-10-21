import fs from 'node:fs';
import path from 'node:path';
const workspace='E:/GPT/Inves';
const skills='C:/Users/SOC-Peyman/.codex/skills';
const builderPath=path.join(workspace,'build_trading_skills.mjs');
const replacements=[
  ['mt5-trading-manager/references/operating-contract.md',['One position globally,','Price risk plus reserve budget =']],
  ['mt5-trade-execution/SKILL.md',['Read the exact candidate and current config.']],
  ['mt5-trading-research/SKILL.md',['Treat E:/GPT/Inves historical files']],
  ['mt5-trading-manager/SKILL.md',['Install/read the scripts before invoking:']]
];
let builder=fs.readFileSync(builderPath,'utf8').split(/\r?\n/);
for(const [relative,prefixes] of replacements){
  const current=fs.readFileSync(path.join(skills,relative),'utf8').split(/\r?\n/);
  for(const prefix of prefixes){
    const line=current.find(x=>x.startsWith(prefix));
    const oldPrefix=prefix==='Price risk plus reserve budget ='?'Price risk budget =':prefix;
    const matches=builder.map((x,i)=>x.startsWith(oldPrefix)?i:-1).filter(i=>i>=0);
    if(!line||matches.length!==1)throw Error('Builder paragraph mismatch: '+prefix);
    builder[matches[0]]=line;
  }
}
fs.writeFileSync(builderPath,builder.join('\n'));
const config=JSON.parse(fs.readFileSync(path.join(workspace,'Trading_Manager_Config.json'),'utf8'));
const state=JSON.parse(fs.readFileSync(path.join(workspace,'Trading_Manager_State.json'),'utf8'));
const now=new Date().toISOString();
const journalPath=path.join(workspace,'trading-journal','risk_policy_'+now.replace(/[^0-9]/g,'')+'_'+process.pid+'.json');
const record={kind:'risk_policy_amendment',recordedUTC:now,version:config.version,risk_policy_revision:config.risk_policy_revision,authorization:{source:'direct_user_message',text:'اجازه داری ریسک رو تغییر بدی تا سقف ۱۰ درصد سرمایه'},previous:{active_risk_fraction:.01,hard_risk_fraction:.05,drawdown_halt_fraction:.02},current:{active_risk_fraction:config.active_risk_fraction,hard_risk_fraction:config.hard_risk_fraction,drawdown_halt_fraction:config.drawdown_halt_fraction},scope:config.risk_ceiling_scope,reason:'Apply explicit user ceiling authorization; no evidence currently supports increasing active risk.',strategy_fills_at_amendment:state.filled_entries,research_gate_passed:config.research_gate_passed,hypothesis:'A configurable authorized ceiling avoids policy drift; ceiling alone does not increase accepted volume while active risk and drawdown headroom bind.',acceptance_criteria:['price risk plus reserve <= all three configured limits','volume floors to broker step without tightening structural SL','one-position, 4-fill, 2-loss and 2% peak drawdown guards remain'],out_of_sample_status:'No new strategy fills; no evidence for active risk escalation.',implementation_status:'Applied in config, sizing, execution gate, installed skills and builder; automated tests not run in this amendment.'};
fs.writeFileSync(journalPath,JSON.stringify(record,null,2)+'\n',{flag:'wx'});
const toml=fs.readFileSync('C:/Users/SOC-Peyman/.codex/automations/mt5/automation.toml','utf8');
const field=key=>{const m=toml.match(new RegExp('^'+key+' = (.*)$','m'));if(!m)throw Error('Missing automation field '+key);return JSON.parse(m[1]);};
const prompt=field('prompt').replace('ریسک فعال۱٪، hard ceiling۵٪،','ریسک فعال ۱٪ باقی است؛ کاربر در ۸ اکتبر ۲۰۲۶ سقف مجاز مجموع ریسک قیمت پوزیشن‌های باز به‌اضافه ذخیره هزینه را به ۱۰٪ اکویتی افزایش داده است. hard ceiling=۱۰٪ هدف ورود نیست. بودجه حجم از min(ریسک فعال، headroom افت ۲٪ از قله حفظ‌شده، سقف مجاز ۱۰٪) با Trading_Manager_Config.json محاسبه شود. افزایش ریسک فعال همچنان به بازبینی ۱۲ساعته و شواهد خارج‌نمونه نیاز دارد.');
console.log(JSON.stringify({journalPath,automation:{id:field('id'),mode:'update',kind:field('kind'),destination:'thread',name:field('name'),prompt,status:field('status'),rrule:field('rrule'),targetThreadId:field('target_thread_id')}}));
