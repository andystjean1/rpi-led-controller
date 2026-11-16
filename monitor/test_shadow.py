"""Plain-assert checks for the shadow comparison's picks parity and schedule drift: python monitor/test_shadow.py"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))
import shadow  # noqa: E402

NOW = datetime(2026, 11, 15, 20, 0, tzinfo=timezone.utc).timestamp()


def iso(minutes_ago):
    return (datetime.fromtimestamp(NOW, timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()


def pick(key, ago=120, stake=3.0):
    return {"k": key, "t": iso(ago), "stake": stake, "book": "fanduel"}


# Sunday 2026-11-15: the PC placed 7 bets at 11:01, the HP's early 10:01 run placed none.
pc = [pick("picks|g1|%d" % i, ago=240) for i in range(7)]
r = shadow.picks_parity(pc, [], NOW)
assert r["level"] == "bad" and r["missing"] == 7 and r["extra"] == 0, r
assert len(r["missing_sample"]) == 6  # capped for the page

# identical ledgers
r = shadow.picks_parity(pc, [dict(p) for p in pc], NOW)
assert r["level"] == "ok" and r["same"] == 7 and r["missing"] == 0 and r["stake_diff"] == 0, r

# same bets, different stakes (bankroll drift): warn, not bad
hp = [dict(p, stake=3.5) for p in pc]
r = shadow.picks_parity(pc, hp, NOW)
assert r["level"] == "warn" and r["stake_diff"] == 7 and r["missing"] == 0, r

# HP placed one the PC did not: warn
r = shadow.picks_parity(pc, pc + [pick("picks|g9|x", ago=240)], NOW)
assert r["level"] == "warn" and r["extra"] == 1, r

# a pick placed 10 minutes ago is not judged yet (the other side's counts lag)
r = shadow.picks_parity([pick("picks|new", ago=10)], [], NOW)
assert r["level"] == "ok" and r["missing"] == 0, r

# PC stale: HP-only picks are not judged
r = shadow.picks_parity([], [pick("picks|only_hp", ago=240)], NOW, pc_stale=True)
assert r["extra"] == 0, r

# an older feed that sends no pick list
assert shadow.picks_parity(None, pc, NOW) is None and shadow.picks_parity(pc, None, NOW) is None


def utc(month, day, hh, mm):
    return datetime(2026, month, day, hh, mm, tzinfo=timezone.utc).isoformat()


def checks(tasks):
    return {x["task"]: x for x in shadow.schedule_check(tasks)}


# HP next fire vs the spec, in Eastern time. After 2026-11-01 Eastern is UTC-5: Sunday 11:00 = 16:00Z.
good = checks({"touchdown-scorers-sun": utc(11, 22, 16, 0), "touchdown-scorers-thu": utc(11, 19, 22, 0),
               "touchdown-scorers-wed": utc(11, 18, 15, 0), "projects-nightly-grade": utc(11, 17, 7, 30)})
assert all(x["ok"] for x in good.values()), good

# the 2026-11-15 case: the HP's Sunday task an hour early
bad = checks({"touchdown-scorers-sun": utc(11, 22, 15, 0)})
assert bad["touchdown-scorers-sun"]["ok"] is False and bad["touchdown-scorers-sun"]["dev_min"] == -60, bad

# right time, wrong weekday
assert checks({"touchdown-scorers-sun": utc(11, 23, 16, 0)})["touchdown-scorers-sun"]["ok"] is False

# a few seconds late (the HP's tasks start ~10 s after the minute) is fine; a task with no next run is "unknown"
assert checks({"touchdown-scorers-sun": utc(11, 22, 16, 0)})["touchdown-scorers-sun"]["ok"] is True
assert checks({})["projects-nightly-grade"]["ok"] is None

# daylight saving: before 2026-11-01 Eastern is UTC-4, so Sunday 11:00 is 15:00Z
assert checks({"touchdown-scorers-sun": utc(10, 25, 15, 0)})["touchdown-scorers-sun"]["ok"] is True


# actual weekly runs against their slots (Eastern wall clock, from the runs table)
def run(tag, month, day, hh, mm):
    return {"t": utc(month, day, hh, mm), "tag": tag, "n": {}}


slots = shadow.slot_check([
    run("sun", 11, 15, 15, 1),   # HP, 10:01 ET: an hour early, the 2026-11-15 miss
    run("sun", 11, 15, 16, 1),   # PC, 11:01 ET: on slot
    run("wed", 11, 11, 15, 48),  # 10:48 ET: the PC woke late, 48 min after its slot
    run("thu", 11, 12, 22, 1),   # 17:01 ET: on slot
    run("close", 11, 15, 17, 40),  # not a weekly tag: ignored
])
assert [(x["tag"], x["dev_min"]) for x in slots] == [("sun", -59), ("wed", 48)], slots


# compare() end to end: shifted runs report the signed offset
def runs(times):
    return [{"t": t, "tag": "sun", "n": {"line_rows": 10}} for t in times]


base = datetime(2026, 11, 15, 16, 0, tzinfo=timezone.utc)
pc_payload = {"received": NOW, "since": iso(60 * 48), "tasks": {},
              "projects": {"touchdown-scorers": {"runs": runs([base.isoformat()]), "picks": pc, "error": None}}}
hp_payload = {"projects": {"touchdown-scorers": {"runs": runs([(base - timedelta(hours=1)).isoformat()]), "picks": [], "error": None}}, "tasks": {}}
out = shadow.compare(pc_payload, hp_payload, now=NOW)
p = out["projects"][0]
assert p["shifted"] == 1 and p["shift_min"] == -60 and p["hp_missed"] == 1, p
assert p["picks"]["level"] == "bad" and p["picks"]["missing"] == 7
assert len(out["schedule"]["hp_next"]) == 4 and out["schedule"]["off_slot"]["pc"] == []
assert [x["dev_min"] for x in out["schedule"]["off_slot"]["hp"]] == [-60]  # base - 1h is 15:00Z = 10:00 ET

print("ok: shadow parity checks passed")
