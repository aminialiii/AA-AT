"""Offline Graphify structural extraction. Never imports project modules."""
import json, hashlib, sys
from pathlib import Path
from graphify.extract import extract
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'graphify-out'
SKIP = {'node_modules', '__pycache__', '.git', '.venv', 'numpy', 'numpy.libs', 'MetaTrader5', 'yaml', '_yaml', 'bin', 'evidence', '.codex-remote-attachments', '.tmp_pdfreview', 'project-review', 'graphify-out'}
def corpus():
    return sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.py','.js','.mjs','.mq5'} and not any(x in SKIP or x.endswith('.dist-info') for x in p.relative_to(ROOT).parts))
if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    files = corpus()
    records = [{'path':p.relative_to(ROOT).as_posix(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'lines':len(p.read_text(encoding='utf-8-sig').splitlines())} for p in files]
    (OUT/'source_manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    (OUT/'.graphify_python').write_text(sys.executable,encoding='utf-8')
    (OUT/'.graphify_root').write_text(str(ROOT),encoding='utf-8')
    data = extract(files, root=ROOT, cache_root=ROOT, parallel=False)
    (OUT/'.graphify_ast.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    detection={'total_files':len(files),'total_words':sum(len(p.read_text(encoding='utf-8-sig').split()) for p in files),'files':{'code':[str(p) for p in files]},'scan_root':str(ROOT)}
    (OUT/'.graphify_detect.json').write_text(json.dumps(detection,indent=2),encoding='utf-8')
    print(json.dumps({'files':len(files),'words':detection['total_words'],'nodes':len(data['nodes']),'edges':len(data['edges'])}))
