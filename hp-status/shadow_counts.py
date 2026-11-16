"""Collector run counts for the shadow-run comparison (standard library only, read-only).

Each collector project keeps a `runs` table with one row per snapshot (time + row counts). This
reads those tables since the shadow run began, so the Pi can line up the PC's runs against the HP's.
It never writes to a database (opened with mode=ro) and never touches the live files.

    python shadow_counts.py                  print the counts as JSON
    python shadow_counts.py --push URL       POST them to the Pi (used on the PC)
    python shadow_counts.py --root C:\\Projects   where the projects live (default: the PC's folder)
"""
import argparse
import json
import os
import socket
import sqlite3
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone

PC_ROOT = r"C:\Users\Andy\Projects"
HP_ROOT = r"C:\Projects"
# The HP's data was copied from the PC on the evening of 2026-11-06 and its tasks started then, so
# anything earlier is shared history, not something the two machines collected separately.
# Moved from 2026-11-07 on 2026-11-13: the HP's data was re-baselined from the PC at 13:25 local (18:25 UTC),
# so it now holds the PC's earlier runs and only runs after this point say anything about HP coverage.
SHADOW_START = "2026-11-13T18:30:00+00:00"

# project folder -> (database file, runs table, time column, count columns worth comparing)
SOURCES = {
    "nba-edges": ("nba.db", "runs", "snapshot_at", ("game_rows", "line_rows", "injury_rows", "roster_rows")),
    "ncaab-edges": ("ncaab.db", "runs", "snapshot_at", ("game_rows", "line_rows", "rating_rows")),
    "nhl-edges": ("nhl.db", "runs", "snapshot_at", ("game_rows", "line_rows", "injury_rows", "roster_rows")),
    "cfb-edges": ("cfb.db", "runs", "snapshot_at", ("game_rows", "line_rows")),
    "touchdown-scorers": ("td.db", "runs", "snapshot_at", ("espn_rows", "sleeper_rows", "bovada_rows", "line_rows")),
    "parlay-edges": ("parlay.db", "parlay_runs", "placed_at", ("tickets",)),
}


def _runs(db_path, table, time_col, count_cols, since):
    con = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True, timeout=5)
    try:
        have = {r[1] for r in con.execute('pragma table_info("%s")' % table)}
        cols = [c for c in count_cols if c in have]
        has_tag = "tag" in have
        sql = 'select %s, %s%s from "%s" where %s >= ? order by %s' % (
            time_col, "tag, " if has_tag else "", ", ".join(cols) or "1", table, time_col, time_col)
        out = []
        for row in con.execute(sql, (since,)):
            t, rest = row[0], list(row[1:])
            tag = rest.pop(0) if has_tag else ""
            out.append({"t": t, "tag": tag or "", "n": {c: v for c, v in zip(cols, rest) if isinstance(v, int)}})
        return out
    finally:
        con.close()


# project folder -> [(picks table, key columns that identify one bet)]. Parlay tickets are left out: their
# price differs between machines by design, so they have no stable key.
PICK_SOURCES = {
    "nba-edges": [("picks", ("game_id", "market", "side", "line")),
                  ("prop_picks", ("game_id", "athlete_id", "stat", "side", "line"))],
    "ncaab-edges": [("picks", ("game_id", "market", "side", "line"))],
    "nhl-edges": [("picks", ("game_id", "market", "side", "line"))],
    "cfb-edges": [("picks", ("game_id", "market", "side", "line"))],
    "touchdown-scorers": [("picks", ("game_id", "gsis_id", "market", "side", "line"))],
}

# Scheduled tasks whose next fire time says whether the two machines run on the same clock times. Only
# non-repeating ones: a 30-minute collector's next run is always within 30 minutes of the other's.
# value = period in minutes the schedule repeats on (a weekly task fires once every 10080 minutes).
SCHEDULE_TASKS = {
    "touchdown-scorers-wed": 10080,
    "touchdown-scorers-thu": 10080,
    "touchdown-scorers-sun": 10080,
    "projects-nightly-grade": 1440,
}


def _picks(db_path, sources, since):
    """[{k, t, stake, book}] for every bet placed since `since`, one entry per (table, key)."""
    con = sqlite3.connect("file:%s?mode=ro" % db_path.replace("\\", "/"), uri=True, timeout=5)
    try:
        out = []
        for table, key_cols in sources:
            have = {r[1] for r in con.execute('pragma table_info("%s")' % table)}
            if not have:
                continue
            keys = [c for c in key_cols if c in have]
            sel = ", ".join(keys + [c for c in ("placed_at", "stake", "book") if c in have])
            for row in con.execute('select %s from "%s" where placed_at >= ? order by placed_at' % (sel, table), (since,)):
                kv = dict(zip(keys + [c for c in ("placed_at", "stake", "book") if c in have], row))
                key = table + "|" + "|".join("" if kv.get(c) is None else str(kv[c]) for c in keys)
                out.append({"k": key, "t": kv.get("placed_at"), "stake": kv.get("stake"), "book": kv.get("book")})
        return out
    finally:
        con.close()


def _task_times():
    """{task: next run in UTC (ISO) or None} for SCHEDULE_TASKS, via PowerShell. {} if that is unavailable."""
    names = ",".join("'%s'" % n for n in SCHEDULE_TASKS)
    script = (
        "$o=@{}; foreach($n in @(%s)){ $t=Get-ScheduledTask -TaskName $n -EA SilentlyContinue; "
        "if($t){ $i=$t|Get-ScheduledTaskInfo; $o[$n]=if($i.NextRunTime.Year -gt 2000){$i.NextRunTime.ToUniversalTime().ToString('o')}else{$null} } }; "
        "ConvertTo-Json -InputObject $o -Compress" % names
    )
    try:
        flags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW: the PC runs this from a hidden task
        res = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                             capture_output=True, text=True, timeout=30, creationflags=flags)
        return json.loads(res.stdout or "{}")
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def collect(root, since=SHADOW_START):
    """{project: {"runs": [...], "picks": [...], "error": str|None}, "tasks": {...}} for every project under root."""
    projects = {}
    for name, (db, table, time_col, cols) in SOURCES.items():
        path = os.path.join(root, name, "data", db)
        if not os.path.exists(path):
            continue
        try:
            projects[name] = {"runs": _runs(path, table, time_col, cols, since), "error": None}
        except sqlite3.Error as exc:
            projects[name] = {"runs": [], "error": str(exc)[:120]}
            continue
        if name in PICK_SOURCES:
            try:
                projects[name]["picks"] = _picks(path, PICK_SOURCES[name], since)
            except sqlite3.Error as exc:
                projects[name]["picks"] = None
                projects[name]["error"] = ("picks: " + str(exc))[:120]
    return {
        "host": os.environ.get("COMPUTERNAME") or socket.gethostname(),
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "since": since,
        "projects": projects,
        "tasks": _task_times(),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=PC_ROOT)
    ap.add_argument("--push", metavar="URL", help="POST the counts here instead of printing them")
    args = ap.parse_args()
    data = collect(args.root)
    if not args.push:
        print(json.dumps(data, indent=1))
        return 0
    req = urllib.request.Request(args.push, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return 0 if resp.status == 200 else 1
    except OSError as exc:  # the Pi is off or unreachable: try again at the next run
        print("push failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
