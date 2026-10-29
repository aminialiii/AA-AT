"""Read-only all-symbol MicroMAP interpretation. No orders, selection, settings or account switching."""
import sys,json,math,bisect,hashlib,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');J=W/'trading-journal'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def save(kind,obj):
 p=J/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False)
 return str(p)
cfg=read(W/'Trading_Manager_Config.json');model=read(cfg['model_path']);offset=cfg['broker_UTC_offset_minutes']
if cfg['risk_policy']['type']!='user_waiver_demo_only' or cfg['universe_policy']['scope']!='all_broker_symbols':raise RuntimeError('unsupported_policy')
def base():
 current=read(W/'Trading_Manager_Config.json');state=read(W/'Trading_Manager_State.json')
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected or not a.trade_allowed:raise RuntimeError('matching_writable_demo_required')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 blocked=None
 if current['version']!=cfg['version'] or not current['enabled'] or state['run_status']!='ACTIVE':blocked='STOPPED'
 elif now>=stamp(cfg['session_end_utc']):blocked='SESSION_ENDED'
 elif state.get('owned_positions') or state.get('pending_intent') or state.get('unknown_execution_outcome'):blocked='MANAGEMENT_REQUIRED'
 return a,t,state,positions,orders,now,blocked
def currencies(s):
 metals={'XAU','XAG','XPT','XPD'};aliases={'CNH':'CNY','RMB':'CNY','RUR':'RUB'}
 codes={aliases.get(x,x) for x in [s.currency_base,s.currency_profit,s.currency_margin] if len(x)==3 and x not in metals}
 regional=cfg['universe_policy'].get('regional_news_currencies',{}).get(s.name,[])
 return sorted(codes|set(regional))
def classify(s):
 path=s.path.lower()
 if '\\etf\\' in path:return 'ETF'
 if '\\etn\\' in path:return 'ETN'
 if s.trade_calc_mode==mt5.SYMBOL_CALC_MODE_EXCH_STOCKS:return 'exchange_equity_or_fund'
 if 'crypto' in path:return 'broker_crypto_contract'
 if s.currency_base in {'XAU','XAG','XPT','XPD'}:return 'metal_contract'
 if s.trade_calc_mode==mt5.SYMBOL_CALC_MODE_FOREX:return 'forex'
 return 'broker_CFD_or_other'
def contract_reasons(s):
 reasons=[]
 if s.trade_mode not in [mt5.SYMBOL_TRADE_MODE_FULL,mt5.SYMBOL_TRADE_MODE_LONGONLY]:reasons.append('broker_does_not_allow_new_buy')
 if not s.visible:reasons.append('symbol_not_in_market_watch')
 if not s.order_mode&1 or not s.order_mode&16 or not s.order_mode&32:reasons.append('broker_market_SL_TP_not_supported')
 if not all(math.isfinite(x) and x>0 for x in [s.point,s.trade_tick_size,s.trade_contract_size,s.volume_min,s.volume_step,s.volume_max]):reasons.append('contract_specification_unknown')
 return reasons
def news_gate(s,now,trigger):
 try:news=read(W/'.skill-tools/universe-news-cache.json')
 except Exception:return 'calendar_unknown'
 if not news['calendar'].get('ok') or news['calendar'].get('truncated') or now-stamp(news['collectedUTC'])>5*60000:return 'calendar_unknown_or_stale'
 if not stamp(news['coverageFromUTC'])<=now<stamp(news['coverageToUTC']):return 'calendar_coverage_unknown'
 relevant=currencies(s)
 if not relevant:return 'relevant_currency_unknown'
 events={}
 for c in relevant:
  meta=news['byCurrency'].get(c)
  if not meta or not meta.get('ok') or now-stamp(meta['metadataUTC'])>15*60000:return 'calendar_metadata_unknown_'+c
  events.update({str(e['id']):(c,e) for e in meta['events']})
 for v in news['calendar']['values']:
  found=events.get(str(v['event_id']))
  if found is None:continue
  c,e=found
  if e['importance']!='High importance':continue
  if v.get('time_unknown') or not v.get('time'):return 'relevant_news_time_unknown_'+c
  event=stamp(v['time']+'Z')-offset*60000
  if min(now,trigger)<=event+cfg['news_block_minutes_after']*60000 and max(now+cfg['max_holding_seconds']*1000,trigger)>=event-cfg['news_block_minutes_before']*60000:return 'high_impact_news_'+c
 return None
def plan():
 a,t,state,positions,orders,now,blocked=base()
 all=mt5.symbols_get()
 if all is None:raise RuntimeError('broker_catalog_unknown')
 # Authorization includes every broker symbol; operational rotation is not an allowlist.
 cursor=int(state.get('universe_cursor',0))%len(all);quota=cfg['universe_policy']['rotation_batch_size']
 hidden=[];inspected=0
 for name in cfg['universe_policy'].get('initial_priority',[]) if not state.get('universe_initialized') else []:
  s=next((x for x in all if x.name==name),None)
  if s and not s.visible and s.trade_mode in [mt5.SYMBOL_TRADE_MODE_FULL,mt5.SYMBOL_TRADE_MODE_LONGONLY] and name not in hidden:hidden.append(name)
 while inspected<len(all) and len(hidden)<quota:
  s=all[(cursor+inspected)%len(all)];inspected+=1
  if not s.visible and s.name not in hidden and s.trade_mode in [mt5.SYMBOL_TRADE_MODE_FULL,mt5.SYMBOL_TRADE_MODE_LONGONLY]:hidden.append(s.name)
 next_cursor=(cursor+inspected)%len(all)
 names=[s.name for s in all if s.visible]+hidden
 chosen=[s for s in all if s.name in names]
 data={'observedUTC':iso(now),'version':cfg['version'],'status':blocked or 'universe_ready','brokerSymbolCount':len(all),'authorizationScope':'all_broker_symbols','visibleSymbols':[s.name for s in all if s.visible],'symbolsToAdd':hidden,'nextCursor':next_cursor,'relevantCurrencies':sorted(set(c for s in chosen for c in currencies(s))),'symbols':[{'name':s.name,'path':s.path,'description':s.description,'assetClass':classify(s),'currencies':currencies(s),'contract':s._asdict()} for s in chosen]}
 path=save('universe_plan',data)
 return {k:data[k] for k in ['observedUTC','status','brokerSymbolCount','authorizationScope','visibleSymbols','symbolsToAdd','nextCursor','relevantCurrencies']}|{'path':path}
def scan(bars,tick_size,digits):
 setups=[];sp=model['spike'];mc=model['microchannel'];period=sp['ATRPeriod']
 buffer=model['entry']['bufferTicks']*tick_size;stopbuffer=model['SL']['bufferTicks']*tick_size
 for i in range(period+6,len(bars)-3):
  if any(bars[k]['t']-bars[k-1]['t']!=60000 for k in range(i-period-1,i+2)):continue
  atr=sum(max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-period,i))/period
  spike=bars[i:i+sp['bars']]
  if atr<=0 or any(x['close']<=x['open'] or x['high']==x['low'] or (x['close']-x['open'])/(x['high']-x['low'])<sp['bodyFractionMin'] or (x['close']-x['low'])/(x['high']-x['low'])<sp['closeLocationMin'] for x in spike):continue
  net=spike[-1]['close']-spike[0]['open']
  if net<sp['totalNetMoveATRMin']*atr:continue
  avg_range=sum(x['high']-x['low'] for x in spike)/sp['bars'];prev=spike[-1];arms=[]
  for j in range(1,mc['maxBars']+1):
   if i+sp['bars']-1+j>=len(bars):break
   b=bars[i+sp['bars']-1+j]
   if b['t']-prev['t']!=60000 or b['high']>=prev['high'] or b['high']-b['low']>mc['maxRangeVsMeanSpikeRange']*avg_range or b['low']<spike[-1]['close']-mc['maxRetracementOfSpikeNet']*net:break
   if j>=mc['minBars']:
    arms.append({'armed':b['t']+60000,'expires':b['t']+60000+model['entry']['expirySeconds']*1000,'trigger':round(math.ceil((b['high']+buffer-tick_size*1e-7)/tick_size)*tick_size,digits),'sl':round(math.floor((b['low']-stopbuffer+tick_size*1e-7)/tick_size)*tick_size,digits),'microBars':j})
   prev=b
  if arms:setups.append({'origin':spike[0]['t'],'arms':arms,'atr':atr})
 return setups
def observe_symbol(s,state,now):
 reasons=contract_reasons(s);q=mt5.symbol_info_tick(s.name)
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 quote_age=None
 if q is None:reasons.append('quote_unknown')
 else:
  quote_age=(now-(q.time_msc-offset*60000))/1000
  if quote_age<0 or quote_age>cfg['max_quote_age_seconds'] or q.ask<q.bid or q.bid<=0:reasons.append('quote_stale_or_invalid')
 baseinfo={'symbol':s.name,'assetClass':classify(s),'path':s.path,'quoteAgeSeconds':quote_age,'volumeMinimum':s.volume_min,'status':'skip'}
 if reasons:return baseinfo|{'reasons':reasons,'candidate':None,'consumedSignals':[]}
 rates=mt5.copy_rates_from_pos(s.name,mt5.TIMEFRAME_M1,0,200)
 if rates is None:return baseinfo|{'reasons':['M1_history_unknown'],'candidate':None,'consumedSignals':[]}
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 bars=[dict(t=int(x['time'])*1000-offset*60000,open=float(x['open']),high=float(x['high']),low=float(x['low']),close=float(x['close'])) for x in rates if int(x['time'])*1000-offset*60000+60000<=now]
 bars.sort(key=lambda b:b['t'])
 if len(bars)<25 or bars[-1]['t']!=now//60000*60000-60000 or any(not all(math.isfinite(b[k]) and b[k]>0 for k in ['open','high','low','close']) or b['low']>min(b['open'],b['close']) or b['high']<max(b['open'],b['close']) or i and b['t']<=bars[i-1]['t'] for i,b in enumerate(bars)):
  return baseinfo|{'reasons':['latest_closed_M1_missing_or_invalid'],'candidate':None,'consumedSignals':[]}
 fresh=[x for x in scan(bars,s.trade_tick_size,s.digits) if x['origin']>=stamp(cfg['model_activation_utc'])]
 relevant=[x for x in fresh if x['arms'][-1]['expires']>now-cfg['max_trigger_age_seconds']*1000]
 candidate=None;consume=[];pts=[]
 if relevant:
  tick_start=min(x['arms'][0]['armed'] for x in relevant)
  ticks=mt5.copy_ticks_range(s.name,datetime.fromtimestamp(tick_start/1000,timezone.utc)+timedelta(minutes=offset),datetime.fromtimestamp(now/1000,timezone.utc)+timedelta(minutes=offset),mt5.COPY_TICKS_ALL)
  if ticks is not None:pts=[{'t':int(x['time_msc'])-offset*60000,'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks]
  times=[x['t'] for x in pts]
  valid=bool(pts) and times[0]<=tick_start+5000 and 0<=now-times[-1]<=5000 and all(p['bid']>0 and p['ask']>=p['bid'] and (i==0 or 0<=p['t']-pts[i-1]['t']<=cfg['maximum_observed_tick_gap_seconds']*1000) for i,p in enumerate(pts))
  if not valid:reasons.append('native_tick_coverage_unknown')
  else:
   for setup in relevant:
    dedup=cfg['version']+'|'+s.name+'|buy|'+str(setup['origin'])
    if dedup in local_consumed or dedup in state.get('consumed_signals',[]) or any(x.get('dedupKey')==dedup for x in state.get('intents',[])):continue
    hit=arm=None
    for ar in setup['arms']:
     for p in pts[bisect.bisect_left(times,ar['armed']):bisect.bisect_left(times,min(ar['expires'],now+1))]:
      if p['bid']>=ar['trigger']:hit=p;arm=ar;break
     if hit:break
    if not hit:continue
    expires=min(hit['t']+cfg['max_trigger_age_seconds']*1000,arm['expires'],stamp(cfg['session_end_utc']))
    q=mt5.symbol_info_tick(s.name)
    ng=news_gate(s,now,hit['t'])
    if q is None or now>=expires or q.bid<arm['trigger'] or ng or q.ask-q.bid>model['executionFilters']['maxSpreadATR']*setup['atr']:
     consume.append(dedup);local_consumed.add(dedup);reasons.append(ng or 'first_trigger_expired_lost_or_spread');continue
    candidate={'status':'analysis_ready','version':cfg['version'],'modelVersion':model['version'],'modelLabel':'AGENT_INTERPRETATION','symbol':s.name,'side':'buy','assetClass':classify(s),'setupOriginUTC':iso(setup['origin']),'armedUTC':iso(arm['armed']),'triggerUTC':iso(hit['t']),'expiresUTC':iso(expires),'triggerLevel':arm['trigger'],'structuralSL':arm['sl'],'dedupKey':dedup,'microBars':arm['microBars'],'ATR':setup['atr'],'tickSize':s.trade_tick_size,'selectedVolume':s.volume_min,'relevantCurrencies':currencies(s),'researchGatePassed':False}
    break
 snap={'observedUTC':iso(now),'version':cfg['version'],'modelPath':cfg['model_path'],'modelSHA256':hashlib.sha256(Path(cfg['model_path']).read_bytes()).hexdigest(),'symbol':s._asdict(),'tick':q._asdict() if q else None,'closedBars':bars,'nativeTicks':pts,'freshSetups':fresh,'candidate':candidate,'consumedSignals':consume,'reasons':reasons or ([] if candidate else ['no_fresh_signal'])}
 path=save('universe_symbol_screen',snap)
 if candidate:candidate_path=save('universe_candidate',candidate)
 return baseinfo|{'status':'analysis_ready' if candidate else 'skip','reasons':snap['reasons'],'snapshotPath':path,'observedUTC':iso(now),'candidate':candidate,'candidatePath':candidate_path if candidate else None,'consumedSignals':consume,'freshSetups':len(fresh)}
def observe():
 a,t,state,positions,orders,now,blocked=base()
 if blocked:return {'status':blocked,'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders]},True
 all=mt5.symbols_get()
 if all is None:raise RuntimeError('catalog_unknown')
 rows=[];consume=[];candidate=None;candidate_path=None
 for s in all:
  if not s.visible:continue
  try:r=observe_symbol(s,state,int(datetime.now(timezone.utc).timestamp()*1000))
  except Exception as e:r={'symbol':s.name,'status':'skip','reasons':['symbol_observation_error:'+str(e)],'candidate':None,'consumedSignals':[]}
  rows.append(r);consume+=r['consumedSignals']
  if r.get('candidate'):candidate=r['candidate'];candidate_path=r['candidatePath'];break
 snap={'observedUTC':iso(now),'completedUTC':datetime.now(timezone.utc).isoformat(),'version':cfg['version'],'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'externalExposureBlocksByCount':False,'brokerCatalogCount':len(all),'rows':rows,'candidate':candidate,'consumedSignals':consume}
 path=save('universe_native_screen',snap)
 return {'status':'analysis_ready' if candidate else 'skip','snapshotPath':path,'observedUTC':snap['completedUTC'],'candidate':candidate,'candidatePath':candidate_path,'consumedSignals':consume,'screenedSymbols':len(rows),'rows':[{k:r.get(k) for k in ['symbol','assetClass','quoteAgeSeconds','status','reasons','freshSetups']} for r in rows]},bool(candidate)
def probe(candidate):
 a,t,state,positions,orders,now,blocked=base();reasons=[blocked] if blocked else []
 name=candidate['symbol'];s,q=mt5.symbol_info(name),mt5.symbol_info_tick(name)
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 if s is None or q is None:raise RuntimeError('market_unknown')
 reasons+=contract_reasons(s);age=(now-(q.time_msc-offset*60000))/1000
 if candidate['version']!=cfg['version'] or candidate['side']!='buy' or candidate['status']!='analysis_ready':reasons.append('candidate_identity')
 if candidate.get('modelVersion')!=model['version'] or stamp(candidate['setupOriginUTC'])<stamp(cfg['model_activation_utc']):reasons.append('candidate_model_or_activation')
 if age<0 or age>cfg['max_quote_age_seconds'] or q.ask<q.bid or q.bid<=0:reasons.append('quote_stale_or_invalid')
 trigger=stamp(candidate['triggerUTC'])
 if now-trigger>cfg['max_trigger_age_seconds']*1000 or now>=stamp(candidate['expiresUTC']):reasons.append('trigger_expired')
 if q.bid<candidate['triggerLevel']:reasons.append('trigger_lost')
 if candidate['ATR']<=0 or q.ask-q.bid>model['executionFilters']['maxSpreadATR']*candidate['ATR']:reasons.append('spread_vs_ATR')
 if candidate['dedupKey'] in state.get('consumed_signals',[]) or any(x.get('dedupKey')==candidate['dedupKey'] for x in state.get('intents',[])):reasons.append('duplicate')
 ng=news_gate(s,now,trigger)
 if ng:reasons.append(ng)
 if reasons:
  path=save('universe_native_probe',{'observedUTC':iso(now),'status':'skip','reasons':reasons,'candidate':candidate})
  return {'status':'skip','reasons':reasons,'path':path,'observedUTC':iso(now)}
 volume=round(math.ceil((s.volume_min-s.volume_step*1e-7)/s.volume_step)*s.volume_step,8)
 if volume<s.volume_min or volume>s.volume_max:reasons.append('broker_minimum_volume_invalid')
 sl=round(math.floor((candidate['structuralSL']+s.trade_tick_size*1e-7)/s.trade_tick_size)*s.trade_tick_size,s.digits)
 distance=q.ask-sl;tp=round(math.ceil((q.ask+cfg['target_R']*distance-s.trade_tick_size*1e-7)/s.trade_tick_size)*s.trade_tick_size,s.digits)
 if distance<=0 or q.bid-sl<=s.trade_stops_level*s.point or tp-q.bid<s.trade_stops_level*s.point:reasons.append('structural_stop_or_target_invalid')
 profit=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,name,volume,q.ask,sl)
 reserve_move=model['costScenario']['slippageTicks']*s.trade_tick_size+model['costScenario']['spreadWideningMultiples']*(q.ask-q.bid)
 reserve_profit=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,name,volume,q.ask,q.ask-reserve_move)
 margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,name,volume,q.ask)
 reserve=abs(reserve_profit)+model['costScenario']['roundTripFeeUSDPerMinimumVolume'] if reserve_profit is not None else None
 if profit is None or profit>=0 or reserve_profit is None or margin is None or margin<=0:reasons.append('native_risk_or_margin_unknown')
 else:
  if margin>a.margin_free:reasons.append('broker_free_margin')
  if reserve/(-profit)>model['executionFilters']['maxEstimatedReserveVsPriceRisk']:reasons.append('estimated_cost_vs_structure')
 # Re-read executable quote and exposure after broker calculations.
 a2=mt5.account_info();p2,o2=mt5.positions_get(),mt5.orders_get();q2=mt5.symbol_info_tick(name)
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 if a2 is None or p2 is None or o2 is None or q2 is None:reasons.append('final_native_preflight_unknown')
 elif str(a2.login)!=cfg['account_login'] or a2.server!=cfg['account_server'] or a2.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not a2.trade_allowed:reasons.append('final_account_identity')
 elif abs(q2.ask-q.ask)>s.trade_tick_size*1e-7 or abs(q2.bid-q.bid)>s.trade_tick_size*1e-7:reasons.append('quote_changed_recalculate_next_fresh_cycle')
 elif margin is not None and margin>a2.margin_free:reasons.append('broker_margin_changed')
 age=(now-(q.time_msc-offset*60000))/1000
 if age<0 or age>cfg['max_quote_age_seconds'] or now>=stamp(candidate['expiresUTC']):reasons.append('final_freshness')
 out={'observedUTC':iso(now),'version':cfg['version'],'status':'skip' if reasons else 'ready','reasons':reasons,'riskPolicy':cfg['risk_policy_revision'],'percentageRiskGateApplied':False,'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'symbol':s._asdict(),'tick':q._asdict(),'quoteAgeSeconds':age,'request':{'symbol':name,'type':'buy','volume':volume,'sl':sl,'tp':tp,'comment':cfg['entry_comment']},'entry':q.ask,'initialRiskUSD':-profit if profit is not None else None,'reserveUSD':reserve,'costScenarioNotObservedFees':True,'marginUSD':margin,'candidate':candidate}
 path=save('universe_native_probe',out)
 return {k:out[k] for k in ['status','reasons','request','initialRiskUSD','quoteAgeSeconds','observedUTC']}|{'path':path,'dedupKey':candidate['dedupKey']}
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
local_consumed=set()
try:
 mode=sys.argv[1] if len(sys.argv)>1 else 'watch'
 if mode=='plan':print(json.dumps(plan()),flush=True)
 elif mode=='probe':print(json.dumps(probe(read(sys.argv[2]))),flush=True)
 else:
  n=int(sys.argv[2]) if len(sys.argv)>2 else 1
  for i in range(n):
   out,done=observe();print(json.dumps(out),flush=True)
   if done:break
   if i+1<n:time.sleep(15)
finally:mt5.shutdown()
