"""Read the isolated terminal's own tester log; never launch the terminal."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .market_import import DEFAULT_VAULT, atomic_json

STATE = Path(r"E:\GPT\Inves\AA-AT-research-state\v3")


def analyze(*, vault: Path = DEFAULT_VAULT, state: Path = STATE) -> dict:
    probe = json.loads((state / "tester-probe.json").read_text(encoding="utf-8"))
    log = vault / "mt5-portable" / "Tester" / "logs" / "20261025.log"
    if not log.resolve().is_relative_to(vault.resolve()):
        raise ValueError("tester_log_outside_research_vault")
    raw = log.read_bytes()
    encoding = "utf-16" if raw.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8"
    lines = raw.decode(encoding, errors="replace").splitlines()
    account_missing = any("tester not started because the account is not specified" in row for row in lines)
    result = {"schema_version": 1, "probe_observed_utc": probe["observed_utc"],
              "tester_outcome": "ACCOUNT_NOT_SPECIFIED" if account_missing else "UNRESOLVED",
              "tester_log_path": str(log),
              "tester_log_sha256": hashlib.sha256(raw).hexdigest(),
              "terminal_launched": bool(probe.get("launched_pid")),
              "terminal_exited": bool(probe.get("process_exited")),
              "account_file_present": bool(probe.get("account_file_present")),
              "historical_backtest_runs": 0, "simulated_trades": 0,
              "required_next_dependency": "independent_research_demo_account" if account_missing else None}
    atomic_json(state / "tester-probe-analysis.json", result, state)
    return result


if __name__ == "__main__":
    print(json.dumps(analyze()))
