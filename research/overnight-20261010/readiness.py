"""Hash-only integrity check before sealed evaluation; no price decoding."""
import hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

R = Path('E:/GPT/Inves/research/overnight-20261010')
W = Path('E:/GPT/Inves')
def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))
def digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            result.update(chunk)
    return result.hexdigest()

state = read(R / 'state.json')
if state.get('holdoutOpened') or (R / 'holdout_started.json').exists():
    raise RuntimeError('readiness_check_requires_still_sealed_test')
canonical_before = digest(W / 'Trading_Manager_State.json')
selection_hash = digest(state['combinedSelectionPath'])
checks = []
def verify(path, expected, kind):
    actual = digest(path)
    checks.append({'path': str(path), 'kind': kind, 'expectedSHA256': expected, 'actualSHA256': actual, 'passed': actual == expected})
    if actual != expected:
        raise RuntimeError('evidence_hash_mismatch:' + str(path))

pointer = read(R / 'history_pointer.json')
verify(pointer['path'], pointer['sha256'], 'historical_manifest')
manifest = read(pointer['path'])
for name, symbol in manifest['symbols'].items():
    if symbol['status'] != 'AVAILABLE':
        raise RuntimeError('historical_symbol_unavailable:' + name)
    verify(symbol['path'], symbol['sha256'], 'historical_array_hash_only; OHLC_not_decoded')
report = read(state['latestReportJSON'])
if report.get('holdout') is not None or report['sourceSelectionSHA256'] != selection_hash:
    raise RuntimeError('pre_final_report_must_match_frozen_choice_without_test_results')
folder = Path(state['latestReportFolder'])
for name, expected in report['files'].items():
    verify(folder / name, expected, 'simulation_report_export')
for archive in report['fullTradeArchives']:
    verify(archive['tradesPath'], archive['SHA256'], 'development_simulation_archive')
progress = read(state['tickProgressPath'])
if progress['selectionHash'] != selection_hash or progress['completed'] != 140:
    raise RuntimeError('native_validation_selection_or_attempt_count_mismatch')
native_files = set()
for path in progress['batches']:
    batch = read(path)
    if batch['selectionHash'] != selection_hash:
        raise RuntimeError('native_batch_selection_mismatch')
    for sample in batch['samples']:
        if sample.get('tickPath') and sample.get('tickSHA256'):
            verify(sample['tickPath'], sample['tickSHA256'], 'native_validation_tick_archive')
            native_files.add(sample['tickPath'])
if digest(state['combinedSelectionPath']) != selection_hash or digest(W / 'Trading_Manager_State.json') != canonical_before:
    raise RuntimeError('selection_or_canonical_state_changed_during_readiness_check')
if state['robustness']['completed'] != 12 or not read(W / 'Trading_Manager_State.json')['research_session']['entriesSuspended']:
    raise RuntimeError('completed_diagnostics_and_research_suspension_required')
now = datetime.now(timezone.utc)
path = R / ('final_evidence_readiness_' + now.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
artifact = {'kind': 'HASH_ONLY_PRE_FINAL_EVIDENCE_INTEGRITY_CHECK', 'recordedUTC': now.isoformat(), 'checks': checks, 'selectionSHA256': selection_hash, 'canonicalStateUnchanged': True, 'holdoutStillSealed': True, 'holdoutOutcomeQueries': 0, 'rawHistoricalPriceArraysDecoded': False, 'brokerMutations': 0, 'independentNewBacktest': False, 'nativeValidationArchivesVerified': len(native_files), 'readinessMeaning': 'Verifies saved bytes and workflow guards; does not establish profitable trading or complete native tick coverage.'}
with path.open('x', encoding='utf-8') as f:
    json.dump(artifact, f, ensure_ascii=False, indent=2)
state['readinessPath'] = str(path)
temporary = R / 'state.readiness.tmp'
temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
os.replace(temporary, R / 'state.json')
print(json.dumps({'stage': 'final_evidence_readiness', 'artifactPath': str(path), 'hashChecksPassed': len(checks), 'nativeArchivesVerified': len(native_files), 'holdoutStillSealed': True, 'brokerMutations': 0}))
