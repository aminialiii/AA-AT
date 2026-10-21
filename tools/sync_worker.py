"""Four-hour, review-branch GitHub synchronization. Never deploys trading code."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from secret_scan import scan

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT.parent / "AA-AT-sync-state"
STATUS = STATE_DIR / "status.json"
REMOTE = "https://github.com/aminialiii/AA-AT.git"
OWNER = "aminialiii"
REPO = "AA-AT"
BRANCH = "automation/source-sync"


def utc():
    return datetime.now(timezone.utc).isoformat()


def run(args, cwd, *, input_text=None, timeout=180):
    p = subprocess.run(args, cwd=cwd, input=input_text, text=True,
                       capture_output=True, timeout=timeout, check=False)
    if p.returncode:
        # Do not echo output from tools that may expose remote URLs or credentials.
        raise RuntimeError(f"command_failed:{args[0]}:{args[1] if len(args)>1 else ''}:exit_{p.returncode}")
    return p.stdout.strip()


def write_status(value):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATUS)


def read_status():
    return json.loads(STATUS.read_text(encoding="utf-8")) if STATUS.exists() else {}


def source_paths():
    raw = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
                         cwd=ROOT, capture_output=True, check=True).stdout
    return {Path(p.decode("utf-8")).as_posix() for p in raw.split(b"\0") if p and (ROOT / p.decode("utf-8")).is_file()}


def verify_source(paths):
    findings = scan([ROOT / p for p in paths])
    if findings:
        raise RuntimeError(f"secret_scan_blocked:{len(findings)}_files")
    return len(paths)


def refresh_local_outputs():
    exported = json.loads(run([sys.executable, "tools/export_operational_status.py"], ROOT))
    if exported["changed"]:
        graph_python = Path.home() / "AppData/Roaming/uv/tools/graphifyy/Scripts/python.exe"
        if not graph_python.is_file():
            raise RuntimeError("graphify_python_unavailable")
        run([str(graph_python), "tools/build_dev_graph.py"], ROOT)
    run([sys.executable, "tools/build_dashboard.py"], ROOT)


def git_credential():
    try:
        value = run(["git", "credential", "fill"], ROOT,
                    input_text="protocol=https\nhost=github.com\n\n", timeout=20)
        fields = dict(line.split("=", 1) for line in value.splitlines() if "=" in line)
        return fields.get("password")
    except (RuntimeError, subprocess.TimeoutExpired):
        return None


def github_request(method, path, token, data=None):
    payload = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request("https://api.github.com" + path, data=payload, method=method,
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/vnd.github+json",
                                          "X-GitHub-Api-Version": "2022-11-28",
                                          "User-Agent": "AA-AT-source-sync"})
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.loads(response.read())


def ensure_pr():
    token = git_credential()
    if not token:
        return {"state": "PR_PENDING", "url": f"https://github.com/{OWNER}/{REPO}/compare/main...{BRANCH}?expand=1"}
    try:
        found = github_request("GET", f"/repos/{OWNER}/{REPO}/pulls?state=open&head={OWNER}:{BRANCH}&base=main", token)
        if found:
            return {"state": "OPEN", "url": found[0]["html_url"]}
        made = github_request("POST", f"/repos/{OWNER}/{REPO}/pulls", token, {
            "title": "Review synchronized source changes",
            "head": BRANCH,
            "base": "main",
            "body": "Automated source synchronization after offline validation and secret scanning. Review before merging; this PR does not deploy trading code.",
            "draft": True,
        })
        return {"state": "OPEN", "url": made["html_url"]}
    except (urllib.error.URLError, KeyError, ValueError):
        return {"state": "PR_PENDING", "url": f"https://github.com/{OWNER}/{REPO}/compare/main...{BRANCH}?expand=1"}


def once():
    previous = read_status()
    refresh_local_outputs()
    paths = source_paths()
    verify_source(paths)
    with tempfile.TemporaryDirectory(prefix="aa-at-sync-", dir=STATE_DIR) as folder:
        checkout = Path(folder) / "checkout"
        heads = run(["git", "ls-remote", "--heads", "origin", BRANCH], ROOT)
        branch_exists = bool(heads)
        if branch_exists:
            remote_tip = heads.split()[0]
            if previous.get("last_pushed_sha") != remote_tip:
                raise RuntimeError("automation_branch_changed_outside_worker")
            run(["git", "clone", "--quiet", "--branch", BRANCH, REMOTE, str(checkout)], ROOT)
        else:
            run(["git", "clone", "--quiet", "--branch", "main", REMOTE, str(checkout)], ROOT)
            run(["git", "checkout", "-q", "-b", BRANCH], checkout)
        for relative in sorted(paths):
            target = checkout / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
        previous_paths = set(run(["git", "ls-files"], checkout).splitlines())
        for relative in sorted(previous_paths - paths):
            target = checkout / relative
            if target.is_file():
                target.unlink()
        run(["git", "add", "-A"], checkout)
        changed = run(["git", "diff", "--cached", "--name-status"], checkout)
        if not changed:
            state = {**previous, "last_check_utc": utc(), "state": "NO_CHANGE", "checked_files": len(paths)}
            write_status(state)
            return state
        # Validate the staged checkout; this never imports service.py or calls MT5.
        stage_paths = [checkout / p for p in run(["git", "ls-files"], checkout).splitlines()]
        findings = scan(stage_paths)
        if findings:
            raise RuntimeError(f"staged_secret_scan_blocked:{len(findings)}_files")
        run([sys.executable, "-m", "compileall", "-q", "research/demo-live-20261021", "tools", "tests"], checkout)
        run([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"], checkout)
        entries = changed.splitlines()
        summary = f"Validated source synchronization: {len(entries)} changed files"
        run(["git", "-c", "user.name=AA-AT Sync", "-c", "user.email=aa-at-sync@users.noreply.github.com",
             "commit", "-q", "-m", summary], checkout)
        sha = run(["git", "rev-parse", "HEAD"], checkout)
        run(["git", "push", "--quiet", "origin", f"HEAD:refs/heads/{BRANCH}"], checkout)
        pr = ensure_pr()
        state = {"last_check_utc": utc(), "state": "PUSHED_REVIEW_REQUIRED", "checked_files": len(paths),
                 "changed_files": len(entries), "change_summary": summary,
                 "last_pushed_sha": sha, "pull_request": pr,
                 "tests": "offline repository safety tests passed", "secret_scan": "passed",
                 "deployment": "none"}
        write_status(state)
        return state


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not args.once:
        parser.error("pass --once; schedule every four hours with Task Scheduler")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    delays = (0, 30, 120)
    for attempt, delay in enumerate(delays, 1):
        if delay:
            time.sleep(delay)
        try:
            state = once()
            print(json.dumps({k: state.get(k) for k in ("state", "changed_files", "last_pushed_sha", "pull_request")}))
            return 0
        except Exception as error:
            message = str(error)
            if message.startswith(("secret_scan_blocked", "staged_secret_scan_blocked", "automation_branch_changed")):
                write_status({"last_check_utc": utc(), "state": "BLOCKED", "error": message, "attempt": attempt})
                print(f"sync_blocked:{message}", file=sys.stderr)
                return 2
            write_status({"last_check_utc": utc(), "state": "RETRYING" if attempt < len(delays) else "FAILED",
                          "error": message, "attempt": attempt})
    print("sync_failed:see_local_status", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
