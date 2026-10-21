"""Validate saved final outcomes and propose future research; never replay models."""
import csv, gzip, hashlib, json, math, os
from datetime import datetime, timezone
from pathlib import Path
R = Path('E:/GPT/Inves/research/overnight-20261010')
W = Path('E:/GPT/Inves')
def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
def same(a, b, label):
    if not math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-7):
        raise RuntimeError('saved_outcome_accounting_mismatch:' + label)

state = read(R / 'state.json')
if state.get('finalExportValidationPath'):
    prior = read(state['finalExportValidationPath'])
    if prior['holdoutSHA256'] != digest(state['holdoutPath']):
        raise RuntimeError('immutable_final_result_changed')
    if prior['reportFolder'] == state['latestReportFolder']:
        print(json.dumps({'stage': 'final_export_validation', 'status': 'UNCHANGED_SAVED_FINAL_OUTCOMES', 'artifactPath': state['finalExportValidationPath'], 'modelReplayCount': 0}))
        raise SystemExit(0)
if state.get('holdoutStatus') != 'COMPLETE':
    raise RuntimeError('completed_once_only_final_evaluation_required')
canonical_hash = digest(W / 'Trading_Manager_State.json')
holdout = read(state['holdoutPath'])
selection = read(state['combinedSelectionPath'])
selection_hash = digest(state['combinedSelectionPath'])
started = read(R / 'holdout_started.json')
if stamp(started['openedUTC']) < stamp(read(R / 'plan.json')['holdoutReleaseUTC']):
    raise RuntimeError('early_final_evaluation')
if started['selectionSHA256'] != selection_hash or holdout['selectionSHA256'] != selection_hash:
    raise RuntimeError('final_selection_hash_mismatch')
if digest(holdout['tradePath']) != holdout['tradeSHA256']:
    raise RuntimeError('final_trade_archive_hash_mismatch')
with gzip.open(holdout['tradePath'], 'rt', encoding='utf-8') as f:
    archive = [json.loads(line) for line in f]
closed = [x for x in archive if not x.get('excludedFromWR')]
censored = [x for x in archive if x.get('excludedFromWR')]
folder = Path(state['latestReportFolder'])
with (folder / 'selected_trade_history.csv').open(encoding='utf-8-sig', newline='') as f:
    exported = [x for x in csv.DictReader(f) if x['partition'] == 'sealed_holdout']
with (folder / 'equity_drawdown_data.csv').open(encoding='utf-8-sig', newline='') as f:
    curves = [x for x in csv.DictReader(f) if x['partition'] == 'sealed_holdout']
checks = []
for outcome in holdout['results']:
    name = outcome['symbol']
    frozen = next(x for x in selection['choices'] if x['symbol'] == name)
    if outcome['frozenModel'] != frozen['model'] or outcome['timeframe'] != frozen['timeframe']:
        raise RuntimeError('frozen_rule_mismatch:' + name)
    rows = sorted([x for x in closed if x['symbol'] == name], key=lambda x: x['exitBarTime'])
    csv_rows = [x for x in exported if x['symbol'] == name]
    points = [x for x in curves if x['symbol'] == name]
    metrics = outcome['metrics']
    if len(rows) != metrics['n'] or len(csv_rows) != len(rows) or len(points) != len(rows):
        raise RuntimeError('archive_csv_curve_count_mismatch:' + name)
    winners = sum(x['netR'] > 0 for x in rows)
    same(winners, metrics['wins'], name + ':wins')
    same(sum(x['netR'] < 0 for x in rows), metrics['losses'], name + ':losses')
    same(100 * winners / len(rows), metrics['winRatePct'], name + ':WR')
    same(sum(x['netR'] for x in rows), metrics['netR'], name + ':netR')
    same(sum(x['netUSD'] for x in rows), metrics['netUSDAtBrokerMinVolume'], name + ':netUSD')
    same(sum(float(x['netR']) for x in csv_rows), metrics['netR'], name + ':CSV_netR')
    same(sum(x['plannedRR'] for x in rows) / len(rows), metrics['averagePlannedRR'], name + ':RR')
    pos = sum(x['netR'] for x in rows if x['netR'] > 0)
    neg = -sum(x['netR'] for x in rows if x['netR'] < 0)
    same(pos / neg, metrics['profitFactorR'], name + ':PF')
    same(sum(x['exitReason'] == 'TP' for x in rows), metrics['TPHits'], name + ':TP')
    same(sum(x['exitReason'] == 'SL' for x in rows), metrics['SLHits'], name + ':SL')
    eq, peak, dd = 0.0, 0.0, 0.0
    for index, (row, point) in enumerate(zip(rows, points), 1):
        entry, sl, tp = (row[k] for k in ['entry', 'SL', 'TP'])
        if not ((row['side'] == 'buy' and sl < entry < tp) or (row['side'] == 'sell' and tp < entry < sl)) or row['plannedRR'] < 2 - 1e-8:
            raise RuntimeError('final_protection_or_RR_violation:' + name)
        if stamp(row['entryUTC']) < stamp(row['informationThroughUTC']):
            raise RuntimeError('final_causal_timestamp_violation:' + name)
        same(row['grossUSD'] - row['commissionScenarioUSD'] - row['swapScenarioUSD'], row['netUSD'], name + ':costs')
        same(row['netUSD'] / row['priceRiskUSD'], row['netR'], name + ':normalization')
        eq += row['netR']; peak = max(peak, eq); dd = max(dd, peak - eq)
        same(point['closedSimulationIndex'], index, name + ':chart_index')
        same(point['equityR'], eq, name + ':chart_equity')
        same(point['drawdownR'], peak - eq, name + ':chart_DD')
    same(dd, metrics['maxClosedTradeDrawdownR'], name + ':maximum_DD')
    excluded = sum(x['symbol'] == name for x in censored)
    same(excluded, metrics['censoredNotCounted'], name + ':censored')
    checks.append({'symbol': name, 'closedRows': len(rows), 'censoredRowsExcludedFromWR': excluded, 'minimumPlannedRR': min(x['plannedRR'] for x in rows), 'countsCostsWinRateProfitFactorEquityDrawdownMatched': True, 'frozenRulesMatched': True})
report = read(state['latestReportJSON'])
for filename, expected in report['files'].items():
    if digest(folder / filename) != expected:
        raise RuntimeError('final_report_export_hash_mismatch:' + filename)
if digest(report['charts']['SVG']) != report['charts']['SHA256']:
    raise RuntimeError('final_chart_hash_mismatch')
if digest(W / 'Trading_Manager_State.json') != canonical_hash:
    raise RuntimeError('canonical_demo_state_changed_during_export_validation')
now = datetime.now(timezone.utc)
suffix = now.strftime('%Y%m%dT%H%M%S%fZ')
protocol_path = R / ('next_research_protocol_' + suffix + '.json')
protocol = {'kind': 'PROPOSED_FUTURE_RESEARCH_ONLY_NOT_APPLIED', 'registeredUTC': now.isoformat(), 'basedOnSelectionSHA256': selection_hash, 'basedOnCompletedHoldoutSHA256': digest(state['holdoutPath']), 'confirmedStrategy': None, 'primaryResearchCandidate': 'XAUUSD RANGE_REJECTION; retains frozen numeric rule only as an exploratory hypothesis', 'riskRewardGrossTarget': 2, 'newsFilterEnabled': False, 'priorLossesRemainInOriginalSamples': True, 'actualDemoSevenSymbol700ExitGoalUnchanged': True, 'currentLiveStrategyChanged': False, 'requirements': ['New entry or time filters must be registered prospectively and validated on fresh chronological data; never tune and retest this now-exposed holdout.', 'Gather complete native tick paths for unresolved entries; gaps and censored trades stay unknown.', 'Confirm historical spread, commission, swap and broker UTC offset instead of treating hypothetical costs as actual.', 'Keep SL structural and calculate exact native gross TP>=2R; shrinking TP to improve WR is not a permitted improvement.', 'Use fixed sample blocks and version-separated cumulative results; a recent winning streak or repeated resampling is not proof of WR>50.', 'Any future demo experiment needs matching demo account, fresh quotes, actual margin, valid minimum volume, unique intent and initial broker SL/TP.', 'Keep the already authorized seven-symbol live prototype separate from this unconfirmed historical research; no automatic promotion.'], 'entryTimeFiltersApproved': [], 'readyForUnattendedLiveTrading': False}
with protocol_path.open('x', encoding='utf-8') as f:
    json.dump(protocol, f, ensure_ascii=False, indent=2)
path = R / ('final_export_validation_' + suffix + '.json')
artifact = {'kind': 'SAVED_FINAL_OUTCOME_ACCOUNTING_AND_EXPORT_VALIDATION', 'recordedUTC': now.isoformat(), 'checks': checks, 'holdoutSHA256': digest(state['holdoutPath']), 'selectionSHA256': selection_hash, 'closedSimulationRowsChecked': len(closed), 'censoredRowsExcluded': len(censored), 'savedModelReplayCount': 0, 'freshHoldoutEvaluationCount': 0, 'canonicalDemoStateUnchanged': True, 'actualDemoClosed': read(W / 'Trading_Manager_State.json')['hundred']['closed'], 'brokerMutations': 0, 'visualReviewNotAutomaticallyAsserted': True, 'reportFolder': str(folder), 'reportFilesSHA256': {p.name: digest(p) for p in folder.iterdir() if p.is_file()}, 'proposedNextProtocolPath': str(protocol_path), 'issues': []}
with path.open('x', encoding='utf-8') as f:
    json.dump(artifact, f, ensure_ascii=False, indent=2)
state['finalExportValidationPath'] = str(path)
state['nextResearchProtocolPath'] = str(protocol_path)
temporary = R / 'state.exports.tmp'
temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
os.replace(temporary, R / 'state.json')
print(json.dumps({'stage': 'final_export_validation', 'artifactPath': str(path), 'closedSimulationRowsChecked': len(closed), 'censoredRowsExcluded': len(censored), 'modelReplayCount': 0, 'issues': [], 'nextProtocolPath': str(protocol_path), 'actualDemoStateUnchanged': True}))
