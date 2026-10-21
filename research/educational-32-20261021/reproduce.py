"""Verify canonical trade/metric reproducibility without touching original outputs.

Default: six replays for nominated S01 baseline+candidate across three partitions.
--all verifies all840primary partition runs. Gzip container metadata may differ;
canonical decompressed JSON records and actual numerical metrics must match.
"""
import argparse,gzip,json,hashlib,math
from pathlib import Path
import experiment as e
def canon(rows):return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true');parser.add_argument('--output',default='research_outputs/reproduction_verification.json');args=parser.parse_args();destination=(e.ROOT/args.output).resolve()
 if not destination.is_relative_to(e.ROOT):raise ValueError('output must remain inside workspace')
 if destination.exists():raise FileExistsError(destination)
 e.verify_originals();base=e.read(e.OUT/'baseline_results.json');candidates=e.read(e.OUT/'candidate_results.json');expected=base+candidates
 if not args.all:expected=[r for r in expected if r['case_id']=='S01_M1_XAUUSD' and r['candidate_id'] in ['BASELINE','PRICE_ACTION_CONFIRMATION']]
 cases={x['case_id']:x for x in e.plans()['cases']};cache={};checks=[]
 for record in expected:
  case=cases[record['case_id']];tf=case['timeframe'];seconds=60 if tf=='M1' else 300;key=(case['case_id'],record['candidate_id'])
  if key not in cache:
   m=e.module(tf);d=m.load_data(case['symbol'],case['bounds']['holdout'][1]);signals=m.signals(d,case['model']);cid=record['candidate_id'];signal=signals if cid=='BASELINE' else e.filtered(d,signals,cid,seconds);m.signals=lambda d,p,s=signal:s;cache[key]=(m,d)
  m,d=cache[key];rows,cens,skips=m.replay(d,case['model'],*case['bounds'][record['partition']]);actual=[{**r,'candidate_id':record['candidate_id'],'timeframe':tf,'partition':record['partition']} for r in rows]+[{**r,'candidate_id':record['candidate_id'],'timeframe':tf,'partition':record['partition'],'censored':True} for r in cens]
  with gzip.open(record['test_artifact_path'],'rt',encoding='utf-8') as f:saved=[json.loads(line) for line in f]
  oldhash=canon(saved);newhash=canon(actual);assert oldhash==newhash,(key,record['partition'])
  metrics=m.metrics(rows,len(cens));assert metrics['n']==record['trade_count'];assert metrics['netR']==record['net_profit_R'];assert math.isclose(metrics['netUSDAtBrokerMinVolume'],record['net_profit'],rel_tol=1e-12,abs_tol=1e-10)
  checks.append({'case_id':record['case_id'],'candidate_id':record['candidate_id'],'partition':record['partition'],'canonicalTradeSHA256':newhash,'canonicalRecordsMatch':True,'metricsMatch':True,'closed':len(rows),'censored':len(cens)})
 e.verify_originals();e.exclusive(destination,{'status':'PASS','mode':'all840primaryRuns' if args.all else 'six nominated S01 partition runs','replayedPartitionRuns':len(checks),'containerHashNote':'Gzip timestamps/headers are not a determinism contract; canonical decompressed JSON trade records and numerical metrics are.','checks':checks});e.log('reproduction_verified',runs=len(checks),artifact=str(destination));print(json.dumps({'status':'PASS','replayedPartitionRuns':len(checks)}))
if __name__=='__main__':main()
