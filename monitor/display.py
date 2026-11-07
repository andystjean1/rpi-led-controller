"""Where the status meets the LEDs.

`render(status)` is called after every poll. `status` is the HP feed plus:
  overall       "ok" | "warn" | "bad" | "down" (HP unreachable)
  services      list of {name, level: ok|idle|warn|bad, reason, ...}
  host_vitals   {level, disk_free_pct, problems}
  clock_skew_s  HP clock minus Pi clock, or None

Until the strip is wired up this only logs state changes. To drive the strip, replace the body
with calls into ledstrip.py / colors.py (a segment per service, a pulse for "down").
"""
import logging

log = logging.getLogger("display")
_last = None


def render(status):
    global _last
    summary = {s["name"]: s["level"] for s in status.get("services", [])}
    state = (status["overall"], tuple(sorted(summary.items())))
    if state == _last:
        return  # log only changes
    _last = state
    bad = [f'{s["name"]}: {s["reason"] or s["level"]}' for s in status.get("services", [])
           if s["level"] in ("warn", "bad")]
    log.info("HP overall=%s %s%s", status["overall"], status.get("reason", ""),
             (" | " + "; ".join(bad)) if bad else "")
    for name, level in summary.items():
        log.debug("  %-24s %s", name, level)
