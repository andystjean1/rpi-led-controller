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

MATCH_MINUTES = 20
SHIFT_MINUTES = 90  # an unmatched pair closer than this looks like one run on a shifted schedule
# Collector steps that only run on the PC by design (not registered on the HP), so they never pair.
PC_ONLY = {("touchdown-scorers", "close")}
PC_FILE = os.environ.get("SHADOW_PC", os.path.expanduser("~/hp-monitor/shadow_pc.json"))
PC_STALE_MIN = 45  # the PC pushes every 10 minutes; older than this means it is off or its task stopped
_lock = threading.Lock()


def _ts(s):
    try:
        d = datetime.fromisoformat(s)
    except (TypeError, ValueError):
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


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
        clean[str(name)[:40]] = {"runs": runs, "error": str(p.get("error") or "")[:120] or None}
    out = {"host": str(payload.get("host", ""))[:40], "since": str(payload.get("since", ""))[:40],
           "received": time.time(), "projects": clean}
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
        shifted = sum(1 for r in pc_only
                      if any(abs(_ts(r["t"]).timestamp() - ht) <= SHIFT_MINUTES * 60 for ht in hp_times))
        points = ([{"t": a["t"], "k": "both", "same": d["same"]} for (a, _b), d in zip(pairs, deltas)]
                  + [{"t": r["t"], "k": "pc"} for r in pc_only]
                  + [{"t": r["t"], "k": "hp"} for r in hp_only])
        points.sort(key=lambda x: x["t"])
        projects.append({
            "name": name, "pc_runs": len(pc_runs), "hp_runs": len(h["runs"]), "matched": len(pairs),
            "hp_missed": len(pc_only), "pc_missed": len(hp_only), "shifted": shifted, "agree": agree,
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
    }
