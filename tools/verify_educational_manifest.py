"""Verify all 32 educational source files without reading or executing rules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "strategy_research_input"


def main():
    manifest = json.loads((ROOT / "SOURCE_SHA256_MANIFEST.json").read_text(encoding="utf-8"))
    if manifest["file_count"] != 32 or len(manifest["files"]) != 32:
        raise RuntimeError("educational_manifest_count_mismatch")
    for item in manifest["files"]:
        relative = Path(item["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError("invalid_manifest_path")
        path = ROOT / relative
        data = path.read_bytes()
        if len(data) != item["size_bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise RuntimeError(f"educational_source_mismatch:{relative}")
    print("educational_manifest_verified=32")


if __name__ == "__main__":
    main()
