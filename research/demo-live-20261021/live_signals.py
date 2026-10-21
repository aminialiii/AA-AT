"""Completed-candle adapter for the hash-pinned original signal function.

It reads terminal rates only as indicator warm-up. It never replays historic
signals or manufactures executions. The last, still-forming MT5 bar is removed.
"""
from __future__ import annotations

import ast
import hashlib
import math
from pathlib import Path

import numpy as np


def original_signals(path: Path, expected_sha256: str):
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise RuntimeError("frozen_strategy_source_changed")
    tree = ast.parse(raw, filename=str(path))
    funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "signals"]
    if len(funcs) != 1:
        raise RuntimeError("original_signals_symbol_missing_or_ambiguous")
    module = ast.fix_missing_locations(ast.Module(body=funcs, type_ignores=[]))
    scope = {"np": np}
    exec(compile(module, str(path), "exec"), scope)
    return scope["signals"]


def completed_features(rates, spec, offset_s: int, now_utc_s: float):
    if rates is None or len(rates) < 260:
        raise ValueError("insufficient_live_warmup")
    server_times = rates["time"].astype(np.int64)
    utc_times = server_times - offset_s
    current_start = int(now_utc_s // 60) * 60
    if abs(int(utc_times[-1]) - current_start) > 60:
        raise ValueError("forming_candle_not_current")
    if int(utc_times[-1]) != current_start:
        raise ValueError("forming_candle_not_aligned")
    a = rates[:-1]
    t = utc_times[:-1]
    if t[-1] != current_start - 60:
        raise ValueError("latest_completed_candle_stale")
    n = len(a)
    o, h, l, c = (a[k].astype(float) for k in ("open", "high", "low", "close"))
    if not all(np.all(np.isfinite(x)) for x in (o, h, l, c)) or np.any(l > h):
        raise ValueError("invalid_rate_fields")
    tick = float(spec.trade_tick_size or spec.point)
    if tick <= 0:
        raise ValueError("invalid_tick_size")
    tr = np.maximum(h-l, np.maximum(np.abs(h-np.r_[c[0], c[:-1]]), np.abs(l-np.r_[c[0], c[:-1]])))
    atr = np.maximum(np.convolve(tr, np.ones(14)/14, "full")[:n], tick)
    def ema(k):
        out = np.empty(n)
        out[0] = c[0]
        alpha = 2/(k+1)
        for i in range(1, n):
            out[i] = alpha*c[i] + (1-alpha)*out[i-1]
        return out
    hi20 = np.r_[np.full(20, np.nan), np.max(np.lib.stride_tricks.sliding_window_view(h, 20), axis=1)[:-1]]
    lo20 = np.r_[np.full(20, np.nan), np.min(np.lib.stride_tricks.sliding_window_view(l, 20), axis=1)[:-1]]
    previous_sp = np.r_[np.full(5, np.nan), np.max(np.lib.stride_tricks.sliding_window_view(a["spread"].astype(float)*spec.point, 5), axis=1)[:-1]]
    spread = np.maximum(np.nan_to_num(previous_sp, nan=tick), tick)*1.25
    valid = np.ones(n, dtype=bool)
    valid[:100] = False
    for j in np.flatnonzero(np.diff(t) != 60):
        valid[j+1:min(n, j+101)] = False
    return {"name": spec.name, "raw": a, "t": t, "o": o, "h": h, "l": l, "c": c,
            "atr": atr, "ema20": ema(20), "ema60": ema(60), "hi20": hi20,
            "lo20": lo20, "spread": spread, "valid": valid, "spec": spec,
            "tick": tick}


def next_signal(signal_function, rates, spec, offset_s, now_utc_s, model):
    d = completed_features(rates, spec, offset_s, now_utc_s)
    signals = signal_function(d, model)
    if len(signals) != len(d["t"]):
        raise RuntimeError("signal_length_mismatch")
    return {"bar_utc_s": int(d["t"][-1]), "side": int(signals[-1]),
            "atr": float(d["atr"][-1]), "spread_model": float(d["spread"][-1]),
            "last3_low": float(min(d["l"][-3:])), "last3_high": float(max(d["h"][-3:])),
            "valid": bool(d["valid"][-1]), "tick_size": d["tick"]}
