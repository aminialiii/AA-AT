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

from .market_import import DEFAULT_CATALOG, atomic_json
from .parity import MODEL, _features, frozen_signals

TRACE = re.compile(
    r"AAAT_V3_TRACE,S04,([A-Za-z0-9_.-]+),(\d{4}\.\d{2}\.\d{2} "
    r"\d{2}:\d{2}:\d{2}),(-?\d+),([0-9.eE+-]+),([0-9.eE+-]+),([01])")


def read_tester_trace(log: Path) -> list[dict]:
    observations = []
    for line_number, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        match = TRACE.search(line)
        if not match:
            continue
        symbol, stamp, side, atr, spread, eligible = match.groups()
        observed = datetime.strptime(stamp, "%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc)
        observations.append({"symbol": symbol, "signal_bar_utc": observed.isoformat(),
                             "side": int(side), "atr": float(atr),
                             "modeled_spread": float(spread), "eligible": bool(int(eligible)),
                             "log_line": line_number})
    return observations


def python_reference(rates: np.ndarray, *, tick_size: float, point: float,
                     symbol: str) -> list[dict]:
    if point <= 0 or tick_size <= 0 or "spread" not in rates.dtype.names:
        raise ValueError("verified_point_tick_and_spread_bars_required")
    if len(rates) and np.any(np.diff(rates["time"].astype(np.int64)) <= 0):
        raise ValueError("bars_must_have_unique_increasing_utc_time")
    d = _features(rates, tick_size)
    signals = frozen_signals()(d, MODEL)
    spread_price = rates["spread"].astype(float) * point
    rows = []
    for i in np.flatnonzero(d["valid"]):
        # EA's CopyRates runs after the next forming candle starts. The
        # original replay also requires an adjacent next entry bar.
        if i + 1 >= len(rates) or d["t"][i+1] - d["t"][i] != 60:
            continue
        previous = max(float(np.max(spread_price[i-5:i])), tick_size) * 1.25
        side = int(signals[i])
        rows.append({"symbol": symbol,
                     "signal_bar_utc": datetime.fromtimestamp(int(d["t"][i]), timezone.utc).isoformat(),
                     "side": side, "atr": float(d["atr"][i]),
                     "modeled_spread": previous,
                     "eligible": bool(side and previous / d["atr"][i] <= .25)})
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
        for field in ("side", "eligible", "atr", "modeled_spread"):
            left, right = e[key][field], a[key][field]
            different = (abs(left-right) > price_tolerance if field in ("atr", "modeled_spread")
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


def run(*, rates_npz: Path, tester_log: Path, symbol: str, tick_size: float,
        point: float, utc_verified: bool, catalog: Path = DEFAULT_CATALOG) -> dict:
    if not utc_verified:
        raise ValueError("source_utc_mapping_not_verified")
    if not tester_log.is_file():
        raise FileNotFoundError("real_tester_log_required")
    with np.load(rates_npz, allow_pickle=False) as package:
        expected = python_reference(package["rates"], tick_size=tick_size,
                                    point=point, symbol=symbol)
    actual = read_tester_trace(tester_log)
    result = compare(expected, actual)
    result.update({"schema_version": 1, "strategy_id": "S04",
                   "evidence_class": "MQL_TESTER_RUNTIME_VS_FROZEN_PYTHON",
                   "frozen_source_sha256": hashlib.sha256(
                       Path(r"E:\GPT\Inves\research\overnight-20261010\engine.py").read_bytes()).hexdigest(),
                   "market_file_sha256": hashlib.sha256(rates_npz.read_bytes()).hexdigest(),
                   "tester_log_sha256": hashlib.sha256(tester_log.read_bytes()).hexdigest(),
                   "utc_mapping_verified": True,
                   "run_utc": datetime.now(timezone.utc).isoformat()})
    identity = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()[:20]
    target = catalog.parent / "parity" / f"S04-runtime-{identity}.json"
    atomic_json(target, result, catalog.parent)
    return {"report": str(target), "signal_parity_passed": result["signal_parity_passed"],
            "mismatch_count": result["mismatch_count"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rates-npz", type=Path, required=True)
    parser.add_argument("--tester-log", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tick-size", type=float, required=True)
    parser.add_argument("--point", type=float, required=True)
    parser.add_argument("--utc-verified", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(rates_npz=args.rates_npz, tester_log=args.tester_log,
                         symbol=args.symbol, tick_size=args.tick_size,
                         point=args.point, utc_verified=args.utc_verified)))


if __name__ == "__main__":
    main()
