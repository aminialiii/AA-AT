"""Fail-closed pre-commit scan for secrets and broker account identifiers."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "account_assignment": re.compile(rb"(?i)(?:account[_-]?(?:number|login)|login)\s*[:=]\s*[\"']?\d{6,12}\b"),
    "private_key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(rb"\b(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_)[A-Za-z0-9_]{12,}"),
    "cloud_key": re.compile(rb"\bAKIA[0-9A-Z]{16}\b"),
    "password_assignment": re.compile(rb"(?i)(?:password|client_secret|api_key|access_token)\s*[:=]\s*[\"'](?!\$\{|\$|<|your_|example|change_me|\s*[\"'])[A-Za-z0-9+/_=-]{8,}"),
}


def protected_account_ids():
    """Read exact account IDs from local-only state, never from tracked source."""
    configured = os.environ.get("AAAT_SECRET_SCAN_DENYLIST")
    path = Path(configured) if configured else ROOT.parent / "AA-AT-sync-state" / "protected_account_ids.txt"
    if not path.is_file():
        if configured:
            raise RuntimeError("configured_secret_scan_denylist_missing")
        return []
    values = [line.strip().encode("ascii") for line in path.read_text(encoding="ascii").splitlines()
              if line.strip() and not line.lstrip().startswith("#")]
    if any(not re.fullmatch(rb"\d{6,12}", value) for value in values):
        raise RuntimeError("invalid_secret_scan_denylist")
    return values


def tracked_paths():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    return [ROOT / p.decode("utf-8") for p in result.stdout.split(b"\0") if p]


def scan(paths):
    findings = []
    protected = protected_account_ids()
    for path in paths:
        if not path.is_file():
            continue
        data = path.read_bytes()
        if b"\0" in data or len(data) > 8_000_000:
            findings.append((path, "binary_or_oversized"))
            continue
        for label, pattern in PATTERNS.items():
            if pattern.search(data):
                findings.append((path, label))
        if any(re.search(rb"(?<!\d)" + value + rb"(?!\d)", data) for value in protected):
            findings.append((path, "protected_account_id"))
    return findings


if __name__ == "__main__":
    paths = tracked_paths() if len(sys.argv) == 1 else [Path(p).resolve() for p in sys.argv[1:]]
    findings = scan(paths)
    for path, label in findings:
        print(f"BLOCK {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}: {label}")
    print(f"scanned={len(paths)} findings={len(findings)}")
    raise SystemExit(1 if findings else 0)
