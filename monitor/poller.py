"""Pi side of the laptop monitor: polls each laptop's status feed and hands the result to a display.

Standard library only. Today the display just logs; when the strip is wired up, replace
`display.render` in display.py (nothing else here needs to change).

    python poller.py [--url http://HOST:8740/status.json ...] [--interval 30] [--once]

Pass --url once per laptop; with none, it polls the HP and the Lenovo.
"""
import argparse
import json
import logging
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from urllib.parse import urlparse

import display
import store
import web

DEFAULT_URLS = [
    "http://DESKTOP-06CD787.local:8740/status.json",  # HP
    "http://DESKTOP-7MO22GL.local:8740/status.json",  # Lenovo
]
MAX_CLOCK_SKEW_S = 120      # laptop clock off by more than this vs the Pi -> warn
UNREACHABLE_AFTER = 2       # consecutive failed polls before a laptop counts as down

log = logging.getLogger("poller")


def fetch(url, timeout=8):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.load(resp)


def check_clock(status):
    """Return seconds the laptop clock is ahead of this machine, or None if unparsable."""
    try:
        remote = datetime.fromisoformat(status["time"])
    except (KeyError, ValueError):
        return None
    return (remote - datetime.now(timezone.utc)).total_seconds()


def unreachable(reason):
    return {"overall": "down", "reason": reason, "services": [], "host_vitals": {}}


def label_for(url):
    """Short name for logs and the page: the first part of the URL's hostname (DESKTOP-06CD787).

    urlparse lowercases hostnames; Windows computer names are uppercase, which store.NAMES uses.
    """
    return (urlparse(url).hostname or url).split(".")[0].upper()


def poll_one(url, failures):
    """Poll one laptop. Returns (status or None, failures).

    None means "hold the last displayed state": one blip (laptop busy, Wi-Fi hiccup) shouldn't
    flash red; it only counts as down once it repeats.
    """
    try:
        status = fetch(url)
    except Exception as exc:
        failures += 1
        log.warning("%s poll failed (%d): %s", label_for(url), failures, exc)
        if failures < UNREACHABLE_AFTER:
            return None, failures
        return unreachable(str(exc)), failures
    skew = check_clock(status)
    status["clock_skew_s"] = skew
    if skew is not None and abs(skew) > MAX_CLOCK_SKEW_S and status.get("overall") == "ok":
        status["overall"] = "warn"
        status["reason"] = "clock is off by %d s" % skew
    return status, 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", action="append", help="status feed URL; repeat for several laptops")
    ap.add_argument("--interval", type=int, default=30)
    ap.add_argument("--once", action="store_true", help="poll once, print the state, exit")
    ap.add_argument("--web-port", type=int, default=8750, help="port for the monitor page")
    ap.add_argument("--no-web", action="store_true", help="poll and log only, no page")
    args = ap.parse_args()
    urls = args.url or DEFAULT_URLS
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # --once keeps its events in memory so a test poll never touches the saved feed
    events = store.Store(path=None if args.once else store.EVENTS_FILE)
    if not args.once and not args.no_web:
        try:
            server = web.make_server(events, args.web_port)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            log.info("monitor page on port %d", args.web_port)
        except OSError as exc:  # keep polling even if the port is taken
            log.error("could not start the page on port %d: %s", args.web_port, exc)

    failures = {u: 0 for u in urls}
    while True:
        ok = True
        for url in urls:
            status, failures[url] = poll_one(url, failures[url])
            if status is None:
                ok = False  # a blip counts against --once, but is not displayed yet
                continue
            events.record(label_for(url), status)
            display.render(status, label_for(url))
            ok = ok and status["overall"] in ("ok", "idle")
        if args.once:
            return 0 if ok else 1
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
