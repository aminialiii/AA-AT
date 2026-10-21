"""Read-only native broker inventory; no orders, symbol selection or account changes."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
root=Path('E:/GPT/Inves')
cfg=json.loads((root/'Trading_Manager_Config.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('matching_demo_account_required')
 all=mt5.symbols_get()
 if all is None:raise RuntimeError('catalog_unknown')
 data={'recordedUTC':datetime.now(timezone.utc).isoformat(),'account':{'login':str(a.login),'server':a.server,'currency':a.currency},'total':mt5.symbols_total(),'symbols':[s._asdict() for s in all]}
 p=root/'trading-journal'/('native_all_symbols_catalog_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(data,f)
 types={}
 for s in all:types[str(s.trade_calc_mode)]=types.get(str(s.trade_calc_mode),0)+1
 crypto=[{'name':s.name,'description':s.description,'path':s.path,'calc':s.trade_calc_mode,'volume_min':s.volume_min} for s in all if 'Crypto' in s.path or 'Bitcoin' in s.description or 'Ethereum' in s.description]
 print(json.dumps({'path':str(p),'count':len(all),'total':data['total'],'types':types,'cryptoExamples':crypto[:20],'visible':[s.name for s in all if s.visible]}))
finally:mt5.shutdown()
