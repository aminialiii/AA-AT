"""Read-only, versioned descriptive research over broker-reconciled closes.

This module never imports the trading service or MetaTrader. Its input is a
transactionally consistent SQLite copy of the independent research warehouse.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import sqlite3
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from .analytics import session_labels, wilson

SCHEMA = 1
DEFAULT_STATE = Path(r"E:\GPT\Inves\AA-AT-research-state")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def consistent_snapshot(source: Path, destination: Path) -> str:
    """Use SQLite's online backup API; never copy a live WAL database as a file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name("." + destination.name + "." + uuid.uuid4().hex)
    reader = sqlite3.connect("file:" + source.as_posix() + "?mode=ro", uri=True,
                             timeout=5)
    writer = sqlite3.connect(temporary)
    try:
        reader.backup(writer, pages=256, sleep=0.01)
        if writer.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("snapshot_integrity_failed")
    finally:
        writer.close()
        reader.close()
    os.replace(temporary, destination)
    return sha256_file(destination)


def _block_interval(values: list[dict], seed: int) -> list[float] | None:
    """Resample trading days, not correlated trades, when enough days exist."""
    days = defaultdict(list)
    for row in values:
        if row["realized_r"] is not None:
            days[row["exit_utc"][:10]].append(float(row["realized_r"]))
    if len(days) < 5 or sum(map(len, days.values())) < 30:
        return None
    blocks = list(days.values())
    rng = random.Random(seed)
    samples = []
    for _ in range(2000):
        draw = [value for block in rng.choices(blocks, k=len(blocks)) for value in block]
        samples.append(mean(draw))
    samples.sort()
    return [samples[49], samples[1949]]


def summarize(rows: list[dict], seed: int = 0) -> dict:
    """All drawdown values here are closed-trade PnL proxies, never MTM equity."""
    ordered = sorted(rows, key=lambda row: (row["exit_utc"], row["trade_id"]))
    net = [float(row["net_pnl"]) for row in ordered]
    gross = [float(row["gross_pnl"]) for row in ordered]
    r_values = [float(row["realized_r"]) for row in ordered
                if row["realized_r"] is not None]
    positives = [value for value in net if value > 0]
    negatives = [value for value in net if value < 0]
    balance = peak = max_dd = 0.0
    underwater_start = None
    max_underwater_trades = 0
    win_streak = loss_streak = max_wins = max_losses = 0
    for index, value in enumerate(net):
        balance += value
        if balance >= peak:
            if underwater_start is not None:
                max_underwater_trades = max(max_underwater_trades,
                                            index - underwater_start)
                underwater_start = None
            peak = balance
        else:
            if underwater_start is None:
                underwater_start = index
            max_dd = max(max_dd, peak - balance)
        win_streak = win_streak + 1 if value > 0 else 0
        loss_streak = loss_streak + 1 if value < 0 else 0
        max_wins = max(max_wins, win_streak)
        max_losses = max(max_losses, loss_streak)
    if underwater_start is not None:
        max_underwater_trades = max(max_underwater_trades,
                                    len(ordered) - underwater_start)
    days = {row["exit_utc"][:10] for row in ordered}
    cost_effect = sum(float(row[field] or 0) for row in ordered
                      for field in ("commission", "swap", "fees"))
    return {
        "closed_trades": len(ordered), "distinct_exit_days": len(days),
        "first_exit_utc": ordered[0]["exit_utc"] if ordered else None,
        "last_exit_utc": ordered[-1]["exit_utc"] if ordered else None,
        "wins": len(positives), "losses": len(negatives),
        "win_rate": len(positives) / len(ordered) if ordered else None,
        "win_rate_wilson_95": wilson(len(positives), len(ordered)),
        "gross_profit_currency": sum(x for x in gross if x > 0),
        "gross_loss_currency": sum(x for x in gross if x < 0),
        "broker_cost_effect_currency": cost_effect,
        "net_pnl_currency": sum(net),
        "net_profit_factor": (sum(positives) / -sum(negatives)
                              if negatives else None),
        "average_win_currency": mean(positives) if positives else None,
        "average_loss_currency": mean(negatives) if negatives else None,
        "expectancy_r": mean(r_values) if r_values else None,
        "expectancy_r_day_block_95": _block_interval(ordered, seed),
        "realized_r_coverage": len(r_values) / len(ordered) if ordered else None,
        "max_closed_trade_drawdown_currency": max_dd,
        "max_closed_trade_underwater_trades": max_underwater_trades,
        "max_consecutive_wins": max_wins,
        "max_consecutive_losses": max_losses,
        "average_holding_seconds": mean(float(row["holding_seconds"])
                                        for row in ordered if row["holding_seconds"] is not None)
        if any(row["holding_seconds"] is not None for row in ordered) else None,
        "evidence_status": "DESCRIPTIVE_ONLY" if len(days) >= 5 else
                           "EXPLORATORY_TOO_FEW_DAYS",
        "drawdown_kind": "CLOSED_TRADE_PNL_PROXY_NOT_EQUITY",
    }


def analyze_snapshot(snapshot: Path, *, git_commit: str, backup_sha256: str) -> dict:
    connection = sqlite3.connect("file:" + snapshot.as_posix() + "?mode=ro",
                                 uri=True, timeout=5)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        rows = [dict(row) for row in connection.execute("""
            SELECT trade_id,strategy_id,config_sha256,symbol,direction,
                   entry_utc,exit_utc,gross_pnl,commission,swap,fees,net_pnl,
                   realized_r,holding_seconds,source_sha256
            FROM trades WHERE attribution_status='VERIFIED'
            ORDER BY exit_utc,trade_id""")]
        total = connection.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        market_bars = connection.execute("SELECT COUNT(*) FROM market_bars").fetchone()[0]
        market_ticks = connection.execute("SELECT COUNT(*) FROM market_ticks").fetchone()[0]
        market_sources = [dict(row) for row in connection.execute("""
            SELECT sha256,source_type,symbol,timeframe,row_count
            FROM market_sources ORDER BY sha256""")]
        issues = {row[0]: row[1] for row in connection.execute(
            "SELECT code,COUNT(*) FROM quality_issues GROUP BY code")}
        signal_counts = [dict(row) for row in connection.execute("""
            SELECT strategy_id,kind,COUNT(*) count FROM signals
            GROUP BY strategy_id,kind ORDER BY strategy_id,kind""")]
    finally:
        connection.close()
    source_hash = hashlib.sha256("\n".join(row["source_sha256"] for row in rows).encode()).hexdigest()
    snapshot_hash = sha256_file(snapshot)
    evidence_fingerprint = hashlib.sha256(json.dumps(
        {"trade_sources": source_hash, "market_sources": market_sources,
         "quality_issues": issues, "signal_counts": signal_counts},
        sort_keys=True).encode()).hexdigest()
    engine_hash = sha256_file(Path(__file__))
    run_id = hashlib.sha256(
        f"{SCHEMA}|{evidence_fingerprint}|{engine_hash}".encode()).hexdigest()[:20]
    groups = {name: defaultdict(list) for name in (
        "strategy", "strategy_version", "strategy_version_symbol",
        "strategy_version_direction", "strategy_version_session",
        "strategy_version_hour_utc", "strategy_version_weekday_utc",
        "strategy_version_month_utc", "symbol")}
    for row in rows:
        sid = row["strategy_id"]
        version = sid + "|" + (row["config_sha256"] or "UNVERSIONED")
        moment = datetime.fromisoformat(row["entry_utc"]).astimezone(timezone.utc)
        for group, key in (
            ("strategy", sid), ("strategy_version", version),
            ("strategy_version_symbol", version + "|" + row["symbol"]),
            ("strategy_version_direction", version + "|" + row["direction"]),
            ("strategy_version_hour_utc", version + "|" + f"{moment.hour:02d}"),
            ("strategy_version_weekday_utc", version + "|" + str(moment.weekday())),
            ("strategy_version_month_utc", version + "|" + moment.strftime("%Y-%m")),
            ("symbol", row["symbol"]),
        ):
            groups[group][key].append(row)
        for label in session_labels(row["entry_utc"]):
            groups["strategy_version_session"][version + "|" + label].append(row)
    partitions = {
        name: {key: summarize(value, int(hashlib.sha256(key.encode()).hexdigest()[:8], 16))
               for key, value in sorted(group.items())}
        for name, group in groups.items()}
    versions_per_strategy = defaultdict(set)
    for row in rows:
        versions_per_strategy[row["strategy_id"]].add(row["config_sha256"])
    for sid, item in partitions["strategy"].items():
        item["mixed_configuration_versions"] = len(versions_per_strategy[sid]) > 1
    no_quote_coverage = market_ticks == 0 and market_bars == 0
    return {
        "schema_version": SCHEMA, "analysis_run_id": run_id,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "evidence_class": "BROKER_ACTUAL", "git_commit": git_commit,
        "backup_sha256": backup_sha256, "warehouse_snapshot_sha256": snapshot_hash,
        "analysis_engine_sha256": engine_hash,
        "trade_source_digest": source_hash,
        "cutoff": {"last_closed_trade_utc": rows[-1]["exit_utc"] if rows else None,
                   "broker_reconciled_lifecycles": total,
                   "verified_attribution_lifecycles": len(rows)},
        "definitions": {
            "trade": "One fully closed broker-reconciled position lifecycle; deals and partial closes are not extra trades.",
            "profit_factor": "Sum of positive net trade PnL divided by absolute sum of negative net trade PnL.",
            "gross_pnl": "Broker gross PnL before commission, swap and fees.",
            "drawdown": "Cumulative closed-trade PnL drawdown from a zero starting point; no capital allocation or intratrade equity curve.",
            "sessions": "Entry time classified by IANA London, New York and Tokyo wall clocks; sessions can overlap.",
        },
        "portfolio_closed": summarize(rows, 1), "groups": partitions,
        "signal_counts": signal_counts,
        "data_quality": {"issues_by_code": issues,
                         "market_bars": market_bars,"market_ticks": market_ticks,
                         "market_sources": market_sources,
                         "true_equity_drawdown": None,
                         "market_context_available": not no_quote_coverage,
                         "tick_side_counterfactual_eligible": market_ticks > 0},
        "research_gates": {
            "trade_charts": "BLOCKED_NO_VERIFIED_MARKET_DATA" if no_quote_coverage else "ASSESS_PER_TRADE_COVERAGE",
            "mfe_mae": "BLOCKED_NO_VERIFIED_MARKET_DATA" if no_quote_coverage else "ASSESS_PER_TRADE_COVERAGE",
            "fill_sensitive_counterfactuals": "BLOCKED_NO_BROKER_BID_ASK" if market_ticks == 0 else "ASSESS_PER_TRADE_COVERAGE_AND_CONTRACT_SPECS",
            "one_year_backtest": "INSUFFICIENT_EVIDENCE_UNTIL_RULES_DATA_SPECS_COSTS_VERIFIED",
            "tp_equals_5": "EXCLUDED_UNIT_UNSPECIFIED",
        },
        "limitations": [
            "Closed trades span too few independent trading days for reliable day-block confidence intervals or time-window selection.",
            "No complete synchronized broker equity path is available; closed-trade drawdown is not true equity drawdown.",
            "Broker quote-side execution quality, MFE/MAE and price charts require genuine matched market history.",
            "No performance improvement is estimated without preregistered scenarios and eligible market data.",
        ],
    }


def run(state: Path = DEFAULT_STATE, *, git_commit: str = "UNKNOWN",
        backup_sha256: str = "UNKNOWN") -> dict:
    source = state / "research.sqlite3"
    if not source.is_file():
        raise FileNotFoundError("research_warehouse_unavailable")
    analytics = state / "analytics"
    analytics.mkdir(parents=True, exist_ok=True)
    snapshot = analytics / (".snapshot-" + uuid.uuid4().hex + ".sqlite3")
    try:
        consistent_snapshot(source, snapshot)
        result = analyze_snapshot(snapshot, git_commit=git_commit,
                                  backup_sha256=backup_sha256)
        run_dir = analytics / "runs" / result["analysis_run_id"]
        if not (run_dir / "priority3.json").is_file():
            run_dir.mkdir(parents=True, exist_ok=True)
            image_tmp = run_dir / (".warehouse." + uuid.uuid4().hex + ".tmp")
            shutil.copyfile(snapshot, image_tmp)
            os.replace(image_tmp, run_dir / "warehouse.sqlite3")
            csv_tmp = run_dir / (".strategy_versions." + uuid.uuid4().hex + ".tmp")
            with csv_tmp.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.writer(stream)
                writer.writerow(("strategy_version", "closed_trades", "distinct_exit_days",
                                 "win_rate", "net_pnl_currency", "expectancy_r",
                                 "net_profit_factor", "max_closed_trade_drawdown_currency",
                                 "evidence_status"))
                for key, value in result["groups"]["strategy_version"].items():
                    writer.writerow((key, *(value.get(field) for field in (
                        "closed_trades", "distinct_exit_days", "win_rate", "net_pnl_currency",
                        "expectancy_r", "net_profit_factor",
                        "max_closed_trade_drawdown_currency", "evidence_status"))))
            os.replace(csv_tmp, run_dir / "strategy_versions.csv")
            json_tmp = run_dir / (".priority3." + uuid.uuid4().hex + ".tmp")
            json_tmp.write_text(json.dumps(result, indent=2, sort_keys=True),
                                encoding="utf-8")
            os.replace(json_tmp, run_dir / "priority3.json")
        if (run_dir / "priority3.json").is_file():
            saved = json.loads((run_dir / "priority3.json").read_text(encoding="utf-8"))
            if saved.get("analysis_run_id") != result["analysis_run_id"]:
                raise RuntimeError("existing_analysis_run_mismatch")
            result = saved
        pointer = analytics / "latest.json"
        temporary = pointer.with_name(".latest." + uuid.uuid4().hex + ".json")
        temporary.write_text(json.dumps({"analysis_run_id": result["analysis_run_id"],
                                         "report": str(run_dir / "priority3.json")},
                                        sort_keys=True), encoding="utf-8")
        os.replace(temporary, pointer)
        return {"analysis_run_id": result["analysis_run_id"],
                "report": str(run_dir / "priority3.json"),
                "cutoff": result["cutoff"], "data_quality": result["data_quality"]}
    finally:
        snapshot.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--git-commit", default="UNKNOWN")
    parser.add_argument("--backup-sha256", default="UNKNOWN")
    args = parser.parse_args()
    print(json.dumps(run(args.state, git_commit=args.git_commit,
                         backup_sha256=args.backup_sha256)))


if __name__ == "__main__":
    main()
