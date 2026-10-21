"""Read-only broker request validation. order_check does not place, modify or cancel orders."""
import json,time,sys,math
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');c=json.loads((W/'Trading_Manager_Config.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info();ps,os=mt5.positions_get(),mt5.orders_get()
 if a is None or t is None or str(a.login)!=c['account_login'] or a.server!=c['account_server'] or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or a.currency!='USD' or not t.connected or ps is None or os is None:raise RuntimeError('demo_gate')
 symbol='USDCAD';s,q=mt5.symbol_info(symbol),mt5.symbol_info_tick(symbol);now=time.time()
 if s is None or q is None or not 0<=now-(q.time-c['broker_UTC_offset_minutes']*60)<=5:raise RuntimeError('quote_not_fresh')
 tick=s.trade_tick_size;gap=max(10*tick,3*(q.ask-q.bid),(s.trade_stops_level+2)*s.point);price=round(math.floor((q.ask-gap)/tick)*tick,s.digits);sl=round(price-10*gap,s.digits);tp=round(price+20*gap,s.digits)
 tests=[]
 for seconds in (45,120,300):
  expiry=int(time.time()+c['broker_UTC_offset_minutes']*60+seconds)
  request={'action':mt5.TRADE_ACTION_PENDING,'symbol':symbol,'volume':s.volume_min,'type':mt5.ORDER_TYPE_BUY_LIMIT,'price':price,'sl':sl,'tp':tp,'type_time':mt5.ORDER_TIME_SPECIFIED,'expiration':expiry,'type_filling':mt5.ORDER_FILLING_RETURN}
  r=mt5.order_check(request)
  if r is None:result={'error':mt5.last_error()}
  else:result=r._asdict();result['request']=r.request._asdict()
  tests.append({'lifetimeSeconds':seconds,'request':request,'result':result})
 p=W/'trading-journal'/('rr2_expiry_readonly_check_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump({'kind':'READ_ONLY_ORDER_CHECK_NO_SEND','tests':tests,'positionsBefore':[x._asdict() for x in ps],'ordersBefore':[x._asdict() for x in os],'ordersSent':0},f)
 print(json.dumps({'path':str(p),'ordersSent':0,'checks':[{'seconds':x['lifetimeSeconds'],'retcode':x['result'].get('retcode'),'comment':x['result'].get('comment')} for x in tests]}))
finally:mt5.shutdown()
