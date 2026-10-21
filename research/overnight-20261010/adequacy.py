"""Post-selection development evidence audit. No broker API or holdout reads.

This analysis describes already observed evidence. It cannot change frozen
models, authorize orders, or count repeated simulations as new experiments.
"""
import csv, hashlib, json, math, os, statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

R = Path('E:/GPT/Inves/research/overnight-20261010')

def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def quantile(values, p):
    if not values:
        return None
    values = sorted(values)
    position = (len(values) - 1) * p
    lo = int(position)
    hi = math.ceil(position)
    return values[lo] + (values[hi] - values[lo]) * (position - lo)

def utc_stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()

def run():
    state = read(R / 'state.json')
    if state.get('adequacyPath'):
        old = read(state['adequacyPath'])
        if old['selectionSHA256'] != digest(state['combinedSelectionPath']):
            raise RuntimeError('frozen_selection_changed_after_evidence_audit')
        print(json.dumps({'stage': 'evidence_adequacy', 'status': 'UNCHANGED_DEVELOPMENT_EVIDENCE', 'artifactPath': state['adequacyPath'], 'newIndependentValidation': False}))
        return
    robust = state.get('robustness', {})
    if robust.get('completed') != robust.get('total') or robust.get('completed') != 12:
        raise RuntimeError('complete_registered_robustness_required')
    selection_path = state['combinedSelectionPath']
    selection_hash = digest(selection_path)
    selection = read(selection_path)
    progress = read(state['tickProgressPath'])
    if progress['selectionHash'] != selection_hash or progress['completed'] != progress['total']:
        raise RuntimeError('complete_matching_tick_attempts_required')
    # Read only immutable train/validation and native-validation artifacts.
    samples = []
    inputs = [selection_path, state['tickProgressPath'], state['diagnosticsPath']]
    for path in progress['batches']:
        batch = read(path)
        if batch['selectionHash'] != selection_hash:
            raise RuntimeError('native_tick_selection_mismatch')
        samples.extend(batch['samples'])
        inputs.append(path)
    if len(samples) != 140 or len({x['sampleIndex'] for x in samples}) != 140:
        raise RuntimeError('native_sample_count_or_duplicates')
    scenarios = {}
    for path in robust['artifacts']:
        artifact = read(path)
        if artifact['sourceSelectionSHA256'] != selection_hash or artifact['holdoutOutcomeQueries'] != 0:
            raise RuntimeError('development_only_robustness_required')
        inputs.append(path)
        for result in artifact['results']:
            scenarios[result['symbol'], result['scenario']['id']] = result
    diagnostics = read(state['diagnosticsPath'])
    report_folder = Path(state['latestReportFolder'])
    trade_path = report_folder / 'selected_trade_history.csv'
    inputs.append(str(trade_path))
    with trade_path.open(encoding='utf-8-sig', newline='') as f:
        # Sealed holdout records, if present after release, are never analyzed here.
        trade_rows = [row for row in csv.DictReader(f) if row['partition'] == 'validation']
    rows = []
    bucket_rows = []
    integrity_issues = []
    for choice in selection['choices']:
        symbol = choice['symbol']
        own = [x for x in trade_rows if x['symbol'] == symbol]
        val, train = choice['validation'], choice['train']
        if len(own) != val['n'] or abs(sum(float(x['netR']) for x in own) - val['netR']) > 1e-7:
            raise RuntimeError('validation_archive_reconciliation_' + symbol)
        protection, timing, costs, spread_risk = [], [], [], []
        for row in own:
            entry, sl, tp = (float(row[k]) for k in ['entry', 'SL', 'TP'])
            if not ((row['side'] == 'buy' and sl < entry < tp) or (row['side'] == 'sell' and tp < entry < sl)) or float(row['plannedRR']) < 2 - 1e-8:
                protection.append(row['entryUTC'])
            if utc_stamp(row['entryUTC']) < utc_stamp(row['informationThroughUTC']) or float(row['exitBarTime']) < float(row['entryBarTime']):
                timing.append(row['entryUTC'])
            risk = float(row['priceRiskUSD'])
            costs.append((float(row['commissionScenarioUSD']) + float(row['swapScenarioUSD'])) / risk)
            spread_risk.append(float(row['spreadPriceAssumption']) / abs(entry - sl))
        if protection or timing:
            integrity_issues.append({'symbol': symbol, 'protection': protection, 'timing': timing})
        zero = scenarios[symbol, 'fee0_spread1']['net']
        three = scenarios[symbol, 'fee3_spread1']['net']
        seven = scenarios[symbol, 'fee7_spread1']['net']
        constant_fee_path = zero['n'] == three['n'] == seven['n'] and zero['wins'] == three['wins'] == seven['wins']
        slope = (zero['expectancyR'] - seven['expectancyR']) / 7 if constant_fee_path else None
        linear_check = constant_fee_path and abs((zero['expectancyR'] - 3 * slope) - three['expectancyR']) < 1e-9
        fee_ceiling = zero['expectancyR'] / slope if linear_check and slope > 0 and zero['expectancyR'] > 0 else None
        own_scenarios = [x for (name, _), x in scenarios.items() if name == symbol]
        native = [x for x in samples if x['symbol'] == symbol]
        native_rows = []
        for delay in [5, 20]:
            replay = [r for sample in native for r in sample['results'] if r['latencySeconds'] == delay]
            closed = [x for x in replay if x['status'] == 'SIMULATED_EXIT']
            native_rows.append({'latencySeconds': delay, 'samplesAttempted': len(native), 'replayStatusCounts': dict(Counter(x['status'] for x in replay)), 'closedSimulations': len(closed), 'coverageOfPlannedSamplesPct': 100 * len(closed) / len(native), 'conditionalWinRatePct': 100 * sum(x['netR'] > 0 for x in closed) / len(closed) if closed else None, 'noUnresolvedResultConvertedToWinOrLoss': True})
        flags = []
        if train['expectancyR'] < 0:
            flags.append('TRAIN_EXPECTANCY_NEGATIVE')
        if train['expectancyR'] < 0 < val['expectancyR']:
            flags.append('TRAIN_VALIDATION_EXPECTANCY_SIGN_CHANGE')
        if val['winRatePct'] <= 50:
            flags.append('VALIDATION_POINT_WIN_RATE_NOT_ABOVE_50')
        if choice['validationDayBootstrap']['lower95'] is None or choice['validationDayBootstrap']['lower95'] <= 0:
            flags.append('UNADJUSTED_DEVELOPMENT_EXPECTANCY_LOWER_BOUND_NOT_POSITIVE')
        if choice['positiveWalkForwardFolds'] < 2:
            flags.append('PREQUENTIAL_SELECTION_PROCEDURE_LACKS_TWO_POSITIVE_FOLDS')
        if any(x['closedSimulations'] < x['samplesAttempted'] for x in native_rows):
            flags.append('NATIVE_TICK_EXIT_COVERAGE_INCOMPLETE')
        if zero['expectancyR'] <= 0:
            flags.append('NO_POSITIVE_EXPECTANCY_EVEN_IN_ZERO_COMMISSION_BASE_SCENARIO')
        diagnostic = next(x for x in diagnostics['results'] if x['symbol'] == symbol)
        time_groups = {}
        for dimension, buckets in diagnostic['buckets'].items():
            qualified = [x for x in buckets if x['train']['n'] >= 50 and x['validation']['n'] >= 50]
            ordered = sorted(qualified, key=lambda x: x['validation']['expectancyR'])
            time_groups[dimension] = {'bucketsReviewed': len(buckets), 'bucketsWith50TrainAnd50Validation': len(qualified), 'bestDescriptiveLabel': ordered[-1]['label'] if ordered else None, 'worstDescriptiveLabel': ordered[0]['label'] if ordered else None, 'confirmedFilterRemovalAllowed': False}
            for bucket in buckets:
                bucket_rows.append({'symbol': symbol, 'dimension': dimension, 'label': bucket['label'], 'trainN': bucket['train']['n'], 'validationN': bucket['validation']['n'], 'trainExpectancyR': bucket['train']['expectancyR'], 'validationExpectancyR': bucket['validation']['expectancyR'], 'validationWR': bucket['validation']['winRatePct'], 'validationPF': bucket['validation']['profitFactorR'], 'validationDD': bucket['validation']['maxClosedTradeDrawdownR'], 'validationCILower': bucket['validationDayBootstrap']['lower95'], 'validationCIUpper': bucket['validationDayBootstrap']['upper95'], 'weakDiscoveryInBothPartitions': bucket['negativeInBothDevelopmentPartitions'], 'ruleRemovalApplied': False})
        rows.append({'symbol': symbol, 'timeframe': choice['timeframe'], 'modelId': choice['model']['id'], 'validationN': val['n'], 'validationWR': val['winRatePct'], 'validationWilson95': val['wilson95Pct'], 'trainingExpectancyR': train['expectancyR'], 'validationExpectancyR': val['expectancyR'], 'validationDays': choice['validationDayBootstrap']['days'], 'developmentGatePassed': choice['provisionalGate'], 'weaknessFlags': flags, 'feeLinearPathVerified': linear_check, 'hypotheticalFeeBreakEvenUSDPerLotRoundTrip': fee_ceiling, 'feeCeilingMeaning': 'Conditional interpolation of the same validation trades under modeled spread, slippage and swap; not an actual broker fee or a profitability forecast.', 'commissionAndSwapCostRMedian': quantile(costs, .5), 'commissionAndSwapCostRP90': quantile(costs, .9), 'spreadToInitialStopPriceRatioMedian': quantile(spread_risk, .5), 'protectionViolations': len(protection), 'causalTimestampViolations': len(timing), 'plannedRRMinimum': min(float(x['plannedRR']) for x in own), 'nativeRecordStatuses': dict(Counter(x['status'] for x in native)), 'nativeCoverage': native_rows, 'scenarioCount': len(own_scenarios), 'scenarioCountsIndependent': False, 'scenarioExpectancyRRange': [min(x['net']['expectancyR'] for x in own_scenarios), max(x['net']['expectancyR'] for x in own_scenarios)], 'scenarioWRRange': [min(x['net']['winRatePct'] for x in own_scenarios), max(x['net']['winRatePct'] for x in own_scenarios)], 'positiveExpectancyScenarios': sum(x['net']['expectancyR'] > 0 for x in own_scenarios), 'entryAndTimeGroupAdequacy': time_groups})
    if integrity_issues:
        raise RuntimeError('development_trade_integrity_violations:' + json.dumps(integrity_issues))
    if digest(selection_path) != selection_hash:
        raise RuntimeError('selection_modified_during_audit')
    recorded = datetime.now(timezone.utc)
    path = R / ('development_evidence_adequacy_' + recorded.strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    artifact = {'kind': 'POST_SELECTION_DESCRIPTIVE_EVIDENCE_AUDIT', 'recordedUTC': recorded.isoformat(), 'selectionSHA256': selection_hash, 'selectionChanged': False, 'holdoutOutcomeQueries': 0, 'brokerMutations': 0, 'newIndependentValidation': False, 'uniqueValidationTradesAudited': len(trade_rows), 'rows': rows, 'entryTimeBuckets': bucket_rows, 'sourceSHA256': {str(p): digest(p) for p in inputs}, 'claims': {'confirmedBestSymbol': None, 'newRulesPromoted': [], 'feeBreakEvenIsHistoricalBrokerPolicy': False, 'smallNativeConditionalWRIsWholeStrategyWR': False, 'allScenarioComparisonsIndependent': False}, 'nextResearchRequirements': ['Preserve the frozen choice for the single untouched final evaluation.', 'Confirm historical fee and broker clock policy before trusting session or net-return conclusions.', 'Acquire complete tick coverage for unresolved validation paths before any execution-quality claim.', 'Validate future entry/time filters on a fresh chronological sample; present bucket ranks are descriptive discoveries.', 'Keep historical simulations, prior88 real exits and current22 real exits separate.']}
    with path.open('x', encoding='utf-8') as f:
        json.dump(artifact, f, ensure_ascii=False, indent=2, allow_nan=False)
    state['adequacyPath'] = str(path)
    if 'evidence_adequacy' not in state['completedStages']:
        state['completedStages'].append('evidence_adequacy')
    if not state.get('holdoutOpened'):
        state['nextStage'] = 'WAITING_SEALED_HOLDOUT'
    state['updatedUTC'] = recorded.isoformat()
    temporary = R / 'state.adequacy.tmp'
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temporary, R / 'state.json')
    print(json.dumps({'stage': 'evidence_adequacy', 'artifactPath': str(path), 'uniqueValidationTradesAudited': len(trade_rows), 'nativeSamplesAttempted': len(samples), 'selectionChanged': False, 'holdoutOutcomeQueries': 0, 'integrityViolations': 0, 'newIndependentValidation': False}))

if __name__ == '__main__':
    run()
