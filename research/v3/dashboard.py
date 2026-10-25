"""Loopback-only, authenticated staged research status; no worker controls."""
from __future__ import annotations

import argparse
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from .status import build_status

HTML = """<!doctype html><html lang='en'><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>AA-AT V3 Historical Research</title>
<style>
:root{color-scheme:dark;font:15px system-ui}body{margin:0;background:#0a101b;color:#e7edf7}
header{padding:24px 5vw;background:#111d30;border-bottom:1px solid #29405e}
h1{margin:0;font-size:26px}.sub{color:#9fb2cc;margin-top:8px}.wrap{padding:24px 5vw}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}
.card{background:#132238;border:1px solid #29405e;border-radius:12px;padding:16px}
.card strong{display:block;font-size:26px;color:#83d5d4;margin-top:6px}
.warning{margin:22px 0;padding:14px;background:#3a2d15;border:1px solid #a77a2d;border-radius:10px}
input,button{padding:10px;background:#1b2b43;color:#e7edf7;border:1px solid #446483;border-radius:7px}
button{cursor:pointer}table{border-collapse:collapse;width:100%;margin-top:15px}
td,th{text-align:left;border-bottom:1px solid #26394f;padding:10px}th{color:#a9bfd7}
.scroll{overflow:auto}.pill{padding:4px 8px;border-radius:6px;background:#334258;white-space:nowrap}
.status{margin:20px 0;color:#a9bfd7}@media(max-width:600px){header,.wrap{padding:16px}h1{font-size:21px}}
</style><header><h1>AA-AT · Three-Year Historical Research</h1>
<div class='sub'>Staged research service · simulated outcomes stay separate from broker-confirmed DEMO records</div></header>
<main class='wrap'><div class='warning'>No three-year baseline has completed. Saved broker M1 archives have partial coverage and an unverified UTC offset. Gold DEMO activation is not authorized.</div>
<label>Research access token <input id='token' type='password' autocomplete='off'></label>
<button id='load'>Load status</button><div id='status' class='status'>Enter the local research token to view the catalog.</div>
<section class='cards' id='cards'></section><h2>Strategies</h2><div class='scroll'><table><thead><tr><th>ID</th><th>Strategy</th><th>State</th><th>EA</th><th>Parity</th><th>Blocker</th></tr></thead><tbody id='strategies'></tbody></table></div>
<h2>Source coverage</h2><div class='scroll'><table><thead><tr><th>Symbol</th><th>Source</th><th>Rows</th><th>First</th><th>Last</th><th>UTC verified</th></tr></thead><tbody id='sources'></tbody></table></div>
<h2>Market status · research only</h2><p class='sub'>Broker schedules and fresh research quotes are not connected. UNKNOWN is not a trading signal.</p>
<div class='scroll'><table><thead><tr><th>Symbol</th><th>Status</th><th>Schedule source</th><th>Quote time</th></tr></thead><tbody id='markets'></tbody></table></div>
<h2>Economic calendar</h2><p id='calendar' class='sub'>No verified event source connected.</p></main>
<script>
const el=id=>document.getElementById(id);
function td(row,value){const cell=document.createElement('td');cell.textContent=value??'—';row.append(cell)}
el('load').onclick=async()=>{try{const response=await fetch('/api/status',{headers:{Authorization:'Bearer '+el('token').value},cache:'no-store'});if(!response.ok)throw Error('Access denied or research service unavailable');const data=await response.json();el('status').textContent='Observed '+data.observed_utc+' · Research only';el('cards').replaceChildren();for(const [name,value] of [['Strategies',data.strategies.length],['Historical sources',data.source_count],['Saved rows',data.source_rows.toLocaleString()],['3-year runs',data.historical_backtest_runs]]){const c=document.createElement('div');c.className='card';c.textContent=name;const n=document.createElement('strong');n.textContent=value;c.append(n);el('cards').append(c)}el('strategies').replaceChildren();for(const s of data.strategies){const tr=document.createElement('tr');for(const value of [s.id,s.name,s.status,s.ea_compiled?'Compiled':'—',s.python_rule_parity||'—',s.blocker])td(tr,value);el('strategies').append(tr)}el('sources').replaceChildren();for(const s of data.coverage){const tr=document.createElement('tr');for(const value of [s.symbol,s.source_type,s.rows,s.first_utc,s.last_utc,s.utc_verified?'Yes':'No'])td(tr,value);el('sources').append(tr)}el('markets').replaceChildren();for(const s of data.market_status){const tr=document.createElement('tr');for(const value of [s.symbol,s.status,s.schedule_source,s.last_quote_utc])td(tr,value);el('markets').append(tr)}el('calendar').textContent=data.economic_calendar.status+' · '+data.economic_calendar.verified_events+' verified events'}catch(error){el('status').textContent=error.message}};
</script></html>"""


def handler_factory(token: str):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/":
                body = HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif self.path == "/api/status":
                supplied = self.headers.get("Authorization", "")
                if not hmac.compare_digest(supplied, "Bearer " + token):
                    self.send_response(401)
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    return
                body = json.dumps(build_status()).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args):
            # No token, request path or account data in console output.
            return
    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8775)
    args = parser.parse_args()
    token = args.token_file.read_text(encoding="utf-8").strip()
    if len(token) < 32 or not 1024 <= args.port <= 65535:
        raise SystemExit("invalid_research_token_or_port")
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_factory(token))
    server.serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()
