"""Bounded 15-second read-only gold screening. No broker mutations or orders."""
import json,subprocess,sys,time
from pathlib import Path
from datetime import datetime,timezone
root=Path('E:/GPT/Inves');start=time.monotonic()
for index in range(4):
 cfg=json.loads((root/'Trading_Manager_Config.json').read_text(encoding='utf-8'));state=json.loads((root/'Trading_Manager_State.json').read_text(encoding='utf-8'))
 if state['run_status']!='ACTIVE' or not cfg['enabled']:print(json.dumps(dict(status='STOPPED')),flush=True);break
 if datetime.now(timezone.utc)>=datetime.fromisoformat(cfg['session_end_utc'].replace('Z','+00:00')):print(json.dumps(dict(status='SESSION_ENDED')),flush=True);break
 if state['filled_entries']>=cfg['max_entries'] or state['closed_losses']>=cfg['max_closed_losses']:print(json.dumps(dict(status='SESSION_HALT')),flush=True);break
 call=subprocess.run([sys.executable,str(root/'.skill-tools/gold-observe.py'),'-'],capture_output=True,text=True)
 if call.returncode:raise RuntimeError(call.stderr or call.stdout)
 obs=json.loads(call.stdout.strip().splitlines()[-1])
 if obs['positions'] or obs['orders']:print(json.dumps(dict(status='MANAGEMENT_REQUIRED',snapshotPath=obs['snapshotPath'],positions=obs['positions'],orders=obs['orders'])),flush=True);break
 call=subprocess.run(['node',str(root/'.skill-tools/gold-native-analyze.mjs'),obs['snapshotPath']],capture_output=True,text=True)
 if call.returncode:raise RuntimeError(call.stderr or call.stdout)
 result=json.loads(call.stdout.strip());result['watchElapsedSeconds']=round(time.monotonic()-start,3)
 print(json.dumps(result),flush=True)
 if result['candidate']['status']=='analysis_ready':break
 if index<3:
  due=start+(index+1)*cfg.get('screen_interval_seconds',15)
  while time.monotonic()<due:
   time.sleep(min(1,due-time.monotonic()))
   state=json.loads((root/'Trading_Manager_State.json').read_text(encoding='utf-8'))
   if state['run_status']!='ACTIVE':sys.exit(0)
