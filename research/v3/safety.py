"""Read-only production-integrity observations for isolated research phases.

This module never imports broker or trading-service code. It writes only its
own report path, supplied explicitly by the research runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"E:\GPT\Inves")
STRATEGY_INVENTORY = ROOT / "research_outputs" / "inventory.json"
RUNTIME = ROOT / "research" / "demo-live-20261021" / "runtime"
PROTECTED = (
    ROOT / "research" / "demo-live-20261021" / "service.py",
    ROOT / "research" / "demo-live-20261021" / "risk_policy.json",
    ROOT / "research" / "demo-live-20261021" / "campaign_config.json",
)
TASKS = ("CodexDemoForward20261021", "aa-at-backup-worker",
         "AAATGitHubSync4h", "AAATCommandCenter")
PRODUCTION_META = Path(r"C:\Users\SOC-Peyman\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075")
RESEARCH_META = Path(r"C:\Users\SOC-Peyman\AppData\Roaming\MetaQuotes\Terminal\A7806C9494F93E37A61F4174F2E3283B")
RESEARCH_TERMINAL_DIR = Path(r"E:\GPT\Inves\AA-AT-v3-market-vault\mt5-portable")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def _powershell_json(source: str):
    process = subprocess.run(
        ["pwsh", "-NoProfile", "-NonInteractive", "-Command", source],
        capture_output=True, text=True, timeout=20, check=True)
    return json.loads(process.stdout)


def _task(name: str) -> dict:
    # Only the digest leaves PowerShell; task XML may contain local user names.
    script = ("$t=Get-ScheduledTask -TaskName '" + name + "' -ErrorAction Stop; "
              "$x=Export-ScheduledTask -TaskName '" + name + "'; "
              "$h=[Security.Cryptography.SHA256]::HashData([Text.Encoding]::UTF8.GetBytes($x)); "
              "@{xml_sha256=[Convert]::ToHexString($h).ToLowerInvariant(); "
              "enabled=$t.Settings.Enabled; state=[string]$t.State} | ConvertTo-Json -Compress")
    return _powershell_json(script)


def _terminal() -> list[dict]:
    processes = _powershell_json(
        "@((Get-CimInstance Win32_Process -Filter \"name = 'terminal64.exe'\" | "
        "ForEach-Object {@{id=$_.ProcessId;path=$_.ExecutablePath}})) | ConvertTo-Json -Compress") or []
    if isinstance(processes, dict):
        processes = [processes]
    protected_path = str(Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")).lower()
    return [row for row in processes if str(row.get("path", "")).lower() == protected_path]


def _ledger() -> dict:
    path = RUNTIME / "campaign.sqlite3"
    db = sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True, timeout=3)
    try:
        return {
            "integrity": db.execute("PRAGMA integrity_check").fetchone()[0],
            "closed_count": db.execute("SELECT COUNT(*) FROM closed").fetchone()[0],
            "safety_event_count": db.execute("SELECT COUNT(*) FROM safety_events").fetchone()[0],
        }
    finally:
        db.close()


def _metadata_file(path: Path) -> dict:
    if not path.is_file():
        return {"present": False}
    return {"present": True, "sha256": sha256(path),
            "mtime_ns": path.stat().st_mtime_ns}


def _terminal_metadata() -> dict:
    # The terminal itself can update its own config independently of research.
    # Record those observations, and compare stable origin/account/server files.
    protected = {name: _metadata_file(PRODUCTION_META / name) for name in
                 ("origin.txt", "config/accounts.dat", "config/servers.dat")}
    origin = RESEARCH_META / "origin.txt"
    research_origin = None
    if origin.is_file():
        raw = origin.read_bytes()
        encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
        research_origin = raw.decode(encoding).strip()
    return {"production": protected,
            "research_metadata_path": str(RESEARCH_META),
            "research_origin_matches_vault":
                research_origin is None or Path(research_origin).resolve() == RESEARCH_TERMINAL_DIR.resolve(),
            "research_accounts_file_present": (RESEARCH_META / "config/accounts.dat").is_file(),
            "production_terminal_ini": _metadata_file(PRODUCTION_META / "config/terminal.ini")}


def snapshot() -> dict:
    inventory = json.loads(STRATEGY_INVENTORY.read_text(encoding="utf-8"))
    sources = {}
    for item in inventory["strategies"]:
        path = ROOT / item["source_file"]
        digest = sha256(path) if path.is_file() else None
        sources[item["strategy_id"]] = {"sha256": digest,
            "frozen_sha256": item["sourceSHA256"], "matches_frozen": digest == item["sourceSHA256"]}
    files = {}
    for path in PROTECTED:
        files[path.relative_to(ROOT).as_posix()] = (
            {"sha256": sha256(path), "mtime_ns": path.stat().st_mtime_ns} if path.is_file()
            else {"missing": True})
    marker = RUNTIME / "EMERGENCY_STOP"
    return {
        "observed_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_sources": sources,
        "protected_files": files,
        "tasks": {name: _task(name) for name in TASKS},
        "terminal_processes": _terminal(),
        "production_terminal_exe": str(Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")),
        "terminal_metadata": _terminal_metadata(),
        "emergency_stop": {"present": marker.is_file(),
                           "sha256": sha256(marker) if marker.is_file() else None},
        "ledger": _ledger(),
    }


def compare(before: dict, after: dict) -> list[str]:
    failures = []
    for key in ("strategy_sources", "protected_files", "emergency_stop"):
        if before[key] != after[key]:
            failures.append(key + "_changed")
    for name in TASKS:
        for field in ("xml_sha256", "enabled", "state"):
            if before["tasks"][name][field] != after["tasks"][name][field]:
                failures.append(f"task_{name}_{field}_changed")
    old_metadata = before.get("terminal_metadata")
    new_metadata = after.get("terminal_metadata")
    if new_metadata:
        if not new_metadata["research_origin_matches_vault"]:
            failures.append("research_terminal_metadata_origin_mismatch")
        if new_metadata["research_accounts_file_present"]:
            failures.append("research_terminal_has_account_file")
    if old_metadata and new_metadata and old_metadata["production"] != new_metadata["production"]:
        failures.append("production_terminal_identity_files_changed")
    old_processes = before["terminal_processes"]
    new_processes = after["terminal_processes"]
    if isinstance(old_processes, dict):
        old_processes = [old_processes]
    if isinstance(new_processes, dict):
        new_processes = [new_processes]
    if old_processes != new_processes:
        failures.append("production_terminal_process_changed")
    if after["ledger"]["integrity"] != "ok":
        failures.append("production_ledger_integrity_failure")
    if after["ledger"]["closed_count"] < before["ledger"]["closed_count"]:
        failures.append("production_closed_count_decreased")
    # A running broker campaign may append legitimate closes and safety events.
    return failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--before", type=Path)
    args = parser.parse_args()
    observation = snapshot()
    result = {"observation": observation}
    if args.before:
        prior = json.loads(args.before.read_text(encoding="utf-8"))["observation"]
        result["unexpected_changes"] = compare(prior, observation)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sources_ok": all(
        row["matches_frozen"] for row in observation["strategy_sources"].values()),
        "ledger_integrity": observation["ledger"]["integrity"],
        "unexpected_changes": result.get("unexpected_changes", [])}))
    if result.get("unexpected_changes"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
