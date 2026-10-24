"""Portable, redacted research report package; no broker records are rewritten."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .priority3 import DEFAULT_STATE, sha256_file


def export(state: Path = DEFAULT_STATE) -> dict:
    pointer = json.loads((state / "analytics" / "latest.json").read_text(encoding="utf-8"))
    run_id = pointer["analysis_run_id"]
    if len(run_id) != 20 or any(c not in "0123456789abcdef" for c in run_id):
        raise ValueError("invalid_analysis_run_id")
    run_dir = state / "analytics" / "runs" / run_id
    files = {
        "analytics/priority3.json": run_dir / "priority3.json",
        "analytics/strategy_versions.csv": run_dir / "strategy_versions.csv",
    }
    for path in files.values():
        if not path.is_file():
            raise FileNotFoundError("analytics_package_source_missing:" + path.name)
    payloads = {name: path.read_bytes() for name, path in files.items()}
    cache_root = state / "broker_cache_snapshots"
    if cache_root.is_dir():
        manifests = sorted(cache_root.glob("*/manifest.json"))
        if manifests:
            original = json.loads(manifests[-1].read_text(encoding="utf-8"))
            safe = {"snapshot_utc": original.get("snapshot_utc"),
                    "source": original.get("source"),
                    "historical_coverage": "UNVERIFIED",
                    "files": [{key: row.get(key) for key in (
                        "symbol", "kind", "file", "status", "bytes", "sha256", "coverage")}
                              for row in original.get("files", [])]}
            payloads["analytics/opaque_cache_manifest.json"] = json.dumps(
                safe, indent=2).encode()
    report = json.loads(files["analytics/priority3.json"].read_text(encoding="utf-8"))
    if report.get("analysis_run_id") != run_id or report.get("evidence_class") != "BROKER_ACTUAL":
        raise RuntimeError("analysis_report_provenance_invalid")
    output = state / "exports"
    output.mkdir(parents=True, exist_ok=True)
    final = output / "AA-AT-STRATEGY-ANALYTICS.zip"
    temporary = output / ("." + final.name + "." + uuid.uuid4().hex)
    readme = ("AA AT strategy analytics\n\n"
              "This archive contains versioned descriptive broker-actual aggregates, "
              "not trade fills or simulated outcomes. Market-cache metadata is opaque "
              "and does not prove price coverage. The full redacted trade journal is "
              "a separate AA-AT-RESEARCH-DATASET.zip export.\n\n"
              "Python: import json, zipfile; z=zipfile.ZipFile('AA-AT-STRATEGY-ANALYTICS.zip'); "
              "report=json.loads(z.read('analytics/priority3.json'))\n"
              "pandas: import pandas as pd; import io; "
              "pd.read_csv(io.BytesIO(z.read('analytics/strategy_versions.csv')))\n")
    manifest = {
        "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_run_id": run_id, "evidence_class": "BROKER_ACTUAL",
        "broker_reconciled_lifecycles": report["cutoff"]["broker_reconciled_lifecycles"],
        "entries": {name: hashlib.sha256(raw).hexdigest()
                    for name, raw in payloads.items()},
        "account_identifiers_included": False,
        "broker_tick_coverage_verified": False,
    }
    with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for name, raw in payloads.items():
            package.writestr(name, raw)
        package.writestr("README.txt", readme)
        package.writestr("manifest.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(temporary) as package:
        if package.testzip() is not None:
            raise RuntimeError("analytics_export_crc_failed")
        for name, digest in manifest["entries"].items():
            if hashlib.sha256(package.read(name)).hexdigest() != digest:
                raise RuntimeError("analytics_export_member_hash_mismatch")
    digest = sha256_file(temporary)
    os.replace(temporary, final)
    final.with_suffix(".sha256").write_text(digest + "  " + final.name + "\n",
                                                 encoding="ascii")
    return {"archive": str(final), "sha256": digest,
            "analysis_run_id": run_id, "entries": len(manifest["entries"]) + 2}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    args = parser.parse_args()
    print(json.dumps(export(args.state)))


if __name__ == "__main__":
    main()
