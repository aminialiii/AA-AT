"""Rebuild a directed Graphify graph with an auditable lossless edge ledger.

Reads source as text only; never imports or runs trading/research modules.
Run extract_graph.py first. Semantic evidence is curated separately.
"""
import json, re, hashlib, ast
from collections import Counter
from pathlib import Path
from graphify.build import build_from_json
from graphify.cluster import cluster, score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json
from graphify.diagnostics import diagnose_extraction
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'graphify-out'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')
def main():
    raw=read(OUT/'.graphify_ast.json'); sem=read(OUT/'.graphify_semantic.json')
    nodes=list(raw['nodes'])+sem['nodes']; edges=list(raw['edges'])+sem['edges']; audit=[]
    # Explicitly retain file identities for IIFE wrappers and unsupported MQL5.
    byid={n['id']:n for n in nodes}
    def file_node(path):
        found=next((n for n in nodes if n.get('source_file')==path and n.get('label')==Path(path).name and n.get('file_type')=='code'),None)
        if found:return found['id']
        ident='file_'+hashlib.sha256(path.encode()).hexdigest()[:16]
        if ident not in byid:
            n={'id':ident,'label':Path(path).name,'file_type':'code' if Path(path).suffix in {'.js','.mjs','.py','.mq5'} else 'document','source_file':path,'source_location':'L1','_origin':'semantic','description':'Static file identity; existence does not establish runtime activation.'};nodes.append(n);byid[ident]=n
        return ident
    for rec in read(OUT/'source_manifest.json'):file_node(rec['path'])
    # IIFE wrappers contain host tool calls that the JS extractor does not model.
    # A lexical reference is deliberately weaker than an executed API call.
    for rec in read(OUT/'source_manifest.json'):
        path=rec['path']
        for line,text in enumerate((ROOT/path).read_text(encoding='utf-8-sig').splitlines(),1):
            for api in sorted(set(re.findall(r'tools\.(mcp__[A-Za-z0-9_]+)\s*\(',text))):
                ident='api_'+api
                if ident not in byid:
                    n={'id':ident,'label':api,'file_type':'external','type':'external','external':True,'source_file':None,'source_location':None,'description':'Host tool API reference; availability and execution not verified.'};nodes.append(n);byid[ident]=n
                edges.append({'source':file_node(path),'target':ident,'relation':'references_external_api','confidence':'EXTRACTED','source_file':path,'source_location':f'L{line}','_origin':'semantic','evidence':text.strip(),'description':'Lexical tool reference, possibly inside a deferred function/string; not proof of invocation.'})
    # Canonical package identity: both forms denote the same excluded vendor dependency.
    for e in edges:
        if e['target']=='skill_tools_metatrader5_init':
            audit.append({'change':'canonicalize excluded dependency to external package','before':dict(e)})
            e['target']='metatrader5'
    for src,dst,rel,needle,confidence in read(Path(__file__).with_name('graph_mappings.json'))['mappings']:
        lines=(ROOT/src).read_text(encoding='utf-8').splitlines();hits=[i+1 for i,l in enumerate(lines) if needle in l]
        if not hits or not (ROOT/dst).is_file():raise ValueError(('stale mapping',src,dst,needle))
        edges.append({'source':file_node(src),'target':file_node(dst),'relation':rel,'confidence':confidence,'source_file':src,'source_location':f'L{hits[0]}','_origin':'semantic','evidence':lines[hits[0]-1].strip(),'description':'Static relationship only; configuration-dependent where applicable.'})
    # Data propagation is distinct from direct invocation. The caller line is evidence;
    # this does not mean load_data itself calls replay or that a run occurred.
    for path,source_label,target_label,needle,detail in [
        ('research/overnight-20261010/engine.py','load_data()','replay()',"ts,cs,sk=replay(d,model,*bounds[part])",'grid passes its loaded d into replay'),
        ('research/overnight-20261010/engine.py','signals()','replay()',"sig=signals(d,p)",'replay consumes the returned signal array'),
        ('research/overnight-20261010/engine.py','replay()','metrics()',"row['partitions'][part]=metrics(ts,len(cs))",'grid passes replay trade and censor outputs to metrics'),
        ('research/overnight-20261010/engine.py','load_data()','signals()',"sig=signals(d,p)",'replay passes its d argument, including precomputed indicators, into signals'),
    ]:
        src=next(n['id'] for n in nodes if n.get('source_file')==path and n.get('label')==source_label)
        dst=next(n['id'] for n in nodes if n.get('source_file')==path and n.get('label')==target_label)
        lines=(ROOT/path).read_text(encoding='utf-8').splitlines();line=next(i+1 for i,t in enumerate(lines) if needle in t)
        edges.append({'source':src,'target':dst,'relation':'data_flow','confidence':'INFERRED','source_file':path,'source_location':f'L{line}','evidence':lines[line-1].strip(),'description':detail+'; statically traced, not runtime observation.','_origin':'semantic'})
    # Call targets minted from import namespaces are module member use, not calls to a module.
    missing={e['target'] for e in edges if e['target'] not in byid}
    for ident in sorted(missing):
        ambiguous=ident.startswith('ambiguous_')
        n={'id':ident,'label':ident,'file_type':'external','type':'external','external':True,'source_file':None,'source_location':None,'description':'Unresolved import identity; target ambiguous.' if ambiguous else 'External package/namespace; implementation excluded from review.'}
        nodes.append(n);byid[ident]=n
    for e in edges:
        if e['relation']=='calls' and byid[e['target']].get('external'):
            audit.append({'change':'namespace call is member use, not module invocation','before':dict(e)})
            e['relation']='uses_module_member'; e['context']='static namespace member reference'
        if e['target'].startswith('ambiguous_'):e['confidence']='AMBIGUOUS'
        sf=e.get('source_file'); loc=e.get('source_location')
        if sf and loc and re.match(r'^L\d+',str(loc)):
            lines=(ROOT/sf).read_text(encoding='utf-8-sig').splitlines();i=int(re.match(r'^L(\d+)',loc).group(1))
            if not 1<=i<=len(lines):raise ValueError(('invalid edge location',e))
            e.setdefault('evidence',lines[i-1].strip())
        e.setdefault('description','Static source relationship, not evidence that this path ran.')
    # Exact duplicate records only: keep repeated call sites and distinct relation types.
    unique=[];seen=set()
    for e in edges:
        key=tuple(e.get(k) for k in ('source','target','relation','source_file','source_location','confidence'))
        if key in seen:audit.append({'change':'deduplicate identical evidence record','before':e});continue
        seen.add(key);unique.append(e)
    data={'nodes':nodes,'edges':unique,'hyperedges':sem.get('hyperedges',[]),'input_tokens':sem.get('input_tokens',0),'output_tokens':sem.get('output_tokens',0)}
    ids=[n['id'] for n in nodes]
    if len(ids)!=len(set(ids)):raise ValueError('duplicate node identities')
    errors=[]
    for n in nodes:
        sf=n.get('source_file')
        if sf and not (ROOT/sf).is_file():errors.append(('missing node source',n['id'],sf))
        loc=str(n.get('source_location',''))
        if sf and re.match(r'^L\d+',loc):
            i=int(re.match(r'^L(\d+)',loc).group(1))
            if not 1<=i<=len((ROOT/sf).read_text(encoding='utf-8-sig').splitlines()):errors.append(('invalid node line',n['id']))
    for e in unique:
        if e['source'] not in byid or e['target'] not in byid:errors.append(('missing endpoint',e))
        if e.get('confidence') not in {'EXTRACTED','INFERRED','AMBIGUOUS'}:errors.append(('bad confidence',e))
    if errors:raise ValueError(errors)
    write(OUT/'extraction_repaired.json',data);write(OUT/'repair_log.json',audit)
    G=build_from_json(data,root=ROOT,directed=True,dedup=False)
    if set(G.nodes)!=set(ids):raise ValueError('Graphify changed node identities; explicit remap required')
    communities=cluster(G);cohesion=score_all(G,communities)
    labels={}
    for k,members in communities.items():
        paths=[byid[n].get('source_file') or 'External libraries' for n in members]
        group=Counter('Offline research' if 'overnight' in p or 'backtest-only' in p else 'Native execution helpers' if '.skill-tools' in p else 'Microchannel research' if 'poursamadi' in p else 'Event and shared utilities' for p in paths).most_common(1)[0][0]
        labels[k]=group+' '+str(k)
    gods=god_nodes(G);surprises=surprising_connections(G,communities);questions=suggest_questions(G,communities,labels)
    if not to_json(G,communities,str(OUT/'graph.json'),community_labels=labels,original_links=unique):raise RuntimeError('Graphify export refused shrink; inspect changes before force')
    exported=read(OUT/'graph.json')
    if len(exported['links'])!=len(unique):raise ValueError('edge loss on export')
    counts={'prior_graph':'absent','raw_nodes':len(raw['nodes']),'raw_edges':len(raw['edges']),'raw_missing_endpoint_edges':sum(e['source'] not in {n['id'] for n in raw['nodes']} or e['target'] not in {n['id'] for n in raw['nodes']} for e in raw['edges']),'after_nodes':len(nodes),'after_edges':len(unique),'projection_edges':G.number_of_edges(),'after_missing_endpoints':0,'after_duplicate_ids':0,'invalid_source_references':0,'exact_duplicate_edges_removed':sum(x['change'].startswith('deduplicate') for x in audit),'confidence_counts':dict(Counter(e['confidence'] for e in unique)),'repair_counts':dict(Counter(x['change'] for x in audit)),'semantic_token_usage':'unavailable; numeric zero is a tooling placeholder, not measured usage'}
    write(OUT/'validation.json',counts)
    write(OUT/'.graphify_labels.json',{str(k):v for k,v in labels.items()})
    detection=read(OUT/'.graphify_detect.json')
    report=generate(G,communities,cohesion,labels,gods,surprises,detection,{'input':0,'output':0},str(ROOT),suggested_questions=questions)
    report=report.replace('- Token cost: 0 input · 0 output','- Token cost: unavailable for semantic extraction (zero placeholders are not measured usage).')
    report=report.replace(f'- {len(nodes)} nodes · {G.number_of_edges()} edges',f'- {len(nodes)} nodes · {len(unique)} preserved relationships; {G.number_of_edges()} directed pairs in the clustering projection')
    report=report.replace('## Corpus Check','## Corpus Check\n\nThe count below is the structural code corpus. Semantic extraction additionally covered 23 selected documents/configurations; selected external installed skill dependencies are explicitly mapped. Derived community statistics describe the simple projection.')
    report+='\n\n## Repair audit and representation limits\n\n'+json.dumps(counts,indent=2)+'\n\nJSON preserves directed parallel relationships and separate evidence sites via Graphify original_links. Clustering and centrality above use the directed simple projection ('+str(G.number_of_edges())+' endpoint pairs), not independent evidence counts. These are static relations, not runtime traces. No prior graph existed. Code extraction misses IIFE internals and dynamic eval/subprocess dispatch; explicit file mappings restore selected wiring only. External dependency bodies are excluded. Semantic token usage unavailable. Review corpus and source hashes: source_manifest.json. Full edge evidence: extraction_repaired.json. Repeat corrections: research/project-review/repair_graph.py and graph_mappings.json. Do not run generic update alone: it bypasses these project corrections.\n'
    (OUT/'GRAPH_REPORT.md').write_text(report,encoding='utf-8')
    write(OUT/'diagnostics.json',diagnose_extraction(data,directed=True,root=ROOT))
    print(json.dumps(counts,indent=2))
if __name__=='__main__':main()
