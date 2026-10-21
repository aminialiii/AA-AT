"""Retrospective fixed-minimum-volume policy reanalysis; no terminal orders."""
import json,copy
from pathlib import Path
from datetime import datetime,timezone
R=Path('E:/GPT/Inves/research/poursamadi-backtest')
src=R/'backtest_result_20261008T153525891254Z.json'
old=json.loads(src.read_text(encoding='utf-8'))
initial=100.55;eq=peak=initial;dd=0;trades=[];skip=[];busy=0
for row in sorted(old['rows'],key=lambda r:r['entryTime']):
 if row['entryTime']<busy:skip.append({'id':row['setupId'],'code':'serialized_measurement_overlap'});continue
 if row['marginUSDMin']>eq:skip.append({'id':row['setupId'],'code':'broker_margin_exceeds_actual_free_equity'});continue
 x=copy.deepcopy(row);x['volume']=x['volumeMin'];x['netUSD']=x['netUSDMin'];x['initialRiskUSD']=x['priceRiskUSDMin']
 for tm,bid,flt in x['equityPathMin']:
  current=eq+flt;peak=max(peak,current);dd=max(dd,(peak-current)/peak)
 eq+=x['netUSD'];peak=max(peak,eq);dd=max(dd,(peak-eq)/peak);busy=x['exitTime'];trades.append(x)
def metric(rows):
 wins=sum(r['netUSD'] for r in rows if r['netUSD']>0);loss=-sum(r['netUSD'] for r in rows if r['netUSD']<0)
 return {'N':len(rows),'netUSD':sum(r['netUSD'] for r in rows),'grossUSD':sum(r['grossUSDMin'] for r in rows),'assumedFeesUSD':sum(r['commissionUSDMin'] for r in rows),'PF':wins/loss if loss else None,'meanNetR':sum(r['netR'] for r in rows)/len(rows) if rows else None}
parts={k:metric([x for x in trades if lo<=x['entryUTC'][:10]<hi]) for k,lo,hi in [('train','2026-09-08','2026-09-22'),('validation','2026-09-22','2026-10-01'),('previous_historical_holdout','2026-10-01','2026-10-08')]}
out={'recordedUTC':datetime.now(timezone.utc).isoformat(),'riskPolicy':'DIRECT_DEMO_RISK_WAIVER_20261008','sourceResult':str(src),'signalThresholdsChanged':False,'selectedVolume':0.01,'selectionAfterPriorResultsKnown':True,'independentNewOOS':False,'claim':'Retrospective risk-policy reanalysis, not new independently validated profitability.','metrics':metric(trades),'initialEquityUSD':initial,'endEquityUSD':eq,'observedMaximumDDFraction':dd,'partitions':parts,'trades':trades,'skipped':skip,'research_gate_passed':False,'ordersSubmitted':0}
path=R/('backtest_demo_free_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with path.open('x',encoding='utf-8') as f:json.dump(out,f)
print(json.dumps({'path':str(path),'metrics':out['metrics'],'endEquityUSD':eq,'observedDDFraction':dd,'partitions':parts,'researchGatePassed':False}))
