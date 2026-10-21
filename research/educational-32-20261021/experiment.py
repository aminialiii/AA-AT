"""Bounded offline research; no MT5, MCP, network, scheduling or production writes.

Only whitelisted function definitions from hash-frozen original engines execute.
Original baselines are copied intact; new signal filters are independently defined.
"""
import ast,copy,csv,gzip,hashlib,json,math,os,sys,time,types,platform
from pathlib import Path
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'.skill-tools'))
import numpy as np
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'research_outputs'; WORK=Path(__file__).resolve().parent
FAMILIES={'S01':'RANGE_REJECTION','S02':'TREND_PULLBACK','S03':'BREAK_RETEST','S04':'M1_MOMENTUM_PROXY','S05':'SP2L_AGENT_INTERPRETATION'}
ALLOWED={'read','iso','stamp','digest','manifest','load_data','signals','profit','rr_tp','replay','metrics','session'}
SEED=20261021
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def iso(t):return datetime.fromtimestamp(float(t),timezone.utc).isoformat()
def stamp(s):return datetime.fromisoformat(s.replace('Z','+00:00')).timestamp()
def exclusive(p,data):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2,allow_nan=False)
def log(kind,**data):
 with (OUT/'audit.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps({'utc':datetime.now(timezone.utc).isoformat(),'event':kind,**data},ensure_ascii=False,allow_nan=False)+'\n')
def writecsv(path,rows):
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with Path(path).open('x',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=keys);w.writeheader()
  for row in rows:w.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,(list,dict)) else v for k,v in row.items()})
def verify_originals():
 for x in read(OUT/'original_baseline_manifest.json')['files']:
  if digest(ROOT/x['path'])!=x['sha256']:raise RuntimeError('ORIGINAL_CHANGED:'+x['path'])
def module(tf):
 path=OUT/'frozen'/f'{tf}_engine.py';source=path.read_text(encoding='utf-8-sig');tree=ast.parse(source)
 defs=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ALLOWED]
 assert {n.name for n in defs}==ALLOWED
 m=types.ModuleType('frozen_'+tf);m.__dict__.update({'np':np,'math':math,'json':json,'Path':Path,'hashlib':hashlib,'datetime':datetime,'timezone':timezone,'R':ROOT/('research/overnight-20261010'+('/m5' if tf=='M5' else ''))})
 exec(compile(ast.Module(body=defs,type_ignores=[]),str(path),'exec'),m.__dict__)
 return m
def plans():return read(OUT/'registration_baseline.json')
def register_baseline():
 verify_originals();dest=OUT/'frozen';dest.mkdir(exist_ok=True)
 manifest_path=ROOT/'research/overnight-20261010/history_pointer.json';pointer=read(manifest_path);manifest=read(pointer['path'])
 assert digest(pointer['path'])==pointer['sha256']
 datasets=[];cases=[];engine_hashes={}
 for symbol,x in manifest['symbols'].items():
  assert x['status']=='AVAILABLE' and digest(x['path'])==x['sha256']
  a=np.load(x['path'],allow_pickle=False)['rates'];assert np.all(np.diff(a['time'])>0)
  assert np.all(np.isfinite(np.column_stack([a[k] for k in ['open','high','low','close']])))
  assert np.all((a['low']>0)&(a['low']<=a['open'])&(a['low']<=a['close'])&(a['high']>=a['open'])&(a['high']>=a['close'])&(a['spread']>=0))
  datasets.append({'symbol':symbol,'path':x['path'],'sha256':x['sha256'],'bars':len(a),'firstUTC':x['firstUTC'],'lastUTC':x['lastUTC'],'gaps':int(np.sum(np.diff(a['time'])!=60))})
 for tf in ['M1','M5']:
  folder=ROOT/('research/overnight-20261010'+('/m5' if tf=='M5' else ''));src=folder/'engine.py';snapshot=dest/f'{tf}_engine.py'
  with snapshot.open('xb') as f:f.write(src.read_bytes())
  engine_hashes[tf]=digest(src);p=read(folder/'plan.json');s=read(folder/'state.json')
  for sid,family in FAMILIES.items():
   models=[m for m in p['models'] if m['family']==family]
   if not models:continue
   selected=models[0] # prespecified first registered q=.2/minStop=.5/ALL; no outcome selection
   for symbol in manifest['symbols']:
    key=f'{sid}_{tf}_{symbol}';cases.append({'case_id':key,'strategy_id':sid,'timeframe':tf,'symbol':symbol,'model':selected,'bounds':p['bounds'],'planPath':str(folder/'plan.json'),'planSHA256':digest(folder/'plan.json'),'savedGridPath':s['gridPath'],'savedGridSHA256':digest(s['gridPath'])})
 registration={'registeredUTC':datetime.now(timezone.utc).isoformat(),'phase':'BASELINE_BEFORE_CANDIDATES','caseCount':len(cases),'cases':cases,'datasets':datasets,'engineSHA256':engine_hashes,'manifestPath':pointer['path'],'manifestSHA256':pointer['sha256'],'historicalBrokerOffsetMinutes':manifest['brokerOffsetMinutes'],'historicalOffsetIndependentlyVerified':False,'codeCommit':None,'startingCapitalDiagnosticUSD':10000,'capitalModel':'fixed broker-minimum volume per symbol; cash curve diagnostic only; historical margin feasibility unknown','oldSearchComparisons':448,'holdoutStatus':'ALREADY_EXPOSED_HISTORICAL_DATA_NO_FRESH_UNTOUCHED_TEST','runtime':{'python':sys.version,'numpy':np.__version__,'platform':platform.platform()},'safety':{'offline':True,'importsMT5':False,'productionWrites':False},'definitionAllowlist':sorted(ALLOWED)}
 exclusive(OUT/'registration_baseline.json',registration);log('baseline_registered',cases=len(cases),datasets=len(datasets))
def more_metrics(rows,censored,seconds,bootstrap=True):
 ordered=sorted(rows,key=lambda r:(r['exitBarTime'],r['entryBarTime']));x=np.array([r['netR'] for r in ordered]);pnl=np.array([r['netUSD'] for r in ordered]);eq=np.r_[10000,10000+np.cumsum(pnl)];peak=np.maximum.accumulate(eq);dd=(peak-eq)/peak*100
 grouped={}
 for r in ordered:grouped.setdefault(r['entryBarTime']//86400,[]).append(r['netR'])
 ci=None
 if bootstrap and len(grouped)>=5:
  sums=np.array([sum(v) for v in grouped.values()]);counts=np.array([len(v) for v in grouped.values()]);rng=np.random.default_rng(SEED);idx=rng.integers(0,len(sums),(2000,len(sums)));draw=sums[idx].sum(1)/counts[idx].sum(1);ci=[float(np.percentile(draw,2.5)),float(np.percentile(draw,97.5))]
 m=module('M1').metrics(ordered,len(censored))
 regimes={}
 for name,keep in [('UP',lambda r:r['side']=='buy'),('DOWN',lambda r:r['side']=='sell'),('TREND',lambda r:r['trendStrength']>.35),('WEAK',lambda r:r['trendStrength']<=.35)]:
  a=[r['netR'] for r in ordered if keep(r)];regimes[name]={'n':len(a),'expectancyR':sum(a)/len(a) if a else None}
 durations=[];begin=None;longest=0
 for i,r in enumerate(ordered,1):
  if eq[i]<peak[i]:
   if begin is None:begin=r['exitBarTime']
   longest=max(longest,r['exitBarTime']+seconds-begin)
  else:begin=None
 return {**m,'trade_count':len(rows),'net_expectancy_R':m['expectancyR'],'net_profit':sum(pnl).item() if len(pnl) else 0.0,'net_profit_R':float(np.sum(x)),'max_drawdown_pct':float(np.max(dd)),'drawdown_basis':'closed fixed-minimum-volume cash on proposed $10000, not mark-to-market or margin-validated','max_drawdown_duration_hours_closed':longest/3600,'profit_factor':m['profitFactorR'],'win_rate':m['winRatePct'],'independent_entry_days':len(grouped),'confidence_interval':ci,'ci_method':'2000 day-block percentile bootstrap, seed20261021, descriptive/unadjusted','regime_stability':regimes,'turnover_lots':sum(r['volume']*2 for r in rows),'median_holding_minutes':float(np.median([r['holdingMinutesUpperBound'] for r in rows])) if rows else None,'holding_total_seconds':sum(r['holdingMinutesUpperBound']*60 for r in rows),'censored_count':len(censored),'censored_price_risk_USD':sum(r['priceRiskUSD'] for r in censored),'historical_actual_costs_known':False,'both_hit_count':sum(r['bothSLTPInSameBar'] for r in rows)}
def output_record(case,cid,part,metrics,tradepath,reason=None):
 bounds=case['bounds'];return {'strategy_id':case['strategy_id'],'case_id':case['case_id'],'candidate_id':cid,'parent_candidate_id':None if cid=='BASELINE' else 'BASELINE','code_commit':None,'data_hash':next(x['sha256'] for x in plans()['datasets'] if x['symbol']==case['symbol']),'symbol':case['symbol'],'timeframe':case['timeframe'],'evidence_class':'RESEARCH_HYPOTHESIS','run_status':'RUN' if reason is None else 'NOT_RUN','reason_if_not_run':reason,'partition':part,'train_period':list(map(iso,bounds['train'])),'validation_period':list(map(iso,bounds['validation'])),'test_period':list(map(iso,bounds['holdout'])),'cost_model':{'spread':'1.25*max prior5 completed bars (M5 means5M5)','entrySlippageTicks':.5,'stopSlippageTicks':2,'feePerLot':7,'swapStressPerLotNight':10,'actualCostsKnown':False},'holdout_touched_for_tuning':True,'holdout_detail':'Historical test previously disclosed; no untouched confirmation. Current candidate rules frozen before their outcome evaluation.','test_artifact_path':str(tradepath),**metrics}
def execute_cases(cid_list,stage):
 registration=plans();results=[];proof=[];began=time.monotonic();folders=OUT/'runs';folders.mkdir(exist_ok=True)
 for tf in ['M1','M5']:
  m=module(tf);seconds=60 if tf=='M1' else 300;orig_signals=m.signals;grid=None
  data={}
  for symbol in [x['symbol'] for x in registration['datasets']]:
   examples=[c for c in registration['cases'] if c['timeframe']==tf and c['symbol']==symbol];end=max(c['bounds']['holdout'][1] for c in examples);data[symbol]=m.load_data(symbol,end)
  for case in [c for c in registration['cases'] if c['timeframe']==tf]:
   d=data[case['symbol']];model=case['model'];base_signal=orig_signals(d,model)
   if stage=='baseline':
    if grid is None:grid=read(case['savedGridPath'])
    saved=next(x for x in grid['rows'] if x['symbol']==case['symbol'] and x['model']['id']==model['id'])
   for cid in cid_list:
    signal=base_signal.copy() if cid=='BASELINE' else filtered(d,base_signal,cid,seconds)
    m.signals=lambda _d,_p,s=signal:s
    for part in ['train','validation','holdout']:
     lo,hi=case['bounds'][part];rows,censored,skips=m.replay(d,model,lo,hi)
     path=folders/(case['case_id']+'_'+cid+'_'+part+'.jsonl.gz')
     with gzip.open(path,'xt',encoding='utf-8') as f:
      for row in rows:f.write(json.dumps({**row,'candidate_id':cid,'timeframe':tf,'partition':part},separators=(',',':'))+'\n')
      for row in censored:f.write(json.dumps({**row,'candidate_id':cid,'timeframe':tf,'partition':part,'censored':True},separators=(',',':'))+'\n')
     mm=more_metrics(rows,censored,seconds);mm['skip_counts']=skips;mm['exposure_fraction']=mm['holding_total_seconds']/(hi-lo);mm['trade_archive_sha256']=digest(path)
     results.append(output_record(case,cid,part,mm,path))
     if stage=='baseline' and part in ['train','validation']:
      expected=saved['partitions'][part];actual=m.metrics(rows,len(censored));keys=['n','expectancyR','profitFactorR','netR','netUSDAtBrokerMinVolume','intrabarAmbiguous','censoredNotCounted']
      matches={k:(actual[k]==expected[k] if actual[k] is None or expected[k] is None else math.isclose(actual[k],expected[k],rel_tol=1e-9,abs_tol=1e-8)) for k in keys}
      proof.append({'case_id':case['case_id'],'partition':part,'saved_grid_sha256':case['savedGridSHA256'],'matched':all(matches.values()),'checks':matches})
    log('case_completed',stage=stage,case=case['case_id'],candidate=cid,elapsedSeconds=round(time.monotonic()-began,3))
  m.signals=orig_signals
 writecsv(OUT/(stage+'_results.csv'),results);exclusive(OUT/(stage+'_results.json'),results)
 if stage=='baseline':
  exclusive(OUT/'baseline_reproduction.json',{'comparisons':proof,'allMatched':all(x['matched'] for x in proof),'count':len(proof)})
  if not all(x['matched'] for x in proof):raise RuntimeError('BASELINE_MISMATCH_NO_CANDIDATES_ALLOWED')
 verify_originals();log('stage_completed',stage=stage,rows=len(results),elapsedSeconds=round(time.monotonic()-began,3))
def prior_levels(d):
 """Prior completed UTC trading-day/week only, never current-day extrema."""
 t=d['t'];day=(t//86400).astype(np.int64);week=((day+3)//7).astype(np.int64);values=[]
 for grouping in [day,week]:
  hi=np.full(len(t),np.nan);lo=hi.copy();mid=hi.copy();prev=None;start=0
  for i in range(1,len(t)+1):
   if i==len(t) or grouping[i]!=grouping[start]:
    if prev is not None:hi[start:i],lo[start:i],mid[start:i]=prev[0],prev[1],(prev[0]+prev[1])/2
    count=i-start
    # At least100min of coverage per completed day; week must contain3 dates.
    if count>=max(20,100//int(d.get('seconds',60))) and (grouping is day or len(set(day[start:i]))>=3):prev=(float(np.max(d['h'][start:i])),float(np.min(d['l'][start:i])))
    else:prev=None
    start=i
  values.extend([hi,lo,mid])
 return np.stack(values,axis=1)
def time_mask(t,seconds,variant='TIME_FILTER'):
 calendar=read(OUT/'timezone_rules_2026.json');rules=np.array(calendar['rows'],dtype=np.int64);closed=t+seconds;indices=np.searchsorted(rules[:,0],closed,side='right')-1
 if np.any(indices<0) or np.any(closed>=rules[-1,0]+3600):raise RuntimeError('timezone_calendar_outside_2026')
 lm=((closed+rules[indices,1]*60)%86400)//60;nm=((closed+rules[indices,2]*60)%86400)//60
 # Explicit research translation of source summer windows, not broker-fixed GMT+3.
 return ((lm>=480)&(lm<660))|((nm>=510)&(nm<660))
def filtered(d,sig,cid,seconds):
 out=sig.copy();a=d['atr'];span=d['h']-d['l'];safe=np.maximum(span,d['tick']);keep=np.ones(len(sig),bool)
 if cid=='TIME_FILTER':keep=time_mask(d['t'],seconds)
 elif cid=='LEVEL_FILTER':
  levels=prior_levels(d);long=np.any((d['l'][:,None]<=levels+.25*a[:,None])&(d['c'][:,None]>=levels),axis=1);short=np.any((d['h'][:,None]>=levels-.25*a[:,None])&(d['c'][:,None]<=levels),axis=1);keep=np.where(sig>0,long,short)
 elif cid=='PRICE_ACTION_CONFIRMATION':keep=np.where(sig>0,(d['c']-d['l'])/safe>=.75,(d['h']-d['c'])/safe>=.75)
 elif cid=='RISK_EXECUTION_REFINEMENT':keep=(d['spread']/a<=.15)&(span<=2.5*a)
 elif cid=='PA_NEIGHBOR_070':keep=np.where(sig>0,(d['c']-d['l'])/safe>=.70,(d['h']-d['c'])/safe>=.70)
 elif cid=='PA_NEIGHBOR_080':keep=np.where(sig>0,(d['c']-d['l'])/safe>=.80,(d['h']-d['c'])/safe>=.80)
 else:raise ValueError(cid)
 out[~keep]=0;return out
def register_candidates():
 assert read(OUT/'baseline_reproduction.json')['allMatched'];verify_originals()
 variants=[{'candidate_id':'TIME_FILTER','rule':'signal close within London08:00-11:00 OR NewYork08:30-11:00, timezone-aware Windows2026rules','source':'implementations/implementation_guide.md:42','evidence_class':'RESEARCH_HYPOTHESIS','assumptions':'Research translation of reconstructed/companion summer gold windows to FX; not exact source calibration'},
 {'candidate_id':'LEVEL_FILTER','rule':'long low <= any prior completed UTC-day/week H/L/Mid +.25ATR and close >= that level; short inverse; exclude incomplete prior groups','source':'implementations/implementation_guide.md:14','evidence_class':'RESEARCH_HYPOTHESIS','assumptions':'UTC research day/week, not source broker-session day; proximity tolerance.25ATR is agent hypothesis'},
 {'candidate_id':'PRICE_ACTION_CONFIRMATION','rule':'long close upper25% of completed candle, short lower25%; no extra confirmation delay','source':'video_analysis/video_02_analysis.md','evidence_class':'RESEARCH_HYPOTHESIS','assumptions':'Numeric.75 threshold added to existing proxies; exact teacher trigger unchanged/unspecified'},
 {'candidate_id':'RISK_EXECUTION_REFINEMENT','rule':'modeled spread/ATR<=.15 AND signal range<=2.5ATR; retain sizing/SL/TP','source':'implementations/implementation_guide.md:90','evidence_class':'RESEARCH_HYPOTHESIS','assumptions':'Thresholds are research hypotheses, no10%cap/180sbroker floor/no scale-in adopted'}]
 exclusive(OUT/'registration_candidates.json',{'registeredUTC':datetime.now(timezone.utc).isoformat(),'baselineVerifiedBeforeRegistration':True,'baselineResultsSHA256':digest(OUT/'baseline_results.json'),'engineAdapterSHA256':digest(__file__),'timezoneSHA256':digest(OUT/'timezone_rules_2026.json'),'variants':variants,'caseCount':len(plans()['cases']),'primaryComparisons':4*len(plans()['cases']),'selectionUses':'validation only; historical test never used to select current candidate','COMBINED':'NOT_RUN unless independent ablations show prespecified justification; no forced combined candidate','sensitivity':'PA.70/.80 only for nominated validation candidates, report not tune','freshUntouchedOOS':'NOT_RUN: no unexposed archive available; future data collection not authorized','multipleTesting':'Bonferroni day-block improvement tests across all224primary comparisons, alpha.05; no claim from unadjusted CI','startingCapitalDiagnosticUSD':10000})
 log('candidates_registered',primaryComparisons=4*len(plans()['cases']))
def main():
 action=sys.argv[1]
 if action=='register_baseline':register_baseline()
 elif action=='baseline':execute_cases(['BASELINE'],'baseline')
 elif action=='register_candidates':register_candidates()
 elif action=='candidates':
  assert digest(__file__)==read(OUT/'registration_candidates.json')['engineAdapterSHA256'];execute_cases([x['candidate_id'] for x in read(OUT/'registration_candidates.json')['variants']],'candidate')
 else:raise ValueError(action)
if __name__=='__main__':main()
