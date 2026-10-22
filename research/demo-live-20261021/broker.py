"""Only broker transport for this campaign. Never logs in or switches accounts."""
from __future__ import annotations

import math
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, "E:/GPT/Inves/.skill-tools")
import MetaTrader5 as mt5
from portfolio_policy import SharedExposureBlocked

SYMBOLS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD")


def plain(x):
    if hasattr(x, "_asdict"):
        return {k: plain(v) for k, v in x._asdict().items()}
    if isinstance(x, (list, tuple)):
        return [plain(v) for v in x]
    if isinstance(x, dict):
        return {k: plain(v) for k, v in x.items()}
    return x


class Broker:
    def __init__(self, config):
        self.config = config
        self.connected = False
        self.offset_s = None

    def attach(self):
        if self.connected:
            return
        if not mt5.initialize(self.config["terminal_path"], timeout=5000):
            raise RuntimeError(f"terminal_unavailable:{mt5.last_error()}")
        self.connected = True
        self.guard()

    def guard(self):
        """Fails closed on any account, connection, permission, or mode discrepancy."""
        a, t = mt5.account_info(), mt5.terminal_info()
        if a is None or t is None:
            raise RuntimeError("terminal_or_account_unavailable")
        expected = self.config["account"]
        if not (a.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO
                and str(a.login) == str(expected["login"])
                and a.server == expected["server"]
                and a.currency == expected["currency"]
                and a.margin_mode == mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING):
            raise RuntimeError("DEMO_ACCOUNT_GUARD_FAILED")
        if not (t.connected and t.trade_allowed and a.trade_allowed and a.trade_expert):
            raise RuntimeError("DEMO_ROUTING_PERMISSION_OR_CONNECTIVITY_FAILED")
        if not all(math.isfinite(float(v)) for v in (a.balance, a.equity, a.margin_free)) or a.equity <= 0:
            raise RuntimeError("account_equity_invalid")
        return a, t

    def exposure(self):
        positions, orders = mt5.positions_get(), mt5.orders_get()
        if positions is None or orders is None:
            raise RuntimeError(f"exposure_query_failed:{mt5.last_error()}")
        return positions, orders

    def clock_offset(self):
        now = time.time()
        raw_ages = []
        for symbol in SYMBOLS:
            tick = mt5.symbol_info_tick(symbol)
            if tick is not None:
                raw_ages.append(now - tick.time_msc / 1000)
        if len(raw_ages) < 5:
            raise RuntimeError("insufficient_broker_clock_samples")
        offset = round(-statistics.median(raw_ages) / 3600) * 3600
        corrected = [age + offset for age in raw_ages]
        if sum(-2 <= age <= 10 for age in corrected) < 5:
            raise RuntimeError("broker_clock_or_quotes_inconsistent")
        if self.offset_s is not None and self.offset_s != offset:
            raise RuntimeError("broker_clock_offset_changed_during_campaign")
        self.offset_s = offset
        return offset

    def symbol_and_tick(self, symbol):
        spec = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if spec is None or tick is None or not spec.visible or spec.trade_mode != mt5.SYMBOL_TRADE_MODE_FULL:
            raise RuntimeError(f"symbol_unavailable:{symbol}")
        if self.offset_s is None:
            raise RuntimeError("broker_clock_not_verified")
        age = time.time() - tick.time_msc / 1000 + self.offset_s
        if not (-2 <= age <= self.config["risk"]["max_quote_age_s"]):
            raise RuntimeError(f"stale_or_future_quote:{symbol}:{age:.3f}")
        if not (tick.bid > 0 and tick.ask >= tick.bid):
            raise RuntimeError(f"invalid_bid_ask:{symbol}")
        return spec, tick, age

    def rates(self, symbol):
        rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, 500)
        if rates is None:
            raise RuntimeError(f"live_rates_unavailable:{symbol}:{mt5.last_error()}")
        return rates

    def native_loss(self, side, symbol, volume, entry, stop):
        action = mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL
        p = mt5.order_calc_profit(action, symbol, volume, entry, stop)
        if p is None or not math.isfinite(p) or p >= 0:
            raise RuntimeError(f"native_stop_loss_unknown:{symbol}:{mt5.last_error()}")
        return -float(p)

    def native_margin(self, side, symbol, volume, entry):
        action = mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL
        margin = mt5.order_calc_margin(action, symbol, volume, entry)
        if margin is None or not math.isfinite(margin) or margin <= 0:
            raise RuntimeError(f"native_margin_unknown:{symbol}:{mt5.last_error()}")
        return float(margin)

    def cost_reserve(self, side, symbol, volume, entry, spec, tick):
        """Conservative round-trip commission, spread, and fill-deviation reserve."""
        spread = float(tick.ask - tick.bid)
        if not math.isfinite(spread) or spread < 0:
            raise RuntimeError("native_cost_reserve_unknown")
        action = mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL
        allowance = 2 * spread + 5 * float(spec.point)
        value = mt5.order_calc_profit(action, symbol, volume, entry,
                                      entry + side * allowance)
        if value is None or not math.isfinite(value):
            raise RuntimeError("native_cost_reserve_unknown")
        return (self.config["risk"]["commission_reserve_per_lot_usd"] * volume
                + abs(float(value)))

    def target_price(self, side, symbol, volume, entry, risk, tick_size, digits):
        """Find >=2R account-currency gross target using native broker calculation."""
        action = mt5.ORDER_TYPE_BUY if side == 1 else mt5.ORDER_TYPE_SELL
        lo, hi = 0.0, max(tick_size * 2, entry * 1e-5)
        for _ in range(40):
            p = mt5.order_calc_profit(action, symbol, volume, entry, entry + side * hi)
            if p is None:
                raise RuntimeError("native_target_profit_unavailable")
            if p >= 2 * risk:
                break
            hi *= 2
        else:
            raise RuntimeError("native_target_unavailable")
        for _ in range(45):
            mid = (lo + hi) / 2
            p = mt5.order_calc_profit(action, symbol, volume, entry, entry + side * mid)
            if p is None:
                raise RuntimeError("native_target_profit_unavailable")
            if p >= 2 * risk:
                hi = mid
            else:
                lo = mid
        ticks = math.ceil((hi - 1e-10 * tick_size) / tick_size)
        tp = round(entry + side * ticks * tick_size, digits)
        actual = mt5.order_calc_profit(action, symbol, volume, entry, tp)
        if actual is None or actual + .01 < 2 * risk:
            raise RuntimeError("target_rounding_below_2R")
        return tp

    def send(self, request, expected_position_tickets, expected_order_tickets,
             minimum_equity, pre_send_gate):
        # The account check is intentionally adjacent to the one route-capable call.
        account, _ = self.guard()
        if float(account.equity) <= float(minimum_equity):
            raise RuntimeError("equity_halt_at_order_submission")
        self.clock_offset()
        positions, orders = self.exposure()
        if ({int(p.ticket) for p in positions} != set(expected_position_tickets)
                or {int(o.ticket) for o in orders} != set(expected_order_tickets)):
            raise SharedExposureBlocked("shared_exposure_changed_before_order_submission")
        spec, tick, _ = self.symbol_and_tick(request["symbol"])
        current = tick.ask if request["type"] == mt5.ORDER_TYPE_BUY else tick.bid
        if abs(float(request["price"]) - current) > request["deviation"] * spec.point + 1e-12:
            raise SharedExposureBlocked("quote_moved_before_order_submission")
        # The service rechecks both global limits against fresh broker exposure
        # under its one-process router lock immediately before this only send.
        pre_send_gate(account, positions, orders)
        return mt5.order_send(request)
