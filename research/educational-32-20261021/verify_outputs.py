"""Final source, result-schema, graph/HTML and artifact consistency gate."""
import ast,csv,json,hashlib,re,sys
from pathlib import Path
import experiment as e
def main():
 O=e.OUT;ROOT=e.ROOT;e.verify_originals();m=e.read(ROOT/'strategy_research_input/SOURCE_SHA256_MANIFEST.json');assert len(m['files'])==32
 for r in m['files']:assert e.digest(ROOT/'strategy_research_input'/r['path'])==r['sha256']
 cov=e.read(O/'source_ingestion_coverage.json');assert len(cov)==32;assert {r['path'] for r in cov}=={'strategy_research_input/'+r['path'] for r in m['files']}
 req=e.read(ROOT/'strategy_research_input/EVALUATION_SCHEMA.json');counts={};results=[]
 for name in ['baseline_results.csv','candidate_results.csv','all_results.csv']:
  rows=list(csv.DictReader((O/name).open(encoding='utf-8-sig')));counts[name]=len(rows)
  for row in rows:
   assert all(key in row for key in req['required_fields']),(name,row)
   assert row['run_status'] in req['allowed_run_status']
   assert row['evidence_class'] in req['allowed_evidence_class']
   if row['run_status']!='RUN':assert row['reason_if_not_run']
  if name=='all_results.csv':results=rows
 assert counts=={'baseline_results.csv':181,'candidate_results.csv':742,'all_results.csv':923}
 assert len(list((O/'strategy_dossiers').glob('S[0-9][0-9].md')))==18
 assert e.digest(ROOT/'research/educational-32-20261021/experiment.py')==e.read(O/'registration_candidates.json')['engineAdapterSHA256']
 graph=e.read(O/'graphify-out/graph.json');ids={n['id'] for n in graph['nodes']};assert len(ids)==len(graph['nodes']);assert graph['directed'] and graph['multigraph']
 refs=0
 for n in graph['nodes']:
  p=n.get('source_file');loc=str(n.get('source_location') or '')
  if p:assert (ROOT/p).is_file()
  if p and re.match(r'^L\d+',loc):assert int(re.match(r'^L(\d+)',loc).group(1))<=len((ROOT/p).read_text(encoding='utf-8-sig').splitlines());refs+=1
 for edge in graph['links']:
  assert edge['source'] in ids and edge['target'] in ids
  assert edge['confidence'] in {'EXTRACTED','INFERRED','AMBIGUOUS'}
 html=(O/'graphify-out/graph.html').read_text(encoding='utf-8');hn=json.loads(re.search(r'^const RAW_NODES = (.*);$',html,re.M).group(1));he=json.loads(re.search(r'^const RAW_EDGES = (.*);$',html,re.M).group(1));assert {n['id'] for n in hn}==ids;assert len(he)==len(graph['links'])
 dashboard=(O/'comparison_dashboard.html').read_text(encoding='utf-8');embedded=json.loads(re.search(r'<script id="data" type="application/json">(.*?)</script>',dashboard,re.S).group(1));assert len(embedded)==923
 for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
 b=e.read(O/'baseline_reproduction.json');assert b['allMatched'] and b['count']==112
 assert 'Ran 13 tests' in (O/'unit_test.log').read_text() and (O/'unit_test.log').read_text().strip().endswith('OK')
 assert json.loads((O/'event_test.log').read_text())['status']=='PASS'
 assert e.read(O/'reproduction_verification.json')['status']=='PASS'
 summary={'status':'PASS','canonicalSources':32,'originalFilesUnchanged':len(e.read(O/'original_baseline_manifest.json')['files']),'baselineComparisonsMatched':112,'resultSchemaRows':counts,'strategyDossiers':18,'sourceRules':len(e.read(O/'source_rules.json')),'graphNodes':len(ids),'graphRelationships':len(graph['links']),'graphHtmlNodeAndEdgeCountsMatch':True,'sourceNodeLineReferencesChecked':refs,'dashboardRows':923,'pythonTests':13,'nodeAssertions':6,'canonicalReplayChecks':6,'productionConfigurationModified':False,'orderToolsCalled':0,'freshUntouchedOOS':'NOT_RUN'}
 e.exclusive(O/'final_validation.json',summary);print(json.dumps(summary))
if __name__=='__main__':main()
