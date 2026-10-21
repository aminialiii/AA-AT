"""Offline regression/property fixtures; no terminal or educational code execution."""
import unittest,json,hashlib,copy
from pathlib import Path
import experiment as e
import numpy as np
from research_safety import research_model_identity,expiry_outcome
class ResearchTests(unittest.TestCase):
 def test_32_integrity(self):
  rows=e.read(e.OUT/'source_integrity.json')['files'];self.assertEqual(len(rows),32)
  for x in rows:self.assertEqual(e.digest(e.ROOT/'strategy_research_input'/x['path']),x['sha256'])
 def test_original_files_unchanged(self):e.verify_originals()
 def test_baseline_reproduced(self):
  r=e.read(e.OUT/'baseline_reproduction.json');self.assertTrue(r['allMatched']);self.assertEqual(r['count'],112)
 def test_timeframe_identity_defect_and_repair(self):
  import ast,tempfile,types
  p={'family':'RANGE_REJECTION','bodyATR':.2,'minStopATR':.5,'session':'ALL','targetR':2};generated=[]
  # Invoke the actual original plan() definition with synthetic inputs and an
  # isolated temporary R. No production writes or historical replay occurs.
  a=np.array([(int(e.stamp('2026-01-01T00:00:00Z'))+i*86400,) for i in range(50)],dtype=[('time','i8')])
  req={'models':['RANGE_REJECTION'],'grid':{'bodyATR':[.2],'minStopATR':[.5],'sessions':['ALL']},'symbols':['TEST'],'holdoutReleaseUTC':'2026-04-01T00:00:00Z','sources':[]}
  for tf in ['M1','M5']:
   source=(e.OUT/'frozen'/f'{tf}_engine.py').read_text(encoding='utf-8-sig');definition=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='plan')
   with tempfile.TemporaryDirectory(prefix='identity_fixture_',dir=e.OUT) as temp:
    r=Path(temp)
    def fixture_read(path):
     return req if Path(path).name=='request.json' else {'quarantineFromUTC':'2026-03-01T00:00:00Z'} if Path(path).name=='history-extension.json' else {'path':'fixture_manifest'}
    ns={'R':r,'read':fixture_read,'manifest':lambda:{'symbols':{'TEST':{'status':'AVAILABLE','path':'fixture_array','sha256':'fixture'}},'brokerOffsetMinutes':0},'stamp':e.stamp,'digest':lambda p:'fixture','np':types.SimpleNamespace(load=lambda p:{'rates':a}),'itertools':__import__('itertools'),'hashlib':hashlib,'json':json,'utc':lambda:'2026-10-21T00:00:00Z','iso':e.iso,'save':lambda *a:'fixture_only','finish':lambda *a,**k:None}
    exec(compile(ast.Module(body=[definition],type_ignores=[]),'original_plan_fixture','exec'),ns);ns['plan']();generated.append(e.read(r/'plan.json')['models'][0]['id'])
  self.assertEqual(*generated)
  self.assertNotEqual(research_model_identity(p,'M1'),research_model_identity(p,'M5'))
  cases=e.plans()['cases'];keys=[x['case_id'] for x in cases];self.assertEqual(len(keys),len(set(keys)))
 def test_saved_ids_have_no_collision(self):
  root=e.ROOT/'research/overnight-20261010';a=e.read(root/'plan.json');b=e.read(root/'m5/plan.json')
  self.assertFalse({x['id'] for x in a['models']}&{x['id'] for x in b['models']})
 def test_timezone_dst_transitions(self):
  rules=np.array(e.read(e.OUT/'timezone_rules_2026.json')['rows'])
  def offsets(ts):return rules[np.searchsorted(rules[:,0],e.stamp(ts),side='right')-1,1:].tolist()
  self.assertEqual(offsets('2026-03-08T06:00:00Z'),[0,-300]);self.assertEqual(offsets('2026-03-08T07:00:00Z'),[0,-240])
  self.assertEqual(offsets('2026-03-29T00:00:00Z'),[0,-240]);self.assertEqual(offsets('2026-03-29T01:00:00Z'),[60,-240])
 def test_time_filter_boundary(self):
  t=np.array([e.stamp('2026-07-15T06:58:00Z'),e.stamp('2026-07-15T06:59:00Z'),e.stamp('2026-07-15T09:59:00Z')])
  self.assertEqual(e.time_mask(t,60).tolist(),[False,True,False])
 def synthetic(self,hit=False):
  n=130;t=np.arange(n)*60+e.stamp('2026-07-15T00:00:00Z');a=np.full(n,100.0)
  d={'name':'XAUUSD','t':t,'o':a.copy(),'c':a.copy(),'h':a+.1,'l':a-.1,'atr':np.ones(n),'spread':np.full(n,.01),'tick':.01,'ema20':a.copy(),'ema60':a.copy(),'hi20':a+.1,'lo20':a-.1,'valid':np.ones(n,bool),'spec':{'volume_min':.01,'trade_contract_size':100,'trade_stops_level':0,'point':.01}}
  if hit:d['h'][101]=103;d['l'][101]=98
  return d
 def replay_fixture(self,hit):
  m=e.module('M1');d=self.synthetic(hit);sig=np.zeros(len(d['t']),np.int8);sig[100]=1;m.signals=lambda d,p:sig
  return m.replay(d,{'id':'FIXTURE_M1','family':'M1_MOMENTUM_PROXY','bodyATR':.2,'minStopATR':.5,'session':'ALL'},d['t'][100],d['t'][-1]+60)
 def test_intrabar_pessimistic_and_timing(self):
  rows,cens,skips=self.replay_fixture(True);self.assertEqual(len(rows),1);r=rows[0]
  self.assertEqual(r['exitReason'],'SL');self.assertTrue(r['bothSLTPInSameBar']);self.assertGreaterEqual(r['entryBarTime'],e.stamp(r['informationThroughUTC']));self.assertLess(r['netUSD'],0)
 def test_open_trade_censoring(self):
  rows,cens,skips=self.replay_fixture(False);self.assertFalse(rows);self.assertEqual(len(cens),1);self.assertTrue(cens[0]['excludedFromWR'])
 def test_replay_determinism(self):
  self.assertEqual(self.replay_fixture(True),self.replay_fixture(True))
 def test_gtc_expiry_is_manager_dependent(self):
  self.assertEqual(expiry_outcome(60,None),'FILLED_LATE');self.assertEqual(expiry_outcome(60,90),'FILLED_LATE');self.assertEqual(expiry_outcome(60,45),'CANCELLED_OR_EXPIRED');self.assertEqual(expiry_outcome(60,None,45),'CANCELLED_OR_EXPIRED')
 def test_causal_features_and_signals(self):
  for tf in ['M1','M5']:
   m=e.module(tf);cut=e.stamp('2026-08-14T00:00:00Z');full=m.load_data('EURUSD',e.stamp('2026-08-26T00:00:00Z'));small=m.load_data('EURUSD',cut);n=len(small['t'])
   for key in ['atr','ema20','ema60','hi20','lo20','spread']:np.testing.assert_allclose(small[key],full[key][:n],equal_nan=True)
   np.testing.assert_allclose(e.prior_levels(small),e.prior_levels(full)[:n],equal_nan=True)
   for case in [c for c in e.plans()['cases'] if c['symbol']=='EURUSD' and c['timeframe']==tf]:
    a=m.signals(small,case['model']);b=m.signals(full,case['model']);np.testing.assert_array_equal(a,b[:n])
    for cid in ['TIME_FILTER','LEVEL_FILTER','PRICE_ACTION_CONFIRMATION','RISK_EXECUTION_REFINEMENT']:
     np.testing.assert_array_equal(e.filtered(small,a,cid,60 if tf=='M1' else 300),e.filtered(full,b,cid,60 if tf=='M1' else 300)[:n])
 def test_adapter_no_account_imports(self):
  import ast
  tree=ast.parse(Path(e.__file__).read_text());names=[]
  for n in ast.walk(tree):
   if isinstance(n,ast.Import):names.extend(x.name for x in n.names)
   if isinstance(n,ast.ImportFrom):names.append(n.module or '')
  self.assertFalse(any('MetaTrader' in x or 'requests' in x or 'socket' in x for x in names))
if __name__=='__main__':unittest.main(verbosity=2)
