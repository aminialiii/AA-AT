"""Frozen research interpretation; native read-only tick replay. Never places orders."""
import sys,json,math,hashlib,bisect
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import MetaTrader5 as mt5
ROOT=Path('E:/GPT/Inves/research/poursamadi-backtest')
run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
model=json.loads((ROOT/'model-v1.json').read_text())
protocol=json.loads((ROOT/'protocol-v1.json').read_text())
assumptions=json.loads((ROOT/'execution-assumptions-v1.json').read_text())
history=json.loads(Path(protocol['history']['path']).read_text())
calendar=json.loads(Path(protocol['calendarPath']).read_text())
cfg=json.loads(Path('E:/GPT/Inves/Trading_Manager_Config.json').read_text(encoding='utf-8'))
bars=history['bars'];offset=history['brokerOffsetMinutes'];spec={**history['symbol'],'contract_size':history['symbol']['trade_contract_size']}
if abs(abs(history['nativeProbe']['onePriceUnitProfit'])-spec['contract_size']*spec['volume_min'])>1e-6:raise RuntimeError('linear_native_profit_probe_mismatch')
def iso(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat()
def stamp(s):return int(datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()*1000)
def count_codes(items):
 out={}
 for x in items:out[x['code']]=out.get(x['code'],0)+1
 return out
if hashlib.sha256(Path(protocol['history']['path']).read_bytes()).hexdigest()!=protocol['history']['sha256']:raise RuntimeError('history_hash_changed')
if any(b['low']>min(b['open'],b['close']) or b['high']<max(b['open'],b['close']) or b['high']<b['low'] or i and b['t']<=bars[i-1]['t'] for i,b in enumerate(bars)):raise RuntimeError('invalid_bars')
def priority(t):
 m=((t//60000)+180)%(24*60)
 return any((int(lo[:2])*60+int(lo[3:]))<=m<(int(hi[:2])*60+int(hi[3:])) for lo,hi in model['timePriority']['windows'])
events={str(e['id']):e for e in calendar['events']['events']}
if not calendar['events']['ok'] or not calendar['values']['ok'] or calendar['values']['truncated']:raise RuntimeError('historical_calendar_unknown')
blackouts=[];unknown_days=set()
for v in calendar['values']['values']:
 e=events.get(str(v['event_id']))
 if not e or e['importance']!='High importance':continue
 if v.get('time_unknown') or not v.get('time'):
  if v.get('time'):unknown_days.add(iso(stamp(v['time']+'Z')-offset*60000)[:10])
  else:raise RuntimeError('undated_high_USD_event')
  continue
 t=stamp(v['time']+'Z')-offset*60000;blackouts.append((t-15*60000,t+15*60000,str(v['event_id'])))
def news(t):return iso(t)[:10] in unknown_days or any(lo<=t<=hi for lo,hi,e in blackouts)
setups=[];bar_gaps=[]
for i,b in enumerate(bars):
 if i and b['t']-bars[i-1]['t']!=60000:bar_gaps.append({'afterUTC':iso(bars[i-1]['t']),'beforeUTC':iso(b['t']),'seconds':(b['t']-bars[i-1]['t'])/1000})
for i in range(20,len(bars)-3):
 if any(bars[k]['t']-bars[k-1]['t']!=60000 for k in range(i-19,i+2)):continue
 atr=sum(max(bars[k]['high']-bars[k]['low'],abs(bars[k]['high']-bars[k-1]['close']),abs(bars[k]['low']-bars[k-1]['close'])) for k in range(i-14,i))/14
 spike=bars[i:i+2]
 if atr<=0 or any(x['close']<=x['open'] or x['high']==x['low'] or (x['close']-x['open'])/(x['high']-x['low'])<.65 or (x['close']-x['low'])/(x['high']-x['low'])<.75 for x in spike):continue
 net=spike[-1]['close']-spike[0]['open']
 if net<2*atr:continue
 avg_range=sum(x['high']-x['low'] for x in spike)/2;prev=spike[-1];arms=[]
 for j in range(1,6):
  if i+1+j>=len(bars):break
  b=bars[i+1+j]
  if b['t']-prev['t']!=60000 or b['high']>=prev['high'] or b['high']-b['low']>.7*avg_range or b['low']<spike[-1]['close']-.5*net:break
  if j>=2:arms.append({'armed':b['t']+60000,'expires':b['t']+120000,'trigger':round(b['high']+.02,2),'sl':math.floor((b['low']-.02+1e-8)*100)/100,'microBars':j})
  prev=b
 if arms:setups.append({'id':model['version']+'|'+str(spike[0]['t']),'origin':spike[0]['t'],'arms':arms,'atr':atr})
plan={'registeredUTC':model['registeredUTC'],'historyHash':protocol['history']['sha256'],'setups':setups,'barGapCount':len(bar_gaps),'blackoutCount':len(blackouts),'unknownNewsDays':sorted(unknown_days),'assumptions':assumptions}
plan_path=ROOT/('candidate_plan_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with plan_path.open('x') as f:json.dump(plan,f)
print(json.dumps({'stage':'plan','setups':len(setups),'barGaps':len(bar_gaps),'newsBlackouts':len(blackouts),'planPath':str(plan_path)}),flush=True)
if not mt5.initialize('C:/Program Files/MetaTrader 5/terminal64.exe',timeout=5000):raise RuntimeError(str(mt5.last_error()))
rows=[];skip=[];tick_paths=[]
try:
 a,t=mt5.account_info(),mt5.terminal_info()
 if a is None or t is None or str(a.login)!=cfg['account_login'] or a.server!=cfg['account_server'] or a.currency!='USD' or a.trade_mode!=mt5.ACCOUNT_TRADE_MODE_DEMO or not t.connected:raise RuntimeError('account_gate')
 positions,orders=mt5.positions_get(),mt5.orders_get()
 if positions is None or orders is None:raise RuntimeError('exposure_unknown')
 if positions or orders:raise RuntimeError('exposure_present_read_only_research_paused')
 def replay(setup,ticks,latency):
  pts=[{'t':int(x['time_msc'])-offset*60000,'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks]
  if len(pts)<20 or any(p['bid']<=0 or p['ask']<p['bid'] or k and p['t']<pts[k-1]['t'] for k,p in enumerate(pts)):return {'code':'ticks_unknown_or_invalid'}
  times=[p['t'] for p in pts];first=setup['arms'][0]['armed'];last=setup['arms'][-1]['expires']+(assumptions['primaryLatencySeconds']+model['maxHoldingSeconds'])*1000
  if times[0]>first+5000 or times[-1]<last-5000 or any(times[k]-times[k-1]>10000 for k in range(1,len(times))):return {'code':'tick_coverage_gap'}
  trigger=None;arm=None
  for ar in setup['arms']:
   for p in pts[bisect.bisect_left(times,ar['armed']):bisect.bisect_left(times,ar['expires'])]:
    if p['bid']>=ar['trigger']:trigger=p;arm=ar;break
   if trigger:break
  if trigger is None:return {'code':'no_trigger'}
  idx=bisect.bisect_left(times,trigger['t']+latency*1000)
  if idx>=len(pts):return {'code':'delayed_quote_missing'}
  p=pts[idx]
  if p['t']-(trigger['t']+latency*1000)>5000 or p['t']-trigger['t']>45000:return {'code':'stale_trigger'}
  if p['bid']<arm['trigger']:return {'code':'trigger_lost_during_latency'}
  if news(trigger['t']) or news(p['t']):return {'code':'USD_news'}
  if p['ask']-p['bid']>model['risk']['maxSpreadPrice']+1e-8:return {'code':'spread'}
  entry=round(p['ask']+model['risk']['adverseEntryPrice'],2);sl=arm['sl']
  if sl>=p['bid'] or entry<=sl:return {'code':'structural_stop_invalid'}
  loss=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',spec['volume_min'],entry,sl)
  margin=mt5.order_calc_margin(mt5.ORDER_TYPE_BUY,'XAUUSD',spec['volume_min'],entry)
  if loss is None or margin is None or loss>=0 or margin<=0:return {'code':'native_risk_or_margin_unknown'}
  reserve_per_min=spec['contract_size']*spec['volume_min']*(model['risk']['reserveSlippagePrice']+model['risk']['reserveSpreadWideningPrice'])+7*spec['volume_min']
  min_total=-loss+reserve_per_min
  tp=round(entry+model['TP']['R']*(entry-sl),2)
  deadline=p['t']+model['maxHoldingSeconds']*1000
  future_news=[lo for lo,hi,e in blackouts if p['t']<lo<=deadline]
  if future_news:deadline=min(deadline,min(future_news))
  exit_pt=None;reason=None;mae=0.;mfe=0.;equity_path=[]
  for z in pts[idx:]:
   mae=max(mae,entry-z['bid']);mfe=max(mfe,z['bid']-entry)
   equity_path.append([z['t'],z['bid'],(z['bid']-entry)*spec['contract_size']*spec['volume_min']-7*spec['volume_min']/2])
   if z['bid']<=sl:exit_pt=z;reason='SL';break
   if z['bid']>=tp:exit_pt=z;reason='TP';break
   if z['t']>=deadline:exit_pt=z;reason='news_exit' if future_news else 'time_exit';break
  if exit_pt is None:return {'code':'exit_quote_missing'}
  exit_price=round((min(exit_pt['bid'],tp) if reason=='TP' else exit_pt['bid'])-model['risk']['adverseExitPrice'],2)
  gross=mt5.order_calc_profit(mt5.ORDER_TYPE_BUY,'XAUUSD',spec['volume_min'],entry,exit_price)
  if gross is None:return {'code':'native_exit_profit_unknown'}
  commission=7*spec['volume_min'];net_pnl=gross-commission
  return {'code':'simulated','setupId':setup['id'],'originUTC':iso(setup['origin']),'entryTime':p['t'],'entryUTC':iso(p['t']),'exitTime':exit_pt['t'],'exitUTC':iso(exit_pt['t']),'triggerUTC':iso(trigger['t']),'side':'buy','volumeMin':spec['volume_min'],'entry':entry,'SL':sl,'TP':tp,'exit':exit_price,'exitReason':reason,'priceRiskUSDMin':-loss,'reserveUSDMin':reserve_per_min,'totalRiskUSDMin':min_total,'marginUSDMin':margin,'grossUSDMin':gross,'commissionUSDMin':commission,'netUSDMin':net_pnl,'netR':net_pnl/(-loss),'MAEPriceObserved':mae,'MFEPriceObserved':mfe,'equityPathMin':equity_path,'timePriority':priority(p['t']),'latencySeconds':latency}
 for k,setup in enumerate(setups):
  start=setup['arms'][0]['armed'];end=setup['arms'][-1]['expires']+(assumptions['primaryLatencySeconds']+model['maxHoldingSeconds']+10)*1000
  d1=datetime.fromtimestamp(start/1000,timezone.utc)+timedelta(minutes=offset);d2=datetime.fromtimestamp(end/1000,timezone.utc)+timedelta(minutes=offset)
  ticks=mt5.copy_ticks_range('XAUUSD',d1,d2,mt5.COPY_TICKS_ALL)
  if ticks is None:skip.append({'setupId':setup['id'],'code':'native_ticks_unavailable','error':str(mt5.last_error())});continue
  tick_path=ROOT/('ticks_'+run_id+'_'+str(setup['origin'])+'.json')
  tick_record={'source':'native_copy_ticks_range','setupId':setup['id'],'offsetMinutes':offset,'ticks':[{'time_msc':int(x['time_msc']),'bid':float(x['bid']),'ask':float(x['ask'])} for x in ticks]}
  with tick_path.open('x') as f:json.dump(tick_record,f,separators=(',',':'))
  tick_paths.append(str(tick_path))
  primary=replay(setup,ticks,assumptions['primaryLatencySeconds']);zero=replay(setup,ticks,assumptions['diagnosticLatencySeconds'])
  if primary['code']=='simulated':rows.append(primary)
  else:skip.append({'setupId':setup['id'],**primary})
  setup['diagnosticZeroLatency']=zero
  if (k+1)%25==0:print(json.dumps({'stage':'ticks','processed':k+1,'setups':len(setups),'primarySimulations':len(rows),'skips':len(skip)}),flush=True)
finally:mt5.shutdown()
def metrics(trades,initial):
 pos=sum(x['netUSD'] for x in trades if x['netUSD']>0);neg=-sum(x['netUSD'] for x in trades if x['netUSD']<0)
 equity=initial;peak=initial;dd=0.;streak=0;max_streak=0
 for x in trades:
  for tm,bid,floating_min in x['equityPathMin']:
   floating=equity+floating_min*x['volume']/spec['volume_min'];peak=max(peak,floating);dd=max(dd,(peak-floating)/peak)
  equity+=x['netUSD'];peak=max(peak,equity);dd=max(dd,(peak-equity)/peak)
  streak=streak+1 if x['netUSD']<0 else 0;max_streak=max(max_streak,streak)
 return {'N':len(trades),'netUSD':sum(x['netUSD'] for x in trades),'grossUSD':sum(x['grossUSD'] for x in trades),'feesUSD':sum(x['commissionUSD'] for x in trades),'PF':pos/neg if neg else None,'winRate':sum(x['netUSD']>0 for x in trades)/len(trades) if trades else None,'expectancyR':sum(x['netR'] for x in trades)/len(trades) if trades else None,'observedMaxDDFraction':dd,'maxConsecutiveLosses':max_streak,'endEquityUSD':equity}
def portfolio(start,end):
 initial=model['risk']['initialSimulatedEquityUSD'];eq=peak=initial;day=None;fills=losses=0;busy_until=0;trades=[];rejected=[];halt=False
 for row in sorted((x for x in rows if start<=x['entryTime']<end),key=lambda x:x['entryTime']):
  date=row['entryUTC'][:10]
  if date!=day:day=date;fills=losses=0
  if halt:rejected.append({'setupId':row['setupId'],'code':'preserved_peak_DD_halt'});continue
  if row['entryTime']<busy_until:rejected.append({'setupId':row['setupId'],'code':'one_position'});continue
  if fills>=12 or losses>=2:rejected.append({'setupId':row['setupId'],'code':'daily_cap'});continue
  budget=min(eq*.01,eq-peak*.98,eq*.1)
  raw=budget/row['totalRiskUSDMin']*spec['volume_min'];volume=math.floor((min(raw,spec['volume_max'])+1e-10)/spec['volume_step'])*spec['volume_step']
  while volume>=spec['volume_min']-1e-10 and row['marginUSDMin']*volume/spec['volume_min']>eq*.5:volume=round(volume-spec['volume_step'],8)
  if volume<spec['volume_min']-1e-10:rejected.append({'setupId':row['setupId'],'code':'min_volume_or_margin','budgetUSD':budget,'minimumRiskUSD':row['totalRiskUSDMin']});continue
  multiplier=volume/spec['volume_min'];trade={**row,'volume':volume,'riskBudgetUSD':budget,'initialRiskUSD':row['priceRiskUSDMin']*multiplier,'grossUSD':row['grossUSDMin']*multiplier,'commissionUSD':row['commissionUSDMin']*multiplier,'netUSD':row['netUSDMin']*multiplier}
  for k,(tm,bid,floating_min) in enumerate(row['equityPathMin']):
   floating=eq+floating_min*multiplier;peak=max(peak,floating)
   if floating<=peak*.98:
    trade['exitTime']=tm;trade['exitUTC']=iso(tm);trade['exit']=round(bid-model['risk']['adverseExitPrice'],2);trade['exitReason']='preserved_peak_DD_exit';trade['grossUSD']=(trade['exit']-trade['entry'])*spec['contract_size']*volume;trade['netUSD']=trade['grossUSD']-trade['commissionUSD'];trade['netR']=trade['netUSD']/trade['initialRiskUSD'];trade['equityPathMin']=row['equityPathMin'][:k+1];trade['MAEPriceObserved']=max(0,max(trade['entry']-z[1] for z in trade['equityPathMin']));trade['MFEPriceObserved']=max(0,max(z[1]-trade['entry'] for z in trade['equityPathMin']));trade['grossUSDMin']=trade['grossUSD']/multiplier;trade['netUSDMin']=trade['netUSD']/multiplier;halt=True;break
  trades.append(trade)
  eq+=trade['netUSD'];peak=max(peak,eq);fills+=1;losses+=trade['netUSD']<0;busy_until=trade['exitTime']
  if eq<=peak*.98:halt=True
 return {'metrics':metrics(trades,initial),'trades':trades,'rejected':rejected,'skipCounts':count_codes(rejected)}
spl=model['split'];boundaries=[('train',stamp(spl['trainFromUTC']),stamp(spl['trainToUTC'])),('validation',stamp(spl['trainToUTC']),stamp(spl['validationToUTC'])),('test',stamp(spl['validationToUTC']),stamp(spl['testToUTC']))]
partitions={name:portfolio(lo,hi) for name,lo,hi in boundaries}
diagnostic=[{**x,'volume':spec['volume_min'],'grossUSD':x['grossUSDMin'],'commissionUSD':x['commissionUSDMin'],'netUSD':x['netUSDMin']} for x in rows]
diagnostic_metrics=metrics(diagnostic,100.55)
for field in ['observedMaxDDFraction','endEquityUSD']:diagnostic_metrics.pop(field,None)
test=partitions['test']['metrics'];accept=model['acceptance'];failures=[]
if test['N']<accept['minOOSClosedTrades']:failures.append('OOS_sample_below_30')
if test['netUSD']<=0:failures.append('OOS_net_not_positive')
if test['PF'] is None or test['PF']<accept['PFAtLeast']:failures.append('OOS_PF_below_1.1_or_undefined')
if test['observedMaxDDFraction']>=accept['maxControlledObservedDD']:failures.append('OOS_DD_halt_or_limit')
result={'recordedUTC':datetime.now(timezone.utc).isoformat(),'version':model['version'],'teacherExactRules':False,'userApprovedAgentInterpretation':True,'historyPath':protocol['history']['path'],'historyHash':protocol['history']['sha256'],'calendarPath':protocol['calendarPath'],'planPath':str(plan_path),'bars':len(bars),'setups':len(setups),'primaryLatencySeconds':assumptions['primaryLatencySeconds'],'primarySimulations':len(rows),'simulationSkips':count_codes(skip),'partitions':partitions,'fixedMinLotDiagnostic':diagnostic_metrics,'zeroLatencyDiagnosticSimulations':sum(x['diagnosticZeroLatency']['code']=='simulated' for x in setups if 'diagnosticZeroLatency' in x),'researchGatePassed':not failures,'acceptanceFailures':failures,'tickPaths':tick_paths,'rows':rows,'skippedSetups':skip,'limitations':['Not a replication of the seven videos or exact teacher method.','Untouched chronological historical holdout; not prospective actual fills.','Current symbol specs and leverage applied to historical replay.','20-second latency/slippage/commission are frozen assumptions, not historical broker charges.','Daily sessions are UTC dates; three split portfolios are independent simulations.','Fixed-minimum-volume diagnostic may overlap and exceed account risk; it is not a deployable return.','Observed tick gaps reject replay; missing archive coverage cannot establish profitability.','Historical calendar metadata is current; original historical classifications were not reconstructed.','Real account peak/counters are not modified by this script.']}
result_path=ROOT/('backtest_result_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with result_path.open('x') as f:json.dump(result,f)
print(json.dumps({'stage':'complete','resultPath':str(result_path),'bars':len(bars),'setups':len(setups),'primarySimulations':len(rows),'simulationSkips':result['simulationSkips'],'partitions':{k:v['metrics'] for k,v in partitions.items()},'fixedMinLotDiagnostic':result['fixedMinLotDiagnostic'],'researchGatePassed':result['researchGatePassed'],'acceptanceFailures':failures}),flush=True)
