"""Read-only LSE client. API_KEY is read only from the process environment.

Base URL and x-api-key header are verified against the official API page and
official lse-data client archived in evidence/. No order endpoint exists here.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
BASE = "https://api.londonstrategicedge.com/vault"


def utcnow():
    return dt.datetime.now(dt.timezone.utc).isoformat()


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("Authenticated redirect refused")


class Client:
    def __init__(self):
        self.key = os.environ.get("API_KEY", "").strip()
        if not self.key:
            raise RuntimeError("API_KEY is not present in the process environment")
        if any(ch in self.key for ch in '\r\n"\\'):
            raise RuntimeError("Unexpected control characters in API_KEY")
        self.opener = urllib.request.build_opener(NoRedirect())
        self.last_query = 0.0
        self.calls_per_minute = 60

    def sanitize(self, value):
        s = json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value
        return re.sub(r"lse_live_[A-Za-z0-9_-]+", "[REDACTED]", s.replace(self.key, "[REDACTED]"))

    def get(self, path, params=None, artifact=None):
        if path not in ("/usage", "/meta", "/catalog", "/reference", "/candles") and not path.startswith("/ref/"):
            raise ValueError("Endpoint is not in this read-only research allowlist")
        params = params or {}
        if path in ("/candles",) or path.startswith("/ref/"):
            time.sleep(max(0, 60 / max(1, self.calls_per_minute) + .08 - (time.monotonic()-self.last_query)))
            self.last_query = time.monotonic()
        query = urllib.parse.urlencode(params)
        url = BASE + path + ("?"+query if query else "")
        req = urllib.request.Request(url, headers={"x-api-key": self.key,
            "User-Agent": "lse-data-sdk (+https://londonstrategicedge.com)", "Accept": "application/json"}, method="GET")
        record = {"requested_at_utc": utcnow(), "method": "GET", "path": path, "params": params}
        began = time.monotonic()
        raw = b""
        try:
            if shutil.which("curl.exe"):
                # Secret travels over stdin, never argv, URL, files, or logs.
                proc = subprocess.run(["curl.exe", "--silent", "--show-error", "--connect-timeout", "10",
                    "--max-time", "40", "--config", "-", "--write-out", "\n__LSE_STATUS__%{http_code}", url],
                    input=('header = "x-api-key: '+self.key+'"\nuser-agent = "lse-data-sdk (+https://londonstrategicedge.com)"\n').encode(),
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=45)
                raw, _, status = proc.stdout.rpartition(b"\n__LSE_STATUS__")
                record.update(status=int(status or 0), transport="curl", data_bytes=None)
                if proc.returncode:
                    raise RuntimeError("curl transport failure: "+self.sanitize(proc.stderr.decode("utf-8", "replace")))
                if record["status"] != 200:
                    raise RuntimeError("HTTP response: "+self.sanitize(raw.decode("utf-8", "replace"))[:300])
            else:
                with self.opener.open(req, timeout=35) as resp:
                    raw = resp.read()
                    record.update(status=resp.status, transport="urllib", data_bytes=resp.headers.get("X-Data-Bytes"),
                                  server_date=resp.headers.get("Date"))
            result = json.loads(raw)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            record.update(status=exc.code, error=self.sanitize(raw.decode("utf-8", "replace"))[:500])
            result = None
        except Exception as exc:
            record.setdefault("status", None)
            record.update(error=self.sanitize(str(exc))[:500])
            result = None
        record.update(elapsed_seconds=round(time.monotonic()-began, 4), response_bytes=len(raw),
                      response_sha256=hashlib.sha256(raw).hexdigest())
        (ROOT/"evidence").mkdir(exist_ok=True)
        with (ROOT/"evidence"/"requests.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False)+"\n")
        if artifact:
            (ROOT/"evidence"/artifact).write_text(self.sanitize(result if result is not None else record), encoding="utf-8")
        if result is None:
            raise RuntimeError(f"Read failed: {record.get('status')}; {record.get('error')}")
        return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["probe", "discover", "sample"])
    a = p.parse_args()
    c = Client()
    if a.action == "probe":
        usage = c.get("/usage", artifact="usage-initial.json")
        print(c.sanitize(usage))
    elif a.action == "discover":
        meta = c.get("/meta", artifact="meta.json")
        catalog = c.get("/catalog", artifact="catalog.json")
        print(c.sanitize(meta))
        targets = {"BTC/USD", "ETH/USD", "EUR/USD", "GBP/USD", "AAPL", "MSFT"}
        rows = [x for x in catalog if x.get("symbol") in targets and x.get("dataset") in {"crypto","fx","stocks"}]
        print(c.sanitize(rows))
    else:
        catalog = json.loads((ROOT/"evidence"/"catalog.json").read_text("utf-8"))
        for symbol in ["BTC/USD", "EUR/USD", "AAPL"]:
            candidates = [r for r in catalog if r["symbol"] == symbol and r["dataset"] in {"crypto","fx","stocks"}]
            if len(candidates) != 1:
                raise RuntimeError("Ambiguous or absent catalog symbol: "+symbol)
            dataset = candidates[0]["dataset"]
            rows = c.get("/candles", {"dataset":dataset,"symbol":symbol,"timeframe":"1m","order":"desc","limit":5,
                                      "end":"2026-10-10T00:00:00"}, artifact=f"sample-{dataset}.json")
            print(c.sanitize({"dataset":dataset,"symbol":symbol,"rows":rows}))


if __name__ == "__main__":
    main()
