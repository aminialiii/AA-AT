"""Validate the committed command-center shell during 4-hour sync.

Live account telemetry is served only from the local authenticated backend.
The old builder overwrote docs/dashboard.html with a stale static snapshot;
that would erase the interactive application on every synchronization.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    files = (ROOT / "docs/dashboard.html", ROOT / "docs/assets/app.css",
             ROOT / "docs/assets/app.js")
    for path in files:
        if not path.is_file() or path.stat().st_size < 100:
            raise RuntimeError(f"dashboard_asset_missing_or_empty:{path.name}")
    html = files[0].read_text(encoding="utf-8")
    if "Trading Command Center" not in html or "/assets/app.js" not in html:
        raise RuntimeError("interactive_dashboard_shell_invalid")
    print(json.dumps({"dashboard": str(files[0]), "kind": "authenticated_live_shell",
                      "assets_checked": len(files)}))


if __name__ == "__main__":
    main()
