"""Read all owned demo positions/orders together; no trade operations or settings."""
import json,time,sys
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves')
def read(p):return json.loads(p.read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
samples=[];expiry_due=False
try:
 for _ in range(8):
  c=read(W/'Trading_Manager_Config.json');s=read(W/'Trading_Manager_State.json');a=mt5.account_info();t=mt5.terminal_info();ps=mt5.positions_get();os=mt5.orders_get()
  if a is None or t is None or ps is None or os is None or str(a.login)!=c['account_login'] or a.server!=c['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('demo_or_exposure_unknown')
  rows=[];changed=False
  for owner in s.get('owned_positions',[]):
   p=next((p for p in ps if p.ticket==owner['ticket']),None);q=mt5.symbol_info_tick(owner['symbol'])
   if p is None:changed=True
   elif p.comment!=owner['dedupKey'] or p.sl!=owner['initialSL'] or p.tp!=owner['initialTP'] or not p.sl or not p.tp:raise RuntimeError('protection_or_ownership_changed')
   rows.append({'symbol':owner['symbol'],'ticket':owner['ticket'],'position':p._asdict() if p else None,'quote':q._asdict() if q else None})
  for owner in s.get('owned_orders',[]):
   o=next((o for o in os if o.ticket==owner['orderTicket']),None)
   if o is None:changed=True
   rows.append({'symbol':owner['symbol'],'orderTicket':owner['orderTicket'],'order':o._asdict() if o else None})
  samples.append({'observedUTC':datetime.now(timezone.utc).isoformat(),'account':a._asdict(),'exposure':rows})
  if changed:break
  expiries=[datetime.fromisoformat(o['expirationUTC'].replace('Z','+00:00')).timestamp() for o in s.get('owned_orders',[]) if o.get('expiryPolicy')=='ACTIVE_MANAGER_CANCEL_UNFILLED_ONLY' and not o.get('cancelRequested')]
  remaining=min(expiries)-time.time() if expiries else None
  if remaining is not None and remaining<=0:expiry_due=True;break
  time.sleep(min(1,remaining) if remaining is not None else 1)
 p=W/'trading-journal'/('rr2_parallel_watch_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump({'samples':samples,'ordersSentByPython':0,'pendingExpiryDue':expiry_due},f)
 print(json.dumps({'status':'EXPOSURE_CHANGED' if changed else 'PENDING_EXPIRY_DUE' if expiry_due else 'WAITING_BROKER_SL_TP','path':str(p),'samples':len(samples)}))
finally:mt5.shutdown()
