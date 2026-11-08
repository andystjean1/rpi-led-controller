"""Effects and monitor modes for the 5x60 LED grid.

Everything here is pure Python with no hardware imports, so it can be tried on any machine.
An effect is a function `fn(cv, ctx)` that draws into the canvas `cv` (a list of ROWS lists of COLS
(r, g, b) tuples; row 0 is the top, col 0 the left). `strip_daemon.py` maps the finished canvas onto
the real wiring with `grid_index`.

ctx keys:
  t        seconds (float, monotonic enough for animation)
  dt       seconds since the previous frame
  rgb      colour picked on the phone
  speed    1-10 from the phone
  laptops  {label: {"overall", "services": [[name, level]], "disk_free_pct", "bad": [names]}},
           or None when the poller's state file is stale or missing
  state    dict that persists between frames (fire heat, rain drops, stars)
"""
import math
import random

ROWS, COLS = 5, 60
BLACK = (0, 0, 0)
# Health colours, dim enough for a wall of 300 pixels
LEVEL = {"ok": (0, 90, 0), "idle": (15, 35, 90), "warn": (200, 110, 0), "bad": (220, 0, 0),
         "down": (220, 0, 0)}


def new():
    return [[BLACK] * COLS for _ in range(ROWS)]


def scale(rgb, k):
    return (int(rgb[0] * k), int(rgb[1] * k), int(rgb[2] * k))


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def wheel(pos):
    pos = int(pos) % 256
    if pos < 85:
        return (pos * 3, 255 - pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (255 - pos * 3, 0, pos * 3)
    pos -= 170
    return (0, pos * 3, 255 - pos * 3)


def fill(cv, rgb, rows=range(ROWS), cols=range(COLS)):
    for r in rows:
        for c in cols:
            cv[r][c] = rgb


def pulse(t, hz):
    """0..1 sine"""
    return 0.5 + 0.5 * math.sin(t * hz * math.tau)


# ---------------------------------------------------------------- show-off effects

def solid(cv, ctx):
    fill(cv, tuple(ctx["rgb"]))


def breathe(cv, ctx):
    fill(cv, scale(ctx["rgb"], 0.5 + 0.5 * math.sin(ctx["t"] * ctx["speed"] * 0.6)))


def rainbow(cv, ctx):
    shift = ctx["t"] * ctx["speed"] * 20
    for r in range(ROWS):
        for c in range(COLS):
            cv[r][c] = wheel(c * 256 / COLS + r * 10 + shift)


def chase(cv, ctx):
    head = int(ctx["t"] * ctx["speed"] * 8) % COLS
    for c in range(COLS):
        k = max(0.0, 1 - ((head - c) % COLS) / 15)
        fill(cv, scale(ctx["rgb"], k), cols=[c])


def plasma(cv, ctx):
    t = ctx["t"] * ctx["speed"] * 0.35
    for r in range(ROWS):
        for c in range(COLS):
            v = (math.sin(c * 0.21 + t) + math.sin(r * 0.9 - t * 1.3)
                 + math.sin((c * 0.13 + r * 0.6) + t * 0.7) + math.sin(math.hypot(c - 30, r * 3) * 0.25 - t))
            cv[r][c] = wheel((v + 4) / 8 * 255 + t * 8)


def aurora(cv, ctx):
    t = ctx["t"] * ctx["speed"] * 0.15
    for c in range(COLS):
        mid = 2 + 1.4 * math.sin(c * 0.11 + t * 2.1) + 0.6 * math.sin(c * 0.29 - t * 3.3)
        tint = 0.5 + 0.5 * math.sin(c * 0.05 + t)
        colour = mix((0, 220, 90), (150, 40, 220), tint)
        for r in range(ROWS):
            k = math.exp(-((r - mid) ** 2) / 0.9) * (0.45 + 0.55 * math.sin(c * 0.4 + t * 5) ** 2)
            cv[r][c] = scale(colour, k * 0.9)


def wave(cv, ctx):
    t = ctx["t"] * ctx["speed"] * 0.8
    for c in range(COLS):
        y = 2 + 1.9 * math.sin(c * 0.22 - t)
        for r in range(ROWS):
            cv[r][c] = scale(ctx["rgb"], max(0.0, 1 - abs(r - y) / 1.2))


def scanner(cv, ctx):
    span = COLS - 1
    ph = (ctx["t"] * ctx["speed"] * 10) % (2 * span)
    x = ph if ph < span else 2 * span - ph
    for c in range(COLS):
        fill(cv, scale(ctx["rgb"], max(0.0, 1 - abs(c - x) / 7) ** 2), cols=[c])


def twinkle(cv, ctx):
    stars = ctx["state"].setdefault("stars", {})
    for _ in range(int(ctx["speed"] * 0.4) + (random.random() < (ctx["speed"] * 0.4) % 1)):
        stars[(random.randrange(ROWS), random.randrange(COLS))] = 1.0
    for cell in list(stars):
        stars[cell] -= ctx["dt"] * 0.9
        if stars[cell] <= 0:
            del stars[cell]
        else:
            cv[cell[0]][cell[1]] = mix(scale(ctx["rgb"], stars[cell]), (255, 255, 255), stars[cell] ** 3 * 0.6)


def meteor(cv, ctx):
    t = ctx["t"] * ctx["speed"]
    for r in range(ROWS):
        head = (t * (5 + r * 2.5) + r * 23) % (COLS + 24)
        for c in range(COLS):
            d = head - c
            if 0 <= d < 14:
                cv[r][c] = scale(ctx["rgb"], (1 - d / 14) ** 2)


def fire(cv, ctx):
    heat = ctx["state"].get("heat")
    if heat is None:
        heat = ctx["state"]["heat"] = [[0.0] * COLS for _ in range(ROWS)]
    for c in range(COLS):  # ignite the bottom row
        heat[ROWS - 1][c] = max(heat[ROWS - 1][c], random.uniform(0.55, 1.0)) if random.random() < 0.7 else heat[ROWS - 1][c] * 0.7
    for r in range(ROWS - 1):  # rise and cool
        for c in range(COLS):
            below = (heat[r + 1][(c - 1) % COLS] + heat[r + 1][c] * 2 + heat[r + 1][(c + 1) % COLS]) / 4
            heat[r][c] = max(0.0, below - random.uniform(0.05, 0.28) * (1.2 - ctx["speed"] * 0.05))
    for r in range(ROWS):
        for c in range(COLS):
            h = heat[r][c]
            cv[r][c] = (int(min(255, h * 400)), int(max(0, min(200, (h - 0.35) * 300))), int(max(0, (h - 0.85) * 600)))


def matrix(cv, ctx):
    drops = ctx["state"].get("drops")
    if drops is None:
        drops = ctx["state"]["drops"] = [[-random.uniform(0, 12), random.uniform(3, 9)] for _ in range(COLS)]
    for c, drop in enumerate(drops):
        drop[0] += drop[1] * ctx["dt"] * ctx["speed"] * 0.35
        if drop[0] - 6 > ROWS:
            drop[0], drop[1] = -random.uniform(0, 18), random.uniform(3, 9)
        for r in range(ROWS):
            d = drop[0] - r
            if 0 <= d < 5:
                cv[r][c] = (200, 255, 200) if d < 1 else scale((0, 255, 70), (1 - d / 5) ** 1.5)


# ---------------------------------------------------------------- monitor modes

def bands(n):
    """Rows given to each laptop: (first row, one past the last row)."""
    if n <= 1:
        return [(0, ROWS)]
    if n == 2:
        return [(0, 2), (3, ROWS)]
    return [(i, i + 1) for i in range(min(n, ROWS))]


def _each(ctx):
    """(info, first row, end row) per laptop in name order; empty if there is no fresh data."""
    laptops = ctx["laptops"] or {}
    labels = sorted(laptops)
    return [(laptops[label], a, b) for label, (a, b) in zip(labels, bands(len(labels)))]


def no_data(cv, ctx):
    """The poller's state file is stale: pulse blue so it is obvious something upstream died."""
    fill(cv, scale((0, 40, 220), 0.15 + 0.85 * pulse(ctx["t"], 0.32)))


def monitor(cv, ctx):
    """Ambient health: each laptop owns a half of the wall and glows its colour."""
    laptops = ctx["laptops"]
    if laptops is None:
        return no_data(cv, ctx)
    labels = sorted(laptops)
    seg = COLS // max(len(labels), 1)
    blink = int(ctx["t"] * 2) % 2 == 0
    for idx, label in enumerate(labels):
        info = laptops[label]
        state = info.get("overall", "down")
        k = 0.2 + 0.8 * pulse(ctx["t"], 0.24) if state == "down" else 1.0
        start = idx * seg
        end = COLS if idx == len(labels) - 1 else start + seg
        fill(cv, scale(LEVEL.get(state, LEVEL["down"]), k), cols=range(start, end))
        if state in ("warn", "bad"):  # one white pip per failing service, blinking
            for j in range(min(len(info.get("bad", [])), 8)):
                cv[0][start + j] = (255, 255, 255) if blink else BLACK


def rack(cv, ctx):
    """One block per service, in name order. Green ok, blue idle, amber warn, red (blinking) bad."""
    if ctx["laptops"] is None:
        return no_data(cv, ctx)
    blink = int(ctx["t"] * 3) % 2 == 0
    for info, a, b in _each(ctx):
        state = info.get("overall", "down")
        if state == "down":
            fill(cv, scale(LEVEL["down"], 0.15 + 0.85 * pulse(ctx["t"], 0.5)), rows=range(a, b))
            continue
        fill(cv, scale(LEVEL.get(state, LEVEL["ok"]), 0.5), rows=range(a, b), cols=[0])
        services = sorted(info.get("services") or [])
        if not services:  # state file from before services were recorded
            fill(cv, LEVEL.get(state, LEVEL["ok"]), rows=range(a, b), cols=range(2, COLS))
            continue
        for k, (_name, level) in enumerate(services[:(COLS - 2) // 4]):
            rgb = LEVEL.get(level, LEVEL["warn"])
            if level == "bad" and not blink:
                rgb = scale(rgb, 0.25)
            fill(cv, rgb, rows=range(a, b), cols=range(2 + 4 * k, 5 + 4 * k))


def heartbeat(cv, ctx):
    """An ECG sweep per laptop: the trace spikes while healthy, beats faster when unwell, and goes
    flat and dim red when the laptop is unreachable."""
    if ctx["laptops"] is None:
        return no_data(cv, ctx)
    head = (ctx["t"] * (6 + ctx["speed"] * 3)) % COLS
    for info, a, b in _each(ctx):
        state = info.get("overall", "down")
        rgb = LEVEL.get(state, LEVEL["down"])
        base = (b - 1) - (b - 1 - a) // 2
        period = 20 if state in ("ok", "idle") else 12
        for c in range(COLS):
            k = max(0.0, 1 - ((head - c) % COLS) / (COLS * 0.9))
            if state == "down":
                cv[base][c] = scale(rgb, 0.15 + 0.15 * pulse(ctx["t"], 0.5))
                continue
            k = 0.12 + 0.88 * k
            if c % period == 0:
                rows = range(a, base + 1)
            elif c % period == 1:
                rows = range(base, b)
            else:
                rows = [base]
            for r in rows:
                cv[r][c] = scale(rgb, k)


def vitals(cv, ctx):
    """Two bars per laptop: top = share of services that are fine, bottom = free disk."""
    if ctx["laptops"] is None:
        return no_data(cv, ctx)
    for info, a, b in _each(ctx):
        state = info.get("overall", "down")
        rgb = LEVEL.get(state, LEVEL["down"])
        services = info.get("services") or []
        if state == "down":
            frac = 0.0
        elif services:
            frac = sum(1 for _n, lv in services if lv in ("ok", "idle")) / len(services)
        else:
            frac = 1.0 if state == "ok" else 0.5
        _bar(cv, a, frac, rgb)
        if b - a > 1:
            disk = info.get("disk_free_pct")
            if isinstance(disk, (int, float)):
                _bar(cv, a + 1, disk / 100, LEVEL["ok"] if disk >= 30 else LEVEL["warn"] if disk >= 15 else LEVEL["bad"])
            else:
                _bar(cv, a + 1, 0.0, LEVEL["ok"])


def _bar(cv, row, frac, rgb):
    full = int(max(0.0, min(1.0, frac)) * COLS + 0.5)
    for c in range(COLS):
        cv[row][c] = rgb if c < full else scale(rgb, 0.1)


def alert_overlay(cv, ctx):
    """Drawn over any other mode: red end-caps on the rows of a laptop that is bad or unreachable.
    Returns True when something is alerting."""
    alerting = False
    for info, a, b in _each(ctx):
        state = info.get("overall")
        if state not in ("bad", "down"):
            continue
        alerting = True
        k = 0.2 + 0.8 * pulse(ctx["t"], 1.4 if state == "bad" else 0.5)
        cap = scale((255, 0, 0), k)
        for r in range(a, b):
            for c in (0, 1, 2, COLS - 3, COLS - 2, COLS - 1):
                cv[r][c] = cap
    return alerting


EFFECTS = {
    "solid": solid, "breathe": breathe, "rainbow": rainbow, "chase": chase, "plasma": plasma,
    "aurora": aurora, "wave": wave, "scanner": scanner, "twinkle": twinkle, "meteor": meteor,
    "fire": fire, "matrix": matrix,
}
MONITORS = {"monitor": monitor, "rack": rack, "heartbeat": heartbeat, "vitals": vitals}
MODES = {**EFFECTS, **MONITORS}
