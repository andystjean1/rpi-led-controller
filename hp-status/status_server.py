"""Status feed: a tiny read-only HTTP server for the Raspberry Pi LED monitor.

Runs on each always-on laptop (Windows, Python 3.12, standard library only): the HP and the Lenovo.
GET /status.json returns task health, data freshness, host vitals and whether the apps on the
machine answer (the sports hub and its APIs on the HP).
Read-only: it never starts, stops or changes anything.

    python status_server.py [--port 8740]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PROJECTS = r"C:\Projects"
CACHE_SECONDS = 15

# Per machine (keyed by COMPUTERNAME): task name -> (project folder holding data/, max minutes
# between runs or None for weekly tasks). A machine with an empty or missing entry still reports
# host vitals, so a freshly built box shows up on the Pi before it runs anything. Add its tasks
# here when it takes on a workload.
SERVICES_BY_HOST = {
    "DESKTOP-06CD787": {  # HP
        "nba-edges-collect": ("nba-edges", 60),
        "ncaab-edges-collect": ("ncaab-edges", 60),
        "nhl-edges-collect": ("nhl-edges", 60),
        "cfb-edges-collect": ("cfb-edges", 60),
        "parlay-edges-build": ("parlay-edges", 60),
        "touchdown-scorers-wed": ("touchdown-scorers", None),
        "touchdown-scorers-thu": ("touchdown-scorers", None),
        "touchdown-scorers-sun": ("touchdown-scorers", None),
    },
    "DESKTOP-7MO22GL": {},  # Lenovo: no workload yet
}
SERVICES = SERVICES_BY_HOST.get(os.environ.get("COMPUTERNAME", ""), {})

# Apps that should answer an HTTP GET on this machine (checked from here, so loopback URLs):
# (name, url, port the page may link to or None). A non-2xx answer or no answer is "bad".
APPS_BY_HOST = {
    "DESKTOP-06CD787": [  # HP: the shadow-run sports hub and the six APIs behind it
        ("Sports hub", "http://127.0.0.1:8700/", 8700),
        ("touchdown-scorers API", "http://127.0.0.1:8702/api/td/health", None),
        ("nba-edges API", "http://127.0.0.1:8703/api/nba/health", None),
        ("ncaab-edges API", "http://127.0.0.1:8704/api/ncaab/health", None),
        ("nhl-edges API", "http://127.0.0.1:8705/api/nhl/health", None),
        ("parlay-edges API", "http://127.0.0.1:8706/api/parlay/health", None),
        ("cfb-edges API", "http://127.0.0.1:8707/api/cfb/health", None),
    ],
}
APPS = APPS_BY_HOST.get(os.environ.get("COMPUTERNAME", ""), [])
APP_TIMEOUT_S = 5  # the HP's disk is slow and a collector run can make an API take a few seconds

# Task Scheduler result codes that are not failures
RESULT_RUNNING = 267009
RESULT_NEVER_RAN = 267011

PS_TASKS = r"""
$names = @(%s)
Get-ScheduledTask | Where-Object { $names -contains $_.TaskName } | ForEach-Object {
  $i = $_ | Get-ScheduledTaskInfo
  [pscustomobject]@{
    name = $_.TaskName
    state = [string]$_.State
    result = [int64]$i.LastTaskResult
    last_run = $i.LastRunTime.ToUniversalTime().ToString('o')
    next_run = $i.NextRunTime.ToUniversalTime().ToString('o')
  }
} | ConvertTo-Json -Compress
"""

_lock = threading.Lock()
_cache = {"at": 0.0, "body": b"{}"}
_started = time.monotonic()  # not the wall clock: a laptop that boots with a wrong clock steps it later


def _parse(ts):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def read_tasks():
    names = ",".join("'%s'" % n for n in SERVICES)
    out = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_TASKS % names],
        capture_output=True, text=True, timeout=30,
    )
    if out.returncode != 0 or not out.stdout.strip():
        raise RuntimeError("task query failed: " + out.stderr.strip()[:200])
    data = json.loads(out.stdout)
    return data if isinstance(data, list) else [data]


def newest_data_mtime(project):
    """Newest modification time (epoch seconds) of any file under <project>\\data."""
    root = os.path.join(PROJECTS, project, "data")
    newest = 0.0
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            try:
                newest = max(newest, os.stat(os.path.join(dirpath, f)).st_mtime)
            except OSError:
                pass
    return newest or None


def classify(info, max_minutes, now):
    """Return (level, reason). Levels: ok, idle, warn, bad."""
    if info is None:
        return "bad", "task not registered"
    result = info["result"]
    if result == RESULT_NEVER_RAN:
        next_run = _parse(info["next_run"])
        if next_run and next_run < now:
            return "bad", "never ran and its next run time has passed"
        return "idle", "waiting for first scheduled run"
    if result not in (0, RESULT_RUNNING):
        return "bad", "last result 0x%X" % (result & 0xFFFFFFFF)
    if info["state"] == "Disabled":
        return "warn", "task disabled"
    if max_minutes is not None:
        last = _parse(info["last_run"])
        if last is None:
            return "warn", "no last run time"
        # The collectors run in a daily window (10:00 to about 23:00), so the gap overnight is
        # normal. If the scheduler has its next run queued in the future, it is on schedule; only
        # fall back to the age of the last run once that next run time has passed (machine was off).
        next_run = _parse(info["next_run"])
        if next_run and next_run > now:
            return "ok", ""
        age = (now - last).total_seconds() / 60
        if age > max_minutes * 3:
            return "bad", "last ran %d min ago" % age
        if age > max_minutes:
            return "warn", "last ran %d min ago" % age
    return "ok", ""


def check_app(app):
    """GET one app's URL. Returns {name, level ok|bad, reason, ms, link_port}."""
    name, url, link_port = app
    started = time.monotonic()
    reason = ""
    try:
        with urllib.request.urlopen(url, timeout=APP_TIMEOUT_S) as resp:
            if not 200 <= resp.status < 300:
                reason = "HTTP %d" % resp.status
    except urllib.error.HTTPError as exc:
        reason = "HTTP %d" % exc.code
    except Exception as exc:  # refused, timed out, reset: all just "not answering"
        reason = str(getattr(exc, "reason", exc))[:100] or "no answer"
    return {
        "name": name, "level": "bad" if reason else "ok", "reason": reason,
        "ms": round((time.monotonic() - started) * 1000), "link_port": link_port,
    }


def check_apps():
    if not APPS:
        return []
    with ThreadPoolExecutor(max_workers=len(APPS)) as pool:
        return list(pool.map(check_app, APPS))


def build_status():
    now = datetime.now(timezone.utc)
    problems = []
    try:
        by_name = {t["name"]: t for t in read_tasks()} if SERVICES else {}
    except Exception as exc:  # report, don't crash: the Pi should see a degraded HP
        by_name = {}
        problems.append(str(exc))

    services = []
    for name, (project, max_minutes) in SERVICES.items():
        info = by_name.get(name)
        level, reason = classify(info, max_minutes, now) if by_name else ("warn", "task query failed")
        mtime = newest_data_mtime(project)
        services.append({
            "name": name,
            "project": project,
            "level": level,
            "reason": reason,
            "last_run": info["last_run"] if info else None,
            "next_run": info["next_run"] if info else None,
            "last_result": info["result"] if info else None,
            "data_age_min": round((time.time() - mtime) / 60, 1) if mtime else None,
        })

    usage = shutil.disk_usage("C:\\")
    disk_free_pct = round(100 * usage.free / usage.total, 1)
    host_level = "ok"
    if disk_free_pct < 10:
        host_level = "bad"
    elif disk_free_pct < 20:
        host_level = "warn"
    if problems:
        host_level = "warn" if host_level == "ok" else host_level

    apps = check_apps()
    order = {"ok": 0, "idle": 0, "warn": 1, "bad": 2}
    worst = max([host_level] + [s["level"] for s in services] + [a["level"] for a in apps], key=lambda l: order[l])
    attention = [s["name"] for s in services if s["level"] in ("warn", "bad")]
    attention += [a["name"] for a in apps if a["level"] != "ok"]
    return {
        "host": os.environ.get("COMPUTERNAME", "unknown"),
        "time": now.isoformat(),  # the Pi compares this with its own clock
        "uptime_min": round((time.monotonic() - _started) / 60, 1),
        "overall": worst,
        "reason": ("Needs attention: " + ", ".join(attention)) if attention else "",
        "host_vitals": {"level": host_level, "disk_free_pct": disk_free_pct, "problems": problems},
        "services": services,
        "apps": apps,
    }


def current_body():
    with _lock:
        if time.time() - _cache["at"] > CACHE_SECONDS:
            _cache["body"] = json.dumps(build_status()).encode()
            _cache["at"] = time.time()
        return _cache["body"]


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.split("?")[0] not in ("/", "/status.json"):
            self.send_error(404)
            return
        try:
            body = current_body()
            self.send_response(200)
        except Exception as exc:
            body = json.dumps({"overall": "bad", "error": str(exc)}).encode()
            self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # polled every 30s; keep the log quiet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8740)
    ap.add_argument("--print", action="store_true", help="print the status once and exit")
    args = ap.parse_args()
    if args.print:
        print(json.dumps(build_status(), indent=2))
        return 0
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("status feed on port %d" % args.port, flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
