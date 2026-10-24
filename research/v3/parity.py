"""Source-pinned S04 signal reference over genuine, saved historical bars.

This checks the research EA's documented decision equation against the frozen
Python rule. It does NOT claim runtime MQL5 or broker-fill parity; those need
an independently running Strategy Tester and source-verified tick history.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .market_import import DEFAULT_CATALOG, DEFAULT_VAULT, atomic_json

SOURCE = Path(r"E:\GPT\Inves\research\overnight-20261010\engine.py")
SOURCE_SHA256 = "7858325bc531382b52bdb9e5fdc910b44cf7ebfe6bea19934e24faafd618ebfb"
POINTER = Path(r"E:\GPT\Inves\research\overnight-20261010\history_pointer.json")
MODEL = {"family": "M1_MOMENTUM_PROXY", "bodyATR": 0.2,
         "minStopATR": 0.5, "session": "ALL", "targetR": 2,
         "id": "OR1_40091e532162"}


def frozen_signals():
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise RuntimeError("frozen_strategy_source_changed")
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    funcs = [node for node in tree.body
             if isinstance(node, ast.FunctionDef) and node.name == "signals"]
    if len(funcs) != 1:
        raise RuntimeError("frozen_signal_symbol_missing_or_ambiguous")
    scope = {"np": np}
    exec(compile(ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[])),
                 str(SOURCE), "exec"), scope)
    return scope["signals"]


def _features(rates, tick_size: float) -> dict:
    t = rates["time"].astype(np.int64)
    o, h, l, c = (rates[name].astype(float) for name in ("open", "high", "low", "close"))
    n = len(c)
    tr = np.maximum(h-l, np.maximum(np.abs(h-np.r_[c[0],c[:-1]]),
                                    np.abs(l-np.r_[c[0],c[:-1]])))
    atr = np.maximum(np.convolve(tr, np.ones(14)/14, "full")[:n], tick_size)
    def ema(period):
        values = np.empty(n)
        values[0] = c[0]
        alpha = 2/(period+1)
        for k in range(1,n):
            values[k] = alpha*c[k]+(1-alpha)*values[k-1]
        return values
    valid = np.ones(n, dtype=bool)
    valid[:100] = False
    for j in np.flatnonzero(np.diff(t) != 60):
        valid[j+1:min(n,j+101)] = False
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "atr": atr,
            "ema20": ema(20), "ema60": ema(60), "valid": valid}


def reference_check(rates, tick_size: float) -> dict:
    d = _features(rates, tick_size)
    expected = frozen_signals()(d, MODEL)
    # Independent translation of S04's closed-candle branch and the EA's
    # 100-bar contiguous-window check. No synthetic prices or fills.
    translated = np.zeros(len(rates), dtype=np.int8)
    for i in range(100,len(rates)):
        if np.any(np.diff(d["t"][i-100:i+1]) != 60):
            continue
        atr = d["atr"][i]
        if atr <= 0:
            continue
        body = (d["c"][i]-d["o"][i])/atr
        if body >= MODEL["bodyATR"] and d["c"][i] > d["c"][i-1]:
            translated[i] = 1
        elif body <= -MODEL["bodyATR"] and d["c"][i] < d["c"][i-1]:
            translated[i] = -1
    mismatches = np.flatnonzero(expected != translated)
    return {"bars_checked": len(rates),
            "frozen_source_signals": int(np.count_nonzero(expected)),
            "translated_signals": int(np.count_nonzero(translated)),
            "mismatches": int(len(mismatches)),
            "first_mismatch_index": int(mismatches[0]) if len(mismatches) else None,
            "first_signal_server_epoch": [int(d["t"][i]) for i in
                                          np.flatnonzero(expected)[:20]]}


def run(vault: Path = DEFAULT_VAULT, catalog: Path = DEFAULT_CATALOG) -> dict:
    pointer = json.loads(POINTER.read_text(encoding="utf-8"))
    frozen_manifest = Path(pointer["path"])
    if hashlib.sha256(frozen_manifest.read_bytes()).hexdigest() != pointer["sha256"]:
        raise RuntimeError("frozen_history_manifest_changed")
    source_manifest = json.loads(frozen_manifest.read_text(encoding="utf-8"))
    rows = []
    for path in sorted((catalog / "sources").glob("*.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row["source_type"] != "LEGACY_BROKER_M1_OFFSET_UNVERIFIED":
            continue
        raw = Path(row["raw_path"])
        if not raw.resolve().is_relative_to(vault.resolve()):
            raise RuntimeError("raw_path_outside_vault")
        if hashlib.sha256(raw.read_bytes()).hexdigest() != row["source_sha256"]:
            raise RuntimeError("vault_raw_hash_mismatch")
        source_row = source_manifest["symbols"][row["symbol"]]
        if source_row["sha256"] != row["source_sha256"]:
            raise RuntimeError("source_manifest_disagrees_with_vault")
        tick_size = float(source_row["spec"]["trade_tick_size"])
        with np.load(raw, allow_pickle=False) as package:
            result = reference_check(package["rates"], tick_size)
        rows.append({"symbol": row["symbol"], "data_sha256": row["source_sha256"],
                     "tick_size_from_frozen_manifest": tick_size, **result})
    identity = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:20]
    result = {
        "check_id": identity, "observed_utc": datetime.now(timezone.utc).isoformat(),
        "strategy_id": "S04", "model_id": MODEL["id"],
        "frozen_source_sha256": SOURCE_SHA256,
        "evidence_class": "PYTHON_RULE_TRANSLATION_PARITY",
        "ea_runtime_parity": "NOT_TESTED", "fill_parity": "NOT_TESTED",
        "timestamps": "SAVED_BROKER_TIME_FIXED_OFFSET_UNVERIFIED",
        "datasets": rows,
        "passed": bool(rows) and all(row["mismatches"] == 0 for row in rows),
    }
    target = catalog.parent / "parity" / ("S04-" + identity + ".json")
    if target.exists():
        existing = json.loads(target.read_text(encoding="utf-8"))
        if existing["datasets"] != rows or existing["frozen_source_sha256"] != SOURCE_SHA256:
            raise RuntimeError("parity_report_identity_collision")
    else:
        atomic_json(target, result, catalog.parent)
    return {"report": str(target), "passed": result["passed"],
            "datasets": len(rows), "signals": sum(r["frozen_source_signals"] for r in rows),
            "mismatches": sum(r["mismatches"] for r in rows)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--vault", type=Path, default=DEFAULT_VAULT)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    print(json.dumps(run(args.vault, args.catalog)))
