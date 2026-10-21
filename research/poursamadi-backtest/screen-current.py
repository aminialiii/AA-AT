"""Read-only current MicroMAP agent-interpretation screen. Never sends orders."""
import sys,json,hashlib,math,bisect
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
ROOT=Path('E:/GPT/Inves/research/poursamadi-backtest')
model=json.loads((ROOT/'model-v1.json').read_text())
cfg=json.loads(Path('E:/GPT/Inves/Trading_Manager_Config.json').read_text())
offset=cfg['broker_UTC_offset_minutes']
source=(ROOT/'backtest.py').read_text()
scanner=source[source.index('setups=[];bar_gaps=[]'):source.index("plan={'registeredUTC'")]
def iso(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat()
activation=int(datetime.fromisoformat(model['registeredUTC'].replace('Z','+00:00')).timestamp()*1000)
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('account_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 rates=mt5.copy_rates_from_pos('XAUUSD',mt5.TIMEFRAME_M1,0,200)
 q=mt5.symbol_info_tick('XAUUSD');spec=mt5.symbol_info('XAUUSD')
 if rates is None or q is None or spec is None:raise RuntimeError('market_unknown')
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 bars=[dict(t=int(x['time'])*1000-offset*60000,open=float(x['open']),high=float(x['high']),low=float(x['low']),close=float(x['close'])) for x in rates if int(x['time'])*1000-offset*60000+60000<=now]
 bars.sort(key=lambda x:x['t'])
 exec(scanner)
 fresh=[x for x in setups if x['origin']>=activation]
 current=[(x,ar) for x in fresh for ar in x['arms'] if ar['armed']<=now<ar['expires']]
 age=(now-(q.time_msc-offset*60000))/1000
 reasons=[]
 if positions or orders:reasons.append('external_or_owned_exposure_requires_reconciliation')
 if not bars or bars[-1]['t']!=now//60000*60000-60000:reasons.append('latest_closed_M1_missing')
 if age<0 or age>5:reasons.append('quote_stale_or_clock_unknown')
 if not current:reasons.append('no_fresh_active_setup')
 result_path=ROOT/'backtest_result_20261008T153525891254Z.json'
 result=json.loads(result_path.read_text())
 if not result['researchGatePassed']:reasons.append('research_gate_failed')
 candidates=[]
 for setup,ar in current:
  price_risk=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',spec.volume_min,q.ask,ar['sl'])
  margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,'XAUUSD',spec.volume_min,q.ask)
  reserve=spec.trade_contract_size*spec.volume_min*.2+7*spec.volume_min
  peak=max(a.equity,100.55)
  budget=min(a.equity*.01,a.equity-peak*.98,a.equity*.1)
  candidates.append({'setupId':setup['id'],'arm':ar,'bidCurrentlyAboveTrigger':q.bid>=ar['trigger'],'minimumPriceRiskUSD':-price_risk if price_risk is not None else None,'reserveUSD':reserve,'minimumMarginUSD':margin,'riskBudgetUSD':budget,'minimumVolumeFits':price_risk is not None and price_risk<0 and -price_risk+reserve<=budget})
 output={'recordedUTC':iso(now),'version':model['version'],'modelLabel':'تفسیر ایجنت','backtestPath':str(result_path),'scannerSourceHash':hashlib.sha256(source.encode()).hexdigest(),'brokerOffsetMinutes':offset,'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'symbol':spec._asdict(),'tick':q._asdict(),'quoteAgeSeconds':age,'lastClosedM1UTC':iso(bars[-1]['t']) if bars else None,'closedBars':bars,'activationUTC':model['registeredUTC'],'freshSetupsSinceActivation':fresh,'candidates':candidates,'decision':'BLOCKED_ENTRY' if reasons else 'ANALYSIS_ONLY_PENDING_NEWS_AND_EXECUTION_GATE','reasons':reasons,'ordersSubmitted':0}
 path=ROOT/('current_screen_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with path.open('x',encoding='utf-8') as f:json.dump(output,f,ensure_ascii=False)
 print(json.dumps({'path':str(path),'equityUSD':a.equity,'positions':len(positions),'orders':len(orders),'quoteAgeSeconds':age,'freshSetups':len(fresh),'candidates':len(candidates),'decision':output['decision'],'reasons':reasons}))
finally:mt5.shutdown()
