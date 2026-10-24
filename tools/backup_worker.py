"""Independent, non-disruptive AA-AT backup worker.

Only reads project files and SQLite online snapshots. It never imports the
trading service or connects to MetaTrader.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT_NAMES = (
    "AA-AT", "AA-AT-recovery-20261023", "AA-AT-dashboard-release-a5a338e",
    "AA-AT-dashboard-release-research-v1",
    "AA-AT-command-center-state", "AA-AT-sync-state", "AA-AT-deploy-backups",
    "AA-AT-research-state", "AA-AT-backup-release-v1", "AA-AT-research-release-v1",
    "research", "research_outputs", "strategy_research_input", "trading-journal",
    "meta-trader-mcp", "graphify-out",
)
SKIP_DIRS = frozenset(("__pycache__", ".venv", "venv", "node_modules",
                       ".pytest_cache", ".mypy_cache"))
TASKS = ("CodexDemoForward20261021", "AAATCommandCenter", "AAATGitHubSync4h")
PERIOD = timedelta(hours=24)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def atomic_json(path: Path, value: dict) -> None:
    temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def source_files(workspace: Path, names: tuple[str, ...] = ROOT_NAMES):
    for name in names:
        root = workspace / name
        if not root.is_dir():
            raise RuntimeError(f"required_backup_root_missing:{root}")
        for current, directories, filenames in os.walk(root):
            directories[:] = sorted(
                directory for directory in directories
                if directory not in SKIP_DIRS and
                not (Path(current) / directory).is_symlink()
            )
            for filename in sorted(filenames):
                path = Path(current) / filename
                if (path.is_symlink() or path.suffix.lower() in {".pyc", ".pyo", ".lock"}
                        or filename.endswith(("-wal", "-shm"))):
                    continue
                yield path


def snapshot_database(path: Path, temporary_directory: Path) -> Path:
    destination = temporary_directory / (uuid.uuid4().hex + ".sqlite3")
    source = sqlite3.connect("file:" + path.as_posix() + "?mode=ro", uri=True, timeout=2)
    target = sqlite3.connect(destination)
    try:
        source.backup(target, pages=256, sleep=0.02)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError(f"database_integrity_failed:{path}")
    finally:
        target.close()
        source.close()
    return destination


def metadata(workspace: Path, names: tuple[str, ...]) -> dict:
    tasks = {}
    for name in TASKS:
        command = subprocess.run(
            ["schtasks", "/Query", "/TN", name, "/XML"],
            capture_output=True, text=True, timeout=10, check=False,
        )
        if command.returncode == 0:
            tasks[name] = command.stdout
    acls = {}
    for name in names:
        command = subprocess.run(
            ["icacls", str(workspace / name)],
            capture_output=True, text=True, timeout=10, check=False,
        )
        acls[name] = {"exit_code": command.returncode, "text": command.stdout}
    git = subprocess.run(
        ["git", "-C", str(workspace / "AA-AT"), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    return {"scheduled_tasks": tasks, "root_acls": acls,
            "git_commit": git.stdout.strip() if git.returncode == 0 else None}


def verify_campaign_refs(database: Path, archive: Path, workspace: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        records = [json.loads(row[0]) for row in
                   connection.execute("SELECT record_json FROM closed")]
    finally:
        connection.close()
    with zipfile.ZipFile(archive) as package:
        for record in records:
            for evidence in record.get("broker_evidence", []):
                source = Path(evidence["path"])
                try:
                    relative = source.relative_to(workspace)
                except ValueError as exc:
                    raise RuntimeError("external_broker_evidence_reference") from exc
                member = "source/" + relative.as_posix()
                try:
                    raw = package.read(member)
                except KeyError as exc:
                    raise RuntimeError(f"broker_evidence_missing:{member}") from exc
                if hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
                    raise RuntimeError(f"broker_evidence_hash_mismatch:{member}")
    return len(records)


def verify_research_refs(database: Path, archive: Path, workspace: Path) -> int:
    connection = sqlite3.connect(database)
    try:
        refs = connection.execute(
            "SELECT sha256,local_path FROM source_artifacts").fetchall()
    finally:
        connection.close()
    with zipfile.ZipFile(archive) as package:
        for expected, source in refs:
            try:
                relative = Path(source).relative_to(workspace)
            except ValueError as exc:
                raise RuntimeError("external_research_artifact_reference") from exc
            member = "source/" + relative.as_posix()
            try:
                raw = package.read(member)
            except KeyError as exc:
                raise RuntimeError(f"research_artifact_missing:{member}") from exc
            if hashlib.sha256(raw).hexdigest() != expected:
                raise RuntimeError(f"research_artifact_hash_mismatch:{member}")
    return len(refs)


def latest_success(destination: Path) -> tuple[int, datetime | None]:
    latest: tuple[int, datetime | None] = (0, None)
    for slot in (1, 2, 3):
        info = read_json(destination / f"AA-AT-Backup-V{slot}.manifest.json")
        archive = destination / f"AA-AT-Backup-V{slot}.zip"
        if info.get("status") != "SUCCESS" or not archive.is_file():
            continue
        try:
            when = datetime.fromisoformat(info["verified_utc"])
        except (KeyError, ValueError):
            continue
        if latest[1] is None or when > latest[1]:
            latest = slot, when
    return latest


def request_backup(destination: Path, key: str, actor: str) -> dict:
    if not 8 <= len(key) <= 128 or not all(c.isalnum() or c in "-_" for c in key):
        raise ValueError("invalid_idempotency_key")
    destination.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(destination / "backup-requests.sqlite3", timeout=2)
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS requests(
            id TEXT PRIMARY KEY, actor TEXT NOT NULL, requested_utc TEXT NOT NULL,
            state TEXT NOT NULL, finished_utc TEXT, detail TEXT)""")
        connection.execute(
            "INSERT OR IGNORE INTO requests(id,actor,requested_utc,state) VALUES (?,?,?,'PENDING')",
            (key, actor, utc()))
        connection.commit()
        row = connection.execute(
            "SELECT id,requested_utc,state,finished_utc,detail FROM requests WHERE id=?", (key,)
        ).fetchone()
        return dict(zip(("id", "requested_utc", "state", "finished_utc", "detail"), row))
    finally:
        connection.close()


def pending_request(destination: Path) -> str | None:
    path = destination / "backup-requests.sqlite3"
    if not path.exists():
        return None
    connection = sqlite3.connect(path, timeout=2)
    try:
        connection.execute("BEGIN IMMEDIATE")
        row = connection.execute(
            "SELECT id FROM requests WHERE state='PENDING' ORDER BY requested_utc LIMIT 1"
        ).fetchone()
        if row:
            connection.execute("UPDATE requests SET state='RUNNING' WHERE id=?", (row[0],))
        connection.commit()
        return row[0] if row else None
    finally:
        connection.close()


def finish_request(destination: Path, key: str, result: dict) -> None:
    connection = sqlite3.connect(destination / "backup-requests.sqlite3", timeout=2)
    try:
        connection.execute(
            "UPDATE requests SET state=?,finished_utc=?,detail=? WHERE id=?",
            (result["status"], utc(), json.dumps(result, separators=(",", ":"))[:1000], key))
        connection.commit()
    finally:
        connection.close()


def create_backup(workspace: Path, destination: Path,
                  names: tuple[str, ...] = ROOT_NAMES) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    prior, _ = latest_success(destination)
    slot = prior % 3 + 1
    final = destination / f"AA-AT-Backup-V{slot}.zip"
    temporary = destination / ("." + final.name + "." + uuid.uuid4().hex)
    files = list(source_files(workspace, names))
    size = sum(path.stat().st_size for path in files)
    if shutil.disk_usage(destination).free < size * 2 + 1024 ** 3:
        raise RuntimeError("insufficient_backup_storage")
    info = metadata(workspace, names)
    entries = []
    snapshotted = {}
    # Database snapshots are small and isolated; all other files stream into ZIP.
    with tempfile.TemporaryDirectory(prefix="aaat-db-snapshot-", dir=destination) as scratch:
        scratch_path = Path(scratch)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=6, allowZip64=True) as package:
            for source in files:
                member = "source/" + source.relative_to(workspace).as_posix()
                before = source.stat()
                data = snapshot_database(source, scratch_path) if source.suffix.lower() == ".sqlite3" else source
                package.write(data, member)
                after = source.stat()
                if source.suffix.lower() != ".sqlite3" and (
                    before.st_size != after.st_size or before.st_mtime_ns != after.st_mtime_ns
                ):
                    raise RuntimeError(f"source_changed_during_backup:{source}")
                entries.append({"path": source.relative_to(workspace).as_posix(),
                                "bytes": data.stat().st_size, "sha256": sha256(data),
                                "method": "sqlite_online_backup" if data != source else "copied"})
                if source.name == "campaign.sqlite3" and "demo-live-20261021" in source.parts:
                    snapshotted["campaign"] = data
                if source.name == "research.sqlite3" and "AA-AT-research-state" in source.parts:
                    snapshotted["research"] = data
            manifest = {
                "schema_version": 1, "created_utc": utc(), "slot": f"V{slot}",
                "encrypted": False, "roots": names, "source_checkpoint": "AA-AT/CHECKPOINT.json",
                "git_commit": info["git_commit"], "file_count": len(entries),
                "exclusions": ["generated caches/dependencies", "*.lock", "*.pyc",
                               "SQLite WAL/SHM replaced by online snapshots"],
                "entries": entries,
            }
            package.writestr("metadata/scheduled_tasks.json",
                             json.dumps(info["scheduled_tasks"]))
            package.writestr("metadata/root_acl.json", json.dumps(info["root_acls"]))
            package.writestr("manifest.json", json.dumps(manifest, separators=(",", ":")))
        with zipfile.ZipFile(temporary) as package:
            bad = package.testzip()
            if bad is not None:
                raise RuntimeError(f"zip_crc_failed:{bad}")
            if json.loads(package.read("manifest.json"))["file_count"] != len(entries):
                raise RuntimeError("backup_manifest_mismatch")
            for entry in entries:
                member = "source/" + entry["path"]
                if hashlib.sha256(package.read(member)).hexdigest() != entry["sha256"]:
                    raise RuntimeError(f"archive_hash_mismatch:{member}")
        if "campaign" not in snapshotted:
            raise RuntimeError("campaign_snapshot_missing")
        closed = verify_campaign_refs(snapshotted["campaign"], temporary, workspace)
        research_artifacts = (verify_research_refs(
            snapshotted["research"], temporary, workspace)
            if "research" in snapshotted else None)
    digest = sha256(temporary)
    result = {
        "status": "SUCCESS", "slot": f"V{slot}", "verified_utc": utc(),
        "archive_bytes": temporary.stat().st_size, "sha256": digest,
        "file_count": len(entries), "closed_trades": closed,
        "research_artifacts": research_artifacts,
        "git_commit": info["git_commit"],
    }
    # Replacement occurs only after all checks, preserving a valid previous slot on failure.
    os.replace(temporary, final)
    atomic_json(destination / f"AA-AT-Backup-V{slot}.manifest.json", result)
    (destination / f"AA-AT-Backup-V{slot}.sha256").write_text(
        digest + "  " + final.name + "\n", encoding="ascii")
    atomic_json(destination / "backup-status.json",
                {**result, "next_due_utc": (datetime.fromisoformat(result["verified_utc"])
                                             + PERIOD).isoformat()})
    return result


def run_forever(workspace: Path, destination: Path) -> None:
    import msvcrt
    destination.mkdir(parents=True, exist_ok=True)
    lock = (destination / "backup-worker.lock").open("a+b")
    try:
        lock.seek(0)
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError as exc:
        lock.close()
        raise RuntimeError("backup_worker_already_running") from exc
    failures = 0
    while True:
        _, last = latest_success(destination)
        request = pending_request(destination)
        atomic_json(destination / "backup-heartbeat.json", {
            "status": "RUNNING", "observed_utc": utc(),
            "last_success_utc": last.isoformat() if last else None,
            "next_due_utc": (last + PERIOD).isoformat() if last else None,
            "pending_manual_request": bool(request),
        })
        if request or last is None or datetime.now(timezone.utc) >= last + PERIOD:
            try:
                result = create_backup(workspace, destination)
                if request:
                    finish_request(destination, request, result)
                failures = 0
            except Exception as exc:
                failures += 1
                if request:
                    finish_request(destination, request,
                                   {"status": "FAILED", "error": str(exc)[:240]})
                atomic_json(destination / "backup-status.json",
                            {"status": "FAILED", "observed_utc": utc(),
                             "error": str(exc)[:240], "attempt": failures})
                time.sleep(min(6 * 3600, 15 * 60 * 2 ** min(failures - 1, 5)))
                continue
        time.sleep(60)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, default=Path(r"E:\GPT\Inves"))
    parser.add_argument("--destination", type=Path, default=Path(r"D:\AA-AT-Backups"))
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--serve", action="store_true")
    args = parser.parse_args()
    if args.once == args.serve:
        parser.error("choose --once or --serve")
    if args.once:
        print(json.dumps(create_backup(args.workspace, args.destination)))
    else:
        run_forever(args.workspace, args.destination)


if __name__ == "__main__":
    main()
