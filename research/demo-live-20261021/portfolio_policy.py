"""Pure portfolio admission policy; importing this module never connects to MT5."""
from __future__ import annotations

import asyncio
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path


class SharedExposureBlocked(RuntimeError):
    """Shared broker exposure is not fully owned or priced; retry a later signal."""


def may_wait_for_startup_quotes(reason: str, already_activated: bool,
                                same_policy: bool) -> bool:
    """Only an existing verified campaign may wait for transient quote recovery."""
    return (already_activated and same_policy and
            reason.startswith(("stale_or_future_quote:",
                               "broker_clock_or_quotes_inconsistent",
                               "insufficient_broker_clock_samples")))


@dataclass(frozen=True)
class Exposure:
    kind: str
    risk: float | None
    symbol: str = ""
    strategy: str = ""


@dataclass(frozen=True)
class Admission:
    allowed: bool
    reason: str
    occupied_slots: int
    committed_risk: float
    risk_limit: float


class PortfolioSupervisor:
    """One lock spans snapshot, durable intent reservation, and broker submission."""

    def __init__(self, max_positions: int, max_risk_fraction: float):
        if max_positions < 1 or not 0 < max_risk_fraction < 1:
            raise ValueError("invalid_portfolio_policy")
        self.max_positions = max_positions
        self.max_risk_fraction = max_risk_fraction
        self.lock = asyncio.Lock()

    def admit(self, equity: float, positions, pending, reservations,
              candidate_risk: float) -> Admission:
        if not math.isfinite(equity) or equity <= 0:
            raise SharedExposureBlocked("portfolio_equity_unknown")
        exposures = tuple(positions) + tuple(pending) + tuple(reservations)
        occupied = len(exposures)
        if occupied >= self.max_positions:
            return Admission(False, "portfolio_position_slots_full", occupied, 0.0,
                             equity * self.max_risk_fraction)
        if any(x.risk is None or not math.isfinite(x.risk) or x.risk < 0 for x in exposures):
            raise SharedExposureBlocked("pending_or_open_risk_unknown")
        if not math.isfinite(candidate_risk) or candidate_risk <= 0:
            raise SharedExposureBlocked("candidate_risk_unknown")
        committed = sum(x.risk for x in exposures)
        limit = equity * self.max_risk_fraction
        if committed + candidate_risk > limit + 1e-9:
            return Admission(False, "portfolio_open_and_pending_risk_cap", occupied,
                             committed, limit)
        return Admission(True, "admitted", occupied, committed, limit)


def worst_fill_risk(native_loss, side: int, symbol: str, volume: float,
                    requested_entry: float, stop: float, deviation_points: int,
                    point: float, cost_reserve: float) -> tuple[float, float]:
    """Reserve stop risk at the most adverse permitted fill, plus all costs.

    This deliberately retains the full cost reserve after adding fill movement.
    A broker fill beyond its requested deviation still triggers the post-fill
    breaker; this pre-trade bound does not replace that check.
    """
    values = (volume, requested_entry, stop, point, cost_reserve)
    if (side not in (-1, 1) or deviation_points < 0 or
            any(not math.isfinite(x) for x in values) or
            volume <= 0 or requested_entry <= 0 or point <= 0 or cost_reserve < 0):
        raise ValueError("worst_fill_risk_inputs_invalid")
    adverse_entry = requested_entry + side * deviation_points * point
    if adverse_entry <= 0:
        raise ValueError("worst_fill_entry_invalid")
    price_risk = native_loss(side, symbol, volume, adverse_entry, stop)
    if not math.isfinite(price_risk) or price_risk <= 0:
        raise ValueError("worst_fill_price_risk_unknown")
    return price_risk + cost_reserve, price_risk


def load_policy(path: Path, baseline: dict) -> tuple[dict, str]:
    raw = path.read_bytes()
    policy = json.loads(raw)
    if set(policy) != {"policy_version", "max_positions_account", "max_open_fraction",
                       "initial_evaluation_trades", "continue_after_milestone"}:
        raise RuntimeError("risk_policy_fields_invalid")
    if (policy["policy_version"] != 2 or policy["max_positions_account"] != 5
            or policy["max_open_fraction"] != 0.02
            or policy["initial_evaluation_trades"] != baseline["target_trades_per_strategy"]
            or policy["continue_after_milestone"] is not True):
        raise RuntimeError("risk_policy_not_authorized_version")
    effective = dict(baseline)
    effective["max_positions_account"] = policy["max_positions_account"]
    effective["max_open_fraction"] = policy["max_open_fraction"]
    return effective, hashlib.sha256(raw).hexdigest()
