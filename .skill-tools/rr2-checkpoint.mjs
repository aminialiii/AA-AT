import fs from 'node:fs';
const W='E:/GPT/Inves',p=W+'/Trading_Manager_State.json',s=JSON.parse(fs.readFileSync(p,'utf8'));
if(!s.version.startsWith('DEMO_7_SYMBOLS_RR2_'))throw Error('wrong_version');
if(process.argv[2]==='hold'){s.entry_hold={reason:process.argv[3],evidencePath:process.argv[4],recordedUTC:new Date().toISOString()};s.stage='BLOCKED_ENTRY';}
else throw Error('unknown_mode');
const audit=W+'/trading-journal/rr2_entry_hold_'+Date.now()+'.json';fs.writeFileSync(audit,JSON.stringify(s.entry_hold,null,2),{flag:'wx'});fs.writeFileSync(p,JSON.stringify(s,null,2));console.log(JSON.stringify({status:s.stage,path:audit}));
