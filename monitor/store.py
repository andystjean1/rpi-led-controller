"""Shared state for the monitor page: the latest status of each laptop plus a running event feed.

The poller calls `record()` after every poll; the web server reads `snapshot()` and `events()`.
Events come from comparing each poll with the last good one (state changes, task runs, feed
restarts, outages) and are appended to a JSON-lines file so the feed survives a restart.
Standard library only.
"""
import json
import os
import threading
from collections import deque
from datetime import datetime, timezone

NAMES = {"DESKTOP-06CD787": "HP laptop", "DESKTOP-7MO22GL": "Lenovo laptop"}
EVENT_LIMIT = 1000
EVENTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "events.jsonl")
RESULT_RUNNING = 267009  # Task Scheduler: task is running now

# feed level -> event level shown on the page
_LEVEL = {"ok": "ok", "idle": "ok", "warn": "warn", "bad": "bad", "down": "bad"}


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Store:
    def __init__(self, path=EVENTS_FILE, limit=EVENT_LIMIT):
        """path=None keeps events in memory only (used by `poller.py --once`)."""
        self._lock = threading.Lock()
        self._path = path
        self._events = deque(maxlen=limit)
        self._next_id = 1
        self._hosts = {}  # label -> {"status", "good", "polled_at", "last_ok"}
        self._load()

    def _load(self):
        if not self._path or not os.path.exists(self._path):
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                lines = f.readlines()[-self._events.maxlen:]
        except OSError:
            return
        for line in lines:
            try:
                ev = json.loads(line)
                self._next_id = max(self._next_id, ev["id"] + 1)
            except (ValueError, KeyError, TypeError):
                continue
            self._events.append(ev)
        try:  # rewrite trimmed, so the file cannot grow without bound
            with open(self._path, "w", encoding="utf-8") as f:
                for ev in self._events:
                    f.write(json.dumps(ev) + "\n")
        except OSError:
            pass

    def _add(self, label, level, message, kind="state", service=None):
        ev = {
            "id": self._next_id, "time": _now(), "host": label,
            "name": NAMES.get(label, label), "kind": kind, "level": level,
            "service": service, "message": message,
        }
        self._next_id += 1
        self._events.append(ev)
        if self._path:
            try:
                with open(self._path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(ev) + "\n")
            except OSError:
                pass

    def record(self, label, status):
        """Store a poll result (a feed reply, or the poller's "down" placeholder) and log changes."""
        with self._lock:
            overall = status.get("overall", "bad")
            host = self._hosts.get(label)
            if host is None:
                host = self._hosts[label] = {"status": None, "good": None, "last_ok": None}
                n = len(status.get("services", []))
                if overall == "down":
                    msg = "monitor started; unreachable: " + status.get("reason", "")
                else:
                    msg = "monitor started; %s, %s" % (overall, "%d tasks" % n if n else "no tasks reported")
                self._add(label, _LEVEL.get(overall, "info"), msg)
            else:
                self._diff(label, host, status)
            host["status"] = status
            host["polled_at"] = _now()
            if overall != "down":
                host["good"] = status
                host["last_ok"] = host["polled_at"]

    def _diff(self, label, host, new):
        old = host["status"]
        o_old, o_new = old.get("overall"), new.get("overall")
        reason = new.get("reason", "")
        if o_old != o_new:
            if o_new == "down":
                msg = "unreachable: " + reason
            elif o_old == "down":
                msg = "back online (%s)" % o_new
            else:
                msg = "overall %s → %s" % (o_old, o_new) + (": " + reason if reason else "")
            self._add(label, _LEVEL.get(o_new, "info"), msg)
        good = host["good"]
        if o_new == "down" or not good:
            return

        if new.get("uptime_min", 0) + 0.5 < good.get("uptime_min", 0):
            self._add(label, "warn", "status feed restarted (the laptop rebooted, or the task was restarted)")

        hv_old, hv_new = good.get("host_vitals", {}), new.get("host_vitals", {})
        if hv_old.get("level") != hv_new.get("level") and hv_new.get("level"):
            self._add(label, _LEVEL.get(hv_new["level"], "info"),
                      "host vitals %s → %s (disk %s%% free)" % (
                          hv_old.get("level"), hv_new["level"], hv_new.get("disk_free_pct")))

        before = {s["name"]: s for s in good.get("services", [])}
        for s in new.get("services", []):
            prev = before.get(s["name"])
            if prev is None:
                continue
            name = s["name"]
            level_changed = prev["level"] != s["level"]
            if level_changed:
                msg = "%s: %s → %s" % (name, prev["level"], s["level"])
                if s.get("reason"):
                    msg += " (%s)" % s["reason"]
                self._add(label, _LEVEL.get(s["level"], "info"), msg, service=name)
            if s.get("last_run") and s["last_run"] != prev.get("last_run"):
                r = s.get("last_result")
                if r == RESULT_RUNNING:
                    self._add(label, "ok", "%s started" % name, kind="run", service=name)
                elif r in (0, None):
                    self._add(label, "ok", "%s ran ok" % name, kind="run", service=name)
                elif not level_changed:  # a failure that also changed the level is already logged above
                    self._add(label, "bad", "%s finished with result 0x%X" % (name, r & 0xFFFFFFFF),
                              kind="run", service=name)

    def snapshot(self):
        """Latest state per laptop. While a laptop is unreachable, details are the last good ones."""
        with self._lock:
            hosts = []
            for label, h in self._hosts.items():
                st, good = h["status"], h["good"] or {}
                hosts.append({
                    "label": label,
                    "name": NAMES.get(label, label),
                    "overall": st.get("overall"),
                    "reason": st.get("reason", ""),
                    "down": st.get("overall") == "down",
                    "polled_at": h["polled_at"],
                    "last_ok_at": h["last_ok"],
                    "host_vitals": good.get("host_vitals", {}),
                    "uptime_min": good.get("uptime_min"),
                    "clock_skew_s": good.get("clock_skew_s"),
                    "services": good.get("services", []),
                })
            return {"now": _now(), "hosts": hosts, "last_event_id": self._next_id - 1}

    def events(self, since=0):
        """Events with id > since, oldest first."""
        with self._lock:
            return [e for e in self._events if e["id"] > since]
