"""Register fixed native-tick validation of the completed Oct8-9 baseline.
No broker/data outcome queries; membership uses every existing baseline row.
"""
import gzip, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
R=Path(__file__).resolve().parent
D=R/'native-oct8-9-validation'
OLD=Path('E:/GPT/Inves/research/overnight-20261010')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def exclusive(p,obj):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
pointer=read(R/'active_program.json'); parent=Path(pointer['directory']); state=read(parent/'state.json')
assert len(state['completedStages'])==35
proof=[]; samples=[]
for sid,record in state['results'].items():
    assert digest(record['path'])==record['sha256']
    result=read(record['path']); assert digest(result['tradesPath'])==result['tradesSHA256']
    assert digest(parent/(sid+'_started.json'))==result['startedSHA256']
    proof.append({'path':record['path'],'sha256':record['sha256'],'tradesPath':result['tradesPath'],'tradesSHA256':result['tradesSHA256']})
    if sid.startswith('BASELINE_'):
        with gzip.open(result['tradesPath'],'rt',encoding='utf-8') as f:
            samples.extend(json.loads(line) for line in f if line.strip())
samples=[x for x in samples if x.get('exitBarTime') is not None]
samples.sort(key=lambda x:(x['entryBarTime'],x['symbol'],x['exitBarTime']))
D.mkdir()
source=(OLD/'ticks.py').read_text(encoding='utf-8')
body=source[source.index("if not mt5.initialize"):]
body=body.replace("e.state_update(tickProgressPath=str(progress));",'')
header='''import sys,json,gzip,hashlib,math,time,os
from pathlib import Path
from datetime import datetime,timezone,timedelta
sys.path.insert(0,'E:/GPT/Inves/.skill-tools')
sys.path.insert(0,'E:/GPT/Inves/research/overnight-20261010')
import numpy as np
import MetaTrader5 as mt5
import engine as e
R=Path(__file__).resolve().parent
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
plan=read(R/'plan.json'); checkpoint=read(R/'state.json')
assert digest(R/'plan.json')==checkpoint['planSHA256']
assert digest(__file__)==plan['helperSHA256']
for proof in plan['parentProof']:
 assert digest(proof['path'])==proof['sha256'] and digest(proof['tradesPath'])==proof['tradesSHA256']
for path,sha in plan['engineHashes'].items():assert digest(path)==sha
def save(kind,obj):
 p=R/(kind+'_'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.json')
 with p.open('x',encoding='utf-8') as f:json.dump(obj,f,indent=2)
 return str(p)
e.save=save
selection_hash=checkpoint['planSHA256']
progress=R/'progress.json'
done=read(progress) if progress.exists() else {'selectionHash':selection_hash,'completed':0,'total':len(plan['samples']),'batches':[]}
assert done['selectionHash']==selection_hash
for path in done['batches']:
 assert digest(path)==done['batchHashes'][path]
if done['completed']>=done['total']:
 print(json.dumps({'status':'NATIVE_VALIDATION_COMPLETE','completed':done['completed'],'total':done['total']}));sys.exit(0)
'''
body=body.replace("done['completed']+=len(out);", "done.setdefault('batchHashes',{})[batch]=digest(batch);done['completed']+=len(out);")
helper=D/'cycle.py'
helper.write_text(header+body,encoding='utf-8')
plan={'version':'FIXED_NATIVE_VALIDATION_OCT8_9_20261011','registeredUTC':datetime.now(timezone.utc).isoformat(),
 'helperSHA256':digest(helper),'boundsUTC':read(parent/'plan.json')['boundsUTC'],
 'parentProof':proof,'samples':samples,'latenciesSeconds':[5,20],
 'engineHashes':{str(OLD/'engine.py'):digest(OLD/'engine.py')},
 'sampleRule':'All closed BASELINE rows, chronological entry time then symbol. No outcome ranking or new independent trades. Native windows over 3h explicitly unknown; no silent removal.',
 'feesPerLotRoundTripUSD':7,'swapStressPerLotNightUSD':10,'entrySlippageTicks':0.5,'stopSlippageTicks':2,
 'structuralSL':'Keep frozen baseline structural SL; recompute gross RR2 target from executable native bid/ask.',
 'newIntervalOutcomeQueriesBeforeRegistration':0,'brokerMutationsAllowed':False,'strategyPromotionAllowed':False,
 'limitations':['Native validation of existing Oct8-9 partly exposed data; not independent new sample.','Latency variants not independent samples.','Tick gaps >10s, missing/stale entry, long windows and censored separate.','Costs and historical contract/currency conversion assumptions remain unverified.','No exact five-second live model claim.']}
exclusive(D/'plan.json',plan)
exclusive(D/'state.json',{'planSHA256':digest(D/'plan.json'),'version':plan['version']})
exclusive(R/'next_research.json',{'directory':str(D),'helperPath':str(helper),'helperSHA256':digest(helper),'planPath':str(D/'plan.json'),'planSHA256':digest(D/'plan.json'),'parentCompleted':35})
print(json.dumps({'status':'NATIVE_PLAN_REGISTERED_BEFORE_RESULTS','samples':len(samples),'path':str(D/'plan.json')}))
