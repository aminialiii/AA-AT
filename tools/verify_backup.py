"""Read-only isolated restore drill for a verified AA-AT ZIP slot."""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import tempfile
import zipfile
from pathlib import Path


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(archive: Path, *, full: bool = True) -> dict:
    sidecar = archive.with_suffix(".manifest.json")
    info = json.loads(sidecar.read_text(encoding="utf-8"))
    archive_hash = hashlib.sha256()
    with archive.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            archive_hash.update(block)
    if archive_hash.hexdigest() != info["sha256"]:
        raise RuntimeError("archive_sha256_mismatch")
    restored = []
    with zipfile.ZipFile(archive) as package, tempfile.TemporaryDirectory(
            prefix="aaat-restore-drill-") as scratch:
        if package.testzip() is not None:
            raise RuntimeError("zip_crc_failed")
        manifest = json.loads(package.read("manifest.json"))
        if manifest["file_count"] != len(manifest["entries"]):
            raise RuntimeError("manifest_entry_count_mismatch")
        for entry in manifest["entries"]:
            member = "source/" + entry["path"]
            sqlite_snapshot = entry["method"] in {"sqlite_online_backup", "online_sqlite_snapshot"}
            if not full and not sqlite_snapshot:
                continue
            raw = package.read(member)
            if digest(raw) != entry["sha256"]:
                raise RuntimeError("member_sha256_mismatch:" + member)
            if sqlite_snapshot:
                # WAL-mode SQLite images cannot always be deserialized in
                # memory. Extract into a separate temporary directory; never
                # point this tool at the trading or research runtime.
                extracted = Path(scratch) / (str(len(restored)) + ".sqlite3")
                extracted.write_bytes(raw)
                connection = sqlite3.connect("file:" + extracted.as_posix() + "?mode=ro",
                                             uri=True)
                try:
                    if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise RuntimeError("sqlite_restore_integrity_failed:" + member)
                    restored.append(member)
                finally:
                    connection.close()
    return {"status": "SUCCESS", "archive": str(archive),
            "sha256": archive_hash.hexdigest(),
            "validated_members": len(manifest["entries"]) if full else len(restored),
            "isolated_sqlite_restores": restored}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sqlite-only", action="store_true")
    args = parser.parse_args()
    print(json.dumps(verify(args.archive, full=not args.sqlite_only)))
