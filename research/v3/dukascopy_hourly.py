"""Research-only intake for legacy Dukascopy hourly Bid/Ask BI5 files.

Month in the provider path is zero-indexed; each tick timestamp is milliseconds
from the start of the specified UTC hour. No production terminal is accessed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import lzma
import os
import re
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json, digest, ensure_under, require_capacity

MAX_COMPRESSED = 8 * 1024 * 1024
MAX_RECORDS = 1_000_000
PROVIDER_DOC = "https://www.dukascopy.com/wiki/en/development/data-export/"


def source_url(symbol: str, hour: datetime) -> str:
    if not re.fullmatch(r"[A-Z]{6}", symbol) or hour.tzinfo != timezone.utc or hour.minute or hour.second or hour.microsecond:
        raise ValueError("invalid_symbol_or_hour")
    return (f"https://datafeed.dukascopy.com/datafeed/{symbol}/{hour.year}/"
            f"{hour.month-1:02d}/{hour.day:02d}/{hour.hour:02d}h_ticks.bi5")


def decode(raw: bytes, hour: datetime, scale: int) -> np.ndarray:
    source_url("EURUSD", hour)  # validates UTC hour alignment
    if not 0 < len(raw) <= MAX_COMPRESSED or scale <= 0:
        raise ValueError("invalid_hour_archive_or_scale")
    try:
        decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
        data = decoder.decompress(raw, max_length=MAX_RECORDS * 20 + 1)
    except lzma.LZMAError as exc:
        raise ValueError("invalid_lzma_hour") from exc
    if not decoder.eof or not data or len(data) % 20 or len(data) // 20 > MAX_RECORDS:
        raise ValueError("invalid_hour_record_count")
    records = np.frombuffer(data, dtype=np.dtype([
        ("millis", ">u4"), ("ask_scaled", ">u4"), ("bid_scaled", ">u4"),
        ("ask_volume", ">f4"), ("bid_volume", ">f4")]))
    ms = records["millis"].astype(np.int64)
    bid = records["bid_scaled"].astype(np.float64) / scale
    ask = records["ask_scaled"].astype(np.float64) / scale
    if (np.any(ms >= 3_600_000) or np.any(np.diff(ms) < 0)
            or np.any((bid <= 0) | (ask < bid))
            or not np.isfinite(records["ask_volume"]).all()
            or not np.isfinite(records["bid_volume"]).all()):
        raise ValueError("invalid_hour_ticks")
    out = np.empty(len(ms), dtype=[("time_ms_utc", "i8"), ("bid", "f8"),
                                   ("ask", "f8"), ("bid_volume", "f4"),
                                   ("ask_volume", "f4")])
    out["time_ms_utc"] = int(hour.timestamp() * 1000) + ms
    for name, values in (("bid", bid), ("ask", ask),
                         ("bid_volume", records["bid_volume"]),
                         ("ask_volume", records["ask_volume"])):
        out[name] = values
    return out


def acquire(symbol: str, hour: datetime, *, vault: Path = DEFAULT_VAULT) -> dict:
    url = source_url(symbol, hour)
    require_capacity(vault, MAX_COMPRESSED * 3)
    folder = ensure_under(vault / "raw" / "DukascopyHourly" / symbol /
                          hour.strftime("%Y-%m-%d"), vault)
    folder.mkdir(parents=True, exist_ok=True)
    temp = folder / (".partial-" + uuid.uuid4().hex + ".bi5")
    try:
        with urllib.request.urlopen(url, timeout=25) as response:
            if response.status != 200 or response.url != url:
                raise RuntimeError("provider_hour_response_invalid")
            length = int(response.headers.get("Content-Length") or 0)
            if length > MAX_COMPRESSED:
                raise RuntimeError("provider_hour_oversize")
            h = hashlib.sha256()
            size = 0
            with temp.open("xb") as output:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_COMPRESSED:
                        raise RuntimeError("provider_hour_exceeded_limit")
                    h.update(block)
                    output.write(block)
            if not size or (length and length != size):
                raise RuntimeError("provider_hour_truncated")
        target = folder / (h.hexdigest() + ".bi5")
        if target.exists():
            if digest(target) != h.hexdigest():
                raise RuntimeError("provider_hour_identity_conflict")
        else:
            os.replace(temp, target)
        return {"source_url": url, "archive_path": str(target),
                "source_sha256": h.hexdigest(), "archive_bytes": size,
                "acquired_utc": datetime.now(timezone.utc).isoformat()}
    finally:
        temp.unlink(missing_ok=True)


def ingest(acquired: dict, symbol: str, hour: datetime, scale: int,
           scale_evidence: str, *, vault: Path = DEFAULT_VAULT,
           catalog: Path = DEFAULT_CATALOG) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    if not scale_evidence or acquired.get("source_url") != source_url(symbol, hour):
        raise ValueError("scale_evidence_or_url_missing")
    path = Path(acquired["archive_path"]).resolve(strict=True)
    if not path.is_relative_to((vault / "raw" / "DukascopyHourly").resolve()):
        raise ValueError("archive_outside_research_vault")
    if digest(path) != acquired["source_sha256"]:
        raise ValueError("archive_hash_mismatch")
    ticks = decode(path.read_bytes(), hour, scale)
    require_capacity(vault, ticks.nbytes * 3)
    table = pa.table({"time_utc": pa.array(ticks["time_ms_utc"], type=pa.timestamp("ms", tz="UTC")),
                      "bid": ticks["bid"], "ask": ticks["ask"],
                      "bid_volume": ticks["bid_volume"],
                      "ask_volume": ticks["ask_volume"]})
    target = ensure_under(vault / "parquet" / "DukascopyHourly" / symbol /
                          hour.strftime("%Y-%m-%dT%H") / (acquired["source_sha256"] + ".parquet"), vault)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name("." + target.name + "." + uuid.uuid4().hex)
    try:
        pq.write_table(table, temp, compression="zstd")
        parquet_hash = digest(temp)
        if target.exists():
            if digest(target) != parquet_hash:
                raise RuntimeError("hour_parquet_identity_conflict")
        else:
            os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    iso = lambda ms: datetime.fromtimestamp(int(ms) / 1000, timezone.utc).isoformat()
    ms = ticks["time_ms_utc"]
    record = {"schema_version": 1, "source_type": "EXTERNAL_DUKASCOPY_LEGACY_HOUR_TICKS",
              "provider": "Dukascopy", "provider_documentation": PROVIDER_DOC,
              "symbol": symbol, "hour_utc": hour.isoformat(),
              "source_sha256": acquired["source_sha256"], "source_url": acquired["source_url"],
              "raw_path": str(path), "parquet_path": str(target),
              "parquet_sha256": parquet_hash, "row_count": len(ticks),
              "first_utc": iso(ms[0]), "last_utc": iso(ms[-1]),
              "duplicate_timestamps": int(np.count_nonzero(np.diff(ms) == 0)),
              "gaps_over_60s": int(np.count_nonzero(np.diff(ms) > 60_000)),
              "utc_mapping_verified": True, "bid_ask_ticks": True,
              "price_scale": scale, "scale_evidence": scale_evidence,
              "broker_matched": False, "eligible_for_three_year_backtest": False,
              "provider_acquisition": acquired}
    record["catalog_path"] = str(catalog / "sources" / (acquired["source_sha256"] + ".json"))
    atomic_json(Path(record["catalog_path"]), record, catalog)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol")
    parser.add_argument("hour_utc", help="YYYY-MM-DDTHH:00:00Z")
    parser.add_argument("--scale", type=int, required=True)
    parser.add_argument("--scale-evidence", required=True)
    parser.add_argument("--existing", type=Path, help="Source-hashed archive already in the research vault")
    args = parser.parse_args()
    hour = datetime.strptime(args.hour_utc, "%Y-%m-%dT%H:00:00Z").replace(tzinfo=timezone.utc)
    acquired = ({"source_url": source_url(args.symbol, hour),
                 "archive_path": str(args.existing),
                 "source_sha256": digest(args.existing),
                 "acquisition_note": "existing_manually_downloaded_https_file"}
                if args.existing else acquire(args.symbol, hour))
    result = ingest(acquired, args.symbol, hour, args.scale, args.scale_evidence)
    print(json.dumps({k: result[k] for k in ("symbol", "hour_utc", "row_count", "first_utc",
                                              "last_utc", "source_sha256", "catalog_path")}))


if __name__ == "__main__":
    main()
