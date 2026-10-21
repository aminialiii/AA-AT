"""Dispatch exactly one registered offline stage, retaining prior evidence.

This module only reads local files and runs the hash-pinned offline helper.
"""
import hashlib
import json
import os
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path('E:/GPT/Inves')
R = Path(__file__).resolve().parent


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check(path, expected):
    if digest(path) != expected:
        raise RuntimeError('OFFLINE_PROOF_HASH_CHANGED_' + str(path))


def main():
    c, manager = read(ROOT / 'Trading_Manager_Config.json'), read(ROOT / 'Trading_Manager_State.json')
    if (c.get('enabled') is not False or c.get('automation_execution_allowed') is not False
            or not c.get('direct_user_demo_suspension', {}).get('active')
            or manager.get('stop_requested') is not True
            or not manager.get('research_session', {}).get('entriesSuspended')
            or manager.get('run_status') not in ['STOPPING', 'STOPPED']):
        raise RuntimeError('DIRECT_USER_DEMO_SUSPENSION_REQUIRED_NO_AUTO_RESUME')
    pointer = read(R / 'active_program.json')
    directory = Path(pointer['directory']).resolve()
    helper, plan = Path(pointer['helperPath']).resolve(), Path(pointer['planPath']).resolve()
    if (not directory.is_relative_to(R.resolve()) or directory == R.resolve()
            or helper != directory / 'cycle.py' or plan != directory / 'plan.json'
            or pointer['newDemoEntriesAllowed'] is not False or pointer['strategyPromotionAllowed'] is not False):
        raise RuntimeError('REGISTERED_OFFLINE_PROGRAM_PATH_OR_PERMISSION_MISMATCH')
    check(helper, pointer['helperSHA256'])
    check(plan, pointer['planSHA256'])
    receipt_path = Path(pointer['parentReceiptPath']).resolve()
    if receipt_path != (R / 'program01_completed_receipt.json').resolve():
        raise RuntimeError('PARENT_PROGRAM_RECEIPT_MISMATCH')
    check(receipt_path, pointer['parentReceiptSHA256'])
    receipt = read(receipt_path)
    if receipt['completedStages'] != 35 or receipt['newDemoEntriesAllowed'] is not False:
        raise RuntimeError('PARENT_PROGRAM_INCOMPLETE')
    for item in ['helper', 'plan', 'request', 'state']:
        check(receipt[item + 'Path'], receipt[item + 'SHA256'])
    for record in receipt['results'].values():
        check(record['path'], record['sha256'])
        check(record['tradesPath'], record['tradesSHA256'])
    lock = R / 'cycle.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        try:
            os.write(fd, json.dumps({'pid': os.getpid(), 'startedUTC': datetime.now(timezone.utc).isoformat(),
                                    'version': pointer['version'], 'offlineOnly': True}).encode('utf-8'))
        finally:
            os.close(fd)
        # The registered child also holds its own exclusive stage lock.
        runpy.run_path(str(helper), run_name='__main__')
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
