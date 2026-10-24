"""Pure, research-only tick-path trade-management counterfactuals.

No broker API, warehouse write, or campaign trade is produced here. Callers
must supply recorded broker Bid/Ask ticks and provenance-backed contract/cost
specifications. An unavailable input returns INSUFFICIENT_EVIDENCE.
"""
from __future__ import annotations

from datetime import datetime
from math import isfinite
import re


def _seconds(raw: str) -> float:
    value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    if value.tzinfo is None:
        raise ValueError("timezone_required")
    return value.timestamp()


def evaluate(trade: dict, ticks: list[dict], scenario: dict,
             cost: dict, *, max_gap_seconds: int = 60) -> dict:
    """Evaluate a frozen management scenario using close-side tick quotes.

    Supported independent or combined rules: stop_r, target_r,
    break_even_trigger_r, trailing_activation_r/trailing_distance_r,
    partial_target_r/partial_fraction, and time_exit_seconds. A finite
    max_holding_seconds is mandatory. All prices are actual recorded quotes;
    hypothetical fills remain COUNTERFACTUAL, never DEMO executions.
    """
    provenance = {tick.get("source_sha256") for tick in ticks}
    if (not ticks or len(provenance) != 1 or None in provenance or
            not re.fullmatch(r"[0-9a-f]{64}", next(iter(provenance))) or
            any(tick.get("source_type") != "BROKER_EXPORT" for tick in ticks)):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "broker_bid_ask_source_required"}
    required = ("volume", "initial_risk_currency", "entry_price", "initial_sl",
                "entry_utc", "direction")
    if any(trade.get(key) is None for key in required):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "incomplete_trade_facts"}
    if any(cost.get(key) is None for key in (
            "account_currency_value_per_price_unit_per_lot",
            "commission_round_trip_currency", "adverse_exit_slippage_price",
            "financing_per_day_currency", "contract_spec_sha256")):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "verified_contract_and_cost_model_required"}
    if not re.fullmatch(r"[0-9a-f]{64}", str(cost["contract_spec_sha256"])):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "contract_provenance_hash_required"}
    side = trade["direction"]
    if side not in {"BUY", "SELL"}:
        raise ValueError("invalid_trade_direction")
    sign = 1 if side == "BUY" else -1
    entry = float(trade["entry_price"])
    initial_sl = float(trade["initial_sl"])
    risk_distance = (entry - initial_sl) * sign
    volume = float(trade["volume"])
    initial_risk = float(trade["initial_risk_currency"])
    per_price_unit = float(cost["account_currency_value_per_price_unit_per_lot"])
    commission = float(cost["commission_round_trip_currency"])
    slippage = float(cost["adverse_exit_slippage_price"])
    financing_day = float(cost["financing_per_day_currency"])
    if (min(risk_distance, volume, initial_risk, per_price_unit) <= 0 or
            min(commission, slippage, financing_day) < 0 or
            not all(isfinite(x) for x in (risk_distance, volume, initial_risk,
                                            per_price_unit, commission, slippage,
                                            financing_day))):
        raise ValueError("invalid_risk_or_cost")
    horizon = scenario.get("max_holding_seconds")
    if not isinstance(horizon, (int, float)) or not 0 < horizon <= 30 * 86400:
        raise ValueError("finite_max_holding_seconds_required")
    params = {name: scenario.get(name) for name in (
        "stop_r", "target_r", "break_even_trigger_r",
        "trailing_activation_r", "trailing_distance_r",
        "partial_target_r", "partial_fraction", "time_exit_seconds")}
    for name in ("stop_r", "target_r", "break_even_trigger_r",
                 "trailing_activation_r", "trailing_distance_r", "partial_target_r"):
        if params[name] is not None and (not isfinite(float(params[name])) or
                                         float(params[name]) <= 0):
            raise ValueError("invalid_scenario_parameter:" + name)
    if params["partial_target_r"] is not None and not (
            params["partial_fraction"] is not None and
            0 < float(params["partial_fraction"]) < 1):
        raise ValueError("partial_fraction_required")
    if (params["trailing_activation_r"] is None) != (
            params["trailing_distance_r"] is None):
        raise ValueError("complete_trailing_rule_required")
    if (params["time_exit_seconds"] is not None and
            not 0 < float(params["time_exit_seconds"]) <= horizon):
        raise ValueError("invalid_time_exit")
    start = _seconds(trade["entry_utc"])
    deadline = start + horizon
    stop = entry - sign * risk_distance * float(params["stop_r"] or 1)
    target_r = params["target_r"]
    if target_r is None:
        if trade.get("initial_tp") is None:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "target_not_recorded"}
        target_r = (float(trade["initial_tp"]) - entry) * sign / risk_distance
    target = entry + sign * risk_distance * float(target_r)
    if (target - entry) * sign <= 0:
        raise ValueError("target_required_on_profitable_side")
    partial_target = (entry + sign * risk_distance * float(params["partial_target_r"])
                      if params["partial_target_r"] is not None else None)
    remaining = 1.0
    gross = 0.0
    partials = []
    favorable = 0.0
    previous = None
    for tick in ticks:
        when = _seconds(tick["time_utc"])
        bid, ask = float(tick["bid"]), float(tick["ask"])
        if bid <= 0 or ask < bid:
            raise ValueError("invalid_bid_ask_tick")
        if previous is not None and when < previous:
            raise ValueError("unordered_ticks")
        if when < start:
            previous = when
            continue
        if when > deadline:
            break
        if ((previous is None and when - start > max_gap_seconds) or
                (previous is not None and when - max(previous, start) > max_gap_seconds)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "tick_gap",
                    "source_sha256": next(iter(provenance))}
        previous = when
        quote = bid if side == "BUY" else ask
        move = (quote - entry) * sign
        favorable = max(favorable, move)
        if params["break_even_trigger_r"] is not None and (
                favorable >= float(params["break_even_trigger_r"]) * risk_distance):
            stop = max(stop, entry) if side == "BUY" else min(stop, entry)
        stopped = quote <= stop if side == "BUY" else quote >= stop
        targeted = quote >= target if side == "BUY" else quote <= target
        timed = (params["time_exit_seconds"] is not None and
                 when >= start + float(params["time_exit_seconds"]))
        if partial_target is not None and remaining == 1.0 and (
                (quote >= partial_target) if side == "BUY" else
                (quote <= partial_target)) and not stopped:
            fraction = float(params["partial_fraction"])
            # Conservative target fill at specified threshold, with adverse
            # slippage. This is an assumption, not an observed broker fill.
            fill = partial_target - sign * slippage
            gross += (fill - entry) * sign * volume * fraction * per_price_unit
            remaining -= fraction
            partials.append({"utc": tick["time_utc"], "fraction": fraction,
                             "assumed_fill_price": fill})
        if stopped or targeted or timed:
            reason = "STOP" if stopped else "TARGET" if targeted else "TIME"
            fill = quote
            if targeted:
                fill = min(quote, target) if side == "BUY" else max(quote, target)
            fill -= sign * slippage
            gross += (fill - entry) * sign * volume * remaining * per_price_unit
            financing = financing_day * ((when - start) / 86400)
            net = gross - commission - financing
            return {
                "status": "COUNTERFACTUAL", "evidence_class": "COUNTERFACTUAL",
                "source_sha256": next(iter(provenance)),
                "contract_spec_sha256": cost["contract_spec_sha256"],
                "exit_utc": tick["time_utc"], "exit_reason": reason,
                "assumed_exit_price": fill, "partial_exits": partials,
                "gross_pnl_currency": gross, "net_pnl_currency": net,
                "realized_r": net / initial_risk,
                "assumptions": ["Conservative threshold target fill",
                                "Explicit adverse slippage and financing model",
                                "Static account-currency value per price unit"],
            }
        if (params["trailing_activation_r"] is not None and
                favorable >= float(params["trailing_activation_r"]) * risk_distance):
            candidate = quote - sign * risk_distance * float(params["trailing_distance_r"])
            stop = max(stop, candidate) if side == "BUY" else min(stop, candidate)
    return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unresolved_before_horizon",
            "source_sha256": next(iter(provenance))}
