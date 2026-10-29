"""Read-only XAUUSD native profit/margin diagnostics; no orders or account changes."""
import sys,json,math
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
cfg=json.loads(Path('E:/GPT/Inves/Trading_Manager_Config.json').read_text(encoding='utf-8'))
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('native_account_gate')
 s,q=mt5.symbol_info('XAUUSD'),mt5.symbol_info_tick('XAUUSD')
 if s is None or q is None:raise RuntimeError('native_symbol_missing')
 if len(sys.argv)>1:
  candidate=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
  state=json.loads(Path('E:/GPT/Inves/Trading_Manager_State.json').read_text(encoding='utf-8'))
  now=datetime.now(timezone.utc);reason=None
  if candidate.get('status')!='analysis_ready' or candidate.get('version')!=cfg['version'] or candidate.get('symbol')!='XAUUSD':reason='candidate_gate'
  elif now>=datetime.fromisoformat(candidate['expiresUTC'].replace('Z','+00:00')):reason='expired'
  elif len(mt5.positions_get() or []) or len(mt5.orders_get() or []) or state.get('pending_intent') or state.get('unknown_execution_outcome'):reason='exposure_or_intent'
  elif state['filled_entries']>=cfg['max_entries'] or state['closed_losses']>=cfg['max_closed_losses'] or a.equity<=state['observed_peak_equity']*(1-cfg['drawdown_halt_fraction']):reason='session_halt'
  elif (now.timestamp()-(q.time_msc/1000-cfg['broker_UTC_offset_minutes']*60))>cfg['max_quote_age_seconds']:reason='stale_quote'
  elif q.ask-q.bid>cfg['spread_max_price']:reason='spread'
  elif candidate['dedupKey'] in state.get('consumed_signals',[]) or any(x.get('dedupKey')==candidate['dedupKey'] for x in state.get('intents',[])):reason='duplicate'
  if reason:print(json.dumps(dict(status='skip',code=reason,observedUTC=now.isoformat())));sys.exit(0)
  side=candidate['side'];typ=mt5.ORDER_TYPE_BUY if side=='buy' else mt5.ORDER_TYPE_SELL;entry=q.ask if side=='buy' else q.bid
  sl=(math.floor(candidate['structuralSL']/s.trade_tick_size) if side=='buy' else math.ceil(candidate['structuralSL']/s.trade_tick_size))*s.trade_tick_size
  sl=round(sl,s.digits);liquidation=q.bid if side=='buy' else q.ask
  if (liquidation-sl if side=='buy' else sl-liquidation)<s.trade_stops_level*s.point:print(json.dumps(dict(status='skip',code='stop_level')));sys.exit(0)
  peak=max(state['observed_peak_equity'],a.equity);budget=min(a.equity*cfg['active_risk_fraction'],a.equity-peak*(1-cfg['drawdown_halt_fraction']),a.equity*cfg['hard_risk_fraction'])
  extra=cfg['spread_widening_reserve_price']+cfg['slippage_reserve_price']
  reserve_close=entry-extra if side=='buy' else entry+extra
  minrisk=abs(mt5.order_calc_profit(typ,'XAUUSD',s.volume_min,entry,sl));minreserve=abs(mt5.order_calc_profit(typ,'XAUUSD',s.volume_min,entry,reserve_close))+cfg['round_trip_commission_per_lot']*s.volume_min
  volume=math.floor((budget/(minrisk+minreserve)*s.volume_min)/s.volume_step+1e-10)*s.volume_step
  if volume<s.volume_min:print(json.dumps(dict(status='skip',code='min_volume_risk',budgetUSD=budget,minPriceRiskUSD=minrisk,minReserveUSD=minreserve,entry=entry,sl=sl)));sys.exit(0)
  volume=round(min(volume,s.volume_max),8);margin=mt5.order_calc_margin(typ,'XAUUSD',volume,entry)
  if margin is None or margin>a.margin_free*.5:print(json.dumps(dict(status='skip',code='margin',margin=margin,margin_free=a.margin_free)));sys.exit(0)
  risk=abs(mt5.order_calc_profit(typ,'XAUUSD',volume,entry,sl));reserve=abs(mt5.order_calc_profit(typ,'XAUUSD',volume,entry,reserve_close))+cfg['round_trip_commission_per_lot']*volume
  if risk+reserve>budget+1e-8:raise RuntimeError('risk_rounding_failed')
  d=abs(entry-sl);tp=round((math.ceil((entry+2*d)/s.trade_tick_size) if side=='buy' else math.floor((entry-2*d)/s.trade_tick_size))*s.trade_tick_size,s.digits)
  print(json.dumps(dict(status='ready',symbol='XAUUSD',type=side,volume=volume,entry=entry,sl=sl,tp=tp,initialRiskUSD=risk,reserveUSD=reserve,totalRiskUSD=risk+reserve,budgetUSD=budget,margin=margin,margin_free=a.margin_free,observedUTC=now.isoformat(),dedupKey=candidate['dedupKey'],expiresUTC=candidate['expiresUTC'],comment=cfg['entry_comment'],source='native_OrderCalcProfit_and_OrderCalcMargin')));sys.exit(0)
 rows=[]
 for side,typ,entry in [('buy',mt5.ORDER_TYPE_BUY,q.ask),('sell',mt5.ORDER_TYPE_SELL,q.bid)]:
  for distance in [.1,.25,.5,1,2,5]:
   sl=entry-distance if side=='buy' else entry+distance
   rows.append(dict(side=side,volume=s.volume_min,entry=entry,sl=sl,distance=distance,priceRiskUSD=abs(mt5.order_calc_profit(typ,'XAUUSD',s.volume_min,entry,sl)),margin=mt5.order_calc_margin(typ,'XAUUSD',s.volume_min,entry)))
 print(json.dumps(dict(observedUTC=datetime.now(timezone.utc).isoformat(),login=str(a.login),server=a.server,equity=a.equity,margin_free=a.margin_free,positions=len(mt5.positions_get() or []),orders=len(mt5.orders_get() or []),symbol=s._asdict(),tick=q._asdict(),rows=rows)))
finally:mt5.shutdown()
