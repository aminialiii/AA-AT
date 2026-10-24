"""Copy selected MT5 cache files without connecting to the terminal.

Opaque .hcc/.tkc bytes do not establish historical coverage. A separately
validated offline exporter is required before they become market observations.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .priority3 import sha256_file

SYMBOLS = ("AUDUSD", "EURUSD", "GBPUSD", "USDCAD", "USDCHF", "USDJPY")
DEFAULT_CACHE = Path(
    r"C:\Users\SOC-Peyman\AppData\Roaming\MetaQuotes\Terminal"
    r"\D0E8209F77C8CF37AD8BF550E51FF075\bases\MetaQuotes-Demo")
DEFAULT_STATE = Path(r"E:\GPT\Inves\AA-AT-research-state")


def snapshot(cache: Path, state: Path, *, year: int = 2026,
             month: int = 10, symbols: tuple[str, ...] = SYMBOLS) -> dict:
    if not 1 <= month <= 12 or not 2000 <= year <= 2100:
        raise ValueError("invalid_cache_period")
    root = state / "broker_cache_snapshots"
    root.mkdir(parents=True, exist_ok=True)
    identifier = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    target = root / identifier
    target.mkdir()
    entries = []
    try:
        for symbol in symbols:
            if not symbol.isascii() or not symbol.isalnum():
                raise ValueError("invalid_symbol")
            for kind, name in (("ticks", f"{year}{month:02d}.tkc"),
                               ("history", f"{year}.hcc")):
                source = cache / kind / symbol / name
                if not source.is_file():
                    entries.append({"symbol": symbol, "kind": kind,
                                    "file": name, "status": "MISSING",
                                    "coverage": "UNVERIFIED"})
                    continue
                before = source.stat()
                destination = target / kind / symbol / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                temporary = destination.with_name("." + name + ".tmp")
                shutil.copyfile(source, temporary)
                after = source.stat()
                if (before.st_size != after.st_size or
                        before.st_mtime_ns != after.st_mtime_ns or
                        temporary.stat().st_size != before.st_size or
                        sha256_file(temporary) != sha256_file(source)):
                    raise RuntimeError("cache_changed_during_snapshot:" + symbol + ":" + kind)
                os.replace(temporary, destination)
                entries.append({"symbol": symbol, "kind": kind,
                                "file": name, "status": "COPIED",
                                "bytes": before.st_size,
                                "sha256": sha256_file(destination),
                                "source_modified_utc": datetime.fromtimestamp(
                                    before.st_mtime, timezone.utc).isoformat(),
                                "coverage": "UNVERIFIED"})
        manifest = {
            "schema_version": 1, "snapshot_utc": datetime.now(timezone.utc).isoformat(),
            "source": "LOCAL_MT5_CACHE_OPAQUE_FILES",
            "source_root": str(cache), "terminal_queried": False,
            "broker_trade_or_quote_api_called": False,
            "historical_coverage": "UNVERIFIED",
            "offline_export_status": "NO_SUPPORTED_OFFLINE_EXPORTER_VERIFIED",
            "files": entries,
        }
        (target / "manifest.json").write_text(json.dumps(manifest, indent=2),
                                                encoding="utf-8")
        return {"snapshot": str(target), "copied": sum(
            item["status"] == "COPIED" for item in entries),
            "missing": sum(item["status"] == "MISSING" for item in entries),
            "bytes": sum(item.get("bytes", 0) for item in entries),
            "historical_coverage": "UNVERIFIED"}
    except Exception:
        # Preserve the failed partial snapshot for inspection; no manifest
        # means it must never be used as a verified data source.
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=10)
    args = parser.parse_args()
    print(json.dumps(snapshot(args.cache, args.state, year=args.year, month=args.month)))


if __name__ == "__main__":
    main()
