"""Offline causal M1 research. All executions are SIMULATED; no MT5 import."""
import sys,json,math,hashlib,gzip,csv,os,itertools
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
import numpy as np
R=Path('E:/GPT/Inves/research/overnight-20261010')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def utc():return datetime.now(timezone.utc).isoformat()
def iso(t):return datetime.fromtimestamp(float(t),timezone.utc).isoformat()
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(kind,d):
 p=R/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2,allow_nan=False)
 return str(p)
def state_update(**items):
 s=read(R/'state.json');s.update(items);s['updatedUTC']=utc();tmp=R/'state.tmp';tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,R/'state.json');return s
def finish(stage,p,**extra):
 s=read(R/'state.json');done=s['completedStages']
 if stage not in done:done.append(stage)
 state_update(completedStages=done,**extra)
 print(json.dumps({'stage':stage,'artifactPath':p,**extra}),flush=True)
def manifest():
 ptr=read(R/'history_pointer.json')
 if digest(ptr['path'])!=ptr['sha256']:raise RuntimeError('manifest_hash_changed')
 return read(ptr['path'])
def plan():
 if (R/'plan.json').exists():print(json.dumps({'stage':'plan','path':str(R/'plan.json'),'alreadyRegistered':True}));return
 m=manifest();req=read(R/'request.json');cut=stamp(read(R/'history-extension.json')['quarantineFromUTC']);arrays=[]
 for name,row in m['symbols'].items():
  if row['status']!='AVAILABLE':continue
  if digest(row['path'])!=row['sha256']:raise RuntimeError('archive_hash_changed')
  a=np.load(row['path'])['rates'];ts=a['time']-m['brokerOffsetMinutes']*60;arrays.append(ts)
 start=max(float(a[0]) for a in arrays)+7200
 daysets=[set((a[(a>=start)&(a<cut)]//86400).tolist()) for a in arrays]
 days=sorted(set.intersection(*daysets));days=[int(d) for d in days]
 if len(days)<20:raise RuntimeError('insufficient_common_unexposed_days')
 a=int(len(days)*.60);b=int(len(days)*.80)
 bounds={'train':[days[0]*86400,days[a]*86400],'validation':[days[a]*86400,days[b]*86400],'holdout':[days[b]*86400,cut]}
 models=[]
 for family,body,stop,session in itertools.product(req['models'],req['grid']['bodyATR'],req['grid']['minStopATR'],req['grid']['sessions']):
  item={'family':family,'bodyATR':body,'minStopATR':stop,'session':session,'targetR':2};item['id']='OR1_'+hashlib.sha256(json.dumps(item,sort_keys=True).encode()).hexdigest()[:12];models.append(item)
 p={'registeredUTC':utc(),'requestHash':digest(R/'request.json'),'manifestPath':read(R/'history_pointer.json')['path'],'manifestHash':digest(read(R/'history_pointer.json')['path']),'priorDataQuarantineFromUTC':iso(cut),'commonTradingDays':days,'bounds':bounds,'boundsUTC':{n:list(map(iso,x)) for n,x in bounds.items()},'models':models,'registeredConfigurations':len(models)*len(req['symbols']),'holdoutReleaseUTC':req['holdoutReleaseUTC'],'holdoutOutcomeQueriesBeforeRegistration':0,'sources':req['sources'],'status':'REGISTERED_BEFORE_MODEL_OUTCOMES','timeLimitation':'Measured180minute broker offset applied to July-September archive; session UTC labels remain conditional on historical offset consistency.'}
 with (R/'plan.json').open('x',encoding='utf-8') as f:json.dump(p,f,ensure_ascii=False,indent=2)
 artifact=save('cycle01_data_registration',{'kind':'SIMULATION_RESEARCH','planPath':str(R/'plan.json'),'totalRawBars':sum(v.get('bars',0) for v in m['symbols'].values()),'usableUnexposedDays':len(days),'boundsUTC':p['boundsUTC'],'configurations':p['registeredConfigurations'],'knownOldHundredCycles':'Repeated same prior result; not independent experiments. Never used as new backtest evidence.'})
 finish('plan',artifact,nextStage='grid')
def load_data(name,end):
 m=manifest();row=m['symbols'][name]
 if digest(row['path'])!=row['sha256']:raise RuntimeError('archive_hash_changed_'+name)
 raw=np.load(row['path'])['rates'];ts=raw['time']-m['brokerOffsetMinutes']*60;mask=ts<end;a=raw[mask];ts=ts[mask]
 o,h,l,c=[a[n].astype(float) for n in ['open','high','low','close']];n=len(a)
 tr=np.maximum(h-l,np.maximum(np.abs(h-np.r_[c[0],c[:-1]]),np.abs(l-np.r_[c[0],c[:-1]])))
 def mean(x,k):return np.convolve(x,np.ones(k)/k,'full')[:n]
 def ema(k):
  out=np.empty(n);out[0]=c[0];alpha=2/(k+1)
  for i in range(1,n):out[i]=alpha*c[i]+(1-alpha)*out[i-1]
  return out
 atr=mean(tr,14);e20,e60=ema(20),ema(60);atr=np.maximum(atr,float(row['spec']['trade_tick_size']))
 # Previous bars only: never use the spread or extreme finalized after entry.
 prior_high=np.r_[np.full(20,np.nan),np.max(np.lib.stride_tricks.sliding_window_view(h,20),axis=1)[:-1]]
 prior_low=np.r_[np.full(20,np.nan),np.min(np.lib.stride_tricks.sliding_window_view(l,20),axis=1)[:-1]]
 sp=a['spread'].astype(float)*row['spec']['point'];previous_sp=np.r_[np.full(5,np.nan),np.max(np.lib.stride_tricks.sliding_window_view(sp,5),axis=1)[:-1]]
 tick=float(row['spec']['trade_tick_size'] or row['spec']['point']);spread=np.maximum(np.nan_to_num(previous_sp,nan=tick),tick)*1.25
 valid=np.ones(n,dtype=bool);valid[:100]=False
 gaps=(np.diff(ts)!=60)
 for j in np.flatnonzero(gaps):valid[j+1:min(n,j+101)]=False
 return {'name':name,'raw':a,'t':ts,'o':o,'h':h,'l':l,'c':c,'atr':atr,'ema20':e20,'ema60':e60,'hi20':prior_high,'lo20':prior_low,'spread':spread,'valid':valid,'spec':row['spec'],'tick':tick}
def signals(d,p):
 o,h,l,c,atr=d['o'],d['h'],d['l'],d['c'],d['atr'];body=(c-o)/atr;diff=(d['ema20']-d['ema60'])/atr;threshold=p['bodyATR'];f=p['family'];out=np.zeros(len(c),dtype=np.int8)
 if f=='M1_MOMENTUM_PROXY':
  prev=np.r_[c[0],c[:-1]];out[(body>=threshold)&(c>prev)]=1;out[(body<=-threshold)&(c<prev)]=-1
 elif f=='TREND_PULLBACK':
  out[(diff>.35)&(l<=d['ema20']+.1*atr)&(c>d['ema20'])&(body>=threshold)]=1
  out[(diff<-.35)&(h>=d['ema20']-.1*atr)&(c<d['ema20'])&(body<=-threshold)]=-1
 elif f=='RANGE_REJECTION':
  out[(abs(diff)<.25)&(l<=d['lo20']+.1*atr)&(c>d['lo20']+.2*atr)&(body>=threshold)]=1
  out[(abs(diff)<.25)&(h>=d['hi20']-.1*atr)&(c<d['hi20']-.2*atr)&(body<=-threshold)]=-1
 elif f=='BREAK_RETEST':
  level=None;direction=0;origin=0
  for i in range(100,len(c)):
   if not d['valid'][i]:level=None;continue
   if level is not None:
    if i-origin>5:level=None
    elif direction==1 and l[i]<=level+.1*atr[i] and c[i]>level+.05*atr[i] and body[i]>=threshold:out[i]=1;level=None
    elif direction==-1 and h[i]>=level-.1*atr[i] and c[i]<level-.05*atr[i] and body[i]<=-threshold:out[i]=-1;level=None
   if level is None and out[i]==0:
    if c[i]>d['hi20'][i]+.05*atr[i] and body[i]>=.3:level=d['hi20'][i];direction=1;origin=i
    elif c[i]<d['lo20'][i]-.05*atr[i] and body[i]<=-.3:level=d['lo20'][i];direction=-1;origin=i
 elif f=='SP2L_AGENT_INTERPRETATION':
  for i in range(100,len(c)):
   if not d['valid'][i]:continue
   for count in range(2,6):
    start=i-count-2;spike=range(start,start+2);micro=range(start+2,i)
    for side in [1,-1]:
     if side*body[i]<threshold:continue
     if any(side*(c[k]-o[k])<.65*(h[k]-l[k]) for k in spike):continue
     impulse=side*(c[start+1]-o[start])
     if impulse<2*atr[start-1]:continue
     avg=(h[start]-l[start]+h[start+1]-l[start+1])/2
     if any(h[k]-l[k]>.7*avg or (side==1 and h[k]>=h[k-1]) or (side==-1 and l[k]<=l[k-1]) for k in micro):continue
     if side==1 and min(l[k] for k in micro)>=c[start+1]-.5*impulse and c[i]>h[i-1]+d['tick']:out[i]=1
     if side==-1 and max(h[k] for k in micro)<=c[start+1]+.5*impulse and c[i]<l[i-1]-d['tick']:out[i]=-1
     if out[i]:break
    if out[i]:break
 else:raise RuntimeError('unknown_model')
 out[~d['valid']]=0
 if p['session']=='EU_US':
  hh=((d['t']+60)%86400)//3600;out[(hh<7)|(hh>=20)]=0
 return out
def profit(name,side,entry,exit,units):
 gross=side*(exit-entry)*units
 return gross/exit if name in ['USDJPY','USDCHF','USDCAD'] else gross
def rr_tp(name,side,entry,risk,units):
 target=2*risk
 if name in ['USDJPY','USDCHF','USDCAD']:return units*entry/(units-side*target)
 return entry+side*target/units
def replay(d,p,lo,hi,spread_mult=1,fee_per_lot=7,delay_bars=0):
 sig=signals(d,p);spec=d['spec'];tick=d['tick'];volume=spec['volume_min'];units=spec['trade_contract_size']*volume;out=[];censored=[];skips={};i=max(100,int(np.searchsorted(d['t'],lo)));end=int(np.searchsorted(d['t'],hi));cost=fee_per_lot*volume
 while i<end-1:
  side=int(sig[i]);j=i+1+delay_bars
  if not side or j>=end:i+=1;continue
  if d['t'][j]-d['t'][i]!=(1+delay_bars)*60:skips['entry_gap']=skips.get('entry_gap',0)+1;i+=1;continue
  sp=float(d['spread'][i])*spread_mult
  if sp/d['atr'][i]>.25:skips['spread_ATR']=skips.get('spread_ATR',0)+1;i+=1;continue
  entry=float(d['o'][j])+(sp if side==1 else 0)+side*.5*tick
  minimum=max(p['minStopATR']*d['atr'][i],4*sp,spec['trade_stops_level']*spec['point'])
  if side==1:sl=min(float(min(d['l'][i-2:i+1]))-2*tick,entry-minimum);sl=math.floor((sl+tick*1e-8)/tick)*tick
  else:sl=max(float(max(d['h'][i-2:i+1]))+sp+2*tick,entry+minimum);sl=math.ceil((sl-tick*1e-8)/tick)*tick
  risk=-profit(d['name'],side,entry,sl,units)
  if risk<=0:i+=1;continue
  tp=rr_tp(d['name'],side,entry,risk,units);tp=(math.ceil((tp-tick*1e-8)/tick) if side==1 else math.floor((tp+tick*1e-8)/tick))*tick
  planned_rr=profit(d['name'],side,entry,tp,units)/risk
  if planned_rr<2-1e-6:raise RuntimeError('RR2_rounding_failure')
  k=j;reason=None;ambiguity=False;gap=False;mae=0.;mfe=0.
  while k<end:
   sx=float(d['spread'][k-1])*spread_mult;high=float(d['h'][k])+(sx if side==-1 else 0);low=float(d['l'][k])+(sx if side==-1 else 0);op=float(d['o'][k])+(sx if side==-1 else 0)
   hit_sl=low<=sl if side==1 else high>=sl;hit_tp=high>=tp if side==1 else low<=tp
   gap=gap or (k>j and d['t'][k]-d['t'][k-1]!=60)
   mae=max(mae,entry-low if side==1 else high-entry);mfe=max(mfe,high-entry if side==1 else entry-low)
   if hit_sl:
    price=(min(sl,op) if side==1 else max(sl,op))-side*2*tick;reason='SL';ambiguity=bool(hit_tp);break
   if hit_tp:price=tp;reason='TP';break
   k+=1
  base={'kind':'SIMULATION_M1_APPROXIMATION','symbol':d['name'],'modelId':p['id'],'family':p['family'],'signalBarUTC':iso(d['t'][i]),'informationThroughUTC':iso(d['t'][i]+60),'entryUTC':iso(d['t'][j]),'entryBarTime':int(d['t'][j]),'side':'buy' if side==1 else 'sell','entry':entry,'SL':sl,'TP':tp,'volume':volume,'priceRiskUSD':risk,'plannedRR':planned_rr,'signalBodyATR':float(abs((d['c'][i]-d['o'][i])/d['atr'][i])),'signalATR':float(d['atr'][i]),'spreadPriceAssumption':sp,'spreadATR':float(sp/d['atr'][i]),'trendStrength':float(abs(d['ema20'][i]-d['ema60'][i])/d['atr'][i]),'sessionAssumedUTC':session(int(d['t'][j])),'entryHourAssumedUTC':int((d['t'][j]%86400)//3600),'signalReason':p['family']+' with completed M1 information','MAEPriceBarBound':max(0,mae),'MFEPriceBarBound':max(0,mfe),'excursionsKind':'bar bounds; not tick-observed','delayBarsDiagnostic':delay_bars}
  if reason is None:censored.append({**base,'exitReason':'OPEN_CENSORED','excludedFromWR':True});break
  gross=profit(d['name'],side,entry,price,units);nights=max(0,int((d['t'][k]+10800)//86400)-int((d['t'][j]+10800)//86400));swap_scenario=10*volume*nights;net=gross-cost-swap_scenario
  out.append({**base,'exitBarUTC':iso(d['t'][k]),'exitUTCUpperBound':iso(d['t'][k]+60),'exitBarTime':int(d['t'][k]),'exit':price,'exitReason':reason,'grossUSD':gross,'commissionScenarioUSD':cost,'swapScenarioUSD':swap_scenario,'historicalActualCostsKnown':False,'netUSD':net,'netR':net/risk,'bothSLTPInSameBar':ambiguity,'priceGapDuringTrade':bool(gap),'overnightCount':nights,'holdingMinutesUpperBound':int((d['t'][k]-d['t'][j])/60+1),'successFailureCause':reason+(' conservative both-hit' if ambiguity else '')})
  i=k+1
 return out,censored,skips
def session(t):
 h=(t%86400)//3600
 return 'ASIA' if h<7 else 'EUROPE' if h<12 else 'EU_US_OVERLAP' if h<17 else 'US_LATE' if h<21 else 'ROLLOVER'
def metrics(rows,censored=0):
 x=np.array([r['netR'] for r in rows],float);n=len(x);wins=int(np.sum(x>0));losses=int(np.sum(x<0));pos=float(np.sum(x[x>0]));neg=-float(np.sum(x[x<0]));eq=np.r_[0,np.cumsum(x)];dd=float(np.max(np.maximum.accumulate(eq)-eq)) if n else 0
 if n:
  z=1.959963984540054;v=wins/n;den=1+z*z/n;mid=(v+z*z/(2*n))/den;rad=z*math.sqrt(v*(1-v)/n+z*z/(4*n*n))/den;wilson=[max(0,(mid-rad)*100),min(100,(mid+rad)*100)]
 else:wilson=[None,None]
 return {'n':n,'wins':wins,'losses':losses,'flats':n-wins-losses,'winRatePct':wins/n*100 if n else None,'wilson95Pct':wilson,'TPHits':sum(r['exitReason']=='TP' for r in rows),'SLHits':sum(r['exitReason']=='SL' for r in rows),'netR':float(np.sum(x)),'expectancyR':float(np.mean(x)) if n else None,'profitFactorR':pos/neg if neg else None,'maxClosedTradeDrawdownR':dd,'averagePlannedRR':sum(r['plannedRR'] for r in rows)/n if n else None,'netUSDAtBrokerMinVolume':sum(r['netUSD'] for r in rows),'commissionScenarioUSD':sum(r['commissionScenarioUSD'] for r in rows),'swapScenarioUSD':sum(r['swapScenarioUSD'] for r in rows),'intrabarAmbiguous':sum(r['bothSLTPInSameBar'] for r in rows),'overnightTrades':sum(r['overnightCount']>0 for r in rows),'censoredNotCounted':censored,'equityKind':'fixed1R per trade; not actual account equity or capital-feasible portfolio'}
def grid():
 s=read(R/'state.json')
 if s.get('gridPath'):print(json.dumps({'stage':'grid','alreadyCompleted':True,'artifactPath':s['gridPath']}));return
 p=read(R/'plan.json');m=manifest();bounds=p['bounds'];rows=[];run=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');trades_path=R/('grid_trades_'+run+'.jsonl.gz');censor_path=R/('grid_censored_'+run+'.jsonl.gz');trades=0
 with gzip.open(trades_path,'xb') as log,gzip.open(censor_path,'xb') as cens:
  for name in read(R/'request.json')['symbols']:
   if m['symbols'][name]['status']!='AVAILABLE':continue
   d=load_data(name,bounds['validation'][1])
   for model in p['models']:
    row={'symbol':name,'model':model,'partitions':{}}
    for part in ['train','validation']:
     ts,cs,sk=replay(d,model,*bounds[part]);row['partitions'][part]=metrics(ts,len(cs));row['partitions'][part]['skipCounts']=sk
     for tr in ts:log.write((json.dumps({**tr,'partition':part},separators=(',',':'))+'\n').encode());trades+=1
     for tr in cs:cens.write((json.dumps({**tr,'partition':part},separators=(',',':'))+'\n').encode())
    rows.append(row)
   print(json.dumps({'stage':'grid_progress','symbol':name,'configurationsCompleted':len(rows),'simulatedRows':trades,'holdoutEvaluated':False}),flush=True)
 path=save('cycle03_finite_grid',{'kind':'SIMULATION_RESEARCH','registeredPlanHash':digest(R/'plan.json'),'manifestHash':p['manifestHash'],'rows':rows,'tradesPath':str(trades_path),'tradesSHA256':digest(trades_path),'censoredPath':str(censor_path),'simulatedRows':trades,'holdoutEvaluated':False,'limit':'M1 assumptions; all rows are simulated, never actual demo fills.'})
 finish('grid',path,gridPath=path,nextStage='walkforward')
def score(m):
 if m['n']<50 or m['expectancyR'] is None:return -1e6
 return m['expectancyR']-.15*m['maxClosedTradeDrawdownR']/m['n']
def trade_rows():
 g=read(read(R/'state.json')['gridPath']);groups={}
 if digest(g['tradesPath'])!=g['tradesSHA256']:raise RuntimeError('trade_archive_hash_changed')
 with gzip.open(g['tradesPath'],'rt',encoding='utf-8') as f:
  for line in f:
   t=json.loads(line);groups.setdefault((t['symbol'],t['modelId']),[]).append(t)
 return groups
def walkforward():
 st=read(R/'state.json')
 if st.get('walkforwardPath'):print(json.dumps({'stage':'walkforward','alreadyCompleted':True}));return
 p=read(R/'plan.json');groups=trade_rows();dates=[d for d in p['commonTradingDays'] if d*86400<p['bounds']['validation'][1]];n=len(dates);results=[]
 for name in read(R/'request.json')['symbols']:
  data=load_data(name,p['bounds']['validation'][1])
  for fraction in [.4,.6,.8]:
   start=dates[int(n*fraction)]*86400;stop=dates[min(n-1,int(n*(fraction+.2)))]*86400 if fraction<.8 else p['bounds']['validation'][1]
   ranked=[]
   for model in p['models']:
    training=[r for r in groups.get((name,model['id']),[]) if r['exitBarTime']+60<=start];mm=metrics(training);ranked.append((score(mm),model,mm))
   ranked.sort(key=lambda v:v[0],reverse=True);_,choice,train=ranked[0];ts,cs,sk=replay(data,choice,start,stop)
   results.append({'symbol':name,'trainingThroughUTC':iso(start),'evaluationFromUTC':iso(start),'evaluationToUTC':iso(stop),'selectedUsingTrainingOnly':choice,'train':train,'evaluation':metrics(ts,len(cs)),'skips':sk})
 path=save('cycle04_walkforward',{'kind':'SIMULATION_WALK_FORWARD','folds':results,'holdoutEvaluated':False,'notes':['Each fold chooses using prior closed trades only, then starts a fresh flat simulation.','Model choices can differ across chronological folds; results are not duplicated cycle statistics.']})
 finish('walkforward',path,walkforwardPath=path,nextStage='select')
def bootstrap(rows,seed=20261010,reps=3000):
 days={}
 for r in rows:days.setdefault(r['entryBarTime']//86400,[]).append(r['netR'])
 groups=list(days.values())
 if len(groups)<5:return {'days':len(groups),'lower95':None,'upper95':None,'status':'insufficient_independent_days'}
 sums=np.array([sum(x) for x in groups]);counts=np.array([len(x) for x in groups]);rng=np.random.default_rng(seed);idx=rng.integers(0,len(groups),(reps,len(groups)));e=sums[idx].sum(axis=1)/counts[idx].sum(axis=1)
 return {'days':len(groups),'repetitions':reps,'seed':seed,'lower95':float(np.percentile(e,2.5)),'upper95':float(np.percentile(e,97.5)),'status':'day_block_resampling; unadjusted post-selection diagnostic'}
def choose():
 st=read(R/'state.json')
 if st.get('selectionPath'):print(json.dumps({'stage':'select','alreadyCompleted':True}));return
 p=read(R/'plan.json');g=read(st['gridPath']);wf=read(st['walkforwardPath']);groups=trade_rows();choices=[]
 for name in read(R/'request.json')['symbols']:
  eligible=[x for x in g['rows'] if x['symbol']==name];eligible.sort(key=lambda x:score(x['partitions']['validation']),reverse=True);best=eligible[0];m=best['partitions']['validation'];rows=[r for r in groups.get((name,best['model']['id']),[]) if r['partition']=='validation'];ci=bootstrap(rows);folds=[f for f in wf['folds'] if f['symbol']==name];positive=sum((f['evaluation']['expectancyR'] or -1)<=0 for f in folds)==0
  positive_folds=sum((f['evaluation']['expectancyR'] or -1)>0 for f in folds)
  passing=m['n']>=50 and (m['expectancyR'] or -1)>0 and (m['profitFactorR'] or 0)>=1.15 and ci['lower95'] is not None and ci['lower95']>0 and positive_folds>=2
  choices.append({'symbol':name,'model':best['model'],'train':best['partitions']['train'],'validation':m,'validationDayBootstrap':ci,'positiveWalkForwardFolds':sum((f['evaluation']['expectancyR'] or -1)>0 for f in folds),'provisionalGate':passing,'provenWRAbove50':m['wilson95Pct'][0] is not None and m['wilson95Pct'][0]>50,'status':'PROVISIONAL_BAR_CANDIDATE' if passing else 'EXPLORATORY_NOT_CONFIRMED'})
 choices.sort(key=lambda c:score(c['validation']),reverse=True)
 hist={'hour':{},'session':{},'bodyBand':{},'trendBand':{}}
 for ch in choices:
  rows=[r for r in groups.get((ch['symbol'],ch['model']['id']),[]) if r['partition']=='validation']
  for field,keyer in [('hour',lambda r:str(r['entryHourAssumedUTC'])),('session',lambda r:r['sessionAssumedUTC']),('bodyBand',lambda r:'WEAK' if r['signalBodyATR']<.45 else 'STRONG'),('trendBand',lambda r:'TREND' if r['trendStrength']>.35 else 'RANGE_OR_WEAK')]:
   grouped={}
   for row in rows:grouped.setdefault(keyer(row),[]).append(row)
   hist[field][ch['symbol']]={k:metrics(v) for k,v in grouped.items()}
 path=save('cycle09_frozen_selection',{'registeredUTC':utc(),'selectionUses':'training and validation only; final holdout outcomes not queried','choices':choices,'bestDevelopmentSymbol':choices[0]['symbol'],'holdoutEvaluated':False,'timeAndEntryDiagnostics':hist,'selectionBiasWarning':'280 registered model-symbol comparisons. Bootstrap is descriptive and not multiplicity-adjusted proof. Frozen final test is required.','researchGatePassed':False})
 finish('select',path,selectionPath=path,nextStage='stress')
def stress():
 st=read(R/'state.json')
 if st.get('stressPath'):print(json.dumps({'stage':'stress','alreadyCompleted':True}));return
 p=read(R/'plan.json');sel=read(st['selectionPath']);results=[]
 for ch in sel['choices']:
  d=load_data(ch['symbol'],p['bounds']['validation'][1]);scenarios=[]
  for title,spread,fees,delay in [('registered_base',1,7,0),('spread_x1.5_fee10',1.5,10,0),('spread_x2_fee14',2,14,0),('one_minute_late_entry_DIAGNOSTIC',1,7,1)]:
   ts,cs,sk=replay(d,ch['model'],*p['bounds']['validation'],spread_mult=spread,fee_per_lot=fees,delay_bars=delay);scenarios.append({'scenario':title,'metrics':metrics(ts,len(cs)),'skips':sk,'lateEntryAllowedLive':False})
  results.append({'symbol':ch['symbol'],'model':ch['model'],'scenarios':scenarios})
 path=save('cycle06_cost_latency_stress',{'kind':'SIMULATION_COST_SENSITIVITY','results':results,'holdoutEvaluated':False,'costsAreHistoricalActualFees':False})
 finish('stress',path,stressPath=path,nextStage='verify')
def verify():
 st=read(R/'state.json');p=read(R/'plan.json');groups=trade_rows();violations=[];count=0
 for rows in groups.values():
  for tr in rows:
   count+=1
   if tr['entryBarTime']<stamp(tr['informationThroughUTC']) or tr['plannedRR']<2-1e-6 or tr['priceRiskUSD']<=0 or tr['exitBarTime']<tr['entryBarTime']:violations.append({'ticket':'SIMULATED','entryUTC':tr['entryUTC'],'reason':'causal_or_RR_invariant'})
 prefix=[]
 for ch in read(st['selectionPath'])['choices']:
  d=load_data(ch['symbol'],p['bounds']['validation'][1]);full=signals(d,ch['model']);k=len(full)//2;small={key:(val[:k] if isinstance(val,np.ndarray) else val) for key,val in d.items()};same=np.array_equal(full[:k],signals(small,ch['model']));prefix.append({'symbol':ch['symbol'],'prefixBars':k,'futureRowsDoNotChangeEarlierSignals':bool(same)})
 if any(not x['futureRowsDoNotChangeEarlierSignals'] for x in prefix):violations.append({'reason':'signal_future_leakage'})
 checks={'kind':'ACTUAL_CODE_AND_DATA_CHECKS_NOT_TRADES','rowsChecked':count,'violations':violations,'prefixChecks':prefix,'holdoutOutcomeQueries':0,'oldRepeated100CyclesExcluded':True,'filesSHA256':{n:digest(R/n) for n in ['engine.py','request.json','plan.json']}}
 path=save('cycle08_causality_verification',checks);finish('verify',path,verificationPath=path,nextStage='ticks')
 if violations:raise RuntimeError('causality_verification_failed')
def report(final=False):
 st=read(R/'state.json');sel=read(st['selectionPath']);rows=sel['choices'];lines=['# پژوهش شبانهٔ بک‌تست — تفسیر ایجنت','',f'زمان گزارش: {utc()}','همه معاملات این گزارش «شبیه‌سازی» هستند و به ۷۰۰ معاملهٔ واقعی دمو اضافه نمی‌شوند.','',f"داده: {sum(v.get('bars',0) for v in manifest()['symbols'].values()):,} کندل واقعی M1؛ هفت نماد؛ ۴۰ تنظیم عددی ثابت و ۲۸۰ مقایسهٔ نماد/مدل.",'داده‌های از ۸ سپتامبر به بعد به‌دلیل استفادهٔ قبلی قرنطینه‌اند. آزمون نهایی قدیمی‌تر تا زمان مقرر باز نمی‌شود.','', '## رتبه‌بندی توسعه؛ نتیجهٔ نهایی نیست','|نماد|مدل|تعداد اعتبارسنجی|WR|Expectancy R|PF|DD R|وضعیت|','|---|---|---:|---:|---:|---:|---:|---|']
 for c in rows:
  m=c['validation'];lines.append(f"|{c['symbol']}|{c['model']['family']}|{m['n']}|{m['winRatePct'] or 0:.2f}%|{m['expectancyR'] or 0:.4f}|{m['profitFactorR'] or 0:.3f}|{m['maxClosedTradeDrawdownR']:.2f}|{c['status']}|")
 lines+=['','## محدودیت و ضعف‌های اجرایی','- گزارش قدیمی ۱۰۰ چرخه از تکرار یک نتیجه ساخته شده بود؛ شاهد ۱۰۰ آزمون مستقل نیست.','- چهار fill دیرهنگام در ۲۲ خروج واقعی دیده شده‌اند؛ شبیه‌سازی دقیق زمان پذیرش سفارش با M1 ممکن نیست.','- دامنه حرکت پنج‌ثانیه‌ای کمتر از spread در نمونهٔ واقعی ۸ زیان از ۸ معامله داشت؛ این نمونه کوچک است و حذف قانون نیازمند اعتبارسنجی است.','- ورود بر اساس کندل بسته‌شده، هزینه بر اساس اطلاعات قبلی و SL ساختاری است؛ برخورد همزمان SL/TP در M1 به زیان فرض می‌شود.','- قیمت تاریخی bid/ask داخل دقیقه، کارمزد و swap تاریخی کامل نیست؛ هزینه‌ها سناریوی صریح‌اند و آزمون تیک جدا لازم است.','- این نتایج مجوز تضمین سوددهی یا ارتقای خودکار نسخهٔ زنده نیستند.','', '## شواهد',f"- پروتکل: {R/'plan.json'}",f"- معاملات شبیه‌سازی کامل: {read(st['gridPath'])['tradesPath']}",f"- انتخاب منجمد: {st['selectionPath']}",f"- بررسی علیت: {st.get('verificationPath','pending')}",'- [مرجع رسمی تاریخچهٔ MT5](https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesrange_py)','- [مقالهٔ اصلی احتمال بیش‌برازش بک‌تست](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf)']
 if final:
  f=read(st['holdoutPath']);lines+=['','## آزمون نهایی دیده‌نشده', '|نماد|N|WR|Expectancy R|PF|DD R|قبول|','|---|---:|---:|---:|---:|---:|---|']
  for r in f['results']:
   m=r['metrics'];lines.append(f"|{r['symbol']}|{m['n']}|{m['winRatePct'] or 0:.2f}%|{m['expectancyR'] or 0:.4f}|{m['profitFactorR'] or 0:.3f}|{m['maxClosedTradeDrawdownR']:.2f}|{r['holdoutScreenPassed']}|")
  lines+=['',f"نتیجهٔ انتخاب از قبل منجمدشده: {f['decision']}",'نرخ برد بالای ۵۰٪ با نمونه کم یا انتخاب بهترین ردیف آزمون نهایی اثبات نمی‌شود.','نسخهٔ زنده و معاملات قبلی در اثر این بک‌تست تغییر نکردند.']
 name=('FINAL' if final else 'PROGRESS')+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.md';path=R/name;path.write_text('\n'.join(lines)+'\n',encoding='utf-8');state_update(latestReport=str(path));print(json.dumps({'stage':'report','reportPath':str(path),'final':final}),flush=True);return str(path)
def final():
 st=read(R/'state.json');p=read(R/'plan.json')
 if st.get('holdoutPath'):report(True);return
 if datetime.now(timezone.utc).timestamp()<stamp(p['holdoutReleaseUTC']):print(json.dumps({'stage':'holdout','status':'SEALED','releaseUTC':p['holdoutReleaseUTC']}));return
 if not st.get('verificationPath') or read(st['verificationPath'])['violations']:raise RuntimeError('verification_required_before_holdout')
 sel=read(st['selectionPath']);results=[];tradepath=R/('holdout_trades_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.jsonl.gz')
 with gzip.open(tradepath,'xb') as f:
  for choice in sel['choices']:
   d=load_data(choice['symbol'],p['bounds']['holdout'][1]);ts,cs,sk=replay(d,choice['model'],*p['bounds']['holdout']);m=metrics(ts,len(cs));ci=bootstrap(ts);passing=m['n']>=50 and (m['expectancyR'] or -1)>0 and (m['profitFactorR'] or 0)>=1.1 and ci['lower95'] is not None and ci['lower95']>0
   results.append({'symbol':choice['symbol'],'frozenModel':choice['model'],'metrics':m,'dayBootstrap':ci,'holdoutScreenPassed':passing,'provenWRAbove50':m['wilson95Pct'][0] is not None and m['wilson95Pct'][0]>50,'tickExecutionValidation':False,'readyForUnattendedLiveTrading':False,'skips':sk})
   for row in ts:f.write((json.dumps({**row,'partition':'sealed_holdout'},separators=(',',':'))+'\n').encode())
   for row in cs:f.write((json.dumps({**row,'partition':'sealed_holdout','excludedFromWR':True},separators=(',',':'))+'\n').encode())
 chosen=next(r for r in results if r['symbol']==sel['bestDevelopmentSymbol']);decision='PAPER_RESEARCH_CANDIDATE_WITH_EXECUTION_LIMITATIONS' if chosen['holdoutScreenPassed'] else 'NO_CONFIRMED_STRATEGY_SELECTED; DO_NOT_PROMOTE'
 path=save('cycle10_single_untouched_holdout',{'openedUTC':utc(),'planHash':digest(R/'plan.json'),'selectionHash':digest(st['selectionPath']),'results':results,'preselectedBestSymbol':sel['bestDevelopmentSymbol'],'decision':decision,'tradePath':str(tradepath),'tradeSHA256':digest(tradepath),'reselectionAfterTestAllowed':False,'liveStrategyMutations':0,'actualDemoTradeCountUnchanged':True})
 finish('holdout',path,holdoutPath=path,holdoutOpened=True,status='COMPLETE',nextStage='complete');report(True)
def main():
 action=sys.argv[1]
 {'plan':plan,'grid':grid,'walkforward':walkforward,'select':choose,'stress':stress,'verify':verify,'report':report,'final':final}[action]()
if __name__=='__main__':main()
