"""Read-only native verification of an already discarded demo request; no orders."""
import sys,json
from pathlib import Path
from datetime import datetime,timezone
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves')
pre=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
cfg=json.loads((W/'Trading_Manager_Config.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):
 raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or a.currency!='USD' or not t.connected:
  raise RuntimeError('matching_connected_demo_required')
 req=pre['request'];s=mt5.symbol_info(req['symbol']);pos=mt5.positions_get();orders=mt5.orders_get()
 if s is None or pos is None or orders is None:raise RuntimeError('native_metadata_or_exposure_unknown')
 typ=mt5.ORDER_TYPE_BUY if req['type']=='buy' else mt5.ORDER_TYPE_SELL
 loss=mt5.order_calc_profit(typ,req['symbol'],req['volume'],pre['entry'],req['sl'])
 margin=mt5.order_calc_margin(typ,req['symbol'],req['volume'],pre['entry'])
 if loss is None or margin is None:raise RuntimeError('native_calc_unknown')
 distance=abs(pre['entry']-req['sl'])
 out={'kind':'READ_ONLY_DISCARDED_REQUEST_RISK_AUDIT','observedUTC':datetime.now(timezone.utc).isoformat(),'requestNotResubmitted':True,'preflightPath':sys.argv[1],'accountLogin':a.login,'demo':True,'equityUSD':a.equity,'positions':len(pos),'orders':len(orders),'entryReference':pre['entry'],'SL':req['sl'],'TP':req['tp'],'volume':req['volume'],'contractSize':s.trade_contract_size,'brokerPoint':s.point,'priceRiskDistance':distance,'brokerPoints':distance/s.point,'conventionalFXPips':distance/0.0001 if req['symbol']=='GBPUSD' else None,'nativeSLProfitUSD':loss,'nativePriceRiskUSD':-loss,'equityRiskPct':-loss/a.equity*100,'nativeMarginUSD':margin,'feeReserveScenarioUSD':0.07,'referenceOnePercentUSD':a.equity*.01,'onePercentIsBenchmarkNotCurrentRule':True,'currentFinancialPolicy':cfg['risk_policy']['type'],'authorization':cfg['risk_policy']['authorization']['source']}
 path=W/'trading-journal'/('discarded_request_risk_audit_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with path.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2)
 print(json.dumps({'path':str(path),**out}),flush=True)
finally:mt5.shutdown()
