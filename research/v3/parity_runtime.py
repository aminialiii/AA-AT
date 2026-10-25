"""Compare isolated S04 tester diagnostics with the frozen Python strategy.

Only an actual Strategy Tester log can supply MQL observations. This module
never launches a terminal, reaches a broker, or creates campaign trades.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json
from .parity import MODEL, _features, frozen_signals

TRACE = re.compile(
    r"AAAT_V3_TRACE,S04,([A-Za-z0-9_.-]+),(\d{4}\.\d{2}\.\d{2} "
    r"\d{2}:\d{2}:\d{2}),(-?\d+),([0-9.eE+-]+),([0-9.eE+-]+),([0-9.eE+-]+),([01])")


def read_tester_trace(log: Path, *, server_offset_seconds: int = 0) -> list[dict]:
    observations = []
    raw = log.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8-sig"
    for line_number, line in enumerate(raw.decode(encoding).splitlines(), 1):
        match = TRACE.search(line)
        if not match:
            continue
        symbol, stamp, side, atr, spread, live_spread, eligible = match.groups()
        observed = datetime.strptime(stamp, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        observed = datetime.fromtimestamp(observed.timestamp() - server_offset_seconds, timezone.utc)
        observations.append({"symbol": symbol, "signal_bar_utc": observed.isoformat(),
                             "side": int(side), "atr": float(atr),
                             "modeled_spread": float(spread), "live_spread": float(live_spread),
                             "eligible": bool(int(eligible)),
                             "log_line": line_number})
    return observations


def python_reference(rates: np.ndarray, quotes: np.ndarray, *, tick_size: float, point: float,
                     symbol: str) -> list[dict]:
    if point <= 0 or tick_size <= 0 or "spread" not in rates.dtype.names:
        raise ValueError("verified_point_tick_and_spread_bars_required")
    if len(rates) and np.any(np.diff(rates["time"].astype(np.int64)) <= 0):
        raise ValueError("bars_must_have_unique_increasing_utc_time")
    quote_fields = {"time_ms_utc", "bid", "ask"}
    if not quote_fields.issubset(quotes.dtype.names or ()) or not len(quotes):
        raise ValueError("verified_bid_ask_ticks_required")
    times_ms = quotes["time_ms_utc"].astype(np.int64)
    if np.any(np.diff(times_ms) <= 0) or np.any(quotes["bid"] <= 0) or np.any(quotes["ask"] < quotes["bid"]):
        raise ValueError("invalid_or_duplicate_bid_ask_ticks")
    d = _features(rates, tick_size)
    signals = frozen_signals()(d, MODEL)
    spread_price = rates["spread"].astype(float) * point
    rows = []
    for i in np.flatnonzero(d["valid"]):
        # EA's CopyRates runs after the next forming candle starts. The
        # original replay also requires an adjacent next entry bar.
        if i < 258 or i + 1 >= len(rates) or d["t"][i+1] - d["t"][i] != 60:
            continue
        forming_ms = int(d["t"][i+1]) * 1000
        quote_index = int(np.searchsorted(times_ms, forming_ms))
        if quote_index >= len(quotes) or times_ms[quote_index] >= forming_ms + 60_000:
            continue
        previous = max(float(np.max(spread_price[i-5:i])), tick_size) * 1.25
        live_spread = float(quotes["ask"][quote_index] - quotes["bid"][quote_index])
        side = int(signals[i])
        rows.append({"symbol": symbol,
                     "signal_bar_utc": datetime.fromtimestamp(int(d["t"][i]), timezone.utc).isoformat(),
                     "side": side, "atr": float(d["atr"][i]),
                     "modeled_spread": previous, "live_spread": live_spread,
                     "eligible": bool(side and live_spread / d["atr"][i] <= .25)})
    return rows


def compare(expected: list[dict], actual: list[dict], *,
            price_tolerance: float = 1e-9, max_examples: int = 50) -> dict:
    if price_tolerance <= 0:
        raise ValueError("positive_tolerance_required")
    def keyed(rows):
        result, duplicate = {}, []
        for row in rows:
            key = (row["symbol"], row["signal_bar_utc"])
            if key in result:
                duplicate.append(key)
            result[key] = row
        return result, duplicate
    e, ed = keyed(expected)
    a, ad = keyed(actual)
    issues = []
    for key in sorted(e.keys() | a.keys()):
        if key not in e or key not in a:
            issues.append({"symbol": key[0], "signal_bar_utc": key[1],
                           "kind": "MISSING_MQL_BAR" if key not in a else "UNEXPECTED_MQL_BAR"})
            continue
        for field in ("side", "eligible", "atr", "modeled_spread", "live_spread"):
            left, right = e[key][field], a[key][field]
            different = (abs(left-right) > price_tolerance if field in ("atr", "modeled_spread", "live_spread")
                         else left != right)
            if different:
                issues.append({"symbol": key[0], "signal_bar_utc": key[1],
                               "kind": field.upper() + "_MISMATCH",
                               "python": left, "mql": right})
    return {"expected_bars": len(expected), "mql_bars": len(actual),
            "expected_signals": sum(row["side"] != 0 for row in expected),
            "mql_signals": sum(row["side"] != 0 for row in actual),
            "duplicate_python_keys": len(ed), "duplicate_mql_keys": len(ad),
            "mismatch_count": len(issues) + len(ed) + len(ad),
            "mismatch_examples": issues[:max_examples],
            "signal_parity_passed": bool(expected) and not issues and not ed and not ad,
            "execution_fill_parity": "NOT_ASSESSED",
            "position_management_parity": "NOT_APPLICABLE_NO_BREAK_EVEN_OR_TRAILING_IN_FROZEN_S04_REPLAY"}


def run(*, rates_npz: Path, quotes_npz: Path, source_record: Path,
        tester_log: Path, symbol: str, tick_size: float,
        point: float, catalog: Path = DEFAULT_CATALOG) -> dict:
    record = json.loads(source_record.read_text(encoding="utf-8"))
    if (not record.get("utc_mapping_verified") or not record.get("bid_ask_ticks")
            or record.get("symbol") != symbol or not record.get("tester_clock_verified")
            or type(record.get("tester_server_offset_seconds")) is not int):
        raise ValueError("source_utc_bid_ask_or_symbol_not_verified")
    if (source_record.resolve().parent != (catalog / "parity_inputs").resolve()
            or Path(record.get("rates_path", "")).resolve() != rates_npz.resolve()
            or Path(record.get("quotes_path", "")).resolve() != quotes_npz.resolve()
            or abs(float(record.get("point", 0)) - point) > 1e-12):
        raise ValueError("parity_source_record_identity_mismatch")
    for label, path in (("rates", rates_npz), ("quotes", quotes_npz)):
        if hashlib.sha256(path.read_bytes()).hexdigest() != record.get(label + "_sha256"):
            raise ValueError(label + "_hash_not_registered")
    sources = record.get("raw_sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("raw_sources_missing")
    for source in sources:
        raw = Path(source["raw_path"])
        if (not raw.resolve().is_relative_to((DEFAULT_VAULT / "raw").resolve())
                or hashlib.sha256(raw.read_bytes()).hexdigest() != source.get("source_sha256")):
            raise ValueError("raw_source_hash_mismatch")
    if not tester_log.is_file():
        raise FileNotFoundError("real_tester_log_required")
    with np.load(rates_npz, allow_pickle=False) as package:
        rates = package["rates"]
    with np.load(quotes_npz, allow_pickle=False) as package:
        quotes = package["quotes"]
    expected = python_reference(rates, quotes, tick_size=tick_size,
                                point=point, symbol=symbol)
    actual = read_tester_trace(tester_log, server_offset_seconds=record["tester_server_offset_seconds"])
    result = compare(expected, actual)
    result.update({"schema_version": 1, "strategy_id": "S04",
                   "evidence_class": "MQL_TESTER_RUNTIME_VS_FROZEN_PYTHON",
                   "frozen_source_sha256": hashlib.sha256(
                       Path(r"E:\GPT\Inves\research\overnight-20261010\engine.py").read_bytes()).hexdigest(),
                   "market_file_sha256": hashlib.sha256(rates_npz.read_bytes()).hexdigest(),
                   "quote_file_sha256": hashlib.sha256(quotes_npz.read_bytes()).hexdigest(),
                   "source_record_sha256": hashlib.sha256(source_record.read_bytes()).hexdigest(),
                   "tester_log_sha256": hashlib.sha256(tester_log.read_bytes()).hexdigest(),
                   "utc_mapping_verified": True,
                   "tester_clock_verified": True,
                   "tester_server_offset_seconds": record["tester_server_offset_seconds"],
                   "run_utc": datetime.now(timezone.utc).isoformat()})
    identity = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:20]
    target = catalog.parent / "parity" / f"S04-runtime-{identity}.json"
    atomic_json(target, result, catalog.parent)
    return {"report": str(target), "signal_parity_passed": result["signal_parity_passed"],
            "mismatch_count": result["mismatch_count"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rates-npz", type=Path, required=True)
    parser.add_argument("--quotes-npz", type=Path, required=True)
    parser.add_argument("--source-record", type=Path, required=True)
    parser.add_argument("--tester-log", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tick-size", type=float, required=True)
    parser.add_argument("--point", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(run(rates_npz=args.rates_npz, quotes_npz=args.quotes_npz,
                         source_record=args.source_record, tester_log=args.tester_log,
                         symbol=args.symbol, tick_size=args.tick_size,
                         point=args.point)))


if __name__ == "__main__":
    main()
