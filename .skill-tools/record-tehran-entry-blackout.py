import json, os
from pathlib import Path
from datetime import datetime, timezone
W=Path('E:/GPT/Inves')
now=datetime.now(timezone.utc)
path=W/'trading-journal'/('direct_entry_blackout_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
event={'recordedUTC':now.isoformat(),'userInstruction':'چرخه رو فعال نگه دار؛ چرخه بک تست رو هم پیش ببر؛ ساعت های ۲۳ تا ۱:۳۰ معاملات انجام نده',
       'timezone':'Asia/Tehran','startInclusive':'23:00','endExclusive':'01:30',
       'recurringDaily':True,'blockNewEntries':True,'keepCycleActive':True,'keepResearchActive':True,
       'existingInitialSLTPRemainBrokerManaged':True,'manualCloseAuthorized':False}
with path.open('x',encoding='utf-8') as f:json.dump(event,f,ensure_ascii=False,indent=2)
policy={'enabled':True,'timezone':'Asia/Tehran','utcOffsetMinutes':210,'startInclusive':'23:00','endExclusive':'01:30','authorizationPath':str(path),'blockNewEntries':True}
for name in ['Trading_Manager_Config.json','Trading_Manager_State.json']:
    p=W/name; obj=json.loads(p.read_text(encoding='utf-8')); obj['entry_time_blackout']=policy.copy()
    if name=='Trading_Manager_State.json':obj['stage']='TEHRAN_ENTRY_BLACKOUT_RESEARCH_CONTINUES'
    tmp=p.with_suffix('.blackout.tmp')
    with tmp.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False,indent=2); f.flush();os.fsync(f.fileno())
    os.replace(tmp,p)
print(json.dumps({'recordPath':str(path),'policy':policy}))
