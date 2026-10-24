"""Historical-only market intake into the existing warehouse's V3 namespace.

The active research.sqlite3 and all trading databases are never opened here.
Large immutable files live in a separate vault; small provenance manifests live
under AA-AT-research-state/v3 and are included in the existing daily backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import shutil
import struct
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

DEFAULT_VAULT = Path(r"E:\GPT\Inves\AA-AT-v3-market-vault")
DEFAULT_CATALOG = Path(r"E:\GPT\Inves\AA-AT-research-state\v3\catalog")
PERIOD_START = "2023-10-24T00:00:00Z"
PERIOD_END_EXCLUSIVE = "2026-10-24T00:00:00Z"
MAX_BI5_BYTES = 64 * 1024 * 1024
MAX_TICKS_PER_DAY = 12_000_000
MIN_FREE_AFTER_IMPORT = 5 * 1024 ** 3
LEGACY_POINTER = Path(r"E:\GPT\Inves\research\overnight-20261010\history_pointer.json")
LEGACY_POINTER_SHA256 = "ec80d05f97cb537e8d4986bda91c806f2fdf8035f83d88496fbf304be957ec06"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def ensure_under(path: Path, root: Path) -> Path:
    path = path.resolve()
    root = root.resolve()
    if not path.is_relative_to(root) or path == root:
        raise ValueError("write_path_outside_research_allowlist")
    return path


def require_capacity(vault: Path, projected_bytes: int) -> None:
    """Leave a fixed free-space reserve even if the final Parquet is larger."""
    existing = vault.resolve()
    while not existing.exists():
        existing = existing.parent
    free = shutil.disk_usage(existing).free
    if free - projected_bytes < MIN_FREE_AFTER_IMPORT:
        raise RuntimeError("research_vault_capacity_guard")


def atomic_json(path: Path, value: dict, root: Path) -> None:
    path = ensure_under(path, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name("." + path.name + "." + uuid.uuid4().hex)
    try:
        temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _copy_hashed(source: Path, dest: Path, expected: str, vault: Path) -> None:
    dest = ensure_under(dest, vault)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        if digest(dest) != expected:
            raise RuntimeError("vault_hash_collision")
        return
    temp = dest.with_name("." + dest.name + "." + uuid.uuid4().hex)
    try:
        shutil.copyfile(source, temp)
        if digest(temp) != expected:
            raise RuntimeError("source_changed_during_copy")
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)


def _publish(record: dict, catalog: Path) -> Path:
    path = catalog / "sources" / (record["source_sha256"] + ".json")
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if existing != record:
            raise RuntimeError("source_identity_conflict")
    else:
        atomic_json(path, record, catalog)
    return path


def _write_parquet(table, target: Path, vault: Path) -> str:
    import pyarrow.parquet as pq
    target = ensure_under(target, vault)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name("." + target.name + "." + uuid.uuid4().hex)
    try:
        pq.write_table(table, temp, compression="zstd", row_group_size=100_000)
        value = digest(temp)
        if target.exists():
            if digest(target) != value:
                raise RuntimeError("parquet_identity_conflict")
        else:
            os.replace(temp, target)
        return value
    finally:
        temp.unlink(missing_ok=True)


def import_legacy_m1(source: Path, manifest: dict, *, vault: Path = DEFAULT_VAULT,
                     catalog: Path = DEFAULT_CATALOG) -> dict:
    """Import a frozen broker NPZ without promoting its unverified UTC offset."""
    import pyarrow as pa

    source = source.resolve(strict=True)
    expected = manifest["sha256"]
    if digest(source) != expected:
        raise RuntimeError("legacy_source_hash_mismatch")
    symbol = manifest["symbol"]
    with np.load(source, allow_pickle=False) as package:
        rates = package["rates"]
    fields = {"time", "open", "high", "low", "close", "spread"}
    if not fields.issubset(rates.dtype.names or ()) or not len(rates):
        raise ValueError("legacy_rate_schema_invalid")
    times = rates["time"].astype(np.int64)
    if not np.all(np.diff(times) > 0):
        raise ValueError("nonmonotone_or_duplicate_legacy_bars")
    o, h, l, c = (rates[name].astype(np.float64) for name in ("open", "high", "low", "close"))
    if (not all(np.isfinite(x).all() for x in (o, h, l, c))
            or not np.all((l <= o) & (l <= c) & (h >= o) & (h >= c))
            or not np.all(rates["spread"] >= 0)):
        raise ValueError("invalid_legacy_price_or_spread")
    offset_minutes = int(manifest["assumed_broker_offset_minutes"])
    utc_ms = (times - offset_minutes * 60) * 1000
    schema = pa.schema([
        ("time_utc", pa.timestamp("ms", tz="UTC")), ("open_bid", pa.float64()),
        ("high_bid", pa.float64()), ("low_bid", pa.float64()),
        ("close_bid", pa.float64()), ("spread_points", pa.int32())])
    table = pa.Table.from_arrays([
        pa.array(utc_ms, type=pa.timestamp("ms", tz="UTC")),
        *(pa.array(x) for x in (o, h, l, c)),
        pa.array(rates["spread"].astype(np.int32))], schema=schema)
    require_capacity(vault, source.stat().st_size + 2 * table.nbytes)
    raw = vault / "raw" / "legacy_broker_npz" / (expected + ".npz")
    _copy_hashed(source, raw, expected, vault)
    parquet = vault / "parquet" / "legacy_broker_npz" / symbol / (expected + ".parquet")
    parquet_hash = _write_parquet(table, parquet, vault)
    def iso(ms):
        return datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()
    record = {
        "schema_version": 1, "source_type": "LEGACY_BROKER_M1_OFFSET_UNVERIFIED",
        "provider": "saved_broker_archive", "symbol": symbol, "timeframe": "M1",
        "source_sha256": expected, "raw_path": str(raw), "parquet_path": str(parquet),
        "parquet_sha256": parquet_hash, "row_count": len(rates),
        "first_utc_assuming_fixed_offset": iso(utc_ms[0]),
        "last_utc_assuming_fixed_offset": iso(utc_ms[-1]),
        "broker_offset_minutes_assumed": offset_minutes,
        "utc_mapping_verified": False, "bid_ask_ticks": False,
        "complete_three_year_coverage": False,
        "eligible_for_three_year_backtest": False,
        "non_60_second_intervals": int(np.count_nonzero(np.diff(times) != 60)),
        "origin_path_sha256_verified": True,
        "research_window": [PERIOD_START, PERIOD_END_EXCLUSIVE],
    }
    record["catalog_path"] = str(catalog / "sources" / (expected + ".json"))
    _publish(record, catalog)
    return record


def import_legacy_pointer(pointer_path: Path, *, vault: Path = DEFAULT_VAULT,
                          catalog: Path = DEFAULT_CATALOG) -> list[dict]:
    """Import exactly the source-hashed legacy archives, without claiming UTC fidelity."""
    if pointer_path.resolve(strict=True) != LEGACY_POINTER.resolve(strict=True):
        raise RuntimeError("legacy_pointer_not_frozen_source")
    if digest(pointer_path) != LEGACY_POINTER_SHA256:
        raise RuntimeError("legacy_pointer_hash_changed")
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    manifest_path = Path(pointer["path"]).resolve(strict=True)
    if digest(manifest_path) != pointer["sha256"]:
        raise RuntimeError("legacy_manifest_hash_mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    for symbol, item in sorted(manifest["symbols"].items()):
        if item["status"] != "AVAILABLE":
            continue
        row = import_legacy_m1(Path(item["path"]), {
            "symbol": symbol, "sha256": item["sha256"],
            "assumed_broker_offset_minutes": manifest["brokerOffsetMinutes"],
        }, vault=vault, catalog=catalog)
        rows.append(row)
    return rows


def decode_dukascopy_day(raw: bytes, *, day: datetime, price_scale: int) -> np.ndarray:
    """Decode official 20-byte daily Bid/Ask BI5 format; never guess a gold scale."""
    if day.tzinfo != timezone.utc or day.time() != datetime.min.time():
        raise ValueError("day_must_be_midnight_utc")
    if price_scale <= 0 or len(raw) > MAX_BI5_BYTES:
        raise ValueError("invalid_scale_or_oversize_archive")
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        decoded = decoder.decompress(raw, max_length=MAX_TICKS_PER_DAY * 20 + 1)
    except lzma.LZMAError as exc:
        raise ValueError("unsupported_or_corrupt_bi5_format") from exc
    if not decoder.eof or len(decoded) % 20 or len(decoded) // 20 > MAX_TICKS_PER_DAY:
        raise ValueError("invalid_bi5_record_count")
    dtype = np.dtype([("millis", ">u4"), ("ask_scaled", ">u4"),
                      ("bid_scaled", ">u4"), ("ask_volume", ">f4"),
                      ("bid_volume", ">f4")])
    source = np.frombuffer(decoded, dtype=dtype)
    ms = source["millis"].astype(np.int64)
    bid = source["bid_scaled"].astype(np.float64) / price_scale
    ask = source["ask_scaled"].astype(np.float64) / price_scale
    if (len(ms) == 0 or np.any(ms >= 86_400_000) or np.any(np.diff(ms) < 0)
            or np.any((bid <= 0) | (ask < bid))
            or not np.isfinite(source["ask_volume"]).all()
            or not np.isfinite(source["bid_volume"]).all()):
        raise ValueError("invalid_bi5_ticks")
    out = np.empty(len(ms), dtype=[("time_ms_utc", "i8"), ("bid", "f8"),
                                   ("ask", "f8"), ("ask_volume", "f4"),
                                   ("bid_volume", "f4")])
    out["time_ms_utc"] = int(day.timestamp() * 1000) + ms
    for key in ("bid", "ask", "ask_volume", "bid_volume"):
        out[key] = bid if key == "bid" else ask if key == "ask" else source[key]
    return out


def import_dukascopy_day(source: Path, *, symbol: str, day: datetime,
                         price_scale: int, scale_evidence: str,
                         origin_url: str | None = None,
                         vault: Path = DEFAULT_VAULT,
                         catalog: Path = DEFAULT_CATALOG) -> dict:
    import pyarrow as pa
    if not scale_evidence or not symbol.isalnum() or symbol != symbol.upper():
        raise ValueError("symbol_or_scale_evidence_missing")
    source = source.resolve(strict=True)
    source_hash = digest(source)
    ticks = decode_dukascopy_day(source.read_bytes(), day=day, price_scale=price_scale)
    require_capacity(vault, source.stat().st_size + 2 * ticks.nbytes)
    year_day = day.strftime("%Y-%m-%d")
    raw = vault / "raw" / "Dukascopy" / symbol / (year_day + "-" + source_hash + ".bi5")
    _copy_hashed(source, raw, source_hash, vault)
    table = pa.table({
        "time_utc": pa.array(ticks["time_ms_utc"], type=pa.timestamp("ms", tz="UTC")),
        "bid": ticks["bid"], "ask": ticks["ask"],
        "bid_volume": ticks["bid_volume"], "ask_volume": ticks["ask_volume"]})
    parquet = vault / "parquet" / "Dukascopy" / symbol / (year_day + "-" + source_hash + ".parquet")
    parquet_hash = _write_parquet(table, parquet, vault)
    record = {
        "schema_version": 1, "source_type": "EXTERNAL_DUKASCOPY_TICKS",
        "provider": "Dukascopy", "symbol": symbol, "day_utc": year_day,
        "source_sha256": source_hash, "raw_path": str(raw),
        "parquet_path": str(parquet), "parquet_sha256": parquet_hash,
        "row_count": len(ticks), "price_scale": price_scale,
        "scale_evidence": scale_evidence, "origin_url_asserted": origin_url,
        "origin_verified": False, "utc_mapping_verified": True,
        "first_utc": datetime.fromtimestamp(ticks["time_ms_utc"][0] / 1000, timezone.utc).isoformat(),
        "last_utc": datetime.fromtimestamp(ticks["time_ms_utc"][-1] / 1000, timezone.utc).isoformat(),
        "eligible_for_three_year_backtest": False,
        "eligibility_note": "One day alone cannot establish full-period, cost or contract coverage",
    }
    record["catalog_path"] = str(catalog / "sources" / (source_hash + ".json"))
    _publish(record, catalog)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy-pointer", type=Path,
                        help="Frozen history_pointer.json covering several legacy archives")
    parser.add_argument("--bi5", type=Path)
    parser.add_argument("--symbol")
    parser.add_argument("--day", help="YYYY-MM-DD UTC")
    parser.add_argument("--price-scale", type=int)
    parser.add_argument("--scale-evidence")
    parser.add_argument("--origin-url")
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    if sum(bool(x) for x in (args.legacy_pointer, args.bi5)) != 1:
        parser.error("choose exactly one input type")
    if args.legacy_pointer:
        rows = import_legacy_pointer(args.legacy_pointer, vault=args.vault, catalog=args.catalog)
        print(json.dumps({"imported_sources": len(rows),
                          "rows": sum(row["row_count"] for row in rows),
                          "three_year_eligible": sum(row["eligible_for_three_year_backtest"] for row in rows)}))
        return
    else:
        if not all((args.symbol, args.day, args.price_scale, args.scale_evidence)):
            parser.error("bi5 requires symbol, day, price-scale and scale-evidence")
        day = datetime.strptime(args.day, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        result = import_dukascopy_day(args.bi5, symbol=args.symbol, day=day,
                   price_scale=args.price_scale, scale_evidence=args.scale_evidence,
                   origin_url=args.origin_url, vault=args.vault, catalog=args.catalog)
    print(json.dumps({key: result[key] for key in
                      ("source_type", "symbol", "row_count", "source_sha256", "catalog_path")}))


if __name__ == "__main__":
    main()
