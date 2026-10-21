"""Versioned Graphify research graph; preserves original graphify-out unchanged."""
import json,hashlib,re
from collections import Counter
from pathlib import Path
from graphify.extract import extract
from graphify.build import build_from_json
from graphify.cluster import cluster,score_all
from graphify.analyze import god_nodes,surprising_connections,suggest_questions
from graphify.export import to_json
from graphify.report import generate
from graphify.diagnostics import diagnose_extraction
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'research_outputs';DEST=OUT/'graphify-out'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
 DEST.mkdir(exist_ok=True);old=read(ROOT/'graphify-out/graph.json');nodes=list(old['nodes']);edges=list(old['links']);ids={n['id'] for n in nodes}
 coverage=[];rules=[];identity_repairs=[]
 for filename in ['ingestion_a.json','ingestion_b.json','ingestion_c.json']:
  ing=read(OUT/filename);coverage.extend(ing['coverage']);rules.extend(ing['rules'])
  grouped={}
  for n in ing['nodes']:grouped.setdefault(n['id'],[]).append(n)
  remap={}
  for ident,duplicates in grouped.items():
   if len(duplicates)>1:
    for n in duplicates:
     new=ident+'_'+hashlib.sha256(n['source_file'].encode()).hexdigest()[:10];remap[(ident,n['source_file'])]=new;identity_repairs.append({'old':ident,'new':new,'source_file':n['source_file'],'reason':'same basename with different source extension must remain distinct'});n['id']=new
  for edge in ing['edges']:
   for key in ['source','target']:
    if (edge[key],edge.get('source_file')) in remap:edge[key]=remap[edge[key],edge['source_file']]
  for n in ing['nodes']:
   if n['id'] in ids:raise ValueError('duplicate ingested id '+n['id'])
   nodes.append(n);ids.add(n['id'])
  edges.extend(ing['edges'])
 inventory=read(ROOT/'strategy_research_input/SOURCE_SHA256_MANIFEST.json')['files']
 expected={'strategy_research_input/'+x['path'] for x in inventory};actual={x['path'] for x in coverage}
 if expected!=actual or len(coverage)!=32:raise ValueError('coverage does not match canonical32')
 sourcepaths=sorted(p for p in Path(__file__).parent.glob('*') if p.suffix in {'.py','.mjs'})
 ast=extract(sourcepaths,root=ROOT,cache_root=OUT,parallel=False)
 for n in ast['nodes']:
  if n['id'] in ids:raise ValueError('duplicate source id')
  nodes.append(n);ids.add(n['id'])
 for edge in ast['edges']:
  if edge['target'] not in ids:
   node={'id':edge['target'],'label':edge['target'],'file_type':'external','external':True,'type':'external','source_file':None,'source_location':None};nodes.append(node);ids.add(node['id'])
  if edge['relation']=='calls' and next(n for n in nodes if n['id']==edge['target']).get('external'):edge['relation']='uses_module_member'
  edges.append(edge)
 for n in nodes:
  path=n.get('source_file');loc=str(n.get('source_location') or '')
  if path:
   if not (ROOT/path).is_file():raise ValueError(('missing source',n))
   if re.match(r'^L\d+',loc):
    line=int(re.match(r'^L(\d+)',loc).group(1));assert 1<=line<=len((ROOT/path).read_text(encoding='utf-8-sig').splitlines())
 # Candidate hypothesis edges have exact code evidence and source-rule links.
 source='research/educational-32-20261021/experiment.py';lines=(ROOT/source).read_text(encoding='utf-8').splitlines();filter_node=next(n['id'] for n in nodes if n.get('source_file')==source and n.get('label')=='filtered()')
 for variant in read(OUT/'registration_candidates.json')['variants']:
  cid=variant['candidate_id'];id='edu_candidate_'+cid.lower();line=next(i+1 for i,t in enumerate(lines) if f"cid=='{cid}'" in t)
  nodes.append({'id':id,'label':cid,'file_type':'concept','source_file':source,'source_location':f'L{line}','_origin':'semantic','evidence_class':'RESEARCH_HYPOTHESIS','description':variant['rule']});ids.add(id)
  edges.append({'source':id,'target':filter_node,'relation':'implemented_by','confidence':'EXTRACTED','source_file':source,'source_location':f'L{line}','evidence':lines[line-1].strip(),'_origin':'semantic'})
  for rule in rules:
   formal=str(rule.get('formal_rule','')).lower();family=str(rule.get('candidate_family','')).lower()
   relevant=('time' in family and cid=='TIME_FILTER') or ('level' in family and cid=='LEVEL_FILTER') or ('close' in family and cid=='PRICE_ACTION_CONFIRMATION') or ('cost' in family and cid=='RISK_EXECUTION_REFINEMENT')
   rule_node=next((n['id'] for n in nodes if rule.get('id','').lower() in n['id'].lower()),None)
   if relevant and rule_node:
    edges.append({'source':rule_node,'target':id,'relation':'motivates_research_hypothesis','confidence':'INFERRED','source_file':rule['source_file'],'source_location':f"L{rule['source_line']}",'evidence':rule.get('evidence',str(rule['formal_rule'])),'description':'Motivation only; thresholds and implementation are research hypotheses, no teacher-exact/profitability claim.','_origin':'semantic'})
 clean=[];seen=set()
 for edge in edges:
  key=tuple(edge.get(k) for k in ['source','target','relation','source_file','source_location','confidence'])
  if key in seen:continue
  seen.add(key);clean.append(edge)
  assert edge['source'] in ids and edge['target'] in ids,edge
  assert edge['confidence'] in {'EXTRACTED','INFERRED','AMBIGUOUS'}
  path=edge.get('source_file');loc=str(edge.get('source_location') or '')
  if path and re.match(r'^L\d+',loc):
   text=(ROOT/path).read_text(encoding='utf-8-sig').splitlines();line=int(re.match(r'^L(\d+)',loc).group(1));assert 1<=line<=len(text);edge.setdefault('evidence',text[line-1].strip())
 data={'nodes':nodes,'edges':clean};write(DEST/'extraction.json',data);write(DEST/'identity_repairs.json',identity_repairs);G=build_from_json(data,root=ROOT,directed=True,dedup=False);assert set(G)==ids
 comm=cluster(G);cohesion=score_all(G,comm);labels={k:'Research community '+str(k) for k in comm};assert to_json(G,comm,str(DEST/'graph.json'),community_labels=labels,original_links=clean)
 detection={'total_files':32+len(sourcepaths),'total_words':sum(len((ROOT/x['path']).read_text(encoding='utf-8').split()) for x in coverage),'files':{'document':[str(ROOT/x['path']) for x in coverage],'code':list(map(str,sourcepaths))}}
 report=generate(G,comm,cohesion,labels,god_nodes(G),surprising_connections(G,comm),detection,{'input':0,'output':0},str(ROOT),suggested_questions=suggest_questions(G,comm,labels))
 report=report.replace('- Token cost: 0 input · 0 output','- Semantic token usage unavailable; zeros are tooling placeholders.')
 report='Research graph v20261021. Original graph preserved. JSON is directed multigraph; centrality below uses simple projection. Documentary edges mean supplied text, never verified performance or runtime execution.\n\n'+report
 (DEST/'GRAPH_REPORT.md').write_text(report,encoding='utf-8');write(DEST/'.graphify_labels.json',{str(k):v for k,v in labels.items()});write(DEST/'diagnostics.json',diagnose_extraction(data,directed=True,root=ROOT))
 summary={'beforeNodes':len(old['nodes']),'beforeRelationships':len(old['links']),'afterNodes':len(nodes),'afterRelationships':len(clean),'directedProjectionPairs':G.number_of_edges(),'missingEndpoints':0,'duplicateIdentities':0,'invalidSourceReferences':0,'canonicalSourceFilesVerifiedAndIngested':32,'confidence':dict(Counter(x['confidence'] for x in clean)),'originalGraphSHA256':hashlib.sha256((ROOT/'graphify-out/graph.json').read_bytes()).hexdigest(),'semanticTokenUsage':'unavailable','representationLimit':'72 existing plus new parallel relation records retained in original_links; clustering uses simple projection'}
 write(DEST/'validation.json',summary);write(OUT/'source_ingestion_coverage.json',coverage);write(OUT/'source_rules.json',rules);print(json.dumps(summary))
if __name__=='__main__':main()
