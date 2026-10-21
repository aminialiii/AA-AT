"""Offline, frozen historical research. No terminal import or order interface.

The manager's direct user stop is a prerequisite, never cleared by this script.
Started/completed evidence is exclusive; each stage is evaluated once.
"""
import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('E:/GPT/Inves')
R = Path(__file__).resolve().parent
OLD = ROOT / 'research/overnight-20261010'
SYMBOLS = ['XAUUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'EURUSD', 'GBPUSD', 'USDCAD']
SELECTION = OLD / 'frozen_combined_selection_20261009T224018184056Z.json'
SELECTION_SHA = 'a96a1af6ffa200346247f8e8216dcd0913d0354d9789a17fc4590b1653d3a36d'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def exclusive(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def atomic_state(obj):
    tmp = R / ('state_' + str(time.time_ns()) + '.tmp')
    exclusive(tmp, obj)
    os.replace(tmp, R / 'state.json')


def guard():
    c = read(ROOT / 'Trading_Manager_Config.json')
    s = read(ROOT / 'Trading_Manager_State.json')
    if (c.get('enabled') is not False or c.get('automation_execution_allowed') is not False
            or s.get('stop_requested') is not True
            or not c.get('direct_user_demo_suspension', {}).get('active')
            or not s.get('research_session', {}).get('entriesSuspended')
            or s.get('run_status') not in ['STOPPING', 'STOPPED']):
        raise RuntimeError('DIRECT_USER_DEMO_SUSPENSION_REQUIRED; never auto-resume')
    return c, s


def engine_modules():
    sys.path.insert(0, str(OLD))
    import engine as m1
    spec = importlib.util.spec_from_file_location('backtest_only_frozen_m5', OLD / 'm5/engine.py')
    m5 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m5)
    return {'M1': m1, 'M5': m5}


def register():
    _, manager = guard()
    if (R / 'plan.json').exists():
        return read(R / 'plan.json')
    if digest(SELECTION) != SELECTION_SHA:
        raise RuntimeError('FROZEN_SELECTION_HASH_CHANGED')
    ptr = read(OLD / 'history_pointer.json')
    if digest(ptr['path']) != ptr['sha256']:
        raise RuntimeError('HISTORY_MANIFEST_HASH_CHANGED')
    manifest = read(ptr['path'])
    # Registration reads metadata and hashes only, before new interval outcomes.
    choices = read(SELECTION)['choices']
    by_symbol = {c['symbol']: c for c in choices}
    new_choices = [{k: by_symbol[n][k] for k in ['symbol', 'model', 'timeframe', 'barSeconds']}
                   for n in SYMBOLS]
    start, end = '2026-09-09T00:00:00Z', '2026-10-08T00:00:00Z'
    for n in SYMBOLS:
        row = manifest['symbols'][n]
        if row['status'] != 'AVAILABLE' or digest(row['path']) != row['sha256']:
            raise RuntimeError('ARCHIVE_UNAVAILABLE_OR_CHANGED_' + n)
        if row['firstUTC'][:10] >= start[:10] or row['lastUTC'][:10] < end[:10]:
            raise RuntimeError('METADATA_INTERVAL_COVERAGE_INSUFFICIENT_' + n)
    request = {
        'version': 'BACKTEST_ONLY_USER_20261010', 'registeredUTC': now(),
        'userInstruction': 'تا اطلاع بعدی از معاملات دمو صرف نظر کن؛ فقط روی بک تست زمان بزار؛ طبق چرخه قبلی',
        'cadenceMinutes': 15, 'deadlineUTC': None, 'newDemoEntriesAllowed': False,
        'strategyPromotionAllowed': False, 'resumeRequiresNewDirectUserInstruction': True,
        'symbols': SYMBOLS, 'primarySymbol': 'XAUUSD',
        'rationale': 'Evaluate the original frozen selection on a separate later historical block. No re-selection using the old final-test outcomes.',
        'sourceStopPath': manager['direct_user_demo_suspension']['authorizationPath'],
        'priorFinalTest': {'fromUTC': '2026-08-26T00:00:00Z', 'toExclusiveUTC': '2026-09-08T00:00:00Z',
                           'immutable': True, 'reuseForTuningAllowed': False},
        'dataAlreadyCollectedBeforeRegistration': True, 'isProspectiveForwardDemo': False,
        'sources': read(OLD / 'request.json').get('sources', []),
    }
    scenarios = [
        {'id': 'BASELINE', 'spreadMultiplier': 1.0, 'feePerLotRoundTripUSD': 7.0, 'delayBars': 0},
        {'id': 'FEE_14', 'spreadMultiplier': 1.0, 'feePerLotRoundTripUSD': 14.0, 'delayBars': 0},
        {'id': 'SPREAD_1_5', 'spreadMultiplier': 1.5, 'feePerLotRoundTripUSD': 7.0, 'delayBars': 0},
        {'id': 'ONE_BAR_DELAY', 'spreadMultiplier': 1.0, 'feePerLotRoundTripUSD': 7.0, 'delayBars': 1},
        {'id': 'COMBINED_STRESS', 'spreadMultiplier': 1.5, 'feePerLotRoundTripUSD': 14.0, 'delayBars': 1},
    ]
    stages = [{'id': sc['id'] + '_' + ch['symbol'], 'scenario': sc, 'choice': ch}
              for sc in scenarios for ch in new_choices]
    exclusive(R / 'request.json', request)
    plan = {
        'version': request['version'], 'registeredUTC': now(), 'status': 'REGISTERED_BEFORE_NEW_BLOCK_MODEL_OUTCOMES',
        'newIntervalOutcomeQueriesBeforeRegistration': 0, 'requestSHA256': digest(R / 'request.json'),
        'boundsUTC': {'fromInclusive': start, 'toExclusive': end},
        'previousQuarantineFromUTC': read(OLD / 'history-extension.json')['quarantineFromUTC'],
        'quarantineHandling': 'This separate registered block releases Sep9-Oct7 for the fixed old rules only. Original quarantine and old reports remain immutable. Oct8 onward excluded.',
        'selectionPath': str(SELECTION), 'selectionSHA256': SELECTION_SHA,
        'choices': new_choices, 'priorSelectionComparisons': 448,
        'newBaselineComparisons': 7, 'stressVariantsNotIndependentSamples': True,
        'manifestPath': ptr['path'], 'manifestSHA256': ptr['sha256'],
        'engineHashes': {str(p): digest(p) for p in [OLD / 'engine.py', OLD / 'm5/engine.py']},
        'archiveHashes': {n: {'path': manifest['symbols'][n]['path'], 'sha256': manifest['symbols'][n]['sha256']} for n in SYMBOLS},
        'scenarios': scenarios, 'stages': stages, 'primarySymbolFixed': 'XAUUSD',
        'numericalRules': 'Exact hashed M1/M5 engines and model objects: completed bars; warmup100 after gaps; next-bar entry; structural prior3-bar SL plus2ticks, max(minStopATR*ATR,4spread,broker stops); outward-rounded gross USD TP>=2R; one position per symbol; maxSpreadATR0.25.',
        'costRules': {'spread': '1.25*max previous5 completed bars, minimum1tick, scenario multiplier',
                      'entrySlippageTicks': 0.5, 'stopSlippageTicks': 2, 'sameBarSLTP': 'SL first',
                      'gapStop': 'worse of stop and open', 'takeProfitImprovement': False,
                      'swapStressUSDPerLotPerBrokerNight': 10, 'historicalActualCostsKnown': False},
        'diagnosticGates': {'minClosedPerSymbol': 100, 'minEntryDays': 15, 'minProfitFactorR': 1.15,
                            'netExpectancyR': '>0', 'dayBootstrapLower95R': '>0',
                            'WRAbove50Claim': 'Wilson lower95 >50%; unadjusted diagnostic, never a live confirmation'},
        'confirmation': 'None from bar simulation alone; native path and historical costs remain unverified. No live promotion or auto-resume allowed.',
        'limitations': ['Historical period already elapsed; rules frozen before querying these outcomes, not forward trading.',
                       'Historical broker UTC offset180minutes assumed; session/date labels conditional.',
                       'Bar upper/lower excursions are not tick observations; missing tick MAE/MFE=null.',
                       'Closed trades sorted by exit bar UTC then entry UTC; within-bar exit order unknown.',
                       'Fixed1R equity is not actual account equity; capital-feasible portfolio/margin not modeled.',
                       'Point estimates and intervals retain selection/multiple comparison uncertainty.'],
        'strategyPromotionAllowed': False,
    }
    exclusive(R / 'plan.json', plan)
    atomic_state({'version': plan['version'], 'registeredUTC': now(), 'planSHA256': digest(R / 'plan.json'),
                  'completedStages': [], 'phase': 'BASELINE', 'newDemoEntriesAllowed': False,
                  'lastCycleUTC': None, 'results': {}, 'nextStage': stages[0]['id']})
    return plan


def verify_plan():
    plan, state = read(R / 'plan.json'), read(R / 'state.json')
    for path, expected in [(R / 'plan.json', state['planSHA256']),
                           (R / 'request.json', plan['requestSHA256']),
                           (plan['selectionPath'], plan['selectionSHA256']),
                           (plan['manifestPath'], plan['manifestSHA256'])] + list(plan['engineHashes'].items()):
        if digest(path) != expected:
            raise RuntimeError('RESEARCH_INPUT_HASH_CHANGED_' + str(path))
    return plan, state


def audit(stage, elapsed, manager):
    path = R / ('operational_audit_' + str(time.time_ns()) + '.json')
    exclusive(path, {'recordedUTC': now(), 'kind': 'BACKTEST_ONLY_OPERATIONAL_AUDIT',
                     'stageActuallyExecuted': stage, 'elapsedSeconds': elapsed,
                     'demoStatus': manager['run_status'], 'newDemoEntriesAllowed': False,
                     'actualDemoClosed': manager['hundred']['closed'],
                     'actualOpenPositions': len(manager.get('owned_positions', [])),
                     'simulationsAddedToActualJournal': False,
                     'brokerReconciliation': 'Separate read-only manager task; this offline script does not query terminal.',
                     'issues': []})
    return str(path)


def export_report(plan, state):
    rows = []
    for stage in plan['stages']:
        result = state['results'].get(stage['id'])
        if not result:
            continue
        if digest(result['path']) != result['sha256']:
            raise RuntimeError('COMPLETED_RESULT_HASH_CHANGED')
        r = read(result['path'])
        rows.append({'stage': stage['id'], 'symbol': r['symbol'], 'scenario': r['scenario']['id'],
                     'timeframe': r['timeframe'], **r['metrics'], 'entryDays': r['dayBootstrap']['days'],
                     'bootstrapLower95R': r['dayBootstrap']['lower95'], 'status': r['status']})
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = R / ('report_' + stamp)
    out.mkdir()
    exclusive(out / 'summary.json', {'generatedUTC': now(), 'version': plan['version'],
                                   'boundsUTC': plan['boundsUTC'], 'rows': rows,
                                   'completedStages': len(rows), 'plannedStages': len(plan['stages']),
                                   'actualDemoTradesIncluded': 0, 'limitations': plan['limitations']})
    if rows:
        with (out / 'coverage.csv').open('x', newline='', encoding='utf-8-sig') as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    lines = ['# بک‌تست تاریخی با ورود دمو متوقف', '',
             'بازه جدید: ۹ سپتامبر تا پایان ۷ اکتبر ۲۰۲۶. قواعد قبلی ثابت مانده‌اند.', '',
             f'مراحل واقعاً اجراشده: {len(rows)} از {len(plan["stages"])}. زمان ساخت: {now()}', '',
             '|نماد|سناریو|تعداد|WR %|TP|E خالص R|PF|DD بسته R|',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    def fmt(v):
        return 'unknown' if v is None else f'{v:.4f}'
    for row in rows:
        lines.append(f'|{row["symbol"]}|{row["scenario"]}|{row["n"]}|{fmt(row["winRatePct"])}|{row["TPHits"]}|{fmt(row["expectancyR"])}|{fmt(row["profitFactorR"])}|{fmt(row["maxClosedTradeDrawdownR"])}|')
    lines += ['', 'تمام نتایج شبیه‌سازی و هزینه‌ها فرضی‌اند. سناریوهای هزینه روی همان داده نمونه مستقل نیستند.',
              'Wilson، bootstrap روزانه، پوشش و censored در JSON موجود است. ترتیب خروج درون هر کندل مجهول است.',
              'این پژوهش مجوز ورود دمو یا اثبات سوددهی نیست. نتیجه آزمون قبلی برای انتخاب مجدد استفاده نشده است.',
              'بازه تاریخی سپری شده و اختلاف ساعت تاریخی بروکر و مسیر کامل tick هنوز مستقلاً تأیید نشده‌اند.']
    with (out / 'REPORT.md').open('x', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    state['latestReportPath'] = str(out / 'REPORT.md')
    state['latestReportJSONPath'] = str(out / 'summary.json')
    return str(out / 'REPORT.md')


def execute_one():
    began = time.monotonic()
    _, manager = guard()
    plan, state = verify_plan()
    todo = [s for s in plan['stages'] if s['id'] not in state['completedStages']]
    if not todo:
        print(json.dumps({'status': 'PROGRAM_COMPLETE_REGISTER_NEXT_RESEARCH',
                          'completedStages': len(state['completedStages']),
                          'latestReportPath': state.get('latestReportPath'), 'demoEntriesAllowed': False}))
        return
    stage = todo[0]
    sid = stage['id']
    complete_path, started_path = R / (sid + '_completed.json'), R / (sid + '_started.json')
    if complete_path.exists():
        completed = read(complete_path)
        if completed['planSHA256'] != state['planSHA256']:
            raise RuntimeError('COMPLETED_RESULT_PLAN_MISMATCH')
        # Restore a completed result after an interrupted state checkpoint; no replay.
        state['completedStages'].append(sid)
        state['results'][sid] = {'path': str(complete_path), 'sha256': digest(complete_path)}
        state['lastCycleUTC'] = now()
        state['nextStage'] = todo[1]['id'] if len(todo) > 1 else None
        report = export_report(plan, state)
        atomic_state(state)
        print(json.dumps({'status': 'CHECKPOINT_RECOVERED_NO_REPLAY', 'stage': sid, 'reportPath': report}))
        return
    eng = engine_modules()[stage['choice']['timeframe']]
    if started_path.exists():
        recovery_path = R / (sid + '_runtime_reconciliation.json')
        if not recovery_path.exists():
            raise RuntimeError('INCOMPLETE_STAGE_REQUIRES_RECONCILIATION_NO_AUTOMATIC_REPLAY_' + sid)
        recovery = read(recovery_path)
        if (recovery['planSHA256'] != state['planSHA256']
                or recovery['startedSHA256'] != digest(started_path)
                or recovery.get('modelOutcomeQueriesPerformed') != 0
                or recovery.get('failedPhase') != 'NUMPY_IMPORT_BEFORE_LOAD_DATA'
                or (R / (sid + '_trades.jsonl.gz')).exists()):
            raise RuntimeError('RECOVERY_PROOF_INSUFFICIENT_NO_REPLAY_' + sid)
        exclusive(R / (sid + '_runtime_resumed.json'),
                  {'resumedUTC': now(), 'recoveryPath': str(recovery_path),
                   'recoverySHA256': digest(recovery_path), 'independentSampleAdded': False})
    else:
        exclusive(started_path, {'startedUTC': now(), 'kind': 'SIMULATION_INTENT', 'stage': stage,
                                 'planSHA256': state['planSHA256'], 'newDemoEntriesAllowed': False,
                                 'purpose': 'One new historical scenario, not independent live evidence.'})
    bounds = plan['boundsUTC']
    lo, hi = eng.stamp(bounds['fromInclusive']), eng.stamp(bounds['toExclusive'])
    choice, scenario = stage['choice'], stage['scenario']
    data = eng.load_data(choice['symbol'], hi)
    trades, censored, skips = eng.replay(data, choice['model'], lo, hi,
                                       spread_mult=scenario['spreadMultiplier'],
                                       fee_per_lot=scenario['feePerLotRoundTripUSD'],
                                       delay_bars=scenario['delayBars'])
    trades.sort(key=lambda t: (t['exitBarTime'], t['entryBarTime']))
    for t in trades + censored:
        t.update({'researchVersion': plan['version'], 'scenario': scenario['id'],
                  'partition': 'NEW_CHRONOLOGICAL_FIXED_RULE_TEST', 'actualDemoTrade': False,
                  'nativeObservedMAE': None, 'nativeObservedMFE': None})
        if t['plannedRR'] < 2 - 1e-6 or t['entryBarTime'] < lo or t['entryBarTime'] >= hi:
            raise RuntimeError('FROZEN_REPLAY_INVARIANT_VIOLATION')
    archive = R / (sid + '_trades.jsonl.gz')
    with gzip.open(archive, 'xb') as f:
        for t in trades + censored:
            f.write((json.dumps(t, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))
    mm = eng.metrics(trades, len(censored))
    mm['skipCounts'] = skips
    mm['TPHitRatePct'] = 100 * mm['TPHits'] / mm['n'] if mm['n'] else None
    mm['meanGrossActualRRModel'] = sum(t['grossUSD'] / t['priceRiskUSD'] for t in trades) / len(trades) if trades else None
    bootstrap = eng.bootstrap(trades)
    q = plan['diagnosticGates']
    diagnostic_pass = (mm['n'] >= q['minClosedPerSymbol'] and bootstrap['days'] >= q['minEntryDays']
                       and (mm['expectancyR'] or -1) > 0
                       and (mm['profitFactorR'] or 0) >= q['minProfitFactorR']
                       and bootstrap['lower95'] is not None and bootstrap['lower95'] > 0)
    coverage = {'loadedBarsBeforeTestEnd': len(data['t']),
                'testBars': int(((data['t'] >= lo) & (data['t'] < hi)).sum()),
                'firstEntryUTC': min((t['entryUTC'] for t in trades + censored), default=None),
                'lastExitBarUTC': max((t['exitBarUTC'] for t in trades), default=None),
                'testCalendarDays': (hi - lo) / 86400, 'closedEntryDays': bootstrap['days']}
    result = {'completedUTC': now(), 'kind': 'HISTORICAL_SIMULATION_ONLY', 'stageId': sid,
              'planSHA256': state['planSHA256'], 'symbol': choice['symbol'], 'model': choice['model'],
              'timeframe': choice['timeframe'], 'scenario': scenario, 'boundsUTC': bounds,
              'metrics': mm, 'dayBootstrap': bootstrap, 'coverage': coverage,
              'barDiagnosticGatePassed': diagnostic_pass, 'confirmed': False,
              'status': 'BAR_APPROXIMATION_UNCONFIRMED',
              'tradesPath': str(archive), 'tradesSHA256': digest(archive),
              'elapsedSeconds': time.monotonic() - began, 'newDemoEntriesAllowed': False,
              'simulationsAddedToActualJournal': False, 'limitations': plan['limitations']}
    exclusive(complete_path, result)
    _, manager = guard()
    state['completedStages'].append(sid)
    state['results'][sid] = {'path': str(complete_path), 'sha256': digest(complete_path)}
    state['lastCycleUTC'] = now()
    state['nextStage'] = todo[1]['id'] if len(todo) > 1 else None
    state['phase'] = 'BASELINE' if any(s['scenario']['id'] == 'BASELINE' for s in todo[1:]) else 'COST_ROBUSTNESS'
    state['lastAuditPath'] = audit(sid, time.monotonic() - began, manager)
    report = export_report(plan, state)
    atomic_state(state)
    print(json.dumps({'status': 'NEW_BACKTEST_STAGE_COMPLETED', 'stage': sid,
                      'resultPath': str(complete_path), 'closedSimulatedTrades': len(trades),
                      'censored': len(censored), 'expectancyR': mm['expectancyR'],
                      'completedStages': len(state['completedStages']), 'nextStage': state['nextStage'],
                      'reportPath': report, 'actualDemoClosedUnchanged': manager['hundred']['closed'],
                      'demoEntriesAllowed': False}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--register', action='store_true')
    args = parser.parse_args()
    if args.register:
        plan = register()
        print(json.dumps({'status': 'PROSPECTIVE_PROGRAM_REGISTERED', 'planPath': str(R / 'plan.json'),
                          'newBaselineComparisons': plan['newBaselineComparisons'],
                          'plannedStages': len(plan['stages']), 'boundsUTC': plan['boundsUTC'],
                          'newIntervalOutcomeQueriesBeforeRegistration': plan['newIntervalOutcomeQueriesBeforeRegistration']}))
        return
    lock = R / 'cycle.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, json.dumps({'pid': os.getpid(), 'startedUTC': now()}).encode())
        os.close(fd)
        execute_one()
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
