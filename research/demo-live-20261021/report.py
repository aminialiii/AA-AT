"""Read-only, deterministic broker-ledger report. Historical research is excluded."""
from __future__ import annotations

import json
import math
import os
import random
import sqlite3
import statistics
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE=Path(__file__).resolve().parent
DATA=HERE/"runtime"
CONFIG_PATH=HERE/"campaign_config.json"
if not CONFIG_PATH.exists():
    CONFIG_PATH=HERE/"campaign_config.example.json"  # offline report tests only
config=json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def write_current(path, content):
    tmp=path.with_suffix(path.suffix+".tmp")
    with tmp.open("w",encoding="utf-8") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,path)


def milestones(n):
    fixed=(100,200,500,1000)
    return [x for x in fixed if x<=n]+list(range(1500,n+1,500))


def wilson(wins,n):
    if not n:
        return None
    z=1.959963984540054
    p=wins/n
    den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    rad=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,mid-rad),min(1,mid+rad)]


def day_block_interval(rows):
    groups=defaultdict(list)
    for row in rows:
        groups[row["entry_utc"][:10]].append(float(row["broker_net_profit"])/float(row["initial_risk_account_currency"]))
    if len(groups)<10:
        return None
    days=list(groups.values())
    rng=random.Random(261021)
    means=[]
    for _ in range(2000):
        picked=[days[rng.randrange(len(days))] for _ in days]
        vals=[x for group in picked for x in group]
        means.append(sum(vals)/len(vals))
    means.sort()
    return [means[49],means[1949]]


def metrics(rows):
    n=len(rows)
    if not n:
        return {"completed_trades":0,"net_usd":0.0,"classification":"INCONCLUSIVE",
                "reason":"No broker-reconciled closed trades"}
    net=[float(x["broker_net_profit"]) for x in rows]
    rval=[net[i]/float(rows[i]["initial_risk_account_currency"]) for i in range(n)]
    wins=sum(x>0 for x in net)
    positives=sum(x for x in net if x>0)
    negatives=-sum(x for x in net if x<0)
    curve=0.;peak=0.;drawdown=0.;streak=0.;max_streak=0
    for x in rval:
        curve+=x;peak=max(peak,curve);drawdown=max(drawdown,peak-curve)
        streak=streak+1 if x<0 else 0
        max_streak=max(max_streak,streak)
    durations=[(datetime.fromisoformat(x["exit_utc"])-datetime.fromisoformat(x["entry_utc"])).total_seconds()/60 for x in rows]
    costs=sum(float(x["broker_commission"])+float(x["broker_swap"])+float(x["broker_fees"]) for x in rows)
    variability=statistics.stdev(rval) if n>=2 else None
    slippage=[abs(float(x["entry_price"])-float(x["requested_entry_price"])) for x in rows]
    target=config["risk"]["target_trades_per_strategy"]
    complete=n>=target
    if not complete:
        classification="INCONCLUSIVE"
        reason=f"Below {target} genuine broker-reconciled closed trades"
    elif sum(rval)/n>0 and sum(net)>0:
        classification="INCONCLUSIVE"
        reason="Positive observed results; full cost, execution-quality, drawdown and regime review still required"
    elif sum(rval)/n<0:
        classification="UNDERPERFORMING"
        reason="Negative observed net expectancy after broker-recorded costs; not proof of a persistent negative edge"
    else:
        classification="INCONCLUSIVE"
        reason="Mixed or zero observed results"
    return {"completed_trades":n,"net_usd":sum(net),"gross_usd":sum(float(x["broker_gross_profit"]) for x in rows),
            "win_rate":wins/n,"win_rate_wilson95":wilson(wins,n),
            "average_win_usd":statistics.mean(x for x in net if x>0) if wins else None,
            "average_loss_usd":statistics.mean(x for x in net if x<0) if any(x<0 for x in net) else None,
            "expectancy_R":statistics.mean(rval),"expectancy_R_day_block95":day_block_interval(rows),
            "mean_over_std_R_per_trade":None if not variability else statistics.mean(rval)/variability,
            "profit_factor_usd":positives/negatives if negatives else None,
            "max_closed_trade_drawdown_R":drawdown,"max_consecutive_losses":max_streak,
            "average_duration_minutes":statistics.mean(durations),
            "commission_swap_fee_usd":costs,"average_abs_fill_deviation_price":statistics.mean(slippage),
            "classification":classification,"reason":reason,
            "limitations":["No marked-to-market historical equity curve in this report",
                           "Spread is embedded in broker fills but not separately valued in this ledger",
                           "Regime attribution requires entry-time broker observations",
                           "Per-trade mean/std is not an annualized Sharpe ratio",
                           "One hundred trades are a screening sample, not statistical proof"]}


def refresh():
    db=DATA/"campaign.sqlite3"
    rows=defaultdict(list)
    if db.exists():
        con=sqlite3.connect(f"file:{db.as_posix()}?mode=ro",uri=True)
        try:
            for sid,record in con.execute("SELECT strategy,record_json FROM closed ORDER BY closed_utc,position_id"):
                data=json.loads(record)
                if data.get("execution_kind")!="REAL_TIME_DEMO_BROKER" or data.get("account_trade_mode")!="DEMO" or not data.get("fully_closed"):
                    raise RuntimeError("closed ledger contains ineligible record")
                rows[sid].append(data)
        finally:
            con.close()
    result={"campaign_id":config["campaign_id"],"evidence_kind":"BROKER_RECONCILED_DEMO_ONLY",
            "strategies":{w["id"]:({"classification":"BLOCKED","reason":w["blocker"],"completed_trades":0}
                                   if w["status"]=="BLOCKED" else metrics(rows[w["id"]])) for w in config["workers"]},
            "total_completed_trades":sum(len(x) for x in rows.values()),
            "historical_research_included":False,"synthetic_trades_included":False}
    write_current(DATA/"performance_report.json",json.dumps(result,indent=2)+"\n")
    for worker in config["workers"]:
        sid=worker["id"]
        if worker["status"]=="BLOCKED":
            continue
        for milestone in milestones(len(rows[sid])):
            folder=DATA/"performance_snapshots"/sid
            folder.mkdir(parents=True,exist_ok=True)
            path=folder/f"{milestone}.json"
            if path.exists():
                prior=json.loads(path.read_text(encoding="utf-8"))
                if prior.get("milestone")!=milestone or prior.get("strategy_id")!=sid:
                    raise RuntimeError("historical_performance_snapshot_invalid")
                continue
            prefix=rows[sid][:milestone]
            snapshot={"strategy_id":sid,"milestone":milestone,
                      "evidence_kind":"BROKER_RECONCILED_DEMO_ONLY",
                      "latest_exit_utc":prefix[-1]["exit_utc"],
                      "frozen_config_versions":sorted({x["config_sha256"] for x in prefix}),
                      "risk_policy_versions":sorted({str(x.get("risk_policy_sha256")) for x in prefix}),
                      "metrics":metrics(prefix)}
            with path.open("x",encoding="utf-8") as f:
                f.write(json.dumps(snapshot,indent=2)+"\n")
                f.flush()
                os.fsync(f.fileno())
    lines=["# Broker-reconciled DEMO campaign performance","",
           f"Completed genuine closed trades: {result['total_completed_trades']}. Historical research and simulations are excluded.","",
           f"|ID|Status|Closed (initial minimum {config['risk']['target_trades_per_strategy']})|Net USD|Expectancy R|Main qualification|",
           "|---|---|---:|---:|---:|---|"]
    for w in config["workers"]:
        m=result["strategies"][w["id"]]
        net="—" if "net_usd" not in m else f"{m['net_usd']:.2f}"
        er="—" if m.get("expectancy_R") is None else f"{m['expectancy_R']:.3f}"
        lines.append(f"|{w['id']}|{m['classification']}|{m['completed_trades']}|{net}|{er}|{m['reason']}|")
    lines += ["","One hundred trades triggers an initial evaluation, not a trading stop or proof of an edge. Current metrics refresh after each reconciled close; immutable snapshots are saved at 100, 200, 500, 1000, and every subsequent 500 trades.",
              "Raw broker orders and deals are preserved under `runtime/evidence/`; `runtime/campaign.sqlite3` is the durable index."]
    write_current(DATA/"PERFORMANCE_REPORT.md","\n".join(lines)+"\n")
    return result


if __name__=="__main__":
    result=refresh()
    print(json.dumps({"status":"PASS","completed_trades":result["total_completed_trades"],
                      "artifact":str(DATA/"PERFORMANCE_REPORT.md")}))
