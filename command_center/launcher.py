"""Quiet crash-recovering entry point for the local Windows scheduled task."""
from __future__ import annotations

import time
import traceback

from command_center.server import STATE, serve


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    delay = 2
    while True:
        try:
            serve()
        except KeyboardInterrupt:
            return
        except Exception:
            with (STATE / "server.log").open("a", encoding="utf-8") as log:
                log.write(traceback.format_exc() + "\n")
            time.sleep(delay)
            delay = min(delay * 2, 120)


if __name__ == "__main__":
    main()
