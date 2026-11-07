"""Where the status meets the LEDs.

`render(status, label)` is called after every poll of each laptop (label is its short name, e.g.
DESKTOP-06CD787). `status` is that laptop's feed plus:
  overall       "ok" | "warn" | "bad" | "down" (laptop unreachable)
  services      list of {name, level: ok|idle|warn|bad, reason, ...}
  host_vitals   {level, disk_free_pct, problems}
  clock_skew_s  laptop clock minus Pi clock, or None

Until the strip is wired up this only logs state changes. To drive the strip, replace the body
with calls into ledstrip.py / colors.py (a segment per laptop or service, a pulse for "down").
"""
import logging

log = logging.getLogger("display")
_last = {}  # label -> last state, so only changes are logged


def render(status, label):
    summary = {s["name"]: s["level"] for s in status.get("services", [])}
    state = (status["overall"], tuple(sorted(summary.items())))
    if state == _last.get(label):
        return  # log only changes
    _last[label] = state
    bad = [f'{s["name"]}: {s["reason"] or s["level"]}' for s in status.get("services", [])
           if s["level"] in ("warn", "bad")]
    log.info("%s overall=%s %s%s", label, status["overall"], status.get("reason", ""),
             (" | " + "; ".join(bad)) if bad else "")
    for name, level in summary.items():
        log.debug("  %-24s %s", name, level)
