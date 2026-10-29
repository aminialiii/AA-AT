"""Demo-only native reads, numerical screening and exact margin/profit. NO orders/settings/account switching."""
import sys,json,math,bisect,hashlib,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');J=W/'trading-journal';R=W/'research/poursamadi-backtest'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def save(kind,obj):
 p=J/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,ensure_ascii=False)
 return str(p)
cfg=read(W/'Trading_Manager_Config.json');model=read(cfg['model_path']);offset=cfg['broker_UTC_offset_minutes']
source=(R/'backtest.py').read_text(encoding='utf-8')
scanner=source[source.index('setups=[];bar_gaps=[]'):source.index("plan={'registeredUTC'")]
if cfg['risk_policy']['type']!='user_waiver_demo_only':raise RuntimeError('unsupported_risk_policy')
def gate():
 current=read(W/'Trading_Manager_Config.json');state=read(W/'Trading_Manager_State.json')
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected or not a.trade_allowed:raise RuntimeError('account_or_connection_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 now=int(datetime.now(timezone.utc).timestamp()*1000)
 if current['version']!=cfg['version'] or not current['enabled'] or state['run_status']!='ACTIVE':return a,t,state,positions,orders,now,'STOPPED'
 if now>=stamp(cfg['session_end_utc']):return a,t,state,positions,orders,now,'SESSION_ENDED'
 if state.get('owned_positions') or state.get('pending_intent') or state.get('unknown_execution_outcome'):return a,t,state,positions,orders,now,'MANAGEMENT_REQUIRED'
 return a,t,state,positions,orders,now,None
def news_gate(now,trigger):
 news=read(W/'.skill-tools/micromap-news-cache.json')
 if now-stamp(news['metadataUTC'])>15*60000 or now-stamp(news['collectedUTC'])>5*60000:return 'news_unknown_or_stale'
 if not news['calendar']['ok'] or news['calendar']['truncated'] or not news['events']['ok']:return 'news_unknown'
 if not stamp(news['coverageFromUTC'])<=now<stamp(news['coverageToUTC']):return 'news_coverage_unknown'
 catalog={str(x['id']):x for x in news['events']['events']}
 for v in news['calendar']['values']:
  e=catalog.get(str(v['event_id']))
  if e is None or e['importance']!='High importance':continue
  if v.get('time_unknown') or not v.get('time'):return 'news_time_unknown'
  event=stamp(v['time']+'Z')-offset*60000
  if min(now,trigger)<=event+cfg['news_block_minutes_after']*60000 and max(now+cfg['max_holding_seconds']*1000,trigger)>=event-cfg['news_block_minutes_before']*60000:return 'USD_news'
 return None
def probe(candidate):
 a,t,state,positions,orders,now,blocked=gate()
 reasons=[blocked] if blocked else []
 s,q=mt5.symbol_info('XAUUSD'),mt5.symbol_info_tick('XAUUSD')
 if s is None or q is None:raise RuntimeError('market_unknown')
 quote_ms=q.time_msc-offset*60000;age=(now-quote_ms)/1000
 if s.trade_mode!=mt5.SYMBOL_TRADE_MODE_FULL or not s.visible:reasons.append('symbol_not_tradable')
 if candidate['version']!=cfg['version'] or candidate['symbol']!='XAUUSD' or candidate['side']!='buy' or candidate['status']!='analysis_ready':reasons.append('candidate_identity')
 if age<0 or age>cfg['max_quote_age_seconds']:reasons.append('quote_stale_or_clock_unknown')
 trigger=stamp(candidate['triggerUTC'])
 if now-trigger>cfg['max_trigger_age_seconds']*1000 or now>=stamp(candidate['expiresUTC']):reasons.append('trigger_expired')
 if q.bid<candidate['triggerLevel']:reasons.append('trigger_lost')
 if q.ask-q.bid>cfg['spread_max_price']+1e-8:reasons.append('spread')
 if candidate['dedupKey'] in state.get('consumed_signals',[]) or any(x.get('dedupKey')==candidate['dedupKey'] for x in state.get('intents',[])):reasons.append('duplicate')
 ng=news_gate(now,trigger)
 if ng:reasons.append(ng)
 volume=math.floor((min(cfg['selected_trial_volume'],s.volume_max)+1e-10)/s.volume_step)*s.volume_step
 sl=round(math.floor((candidate['structuralSL']+1e-8)/s.trade_tick_size)*s.trade_tick_size,s.digits)
 distance=q.ask-sl
 tp=round(math.ceil((q.ask+cfg['target_R']*distance-1e-8)/s.trade_tick_size)*s.trade_tick_size,s.digits)
 if volume<s.volume_min:reasons.append('broker_volume')
 if distance<=0 or q.bid-sl<=s.trade_stops_level*s.point or tp-q.bid<s.trade_stops_level*s.point:reasons.append('structural_stop_or_target_invalid')
 profit=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',volume,q.ask,sl)
 reserve_profit=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',volume,q.ask,q.ask-cfg['slippage_reserve_price']-cfg['spread_widening_reserve_price'])
 margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,'XAUUSD',volume,q.ask)
 if profit is None or profit>=0 or reserve_profit is None or margin is None or margin<=0:reasons.append('native_risk_or_margin_unknown')
 elif margin>a.margin_free:reasons.append('broker_margin')
 out={'observedUTC':iso(now),'version':cfg['version'],'status':'skip' if reasons else 'ready','reasons':reasons,'riskPolicy':cfg['risk_policy_revision'],'percentageRiskGateApplied':False,'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'symbol':s._asdict(),'tick':q._asdict(),'quoteAgeSeconds':age,'request':{'symbol':'XAUUSD','type':'buy','volume':round(volume,8),'sl':sl,'tp':tp,'comment':cfg['entry_comment']},'entry':q.ask,'initialRiskUSD':-profit if profit is not None else None,'reserveUSD':abs(reserve_profit)+cfg['round_trip_commission_per_lot']*volume if reserve_profit is not None else None,'marginUSD':margin,'candidate':candidate}
 path=save('micromap_native_probe',out)
 return {'status':out['status'],'reasons':reasons,'path':path,'request':out['request'],'initialRiskUSD':out['initialRiskUSD'],'quoteAgeSeconds':age,'observedUTC':out['observedUTC'],'dedupKey':candidate['dedupKey']}
def observe():
 a,t,state,positions,orders,now,blocked=gate()
 if blocked:return {'status':blocked,'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders]},True
 rates=mt5.copy_rates_from_pos('XAUUSD',mt5.TIMEFRAME_M1,0,200)
 q,s=mt5.symbol_info_tick('XAUUSD'),mt5.symbol_info('XAUUSD')
 if rates is None or q is None or s is None:raise RuntimeError('market_data_unknown')
 bars=[dict(t=int(x['time'])*1000-offset*60000,open=float(x['open']),high=float(x['high']),low=float(x['low']),close=float(x['close'])) for x in rates if int(x['time'])*1000-offset*60000+60000<=now]
 bars.sort(key=lambda x:x['t'])
 if not bars or bars[-1]['t']!=now//60000*60000-60000:raise RuntimeError('latest_closed_M1_missing')
 if any(x['low']>min(x['open'],x['close']) or x['high']<max(x['open'],x['close']) or i and x['t']<=bars[i-1]['t'] for i,x in enumerate(bars)):raise RuntimeError('invalid_bars')
 scope={'bars':bars,'model':model,'iso':iso,'math':math}
 exec(scanner,scope)
 fresh=[x for x in scope['setups'] if x['origin']>=stamp(cfg['session_start_utc'])]
 relevant=[x for x in fresh if x['arms'][-1]['expires']>now-cfg['max_trigger_age_seconds']*1000]
 tick_start=min([now-60000]+[x['arms'][0]['armed'] for x in relevant]);ticks=mt5.copy_ticks_range('XAUUSD',datetime.fromtimestamp(tick_start/1000,timezone.utc)+timedelta(minutes=offset),datetime.fromtimestamp(now/1000,timezone.utc)+timedelta(minutes=offset),mt5.COPY_TICKS_ALL)
 if ticks is None:raise RuntimeError('ticks_unknown')
 pts=[{'t':int(x['time_msc'])-offset*60000,'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks];times=[x['t'] for x in pts]
 valid=bool(pts) and times[0]<=tick_start+5000 and now-times[-1]<=5000 and all(p['bid']>0 and p['ask']>=p['bid'] and (i==0 or 0<=p['t']-pts[i-1]['t']<=cfg['maximum_observed_tick_gap_seconds']*1000) for i,p in enumerate(pts))
 candidate=None;consume=[];reasons=[]
 if not valid:reasons.append('native_tick_coverage_unknown')
 if valid:
  for setup in relevant:
   dedup=cfg['version']+'|XAUUSD|buy|'+str(setup['origin'])
   if dedup in local_consumed or dedup in state.get('consumed_signals',[]) or any(x.get('dedupKey')==dedup for x in state.get('intents',[])):continue
   hit=arm=None
   for ar in setup['arms']:
    for p in pts[bisect.bisect_left(times,ar['armed']):bisect.bisect_left(times,min(ar['expires'],now+1))]:
     if p['bid']>=ar['trigger']:hit=p;arm=ar;break
    if hit:break
   if not hit:continue
   expires=min(hit['t']+cfg['max_trigger_age_seconds']*1000,arm['expires'],stamp(cfg['session_end_utc']))
   if now>=expires or q.bid<arm['trigger']:
    consume.append(dedup);local_consumed.add(dedup);reasons.append('first_trigger_expired_or_lost');continue
   ng=news_gate(now,hit['t'])
   if ng or q.ask-q.bid>cfg['spread_max_price']+1e-8:
    consume.append(dedup);local_consumed.add(dedup);reasons.append(ng or 'spread');continue
   candidate={'status':'analysis_ready','version':cfg['version'],'modelLabel':'AGENT_INTERPRETATION','symbol':'XAUUSD','side':'buy','setupOriginUTC':iso(setup['origin']),'armedUTC':iso(arm['armed']),'triggerUTC':iso(hit['t']),'expiresUTC':iso(expires),'triggerLevel':arm['trigger'],'structuralSL':arm['sl'],'dedupKey':dedup,'microBars':arm['microBars'],'ATR':setup['atr'],'selectedVolume':cfg['selected_trial_volume'],'researchGatePassed':False}
   break
 snapshot={'observedUTC':iso(now),'version':cfg['version'],'riskPolicy':cfg['risk_policy_revision'],'account':a._asdict(),'positions':[x._asdict() for x in positions],'orders':[x._asdict() for x in orders],'externalExposureBlocksByCount':False,'symbol':s._asdict(),'tick':q._asdict(),'closedBars':bars,'nativeTicks':pts,'scannerSourceSHA256':hashlib.sha256(source.encode()).hexdigest(),'freshSetups':fresh,'candidate':candidate,'consumedSignals':consume,'reasons':reasons or ([] if candidate else ['no_fresh_signal'])}
 path=save('micromap_native_screen',snapshot)
 out={'status':'analysis_ready' if candidate else 'skip','snapshotPath':path,'observedUTC':iso(now),'reasons':snapshot['reasons'],'candidate':candidate,'consumedSignals':consume,'freshSetups':len(fresh)}
 if candidate:
  out['candidatePath']=save('micromap_candidate',candidate)
 return out,bool(candidate)
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
local_consumed=set()
try:
 if len(sys.argv)>1 and sys.argv[1]=='probe':print(json.dumps(probe(read(sys.argv[2]))),flush=True)
 else:
  n=int(sys.argv[2]) if len(sys.argv)>2 and sys.argv[1]=='watch' else 1
  for i in range(n):
   out,done=observe();print(json.dumps(out),flush=True)
   if done:break
   if i+1<n:time.sleep(15)
finally:mt5.shutdown()
