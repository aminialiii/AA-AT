"""Bounded, research-only import of HistData's published ASCII ZIP format.

This module never opens MetaTrader or imports the execution service. Provider
prices are external research context, not broker-matched execution evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .store import utc

PROVIDER = "HistData"
PROVIDER_SPEC = "https://www.histdata.com/f-a-q/data-files-detailed-specification/"
PROVIDER_TIMEZONE = "EST_FIXED_UTC_MINUS_05_NO_DST"
SOURCE_TYPE = "EXTERNAL_HISTDATA_CONTEXT"
ALLOWED_SYMBOLS = {"XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD"}
MEMBER_RE = re.compile(r"DAT_ASCII_([A-Z0-9]+)_(M1|T)_(\d{4})(\d{2})?\.csv\Z")
MAX_ARCHIVE_BYTES = 2_000_000_000
MAX_MEMBER_BYTES = 8_000_000_000
BATCH_ROWS = 50_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_time(raw: str, kind: str) -> datetime:
    if kind == "M1":
        if not re.fullmatch(r"\d{8} \d{6}", raw):
            raise ValueError("invalid_m1_timestamp")
        value = datetime.strptime(raw, "%Y%m%d %H%M%S")
        if value.second:
            raise ValueError("m1_second_not_zero")
    else:
        if not re.fullmatch(r"\d{8} \d{9}", raw):
            raise ValueError("invalid_tick_timestamp")
        value = datetime.strptime(raw[:15], "%Y%m%d %H%M%S")
        value = value.replace(microsecond=int(raw[15:]) * 1000)
    # The provider explicitly documents fixed EST without DST, including summer.
    return (value + timedelta(hours=5)).replace(tzinfo=timezone.utc)


def _validate_member(info: zipfile.ZipInfo, symbol: str, kind: str,
                     period: str) -> None:
    if info.is_dir() or "/" in info.filename or "\\" in info.filename:
        raise ValueError("archive_member_path_not_flat")
    match = MEMBER_RE.fullmatch(info.filename)
    if not match or match.group(1) != symbol or match.group(2) != kind:
        raise ValueError("archive_member_name_mismatch")
    member_period = match.group(3) + ("-" + match.group(4) if match.group(4) else "")
    if member_period != period or info.file_size > MAX_MEMBER_BYTES:
        raise ValueError("archive_member_period_or_size_invalid")


def _parse_row(line: str, kind: str, period: str) -> tuple:
    values = line.rstrip("\r\n").split(";" if kind == "M1" else ",")
    if len(values) != (6 if kind == "M1" else 4):
        raise ValueError("invalid_market_row_width")
    when = _parse_time(values[0], kind)
    local_period = values[0][:4] + ("-" + values[0][4:6] if len(period) == 7 else "")
    if local_period != period:
        raise ValueError("row_outside_declared_provider_period")
    if kind == "M1":
        o, h, l, c = map(float, values[1:5])
        if not all(0 < x < float("inf") for x in (o, h, l, c)):
            raise ValueError("invalid_m1_price")
        if h < max(o, c, l) or l > min(o, c):
            raise ValueError("invalid_m1_ohlc")
        volume = float(values[5])
        if volume < 0 or volume == float("inf"):
            raise ValueError("invalid_m1_volume")
        return when, (when, o, h, l, c, volume)
    bid, ask, volume = map(float, values[1:])
    if not (0 < bid <= ask < float("inf")) or not (0 <= volume < float("inf")):
        raise ValueError("invalid_tick_price_or_volume")
    return when, (when, bid, ask, volume)


def _schema(kind: str):
    import pyarrow as pa
    if kind == "M1":
        return pa.schema([("time_utc", pa.timestamp("ms", tz="UTC")),
                          ("open_bid", pa.float64()), ("high_bid", pa.float64()),
                          ("low_bid", pa.float64()), ("close_bid", pa.float64()),
                          ("volume", pa.float64())])
    return pa.schema([("time_utc", pa.timestamp("ms", tz="UTC")),
                      ("bid", pa.float64()), ("ask", pa.float64()),
                      ("volume", pa.float64())])


def import_archive(state: Path, archive: Path, *, symbol: str, kind: str,
                   period: str) -> dict:
    """Copy a verified archive and index its immutable Parquet partition.

    A failed parse leaves no market-source row or accepted partition. The raw
    ZIP remains the provenance anchor; the Parquet file is derived data.
    """
    if symbol not in ALLOWED_SYMBOLS or kind not in {"M1", "T"}:
        raise ValueError("unsupported_symbol_or_kind")
    if not re.fullmatch(r"20\d{2}(?:-(?:0[1-9]|1[0-2]))?", period):
        raise ValueError("invalid_period")
    archive = archive.resolve(strict=True)
    if archive.stat().st_size == 0 or archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise ValueError("archive_empty_or_too_large")
    source_hash = sha256(archive)
    db_path = state / "research.sqlite3"
    if not db_path.is_file():
        raise ValueError("existing_research_warehouse_required")
    connection = sqlite3.connect(db_path, timeout=5)
    connection.execute("PRAGMA busy_timeout=5000")
    try:
        connection.execute("""CREATE TABLE IF NOT EXISTS historical_market_partitions(
            source_sha256 TEXT PRIMARY KEY, provider TEXT NOT NULL,
            source_type TEXT NOT NULL, symbol TEXT NOT NULL, kind TEXT NOT NULL,
            provider_period TEXT NOT NULL, provider_timezone TEXT NOT NULL,
            first_utc TEXT NOT NULL, last_utc TEXT NOT NULL,
            row_count INTEGER NOT NULL, non_60_second_intervals INTEGER NOT NULL,
            duplicate_rows INTEGER NOT NULL, negative_spreads INTEGER NOT NULL,
            min_spread REAL, max_spread REAL, provider_catalog_url TEXT NOT NULL,
            origin_verification TEXT NOT NULL,
            source_archive_path TEXT NOT NULL, parquet_path TEXT NOT NULL,
            parquet_sha256 TEXT NOT NULL, imported_utc TEXT NOT NULL,
            quality_status TEXT NOT NULL)""")
        previous = connection.execute("SELECT row_count,parquet_path,parquet_sha256,symbol,kind,provider_period FROM "
                                      "historical_market_partitions WHERE source_sha256=?",
                                      (source_hash,)).fetchone()
        if previous:
            if (previous[3], previous[4], previous[5]) != (symbol, kind, period):
                raise RuntimeError("existing_source_identity_conflict")
            if sha256(Path(previous[1])) != previous[2]:
                raise RuntimeError("existing_partition_hash_mismatch")
            return {"status": "ALREADY_IMPORTED", "source_sha256": source_hash,
                    "rows": previous[0], "parquet_path": previous[1]}
        with zipfile.ZipFile(archive) as package:
            if package.testzip() is not None:
                raise ValueError("archive_crc_failure")
            members = package.infolist()
            if len(members) != 1:
                raise ValueError("archive_must_have_one_csv_member")
            info = members[0]
            _validate_member(info, symbol, kind, period)
            import pyarrow as pa
            import pyarrow.parquet as pq
            folder = state / "market_data" / "historical" / PROVIDER / kind / symbol
            folder.mkdir(parents=True, exist_ok=True)
            parquet_path = folder / f"{period}-{source_hash[:16]}.parquet"
            temporary = parquet_path.with_name("." + parquet_path.name + "." + uuid.uuid4().hex)
            count = gaps = duplicates = negative_spreads = 0
            first = last = previous_when = previous_row = None
            min_spread = max_spread = None
            batch = []
            writer = None
            try:
                writer = pq.ParquetWriter(temporary, _schema(kind), compression="zstd")
                with package.open(info) as source:
                    for line_number, raw in enumerate(source, 1):
                        try:
                            line = raw.decode("ascii")
                            when, row = _parse_row(line, kind, period)
                        except (UnicodeDecodeError, ValueError) as error:
                            raise ValueError(f"invalid_market_row_{line_number}:{error}") from error
                        if previous_when is not None and when < previous_when:
                            raise ValueError(f"nonmonotone_market_timestamp_at_{line_number}")
                        if kind == "M1" and previous_when is not None:
                            if when == previous_when:
                                raise ValueError(f"duplicate_m1_timestamp_at_{line_number}")
                            if (when - previous_when).total_seconds() != 60:
                                gaps += 1
                        if kind == "T":
                            if previous_row == row:
                                duplicates += 1
                            spread = row[2] - row[1]
                            min_spread = spread if min_spread is None else min(spread, min_spread)
                            max_spread = spread if max_spread is None else max(spread, max_spread)
                        batch.append(row)
                        count += 1
                        first = first or when
                        last = when
                        previous_when, previous_row = when, row
                        if len(batch) == BATCH_ROWS:
                            writer.write_table(pa.Table.from_pylist(
                                [dict(zip(_schema(kind).names, item)) for item in batch],
                                schema=_schema(kind)))
                            batch.clear()
                    if batch:
                        writer.write_table(pa.Table.from_pylist(
                            [dict(zip(_schema(kind).names, item)) for item in batch],
                            schema=_schema(kind)))
                writer.close()
                writer = None
                if count == 0:
                    raise ValueError("empty_market_csv")
                if pq.ParquetFile(temporary).metadata.num_rows != count:
                    raise RuntimeError("parquet_row_count_mismatch")
                parquet_hash = sha256(temporary)
                if parquet_path.exists() and sha256(parquet_path) != parquet_hash:
                    raise RuntimeError("existing_partition_conflict")
                os.replace(temporary, parquet_path)
            finally:
                if writer is not None:
                    writer.close()
                temporary.unlink(missing_ok=True)
        raw_folder = state / "raw" / "market" / "histdata"
        raw_folder.mkdir(parents=True, exist_ok=True)
        raw_path = raw_folder / (source_hash + ".zip")
        if raw_path.exists():
            if sha256(raw_path) != source_hash:
                raise RuntimeError("raw_archive_hash_mismatch")
        else:
            raw_temp = raw_folder / ("." + source_hash + "." + uuid.uuid4().hex)
            try:
                shutil.copyfile(archive, raw_temp)
                if sha256(raw_temp) != source_hash:
                    raise RuntimeError("source_changed_during_copy")
                os.replace(raw_temp, raw_path)
            finally:
                raw_temp.unlink(missing_ok=True)
        catalog_url = ("https://www.histdata.com/download-free-forex-historical-data/"
                      f"?/ascii/{'1-minute-bar-quotes' if kind == 'M1' else 'tick-data-quotes'}"
                      f"/{symbol.lower()}/{period.replace('-', '/')}")
        quality = "REVIEW_GAPS_OR_DUPLICATES" if gaps or duplicates else "STRUCTURE_VALIDATED"
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("INSERT INTO market_sources VALUES (?,?,?,?,?,?,?,NULL)",
                           (source_hash, SOURCE_TYPE, str(raw_path), utc(), symbol,
                            "M1" if kind == "M1" else None, count))
        connection.execute("INSERT INTO historical_market_partitions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           (source_hash, PROVIDER, SOURCE_TYPE, symbol, kind, period,
                            PROVIDER_TIMEZONE, first.isoformat(), last.isoformat(),
                            count, gaps, duplicates, negative_spreads,
                            min_spread, max_spread, catalog_url,
                            "UNVERIFIED_INPUT_ARCHIVE", str(raw_path),
                            str(parquet_path), parquet_hash, utc(), quality))
        connection.commit()
        return {"status": quality, "origin_verification": "UNVERIFIED_INPUT_ARCHIVE",
                "source_sha256": source_hash, "rows": count,
                "first_utc": first.isoformat(), "last_utc": last.isoformat(),
                "non_60_second_intervals": gaps, "duplicate_rows": duplicates,
                "source_type": SOURCE_TYPE, "parquet_path": str(parquet_path)}
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--state", type=Path,
                        default=Path(r"E:\GPT\Inves\AA-AT-research-state"))
    parser.add_argument("--symbol", choices=sorted(ALLOWED_SYMBOLS), required=True)
    parser.add_argument("--kind", choices=("M1", "T"), required=True)
    parser.add_argument("--period", required=True,
                        help="provider's local fixed-EST year YYYY or month YYYY-MM")
    args = parser.parse_args()
    print(json.dumps(import_archive(args.state, args.archive, symbol=args.symbol,
                                    kind=args.kind, period=args.period), sort_keys=True))


if __name__ == "__main__":
    main()
