"""Finite, pre-registered development-only robustness work, one scenario per wake.

Diagnostics cannot alter the frozen selection or final holdout.
"""
import sys,json,math
import engine as e
import combined
R=e.R
def register():
 if (R/'robustness_plan.json').exists():return e.read(R/'robustness_plan.json')
 scenarios=[{'id':'fee0_spread1','fees':0,'spread':1,'delayBars':0},{'id':'fee3_spread1','fees':3,'spread':1,'delayBars':0},{'id':'fee7_spread1','fees':7,'spread':1,'delayBars':0},{'id':'fee10_spread1','fees':10,'spread':1,'delayBars':0},{'id':'fee0_spread1_5','fees':0,'spread':1.5,'delayBars':0},{'id':'fee7_spread1_5','fees':7,'spread':1.5,'delayBars':0},{'id':'fee0_spread2','fees':0,'spread':2,'delayBars':0},{'id':'fee7_spread2','fees':7,'spread':2,'delayBars':0},{'id':'fee0_one_bar_late','fees':0,'spread':1,'delayBars':1},{'id':'fee7_one_bar_late','fees':7,'spread':1,'delayBars':1},{'id':'fee0_two_bars_late','fees':0,'spread':1,'delayBars':2},{'id':'fee7_two_bars_late','fees':7,'spread':1,'delayBars':2}]
 p={'registeredUTC':e.utc(),'scenarios':scenarios,'selectionSHA256':e.digest(e.read(R/'state.json')['combinedSelectionPath']),'partition':'validation only; final test not touched','observedDemoCommissionNote':'Closed live demo sample showed zero commission, but that does not establish historical fee policy. Zero-fee is an explicit alternative scenario. Swap remains stress10USD/lot/night.','lateEntryNote':'These delays deliberately invalidate live freshness; M1 bar60s, M5 bar300s. Diagnostic only, never order permission.','selectionChangesAllowed':False,'newIndependentOOSClaim':False}
 with (R/'robustness_plan.json').open('x',encoding='utf-8') as f:json.dump(p,f,indent=2)
 return p
def run():
 p=register();s=e.read(R/'state.json');progress=s.get('robustness',{'completed':0,'total':len(p['scenarios']),'artifacts':[]})
 if progress['completed']>=progress['total']:print(json.dumps({'stage':'robustness','status':'COMPLETE','completed':progress['completed']}));return
 scenario=p['scenarios'][progress['completed']];selection=e.read(s['combinedSelectionPath'])
 if e.digest(s['combinedSelectionPath'])!=p['selectionSHA256']:raise RuntimeError('frozen_selection_changed')
 rows=[]
 for c in selection['choices']:
  en=combined.ENGINES[c['timeframe']];plan=en.read(en.R/'plan.json');d=en.load_data(c['symbol'],plan['bounds']['validation'][1]);ts,cs,sk=en.replay(d,c['model'],*plan['bounds']['validation'],spread_mult=scenario['spread'],fee_per_lot=scenario['fees'],delay_bars=scenario['delayBars'])
  # Gross outcomes versus scenario net outcomes are separate, never substituted.
  metrics=en.metrics(ts,len(cs));gross=[x['grossUSD']/x['priceRiskUSD'] for x in ts];n=len(ts)
  rows.append({'symbol':c['symbol'],'timeframe':c['timeframe'],'modelId':c['model']['id'],'scenario':scenario,'delaySeconds':c['barSeconds']*scenario['delayBars'],'net':metrics,'grossWinRatePct':100*sum(x>0 for x in gross)/n if n else None,'grossExpectancyR':sum(gross)/n if n else None,'skips':sk,'bootstrapNet':en.bootstrap(ts),'noLiveEntryPermission':True})
 path=e.save('development_robustness_'+scenario['id'],{'kind':'SIMULATION_COST_DELAY_DIAGNOSTIC','recordedUTC':e.utc(),'planSHA256':e.digest(R/'robustness_plan.json'),'scenario':scenario,'results':rows,'holdoutOutcomeQueries':0,'sourceSelectionSHA256':p['selectionSHA256'],'historicalActualFeePolicyKnown':False,'selectionChanged':False})
 progress['completed']+=1;progress['artifacts'].append(path);e.state_update(robustness=progress)
 print(json.dumps({'stage':'robustness','artifactPath':path,'completed':progress['completed'],'total':progress['total'],'selectionChanged':False}))
if __name__=='__main__':
 if len(sys.argv)>1 and sys.argv[1]=='register':print(json.dumps({'stage':'robustness_registration','scenarios':len(register()['scenarios'])}))
 else:run()
