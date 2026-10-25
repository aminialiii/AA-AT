"""Build source-checked S04 parity inputs from contiguous historical Bid/Ask hours.

These files are research inputs, not broker fills or accepted backtest results.
The tester must still prove its bar construction and clock mapping match them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from datetime import datetime
from pathlib import Path

import numpy as np

from .dukascopy_hourly import decode
from .market_import import (DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json, digest,
                            ensure_under, require_capacity)


def _save_npz(path: Path, field: str, values: np.ndarray, vault: Path) -> str:
    path = ensure_under(path, vault)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + uuid.uuid4().hex + ".npz")
    try:
        np.savez_compressed(temporary, **{field: values})
        checksum = digest(temporary)
        if path.exists():
            if digest(path) != checksum:
                raise RuntimeError("parity_input_identity_conflict")
        else:
            os.replace(temporary, path)
        return checksum
    finally:
        temporary.unlink(missing_ok=True)


def build(source_records: list[Path], *, point: float, vault: Path = DEFAULT_VAULT,
          catalog: Path = DEFAULT_CATALOG) -> dict:
    if point <= 0 or not np.isfinite(point) or not source_records:
        raise ValueError("positive_point_and_source_records_required")
    records = [json.loads(path.read_text(encoding="utf-8")) for path in source_records]
    symbols = {row.get("symbol") for row in records}
    scales = {row.get("price_scale") for row in records}
    if len(symbols) != 1 or len(scales) != 1:
        raise ValueError("mixed_symbols_or_price_scales")
    ticks_by_hour = []
    verified = []
    for row in records:
        if (row.get("source_type") != "EXTERNAL_DUKASCOPY_LEGACY_HOUR_TICKS"
                or not row.get("utc_mapping_verified") or not row.get("bid_ask_ticks")):
            raise ValueError("unverified_tick_source")
        raw = Path(row["raw_path"]).resolve(strict=True)
        if not raw.is_relative_to((vault / "raw").resolve()) or digest(raw) != row["source_sha256"]:
            raise ValueError("raw_source_location_or_hash_invalid")
        hour = datetime.fromisoformat(row["hour_utc"])
        ticks = decode(raw.read_bytes(), hour, int(row["price_scale"]))
        if len(ticks) != row["row_count"]:
            raise ValueError("source_tick_count_changed")
        ticks_by_hour.append(ticks)
        verified.append({"raw_path": str(raw), "source_sha256": row["source_sha256"],
                         "hour_utc": row["hour_utc"]})
    ticks = np.concatenate(ticks_by_hour)
    order = np.argsort(ticks["time_ms_utc"], kind="stable")
    ticks = ticks[order]
    if np.any(np.diff(ticks["time_ms_utc"]) <= 0):
        raise ValueError("overlapping_or_duplicate_tick_timestamps")
    minutes, starts, counts = np.unique(ticks["time_ms_utc"] // 60_000,
                                        return_index=True, return_counts=True)
    if len(minutes) < 260 or np.any(np.diff(minutes) != 1):
        raise ValueError("insufficient_contiguous_utc_m1_warmup")
    rates = np.empty(len(minutes), dtype=[("time", "i8"), ("open", "f8"),
        ("high", "f8"), ("low", "f8"), ("close", "f8"), ("spread", "i4")])
    rates["time"] = minutes * 60
    for i, (start, count) in enumerate(zip(starts, counts)):
        batch = ticks[start:start + count]
        bid = batch["bid"]
        rates[i] = (int(minutes[i] * 60), float(bid[0]), float(np.max(bid)),
                    float(np.min(bid)), float(bid[-1]),
                    int(round(float(batch["ask"][-1] - bid[-1]) / point)))
    quotes = np.empty(len(ticks), dtype=[("time_ms_utc", "i8"),
        ("bid", "f8"), ("ask", "f8")])
    for field in ("time_ms_utc", "bid", "ask"):
        quotes[field] = ticks[field]
    source_id = hashlib.sha256(json.dumps({"sources": sorted((x["hour_utc"], x["source_sha256"])
                                                          for x in verified),
                                           "point": point}, sort_keys=True).encode()).hexdigest()[:24]
    folder = vault / "parity-inputs" / "S04" / source_id
    require_capacity(vault, (rates.nbytes + quotes.nbytes) * 4)
    rates_path, quotes_path = folder / "rates.npz", folder / "quotes.npz"
    rates_sha = _save_npz(rates_path, "rates", rates, vault)
    quotes_sha = _save_npz(quotes_path, "quotes", quotes, vault)
    result = {"schema_version": 1, "strategy_id": "S04", "symbol": next(iter(symbols)),
              "raw_sources": verified, "utc_mapping_verified": True,
              "bid_ask_ticks": True, "broker_matched": False,
              "point": point, "rates_path": str(rates_path), "rates_sha256": rates_sha,
              "quotes_path": str(quotes_path), "quotes_sha256": quotes_sha,
              "bar_count": len(rates), "tick_count": len(ticks),
              "first_bar_utc_s": int(rates["time"][0]),
              "last_bar_utc_s": int(rates["time"][-1]),
              "derived_spread_rule": "last Bid/Ask quote in each minute, rounded to point",
              "tester_clock_verified": False, "tester_server_offset_seconds": None,
              "runtime_bar_and_spread_parity": "NOT_TESTED",
              "backtest_eligible": False}
    target = catalog / "parity_inputs" / (source_id + ".json")
    atomic_json(target, result, catalog)
    return {"record": str(target), "bar_count": len(rates), "tick_count": len(ticks),
            "backtest_eligible": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_records", nargs="+", type=Path)
    parser.add_argument("--point", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source_records, point=args.point)))


if __name__ == "__main__":
    main()
