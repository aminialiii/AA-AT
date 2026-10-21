"""Read-only local MetaTrader MCP handshake diagnostic; never calls trade tools."""
from __future__ import annotations

import json
import urllib.error
import urllib.request

PAYLOAD = json.dumps({
    "jsonrpc": "2.0", "id": 1, "method": "initialize",
    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
               "clientInfo": {"name": "aa-at-readonly-probe", "version": "1"}}
}).encode("utf-8")


def probe(port):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/mcp", data=PAYLOAD,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"},
        method="POST")
    try:
        with opener.open(request, timeout=4) as response:
            text = response.read(2000).decode("utf-8", errors="replace")
            return {"port": port, "http_status": response.status,
                    "content_type": response.headers.get("Content-Type"),
                    "initialize_response": text[:500]}
    except urllib.error.HTTPError as error:
        return {"port": port, "http_status": error.code, "error": "HTTP_ERROR",
                "auth_scheme": (error.headers.get("WWW-Authenticate") or "").split(" ", 1)[0] or None}
    except urllib.error.URLError:
        return {"port": port, "http_status": None, "error": "UNREACHABLE"}


if __name__ == "__main__":
    print(json.dumps([probe(22345), probe(22346)]))
