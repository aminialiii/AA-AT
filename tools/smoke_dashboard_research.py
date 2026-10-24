"""Read-only dashboard release smoke test; never issues a control command."""
from __future__ import annotations

import argparse
import json
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener


def check(release: Path, workspace: Path) -> dict:
    sys.path.insert(0, str(release))
    from command_center.server import App, Handler

    auth = workspace / "AA-AT-command-center-state"
    token = next(line.split(": ", 1)[1].strip() for line in
                 (auth / "access_keys.txt").read_text().splitlines()
                 if line.startswith("viewer: "))
    runtime = workspace / "research" / "demo-live-20261021" / "runtime"
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    server.app = App(release, runtime, auth)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    opener = build_opener(ProxyHandler({}))
    codes = {}
    try:
        for path in ("/", "/assets/app.css", "/assets/app.js",
                     "/assets/research.js", "/api/status", "/api/research/status",
                     "/api/research/trades?limit=1", "/api/research/performance",
                     "/api/research/analysis",
                     "/api/research/quality", "/api/backups"):
            request = Request(base + path, headers={"Authorization": "Bearer " + token})
            with opener.open(request, timeout=5) as response:
                codes[path] = response.status
                content = response.read()
                if path == "/api/status":
                    observed = json.loads(content)
                    if observed.get("stale") and (
                            observed.get("broker_status") != "STALE" or
                            observed.get("demo_verified")):
                        raise RuntimeError("stale_broker_status_misrepresented")
                if path == "/api/research/trades?limit=1":
                    count = json.loads(content)["total"]
        try:
            opener.open(base + "/api/research/quality", timeout=5)
        except HTTPError as exc:
            codes["unauthorized"] = exc.code
        if any(code != 200 for path, code in codes.items() if path != "unauthorized"):
            raise RuntimeError("dashboard_endpoint_failed")
        if codes.get("unauthorized") != 401:
            raise RuntimeError("research_endpoint_is_public")
        return {"status": "PASS", "routes": len(codes), "research_trades": count,
                "unauthorized_rejected": True,
                "broker_stale": observed.get("stale"),
                "broker_status": observed.get("broker_status")}
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, default=Path(r"E:\GPT\Inves"))
    args = parser.parse_args()
    print(json.dumps(check(args.release, args.workspace)))
