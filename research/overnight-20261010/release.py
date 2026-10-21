"""Release only the authorized overnight research entry suspension after 9 Tehran.
Local state accounting only; no broker mutation or strategy promotion.
"""
import json,os,sys,hashlib
from pathlib import Path
from datetime import datetime,timezone
R=Path('E:/GPT/Inves/research/overnight-20261010');W=R.parents[1]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
now=datetime.now(timezone.utc);r=read(R/'state.json');req=read(R/'request.json')
if now<datetime.fromisoformat(req['deadlineUTC'].replace('Z','+00:00')):raise RuntimeError('not_before_9_Tehran')
if r.get('holdoutStatus')!='COMPLETE' or not r.get('latestReportJSON'):raise RuntimeError('completed_final_report_required')
report=read(r['latestReportJSON'])
if not report.get('holdout') or not report.get('charts'):raise RuntimeError('final_report_and_charts_required')
s=read(W/'Trading_Manager_State.json');session=s.get('research_session',{})
if session.get('version')!='OVERNIGHT_RR2_RESEARCH_1':raise RuntimeError('research_version_mismatch')
if not session.get('entriesSuspended'):print(json.dumps({'status':'already_released','brokerMutations':0}));sys.exit(0)
baseline={k:s.get(k) for k in ['entry_hold','unknown_execution_outcome','pending_intent','owned_positions','owned_orders','hundred','run_status','market_data_wait']}
session.update(entriesSuspended=False,completedUTC=now.isoformat(),finalReportPath=r['latestReport'],strategyPromotionAllowed=False)
event=R/('research_release_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with event.open('x',encoding='utf-8') as f:json.dump({'observedUTC':now.isoformat(),'action':'RELEASE_ONLY_OVERNIGHT_RESEARCH_ENTRY_SUSPENSION','finalReportPath':r['latestReport'],'approvalHoldsUnchanged':True,'actualCountsUnchanged':True,'brokerMutations':0},f,ensure_ascii=False,indent=2)
if baseline!={k:s.get(k) for k in baseline}:raise RuntimeError('unrelated_state_change')
tmp=W/'Trading_Manager_State.research_release.tmp';tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,W/'Trading_Manager_State.json')
print(json.dumps({'status':'RESEARCH_SUSPENSION_RELEASED','eventPath':str(event),'brokerMutations':0}))
