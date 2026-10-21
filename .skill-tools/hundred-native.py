"""Bounded demo experiment preflight. Native MT5 reads only; never sends orders."""
import sys,json,math,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
W=Path('E:/GPT/Inves');J=W/'trading-journal'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def iso(ms):return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def nowms():return int(datetime.now(timezone.utc).timestamp()*1000)
def write(p,d,exclusive=True):
 with Path(p).open('x' if exclusive else 'w',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2)
cfg=read(W/'Trading_Manager_Config.json');state=read(W/'Trading_Manager_State.json');protocol=read(cfg['experiment_protocol_path']);offset=cfg['broker_UTC_offset_minutes']*60000
if cfg['version'] not in ('DEMO_100_ROUNDTRIPS_1','DEMO_100_ROUNDTRIPS_2_GBPUSD_MOMENTUM'):raise RuntimeError('wrong_experiment')
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
try:
 a,t=mt5.account_info(),mt5.terminal_info();positions,orders=mt5.positions_get(),mt5.orders_get()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not a.trade_allowed or not t.connected:raise RuntimeError('matching_writable_demo_required')
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 if state['run_status']!='ACTIVE' or not cfg['enabled']:raise RuntimeError('STOPPED')
 if state.get('owned_positions') or state.get('pending_intent') or state.get('unknown_execution_outcome'):raise RuntimeError('reconcile_owned_exposure_first')
 if nowms()>=stamp(protocol['deadlineUTC'])-20000:print(json.dumps({'status':'deadline'}));sys.exit(0)
 if state['hundred']['closed']>=100:print(json.dumps({'status':'target_complete'}));sys.exit(0)
 news=read(W/'.skill-tools/hundred-news-cache.json');check_now=nowms()
 if not news['calendar'].get('ok') or news['calendar'].get('truncated') or check_now-stamp(news['collectedUTC'])>300000 or check_now-stamp(news['metadataUTC'])>900000:
  print(json.dumps({'status':'skip','reason':'news_unknown_or_stale'}));sys.exit(0)
 catalog={str(e['id']):e for e in news['events']['events']}
 for value in news['calendar']['values']:
  event=catalog.get(str(value['event_id']))
  if not event or event['importance']!='High importance':continue
  if value.get('time_unknown') or not value.get('time'):
   print(json.dumps({'status':'skip','reason':'news_time_unknown','event':event['name']}));sys.exit(0)
  release=stamp(value['time']+'Z')-offset
  if release-900000<=check_now<=release+900000:
   print(json.dumps({'status':'skip','reason':'relevant_high_impact_news','event':event['name'],'resumeUTC':iso(release+900000)}));sys.exit(0)
 row=protocol['plan'][state['hundred']['closed']];name=row['symbol']
 s=mt5.symbol_info(name);q=mt5.symbol_info_tick(name)
 if s is None or q is None or not s.visible or s.trade_mode!=mt5.SYMBOL_TRADE_MODE_FULL:raise RuntimeError('symbol_unavailable')
 if not all(x>0 for x in [s.trade_tick_size,s.point,s.volume_min,s.volume_step,s.trade_contract_size]):raise RuntimeError('contract_unknown')
 if not s.order_mode&1 or not s.order_mode&16 or not s.order_mode&32:raise RuntimeError('SL_TP_market_not_supported')
 rates=mt5.copy_rates_from_pos(name,mt5.TIMEFRAME_M1,0,30)
 if rates is None:raise RuntimeError('M1_unknown')
 now=nowms();bars=[{'t':int(b['time'])*1000-offset,'open':float(b['open']),'high':float(b['high']),'low':float(b['low']),'close':float(b['close'])} for b in rates if int(b['time'])*1000-offset+60000<=now]
 bars=sorted(bars,key=lambda b:b['t'])
 if len(bars)<16 or bars[-1]['t']!=now//60000*60000-60000 or any(bars[k]['t']-bars[k-1]['t']!=60000 for k in range(len(bars)-15,len(bars))):raise RuntimeError('fresh_closed_M1_missing')
 atr=sum(max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(len(bars)-14,len(bars)))/14
 ticks=mt5.copy_ticks_range(name,datetime.fromtimestamp((now-120000+offset)/1000,timezone.utc),datetime.fromtimestamp((now+offset)/1000,timezone.utc),mt5.COPY_TICKS_ALL)
 if ticks is None or len(ticks)<2:raise RuntimeError('native_ticks_missing')
 pts=[{'t':int(x['time_msc'])-offset,'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks if float(x['ask'])>=float(x['bid'])>0]
 if len(pts)<2:raise RuntimeError('native_ticks_invalid')
 last=pts[-1];previous=[p for p in pts if p['t']<=last['t']-5000]
 if not previous:raise RuntimeError('five_second_reference_missing')
 reference_age_ms=last['t']-5000-previous[-1]['t']
 delta=(last['bid']+last['ask']-previous[-1]['bid']-previous[-1]['ask'])/2
 side=('buy' if delta>0 else 'sell') if delta else row['zeroReturnSide']
 if row['arm']=='reversal' and delta:side='sell' if side=='buy' else 'buy'
 q=mt5.symbol_info_tick(name);now=nowms();age=(now-(q.time_msc-offset))/1000
 wait_until=now+10000
 while age>5 and now<wait_until:
  time.sleep(.5);q=mt5.symbol_info_tick(name);now=nowms();age=(now-(q.time_msc-offset))/1000
 if q.bid<=0 or q.ask<q.bid or age<0 or age>5:raise RuntimeError('quote_stale_or_invalid')
 spread=q.ask-q.bid;tick=s.trade_tick_size;minimum=max(.5*atr,4*spread,(s.trade_stops_level+2)*s.point,2*tick)
 volume=round(math.ceil((s.volume_min-s.volume_step*1e-7)/s.volume_step)*s.volume_step,8)
 if not s.volume_min<=volume<=s.volume_max:raise RuntimeError('broker_volume')
 if side=='buy':
  entry=q.ask;sl=round(math.floor((min(min(b['low'] for b in bars[-2:])-2*tick,q.bid-minimum)+tick*1e-7)/tick)*tick,s.digits)
  tp=round(math.ceil((entry+(entry-sl)-tick*1e-7)/tick)*tick,s.digits);typ=mt5.ORDER_TYPE_BUY
 else:
  entry=q.bid;sl=round(math.ceil((max(max(b['high'] for b in bars[-2:])+2*tick,q.ask+minimum)-tick*1e-7)/tick)*tick,s.digits)
  tp=round(math.floor((entry-(sl-entry)+tick*1e-7)/tick)*tick,s.digits);typ=mt5.ORDER_TYPE_SELL
 loss=mt5.order_calc_profit(typ,name,volume,entry,sl);margin=mt5.order_calc_margin(typ,name,volume,entry)
 if loss is None or margin is None or loss>=0 or margin<=0:raise RuntimeError('native_profit_margin_unknown')
 a=mt5.account_info()
 if a is None or margin>a.margin_free:print(json.dumps({'status':'skip','reason':'broker_free_margin','symbol':name,'requiredMargin':margin,'freeMargin':None if a is None else a.margin_free}));sys.exit(0)
 current=read(W/'Trading_Manager_State.json');current_cfg=read(W/'Trading_Manager_Config.json')
 if current['run_status']!='ACTIVE' or not current_cfg['enabled'] or current.get('pending_intent') or current.get('owned_positions') or current['hundred']['closed']!=state['hundred']['closed']:raise RuntimeError('state_changed')
 attempt=state['hundred']['attempts']+1;uid='D100_'+str(row['ordinal']).zfill(3)+'_'+str(attempt).zfill(3)+'_'+str(nowms())[-7:]
 paths={k:str(J/(uid+'_'+k+'.json')) for k in ['preflight','protocol','intent']}
 request={'symbol':name,'type':side,'volume':volume,'sl':sl,'tp':tp,'comment':uid}
 owned_protocol={'id':uid,'version':cfg['version'],'symbol':name,'comment':uid,'registeredUTC':iso(nowms()),'experimentKind':'ACTUAL_DEMO_100_EXPLORATION','countsAsMicroMAPStrategyTrade':False,'closeRequestAtSeconds':row['holdSeconds'],'holdingTargetSeconds':row['holdSeconds'],'row':row,'direction':side}
 preflight={'observedUTC':iso(nowms()),'version':cfg['version'],'row':row,'request':request,'entry':entry,'initialRiskUSD':-loss,'marginUSD':margin,'quoteAgeSeconds':age,'account':a._asdict(),'positions':[p._asdict() for p in positions],'orders':[o._asdict() for o in orders],'symbol':s._asdict(),'tick':q._asdict(),'closedBars':bars,'nativeTicks':pts,'fiveSecondReturn':delta,'referenceQuoteAgeAtWindowStartMS':reference_age_ms,'signalWindowEndUTC':iso(last['t']),'referenceMethod':'last-known native quote as of five seconds before last native tick','ATR14':atr,'spreadPrice':spread,'oldFinancialAndSignalGatesApplied':False}
 intent={'dedupKey':uid,'recordedUTC':iso(nowms()),'status':'INTENT','request':request,'ordinal':row['ordinal'],'row':row,'preflightPath':paths['preflight'],'protocolPath':paths['protocol'],'intentPath':paths['intent'],'expiresUTC':iso(nowms()+5000)}
 write(J/'execution.lock',{'dedupKey':uid,'intentPath':paths['intent']})
 write(paths['preflight'],preflight);write(paths['protocol'],owned_protocol);write(paths['intent'],intent)
 current['pending_intent']=intent;current['intents'].append(intent);current['hundred']['attempts']=attempt;current['stage']='INTENT';write(W/'Trading_Manager_State.json',current,False)
 print(json.dumps({'status':'ready','intent':intent,'request':request,'initialRiskUSD':-loss,'marginUSD':margin,'entry':entry,'contractSize':s.trade_contract_size,'brokerPoint':s.point,'equityUSD':a.equity,'freeMarginUSD':a.margin_free,'nativeSLProfitUSD':loss,'observedUTC':preflight['observedUTC'],'quoteUTC':iso(q.time_msc-offset)}),flush=True)
finally:mt5.shutdown()
