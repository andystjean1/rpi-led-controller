"""Pi side of the HP monitor: polls the HP status feed and hands the result to a display.

Standard library only. Today the display just logs; when the strip is wired up, replace
`display.render` in display.py (nothing else here needs to change).

    python poller.py [--url http://DESKTOP-06CD787.local:8740/status.json] [--interval 30] [--once]
"""
import argparse
import json
import logging
import sys
import time
import urllib.request
from datetime import datetime, timezone

import display

DEFAULT_URL = "http://DESKTOP-06CD787.local:8740/status.json"
MAX_CLOCK_SKEW_S = 120      # HP clock off by more than this vs the Pi -> warn
UNREACHABLE_AFTER = 2       # consecutive failed polls before the HP counts as down

log = logging.getLogger("poller")


def fetch(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def check_clock(status):
    """Return seconds the HP clock is ahead of this machine, or None if unparsable."""
    try:
        hp = datetime.fromisoformat(status["time"])
    except (KeyError, ValueError):
        return None
    return (hp - datetime.now(timezone.utc)).total_seconds()


def unreachable(reason):
    return {"overall": "down", "reason": reason, "services": [], "host_vitals": {}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--once", action="store_true", help="poll once, print the state, exit")
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    failures = 0
    while True:
        try:
            status = fetch(args.url)
            failures = 0
            skew = check_clock(status)
            status["clock_skew_s"] = skew
            if skew is not None and abs(skew) > MAX_CLOCK_SKEW_S and status.get("overall") == "ok":
                status["overall"] = "warn"
                status["reason"] = "HP clock is off by %d s" % skew
        except Exception as exc:
            failures += 1
            log.warning("poll failed (%d): %s", failures, exc)
            # One blip (HP busy, Wi-Fi hiccup) shouldn't flash red; hold the last state until it repeats.
            if failures < UNREACHABLE_AFTER:
                if args.once:
                    return 1
                time.sleep(args.interval)
                continue
            status = unreachable(str(exc))

        display.render(status)
        if args.once:
            return 0 if status["overall"] in ("ok", "idle") else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
