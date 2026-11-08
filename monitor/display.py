"""Where the status meets the LEDs.

`render(status, label)` is called after every poll of each laptop (label is its short name, e.g.
DESKTOP-06CD787). `status` is that laptop's feed plus:
  overall       "ok" | "warn" | "bad" | "down" (laptop unreachable)
  services      list of {name, level: ok|idle|warn|bad, reason, ...}
  host_vitals   {level, disk_free_pct, problems}
  clock_skew_s  laptop clock minus Pi clock, or None

The poller runs unprivileged, but the WS281x strip on a Pi 3 needs root. So this module only writes
each laptop's state to STATE_FILE (atomically); `strip_daemon.py`, a root systemd service, reads that
file and animates the strip. Every state change is also logged.
"""
import json
import logging
import os
import time

log = logging.getLogger("display")

STATE_FILE = os.environ.get("STRIP_STATE", os.path.expanduser("~/hp-monitor/strip_state.json"))
_last = {}      # label -> last state, so only changes are logged
_states = {}    # label -> {"overall": ..., "bad": [...], "at": epoch seconds}


def _write():
    tmp = STATE_FILE + ".tmp"
    try:
        with open(tmp, "w") as f:
            json.dump({"written": time.time(), "laptops": _states}, f)
        os.replace(tmp, STATE_FILE)
    except OSError as exc:
        log.warning("could not write %s: %s", STATE_FILE, exc)


def render(status, label):
    services = status.get("services", [])
    bad = [f'{s["name"]}: {s["reason"] or s["level"]}' for s in services
           if s["level"] in ("warn", "bad")]
    _states[label] = {"overall": status["overall"], "bad": [s["name"] for s in services
                                                            if s["level"] in ("warn", "bad")],
                      "services": [[s["name"], s["level"]] for s in services],
                      "disk_free_pct": (status.get("host_vitals") or {}).get("disk_free_pct"),
                      "at": time.time()}
    _write()  # every poll, so the daemon can tell the poller is alive

    summary = {s["name"]: s["level"] for s in services}
    state = (status["overall"], tuple(sorted(summary.items())))
    if state == _last.get(label):
        return  # log only changes
    _last[label] = state
    log.info("%s overall=%s %s%s", label, status["overall"], status.get("reason", ""),
             (" | " + "; ".join(bad)) if bad else "")
    for name, level in summary.items():
        log.debug("  %-24s %s", name, level)
