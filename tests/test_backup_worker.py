import hashlib
import json
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from tools.backup_worker import create_backup, latest_success, request_backup


class BackupWorkerTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.workspace = base / "workspace"
        self.destination = base / "backups"
        self.workspace.mkdir()
        (self.workspace / "AA-AT").mkdir()
        live = self.workspace / "research" / "demo-live-20261021" / "runtime"
        evidence = live / "evidence" / "S01"
        evidence.mkdir(parents=True)
        raw = b'{"kind":"BROKER_DEAL","payload":{"ticket":1}}\n'
        source = evidence / "one.json"
        source.write_bytes(raw)
        database = live / "campaign.sqlite3"
        connection = sqlite3.connect(database)
        connection.execute("CREATE TABLE closed(record_json TEXT NOT NULL)")
        connection.execute("INSERT INTO closed VALUES (?)", (json.dumps({
            "broker_evidence": [{"path": str(source),
                                 "sha256": hashlib.sha256(raw).hexdigest()}]
        }),))
        connection.commit()
        connection.close()
        (self.workspace / "AA-AT" / "README.md").write_text("source", encoding="utf-8")
        self.meta = patch("tools.backup_worker.metadata", return_value={
            "scheduled_tasks": {}, "root_acls": {}, "git_commit": "a" * 40
        })
        self.meta.start()
        self.addCleanup(self.meta.stop)

    def test_three_slot_rotation_and_integrity(self):
        results = [create_backup(self.workspace, self.destination,
                                 ("AA-AT", "research")) for _ in range(4)]
        self.assertEqual([x["slot"] for x in results], ["V1", "V2", "V3", "V1"])
        self.assertEqual(latest_success(self.destination)[0], 1)
        for number in (1, 2, 3):
            archive = self.destination / f"AA-AT-Backup-V{number}.zip"
            with zipfile.ZipFile(archive) as package:
                self.assertIsNone(package.testzip())
                self.assertIn("manifest.json", package.namelist())

    def test_failed_replacement_keeps_prior_slot(self):
        for _ in range(3):
            create_backup(self.workspace, self.destination, ("AA-AT", "research"))
        prior = (self.destination / "AA-AT-Backup-V1.zip").read_bytes()
        with patch("tools.backup_worker.verify_campaign_refs",
                   side_effect=RuntimeError("bad_evidence")):
            with self.assertRaisesRegex(RuntimeError, "bad_evidence"):
                create_backup(self.workspace, self.destination, ("AA-AT", "research"))
        self.assertEqual((self.destination / "AA-AT-Backup-V1.zip").read_bytes(), prior)

    def test_manual_request_is_idempotent(self):
        first = request_backup(self.destination, "request-12345678", "admin")
        second = request_backup(self.destination, "request-12345678", "admin")
        self.assertEqual(first, second)

    def test_research_snapshot_requires_its_immutable_raw_artifacts(self):
        state = self.workspace / "AA-AT-research-state"
        raw = state / "raw" / "trade.json"
        raw.parent.mkdir(parents=True)
        raw.write_bytes(b'{"trade":"fixture"}')
        connection = sqlite3.connect(state / "research.sqlite3")
        connection.execute("CREATE TABLE source_artifacts(sha256 TEXT,local_path TEXT)")
        connection.execute("INSERT INTO source_artifacts VALUES (?,?)",
                           (hashlib.sha256(raw.read_bytes()).hexdigest(), str(raw)))
        connection.commit()
        connection.close()
        roots = ("AA-AT", "research", "AA-AT-research-state")
        first = create_backup(self.workspace, self.destination, roots)
        self.assertEqual(first["research_artifacts"], 1)
        raw.write_bytes(b'{"trade":"changed"}')
        with self.assertRaisesRegex(RuntimeError, "research_artifact_hash_mismatch"):
            create_backup(self.workspace, self.destination, roots)
        self.assertEqual(latest_success(self.destination)[0], 1)


if __name__ == "__main__":
    unittest.main()
