"""Shadow-run comparison: lines the PC's collector runs up against the HP's.

Inputs are two payloads from hp-status/shadow_counts.py (the PC pushes its own to /api/shadow, the
HP's rides along in its status feed). Standard library only.

For each project it pairs every PC run with the nearest unused HP run within MATCH_MINUTES, then
reports what is left over on each side and whether the row counts agree on the pairs. The two
machines fetch seconds-to-minutes apart, so a small difference in a count is normal (lines move);
the page shows agreement as a rate rather than calling any one difference a fault.
"""
import json
import os
import threading
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MATCH_MINUTES = 20
SHIFT_MINUTES = 90  # an unmatched pair closer than this looks like one run on a shifted schedule
# Collector steps that only run on the PC by design (none since the HP got touchdown-scorers-close on 2026-11-13).
PC_ONLY = set()
PICK_GRACE_MIN = 30  # a pick placed less than this long ago may not have reached the other machine's push yet
DRIFT_MINUTES = 5  # task fire times closer than this count as the same schedule (the HP's tasks start ~30 s late)
STAKE_EPS = 0.01
SLOT_TOLERANCE_MIN = 20
SLOT_RECENT_HOURS = 72
# Eastern wall-clock slots (weekday Mon=0, hour, minute). Mirrors touchdown-scorers td/config.py
# SNAPSHOT_SCHEDULE and register_nightly_grade.ps1; the Pi does not import them, so change both together.
TAG_SLOTS = {"wed": (2, 10, 0), "thu": (3, 17, 0), "sun": (6, 11, 0)}
SCHEDULE_SPEC = {"touchdown-scorers-wed": TAG_SLOTS["wed"], "touchdown-scorers-thu": TAG_SLOTS["thu"],
                 "touchdown-scorers-sun": TAG_SLOTS["sun"], "projects-nightly-grade": (None, 2, 30)}
ET = ZoneInfo("America/New_York")
PC_FILE = os.environ.get("SHADOW_PC", os.path.expanduser("~/hp-monitor/shadow_pc.json"))
PC_STALE_MIN = 45  # the PC pushes every 10 minutes; older than this means it is off or its task stopped
_lock = threading.Lock()


def _ts(s):
    try:
        d = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def _clean_picks(picks):
    out = []
    for r in picks[:5000]:
        if isinstance(r, dict) and isinstance(r.get("k"), str) and _ts(r.get("t")):
            stake = r.get("stake")
            out.append({"k": r["k"][:160], "t": r["t"], "stake": float(stake) if isinstance(stake, (int, float)) else None,
                        "book": str(r.get("book") or "")[:20]})
    return out


def _clean_tasks(tasks):
    if not isinstance(tasks, dict):
        return {}
    return {str(k)[:60]: (v if isinstance(v, str) and _ts(v) else None) for k, v in list(tasks.items())[:40]}


def save_pc(payload):
    """Validate a push from the PC and save it. Raises ValueError on a bad shape."""
    if not isinstance(payload, dict) or not isinstance(payload.get("projects"), dict):
        raise ValueError("expected {projects: {...}}")
    clean = {}
    for name, p in list(payload["projects"].items())[:12]:
        runs = []
        for r in (p.get("runs") or [])[:2000] if isinstance(p, dict) else []:
            if isinstance(r, dict) and _ts(r.get("t")):
                n = {str(k)[:24]: int(v) for k, v in (r.get("n") or {}).items() if isinstance(v, int)}
                runs.append({"t": r["t"], "tag": str(r.get("tag", ""))[:20], "n": n})
        entry = {"runs": runs, "error": str(p.get("error") or "")[:120] or None}
        if isinstance(p, dict) and isinstance(p.get("picks"), list):
            entry["picks"] = _clean_picks(p["picks"])
        clean[str(name)[:40]] = entry
    out = {"host": str(payload.get("host", ""))[:40], "since": str(payload.get("since", ""))[:40],
           "received": time.time(), "projects": clean, "tasks": _clean_tasks(payload.get("tasks"))}
    tmp = PC_FILE + ".tmp"
    with _lock:
        with open(tmp, "w") as f:
            json.dump(out, f)
        os.replace(tmp, PC_FILE)


def load_pc():
    try:
        with open(PC_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def _pair(pc_runs, hp_runs):
    """Greedy nearest-in-time pairing. Returns (pairs [(pc, hp)], pc_only, hp_only)."""
    limit = MATCH_MINUTES * 60
    hp = [(r, _ts(r["t"]).timestamp()) for r in hp_runs]
    used, pairs, pc_only = set(), [], []
    for r in pc_runs:
        t = _ts(r["t"]).timestamp()
        best = None
        for i, (h, ht) in enumerate(hp):
            if i not in used and abs(ht - t) <= limit and (best is None or abs(ht - t) < abs(hp[best][1] - t)):
                best = i
        if best is None:
            pc_only.append(r)
        else:
            used.add(best)
            pairs.append((r, hp[best][0]))
    return pairs, pc_only, [h for i, (h, _t) in enumerate(hp) if i not in used]


def picks_parity(pc_picks, hp_picks, now, pc_stale=False):
    """Did both machines place the same bets? Keys are table|game|market|side|line (see shadow_counts.PICK_SOURCES).

    missing = the PC placed it and the HP never did (a wrong HP schedule or a model difference: the case that
    matters). extra = only the HP placed it. stake_diff = both placed it at different sizes (bankroll drift).
    A pick younger than PICK_GRACE_MIN is not judged yet, because the other machine's counts lag a few minutes.
    Returns None when either side sent no pick list (older feed)."""
    if pc_picks is None or hp_picks is None:
        return None
    cutoff = now - PICK_GRACE_MIN * 60

    def old(p):
        return _ts(p["t"]).timestamp() <= cutoff

    pc_by = {}
    for p in pc_picks:
        pc_by.setdefault(p["k"], p)
    hp_by = {}
    for p in hp_picks:
        hp_by.setdefault(p["k"], p)
    missing = [p for k, p in pc_by.items() if k not in hp_by and old(p)]
    extra = [] if pc_stale else [p for k, p in hp_by.items() if k not in pc_by and old(p)]
    both = [(pc_by[k], hp_by[k]) for k in pc_by if k in hp_by]
    stake_diff = [(a, b) for a, b in both
                  if a.get("stake") is not None and b.get("stake") is not None and abs(a["stake"] - b["stake"]) > STAKE_EPS]
    level = "bad" if missing else ("warn" if extra or stake_diff else "ok")

    def sample(rows):
        return [{"k": p["k"], "t": p["t"]} for p in sorted(rows, key=lambda r: r["t"])[-6:]]

    return {"level": level, "pc": len(pc_by), "hp": len(hp_by), "same": len(both), "missing": len(missing),
            "extra": len(extra), "stake_diff": len(stake_diff), "missing_sample": sample(missing),
            "extra_sample": sample(extra)}


def schedule_check(hp_tasks):
    """The HP's next fire time of each weekly/daily task against the spec, in Eastern time.

    The spec is td/config.py SNAPSHOT_SCHEDULE (picks are decided at the last run before kickoff, so the
    clock time matters) and scripts/register_nightly_grade.ps1. Only the HP is checked this way: the PC's
    Task Scheduler predicts its weekly tasks an hour early (a time-zone quirk in how they were registered),
    although they have always run on the spec's wall-clock times, so the PC is checked from what it
    actually ran (slot_check) instead. Returns one row per task."""
    out = []
    for name, (weekday, hour, minute) in SCHEDULE_SPEC.items():
        nxt = (hp_tasks or {}).get(name)
        if not nxt:
            out.append({"task": name, "next": None, "ok": None, "why": "no next run reported"})
            continue
        local = _ts(nxt).astimezone(ET)
        want = f"{hour:02d}:{minute:02d}"
        dev = (local.hour * 60 + local.minute) - (hour * 60 + minute)
        ok = abs(dev) <= DRIFT_MINUTES and (weekday is None or local.weekday() == weekday)
        out.append({"task": name, "next": local.strftime("%a %H:%M"), "want": want, "dev_min": dev, "ok": ok})
    return out


def slot_check(runs, tag_slots=None):
    """Actual weekly runs that landed away from their scheduled slot: [{t, tag, dev_min}], newest last.

    A touchdown-scorers pick run more than SLOT_TOLERANCE_MIN from its slot (early, or late after the machine
    slept through it) decides the wrong games, so it is flagged even though the task itself reported success."""
    out = []
    for r in runs:
        slot = (tag_slots or TAG_SLOTS).get(r.get("tag"))
        if not slot:
            continue
        local = _ts(r["t"]).astimezone(ET)
        dev = (local.hour * 60 + local.minute) - (slot[1] * 60 + slot[2])
        if local.weekday() == slot[0] and abs(dev) > SLOT_TOLERANCE_MIN:
            out.append({"t": r["t"], "tag": r["tag"], "dev_min": dev})
    return out[-6:]


def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return None if not n else (xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2)


def compare(pc, hp, now=None):
    """The comparison the page draws, or {"ready": False, "why": ...} while an input is missing."""
    now = now or time.time()
    if not pc:
        return {"ready": False, "why": "The PC has not pushed its run counts yet."}
    if not hp or not hp.get("projects"):
        return {"ready": False, "why": "The HP's status feed has no shadow counts yet (feed not updated?)."}
    since = _ts(pc.get("since") or hp.get("since") or "")
    projects = []
    for name in pc["projects"]:
        if name not in hp["projects"]:
            continue
        p, h = pc["projects"][name], hp["projects"][name]
        pc_runs = [r for r in p["runs"] if (name, r["tag"]) not in PC_ONLY]
        pairs, pc_only, hp_only = _pair(pc_runs, h["runs"])
        agree, deltas = 0, []
        for a, b in pairs:
            keys = [k for k in a["n"] if k in b["n"]]
            same = all(a["n"][k] == b["n"][k] for k in keys)
            agree += same
            deltas.append({"t": a["t"], "tag": a["tag"], "same": same,
                           "diff": {k: b["n"][k] - a["n"][k] for k in keys if a["n"][k] != b["n"][k]}})
        # A PC-only run with an HP-only run an hour or so away is the same snapshot on a shifted
        # schedule (e.g. the task started an hour later), not a gap in collection.
        hp_times = [_ts(r["t"]).timestamp() for r in hp_only]
        offsets = []  # signed minutes, HP minus PC, for each PC-only run with an HP-only run nearby
        for r in pc_only:
            t = _ts(r["t"]).timestamp()
            near = [ht for ht in hp_times if abs(ht - t) <= SHIFT_MINUTES * 60]
            if near:
                offsets.append((min(near, key=lambda ht: abs(ht - t)) - t) / 60)
        shifted = len(offsets)
        shift_min = _median(offsets)
        points = ([{"t": a["t"], "k": "both", "same": d["same"]} for (a, _b), d in zip(pairs, deltas)]
                  + [{"t": r["t"], "k": "pc"} for r in pc_only]
                  + [{"t": r["t"], "k": "hp"} for r in hp_only])
        points.sort(key=lambda x: x["t"])
        projects.append({
            "name": name, "pc_runs": len(pc_runs), "hp_runs": len(h["runs"]), "matched": len(pairs),
            "hp_missed": len(pc_only), "pc_missed": len(hp_only), "shifted": shifted, "agree": agree,
            "shift_min": None if shift_min is None else round(shift_min),
            "picks": picks_parity(p.get("picks"), h.get("picks"), now, pc_stale=(now - pc.get("received", 0)) / 60 > PC_STALE_MIN),
            "coverage_pct": round(100 * len(pairs) / len(pc_runs), 1) if pc_runs else None,
            "agree_pct": round(100 * agree / len(pairs), 1) if pairs else None,
            "points": points, "deltas": deltas[-60:],
            "errors": [e for e in (p.get("error"), h.get("error")) if e],
        })
    age_min = (now - pc.get("received", 0)) / 60
    return {
        "ready": True, "since": since.isoformat() if since else None,
        "hours": round((now - since.timestamp()) / 3600, 1) if since else None,
        "pc_age_min": round(age_min, 1), "pc_stale": age_min > PC_STALE_MIN,
        "match_minutes": MATCH_MINUTES, "projects": projects,
        "schedule": {
            "hp_next": schedule_check(hp.get("tasks")),
            # off-slot weekly runs in the last 72 hours; older ones stay in the run timeline only
            "off_slot": {side: [x for x in slot_check(src["projects"].get("touchdown-scorers", {}).get("runs", []))
                                if now - _ts(x["t"]).timestamp() <= SLOT_RECENT_HOURS * 3600]
                         for side, src in (("pc", pc), ("hp", hp))},
        },
    }
