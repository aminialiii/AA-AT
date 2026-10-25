"""Bounded research-only HistData Bid/Ask tick intake; fixed EST, no DST."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import urllib.parse
import urllib.request
import uuid
import zipfile
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json, digest, ensure_under, require_capacity

HOST = "https://www.histdata.com"
SPEC = HOST + "/f-a-q/data-files-detailed-specification/"
MAX_ZIP = 512 * 1024 * 1024
MAX_CSV = 8 * 1024 * 1024 * 1024
EST = timezone(timedelta(hours=-5))


class DownloadForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and a.get("id") == "file_down":
            self.active = True
        if self.active and tag == "input" and a.get("type") == "hidden":
            self.fields[a.get("name", "")] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def form(opener, symbol: str, year: int, month: int):
    if not re.fullmatch(r"[A-Z]{6}", symbol) or not 2023 <= year <= 2026 or not 1 <= month <= 12:
        raise ValueError("invalid_symbol_or_month")
    page = f"{HOST}/download-free-forex-historical-data/?/ascii/tick-data-quotes/{symbol.lower()}/{year}/{month}"
    with opener.open(page, timeout=20) as response:
        if urllib.parse.urlparse(response.url).hostname != "www.histdata.com":
            raise RuntimeError("provider_page_redirect")
        html = response.read(500_001)
    if len(html) > 500_000:
        raise RuntimeError("provider_page_oversize")
    parser = DownloadForm()
    parser.feed(html.decode("utf-8", errors="replace"))
    expected = {"date": str(year), "datemonth": f"{year}{month:02d}",
                "platform": "ASCII", "timeframe": "T", "fxpair": symbol}
    if not parser.fields.get("tk") or any(parser.fields.get(k) != v for k, v in expected.items()):
        raise RuntimeError("provider_form_mismatch")
    return page, parser.fields


def response_for(opener, fields):
    data = urllib.parse.urlencode(fields).encode("ascii")
    req = urllib.request.Request(HOST + "/get.php", data=data,
                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
    response = opener.open(req, timeout=30)
    if urllib.parse.urlparse(response.url).hostname != "www.histdata.com":
        response.close()
        raise RuntimeError("provider_archive_redirect")
    return response


def acquire(symbol: str, year: int, month: int, *, vault: Path = DEFAULT_VAULT,
            headers_only: bool = False) -> dict:
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    page, fields = form(opener, symbol, year, month)
    if not headers_only:
        require_capacity(vault, MAX_ZIP)
    with response_for(opener, fields) as response:
        meta = {"page": page, "response_url": response.url,
                "status": response.status, "content_type": response.headers.get("Content-Type", ""),
                "content_length": response.headers.get("Content-Length"),
                "acquired_utc": datetime.now(timezone.utc).isoformat()}
        if headers_only:
            return meta
        length = int(meta["content_length"] or 0)
        if length > MAX_ZIP or "html" in meta["content_type"].lower():
            raise RuntimeError("provider_did_not_return_bounded_zip")
        directory = ensure_under(vault / "raw" / "HistData" / symbol / f"{year}-{month:02d}", vault)
        directory.mkdir(parents=True, exist_ok=True)
        temp = directory / (".partial-" + uuid.uuid4().hex + ".zip")
        try:
            h = hashlib.sha256()
            size = 0
            with temp.open("xb") as output:
                while block := response.read(1024 * 1024):
                    size += len(block)
                    if size > MAX_ZIP:
                        raise RuntimeError("provider_zip_exceeded_limit")
                    output.write(block)
                    h.update(block)
            if not size or (length and size != length) or not zipfile.is_zipfile(temp):
                raise RuntimeError("provider_zip_invalid_or_truncated")
            target = directory / (h.hexdigest() + ".zip")
            if target.exists():
                if digest(target) != h.hexdigest():
                    raise RuntimeError("archive_hash_collision")
            else:
                os.replace(temp, target)
            return {**meta, "archive_path": str(target), "source_sha256": h.hexdigest(),
                    "archive_bytes": size}
        finally:
            temp.unlink(missing_ok=True)


def parse_est_millis(value: str) -> int:
    if not re.fullmatch(r"\d{8} \d{9}", value):
        raise ValueError("invalid_tick_timestamp")
    local = datetime.strptime(value[:15], "%Y%m%d %H%M%S").replace(tzinfo=EST)
    return int(local.timestamp()) * 1000 + int(value[15:])


def ingest(acquired: dict, symbol: str, year: int, month: int, *,
           vault: Path = DEFAULT_VAULT, catalog: Path = DEFAULT_CATALOG) -> dict:
    import pyarrow as pa
    import pyarrow.parquet as pq

    path = Path(acquired["archive_path"]).resolve(strict=True)
    if not path.is_relative_to((vault / "raw" / "HistData").resolve()) or digest(path) != acquired["source_sha256"]:
        raise ValueError("archive_origin_or_hash_invalid")
    with zipfile.ZipFile(path) as archive:
        members = [i for i in archive.infolist() if not i.is_dir()]
        expected = f"DAT_ASCII_{symbol}_T_{year}{month:02d}.csv"
        match = [i for i in members if Path(i.filename).name.upper() == expected.upper()]
        if (len(match) != 1 or len(members) > 4 or
                any(".." in Path(i.filename).parts for i in members) or
                sum(i.file_size for i in members) > MAX_CSV or archive.testzip() is not None):
            raise ValueError("archive_schema_or_crc_invalid")
        require_capacity(vault, match[0].file_size * 2)
        target = ensure_under(vault / "parquet" / "HistData" / symbol /
                              f"{year}-{month:02d}-{acquired['source_sha256']}.parquet", vault)
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name("." + target.name + "." + uuid.uuid4().hex)
        schema = pa.schema([("time_utc", pa.timestamp("ms", tz="UTC")),
                            ("bid", pa.float64()), ("ask", pa.float64()),
                            ("provider_volume", pa.float64())])
        writer = None
        columns = [[], [], [], []]
        count = duplicates = gaps = 0
        first = last = previous = None
        try:
            with archive.open(match[0]) as raw:
                for row in csv.reader(io.TextIOWrapper(raw, encoding="ascii", newline="")):
                    if len(row) != 4:
                        raise ValueError("invalid_tick_row_width")
                    timestamp = parse_est_millis(row[0])
                    bid, ask, volume = map(float, row[1:])
                    if not (0 < bid <= ask and 0 <= volume < float("inf")):
                        raise ValueError("invalid_tick_quote")
                    if previous is not None:
                        if timestamp < previous:
                            raise ValueError("tick_time_regression")
                        duplicates += timestamp == previous
                        gaps += timestamp - previous > 60_000
                    previous = last = timestamp
                    first = timestamp if first is None else first
                    for col, val in zip(columns, (timestamp, bid, ask, volume)):
                        col.append(val)
                    count += 1
                    if len(columns[0]) >= 250_000:
                        writer = writer or pq.ParquetWriter(temp, schema, compression="zstd")
                        writer.write_table(pa.Table.from_arrays([pa.array(c, type=t)
                            for c, t in zip(columns, schema.types)], schema=schema))
                        columns = [[], [], [], []]
            if not count:
                raise ValueError("empty_tick_file")
            if columns[0]:
                writer = writer or pq.ParquetWriter(temp, schema, compression="zstd")
                writer.write_table(pa.Table.from_arrays([pa.array(c, type=t)
                    for c, t in zip(columns, schema.types)], schema=schema))
        finally:
            if writer:
                writer.close()
        try:
            parquet_hash = digest(temp)
            if target.exists():
                if digest(target) != parquet_hash:
                    raise RuntimeError("parquet_hash_collision")
            else:
                os.replace(temp, target)
        finally:
            temp.unlink(missing_ok=True)
    iso = lambda ms: datetime.fromtimestamp(ms / 1000, timezone.utc).isoformat()
    record = {"schema_version": 1, "source_type": "EXTERNAL_HISTDATA_TICKS",
              "provider": "HistData", "provider_spec": SPEC,
              "symbol": symbol, "year": year, "month": month,
              "source_sha256": acquired["source_sha256"], "raw_path": str(path),
              "parquet_path": str(target), "parquet_sha256": parquet_hash,
              "row_count": count, "first_utc": iso(first), "last_utc": iso(last),
              "timestamp_source": "EST_FIXED_UTC_MINUS_05_NO_DST_PROVIDER_DOCUMENTED",
              "utc_mapping_verified": True, "bid_ask_ticks": True,
              "duplicate_timestamps": duplicates, "gaps_over_60s": gaps,
              "broker_matched": False, "eligible_for_three_year_backtest": False,
              "provider_acquisition": acquired}
    record["catalog_path"] = str(catalog / "sources" / (acquired["source_sha256"] + ".json"))
    atomic_json(Path(record["catalog_path"]), record, catalog)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("probe", "download"))
    parser.add_argument("symbol")
    parser.add_argument("year", type=int)
    parser.add_argument("month", type=int)
    args = parser.parse_args()
    acquired = acquire(args.symbol, args.year, args.month, headers_only=args.action == "probe")
    if args.action == "probe":
        print(json.dumps(acquired))
        return
    record = ingest(acquired, args.symbol, args.year, args.month)
    print(json.dumps({k: record[k] for k in ("symbol", "row_count", "first_utc", "last_utc", "catalog_path")}))


if __name__ == "__main__":
    main()
