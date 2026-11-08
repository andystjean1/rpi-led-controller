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
  claude   {"sessions": [{"id", "name", "state", "subs"}]} from Agent Town, or None when it is quiet
  events   Claude tool calls since the previous frame: [{"s": session id, "k": kind}]
  text     the banner string for the text mode
  say      {"text", "rgb", "id"}: a one-shot message to scroll over any mode
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


# One heartbeat, as the row (0 = top, 4 = bottom) the trace sits on at each column: flat line, small
# P bump, Q dip, tall R spike, S dip, then the T bump.
BEAT_CALM = [2, 2, 2, 1, 1, 2, 3, 0, 4, 2, 2, 1, 1, 1, 2, 2]
BEAT_FAST = [2, 1, 2, 3, 0, 4, 2, 1, 1, 2]
TRACE = {"ok": (70, 255, 110), "idle": (70, 150, 255), "warn": (255, 170, 0), "bad": (255, 40, 40),
         "down": (255, 0, 0)}


def monitor(cv, ctx):
    """Health monitor: each laptop owns half the wall and an ECG trace sweeps across it, the way a
    bedside monitor draws one, in its health colour on a dark background. Calm beat = ok, fast beat =
    warn or bad, flat line = unreachable."""
    laptops = ctx["laptops"]
    if laptops is None:
        return no_data(cv, ctx)
    labels = sorted(laptops)
    seg = COLS // max(len(labels), 1)
    width = seg - 1  # the last column of each half stays dark as a divider
    head = (ctx["t"] * (8 + ctx["speed"] * 2)) % width
    for idx, label in enumerate(labels):
        state = laptops[label].get("overall", "down")
        start = idx * seg
        beat = [2] if state == "down" else BEAT_CALM if state in ("ok", "idle") else BEAT_FAST
        trace = TRACE.get(state, TRACE["down"])
        prev = beat[0]
        for c in range(width):
            row = beat[c % len(beat)]
            behind = (head - c) % width  # 0 at the sweep head, growing back along the trace
            if behind > width - 3:  # the gap just ahead of the head is erased
                prev = row
                continue
            k = 1 - 0.85 * behind / width
            rgb = scale(trace, k)  # pure health colour, fading along the tail
            for r in range(min(prev, row), max(prev, row) + 1):  # join the points into a line
                cv[r][start + c] = rgb
            prev = row


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


# ---------------------------------------------------------------- Claude Code activity
#
# ctx["claude"] is None when Agent Town has gone quiet (PC off or the town stopped), else
# {"sessions": [{"id", "name", "state": working|waiting|idle, "subs"}], ...}; ctx["events"] lists the
# tool calls since the last frame as {"s": session id, "k": kind}.

KIND_RGB = {"edit": (255, 140, 0), "read": (0, 200, 255), "shell": (60, 255, 90), "web": (170, 90, 255),
            "agent": (255, 60, 200), "mcp": (60, 110, 255), "other": (190, 190, 190), "fail": (255, 30, 30),
            "prompt": (255, 255, 255), "done": (120, 255, 200), "wait": (255, 150, 0)}
AMBER = (255, 150, 0)
SESSION_RGB = [(0, 200, 255), (255, 90, 160), (150, 255, 60), (255, 200, 0), (170, 110, 255)]


def plot(cv, x, y, rgb):
    """Add a light at (x, y), rounding to the nearest pixel."""
    r, c = int(round(y)), int(round(x))
    if 0 <= r < ROWS and 0 <= c < COLS:
        cv[r][c] = tuple(min(255, cv[r][c][i] + rgb[i]) for i in range(3))


def no_claude(cv, ctx):
    """Agent Town isn't reporting: one faint violet line breathing in the middle row."""
    fill(cv, scale((140, 70, 220), 0.05 + 0.25 * pulse(ctx["t"], 0.3)), rows=[2])


def lane_bands(n):
    """Split all five rows between n lanes with no spare rows: 3 lanes -> 2,2,1 rows tall."""
    if n == 2:
        return [(0, 2), (3, ROWS)]  # keep a dark row between two lanes
    base, extra = divmod(ROWS, n)
    out, row = [], 0
    for i in range(n):
        h = base + (1 if i < extra else 0)
        out.append((row, row + h))
        row += h
    return out


def _lane_of(sessions, sid):
    for i, s in enumerate(sessions):
        if s["id"] == sid:
            return i
    return hash(sid) % len(sessions)


def claude_lanes(cv, ctx):
    """One lane per live Claude session. Each tool call sends a pulse along it, coloured by what the
    tool does (orange edit, cyan read, green shell, purple web, magenta agent, blue MCP, red failure,
    white = you sent a prompt). A session waiting on you breathes amber; subagents are purple dots at
    the right-hand end."""
    claude = ctx["claude"]
    if claude is None:
        return no_claude(cv, ctx)
    sessions = claude["sessions"][:ROWS]
    if not sessions:
        return fill(cv, (14, 14, 26), rows=[2])
    spans = lane_bands(len(sessions)) if len(sessions) > 1 else [(0, ROWS)]
    pulses = ctx["state"].setdefault("lanes", [])
    for ev in ctx["events"]:
        pulses.append([_lane_of(sessions, ev["s"]), 0.0, ev["k"]])
    speed = 28 + ctx["speed"] * 5
    for i, s in enumerate(sessions):
        a, b = spans[i]
        if s["state"] == "waiting":
            base = scale(AMBER, 0.2 + 0.5 * pulse(ctx["t"], 0.9))
        else:
            base = (0, 22, 30) if s["state"] == "working" else (8, 8, 14)
        fill(cv, base, rows=range(a, b))
        for j in range(min(s["subs"], 6)):
            fill(cv, scale(KIND_RGB["agent"], 0.35 + 0.65 * pulse(ctx["t"] + j * 0.37, 1.6)),
                 rows=range(a, b), cols=[COLS - 1 - 2 * j])
    for p in pulses:
        a, b = spans[min(p[0], len(spans) - 1)]
        for tail in range(7):
            c = int(p[1]) - tail
            if 0 <= c < COLS:
                fill(cv, scale(KIND_RGB[p[2]], (1 - tail / 7) ** 1.5), rows=range(a, b), cols=[c])
        p[1] += ctx["dt"] * speed
    pulses[:] = [p for p in pulses if p[1] < COLS + 7][-150:]


def claude_drones(cv, ctx):
    """Each session is a glowing drone drifting over the whole grid with a trail. Working drones
    cruise; idle ones barely move. A tool call recolours the drone for a moment; a waiting drone
    stops and pulses amber."""
    claude = ctx["claude"]
    if claude is None:
        return no_claude(cv, ctx)
    sessions = claude["sessions"][:len(SESSION_RGB)]
    drones = ctx["state"].setdefault("drones", {})
    for gone in set(drones) - {s["id"] for s in sessions}:
        del drones[gone]
    t, dt = ctx["t"], ctx["dt"]
    for i, s in enumerate(sessions):
        d = drones.setdefault(s["id"], {"x": 8.0 + 11 * i, "dir": 1 if i % 2 == 0 else -1, "ph": i * 1.9,
                                        "y": 2.0, "trail": [], "kind": None, "kt": -99.0})
        for ev in ctx["events"]:
            if ev["s"] == s["id"]:
                d["kind"], d["kt"] = ev["k"], t
        waiting = s["state"] == "waiting"
        cruise = (10 + ctx["speed"] * 2) if s["state"] == "working" else 2.5
        if not waiting:
            d["x"] += d["dir"] * cruise * dt
            if d["x"] < 0 or d["x"] > COLS - 1:
                d["dir"] = -d["dir"]
                d["x"] = max(0.0, min(COLS - 1.0, d["x"]))
            d["ph"] += dt * (2.2 if s["state"] == "working" else 0.7)
            d["y"] = 2 + 1.9 * math.sin(d["ph"])
        d["trail"] = (d["trail"] + [(d["x"], d["y"])])[-10:]
        if waiting:
            rgb = scale(AMBER, 0.3 + 0.7 * pulse(t, 1.1))
        elif t - d["kt"] < 1.2:
            rgb = KIND_RGB[d["kind"]]
        else:
            rgb = SESSION_RGB[i % len(SESSION_RGB)]
        n = len(d["trail"])
        for k, (x, y) in enumerate(d["trail"]):
            plot(cv, x, y, scale(rgb, ((k + 1) / n) ** 2 * (1 if k == n - 1 else 0.6)))
        for j in range(min(s["subs"], 4)):  # subagents orbit their session
            ang = t * 4 + j * 1.6
            plot(cv, d["x"] + 2.2 * math.cos(ang), d["y"] + 1.2 * math.sin(ang), scale(KIND_RGB["agent"], 0.8))


def claude_meter(cv, ctx):
    """Activity meter: the last 15 seconds of tool calls as a scrolling bar chart, newest on the
    right. Bar height is calls in that quarter-second, colour is the kind of the latest call."""
    claude = ctx["claude"]
    if claude is None:
        return no_claude(cv, ctx)
    m = ctx["state"].setdefault("meter", {"bins": [(0, None)] * COLS, "acc": 0.0, "n": 0, "kind": None})
    for ev in ctx["events"]:
        m["n"] += 1
        m["kind"] = ev["k"]
    m["acc"] += ctx["dt"]
    while m["acc"] >= 0.25:
        m["acc"] -= 0.25
        m["bins"] = (m["bins"] + [(m["n"], m["kind"])])[-COLS:]
        m["n"], m["kind"] = 0, None
    for c, (n, kind) in enumerate(m["bins"]):
        if n == 0:
            cv[ROWS - 1][c] = (10, 10, 20)
            continue
        rgb = scale(KIND_RGB.get(kind, KIND_RGB["other"]), 0.3 + 0.7 * c / COLS)
        for r in range(ROWS - min(ROWS, n), ROWS):
            cv[r][c] = rgb


def waiting_overlay(cv, ctx):
    """Over any other mode: amber bars along the top and bottom edges while a Claude session is
    waiting on you (a permission prompt). Returns True when it is drawn."""
    claude = ctx.get("claude")
    if not claude or not any(s["state"] == "waiting" for s in claude["sessions"]):
        return False
    rgb = scale(AMBER, 0.15 + 0.85 * pulse(ctx["t"], 0.8))
    for c in range(12, COLS - 12):
        cv[0][c] = rgb
        cv[ROWS - 1][c] = rgb
    return True


# ---------------------------------------------------------------- text

# A 5-pixel-tall font. Each glyph is five rows of "#" and "."; most are 3 wide, a few are wider.
_FONT = {
    "A": (".#.", "#.#", "###", "#.#", "#.#"), "B": ("##.", "#.#", "##.", "#.#", "##."),
    "C": (".##", "#..", "#..", "#..", ".##"), "D": ("##.", "#.#", "#.#", "#.#", "##."),
    "E": ("###", "#..", "##.", "#..", "###"), "F": ("###", "#..", "##.", "#..", "#.."),
    "G": (".##", "#..", "#.#", "#.#", ".##"), "H": ("#.#", "#.#", "###", "#.#", "#.#"),
    "I": ("###", ".#.", ".#.", ".#.", "###"), "J": ("..#", "..#", "..#", "#.#", ".#."),
    "K": ("#.#", "#.#", "##.", "#.#", "#.#"), "L": ("#..", "#..", "#..", "#..", "###"),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#"), "N": ("#..#", "##.#", "#.##", "#..#", "#..#"),
    "O": (".#.", "#.#", "#.#", "#.#", ".#."), "P": ("##.", "#.#", "##.", "#..", "#.."),
    "Q": (".#.", "#.#", "#.#", "###", "..#"), "R": ("##.", "#.#", "##.", "#.#", "#.#"),
    "S": (".##", "#..", ".#.", "..#", "##."), "T": ("###", ".#.", ".#.", ".#.", ".#."),
    "U": ("#.#", "#.#", "#.#", "#.#", "###"), "V": ("#.#", "#.#", "#.#", "#.#", ".#."),
    "W": ("#...#", "#...#", "#.#.#", "##.##", "#...#"), "X": ("#.#", "#.#", ".#.", "#.#", "#.#"),
    "Y": ("#.#", "#.#", ".#.", ".#.", ".#."), "Z": ("###", "..#", ".#.", "#..", "###"),
    "0": ("###", "#.#", "#.#", "#.#", "###"), "1": (".#.", "##.", ".#.", ".#.", "###"),
    "2": ("##.", "..#", ".#.", "#..", "###"), "3": ("##.", "..#", ".#.", "..#", "##."),
    "4": ("#.#", "#.#", "###", "..#", "..#"), "5": ("###", "#..", "##.", "..#", "##."),
    "6": (".##", "#..", "###", "#.#", "###"), "7": ("###", "..#", ".#.", ".#.", ".#."),
    "8": ("###", "#.#", "###", "#.#", "###"), "9": ("###", "#.#", "###", "..#", "##."),
    " ": ("..", "..", "..", "..", ".."), ".": (".", ".", ".", ".", "#"), ",": (".", ".", ".", "#", "#"),
    ":": (".", "#", ".", "#", "."), "!": ("#", "#", "#", ".", "#"), "?": ("##.", "..#", ".#.", "...", ".#."),
    "-": ("...", "...", "###", "...", "..."), "+": ("...", ".#.", "###", ".#.", "..."),
    "=": ("...", "###", "...", "###", "..."), "/": ("..#", "..#", ".#.", "#..", "#.."),
    "%": ("#.#", "..#", ".#.", "#..", "#.#"), "'": ("#", "#", ".", ".", "."),
    "(": (".#", "#.", "#.", "#.", ".#"), ")": ("#.", ".#", ".#", ".#", "#."),
    "#": ("#.#", "###", "#.#", "###", "#.#"), "_": ("...", "...", "...", "...", "###"),
    "*": ("#.#", ".#.", "###", ".#.", "#.#"), ">": ("#..", ".#.", "..#", ".#.", "#.."),
    "<": ("..#", ".#.", "#..", ".#.", "..#"), "&": (".#.", "#.#", ".#.", "#.#", ".##"),
}
# Pixel icons, written into a message as :name: (e.g. "build done :rocket:").
SPRITES = {
    "heart": (".#.#.", "#####", "#####", ".###.", "..#.."), "smile": (".###.", "#.#.#", "#...#", "#.#.#", ".###."),
    "star": ("..#..", "#####", ".###.", ".#.#.", "#...#"), "skull": (".###.", "#.#.#", "#####", ".###.", ".#.#."),
    "ghost": (".###.", "#.#.#", "#####", "#####", "#.#.#"), "cat": ("#...#", "#####", "#.#.#", "#####", ".###."),
    "rocket": ("..#..", ".###.", ".###.", "#####", "#.#.#"), "bolt": ("..##", "..#.", ".##.", "..#.", ".#.."),
    "check": ("....#", "...#.", "#.#..", ".#...", "....."), "x": ("#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
}
SAY_STYLES = ("plain", "rainbow", "flash", "wave", "shake", "fire", "disco", "siren", "sparkle")
_text_cache = {}


def _glyph_columns(glyph):
    return [tuple(1 if glyph[r][j] == "#" else 0 for r in range(ROWS)) for j in range(len(glyph[0]))]


def text_columns(text):
    """The message as a list of columns, each a tuple of five 0/1 (top to bottom); one blank column
    between letters. Lower case is shown as capitals, unknown characters as '?', and :name: becomes
    an icon from SPRITES."""
    text = str(text)[:160]
    if text not in _text_cache:
        cols, i = [], 0
        while i < len(text):
            end = text.find(":", i + 1)
            name = text[i + 1:end].lower() if text[i] == ":" and end > 0 else None
            if name in SPRITES:
                cols += _glyph_columns(SPRITES[name]) + [(0,) * ROWS]
                i = end + 1
                continue
            cols += _glyph_columns(_FONT.get(text[i].upper(), _FONT["?"])) + [(0,) * ROWS]
            i += 1
        if len(_text_cache) > 50:
            _text_cache.clear()
        _text_cache[text] = cols
    return _text_cache[text]


def _draw_text(cv, cols, x0, rgb, style="plain", t=0.0):
    """Draw text columns at x0. The style changes how the lit pixels are coloured or moved."""
    dx, dy = (random.choice((-1, 0, 1)), random.choice((-1, 0, 1))) if style == "shake" else (0, 0)
    for j, col in enumerate(cols):
        c = x0 + j + dx
        shift = dy + (round(1.6 * math.sin(j * 0.55 + t * 7)) if style == "wave" else 0)
        for r in range(ROWS):
            if not col[r] or not 0 <= c < COLS or not 0 <= r + shift < ROWS:
                continue
            if style == "rainbow":
                px = wheel(j * 14 + t * 120)
            elif style == "flash":
                px = rgb if int(t * 5) % 2 == 0 else (255, 255, 255)
            elif style == "fire":
                px = mix((255, 30, 0), (255, 230, 60), (ROWS - 1 - r) / (ROWS - 1) * random.uniform(0.7, 1.0))
            elif style in ("disco", "siren"):
                px = (255, 255, 255)
            else:
                px = rgb
            cv[r + shift][c] = px


def _say_background(cv, style, t):
    """Backdrop behind a styled message (most styles have none: the wall just goes black)."""
    if style == "disco":
        for c in range(COLS):
            fill(cv, scale(wheel(c * 13 + int(t * 6) * 40), 0.3), cols=[c])
    elif style == "siren":
        left = int(t * 4) % 2 == 0
        fill(cv, scale((255, 0, 0) if left else (0, 0, 255), 0.45), cols=range(0, COLS // 2))
        fill(cv, scale((0, 0, 255) if left else (255, 0, 0), 0.45), cols=range(COLS // 2, COLS))
    elif style == "sparkle":
        for _ in range(14):
            cv[random.randrange(ROWS)][random.randrange(COLS)] = scale(wheel(random.randrange(256)), 0.35)


def banner(cv, ctx):
    """The banner text from the phone, scrolling round and round."""
    cols = text_columns(ctx.get("text") or "HELLO")
    offset = int(ctx["t"] * (8 + ctx["speed"] * 3)) % (len(cols) + COLS)
    _draw_text(cv, cols, COLS - offset, tuple(ctx["rgb"]), "plain", ctx["t"])


def say_overlay(cv, ctx):
    """A message sent with {"say": {...}} scrolls across once over whatever mode is running, then
    the mode comes back. A message already stored when the daemon starts is not replayed."""
    st, say = ctx["state"], ctx.get("say")
    sid = say.get("id") if isinstance(say, dict) else None
    if "say_init" not in st:
        st.update(say_init=True, say_id=sid, say_t0=None)
    elif sid is not None and sid != st["say_id"]:
        st.update(say_id=sid, say_t0=ctx["t"])
    t0 = st.get("say_t0")
    if t0 is None or not isinstance(say, dict):
        return False
    cols = text_columns(say.get("text", ""))
    span = len(cols) + COLS  # one full pass: in from the right edge, out through the left
    speed = say.get("speed") or ctx["speed"]
    travelled = (ctx["t"] - t0) * (8 + speed * 3)
    if travelled >= span * max(1, int(say.get("repeat") or 1)):
        st["say_t0"] = None
        return False
    for r in range(ROWS):
        cv[r] = [BLACK] * COLS
    style = say.get("style") if say.get("style") in SAY_STYLES else "plain"
    _say_background(cv, style, ctx["t"])
    _draw_text(cv, cols, COLS - int(travelled % span), tuple(say.get("rgb") or (255, 255, 255)), style, ctx["t"])
    return True


EFFECTS = {
    "solid": solid, "breathe": breathe, "rainbow": rainbow, "chase": chase, "plasma": plasma,
    "aurora": aurora, "wave": wave, "scanner": scanner, "twinkle": twinkle, "meteor": meteor,
    "fire": fire, "matrix": matrix,
}
MONITORS = {"monitor": monitor, "rack": rack, "vitals": vitals}
CLAUDE = {"claude_lanes": claude_lanes, "claude_drones": claude_drones, "claude_meter": claude_meter}
MODES = {**EFFECTS, **MONITORS, **CLAUDE, "text": banner}
