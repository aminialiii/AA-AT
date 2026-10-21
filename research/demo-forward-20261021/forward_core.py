"""Fail-closed preparation primitives for a prospective DEMO forward campaign.

This module has no brokerage import, network access, or order-routing method.
It never generates signals or simulated trades. All results must be attached to
independent broker evidence after a separately approved execution integration.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent
EXPECTED_IDS = tuple(f"S{i:02d}" for i in range(1, 19))


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_inventory(path: Path = ROOT / "strategy_inventory.json") -> list[dict]:
    rows = json.loads(path.read_text(encoding="utf-8"))
    ids = tuple(row["id"] for row in rows)
    if ids != EXPECTED_IDS or len(set(row["magic_proposal"] for row in rows)) != 18:
        raise ValueError("inventory must contain exactly S01-S18 with distinct proposed magic IDs")
    for row in rows:
        if not (ROOT.parent.parent / row["source_file"]).is_file():
            raise ValueError(f"missing strategy source: {row['id']}")
        if sha256(ROOT.parent.parent / row["source_file"]) != row["source_sha256"]:
            raise ValueError(f"strategy source changed: {row['id']}")
    return rows


@dataclass(frozen=True)
class RiskLimits:
    per_strategy_fraction: Decimal
    portfolio_fraction: Decimal
    daily_loss_fraction: Decimal
    peak_drawdown_fraction: Decimal
    free_margin_fraction: Decimal
    max_positions_per_strategy: int
    max_positions_shared_account: int
    max_quote_age_seconds: int

    @classmethod
    def proposed(cls, path: Path = ROOT / "risk_proposal.json") -> "RiskLimits":
        p = json.loads(path.read_text(encoding="utf-8"))["limits"]
        return cls(*(Decimal(str(p[k])) for k in (
            "per_strategy_fraction", "portfolio_fraction", "daily_loss_fraction",
            "peak_drawdown_fraction", "free_margin_fraction"
        )), p["max_positions_per_strategy"], p["max_positions_shared_account"],
                   p["max_quote_age_seconds"])


def broker_gate(snapshot: dict, expected: dict, limits: RiskLimits) -> list[str]:
    """Validate independently obtained current broker facts; never query a broker."""
    reasons = []
    if snapshot.get("account_type") != "DEMO" or snapshot.get("trade_mode") != "DEMO":
        reasons.append("account_not_verified_demo")
    for key in ("login", "server", "currency"):
        if str(snapshot.get(key)) != str(expected.get(key)):
            reasons.append(f"{key}_mismatch")
    if not snapshot.get("connected") or not snapshot.get("trade_allowed") or not snapshot.get("terminal_trade_allowed"):
        reasons.append("broker_or_order_routing_unavailable")
    if snapshot.get("positions") is None or snapshot.get("orders") is None:
        reasons.append("exposure_unreconciled")
    if snapshot.get("margin_mode") not in ("HEDGING", "DEDICATED_ACCOUNT"):
        reasons.append("shared_account_isolation_unverified")
    observed = snapshot.get("observed_utc")
    try:
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(observed.replace("Z", "+00:00"))).total_seconds()
        if age < -2 or age > limits.max_quote_age_seconds:
            reasons.append("broker_snapshot_stale")
    except (AttributeError, ValueError):
        reasons.append("broker_snapshot_timestamp_invalid")
    return reasons


def proposal_gate(
    *, approved: bool, broker_reasons: list[str], signal_live: bool,
    signal_age_seconds: float | None, risk_amount: Decimal, strategy_equity: Decimal,
    portfolio_open_risk: Decimal, portfolio_equity: Decimal,
    daily_loss: Decimal, peak_drawdown: Decimal, margin_after: Decimal,
    free_margin: Decimal, strategy_positions: int, shared_positions: int,
    duplicate_intent: bool, conflicting_symbol: bool, limits: RiskLimits,
) -> list[str]:
    """A proposed policy gate. No order routing exists in this package."""
    reasons = list(broker_reasons)
    if not approved:
        reasons.append("explicit_first_order_approval_missing")
    if not signal_live or signal_age_seconds is None or signal_age_seconds < 0 or signal_age_seconds > limits.max_quote_age_seconds:
        reasons.append("fresh_real_time_signal_missing")
    if strategy_equity <= 0 or portfolio_equity <= 0 or risk_amount <= 0:
        reasons.append("risk_or_capital_unknown")
    elif risk_amount > limits.per_strategy_fraction * strategy_equity:
        reasons.append("per_strategy_risk_limit")
    if portfolio_equity <= 0 or portfolio_open_risk + risk_amount > limits.portfolio_fraction * portfolio_equity:
        reasons.append("portfolio_risk_limit")
    if portfolio_equity <= 0 or daily_loss >= limits.daily_loss_fraction * portfolio_equity:
        reasons.append("daily_loss_halt")
    if peak_drawdown >= limits.peak_drawdown_fraction:
        reasons.append("peak_drawdown_halt")
    if free_margin <= 0 or margin_after > limits.free_margin_fraction * free_margin:
        reasons.append("margin_limit_or_unknown")
    if strategy_positions >= limits.max_positions_per_strategy:
        reasons.append("strategy_position_limit")
    if shared_positions >= limits.max_positions_shared_account:
        reasons.append("shared_account_position_limit")
    if duplicate_intent or conflicting_symbol:
        reasons.append("duplicate_or_conflicting_exposure")
    return sorted(set(reasons))


class EvidenceStore:
    """Append-only broker-evidence files plus a rebuildable SQLite index."""

    def __init__(self, directory: Path):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.index_path = self.directory / "index.sqlite3"
        with sqlite3.connect(self.index_path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS evidence (id TEXT PRIMARY KEY, strategy_id TEXT NOT NULL, kind TEXT NOT NULL, utc TEXT NOT NULL, sha256 TEXT NOT NULL, path TEXT NOT NULL UNIQUE)")
            db.execute("CREATE INDEX IF NOT EXISTS evidence_strategy ON evidence(strategy_id,utc)")

    def append_broker_record(self, strategy_id: str, kind: str, record: dict) -> Path:
        if strategy_id not in EXPECTED_IDS:
            raise ValueError("unknown strategy")
        if kind not in {"account", "quote", "signal", "intent", "order", "deal", "position", "reconciliation", "risk_event"}:
            raise ValueError("unknown evidence kind")
        if not record.get("broker_record_id") or not record.get("observed_utc"):
            raise ValueError("broker ID and observation time required")
        identity = hashlib.sha256(canonical([strategy_id, kind, record["broker_record_id"]])).hexdigest()
        payload = canonical({"strategy_id": strategy_id, "kind": kind, "record": record})
        target = self.directory / f"{identity}.json"
        try:
            with target.open("xb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError:
            if target.read_bytes() != payload:
                raise ValueError("broker evidence ID collision with changed payload")
        with sqlite3.connect(self.index_path) as db:
            db.execute("INSERT OR IGNORE INTO evidence VALUES (?,?,?,?,?,?)", (
                identity, strategy_id, kind, record["observed_utc"], hashlib.sha256(payload).hexdigest(), str(target)
            ))
        return target


class StrategyWorker:
    """One independent asynchronous mailbox. A blocked strategy cannot route orders."""

    def __init__(self, definition: dict):
        self.definition = definition
        self.queue: asyncio.Queue = asyncio.Queue(maxsize=128)
        self.state = "BLOCKED"
        self.failure = definition["blocker"]

    async def run(self, stop: asyncio.Event) -> None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(self.queue.get(), timeout=1)
            except asyncio.TimeoutError:
                continue
            self.queue.task_done()
            # A signal adapter and verified broker transport are deliberately absent.
            self.state = "BLOCKED"


def create_workers(rows: list[dict]) -> dict[str, StrategyWorker]:
    return {row["id"]: StrategyWorker(row) for row in rows}


def require_execution_ready(preflight: dict, approval: dict | None) -> None:
    if approval is None or approval.get("first_order_approved") is not True:
        raise RuntimeError("FIRST_ORDER_APPROVAL_REQUIRED")
    if preflight.get("account_verification") != "VERIFIED_DEMO" or preflight.get("order_routing") != "VERIFIED":
        raise RuntimeError("BROKER_PREFLIGHT_INCOMPLETE")
    raise RuntimeError("BROKER_EXECUTION_ADAPTER_NOT_IMPLEMENTED")
