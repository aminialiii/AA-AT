"""Native market reads / exact risk and margin only. No orders, login, symbol selection or settings changes."""
import sys,json,math,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');J=W/'trading-journal'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def nowms():return int(time.time()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def write(p,d,exclusive=True):
 with Path(p).open('x' if exclusive else 'w',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
def save(kind,d):
 p=J/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json');write(p,d);return str(p)
cfg=read(W/'Trading_Manager_Config.json');state=read(W/'Trading_Manager_State.json')
if cfg['version'] not in ('DEMO_7_SYMBOLS_RR2_MOMENTUM_1','DEMO_7_SYMBOLS_RR2_LIMIT_2','DEMO_7_SYMBOLS_RR2_LIMIT_COST_REPORT_3','DEMO_7_SYMBOLS_RR2_MANAGED_LIMIT_4','DEMO_7_SYMBOLS_RR2_NO_NEWS_5'):raise RuntimeError('wrong_version')
offset=cfg['broker_UTC_offset_minutes']*60000;protocol=read(cfg['experiment_protocol_path'])
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
def gate():
 local=datetime.now(timezone(timedelta(minutes=210)))
 minute=local.hour*60+local.minute
 blocked=read(W/'Trading_Manager_Config.json').get('entry_time_blackout',{})
 if blocked.get('enabled') and (minute>=1380 or minute<90):raise RuntimeError('TEHRAN_ENTRY_BLACKOUT_2300_0130')
 a,t=mt5.account_info(),mt5.terminal_info();ps,os=mt5.positions_get(),mt5.orders_get()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not a.trade_allowed or not t.connected:raise RuntimeError('matching_writable_demo_required')
 if ps is None or os is None:raise RuntimeError('exposure_unknown')
 s=read(W/'Trading_Manager_State.json');c=read(W/'Trading_Manager_Config.json')
 if s['run_status']!='ACTIVE' or not c['enabled']:raise RuntimeError('STOPPED')
 if s.get('research_session',{}).get('entriesSuspended'):raise RuntimeError('OVERNIGHT_RESEARCH_ONLY')
 if s.get('entry_hold'):raise RuntimeError('entry_hold:'+str(s['entry_hold']))
 if s['version']!=cfg['version']:raise RuntimeError('version_changed')
 if s.get('pending_intent') or s.get('unknown_execution_outcome'):raise RuntimeError('reconcile_owned_first')
 for owner in s.get('owned_positions',[]):
  active=next((p for p in ps if p.ticket==owner['ticket']),None)
  if active is None:raise RuntimeError('reconcile_owned_first')
  if not owner.get('protectionValidAtFill') or not active.sl or not active.tp:raise RuntimeError('unprotected_owned_exposure')
 for owner in s.get('owned_orders',[]):
  if owner.get('cancelRequested'):raise RuntimeError('pending_cancellation_needs_reconciliation')
  active=next((o for o in os if o.ticket==owner['orderTicket']),None)
  if active is None:raise RuntimeError('reconcile_owned_order_first')
  if not active.sl or not active.tp:raise RuntimeError('unprotected_pending_order')
 return a,ps,os,s
def news_gate(now):
 if cfg.get('news_filter_enabled') is False:return None
 try:n=read(W/'.skill-tools/rr2-news-cache.json')
 except Exception:return 'news_missing'
 if not n['calendar'].get('ok') or n['calendar'].get('truncated') or now-stamp(n['collectedUTC'])>300000 or now-stamp(n['metadataUTC'])>900000 or n['offsetMinutes']!=offset//60000:return 'news_unknown_or_stale'
 ev={str(e['id']):e for e in n['events']}
 for v in n['calendar']['values']:
  e=ev.get(str(v['event_id']))
  if not e:return 'news_metadata_missing'
  if e['importance']!='High importance':continue
  if v.get('time_unknown') or not v.get('time'):return 'high_news_time_unknown'
  release=stamp(v['time']+'Z')-offset
  if release-900000<=now<=release+900000:return 'high_news_block:'+e['name']
 return None
def candidate(name):
 if name not in cfg['symbols']:return {'symbol':name,'reason':'outside_explicit_seven_symbol_scope'}
 a,positions,orders,st=gate();now=nowms()
 if any(p['symbol']==name for p in st.get('owned_positions',[])):return {'symbol':name,'reason':'owned_position_already_open'}
 if any(o['symbol']==name for o in st.get('owned_orders',[])):return {'symbol':name,'reason':'owned_pending_order_already_open'}
 if sum(r['symbol']==name for r in st['hundred']['results'])>=cfg['target_per_symbol']:return {'symbol':name,'reason':'symbol_target_complete'}
 s=mt5.symbol_info(name);q=mt5.symbol_info_tick(name)
 if s is None or q is None:return {'symbol':name,'reason':'quote_or_contract_missing'}
 if not s.visible:return {'symbol':name,'reason':'Market_Watch_not_visible'}
 if s.trade_mode not in (mt5.SYMBOL_TRADE_MODE_FULL,mt5.SYMBOL_TRADE_MODE_LONGONLY,mt5.SYMBOL_TRADE_MODE_SHORTONLY):return {'symbol':name,'reason':'not_entry_tradable'}
 if not all(math.isfinite(x) and x>0 for x in [s.trade_tick_size,s.point,s.volume_min,s.volume_step,s.trade_contract_size]):return {'symbol':name,'reason':'contract_invalid'}
 limit=cfg.get('entry_order_policy') in ('LIMIT_WITH_BROKER_EXPIRY','LIMIT_WITH_MANAGED_EXPIRY')
 if any(not s.order_mode & bit for bit in ((2,16,32) if limit else (1,16,32))):return {'symbol':name,'reason':'entry_SL_TP_not_supported'}
 if cfg.get('entry_order_policy')=='LIMIT_WITH_BROKER_EXPIRY' and not s.expiration_mode & 4:return {'symbol':name,'reason':'broker_specified_expiry_not_supported'}
 age=(now-(q.time_msc-offset))/1000
 if not 0<=age<=5 or q.bid<=0 or q.ask<q.bid:return {'symbol':name,'reason':'quote_stale_or_invalid','ageSeconds':age}
 rates=mt5.copy_rates_from_pos(name,mt5.TIMEFRAME_M1,0,30)
 if rates is None:return {'symbol':name,'reason':'M1_history_unknown'}
 now=nowms();bars=sorted([{'t':int(b['time'])*1000-offset,'open':float(b['open']),'high':float(b['high']),'low':float(b['low']),'close':float(b['close'])} for b in rates if int(b['time'])*1000-offset+60000<=now],key=lambda b:b['t'])
 if len(bars)<16 or bars[-1]['t']!=now//60000*60000-60000 or any(bars[k]['t']-bars[k-1]['t']!=60000 for k in range(len(bars)-15,len(bars))):return {'symbol':name,'reason':'fresh_contiguous_closed_M1_missing'}
 if any(not b['low']<=min(b['open'],b['close'])<=max(b['open'],b['close'])<=b['high'] or b['low']<=0 for b in bars):return {'symbol':name,'reason':'OHLC_invalid'}
 atr=sum(max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(len(bars)-14,len(bars)))/14
 ticks=mt5.copy_ticks_range(name,datetime.fromtimestamp((now-120000+offset)/1000,timezone.utc),datetime.fromtimestamp((now+offset)/1000,timezone.utc),mt5.COPY_TICKS_ALL)
 if ticks is None:return {'symbol':name,'reason':'ticks_unknown'}
 pts=sorted([{'t':int(x['time_msc'])-offset,'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks if float(x['ask'])>=float(x['bid'])>0],key=lambda p:p['t'])
 if len(pts)<2:return {'symbol':name,'reason':'ticks_missing'}
 last=pts[-1];prev=[p for p in pts if p['t']<=last['t']-5000]
 if not prev or last['t']-5000-prev[-1]['t']>10000:return {'symbol':name,'reason':'five_second_reference_missing_or_gap'}
 if last['t']<stamp(protocol['signal']['activationUTC']) or now-last['t']>5000:return {'symbol':name,'reason':'trigger_pre_activation_or_stale'}
 delta=(last['bid']+last['ask']-prev[-1]['bid']-prev[-1]['ask'])/2
 q=mt5.symbol_info_tick(name);now=nowms()
 if q is None or not 0<q.bid<=q.ask or not 0<=now-(q.time_msc-offset)<=5000:return {'symbol':name,'reason':'fresh_quote_failed'}
 tick=s.trade_tick_size;spread=q.ask-q.bid
 if atr<=0 or spread/atr>protocol['costFilters']['maxSpreadATR']:return {'symbol':name,'reason':'spread_ATR_filter','spreadATR':spread/atr if atr else None}
 if abs(delta)+tick*1e-8<max(tick,0.5*spread):return {'symbol':name,'reason':'weak_or_zero_momentum'}
 side='buy' if delta>0 else 'sell';sign=1 if side=='buy' else -1
 if sign*(bars[-1]['close']-bars[-1]['open'])<tick-tick*1e-7:return {'symbol':name,'reason':'M1_direction_not_confirmed'}
 if side=='sell' and s.trade_mode==mt5.SYMBOL_TRADE_MODE_LONGONLY or side=='buy' and s.trade_mode==mt5.SYMBOL_TRADE_MODE_SHORTONLY:return {'symbol':name,'reason':'side_not_allowed'}
 volume=round(math.ceil((s.volume_min-s.volume_step*1e-7)/s.volume_step)*s.volume_step,8)
 if not s.volume_min<=volume<=s.volume_max:return {'symbol':name,'reason':'volume_invalid'}
 minimum=max(.5*atr,4*spread,(s.trade_stops_level+2)*s.point,2*tick)
 if side=='buy':
  entry=q.ask;sl=round(math.floor((min(min(b['low'] for b in bars[-2:])-2*tick,q.bid-minimum)+tick*1e-7)/tick)*tick,s.digits);typ=mt5.ORDER_TYPE_BUY
 else:
  entry=q.bid;sl=round(math.ceil((max(max(b['high'] for b in bars[-2:])+2*tick,q.ask+minimum)-tick*1e-7)/tick)*tick,s.digits);typ=mt5.ORDER_TYPE_SELL
 if sl<=0:return {'symbol':name,'reason':'SL_invalid'}
 if limit:
  gap=max(0.5*spread,(s.trade_stops_level+2)*s.point,2*tick)
  entry=round((math.floor((q.ask-gap+tick*1e-7)/tick) if side=='buy' else math.ceil((q.bid+gap-tick*1e-7)/tick))*tick,s.digits)
  if entry<=0 or sign*(entry-sl)<max((s.trade_stops_level+2)*s.point,2*tick):return {'symbol':name,'reason':'limit_entry_cannot_preserve_structural_SL'}
 loss=mt5.order_calc_profit(typ,name,volume,entry,sl);margin=mt5.order_calc_margin(typ,name,volume,entry)
 if loss is None or loss>=0 or margin is None or margin<0:return {'symbol':name,'reason':'exact_native_profit_margin_unknown'}
 risk=-loss;distance=abs(entry-sl)
 target=entry+sign*2*distance
 tp=round((math.ceil((target-tick*1e-7)/tick) if sign>0 else math.floor((target+tick*1e-7)/tick))*tick,s.digits)
 reward=mt5.order_calc_profit(typ,name,volume,entry,tp)
 for _ in range(100):
  if reward is not None and reward>=2*risk-1e-8:break
  tp=round(tp+sign*tick,s.digits)
  if tp<=0:break
  reward=mt5.order_calc_profit(typ,name,volume,entry,tp)
 if tp<=0 or reward is None or reward<2*risk-1e-8:return {'symbol':name,'reason':'native_RR2_invalid'}
 # Account-currency precision and tick lattice may exceed 2R by at most one target tick.
 one_tick_profit=mt5.order_calc_profit(typ,name,volume,tp,tp+sign*tick)
 if one_tick_profit is None or reward-2*risk>abs(one_tick_profit)+1e-6:return {'symbol':name,'reason':'native_RR2_rounding_invalid'}
 if limit:
  if min(abs(entry-sl),abs(tp-entry),q.ask-entry if side=='buy' else entry-q.bid)<=s.trade_stops_level*s.point:return {'symbol':name,'reason':'broker_pending_distance_invalid'}
 elif side=='buy' and (q.bid-sl<=s.trade_stops_level*s.point or tp-q.bid<=s.trade_stops_level*s.point) or side=='sell' and (sl-q.ask<=s.trade_stops_level*s.point or q.ask-tp<=s.trade_stops_level*s.point):return {'symbol':name,'reason':'broker_stop_distance_invalid'}
 reserve=mt5.order_calc_profit(typ,name,volume,entry,entry-sign*(spread+2*tick))
 if reserve is None:return {'symbol':name,'reason':'reserve_unknown'}
 reserve=abs(reserve)+protocol['costFilters']['feeScenarioUSD']
 if protocol['costFilters'].get('reserveMode','entry_filter')=='entry_filter' and reserve/risk>protocol['costFilters']['maxScenarioReserveVsInitialRisk']:return {'symbol':name,'reason':'cost_vs_risk_filter','scenarioReserveUSD':reserve,'riskUSD':risk}
 a,positions,orders,st=gate()
 reserved=sum(o.get('nativeMarginUSD',0) for o in st.get('owned_orders',[]))
 if margin+reserved>a.margin_free:return {'symbol':name,'reason':'broker_free_margin_with_pending_reserve','requiredMarginUSD':margin,'reservedPendingMarginUSD':reserved,'freeMarginUSD':a.margin_free}
 if nowms()-(q.time_msc-offset)>5000:return {'symbol':name,'reason':'quote_expired_during_calculation'}
 row={'symbol':name,'arm':'MOMENTUM_M1_ALIGNED_RR2','ordinal':st['hundred']['attempts']+1,'partition':'prospective_forward','holdSeconds':None,'targetR':2,'version':cfg['version']}
 request={'symbol':name,'type':side+'_limit' if limit else side,'volume':volume,'sl':sl,'tp':tp}
 expiry=nowms()+cfg.get('pending_validity_seconds',45)*1000
 # Transport field uses a whole-second broker wall-clock ISO value; native verification converts it back with the measured offset.
 if limit:request.update({'price':entry,'expiration_type':'specified','expiration_time':datetime.fromtimestamp((expiry+offset)/1000,timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),'filling_type':'return'})
 if cfg.get('entry_order_policy')=='LIMIT_WITH_MANAGED_EXPIRY':request.pop('expiration_time',None);request['expiration_type']='gtc'
 return {'status':'analysis_ready','row':row,'request':request,'entry':entry,'pendingExpiryUTC':iso(expiry) if limit else None,'initialRiskUSD':risk,'nativeSLProfitUSD':loss,'nativeTPProfitUSD':reward,'nativePlannedRR':reward/risk,'marginUSD':margin,'quoteAgeSeconds':(nowms()-(q.time_msc-offset))/1000,'quoteUTC':iso(q.time_msc-offset),'account':a._asdict(),'positions':[p._asdict() for p in positions],'orders':[o._asdict() for o in orders],'symbol':s._asdict(),'tick':q._asdict(),'closedBars':bars,'nativeTicks':pts,'fiveSecondReturn':delta,'ATR14':atr,'spreadPrice':spread,'costReserveScenarioUSD':reserve,'scenarioIsActualFee':False,'signalWindowEndUTC':iso(last['t']),'observedUTC':iso(nowms()),'version':cfg['version'],'referenceMethod':'last quote available as of exact five-second window start'}
try:
 a,ps,os,st=gate()
 if nowms()>=stamp(protocol['deadlineUTC']):print(json.dumps({'status':'deadline'}));sys.exit(0)
 mode=sys.argv[1]
 if mode=='plan':
  catalog=read(protocol['catalogPath'])['symbols'];groups={}
  for x in catalog:
   if x['name'] not in cfg['symbols']:continue
   if x['trade_mode'] not in (1,2,4) or any(not x['order_mode']&bit for bit in (1,16,32)):continue
   groups.setdefault(str(x['trade_calc_mode']),[]).append(x)
  for xs in groups.values():xs.sort(key=lambda x:(not x['visible'],x['name']))
  names=[];i=0
  while True:
   fresh=[xs[i]['name'] for xs in groups.values() if i<len(xs)]
   if not fresh:break
   names.extend(fresh);i+=1
  names=cfg['symbols'];cursor=st.get('universe_cursor',0);batch=[names[(cursor+i)%len(names)] for i in range(len(names))]
  data={'recordedUTC':iso(nowms()),'version':cfg['version'],'catalogCount':len(cfg['symbols']),'brokerCatalogCount':len(catalog),'entryEligibleCatalogCount':len(names),'cursor':cursor,'nextCursor':cursor+1,'symbols':batch,'symbolsToAdd':[n for n in batch if not mt5.symbol_info(n).visible]}
  p=save('rr2_rotation_plan',data);print(json.dumps(data|{'path':p}),flush=True)
 elif mode in ('prepare','scan'):
  plan=read(sys.argv[2]);now=nowms()
  if plan['version']!=cfg['version'] or now-stamp(plan['recordedUTC'])>300000:raise RuntimeError('plan_stale')
  error=news_gate(now)
  if error:print(json.dumps({'status':'skip','reason':error}));sys.exit(0)
  observations=[];ready=None
  for name in plan['symbols']:
   x=candidate(name)
   if x.get('status')=='analysis_ready':
    observations.append({'symbol':name,'reason':'analysis_ready','nativePlannedRR':x['nativePlannedRR']})
    if ready is None:ready=x
   else:observations.append(x)
  audit=save('rr2_screen',{'recordedUTC':iso(nowms()),'version':cfg['version'],'planPath':sys.argv[2],'observations':observations,'ordersSentByPython':0})
  current=read(W/'Trading_Manager_State.json')
  if current['version']!=cfg['version'] or current.get('pending_intent'):raise RuntimeError('state_changed')
  current['universe_cursor']=plan['nextCursor'];current['last_screen_path']=audit
  for x in observations:
   row=current.setdefault('rr2_coverage',{}).setdefault(x['symbol'],{'checks':0})
   row.update({'checks':row['checks']+1,'lastReason':x['reason'],'lastUTC':iso(nowms())})
  write(W/'Trading_Manager_State.json',current,False)
  if mode=='scan':
   compact=None if ready is None else {k:ready[k] for k in ('request','entry','initialRiskUSD','nativePlannedRR','marginUSD','quoteUTC','signalWindowEndUTC')}
   print(json.dumps({'status':'analysis_ready' if ready else 'skip','reason':'read_only_no_intent_no_orders','screenPath':audit,'screened':observations,'candidate':compact}),flush=True);sys.exit(0)
  if ready is None:print(json.dumps({'status':'skip','reason':'no_qualified_candidate','screenPath':audit,'screened':observations}),flush=True);sys.exit(0)
  # Full fresh recomputation for selected contract immediately before intent; earlier screening is not a quote.
  ready=None;latest=[]
  for name in [x['symbol'] for x in observations if x['reason']=='analysis_ready']:
   x=candidate(name)
   if x.get('status')=='analysis_ready':ready=x;break
   latest.append(x)
  if ready is None:print(json.dumps({'status':'skip','reason':'selected_candidates_no_longer_valid','latest':latest,'screenPath':audit}));sys.exit(0)
  error=news_gate(nowms())
  if error:print(json.dumps({'status':'skip','reason':error}));sys.exit(0)
  a,ps,os,current=gate();attempt=current['hundred']['attempts']+1
  uid='AR2_'+str(ready['row']['ordinal']).zfill(3)+'_'+str(attempt).zfill(3)+'_'+str(nowms())[-7:]
  paths={k:str(J/(uid+'_'+k+'.json')) for k in ('preflight','protocol','intent')};ready['request']['comment']=uid
  ready['screenPath']=audit
  owned={'id':uid,'version':cfg['version'],'symbol':ready['request']['symbol'],'comment':uid,'registeredUTC':iso(nowms()),'experimentKind':'ACTUAL_DEMO_SEVEN_SYMBOLS_RR2','countsAsMicroMAPStrategyTrade':False,'closeRequestAtSeconds':None,'holdingTargetSeconds':None,'row':ready['row'],'direction':ready['request']['type'],'exitPolicy':'BROKER_SL_TP_ONLY','pendingExpiryUTC':ready.get('pendingExpiryUTC')}
  intent={'dedupKey':uid,'recordedUTC':iso(nowms()),'status':'INTENT','request':ready['request'],'ordinal':ready['row']['ordinal'],'row':ready['row'],'preflightPath':paths['preflight'],'protocolPath':paths['protocol'],'intentPath':paths['intent'],'expiresUTC':iso(nowms()+5000)}
  write(J/'execution.lock',{'dedupKey':uid,'intentPath':paths['intent']})
  write(paths['preflight'],ready);write(paths['protocol'],owned);write(paths['intent'],intent)
  current['pending_intent']=intent;current['intents'].append(intent);current['hundred']['attempts']=attempt;current['stage']='INTENT';write(W/'Trading_Manager_State.json',current,False)
  out={k:ready[k] for k in ['request','entry','initialRiskUSD','nativeSLProfitUSD','nativeTPProfitUSD','nativePlannedRR','marginUSD','quoteUTC','observedUTC']}
  out.update({'status':'ready','intent':intent,'contractSize':ready['symbol']['trade_contract_size'],'brokerPoint':ready['symbol']['point'],'equityUSD':a.equity,'screenPath':audit})
  print(json.dumps(out),flush=True)
 else:raise RuntimeError('unknown_mode')
finally:mt5.shutdown()
