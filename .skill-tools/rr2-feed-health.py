"""Read broker feed freshness and initial protection; never mutate terminal state."""
import json,sys
from datetime import datetime,timezone
from pathlib import Path
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves')
c=json.loads((W/'Trading_Manager_Config.json').read_text(encoding='utf-8'))
s=json.loads((W/'Trading_Manager_State.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):
 raise RuntimeError(str(mt5.last_error()))
try:
 a,t,ps,os=mt5.account_info(),mt5.terminal_info(),mt5.positions_get(),mt5.orders_get()
 if a is None or t is None or ps is None or os is None or str(a.login)!=c['account_login'] or a.server!=c['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:
  raise RuntimeError('matching_demo_or_exposure_unavailable')
 now=datetime.now(timezone.utc);offset=c['broker_UTC_offset_minutes']*60000
 quotes=[]
 for name in c['symbols']:
  q=mt5.symbol_info_tick(name)
  age=(now.timestamp()*1000-(q.time_msc-offset))/1000 if q and q.time_msc>0 else None
  quotes.append({'symbol':name,'bid':q.bid if q else None,'ask':q.ask if q else None,'rawBrokerTickMS':q.time_msc if q else None,'quoteAgeSeconds':age})
 owners=[]
 for owner in s.get('owned_positions',[]):
  p=next((p for p in ps if p.ticket==owner['ticket']),None)
  if p is None:raise RuntimeError('reconcile_owned_first')
  if p.comment!=owner['dedupKey'] or abs(p.sl-owner['initialSL'])>1e-8 or abs(p.tp-owner['initialTP'])>1e-8 or not p.sl or not p.tp:
   raise RuntimeError('owned_initial_protection_changed')
  owners.append({'symbol':p.symbol,'ticket':p.ticket,'comment':p.comment,'SL':p.sl,'TP':p.tp,'volume':p.volume,'floatingProfitUSD':p.profit,'observedOpenSwapUSD':p.swap})
 stale=bool(quotes) and all(q['quoteAgeSeconds'] is not None and q['quoteAgeSeconds']>=120 for q in quotes)
 fresh=any(q['quoteAgeSeconds'] is not None and 0<=q['quoteAgeSeconds']<=c['max_quote_age_seconds'] and q['bid']>0 and q['ask']>=q['bid'] for q in quotes)
 out={'observedUTC':now.isoformat(),'account':{'login':str(a.login),'server':a.server,'currency':a.currency,'demo':True,'connected':t.connected,'balanceUSD':a.balance,'equityUSD':a.equity},'quotes':quotes,'allSelectedQuotesStale':stale,'atLeastOneFreshSelectedQuote':fresh,'ownedProtection':owners,'pendingCount':len(os),'accountOrOrderMutations':0,'offsetBasis':'previously_verified_config_broker_UTC_offset','brokerUTCOffsetMinutes':c['broker_UTC_offset_minutes']}
 path=W/'trading-journal'/('rr2_feed_health_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with path.open('x',encoding='utf-8') as f:json.dump(out,f)
 print(json.dumps({'path':str(path),**out}))
finally:mt5.shutdown()
