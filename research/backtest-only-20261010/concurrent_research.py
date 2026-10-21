"""One offline stage under separately recorded human demo/research permission.

Frozen child source, plan, data, results and replay algorithm are unchanged.
Only its local operating-mode prerequisite is adapted. No terminal interfaces.
Never writes manager config/state or activates trading. Keeps original locks.
"""
import importlib.util
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from dispatch_active import ROOT, R, read, check


def guard():
    c, s = read(ROOT / 'Trading_Manager_Config.json'), read(ROOT / 'Trading_Manager_State.json')
    a, b = c.get('direct_user_demo_resume', {}), s.get('direct_user_demo_resume', {})
    if a != b or a.get('status') not in ['PENDING_BROKER_MARKET_OPEN', 'ACTIVE']:
        raise RuntimeError('MATCHING_DIRECT_HUMAN_RESUME_AUTHORIZATION_REQUIRED')
    path = Path(a['authorizationPath']).resolve()
    if path != (ROOT / 'trading-journal/direct_demo_resume_market_open_20261011.json').resolve():
        raise RuntimeError('UNREGISTERED_RESUME_AUTHORIZATION')
    check(path, a['authorizationSHA256'])
    event = read(path)
    if (event['kind'] != 'DIRECT_HUMAN_CONDITIONAL_DEMO_RESUME' or not event['researchContinues']
            or str(c['account_login']) != str(event['accountLogin']) or c['account_server'] != event['server']
            or c['version'] != event['version'] or c['symbols'] != event['symbols']
            or event['researchStrategyPromotionAuthorized'] is not False):
        raise RuntimeError('RESUME_SCOPE_MISMATCH')
    check(event['protocolPath'], event['protocolSHA256'])
    suspension = c['direct_user_demo_suspension']
    if suspension['authorizationPath'] != event['supersedesSuspensionAuthorizationPath']:
        raise RuntimeError('NEW_STOP_OVERRIDES_PREVIOUS_RESUME')
    if a['status'] == 'PENDING_BROKER_MARKET_OPEN':
        if (c['enabled'] is not False or c['automation_execution_allowed'] is not False
                or s['stop_requested'] is not True or not suspension['active']
                or not s['research_session']['entriesSuspended']):
            raise RuntimeError('PENDING_OPENING_MUST_RETAIN_STOP_GUARDS')
    else:
        evidence = Path(a['activationEvidencePath']).resolve()
        if not evidence.is_relative_to((ROOT / 'trading-journal').resolve()):
            raise RuntimeError('ACTIVATION_EVIDENCE_PATH_OUTSIDE_JOURNAL')
        check(evidence, a['activationEvidenceSHA256'])
        opening = read(evidence)
        if (opening.get('authorizationSHA256') != a['authorizationSHA256']
                or opening.get('brokerMarketOpenVerified') is not True
                or opening.get('accountLogin') != event['accountLogin']
                or c['enabled'] is not True or c['automation_execution_allowed'] is not True
                or s['stop_requested'] is not False or suspension['active'] is not False
                or s['run_status'] != 'ACTIVE' or s['research_session']['entriesSuspended'] is not False):
            raise RuntimeError('DEMO_ACTIVATION_PROOF_OR_STATE_MISMATCH')
    return c, s


def main():
    guard()
    if (R/'next_research.json').exists():
        next_program=read(R/'next_research.json')
        next_progress=Path(next_program['directory'])/'progress.json'
        if next_progress.exists():
            previous=read(next_progress).get('lastBatchUTC')
            if previous and (datetime.now(timezone.utc)-datetime.fromisoformat(previous.replace('Z','+00:00'))).total_seconds()<900:
                print(json.dumps({'status':'RESEARCH_NOT_DUE','nextResearchIntervalMinutes':15}))
                return
    pointer = read(R / 'active_program.json')
    directory = Path(pointer['directory']).resolve()
    helper, plan = Path(pointer['helperPath']).resolve(), Path(pointer['planPath']).resolve()
    if (not directory.is_relative_to(R.resolve()) or directory == R.resolve()
            or helper != directory / 'cycle.py' or plan != directory / 'plan.json'
            or pointer['newDemoEntriesAllowed'] is not False or pointer['strategyPromotionAllowed'] is not False):
        raise RuntimeError('OFFLINE_PROGRAM_SCOPE_MISMATCH')
    check(helper, pointer['helperSHA256']); check(plan, pointer['planSHA256'])
    receipt = Path(pointer['parentReceiptPath']).resolve()
    if receipt != (R / 'program01_completed_receipt.json').resolve():
        raise RuntimeError('PARENT_RECEIPT_PATH_MISMATCH')
    check(receipt, pointer['parentReceiptSHA256'])
    parent = read(receipt)
    if parent['completedStages'] != 35 or parent['newDemoEntriesAllowed'] is not False:
        raise RuntimeError('PARENT_PROGRAM_INCOMPLETE')
    for key in ['helper', 'plan', 'request', 'state']:
        check(parent[key + 'Path'], parent[key + 'SHA256'])
    for record in parent['results'].values():
        check(record['path'], record['sha256']); check(record['tradesPath'], record['tradesSHA256'])
    lock = R / 'cycle.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, json.dumps({'pid': os.getpid(), 'startedUTC': datetime.now(timezone.utc).isoformat(),
                                'offlineOnly': True, 'mode': 'SEPARATE_HUMAN_AUTHORIZED_DEMO_AND_RESEARCH'}).encode())
        os.close(fd); fd = None
        spec = importlib.util.spec_from_file_location('frozen_concurrent_research', helper)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.guard = guard
        module.verify_plan()
        # All other functions, child locking and exclusive stage evidence remain frozen.
        if (R/'next_research.json').exists():
            import runpy
            next_program=read(R/'next_research.json')
            module.verify_plan()
            assert len(read(directory/'state.json')['completedStages'])==35
            next_helper=Path(next_program['helperPath']).resolve()
            assert next_helper.is_relative_to(R.resolve())
            check(next_helper,next_program['helperSHA256'])
            check(next_program['planPath'],next_program['planSHA256'])
            runpy.run_path(str(next_helper),run_name='__main__')
        else:
            module.main()
        c, s = guard()
        audit = R / ('concurrent_mode_audit_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        module.exclusive(audit, {'kind': 'OFFLINE_RESEARCH_OPERATING_MODE_AMENDMENT',
            'recordedUTC': module.now(), 'authorization': c['direct_user_demo_resume'],
            'managerStatus': s['run_status'], 'frozenHelperSHA256': pointer['helperSHA256'],
            'replayAlgorithmChanged': False, 'brokerCalls': 0,
            'researchGrantsDemoPermission': False,
            'legacyReportHeading': 'Frozen report heading mentions stopped demo; actual operating mode is recorded here.'})
    finally:
        if fd is not None:
            os.close(fd)
        lock.unlink()


if __name__ == '__main__':
    main()
