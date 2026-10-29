"""Create an unroutable-until-verified local DEMO config from environment inputs.

Does not initialize MetaTrader, log in, or submit orders. Existing campaign
configurations are never overwritten; a new campaign needs separate review.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / "research/demo-live-20261021"


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing_environment_input:{name}")
    return value


def main():
    target = HERE / "campaign_config.json"
    if target.exists():
        raise RuntimeError("existing_frozen_campaign_config_will_not_be_overwritten")
    login = required("AAAT_DEMO_LOGIN")
    if not login.isdecimal() or not 6 <= len(login) <= 12:
        raise RuntimeError("invalid_demo_login_format")
    server = required("AAAT_DEMO_SERVER")
    terminal = Path(required("AAAT_MT5_TERMINAL_PATH"))
    if not terminal.is_file():
        raise RuntimeError("terminal_path_missing")
    config = json.loads((HERE / "campaign_config.example.json").read_text(encoding="utf-8"))
    source = ROOT / "research/overnight-20261010/engine.py"
    registration = ROOT / "research_outputs/registration_baseline.json"
    config["account"]["login"] = int(login)
    config["account"]["server"] = server
    config["terminal_path"] = str(terminal)
    config["strategy_source"] = str(source)
    config["strategy_source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    config["registration_source"] = str(registration)
    config["registration_sha256"] = hashlib.sha256(registration.read_bytes()).hexdigest()
    config["campaign_id"] = "DEMO_LOCAL_ACCOUNT_BOUND_REVIEW_REQUIRED"
    if config["account"]["trade_mode"] != "DEMO" or config["risk"]["target_trades_per_strategy"] != 100:
        raise RuntimeError("unsafe_example_config")
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
        json.dump(config, stream, indent=2)
        stream.write("\n")
    print("Local DEMO configuration created; broker identity, permissions, and risk gates still require live preflight.")


if __name__ == "__main__":
    main()
