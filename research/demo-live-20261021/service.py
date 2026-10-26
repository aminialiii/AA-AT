"""Fail-closed, original-rule, market-time DEMO campaign.

Run only with --run. --preflight is read-only. This process never logs in,
switches account, replays bars, fabricates fills, or routes to a REAL account.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import html
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import msvcrt
from broker import Broker, mt5, plain, SYMBOLS
from live_signals import original_signals, next_signal
from portfolio_policy import (Exposure, PortfolioSupervisor, SharedExposureBlocked,
                              load_policy, may_wait_for_startup_quotes, worst_fill_risk)
from report import refresh as refresh_report
from state import State, utc
from worker_control import ControlStore, persistent_risk_breakers

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "campaign_config.json"
POLICY_PATH = HERE / "risk_policy.json"
DATA = HERE / "runtime"
STOP = DATA / "EMERGENCY_STOP"


def save_json_atomic(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def load_config():
    raw = CONFIG_PATH.read_bytes()
    config = json.loads(raw)
    config["risk"], config["_risk_policy_sha256"] = load_policy(POLICY_PATH, config["risk"])
    # The frozen strategy/config identity remains the original campaign hash.
    # Authorized portfolio policy revisions have their own durable audit trail.
    return config, hashlib.sha256(raw).hexdigest()


class SingleInstance:
    def __init__(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open("a+b")
        self.file.seek(0)
        self.file.write(b"1")
        self.file.flush()
        self.file.seek(0)
        try:
            msvcrt.locking(self.file.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError("another_campaign_service_process_is_running")


class Campaign:
    def __init__(self, config, config_hash):
        self.config = config
        self.hash = config_hash
        self.state = State(DATA, config_hash)
        self.controls = ControlStore(DATA / "command_center.sqlite3")
        self.broker = Broker(config)
        self.signals = original_signals(Path(config["strategy_source"]), config["strategy_source_sha256"])
        if hashlib.sha256(Path(config["registration_source"]).read_bytes()).hexdigest() != config["registration_sha256"]:
            raise RuntimeError("frozen_registration_changed")
        self.workers = {w["id"]: w for w in config["workers"]}
        self.queues = {sid: asyncio.Queue(maxsize=16) for sid in self.workers}
        self.breakers = {sid: w["blocker"] for sid,w in self.workers.items() if w["status"] == "BLOCKED"}
        # A fill that exceeded its risk cap must not become tradable merely
        # because the Windows task or dashboard supervisor restarted.
        self.breakers.update(persistent_risk_breakers(self.state.db, self.workers))
        self.supervisor = PortfolioSupervisor(config["risk"]["max_positions_account"],
                                              config["risk"]["max_open_fraction"])
        self.router = self.supervisor.lock
        self.shared_status = "STARTING"
        self.last_shared_error = None
        self.last_status_write = 0.0
        self.market_warn_last = {}
        self.shared_warn_last = {}
        self.worker_heartbeat = {sid: None for sid in self.workers}
        self.worker_started = {sid: time.time() for sid in self.workers}
        self.last_signal = {sid: None for sid in self.workers}
        self.last_execution = {sid: None for sid in self.workers}
        self.worker_tasks = {}

    def set_shared(self, status, reason=None):
        if status != self.shared_status or reason != self.last_shared_error:
            if reason:
                # Quote-feed interruptions may flap; retain the health state but
                # avoid writing the same non-critical event every few seconds.
                critical=any(k in reason for k in ("DEMO_ACCOUNT_GUARD_FAILED","unowned_or_unreconciled_position",
                                                 "ambiguous_prepared_intent","protective_orders_changed","daily_equity_loss_halt",
                                                 "peak_equity_drawdown_halt"))
                if critical or time.time()-self.shared_warn_last.get(reason,0)>3600:
                    self.state.event("SHARED", reason)
                    self.shared_warn_last[reason]=time.time()
            self.shared_status, self.last_shared_error = status, reason

    def permanent_halt(self, reason):
        if not STOP.exists():
            STOP.write_text(f"{utc()} {reason}\n",encoding="utf-8")
        self.state.event("SHARED",f"PERMANENT_HALT:{reason}")

    def snapshot(self):
        a,t = self.broker.guard()
        positions,orders = self.broker.exposure()
        self.broker.clock_offset()
        return a,t,positions,orders

    def check_ownership(self, positions, orders, prepared_key=None):
        for pos in positions:
            row = self.state.open_for_position(pos.ticket)
            if row is None or row["magic"] != pos.magic or row["symbol"] != pos.symbol:
                raise RuntimeError(f"unowned_or_unreconciled_position:{pos.ticket}")
            req = json.loads(row["request_json"])
            if abs(float(pos.sl) - float(req["sl"])) > 2e-8 or abs(float(pos.tp) - float(req["tp"])) > 2e-8:
                raise RuntimeError(f"protective_orders_changed_or_missing:{pos.ticket}")
        for row in self.state.outstanding():
            if row["state"] == "PREPARED" and row["signal_key"] != prepared_key:
                raise RuntimeError(f"ambiguous_prepared_intent:{row['signal_key']}")

    def portfolio_exposures(self, positions, orders, exclude_key=None):
        """Price owned exposure from broker stops; unknown pending risk blocks entries."""
        current, pending, reserved = [], [], []
        for pos in positions:
            row = self.state.open_for_position(pos.ticket)
            if row is None:
                raise RuntimeError(f"unowned_or_unreconciled_position:{pos.ticket}")
            side = 1 if pos.type == mt5.POSITION_TYPE_BUY else -1
            spec, tick, _ = self.broker.symbol_and_tick(pos.symbol)
            native = self.broker.native_loss(side, pos.symbol, float(pos.volume),
                                             float(pos.price_open), float(pos.sl))
            reserve = self.broker.cost_reserve(side, pos.symbol, float(pos.volume),
                                               float(pos.price_open), spec, tick)
            current.append(Exposure("POSITION", max(float(row["planned_risk"]), native + reserve),
                                    pos.symbol, row["strategy"]))
        for order in orders:
            row = self.state.open_for_order(order.ticket)
            if (row is None or row["state"] != "PENDING" or
                    row["magic"] != order.magic or row["symbol"] != order.symbol):
                # Count this pending order as a slot, but its unverified risk is
                # unbounded for admission. No new order may route until resolved.
                pending.append(Exposure("PENDING", None, order.symbol))
                continue
            buy_types = (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_BUY_STOP,
                         mt5.ORDER_TYPE_BUY_STOP_LIMIT)
            sell_types = (mt5.ORDER_TYPE_SELL_LIMIT, mt5.ORDER_TYPE_SELL_STOP,
                          mt5.ORDER_TYPE_SELL_STOP_LIMIT)
            if order.type not in buy_types + sell_types or not order.sl or not order.volume_current:
                pending.append(Exposure("PENDING", None, order.symbol, row["strategy"]))
                continue
            side = 1 if order.type in buy_types else -1
            spec, tick, _ = self.broker.symbol_and_tick(order.symbol)
            native = self.broker.native_loss(side, order.symbol, float(order.volume_current),
                                             float(order.price_open), float(order.sl))
            reserve = self.broker.cost_reserve(side, order.symbol, float(order.volume_current),
                                               float(order.price_open), spec, tick)
            pending.append(Exposure("PENDING", max(float(row["planned_risk"]), native+reserve),
                                    order.symbol, row["strategy"]))
        for row in self.state.outstanding():
            if row["state"] == "PREPARED" and row["signal_key"] != exclude_key:
                reserved.append(Exposure("RESERVED", float(row["planned_risk"]),
                                         row["symbol"], row["strategy"]))
        if any(x.risk is None for x in pending):
            raise SharedExposureBlocked(f"pending_orders_on_shared_account_require_manual_reconciliation:{len(positions)+len(orders)}_occupied")
        return current, pending, reserved

    def reconcile(self, positions):
        live_tickets = {int(p.ticket) for p in positions}
        for row in self.state.outstanding():
            if row["state"] != "OPEN":
                continue
            position_id = int(row["position_id"])
            if position_id in live_tickets:
                continue
            deals = mt5.history_deals_get(position=position_id)
            if not deals:
                raise RuntimeError(f"closed_position_deals_unavailable:{position_id}")
            opening = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
            closing = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
            opened = sum(float(d.volume) for d in opening)
            closed = sum(float(d.volume) for d in closing)
            if not opening or not closing or abs(opened - closed) > 1e-8:
                raise RuntimeError(f"position_close_not_fully_reconciled:{position_id}")
            if any(int(d.position_id) != position_id for d in deals):
                raise RuntimeError(f"position_id_mismatch:{position_id}")
            evidence = [self.state.evidence(row["strategy"], "BROKER_DEAL", plain(d)) for d in deals]
            order_ids = sorted({int(d.order) for d in deals})
            for order_id in order_ids:
                orders = mt5.history_orders_get(ticket=order_id)
                if not orders:
                    raise RuntimeError(f"broker_order_history_missing:{order_id}")
                evidence += [self.state.evidence(row["strategy"], "BROKER_ORDER", plain(o)) for o in orders]
            profit = sum(float(d.profit) for d in deals)
            commission = sum(float(d.commission) for d in deals)
            swap = sum(float(d.swap) for d in deals)
            fee = sum(float(d.fee) for d in deals)
            open_ts = min(int(d.time_msc) for d in opening)
            close_ts = max(int(d.time_msc) for d in closing)
            if close_ts <= open_ts:
                raise RuntimeError(f"nonchronological_broker_deals:{position_id}")
            req = json.loads(row["request_json"])
            record = {"execution_kind":"REAL_TIME_DEMO_BROKER", "fully_closed":True,
                      "campaign_id":self.config["campaign_id"], "config_sha256":self.hash,
                      "risk_policy_sha256":row["policy_sha256"],
                      "strategy_id":row["strategy"], "symbol":row["symbol"],
                      "account_login":self.config["account"]["login"],
                      "account_server":self.config["account"]["server"],
                      "account_trade_mode":"DEMO", "signal_bar_server_time":row["bar"]+self.broker.offset_s,
                      "signal_utc":datetime.fromtimestamp(row["bar"]+60,timezone.utc).isoformat(),
                      "entry_utc":datetime.fromtimestamp(open_ts/1000-self.broker.offset_s,timezone.utc).isoformat(),
                      "exit_utc":datetime.fromtimestamp(close_ts/1000-self.broker.offset_s,timezone.utc).isoformat(),
                      "opening_order_id":int(opening[0].order), "closing_order_ids":[int(d.order) for d in closing],
                      "opening_deal_ids":[int(d.ticket) for d in opening],
                      "closing_deal_ids":[int(d.ticket) for d in closing],
                      "position_id":position_id, "magic":int(row["magic"]),
                      "opened_volume":opened,"closed_volume":closed,
                      "entry_price":float(opening[0].price),"exit_price":float(closing[-1].price),
                      "requested_entry_price":float(req["price"]),"stop_loss":float(req["sl"]),
                      "take_profit":float(req["tp"]),"initial_risk_account_currency":float(row["planned_risk"]),
                      "broker_gross_profit":profit,"broker_commission":commission,
                      "broker_swap":swap,"broker_fees":fee,
                      "broker_net_profit":profit+commission+swap+fee,
                      "broker_evidence":evidence}
            self.state.evidence(row["strategy"], "RECONCILED_CLOSE", record)
            self.state.mark_closed(position_id,row["strategy"],row["signal_key"],record)
            refresh_report()

    def equity_gate(self, account):
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if self.state.get("equity_day") != day:
            self.state.put("equity_day", day)
            self.state.put("day_start_equity", float(account.equity))
        peak = max(float(account.equity), float(self.state.get("peak_equity", account.equity)))
        self.state.put("peak_equity", peak)
        if (self.config["risk"].get("daily_equity_halt_enabled", True)
                and float(account.equity) <= float(self.state.get("day_start_equity")) * (1-self.config["risk"]["daily_equity_loss_fraction"])):
            raise RuntimeError("daily_equity_loss_halt")
        if (self.config["risk"].get("peak_equity_halt_enabled", True)
                and float(account.equity) <= peak * (1-self.config["risk"]["peak_equity_drawdown_fraction"])):
            raise RuntimeError("peak_equity_drawdown_halt")

    def entry_request(self, worker, symbol, observed, spec, tick, account):
        side = observed["side"]
        model = worker["model"]
        volume = float(spec.volume_min)
        if volume <= 0 or spec.volume_step <= 0 or not math.isclose(volume/spec.volume_step,round(volume/spec.volume_step),abs_tol=1e-7):
            raise RuntimeError("broker_minimum_volume_invalid")
        spread = float(tick.ask-tick.bid)
        atr = float(observed["atr"])
        if atr <= 0 or spread / atr > .25:
            raise ValueError("strategy_spread_atr_gate")
        entry = float(tick.ask if side == 1 else tick.bid)
        size = float(spec.trade_tick_size or spec.point)
        minimum = max(model["minStopATR"] * atr, 4 * spread, spec.trade_stops_level * spec.point)
        if side == 1:
            raw_sl = min(observed["last3_low"]-2*size, entry-minimum)
            sl = math.floor((raw_sl+size*1e-8)/size)*size
        else:
            raw_sl = max(observed["last3_high"]+spread+2*size, entry+minimum)
            sl = math.ceil((raw_sl-size*1e-8)/size)*size
        sl = round(sl, int(spec.digits))
        price_risk = self.broker.native_loss(side,symbol,volume,entry,sl)
        native_margin = self.broker.native_margin(side,symbol,volume,entry)
        tp = self.broker.target_price(side,symbol,volume,entry,price_risk,size,int(spec.digits))
        reserve = self.broker.cost_reserve(side, symbol, volume, entry, spec, tick)
        deviation_points = 5
        total_risk, worst_price_risk = worst_fill_risk(
            self.broker.native_loss, side, symbol, volume, entry, sl,
            deviation_points, float(spec.point), reserve)
        initial_allocation=float(self.state.get("initial_virtual_allocation",float(account.equity)/5))
        realized_for_worker=0.0
        for row in self.state.db.execute("SELECT record_json FROM closed WHERE strategy=?",(worker["id"],)):
            realized_for_worker+=float(json.loads(row[0])["broker_net_profit"])
        allocated=max(0.0,initial_allocation+realized_for_worker)
        if total_risk > min(float(account.equity),allocated)*self.config["risk"]["max_trade_fraction"]:
            raise ValueError(f"broker_min_lot_exceeds_allocated_risk:{total_risk:.4f}")
        if native_margin > self.config["risk"]["max_margin_fraction_of_free"]*float(account.margin_free):
            raise ValueError("new_order_margin_cap")
        if not (spec.filling_mode & 1):
            raise ValueError("FOK_filling_unavailable")
        request = {"action":mt5.TRADE_ACTION_DEAL,"symbol":symbol,"volume":volume,
                   "type":mt5.ORDER_TYPE_BUY if side==1 else mt5.ORDER_TYPE_SELL,
                   "price":entry,"sl":sl,"tp":tp,"deviation":deviation_points,
                   "magic":int(worker["magic"]),"comment":f"DF21{worker['id']}",
                   "type_time":mt5.ORDER_TIME_GTC,"type_filling":mt5.ORDER_FILLING_FOK}
        return request, total_risk, {"price_risk":price_risk,"worst_fill_price_risk":worst_price_risk,
                                     "cost_reserve":reserve,"margin":native_margin,
                                     "allocated_equity":allocated,"live_spread":spread}

    async def route(self, worker, symbol, observed):
        async with self.router:
            with self.controls.admission():
                return await self._route_locked(worker, symbol, observed)

    async def _route_locked(self, worker, symbol, observed):
        sid = worker["id"]
        if STOP.exists():
            raise RuntimeError("EMERGENCY_STOP_FILE_PRESENT")
        if self.controls.emergency() or self.controls.mode(sid) != "RUNNING":
            return
        if sid in self.breakers:
            return
        if time.time()-(observed["bar_utc_s"]+60) > self.config["risk"]["max_signal_age_s"]:
            return
        account,terminal,positions,orders = self.snapshot()
        self.check_ownership(positions,orders)
        self.reconcile(positions)
        self.equity_gate(account)
        current,pending,reserved = self.portfolio_exposures(positions,orders)
        if any(x.symbol == symbol for group in (current,pending,reserved) for x in group):
            return
        if self.state.open_for_strategy(sid):
            return
        spec,tick,age = self.broker.symbol_and_tick(symbol)
        try:
            request,risk,components = self.entry_request(worker,symbol,observed,spec,tick,account)
        except ValueError as exc:
            self.state.evidence(sid,"SIGNAL_SKIPPED",{"symbol":symbol,"bar":observed["bar_utc_s"],"reason":str(exc)})
            return
        admission = self.supervisor.admit(float(account.equity), current, pending,
                                          reserved, risk)
        if not admission.allowed:
            self.state.evidence(sid,"SIGNAL_SKIPPED",{"symbol":symbol,
                "bar":observed["bar_utc_s"],"reason":admission.reason,
                "occupied_slots":admission.occupied_slots,
                "committed_risk":admission.committed_risk,
                "risk_limit":admission.risk_limit})
            return
        key = f"{self.config['campaign_id']}:{sid}:{symbol}:{observed['bar_utc_s']}"
        if self.state.db.execute("SELECT 1 FROM intents WHERE signal_key=?",(key,)).fetchone():
            return
        self.state.evidence(sid,"LIVE_SIGNAL",{"symbol":symbol,"bar":observed["bar_utc_s"],"side":observed["side"],
                                                "model":worker["model"],"risk":components,"quote_age_s":age})
        self.state.prepare(key,sid,symbol,worker["magic"],observed["bar_utc_s"],request,risk)
        floors=[0.0]
        if self.config["risk"].get("daily_equity_halt_enabled", True):
            floors.append(float(self.state.get("day_start_equity"))*(1-self.config["risk"]["daily_equity_loss_fraction"]))
        if self.config["risk"].get("peak_equity_halt_enabled", True):
            floors.append(float(self.state.get("peak_equity"))*(1-self.config["risk"]["peak_equity_drawdown_fraction"]))
        floor=max(floors)
        def pre_send_gate(fresh_account, fresh_positions, fresh_orders):
            if self.controls.emergency() or self.controls.mode(sid) != "RUNNING":
                raise SharedExposureBlocked("worker_or_portfolio_control_latched")
            if time.time()-(observed["bar_utc_s"]+60)>self.config["risk"]["max_signal_age_s"]:
                raise SharedExposureBlocked("signal_expired_before_order_submission")
            if risk > min(float(fresh_account.equity), components["allocated_equity"]) * self.config["risk"]["max_trade_fraction"]:
                raise SharedExposureBlocked("per_trade_risk_cap_changed_before_order_submission")
            self.check_ownership(fresh_positions, fresh_orders, prepared_key=key)
            p2,o2,r2 = self.portfolio_exposures(fresh_positions, fresh_orders,
                                                  exclude_key=key)
            decision = self.supervisor.admit(float(fresh_account.equity),
                                              p2,o2,r2,risk)
            if not decision.allowed:
                raise SharedExposureBlocked(decision.reason)
        try:
            result = self.broker.send(request,{int(p.ticket) for p in positions},
                                      {int(o.ticket) for o in orders},floor,pre_send_gate)
        except SharedExposureBlocked as exc:
            self.state.reject_prepared(key,str(exc))
            self.state.evidence(sid,"SIGNAL_SKIPPED",{"symbol":symbol,
                "bar":observed["bar_utc_s"],"reason":str(exc)})
            return
        self.state.evidence(sid,"BROKER_SEND_RESULT",{"signal_key":key,"result":plain(result),"last_error":mt5.last_error()})
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            self.breakers[sid] = f"order_rejected_or_ambiguous:{None if result is None else result.retcode}"
            self.state.event(sid,self.breakers[sid])
            return
        for _ in range(10):
            current = mt5.positions_get()
            if current is None:
                break
            owned = [p for p in current if p.magic==worker["magic"] and p.symbol==symbol and p.comment==request["comment"]]
            if len(owned)==1:
                pos=owned[0]
                self.state.evidence(sid,"BROKER_POSITION_OPEN",plain(pos))
                if abs(pos.sl-request["sl"])>2e-8 or abs(pos.tp-request["tp"])>2e-8 or abs(pos.volume-request["volume"])>1e-8:
                    raise RuntimeError("broker_position_not_protected_as_requested")
                self.state.mark_sent(key,result,pos.ticket)
                self.last_execution[sid] = utc()
                self.broker.guard()
                actual_price_risk=self.broker.native_loss(observed["side"],symbol,pos.volume,pos.price_open,pos.sl)
                if actual_price_risk+components["cost_reserve"]>components["allocated_equity"]*self.config["risk"]["max_trade_fraction"]:
                    self.breakers[sid]="filled_price_risk_exceeds_cap; protective broker SL/TP retained"
                    self.state.event(sid,self.breakers[sid])
                return
            await asyncio.sleep(.2)
        raise RuntimeError("filled_order_position_not_uniquely_reconciled")

    async def process_commands(self):
        for command in self.controls.pending():
            sid, action = command["worker_id"], command["action"]
            try:
                if action == "EMERGENCY_STOP":
                    self.state.event("SHARED", "dashboard_emergency_stop_latched")
                    self.controls.complete(command["id"], "APPLIED", "new_order_admission_latched; existing broker protection retained")
                    continue
                if sid not in self.workers:
                    raise RuntimeError("unknown_worker")
                if action in {"PAUSE", "STOP"}:
                    # The API already committed the disabling mode under the
                    # cross-process admission lock before it returned.
                    self.controls.complete(command["id"], "APPLIED", "new_signals_disabled; global reconciliation continues")
                    continue
                if self.controls.emergency():
                    raise RuntimeError("emergency_stop_active")
                if sid in self.breakers or self.workers[sid]["status"] == "BLOCKED":
                    raise RuntimeError("worker_blocked")
                async with self.router:
                    account, terminal, positions, orders = self.snapshot()
                    self.check_ownership(positions, orders)
                    self.reconcile(positions)
                    self.equity_gate(account)
                    exposures = self.portfolio_exposures(positions, orders)
                    if len(positions) + len(orders) > self.supervisor.max_positions:
                        raise RuntimeError("portfolio_slots_already_exceeded")
                    if sum(x.risk for group in exposures for x in group) > float(account.equity) * self.supervisor.max_risk_fraction:
                        raise RuntimeError("portfolio_risk_already_exceeded")
                    if action == "START" and self.controls.mode(sid) != "STOPPED":
                        raise RuntimeError("start_requires_stopped_worker")
                    if action == "RESUME" and self.controls.mode(sid) != "PAUSED":
                        raise RuntimeError("resume_requires_paused_worker")
                    if action == "RESTART":
                        if self.state.open_for_strategy(sid):
                            raise RuntimeError("restart_requires_no_outstanding_strategy_intent")
                        task = self.worker_tasks[sid]
                        task.cancel()
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass
                        queue = self.queues[sid]
                        while not queue.empty():
                            queue.get_nowait()
                            queue.task_done()
                        self.worker_started[sid] = time.time()
                        self.worker_heartbeat[sid] = utc()
                        self.worker_tasks[sid] = asyncio.create_task(self.worker_loop(self.workers[sid]), name=sid)
                    else:
                        self.controls.set_mode(sid, "RUNNING")
                    self.controls.complete(command["id"], "APPLIED", "broker_guard_ownership_reconciliation_risk_passed")
            except Exception as exc:
                self.controls.complete(command["id"], "REJECTED", f"{type(exc).__name__}:{exc}")

    async def worker_loop(self, worker):
        sid = worker["id"]
        while not STOP.exists():
            try:
                event = await asyncio.wait_for(self.queues[sid].get(), timeout=10)
            except asyncio.TimeoutError:
                self.worker_heartbeat[sid] = utc()
                continue
            self.worker_heartbeat[sid] = utc()
            try:
                if (worker["status"] == "BLOCKED" or sid in self.breakers or
                        self.controls.emergency() or self.controls.mode(sid) != "RUNNING"):
                    continue
                symbol,rates,spec,offset,dispatch_utc = event
                bar = int(rates["time"][-2])-offset
                previous = self.state.cursor(sid,symbol)
                if previous is None or bar <= previous:
                    self.state.advance(sid,symbol,bar)
                    continue
                self.state.advance(sid,symbol,bar)
                try:
                    observed = next_signal(self.signals,rates,spec,offset,dispatch_utc,worker["model"])
                    if observed["side"]:
                        self.last_signal[sid] = utc()
                        await self.route(worker,symbol,observed)
                except ValueError as exc:
                    self.state.evidence(sid,"DATA_OR_POLICY_SKIP",{"symbol":symbol,"bar":bar,"reason":str(exc)})
                except SharedExposureBlocked as exc:
                    self.state.evidence(sid,"SHARED_EXPOSURE_SKIP",{"symbol":symbol,
                        "bar":bar,"reason":str(exc)})
                except Exception as exc:
                    self.breakers[sid] = f"worker_suspended:{type(exc).__name__}:{exc}"
                    self.state.event(sid,self.breakers[sid])
            finally:
                self.queues[sid].task_done()

    def write_status(self, account=None, positions=(), orders=()):
        now=time.time()
        if now-self.last_status_write < 5:
            return
        self.last_status_write=now
        realized=[]
        by_strategy={sid:[] for sid in self.workers}
        for row in self.state.db.execute("SELECT record_json FROM closed"):
            record=json.loads(row[0])
            realized.append(record)
            by_strategy[record["strategy_id"]].append(record)
        workers=[]
        worker_positions={sid:0 for sid in self.workers}
        worker_unrealized={sid:0.0 for sid in self.workers}
        worker_risk={sid:0.0 for sid in self.workers}
        for pos in positions:
            for sid, definition in self.workers.items():
                if int(pos.magic)==int(definition["magic"]):
                    worker_positions[sid]+=1
                    worker_unrealized[sid]+=float(pos.profit)
                    break
        if account is not None:
            try:
                exposure_groups=self.portfolio_exposures(positions,orders)
                for group in exposure_groups:
                    for exposure in group:
                        if exposure.strategy in worker_risk and exposure.risk is not None:
                            worker_risk[exposure.strategy]+=exposure.risk
            except (RuntimeError,ValueError):
                worker_risk={sid:None for sid in self.workers}
        for sid,w in self.workers.items():
            count=self.state.count_closed(sid)
            target=self.config["risk"]["target_trades_per_strategy"]
            mode=self.controls.mode(sid)
            status=("BLOCKED" if sid in self.breakers else
                    mode if mode != "RUNNING" else
                    "ACTIVE" if self.shared_status=="HEALTHY" else "WAITING_BROKER")
            records=by_strategy[sid]
            rvals=[float(x["broker_net_profit"])/float(x["initial_risk_account_currency"]) for x in records]
            curve=0.0; peak_r=0.0; max_dd_r=0.0
            for rval in rvals:
                curve+=rval; peak_r=max(peak_r,curve); max_dd_r=max(max_dd_r,peak_r-curve)
            workers.append({"id":sid,"name":w["name"],"status":status,"reason":self.breakers.get(sid),
                            "closed_trades":count,"initial_milestone":target,
                            "milestone_reached":count>=target,"continuous_execution":sid not in self.breakers,
                            "magic":w["magic"],
                            "net_demo_pnl":sum(float(x["broker_net_profit"]) for x in records),
                            "expectancy_R":sum(rvals)/len(rvals) if rvals else None,
                            "max_closed_drawdown_R":max_dd_r if rvals else None,
                            "heartbeat":self.worker_heartbeat[sid],
                            "uptime_s":max(0,time.time()-self.worker_started[sid]),
                            "last_signal":self.last_signal[sid],"last_execution":self.last_execution[sid],
                            "open_positions":worker_positions[sid] if account is not None else None,
                            "unrealized_pnl":worker_unrealized[sid] if account is not None else None,
                            "risk_exposure":worker_risk[sid] if account is not None else None})
        current_risk=None
        if account is not None:
            try:
                exposure=self.portfolio_exposures(positions,orders)
                current_risk=sum(x.risk for group in exposure for x in group)
            except (RuntimeError,ValueError):
                pass
        base={"observed_utc":utc(),"campaign_id":self.config["campaign_id"],"config_sha256":self.hash,
              "broker_status":self.shared_status,"broker_issue":self.last_shared_error,
              "demo_verified":self.shared_status=="HEALTHY","account_login":self.config["account"]["login"],
              "broker_server":self.config["account"]["server"],"account_equity":None if account is None else float(account.equity),
              "account_balance":None if account is None else float(account.balance),
              "account_profit":None if account is None else float(account.profit),
              "total_strategies":len(workers),"active_strategies":sum(w["status"]=="ACTIVE" for w in workers),
              "blocked_strategies":sum(w["status"]=="BLOCKED" for w in workers),
              "target_per_strategy":self.config["risk"]["target_trades_per_strategy"],
              "overall_target":18*self.config["risk"]["target_trades_per_strategy"],
              "eligible_target":sum(w["status"]!="BLOCKED" for w in workers)*self.config["risk"]["target_trades_per_strategy"],
              "active_positions":len(positions),"pending_orders":len(orders),"completed_trades":len(realized),
              "occupied_position_slots":len(positions)+len(orders),
              "max_positions_portfolio":self.supervisor.max_positions,
              "max_open_risk_fraction":self.supervisor.max_risk_fraction,
              "daily_equity_halt_enabled":self.config["risk"].get("daily_equity_halt_enabled", True),
              "peak_equity_halt_enabled":self.config["risk"].get("peak_equity_halt_enabled", True),
              "risk_policy_sha256":self.config["_risk_policy_sha256"],
              "continuous_after_milestone":True,
              "realized_demo_pnl":sum(float(x["broker_net_profit"]) for x in realized),
              "open_planned_risk":current_risk,
              "risk_utilization_fraction":None if account is None or current_risk is None else current_risk/(float(account.equity)*self.supervisor.max_risk_fraction),
              "peak_equity":self.state.get("peak_equity"),
              "daily_equity_loss_fraction_observed":None if account is None or not self.state.get("day_start_equity") else max(0.0,1-float(account.equity)/float(self.state.get("day_start_equity"))),
              "peak_equity_drawdown_fraction":None if account is None or not self.state.get("peak_equity") else 1-float(account.equity)/float(self.state.get("peak_equity")),
              "workers":workers,"safety_events":self.state.db.execute("SELECT COUNT(*) FROM safety_events").fetchone()[0],
              "emergency_stop":STOP.exists() or self.controls.emergency(),
              "control_bridge_version":1,"service_pid":os.getpid(),
              "server_offset_s":self.broker.offset_s}
        save_json_atomic(DATA/"status.json",base)
        sync_path=HERE.parent.parent/"AA-AT"/"ops"/"github_sync_status.json"
        checkpoint_path=HERE.parent.parent/"AA-AT"/"CHECKPOINT.json"
        def read_optional(path):
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError,ValueError):
                return None
        sync=read_optional(sync_path)
        checkpoint=read_optional(checkpoint_path)
        cells=[]
        for w in workers:
            er="—" if w["expectancy_R"] is None else f"{w['expectancy_R']:.3f}"
            dd="—" if w["max_closed_drawdown_R"] is None else f"{w['max_closed_drawdown_R']:.2f}"
            cells.append(f"<tr><td>{w['id']}</td><td>{html.escape(w['name'])}</td><td>{w['status']}</td><td>{w['closed_trades']} (min {target})</td><td>{w['net_demo_pnl']:.2f}</td><td>{er}</td><td>{dd}</td><td>{html.escape(w['reason'] or '')}</td></tr>")
        risk_display="—" if base["risk_utilization_fraction"] is None else f"{100*base['risk_utilization_fraction']:.1f}%"
        sync_text="UNAVAILABLE" if sync is None else html.escape(str(sync.get("status","UNKNOWN")))
        checkpoint_text="UNAVAILABLE" if checkpoint is None else html.escape(str(checkpoint.get("updated_utc","UNKNOWN")))
        document=f"""<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='refresh' content='15'><title>AA AT DEMO forward campaign</title><style>body{{font:14px system-ui;background:#101820;color:#e6edf3;margin:2rem}}table{{border-collapse:collapse;width:100%}}td,th{{padding:.5rem;border-bottom:1px solid #30404b;text-align:left}}.cards{{display:flex;gap:1rem;flex-wrap:wrap}}.card{{background:#1b2b37;padding:1rem;border-radius:.4rem}}</style></head><body><h1>AA AT · broker-verified DEMO forward campaign</h1><p>Observed {html.escape(base['observed_utc'])}; DEMO account {base['account_login']} · {html.escape(base['broker_server'])} · status {base['broker_status']}</p><div class='cards'><div class='card'>Strategies<br><strong>{base['total_strategies']} total · {base['active_strategies']} active · {base['blocked_strategies']} blocked</strong></div><div class='card'>Completed trades<br><strong>{base['completed_trades']} · initial minimum {base['overall_target']} overall</strong></div><div class='card'>Realized DEMO PnL<br><strong>{base['realized_demo_pnl']:.2f} USD</strong></div><div class='card'>Portfolio slots<br><strong>{base['occupied_position_slots']}/{base['max_positions_portfolio']}</strong></div><div class='card'>Open and pending risk<br><strong>{risk_display} of {100*base['max_open_risk_fraction']:.1f}% cap</strong></div><div class='card'>Safety events<br><strong>{base['safety_events']}</strong></div><div class='card'>GitHub sync<br><strong>{sync_text}</strong></div><div class='card'>Last checkpoint<br><strong>{checkpoint_text}</strong></div><div class='card'>Codex development<br><strong>CHECKPOINTED; not required for execution</strong></div></div><p>{html.escape(base['broker_issue'] or '')}</p><table><thead><tr><th>ID</th><th>Strategy</th><th>Worker</th><th>Closed</th><th>Net USD</th><th>Expectancy R</th><th>Closed DD R</th><th>Blocker</th></tr></thead><tbody>{''.join(cells)}</tbody></table><p>One hundred closed trades is an evaluation milestone; eligible workers continue afterward. Source: immutable broker evidence and campaign SQLite index.</p></body></html>"""
        tmp=DATA/"dashboard.html.tmp"
        tmp.write_text(document,encoding="utf-8")
        os.replace(tmp,DATA/"dashboard.html")

    async def run(self):
        self.broker.attach()
        startup_verified=True
        try:
            a,t,p,o=self.snapshot()
            self.check_ownership(p,o)
            self.reconcile(p)
            self.equity_gate(a)
            live_exposure=self.portfolio_exposures(p,o)
            if len(p)+len(o)>self.supervisor.max_positions:
                raise RuntimeError("portfolio_slots_already_exceeded")
            if sum(x.risk for group in live_exposure for x in group)>float(a.equity)*self.supervisor.max_risk_fraction:
                raise RuntimeError("portfolio_risk_already_exceeded")
        except RuntimeError as exc:
            already_activated=self.state.get("activation_utc") is not None
            same_policy=self.state.get("risk_policy_sha256")==self.config["_risk_policy_sha256"]
            if not may_wait_for_startup_quotes(str(exc),already_activated,same_policy):
                raise
            # Keep the process alive and fail closed until the ordinary loop
            # verifies fresh quotes and all current broker exposure.
            startup_verified=False
            self.set_shared("SUSPENDED",f"{type(exc).__name__}:{exc}")
        if startup_verified:
            self.state.record_policy(self.config["_risk_policy_sha256"], self.config["risk"])
        refresh_report()
        if self.state.get("activation_utc") is None:
            self.state.put("initial_virtual_allocation",float(a.equity)/5)
            self.state.put("activation_utc",utc())
            self.state.evidence("SYSTEM","CAMPAIGN_ACTIVATED",{"account":plain(a),"terminal":plain(t),"positions":plain(p),"orders":plain(o)})
        for sid,w in self.workers.items():
            for symbol in w["symbols"]:
                if self.state.cursor(sid,symbol) is None:
                    self.state.advance(sid,symbol,int(time.time()//60)*60-60)
        self.worker_tasks={sid:asyncio.create_task(self.worker_loop(w),name=sid)
                           for sid,w in self.workers.items()}
        sent_minute_by_symbol={}
        try:
            while not STOP.exists():
                try:
                    await self.process_commands()
                    # The supervisor must not inspect a worker's transient
                    # broker order while that worker still owns the route lock.
                    async with self.router:
                        a,t,p,o=self.snapshot()
                        self.check_ownership(p,o)
                        self.reconcile(p)
                        self.equity_gate(a)
                        exposure=self.portfolio_exposures(p,o)
                        if len(p)+len(o)>self.supervisor.max_positions:
                            raise RuntimeError("portfolio_slots_already_exceeded")
                        if sum(x.risk for group in exposure for x in group)>float(a.equity)*self.supervisor.max_risk_fraction:
                            raise RuntimeError("portfolio_risk_already_exceeded")
                        self.set_shared("HEALTHY")
                        self.write_status(a,p,o)
                    now=time.time()
                    minute=int(now//60)
                    if now%60<=5.0:
                        for symbol in SYMBOLS:
                            if sent_minute_by_symbol.get(symbol)==minute:
                                continue
                            try:
                                spec,tick,age=self.broker.symbol_and_tick(symbol)
                                rates=self.broker.rates(symbol)
                                if len(rates)<260:
                                    continue
                                if int(rates["time"][-1])-self.broker.offset_s != minute*60:
                                    continue
                                event=(symbol,rates,spec,self.broker.offset_s,now)
                                for sid,w in self.workers.items():
                                    if symbol in w["symbols"] and sid not in self.breakers:
                                        self.queues[sid].put_nowait(event)
                                sent_minute_by_symbol[symbol]=minute
                            except (RuntimeError,ValueError,asyncio.QueueFull) as exc:
                                if now%60>4.0 and now-self.market_warn_last.get(symbol,0)>3600:
                                    self.state.event("MARKET_DATA",f"{symbol}:{type(exc).__name__}:{exc}")
                                    self.market_warn_last[symbol]=now
                except Exception as exc:
                    reason=f"{type(exc).__name__}:{exc}"
                    self.set_shared("SUSPENDED",reason)
                    self.write_status()
                    if "DEMO_ACCOUNT_GUARD_FAILED" in reason or "ambiguous_prepared_intent" in reason or "unowned_or_unreconciled_position" in reason or "protective_orders_changed" in reason:
                        self.permanent_halt(reason)
                        break
                await asyncio.sleep(1.0)
        finally:
            self.set_shared("STOPPED","service_stopped_or_safety_halt")
            self.write_status()
            for task in self.worker_tasks.values():
                task.cancel()
            await asyncio.gather(*self.worker_tasks.values(),return_exceptions=True)
            mt5.shutdown()


def preflight(config):
    broker=Broker(config)
    broker.attach()
    try:
        a,t=broker.guard()
        p,o=broker.exposure()
        offset=broker.clock_offset()
        symbols={}
        for symbol in SYMBOLS:
            try:
                spec,tick,age=broker.symbol_and_tick(symbol)
                rates=broker.rates(symbol)
                symbols[symbol]={"status":"FRESH","quote_age_s":age,"rates_count":len(rates),
                                 "forming_bar_utc_s":int(rates["time"][-1])-offset,
                                 "volume_min":spec.volume_min,"filling_mode":spec.filling_mode,
                                 "native_min_lot_margin_buy":broker.native_margin(1,symbol,float(spec.volume_min),float(tick.ask)),
                                 "native_min_lot_margin_sell":broker.native_margin(-1,symbol,float(spec.volume_min),float(tick.bid))}
            except RuntimeError as exc:
                symbols[symbol]={"status":"UNAVAILABLE","reason":str(exc)}
        return {"observed_utc":utc(),"account":"VERIFIED_DEMO","login":a.login,
                "server":a.server,"hedging":a.margin_mode==mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING,
                "trade_allowed":bool(a.trade_allowed and t.trade_allowed),"equity":a.equity,
                "positions":plain(p),"orders":plain(o),"offset_s":offset,"symbols":symbols,
                "max_positions_portfolio":config["risk"]["max_positions_account"],
                "max_open_risk_fraction":config["risk"]["max_open_fraction"],
                "orders_submitted":0}
    finally:
        mt5.shutdown()


def main():
    parser=argparse.ArgumentParser()
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight",action="store_true")
    mode.add_argument("--run",action="store_true")
    args=parser.parse_args()
    config,config_hash=load_config()
    original_signals(Path(config["strategy_source"]),config["strategy_source_sha256"])
    if args.preflight:
        print(json.dumps(preflight(config),indent=2,default=str))
        return
    if STOP.exists():
        raise RuntimeError("EMERGENCY_STOP_FILE_PRESENT")
    instance=SingleInstance(DATA/"service.lock")
    campaign=Campaign(config,config_hash)
    try:
        asyncio.run(campaign.run())
    except Exception as exc:
        reason=f"startup_or_supervisor_failure:{type(exc).__name__}:{exc}"
        campaign.set_shared("HALTED",reason)
        campaign.write_status()
        # A safety failure must not be restarted into order routing.
        if any(word in reason for word in ("DEMO_ACCOUNT_GUARD_FAILED","ambiguous_prepared_intent",
                                            "unowned_or_unreconciled_position","protective_orders_changed")):
            campaign.permanent_halt(reason)
            return
        raise


if __name__=="__main__":
    main()
