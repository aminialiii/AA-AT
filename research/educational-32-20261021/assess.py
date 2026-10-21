"""Validation-only selection, paired uncertainty and bounded robustness diagnostics."""
import json,math,gzip,copy
from collections import defaultdict
import experiment as e
import numpy as np
O=e.OUT
def trades(record):
 path=record['test_artifact_path'];assert e.digest(path)==record['trade_archive_sha256']
 with gzip.open(path,'rt',encoding='utf-8') as f:return [r for line in f if not (r:=json.loads(line)).get('censored')]
def paired_improvement(a,b,reps=10000):
 """Descriptive paired day-block bootstrap; historical selection bias remains."""
 groups={}
 for j,rows in enumerate([a,b]):
  for r in rows:
   day=r['entryBarTime']//86400;v=groups.setdefault(day,[0.,0,0.,0]);v[j*2]+=r['netR'];v[j*2+1]+=1
 if len(groups)<5 or not a or not b:return {'days':len(groups),'deltaExpectancyR':None,'CI95':None,'p_one_sided_centered_bootstrap':None,'p_bonferroni_224':None}
 z=np.array(list(groups.values()));observed=z[:,2].sum()/z[:,3].sum()-z[:,0].sum()/z[:,1].sum();rng=np.random.default_rng(e.SEED);idx=rng.integers(0,len(z),(reps,len(z)));sample=z[idx].sum(1);ok=(sample[:,1]>0)&(sample[:,3]>0);delta=sample[ok,2]/sample[ok,3]-sample[ok,0]/sample[ok,1];centered=delta-observed
 p=(1+np.sum(centered>=observed))/(1+len(delta)) if observed>0 else 1.
 return {'days':len(groups),'deltaExpectancyR':float(observed),'CI95':list(map(float,np.percentile(delta,[2.5,97.5]))),'p_one_sided_centered_bootstrap':float(p),'p_bonferroni_224':float(min(1,p*224)),'method':'10000 paired day blocks, centered bootstrap approximation, seed20261021; exposed historical data, not confirmatory randomization'}
def select():
 base=e.read(O/'baseline_results.json');cand=e.read(O/'candidate_results.json');bm={(r['case_id'],r['partition']):r for r in base};comparisons=[]
 # This selector intentionally receives validation rows only. Existing historical
 # holdout outcomes are not used to choose the candidates or their order.
 for c in [r for r in cand if r['partition']=='validation']:
  b=bm[c['case_id'],'validation'];paired=paired_improvement(trades(b),trades(c));qualified=c['trade_count']>=50 and c['independent_entry_days']>=5
  comparisons.append({'strategy_id':c['strategy_id'],'case_id':c['case_id'],'symbol':c['symbol'],'timeframe':c['timeframe'],'candidate_id':c['candidate_id'],'validationBaseline':{k:b[k] for k in ['trade_count','net_expectancy_R','net_profit','profit_factor','confidence_interval','independent_entry_days']},'validationCandidate':{k:c[k] for k in ['trade_count','net_expectancy_R','net_profit','profit_factor','confidence_interval','independent_entry_days']},'pairedValidation':paired,'sampleGate':qualified,'positiveNetValidation':(c['net_expectancy_R'] or -999)>0,'adjustedImprovementSupported':paired['p_bonferroni_224'] is not None and paired['p_bonferroni_224']<.05,'evidence':'RETROSPECTIVE_EXPLORATORY'})
 shortlist=[]
 for sid in e.FAMILIES:
  rows=[r for r in comparisons if r['strategy_id']==sid]
  rows.sort(key=lambda r:(r['sampleGate'],r['positiveNetValidation'],r['validationCandidate']['net_expectancy_R'] if r['validationCandidate']['net_expectancy_R'] is not None else -999,r['pairedValidation']['deltaExpectancyR'] if r['pairedValidation']['deltaExpectancyR'] is not None else -999),reverse=True)
  ch=rows[0];shortlist.append({**ch,'provisionalOnly':True,'approvalPurpose':'Choose further offline validation/specification work; no deployment or trading approval inferred.'})
 shortlist.sort(key=lambda r:(r['sampleGate'],r['positiveNetValidation'],r['validationCandidate']['net_expectancy_R'] if r['validationCandidate']['net_expectancy_R'] is not None else -999),reverse=True)
 e.exclusive(O/'selection_frozen.json',{'registeredUTC':e.datetime.now(e.timezone.utc).isoformat(),'selectionInput':'validation partitions only; all historical periods previously exposed','selectionRule':'One candidate per S01-S05, prioritize n>=50 and entry days>=5, positive expectancy then candidate expectancy and paired uplift; order across families same validation criteria','currentTestOutcomesUsedInSelection':False,'allPrimaryComparisons':224,'historicalPriorComparisons':448,'selected':shortlist,'comparisonCount':len(comparisons)})
 e.exclusive(O/'paired_comparisons.json',comparisons);e.writecsv(O/'paired_comparisons.csv',comparisons)
 e.log('selection_frozen',comparisons=len(comparisons),selected=[x['case_id']+'_'+x['candidate_id'] for x in shortlist])
def robustness():
 selected=e.read(O/'selection_frozen.json')['selected'];cases={c['case_id']:c for c in e.plans()['cases']};results=[];data_cache={}
 for ch in selected:
  case=cases[ch['case_id']];tf=case['timeframe'];seconds=60 if tf=='M1' else 300;m=e.module(tf);key=(tf,case['symbol']);end=case['bounds']['holdout'][1]
  if key not in data_cache:data_cache[key]=m.load_data(case['symbol'],end)
  d=data_cache[key];raw=m.signals(d,case['model']);signals={cid:(raw.copy() if cid=='BASELINE' else e.filtered(d,raw,cid,seconds)) for cid in ['BASELINE',ch['candidate_id']]}
  # Equal-length chronological folds within development. Fixed candidate selection
  # was not prequential: these are fixed-rule slices, not a new independent test.
  start,stop=case['bounds']['train'][0],case['bounds']['validation'][1];days=np.unique(d['t'][(d['t']>=start)&(d['t']<stop)]//86400);cuts=[int(days[int(len(days)*f)])*86400 for f in [.4,.6,.8]]+[stop]
  for cid,sig in signals.items():
   m.signals=lambda d,p,s=sig:s
   scenarios=[('registered_base',1,7,0),('spread1.5_fee14',1.5,14,0),('spread2_fee14',2,14,0),('one_bar_delay',1,7,1)]
   for title,spread,fees,delay in scenarios:
    lo,hi=case['bounds']['holdout'];rows,cens,skips=m.replay(d,case['model'],lo,hi,spread_mult=spread,fee_per_lot=fees,delay_bars=delay)
    results.append({'case_id':case['case_id'],'candidate_id':cid,'diagnostic':'cost_stress','scenario':title,'partition':'historical_test_exposed','delaySeconds':delay*seconds,'metrics':e.more_metrics(rows,cens,seconds),'skips':skips})
   for n in range(3):
    rows,cens,skips=m.replay(d,case['model'],cuts[n],cuts[n+1]);results.append({'case_id':case['case_id'],'candidate_id':cid,'diagnostic':'chronological_fixed_rule_fold','fold':n+1,'period':[e.iso(cuts[n]),e.iso(cuts[n+1])],'selectionWarning':'Fixed rule chosen after development; descriptive stability, not unbiased prequential model selection','metrics':e.more_metrics(rows,cens,seconds)})
  # Finite one-at-a-time neighborhoods; no new choice/parameter update is made.
  for cid in ['PA_NEIGHBOR_070','PA_NEIGHBOR_080'] if ch['candidate_id']=='PRICE_ACTION_CONFIRMATION' else []:
   sig=e.filtered(d,raw,cid,seconds);m.signals=lambda d,p,s=sig:s;rows,cens,skips=m.replay(d,case['model'],*case['bounds']['validation']);results.append({'case_id':case['case_id'],'candidate_id':cid,'diagnostic':'parameter_neighborhood','partition':'validation','usedForReselection':False,'metrics':e.more_metrics(rows,cens,seconds)})
  # Extra stop neighborhoods are post-selection descriptive diagnostics, not
  # preregistered primary candidates or evidence for changing the frozen setting.
  for stop_atr in [.4,.6]:
   p={**case['model'],'minStopATR':stop_atr};sig=signals[ch['candidate_id']];m.signals=lambda d,p,s=sig:s;rows,cens,skips=m.replay(d,p,*case['bounds']['validation']);results.append({'case_id':case['case_id'],'candidate_id':ch['candidate_id'],'diagnostic':'stop_parameter_neighborhood','minStopATR':stop_atr,'partition':'validation','usedForReselection':False,'metrics':e.more_metrics(rows,cens,seconds)})
 e.exclusive(O/'robustness_results.json',results);e.writecsv(O/'robustness_results.csv',results);e.log('robustness_completed',runs=len(results))
def walkforward():
 """Expanding development selection among BASELINE+four frozen filters only.

 Historical selection bias remains; no claim of untouched test.
 """
 mbase=e.read(O/'baseline_results.json');mcand=e.read(O/'candidate_results.json');bycase=defaultdict(dict)
 for r in mbase+mcand:
  if r['partition'] in ['train','validation']:
   bycase[r['case_id']].setdefault(r['candidate_id'],[]).extend(trades(r))
 choices=e.read(O/'selection_frozen.json')['selected'];cases={x['case_id']:x for x in e.plans()['cases']};folds=[]
 for choice in choices:
  case=cases[choice['case_id']];tf=case['timeframe'];sec=60 if tf=='M1' else 300;m=e.module(tf);d=m.load_data(case['symbol'],case['bounds']['validation'][1]);raw=m.signals(d,case['model']);dates=np.unique(d['t'][(d['t']>=case['bounds']['train'][0])&(d['t']<case['bounds']['validation'][1])]//86400);cuts=[int(dates[int(len(dates)*f)])*86400 for f in [.4,.6,.8]]+[case['bounds']['validation'][1]]
  for k in range(3):
   candidates=[]
   for cid,rows in bycase[case['case_id']].items():
    eligible=[r for r in rows if r['exitBarTime']+sec<=cuts[k]];n=len(eligible);score=sum(r['netR'] for r in eligible)/n if n>=50 else -999;candidates.append((score,cid,n))
   candidates.sort(key=lambda x:(x[0],x[1]=='BASELINE'),reverse=True);score,cid,n=candidates[0];sig=raw.copy() if cid=='BASELINE' else e.filtered(d,raw,cid,sec);m.signals=lambda d,p,s=sig:s;rows,cens,skips=m.replay(d,case['model'],cuts[k],cuts[k+1]);folds.append({'case_id':case['case_id'],'fold':k+1,'trainEndsExclusiveUTC':e.iso(cuts[k]),'evaluationPeriod':[e.iso(cuts[k]),e.iso(cuts[k+1])],'candidateSelectedUsingPriorClosedTradesOnly':cid,'trainCount':n,'trainExpectancyR':score if score!=-999 else None,'embargo':'Open trades at boundary excluded; fresh flat replay; no position crosses fold','metrics':e.more_metrics(rows,cens,sec),'limitation':'Case nominated on full validation; procedure retrospective and case-selection biased; no new untouched evidence'})
 e.exclusive(O/'walkforward_results.json',folds);e.writecsv(O/'walkforward_results.csv',folds);e.log('walkforward_completed',folds=len(folds))
def aggregate_risk():
 selected=e.read(O/'selection_frozen.json')['selected'];cand=e.read(O/'candidate_results.json');daily={};events=[]
 for ch in selected:
  rec=next(r for r in cand if r['case_id']==ch['case_id'] and r['candidate_id']==ch['candidate_id'] and r['partition']=='holdout');rows=trades(rec);key=ch['case_id']+'_'+ch['candidate_id'];daily[key]=defaultdict(float)
  for r in rows:
   daily[key][r['entryBarTime']//86400]+=r['netUSD'];events.extend([(r['entryBarTime'],1,r['priceRiskUSD']),(r['exitBarTime']+(60 if ch['timeframe']=='M1' else 300),-1,-r['priceRiskUSD'])])
 days=sorted({d for vals in daily.values() for d in vals});matrix=np.array([[vals.get(day,0) for day in days] for vals in daily.values()]);corr=np.corrcoef(matrix) if len(days)>1 else None
 count=0;risk=0;maximum=0;maxcount=0
 for t,dc,dr in sorted(events,key=lambda x:(x[0],x[1])):count+=dc;risk+=dr;maximum=max(maximum,risk);maxcount=max(maxcount,count)
 def clean(x):return [[float(v) if np.isfinite(v) else None for v in row] for row in x] if x is not None else None
 e.exclusive(O/'aggregate_risk_diagnostic.json',{'candidateKeys':list(daily),'entryDates':len(days),'dailyNetUSDpearson':clean(corr),'maxConcurrentPositionsAssumingIndependentSleeves':maxcount,'maximumAggregateInitialPriceRiskUSD':maximum,'capitalDenominator':None,'portfolioRecommendation':'NONE. Several candidates can share symbol; independent-sleeve overlap may violate production one-position-per-symbol; no historical margin/mark-to-market ledger.','costRisk':'Initial stops do not bound gap/slippage risk; no minimum hold rule adopted.'})
if __name__=='__main__':
 import sys
 {'select':select,'robustness':robustness,'walkforward':walkforward,'aggregate_risk':aggregate_risk}[sys.argv[1]]()
