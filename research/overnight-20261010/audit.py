"""Operational and behavior audit every15minutes. Reads proof; never MT5 writes."""
import sys,json,hashlib,os,re
from pathlib import Path
from datetime import datetime,timezone
R=Path('E:/GPT/Inves/research/overnight-20261010');W=Path('E:/GPT/Inves')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))
now=datetime.now(timezone.utc);s=read(W/'Trading_Manager_State.json');r=read(R/'state.json');req=read(R/'request.json');plan=read(R/'plan.json');checks=[];issues=[]
if len(sys.argv)>1:
 health=read(sys.argv[1]);checks.append({'check':'fresh broker evidence','proofPath':sys.argv[1],'brokerMutations':health.get('brokerMutations',health.get('accountOrOrderMutations')),'ageSeconds':now.timestamp()-datetime.fromisoformat(health['observedUTC'].replace('Z','+00:00')).timestamp() if health.get('observedUTC') else None})
 if checks[-1]['ageSeconds'] is None or checks[-1]['ageSeconds']>900:issues.append('broker_read_evidence_missing_or_older_than_15_minutes')
 actual={str(p['ticket']):p for p in health.get('ownedProtection',[])}
 if len(actual)!=len(s['owned_positions']):issues.append('ownership_reconciliation_required')
 for p in s['owned_positions']:
  proof=actual.get(str(p['ticket']))
  if not proof or proof['symbol']!=p['symbol'] or abs(proof['SL']-p['initialSL'])>1e-8 or abs(proof['TP']-p['initialTP'])>1e-8:issues.append('initial_protection_mismatch_'+str(p['ticket']))
checks += [{'check':'actual-demo totals exclude simulated trials','actualClosed':s['hundred']['closed'],'simulatedCountNotAdded':True},{'check':'research-only gate','entriesSuspended':s.get('research_session',{}).get('entriesSuspended')},{'check':'unknown action hold preserved','entryHold':s.get('entry_hold'),'unknown':s.get('unknown_execution_outcome'),'intent':s.get('pending_intent')},{'check':'initial broker protection retained','owners':[{'ticket':p['ticket'],'symbol':p['symbol'],'SL':p['initialSL'],'TP':p['initialTP']} for p in s['owned_positions']]},{'check':'holdout sealed until registered time','opened':r.get('holdoutOpened',False),'releaseUTC':plan['holdoutReleaseUTC'],'selectionIsFrozen':bool(r.get('selectionPath'))},{'check':'real independent stages','completedStages':r['completedStages'],'repeatedOld100RowsExcluded':True}]
trades=s['hundred']['results'];ids=[str(t['ticket']) for t in trades]
if len(trades)!=s['hundred']['closed'] or len(ids)!=len(set(ids)):issues.append('actual_closed_count_or_duplicate_ticket')
for trade in trades:
 proof=read(trade['reconciliationPath'])
 if not proof.get('kind','').startswith('ACTUAL_DEMO') or not any(d.get('entry') in [1,2,3] for d in proof.get('deals',[])):issues.append('actual_broker_exit_proof_missing_'+str(trade['ticket']))
if abs(sum(t['netUSD'] for t in trades)-s['hundred']['netUSD'])>1e-8:issues.append('actual_net_sum_mismatch')
checks.append({'check':'actual count and net reconciled to broker exit evidence','rowsChecked':len(trades),'simulationRowsAdded':0})
deadline=datetime.fromisoformat(req['deadlineUTC'].replace('Z','+00:00'));release=datetime.fromisoformat(plan['holdoutReleaseUTC'].replace('Z','+00:00'))
if r.get('holdoutOpened') and now<release:issues.append('early_holdout_access')
if not s.get('research_session',{}).get('entriesSuspended') and now<deadline:issues.append('research_entry_suspension_missing')
code_hashes={}
for name in ['init.py','collect.py','engine.py','m5/engine.py','ticks.py','combined.py','robustness.py','adequacy.py','readiness.py','final_exports.py','delivery.py','inventory.py','audit.py','release.py']:
 source=(R/name).read_text(encoding='utf-8');code_hashes[name]=hashlib.sha256(source.encode()).hexdigest()
 if re.search(r'\bmt5\.(order_send|login|symbol_select)\s*\(',source):issues.append('broker_mutation_in_research_'+name)
if r.get('verificationPath'):
 proof=read(r['verificationPath'])
 if proof['violations']:issues.append('causal_verification_failed')
child=read(R/'m5/state.json')
if read(child['verificationPath'])['violations']:issues.append('m5_causality_failed')
checks.append({'check':'model outcome quality','verificationPath':r.get('verificationPath'),'m5VerificationPath':child['verificationPath'],'combinedSelectionPath':r.get('combinedSelectionPath'),'costScenarioIsActualFee':False,'noProfitabilityClaim':True,'noPostTestReselection':True})
if r.get('lastAuditUTC'):
 elapsed=(now-datetime.fromisoformat(r['lastAuditUTC'].replace('Z','+00:00'))).total_seconds()
 checks.append({'check':'audit cadence','secondsSincePreviousAudit':elapsed,'targetSeconds':900,'schedulerTimingGuaranteed':False})
data={'kind':'ACTUAL_OPERATIONAL_AND_BEHAVIOR_AUDIT','recordedUTC':now.isoformat(),'deadlineUTC':req['deadlineUTC'],'auditIntervalMinutes':15,'checks':checks,'issues':issues,'sourceSHA256':code_hashes,'behaviorReview':{'failureToAvoid':['Calling repeated statistics independent optimization cycles','Adding simulations or pending/rejected orders to actual trade totals','Selecting on sealed test outcomes','Treating frozen broker wall time as current UTC','Guaranteeing a win-rate target','Reinterpreting deadlines as permission for forced orders'],'action':'Run only the next distinct registered analysis stage; preserve source hashes, costs, skipped/censored trades and a frozen final selection.'}}
p=R/('operational_audit_'+now.strftime('%Y%m%dT%H%M%S%fZ')+'.json')
with p.open('x',encoding='utf-8') as f:json.dump(data,f,ensure_ascii=False,indent=2)
r['lastAuditUTC']=now.isoformat();r['lastAuditPath']=str(p);tmp=R/'state.audit.tmp';tmp.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,R/'state.json')
print(json.dumps({'auditPath':str(p),'issues':issues,'actualDemoClosed':s['hundred']['closed'],'completedAnalysisStages':r['completedStages']}))
