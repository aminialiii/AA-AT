"""Read-only validation of current completed-candle adapter; no order API calls."""
import hashlib
import json
import sys
import time
from pathlib import Path

from broker import Broker, SYMBOLS, mt5
from live_signals import original_signals, next_signal
from service import Campaign

HERE=Path(__file__).resolve().parent
config=json.loads((HERE/"campaign_config.json").read_text())
broker=Broker(config)
broker.attach()
try:
    a,t=broker.guard()
    offset=broker.clock_offset()
    fn=original_signals(Path(config["strategy_source"]),config["strategy_source_sha256"])
    report={"account":"VERIFIED_DEMO","login":a.login,"source_sha256":config["strategy_source_sha256"],
            "registration_sha256":config["registration_sha256"],"server_offset_s":offset,
            "checks":[],"native_risk_checks":[],"orders_submitted":0}
    campaign=Campaign(config,hashlib.sha256((HERE/"campaign_config.json").read_bytes()).hexdigest())
    campaign.broker=broker
    for symbol in SYMBOLS:
        spec=mt5.symbol_info(symbol)
        rates=broker.rates(symbol)
        for w in config["workers"]:
            if symbol not in w["symbols"]:
                continue
            try:
                result=next_signal(fn,rates,spec,offset,time.time(),w["model"])
                report["checks"].append({"strategy":w["id"],"symbol":symbol,"status":"PASS",
                                         "latest_completed_bar_utc_s":result["bar_utc_s"],
                                         "valid":result["valid"],"signal_side":result["side"]})
                if result["side"]:
                    try:
                        current_spec,tick,age=broker.symbol_and_tick(symbol)
                        request,risk,parts=campaign.entry_request(w,symbol,result,current_spec,tick,a)
                        report["native_risk_checks"].append({"strategy":w["id"],"symbol":symbol,
                            "status":"ELIGIBLE_AT_OBSERVATION","planned_risk":risk,"parts":parts,
                            "sl":request["sl"],"tp":request["tp"],"orders_submitted":0})
                    except (RuntimeError,ValueError) as exc:
                        report["native_risk_checks"].append({"strategy":w["id"],"symbol":symbol,
                            "status":"SKIPPED","reason":str(exc),"orders_submitted":0})
            except Exception as exc:
                report["checks"].append({"strategy":w["id"],"symbol":symbol,"status":"FAIL",
                                         "reason":f"{type(exc).__name__}:{exc}"})
    report["passed"]=sum(x["status"]=="PASS" for x in report["checks"])
    report["failed"]=sum(x["status"]=="FAIL" for x in report["checks"])
    path=HERE/"live_adapter_validation.json"
    path.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"passed":report["passed"],"failed":report["failed"],"risk_cases":len(report["native_risk_checks"]),"orders_submitted":0,"artifact":str(path)}))
finally:
    mt5.shutdown()
