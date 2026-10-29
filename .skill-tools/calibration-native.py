"""Read-only native execution calibration support; never sends or changes orders."""
import sys,json,math,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');J=W/'trading-journal'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def save(kind,data):
 p=J/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(data,f)
 return str(p)
cfg=read(W/'Trading_Manager_Config.json');offset=cfg['broker_UTC_offset_minutes']
protocol_path=W/'.skill-tools/calibration-protocol-v1.json'
if '--protocol' in sys.argv:
 arg=sys.argv.index('--protocol');protocol_path=Path(sys.argv[arg+1]);del sys.argv[arg:arg+2]
protocol=read(protocol_path)
def base():
 state=read(W/'Trading_Manager_State.json');a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected or not a.trade_allowed:raise RuntimeError('demo_account_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 return state,a,t,positions,orders,int(datetime.now(timezone.utc).timestamp()*1000)
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 mode=sys.argv[1]
 state,a,t,positions,orders,now=base()
 if mode=='prepare':
  reasons=[]
  current=read(W/'Trading_Manager_Config.json')
  if state['run_status']!='ACTIVE' or not current['enabled'] or current['risk_policy']['type']!='user_waiver_demo_only':reasons.append('not_active_or_unsupported_policy')
  if now>=stamp(cfg['session_end_utc']):reasons.append('session_end')
  if state.get('pending_intent') or state.get('unknown_execution_outcome') or state.get('owned_positions'):reasons.append('unreconciled_agent_exposure')
  if positions or orders:reasons.append('calibration_requires_flat_baseline_for_attribution')
  if protocol['id'] in state.get('consumed_signals',[]) or any(x.get('dedupKey')==protocol['id'] for x in state.get('intents',[])):reasons.append('calibration_already_attempted')
  s,q=mt5.symbol_info('XAUUSD'),mt5.symbol_info_tick('XAUUSD');rates=mt5.copy_rates_from_pos('XAUUSD',mt5.TIMEFRAME_M1,0,10)
  if s is None or q is None or rates is None:raise RuntimeError('market_unknown')
  quote=q.time_msc-offset*60000;age=(now-quote)/1000
  if age<0 or age>5:reasons.append('stale_quote_or_clock_unknown')
  if not s.visible or s.trade_mode!=mt5.SYMBOL_TRADE_MODE_FULL:reasons.append('symbol_not_tradable')
  bars=[{'t':int(x['time'])*1000-offset*60000,'high':float(x['high'])} for x in rates if int(x['time'])*1000-offset*60000+60000<=now][-5:]
  if len(bars)!=5 or bars[-1]['t']!=now//60000*60000-60000 or any(i and x['t']-bars[i-1]['t']!=60000 for i,x in enumerate(bars)):reasons.append('closed_bar_coverage')
  sl=round(math.ceil((max(x['high'] for x in bars)+.02-1e-8)/s.trade_tick_size)*s.trade_tick_size,s.digits)
  volume=math.floor((protocol['volume']+1e-10)/s.volume_step)*s.volume_step
  if volume<s.volume_min or volume>s.volume_max:reasons.append('broker_volume')
  distance=sl-q.bid;tp=round(math.floor((q.bid-2*distance+1e-8)/s.trade_tick_size)*s.trade_tick_size,s.digits)
  if distance<=0 or sl-q.ask<=s.trade_stops_level*s.point or q.ask-tp<s.trade_stops_level*s.point:reasons.append('structural_SL_TP')
  loss=mt5.order_calc_profit(mt5.ORDER_TYPE_SELL,'XAUUSD',volume,q.bid,sl);margin=mt5.order_calc_margin(mt5.ORDER_TYPE_SELL,'XAUUSD',volume,q.bid)
  if loss is None or loss>=0 or margin is None or margin<=0:reasons.append('native_margin_or_profit_unknown')
  elif margin>a.margin_free:reasons.append('broker_free_margin')
  news=read(W/'.skill-tools/micromap-news-cache.json')
  if now-stamp(news['metadataUTC'])>15*60000 or now-stamp(news['collectedUTC'])>5*60000 or not news['calendar']['ok'] or news['calendar']['truncated']:reasons.append('news_unknown_or_stale')
  catalog={str(x['id']):x for x in news['events']['events']}
  for v in news['calendar']['values']:
   e=catalog.get(str(v['event_id']))
   if not e or e['importance']!='High importance':continue
   if v.get('time_unknown') or not v.get('time'):reasons.append('news_time_unknown');continue
   release=stamp(v['time']+'Z')-offset*60000
   if now<=release+15*60000 and now+60000>=release-15*60000:reasons.append('USD_news')
  deals=mt5.history_deals_get(datetime.fromtimestamp((stamp(cfg['session_start_utc'])-120000)/1000,timezone.utc)+timedelta(minutes=offset),datetime.fromtimestamp(now/1000,timezone.utc)+timedelta(minutes=offset))
  out={'status':'skip' if reasons else 'ready','reasons':reasons,'experiment':'EXECUTION_CALIBRATION_NOT_STRATEGY','version':protocol['id'],'dedupKey':protocol['id'],'observedUTC':iso(now),'expiresUTC':iso(now+45000),'riskPolicy':cfg['risk_policy_revision'],'oldFinancialCapsApplied':False,'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'symbol':s._asdict(),'tick':q._asdict(),'quoteAgeSeconds':age,'closedBars':bars,'request':{'symbol':'XAUUSD','type':'sell','volume':round(volume,8),'sl':sl,'tp':tp,'comment':protocol['comment']},'entryReference':q.bid,'initialRiskUSD':-loss if loss is not None else None,'nativeMarginUSD':margin,'manualDealsSinceSession':None if deals is None else [x._asdict() for x in deals]}
  path=save('execution_calibration_preflight',out);print(json.dumps({'status':out['status'],'reasons':reasons,'path':path,'request':out['request'],'entryReference':q.bid,'initialRiskUSD':out['initialRiskUSD'],'marginUSD':margin,'freeMarginUSD':a.margin_free,'quoteAgeSeconds':age,'observedUTC':out['observedUTC'],'expiresUTC':out['expiresUTC']}),flush=True)
 elif mode=='positions':
  wanted=[x._asdict() for x in positions if x.comment==protocol['comment']]
  start=datetime.fromtimestamp((now-5*60000)/1000,timezone.utc)+timedelta(minutes=offset);end=datetime.fromtimestamp(now/1000,timezone.utc)+timedelta(minutes=offset)
  history_orders=mt5.history_orders_get(start,end);history_deals=mt5.history_deals_get(start,end);historical_fills=[]
  if history_orders is not None and history_deals is not None:
   for o in history_orders:
    if o.comment!=protocol['comment'] or o.state!=mt5.ORDER_STATE_FILLED:continue
    entries=[d for d in history_deals if d.order==o.ticket and d.entry==mt5.DEAL_ENTRY_IN]
    if not entries:continue
    vol=sum(d.volume for d in entries);price=sum(d.price*d.volume for d in entries)/vol;identifier=entries[0].position_id
    if any(x.identifier==identifier for x in positions):continue
    historical_fills.append({'ticket':identifier,'identifier':identifier,'time_msc':min(d.time_msc for d in entries),'type':entries[0].type,'volume':vol,'price_open':price,'sl':o.sl,'tp':o.tp,'symbol':o.symbol,'comment':o.comment,'historicalOrder':o._asdict(),'entryDeals':[d._asdict() for d in entries],'positionObservedOpen':False})
  out={'observedUTC':iso(now),'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'matchingPositions':wanted,'historicalFills':historical_fills}
  path=save('execution_calibration_verification',out);print(json.dumps({'path':path,'observedUTC':out['observedUTC'],'matchingPositions':wanted,'historicalFills':historical_fills,'allPositionCount':len(positions),'equityUSD':a.equity}),flush=True)
 elif mode=='watch':
  ticket=int(sys.argv[2]);samples=[]
  while True:
   state,a,t,positions,orders,now=base();p=next((x for x in positions if x.ticket==ticket),None);q=mt5.symbol_info_tick('XAUUSD')
   sample={'observedUTC':iso(now),'position':p._asdict() if p else None,'tick':q._asdict() if q else None,'account':a._asdict()};samples.append(sample)
   if p is None:status='CLOSED';break
   if p.comment!=protocol['comment'] or p.symbol!='XAUUSD':raise RuntimeError('owned_ticket_mismatch')
   if p.sl==0 or p.tp==0:status='PROTECTION_REQUIRED';break
   age=(now-(p.time_msc-offset*60000))/1000
   current=read(W/'Trading_Manager_Config.json')
   if state['run_status']!='ACTIVE' or not current['enabled'] or now>=stamp(cfg['session_end_utc']):status='CLOSE_REQUIRED_STOP_OR_SESSION';break
   if age>=protocol.get('closeRequestAtSeconds',40):status='CLOSE_REQUIRED_TIME';break
   print(json.dumps({'status':'MANAGING','ticket':ticket,'holdingSeconds':age,'profitUSD':p.profit,'observedUTC':iso(now)}),flush=True)
   time.sleep(5)
  path=save('execution_calibration_management',{'ticket':ticket,'status':status,'samples':samples});print(json.dumps({'status':status,'ticket':ticket,'path':path}),flush=True)
 elif mode=='reconcile':
  ticket=int(sys.argv[2]);pre=read(sys.argv[3]);verification=read(sys.argv[4]);p=next(x for x in verification['matchingPositions']+verification.get('historicalFills',[]) if x['ticket']==ticket)
  start=datetime.fromtimestamp((p['time_msc']-offset*60000-60000)/1000,timezone.utc)+timedelta(minutes=offset);end=datetime.fromtimestamp(now/1000,timezone.utc)+timedelta(minutes=offset)
  deals=mt5.history_deals_get(start,end)
  if deals is None:raise RuntimeError('native_deals_unknown')
  own=[x._asdict() for x in deals if x.position_id==p['identifier']]
  closed=not any(x.ticket==ticket for x in positions) and any(x['entry'] in [1,2,3] for x in own)
  if not closed:raise RuntimeError('exit_not_reconciled')
  typ=mt5.ORDER_TYPE_BUY if p['type']==0 else mt5.ORDER_TYPE_SELL
  risk=abs(mt5.order_calc_profit(typ,'XAUUSD',p['volume'],p['price_open'],p['sl'])) if p['sl']>0 else None
  gross=sum(x['profit'] for x in own);fees=sum(x['commission']+x['swap']+x['fee'] for x in own);net=gross+fees
  exit_ms=max(x['time_msc'] for x in own);ticks=mt5.copy_ticks_range('XAUUSD',datetime.fromtimestamp(p['time_msc']/1000,timezone.utc),datetime.fromtimestamp(exit_ms/1000,timezone.utc),mt5.COPY_TICKS_ALL)
  mae=mfe=None;gap=None
  if ticks is not None and len(ticks):
   valid=[x for x in ticks if float(x['ask'])>=float(x['bid'])>0]
   if valid:
    mae=max(0,max(p['price_open']-float(x['bid']) if typ==mt5.ORDER_TYPE_BUY else float(x['ask'])-p['price_open'] for x in valid));mfe=max(0,max(float(x['bid'])-p['price_open'] if typ==mt5.ORDER_TYPE_BUY else p['price_open']-float(x['ask']) for x in valid))
   gap=max([0]+[(int(ticks[k]['time_msc'])-int(ticks[k-1]['time_msc']))/1000 for k in range(1,len(ticks))])
  others=[x._asdict() for x in deals if x.position_id!=p['identifier'] and x.time_msc-offset*60000>=stamp(pre['observedUTC'])]
  out={'recordedUTC':iso(now),'kind':'ACTUAL_DEMO_STRATEGY' if protocol.get('countsAsMicroMAPStrategyTrade') else 'ACTUAL_DEMO_EXECUTION_CALIBRATION_NOT_STRATEGY','ticket':ticket,'identifier':p['identifier'],'protocol':protocol,'preflightPath':sys.argv[3],'verificationPath':sys.argv[4],'deals':own,'grossUSD':gross,'commissionUSD':sum(x['commission'] for x in own),'swapUSD':sum(x['swap'] for x in own),'feesUSD':sum(x['fee'] for x in own),'netUSD':net,'initialRiskUSD':risk,'netR':net/risk if risk else None,'entry':p['price_open'],'initialSL':p['sl'],'initialTP':p['tp'],'volume':p['volume'],'holdingSeconds':(exit_ms-p['time_msc'])/1000,'MAEPriceObserved':mae,'MFEPriceObserved':mfe,'maximumHistoricalTickGapSeconds':gap,'tickCoverageIsCompleteClaim':False,'preflightReferenceSlippagePrice':(p['price_open']-pre.get('entryReference',pre.get('entry'))) if typ==mt5.ORDER_TYPE_BUY else (pre.get('entryReference',pre.get('entry'))-p['price_open']),'baselineBalanceUSD':pre['account']['balance'],'currentBalanceUSD':a.balance,'otherDealsInWindow':others,'balanceBridgeResidualUSD':a.balance-pre['account']['balance']-net-sum(x['profit']+x['commission']+x['swap']+x['fee'] for x in others),'remainingPositions':[x._asdict() for x in positions],'ticks':None if ticks is None else [{'time_msc':int(x['time_msc']),'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks]}
  path=save('execution_calibration_reconciled',out);print(json.dumps({k:out[k] for k in ['ticket','grossUSD','commissionUSD','swapUSD','feesUSD','netUSD','initialRiskUSD','netR','holdingSeconds','MAEPriceObserved','MFEPriceObserved','currentBalanceUSD','balanceBridgeResidualUSD']}|{'path':path,'remainingPositions':len(positions)}),flush=True)
finally:mt5.shutdown()
