"""Import recorded broker market data; never query the active terminal."""
from __future__ import annotations

import argparse
import csv
import hashlib
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .store import Warehouse, utc

TIMEFRAMES = {"M1", "M3", "M5", "M15", "M30", "H1", "H4", "D1"}
SOURCE_TYPES = {"BROKER_EXPORT", "ARCHIVED_RESEARCH"}


def utc_time(raw: str) -> str:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("market_timestamp_must_have_timezone")
    return value.astimezone(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def import_csv(warehouse: Warehouse, path: Path, *, kind: str, symbol: str,
               timeframe: str | None, source_type: str) -> dict:
    if source_type not in SOURCE_TYPES or kind not in {"bars", "ticks"}:
        raise ValueError("unsupported_market_source")
    if kind == "bars" and timeframe not in TIMEFRAMES:
        raise ValueError("unsupported_timeframe")
    if kind == "ticks" and timeframe is not None:
        raise ValueError("ticks_have_no_timeframe")
    if not symbol or not symbol.isascii() or len(symbol) > 32:
        raise ValueError("invalid_symbol")
    source_hash = sha256(path)
    existing = warehouse.db.execute(
        "SELECT row_count FROM market_sources WHERE sha256=?", (source_hash,)).fetchone()
    if existing:
        return {"source_sha256": source_hash, "new_rows": 0,
                "source_rows": existing[0], "status": "ALREADY_IMPORTED"}
    raw_destination = warehouse.raw / "market" / (source_hash + ".csv")
    raw_destination.parent.mkdir(exist_ok=True)
    temporary = raw_destination.with_name("." + raw_destination.name + "." + uuid.uuid4().hex)
    shutil.copyfile(path, temporary)
    if sha256(temporary) != source_hash:
        raise RuntimeError("market_source_changed_during_copy")
    os.replace(temporary, raw_destination)
    rows = []
    previous = None
    with raw_destination.open("r", newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        required = ({"time_utc", "open", "high", "low", "close"} if kind == "bars"
                    else {"time_utc", "bid", "ask"})
        if not required.issubset(set(reader.fieldnames or [])):
            raise ValueError("market_csv_missing_required_columns")
        for source in reader:
            when = utc_time(source["time_utc"])
            if previous is not None and (
                when < previous or (kind == "bars" and when == previous)
            ):
                raise ValueError("market_timestamps_not_strictly_increasing")
            previous = when
            if kind == "bars":
                o, h, l, c = [float(source[field]) for field in ("open", "high", "low", "close")]
                if l <= 0 or h < max(o, c, l) or l > min(o, c):
                    raise ValueError("invalid_ohlc")
                rows.append((source_hash, symbol, timeframe, when, o, h, l, c,
                             float(source["tick_volume"]) if source.get("tick_volume") else None,
                             float(source["real_volume"]) if source.get("real_volume") else None,
                             float(source["spread_points"]) if source.get("spread_points") else None))
            else:
                bid, ask = float(source["bid"]), float(source["ask"])
                if bid <= 0 or ask < bid:
                    raise ValueError("invalid_bid_ask")
                rows.append((source_hash, symbol, when, bid, ask,
                             float(source["volume"]) if source.get("volume") else None))
    if not rows:
        raise ValueError("empty_market_export")
    try:
        warehouse.db.execute("BEGIN IMMEDIATE")
        if kind == "bars":
            warehouse.db.executemany(
                "INSERT INTO market_bars VALUES (?,?,?,?,?,?,?,?,?,?,?)", rows)
        else:
            warehouse.db.executemany(
                "INSERT OR IGNORE INTO market_ticks VALUES (?,?,?,?,?,?)", rows)
        warehouse.db.execute(
            "INSERT INTO market_sources VALUES (?,?,?,?,?,?,?,NULL)",
            (source_hash, source_type, str(path), utc(), symbol, timeframe, len(rows)))
        warehouse.db.commit()
    except Exception:
        warehouse.db.rollback()
        raise
    return {"source_sha256": source_hash, "new_rows": len(rows),
            "source_rows": len(rows), "status": "IMPORTED"}


def derive_m3(warehouse: Warehouse, source_sha256: str, symbol: str) -> dict:
    source = warehouse.db.execute(
        "SELECT source_type FROM market_sources WHERE sha256=? AND symbol=? AND timeframe='M1'",
        (source_sha256, symbol)).fetchone()
    if not source:
        raise ValueError("verified_m1_source_required")
    derived_id = hashlib.sha256(("M3|" + source_sha256).encode()).hexdigest()
    if warehouse.db.execute(
        "SELECT 1 FROM market_sources WHERE sha256=?", (derived_id,)).fetchone():
        return {"source_sha256": derived_id, "new_rows": 0, "status": "ALREADY_DERIVED"}
    rows = warehouse.db.execute(
        """SELECT open_utc,open,high,low,close,tick_volume,real_volume,spread_points
           FROM market_bars WHERE source_sha256=? AND symbol=? AND timeframe='M1'
           ORDER BY open_utc""", (source_sha256, symbol)).fetchall()
    groups = {}
    for row in rows:
        moment = datetime.fromisoformat(row["open_utc"])
        bucket = moment.replace(minute=moment.minute - moment.minute % 3, second=0,
                                microsecond=0).isoformat()
        groups.setdefault(bucket, []).append(row)
    derived = []
    for bucket, bars in groups.items():
        if len(bars) != 3:
            continue
        timestamps = [datetime.fromisoformat(bar["open_utc"]) for bar in bars]
        if any((timestamps[index+1] - timestamps[index]).total_seconds() != 60
               for index in (0, 1)):
            continue
        derived.append((derived_id, symbol, "M3", bucket, bars[0]["open"],
                        max(bar["high"] for bar in bars), min(bar["low"] for bar in bars),
                        bars[-1]["close"],
                        sum(bar["tick_volume"] or 0 for bar in bars),
                        sum(bar["real_volume"] or 0 for bar in bars),
                        max((bar["spread_points"] or 0) for bar in bars)))
    warehouse.db.execute("BEGIN IMMEDIATE")
    try:
        warehouse.db.executemany(
            "INSERT INTO market_bars VALUES (?,?,?,?,?,?,?,?,?,?,?)", derived)
        warehouse.db.execute(
            "INSERT INTO market_sources VALUES (?,?,?,?,?,?,?,?)",
            (derived_id, "DERIVED_M1", "derived:" + source_sha256, utc(), symbol,
             "M3", len(derived), source_sha256))
        warehouse.db.commit()
    except Exception:
        warehouse.db.rollback()
        raise
    return {"source_sha256": derived_id, "new_rows": len(derived),
            "source_rows": len(rows), "status": "DERIVED"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path)
    parser.add_argument("--state", type=Path,
                        default=Path(r"E:\GPT\Inves\AA-AT-research-state"))
    parser.add_argument("--kind", choices=("bars", "ticks"), required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--timeframe", choices=sorted(TIMEFRAMES))
    parser.add_argument("--source-type", choices=sorted(SOURCE_TYPES), required=True)
    args = parser.parse_args()
    warehouse = Warehouse(args.state)
    try:
        print(import_csv(warehouse, args.file, kind=args.kind, symbol=args.symbol,
                         timeframe=args.timeframe, source_type=args.source_type))
    finally:
        warehouse.close()


if __name__ == "__main__":
    main()
