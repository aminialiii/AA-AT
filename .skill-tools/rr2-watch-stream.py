"""Repeated read-only eight-observation chunks in one process; no trade mutations."""
import sys,json,runpy
from pathlib import Path
from datetime import datetime,timezone
W=Path('E:/GPT/Inves')
limit=int(sys.argv[1]) if len(sys.argv)>1 else 30
if not 1<=limit<=60:raise RuntimeError('bounded_read_only_chunks_required')
for index in range(limit):
 state=json.loads((W/'Trading_Manager_State.json').read_text(encoding='utf-8'))
 if not state.get('owned_positions') and not state.get('owned_orders'):
  print(json.dumps({'status':'JOURNAL_FLAT','chunk':index}),flush=True);break
 data=runpy.run_path(str(W/'.skill-tools/rr2-watch-all.py'))
 sys.stdout.flush()
 last=data['samples'][-1]
 quotes=[{'symbol':r['symbol'],'ticket':r.get('ticket',r.get('orderTicket')),'positionPresent':r.get('position') is not None,'profitUSD':r.get('position',{}).get('profit') if r.get('position') else None,'bid':r.get('quote',{}).get('bid') if r.get('quote') else None,'ask':r.get('quote',{}).get('ask') if r.get('quote') else None} for r in last['exposure']]
 print(json.dumps({'stage':'READ_ONLY_STREAM_CHUNK','chunk':index+1,'observedUTC':last['observedUTC'],'balanceUSD':last['account']['balance'],'equityUSD':last['account']['equity'],'quotes':quotes,'accountOrOrderMutations':0}),flush=True)
 if data['changed'] or data['expiry_due']:break
else:print(json.dumps({'status':'BOUNDED_STREAM_FINISHED','chunks':limit}),flush=True)
