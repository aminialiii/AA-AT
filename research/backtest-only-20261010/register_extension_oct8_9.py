"""Register a separate offline diagnostic block before its first replay.

No broker interfaces. Old plans, completed stages, and engines stay immutable.
"""
import copy
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('E:/GPT/Inves')
R = ROOT / 'research/backtest-only-20261010'
NEXT = R / 'extension-oct8-9-20261011'
SOURCE_SHA = 'b65cbee5142c6e85ebebdb30550258b118d33220783cb4d6a8ac035566db521d'
VERSION = 'BACKTEST_ONLY_FIXED_OCT8_9_20261011'


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exclusive(path, obj):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())


def guard():
    c, s = read(ROOT / 'Trading_Manager_Config.json'), read(ROOT / 'Trading_Manager_State.json')
    assert c['enabled'] is False and c['automation_execution_allowed'] is False
    assert c['direct_user_demo_suspension']['active'] is True
    assert s['stop_requested'] is True and s['research_session']['entriesSuspended'] is True
    assert s['run_status'] in ['STOPPING', 'STOPPED']
    return c, s


def main():
    _, manager = guard()
    assert not (R / 'cycle.lock').exists(), 'ACTIVE_CYCLE_NO_REGISTRATION'
    assert not (R / 'active_program.json').exists(), 'ALREADY_REGISTERED_NO_REPLAY'
    assert sha(R / 'cycle.py') == SOURCE_SHA, 'PARENT_HELPER_CHANGED'
    parent_plan, parent_state = read(R / 'plan.json'), read(R / 'state.json')
    assert sha(R / 'plan.json') == parent_state['planSHA256']
    assert sha(R / 'request.json') == parent_plan['requestSHA256']
    expected = [s['id'] for s in parent_plan['stages']]
    assert parent_state['completedStages'] == expected and len(expected) == 35
    assert set(parent_state['results']) == set(expected) and parent_state['nextStage'] is None
    result_proofs = {}
    for sid in expected:
        record = parent_state['results'][sid]
        result = read(record['path'])
        assert sha(record['path']) == record['sha256']
        assert sha(result['tradesPath']) == result['tradesSHA256']
        assert result['planSHA256'] == parent_state['planSHA256']
        assert result['boundsUTC'] == parent_plan['boundsUTC']
        assert result['newDemoEntriesAllowed'] is False and result['confirmed'] is False
        result_proofs[sid] = {'path': record['path'], 'sha256': record['sha256'],
                             'tradesPath': result['tradesPath'], 'tradesSHA256': result['tradesSHA256']}
    for path, digest in list(parent_plan['engineHashes'].items()) + [
            (parent_plan['selectionPath'], parent_plan['selectionSHA256']),
            (parent_plan['manifestPath'], parent_plan['manifestSHA256'])]:
        assert sha(path) == digest, 'FROZEN_INPUT_CHANGED'
    manifest = read(parent_plan['manifestPath'])
    start, end = '2026-10-08T00:00:00Z', '2026-10-09T20:00:00Z'
    assert start == parent_plan['boundsUTC']['toExclusive']
    end_seconds = datetime.fromisoformat(end.replace('Z', '+00:00')).timestamp()
    metadata = {}
    for symbol, item in parent_plan['archiveHashes'].items():
        assert sha(item['path']) == item['sha256']
        row = manifest['symbols'][symbol]
        assert row['status'] == 'AVAILABLE' and row['sha256'] == item['sha256']
        assert row['firstUTC'] < start
        last_seconds = datetime.fromisoformat(row['lastUTC']).timestamp()
        assert last_seconds + 60 >= end_seconds, 'COMMON_COMPLETE_M1_END_REQUIRED'
        metadata[symbol] = {k: row[k] for k in ['firstUTC', 'lastUTC', 'path', 'sha256']}

    source = (R / 'cycle.py').read_text(encoding='utf-8')
    # Preserve the exact previous program helper bytes, with a completion receipt.
    with (R / 'cycle_program01_immutable.py').open('xb') as f:
        f.write((R / 'cycle.py').read_bytes())
        f.flush()
        os.fsync(f.fileno())
    completion = {'recordedUTC': now(), 'kind': 'ORIGINAL_PROGRAM_COMPLETED_HASH_PROOF',
                  'version': parent_plan['version'], 'completedStages': 35,
                  'helperPath': str(R / 'cycle_program01_immutable.py'), 'helperSHA256': SOURCE_SHA,
                  'planPath': str(R / 'plan.json'), 'planSHA256': sha(R / 'plan.json'),
                  'requestPath': str(R / 'request.json'), 'requestSHA256': sha(R / 'request.json'),
                  'statePath': str(R / 'state.json'), 'stateSHA256': sha(R / 'state.json'),
                  'results': result_proofs, 'latestReportPath': parent_state['latestReportPath'],
                  'simulationsAddedToActualJournal': False, 'newDemoEntriesAllowed': False}
    exclusive(R / 'program01_completed_receipt.json', completion)

    NEXT.mkdir()
    # Remove the old hardcoded registration path; all inputs are pre-registered here.
    reg_start, reg_end = source.index('def register():'), source.index('def verify_plan():')
    source = source[:reg_start] + '''def register():
    guard()
    if not (R / 'plan.json').exists():
        raise RuntimeError('EXPLICIT_NEW_BLOCK_REGISTRATION_REQUIRED')
    return verify_plan()[0]


''' + source[reg_end:]
    verify_start, verify_end = source.index('def verify_plan():'), source.index('def audit(')
    source = source[:verify_start] + '''def verify_plan():
    plan, state = read(R / 'plan.json'), read(R / 'state.json')
    inputs = [(R / 'plan.json', state['planSHA256']),
              (R / 'request.json', plan['requestSHA256']),
              (plan['selectionPath'], plan['selectionSHA256']),
              (plan['manifestPath'], plan['manifestSHA256']),
              (R / 'cycle.py', plan['helperSHA256'])] + list(plan['engineHashes'].items())
    inputs += [(v['path'], v['sha256']) for v in plan['archiveHashes'].values()]
    for path, expected in inputs:
        if digest(path) != expected:
            raise RuntimeError('RESEARCH_INPUT_HASH_CHANGED_' + str(path))
    if (state['version'] != plan['version'] or len(set(state['completedStages'])) != len(state['completedStages'])
            or set(state['completedStages']) != set(state['results'])):
        raise RuntimeError('RESEARCH_CHECKPOINT_MISMATCH')
    for sid in state['completedStages']:
        record = state['results'][sid]
        if digest(record['path']) != record['sha256']:
            raise RuntimeError('COMPLETED_RESULT_HASH_CHANGED_' + sid)
        completed = read(record['path'])
        if (completed['planSHA256'] != state['planSHA256'] or completed['boundsUTC'] != plan['boundsUTC']
                or completed['stageId'] != sid or digest(completed['tradesPath']) != completed['tradesSHA256']
                or digest(R / (sid + '_started.json')) != completed['startedSHA256']):
            raise RuntimeError('COMPLETED_STAGE_PROOF_MISMATCH_' + sid)
    return plan, state


''' + source[verify_end:]
    source = source.replace("if completed['planSHA256'] != state['planSHA256']:",
        "if (completed['planSHA256'] != state['planSHA256'] or completed['boundsUTC'] != plan['boundsUTC']\n"
        "                or completed['stageId'] != sid or digest(completed['tradesPath']) != completed['tradesSHA256']\n"
        "                or digest(started_path) != completed['startedSHA256']):")
    source = source.replace("'partition': 'NEW_CHRONOLOGICAL_FIXED_RULE_TEST'", "'partition': 'FIXED_RULE_RETROSPECTIVE_DIAGNOSTIC_PARTLY_EXPOSED'")
    source = source.replace("'planSHA256': state['planSHA256'], 'symbol': choice['symbol']", "'planSHA256': state['planSHA256'], 'startedSHA256': digest(started_path), 'symbol': choice['symbol']")
    source = source.replace("'بازه جدید: ۹ سپتامبر تا پایان ۷ اکتبر ۲۰۲۶. قواعد قبلی ثابت مانده‌اند.'",
        "f'بازه ثبت‌شده UTC: {plan[\"boundsUTC\"][\"fromInclusive\"]} تا {plan[\"boundsUTC\"][\"toExclusive\"]} انحصاری. نسخه: {plan[\"version\"]}.'")
    source = source.replace("'این پژوهش مجوز ورود دمو یا اثبات سوددهی نیست. نتیجه آزمون قبلی برای انتخاب مجدد استفاده نشده است.'",
        "'این بازه حدود دو روز و بخشی قبلاً مشاهده‌شده است؛ بررسی تاریخی با قواعد ثابت است. انتخاب مجدد یا مجوز ورود دمو ندارد.'")
    source = source.replace("'|نماد|سناریو|تعداد|WR %|TP|E خالص R|PF|DD بسته R|'",
        "'|نماد|سناریو|تعداد|WR %|TP %|RR مدل میانگین|E خالص R|PF|DD بسته R|Wilson 95 %|روز ورود|censored|'")
    source = source.replace("'|---|---|---:|---:|---:|---:|---:|---:|'",
        "'|---|---|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|'")
    old_row = 'lines.append(f\'|{row["symbol"]}|{row["scenario"]}|{row["n"]}|{fmt(row["winRatePct"])}|{row["TPHits"]}|{fmt(row["expectancyR"])}|{fmt(row["profitFactorR"])}|{fmt(row["maxClosedTradeDrawdownR"])}|\')'
    new_row = 'lines.append(f\'|{row["symbol"]}|{row["scenario"]}|{row["n"]}|{fmt(row["winRatePct"])}|{fmt(row["TPHitRatePct"])}|{fmt(row["meanGrossActualRRModel"])}|{fmt(row["expectancyR"])}|{fmt(row["profitFactorR"])}|{fmt(row["maxClosedTradeDrawdownR"])}|{row["wilson95Pct"]}|{row["entryDays"]}|{row["censoredNotCounted"]}|\')'
    assert old_row in source
    source = source.replace(old_row, new_row)
    with (NEXT / 'cycle.py').open('x', encoding='utf-8', newline='\n') as f:
        f.write(source)
        f.flush()
        os.fsync(f.fileno())
    request = copy.deepcopy(read(R / 'request.json'))
    request.update({'version': VERSION, 'registeredUTC': now(),
                    'rationale': 'Fixed-rule retrospective diagnostic on the adjacent Oct8-Oct9 block, registered before this replay. All seven original choices retained regardless of program01 outcomes.',
                    'priorCompletedProgramPath': str(R / 'program01_completed_receipt.json'),
                    'priorCompletedProgramSHA256': sha(R / 'program01_completed_receipt.json'),
                    'partlyExposedHistoricalPeriod': True, 'untouchedHoldout': False,
                    'modelSelectionFromProgram01Allowed': False, 'historicalCostsHypothetical': True})
    exclusive(NEXT / 'request.json', request)
    plan = copy.deepcopy(parent_plan)
    plan.update({'version': VERSION, 'registeredUTC': now(),
                 'status': 'REGISTERED_BEFORE_THIS_REPLAY_PARTLY_EXPOSED_RETROSPECTIVE_DIAGNOSTIC',
                 'requestSHA256': sha(NEXT / 'request.json'),
                 'boundsUTC': {'fromInclusive': start, 'toExclusive': end},
                 'quarantineHandling': 'Separate adjacent block. Earlier Aug26-Sep8 and Sep9-Oct7 samples stay immutable and are never reused for model selection. No model search.',
                 'newIntervalOutcomeQueriesBeforeRegistration': 0,
                 'newIntervalPriorOutcomeExposureKnown': 'Some live demo/analysis observations on Oct9; not an untouched independent holdout.',
                 'helperSHA256': sha(NEXT / 'cycle.py'),
                 'parentReceiptPath': str(R / 'program01_completed_receipt.json'),
                 'parentReceiptSHA256': sha(R / 'program01_completed_receipt.json'),
                 'archiveMetadataAtRegistration': metadata,
                 'boundaryPolicy': 'Fresh simulated flat start Oct8; pre-block bars supply indicators only; all unclosed trades at Oct9 20:00 censored. No carry-over claim.',
                 'outcomeDecisionPolicy': 'Report every stage, keep all original choices; no tuning, replacing failures, or live promotion. At completion register native tick validation or a genuinely new data block before outcome queries.'})
    plan['limitations'] += [
        'Oct8-Oct9 is partly exposed through prior live/demo analysis, not an untouched holdout or a forward confirmation.',
        'Only 44 hours / two entry dates; min15 entry-day confirmation gate cannot pass. Day bootstrap and Wilson are descriptive with severe small-sample limits.',
        'Flat simulated start omits carry-over exposure; prior end-censored trades remain separate and are not silently closed or reused.',
        'Common end20:00UTC uses last fully closed gold M1 at19:59. M5 requires completed constituent bars under the frozen engine.',
        'No new model selection. Five scenario variants of each symbol share data and are never added as independent samples.'
    ]
    exclusive(NEXT / 'plan.json', plan)
    exclusive(NEXT / 'state.json', {'version': VERSION, 'registeredUTC': now(),
        'planSHA256': sha(NEXT / 'plan.json'), 'completedStages': [], 'phase': 'BASELINE',
        'newDemoEntriesAllowed': False, 'lastCycleUTC': None, 'results': {}, 'nextStage': plan['stages'][0]['id']})
    pointer = {'registeredUTC': now(), 'kind': 'OFFLINE_RESEARCH_ACTIVE_PROGRAM',
               'version': VERSION, 'directory': str(NEXT), 'helperPath': str(NEXT / 'cycle.py'),
               'helperSHA256': sha(NEXT / 'cycle.py'), 'planPath': str(NEXT / 'plan.json'),
               'planSHA256': sha(NEXT / 'plan.json'), 'parentReceiptPath': str(R / 'program01_completed_receipt.json'),
               'parentReceiptSHA256': sha(R / 'program01_completed_receipt.json'),
               'newDemoEntriesAllowed': False, 'strategyPromotionAllowed': False}
    exclusive(R / 'active_program.json', pointer)
    guard()
    print(json.dumps({'status': 'NEXT_PROGRAM_PROSPECTIVELY_REGISTERED_NO_REPLAY_YET',
        'directory': str(NEXT), 'planSHA256': sha(NEXT / 'plan.json'), 'helperSHA256': sha(NEXT / 'cycle.py'),
        'plannedStages': len(plan['stages']), 'boundsUTC': plan['boundsUTC'],
        'intervalAlreadyPartlyExposed': True, 'newIntervalOutcomeQueriesBeforeRegistration': 0,
        'demoEntriesAllowed': False}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
