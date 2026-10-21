"""Render a static, account-free operations view from verified snapshots."""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SYNC = ROOT.parent / "AA-AT-sync-state/status.json"


def h(value):
    return html.escape("—" if value is None else str(value))


def main():
    status = json.loads((DOCS / "operational_status.json").read_text(encoding="utf-8"))
    sync = json.loads(SYNC.read_text(encoding="utf-8")) if SYNC.exists() else {}
    checkpoint = json.loads((ROOT / "CHECKPOINT.json").read_text(encoding="utf-8"))
    rows = []
    for sid, worker in status["workers"].items():
        expectancy = worker["expectancy_R"]
        pf = worker.get("profit_factor")
        rows.append(f"<tr><td>{h(sid)}</td><td>{h(worker['status'])}</td><td>{worker['closed']} / {status['target_per_strategy']}</td>"
                    f"<td>{worker['net_demo_pnl']:.2f}</td><td>{'—' if expectancy is None else f'{expectancy:.3f}'}</td>"
                    f"<td>{'—' if pf is None else f'{pf:.2f}'}</td></tr>")
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>AA AT DEMO research dashboard</title><style>
body{{font:16px system-ui,sans-serif;color:#e5ebf5;background:#0c1525;margin:0;padding:2rem;max-width:1150px;margin-inline:auto}}
h1{{margin-bottom:.2rem}}p{{color:#aebed1}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:1rem;margin:1.5rem 0}}
.card{{background:#17243a;border:1px solid #324761;border-radius:12px;padding:1rem}}.number{{font-size:1.7rem;font-weight:700;color:#8bd0ff}}
table{{width:100%;border-collapse:collapse;background:#17243a}}th,td{{padding:.65rem;text-align:left;border-bottom:1px solid #324761}}
th{{color:#aebed1}}a{{color:#8bd0ff}}.warning{{background:#2c2230;border-left:4px solid #f1ad69;padding:1rem}}
</style></head><body><h1>AA AT · DEMO forward research</h1>
<p>Account-free snapshot observed {h(status['source_observed_utc'])}. Broker status: <strong>{h(status['broker_status'])}</strong>; DEMO verified at observation: <strong>{h(status['demo_verified_at_observation'])}</strong>.</p>
<div class="grid"><div class="card">Strategies<div class="number">{status['total_strategies']}</div>{status['active_strategies']} active · {status['blocked_strategies']} blocked</div>
<div class="card">Closed broker trades<div class="number">{status['completed_trades']}</div>{status['eligible_target']} currently eligible target · {status['overall_target']} nominal</div>
<div class="card">Realized DEMO PnL<div class="number">{status['realized_demo_pnl']:.2f}</div>USD; closed trades only</div>
<div class="card">Active positions<div class="number">{status['active_positions']}</div>Risk use {status['risk_utilization_fraction']:.3%}</div></div>
<p class="warning">This is a timestamped snapshot, not a live order console. Raw broker order/deal evidence and account identity remain in local storage. No strategy has reached the 100-trade screening target; observed PnL is not evidence of a durable edge.</p>
<h2>Strategies</h2><table><thead><tr><th>ID</th><th>Status</th><th>Closed trades</th><th>Net DEMO USD</th><th>Expectancy R</th><th>Profit factor</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Operations</h2><p>Peak equity drawdown: {status['peak_equity_drawdown_fraction']:.3%}. GitHub sync: {h(sync.get('state','UNVERIFIED'))}. Last checkpoint phase: {h(checkpoint['phase'])}. Development commit: {h(checkpoint.get('git_commit_sha'))}.</p>
<p><a href="../graphify-out/graph.html">Graphify visualization</a> · <a href="../graphify-out/GRAPH_REPORT.md">Graph scope and validation</a> · <a href="../NEXT_ACTIONS.md">Next actions</a></p></body></html>"""
    target = DOCS / "dashboard.html"
    target.write_text(page, encoding="utf-8")
    print(json.dumps({"dashboard": str(target), "workers": len(rows), "closed": status["completed_trades"]}))


if __name__ == "__main__":
    main()
