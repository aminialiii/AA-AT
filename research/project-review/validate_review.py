"""Offline integrity checks only: does not import project trading modules."""
import json,hashlib,re,ast
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'graphify-out'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    g=read(OUT/'graph.json');raw=read(OUT/'extraction_repaired.json');ids=[n['id'] for n in g['nodes']]
    assert g['directed'] is True and g['multigraph'] is True
    assert len(ids)==len(set(ids))
    # Nested close() functions in two different simulators are distinct symbols.
    identity=Counter((n.get('source_file'),n.get('source_location'),n.get('label'),n.get('file_type')) for n in g['nodes'])
    duplicate_identities=[(k,v) for k,v in identity.items() if v>1]
    assert not duplicate_identities,duplicate_identities
    assert len(g['links'])==len(raw['edges'])
    html=(OUT/'graph.html').read_text(encoding='utf-8')
    hn=json.loads(re.search(r'^const RAW_NODES = (.*);$',html,re.M).group(1))
    he=json.loads(re.search(r'^const RAW_EDGES = (.*);$',html,re.M).group(1))
    assert {n['id'] for n in hn}==set(ids)
    assert len(he)==len(g['links'])
    assert Counter((e['from'],e['to']) for e in he)==Counter((e['source'],e['target']) for e in g['links'])
    for e in g['links']:
        assert e['source'] in ids and e['target'] in ids
        assert e['confidence'] in {'EXTRACTED','INFERRED','AMBIGUOUS'}
        assert (ROOT/e['source_file']).is_file()
        assert e.get('evidence'),e
    unchanged=[]
    for x in read(OUT/'source_manifest.json'):
        p=ROOT/x['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],x['path'];unchanged.append(x['path'])
    # Parse Python without imports or execution. Validate review tooling too.
    parsed=[]
    for name in unchanged:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'));parsed.append(name)
    for p in Path(__file__).parent.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
    a=read(ROOT/'research/overnight-20261010/plan.json');b=read(ROOT/'research/overnight-20261010/m5/plan.json')
    collisions=sorted({x['id'] for x in a['models']}&{x['id'] for x in b['models']})
    checked_links=0
    for p in Path(__file__).parent.glob('*.md'):
        for target in re.findall(r'\]\((?:<)?([A-Z]:/[^)>]+)',p.read_text(encoding='utf-8')):
            match=re.match(r'(.+?)(?::(\d+))?$',target);q=Path(match[1]);line=int(match[2]) if match[2] else None
            assert q.is_file(),(p.name,target)
            if line:assert 1<=line<=len(q.read_text(encoding='utf-8-sig').splitlines()),(p.name,target)
            checked_links+=1
    result={'graph_checks':'PASS','html_nodes_match_json':len(hn),'html_edges_match_json':len(he),'directed_parallel_edges_preserved':True,'duplicate_identity_keys':0,'document_links_checked':checked_links,'source_files_unchanged':len(unchanged),'python_source_files_parsed_not_executed':len(parsed),'shared_M1_M5_model_ids':collisions,'shared_id_count':len(collisions),'backtests_executed':0,'trading_modules_imported':0,'order_tools_called':0}
    (OUT/'checks.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
