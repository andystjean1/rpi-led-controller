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
  text     the banner string for the text mode (+ text_style, text_static)
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


def claude_level(ctx, m):
    """How hard Claude is working, 0..1, eased so it surges quickly and dies down slowly. Built from
    the sessions that are mid-turn plus a smoothed tool-calls-per-second (about 1.4 a second, or a
    few busy sessions, is full blast)."""
    dt = ctx["dt"]
    working = sum(1 for s in ctx["claude"]["sessions"] if s["state"] == "working")
    m["rate"] = m["rate"] * math.exp(-dt / 3.0) + len(ctx["events"]) / 3.0
    target = min(1.0, 0.2 * min(working, 3) + m["rate"] / 1.8)
    m["level"] += (target - m["level"]) * (1 - math.exp(-dt / (0.35 if target > m["level"] else 1.8)))
    return m["level"]


def claude_meter(cv, ctx):
    """Blaze: a fire that grows with Claude's workload. Idle is a few embers; one session mid-turn
    is a modest flame in the middle; a flurry of tool calls fills the wall with tall, white-hot
    flames. Every tool call also throws a flare somewhere along the bottom."""
    if ctx["claude"] is None:
        return no_claude(cv, ctx)
    m = ctx["state"].setdefault("blaze", {"heat": [[0.0] * COLS for _ in range(ROWS)], "rate": 0.0, "level": 0.0})
    lv = claude_level(ctx, m) ** 0.55  # a curve, so modest work already makes a proper fire
    heat, last = m["heat"], ROWS - 1
    for _ in ctx["events"]:  # a flare per tool call
        c0 = random.randrange(COLS)
        for c in range(max(0, c0 - 3), min(COLS, c0 + 4)):  # a wider, hotter flare
            heat[last][c] = 1.3
    width = 0.12 + 0.88 * lv  # fuel spreads from the middle outwards as the level rises
    for c in range(COLS):
        w = max(0.0, min(1.0, (1 - abs(c - (COLS - 1) / 2) / (COLS / 2 * width)) * 2.2))  # flat-topped
        heat[last][c] = max(heat[last][c] * 0.82, w * (0.25 + 0.75 * lv) * random.uniform(0.5, 1.0))
    cool = 0.34 - 0.31 * lv  # flames climb higher the less they cool (at full they reach the top row)
    for r in range(last):
        for c in range(COLS):
            below = (heat[r + 1][(c - 1) % COLS] + heat[r + 1][c] * 2 + heat[r + 1][(c + 1) % COLS]) / 4
            heat[r][c] = max(0.0, below - random.uniform(0.3, 1.0) * cool)
    gain = 0.7 + 0.9 * lv  # and burn brighter and whiter
    for r in range(ROWS):
        for c in range(COLS):
            h = min(1.3, heat[r][c] * gain)
            cv[r][c] = (int(min(255, h * 400)), int(max(0, min(255, (h - 0.35) * 300))),
                        int(max(0, min(255, (h - 0.9) * 700))))


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


# ---------------------------------------------------------------- homelab map
#
# The whole house on one wall, every light tied to something real:
#
#   cols  0-1   the internet (left)          58-59  the internet (right)
#   cols  3-12  the PC: col 3 overall health, row 0 one pixel per app (Agent Town's buildings),
#               rows 1-4 one Claude session each
#   cols 13-22  row 2: the wire Agent Town pushes Claude activity down to the Pi
#   cols 23-30  the Pi (raspberry; warms to orange as it heats up, blinks blue if its poller died)
#   cols 31-47  row 1 / row 3: the Pi's poll wires to the HP / the Lenovo
#   cols 48-55  rows 0-1 the HP (row 0 its scheduled tasks, row 1 its apps); rows 3-4 the Lenovo
#
# Packets: each Claude tool call leaves its session's row and runs to the Pi in the tool's colour;
# each real poll sends a ping out to a laptop and its reply comes back in that laptop's health
# colour (a ping to a laptop that is down dies halfway in red). Collector tasks downloading (the
# HP's, or any task mid-run on the PC) and busy Claude sessions talking to the API stream to and
# from the internet at the edges.

HL_PC = 3            # PC node: cols 3..12
HL_PI = (23, 30)
HL_LAP = (48, 55)
HL_WIRE_PC = (2, 13, 22)                       # row, first col, last col
HL_WIRE_LAP = ((1, 31, 47), (3, 31, 47))       # per laptop slot
HL_LAP_ROWS = ((0, 1), (3, 4))
RASPBERRY = (215, 20, 90)
HL_WIRE_RGB = (6, 9, 20)
HL_NET_RGB = (20, 40, 150)
HL_PING = (110, 110, 150)


def add(cv, r, c, rgb):
    """Add light to one pixel (packets and flashes blend over what is there)."""
    if 0 <= r < ROWS and 0 <= c < COLS:
        p = cv[r][c]
        cv[r][c] = (min(255, p[0] + int(rgb[0])), min(255, p[1] + int(rgb[1])), min(255, p[2] + int(rgb[2])))


def _hl_packet(st, path, rgb, speed, tail=4, then=None):
    st["packets"].append({"path": path, "pos": 0.0, "rgb": rgb, "speed": speed, "tail": tail, "then": then,
                          "done": False})


def _hl_flash(st, key, rgb, t, dur=0.4):
    st["flash"][key] = (rgb, t, dur)


def _hl_flash_k(st, key, t):
    """How much of a node's flash is left (0..1) and its colour."""
    f = st["flash"].get(key)
    if not f:
        return 0.0, BLACK
    k = 1 - (t - f[1]) / f[2]
    if k <= 0:
        del st["flash"][key]
        return 0.0, BLACK
    return k, f[0]


def _hl_stream(st, side, rate, dt, both_ways=False):
    """Packets between the internet at one edge and the node next to it, rate per second."""
    acc = st["acc"].get(side, 0.0) + rate * dt
    while acc >= 1:
        acc -= 1
        if side == "L":
            row = random.randrange(ROWS)
            path = [(row, c) for c in (0, 1, 2)]
        else:
            row = random.choice(HL_LAP_ROWS[0])
            path = [(row, c) for c in (59, 58, 57, 56)]
        if both_ways and random.random() < 0.5:
            path.reverse()  # a request going out rather than data coming in
        _hl_packet(st, path, (90, 120, 255), random.uniform(9, 14), tail=3)
    st["acc"][side] = acc


def _hl_net(cv, t, cols, busy):
    """The internet: a dim blue shimmer that brightens while something is talking to it."""
    for r in range(ROWS):
        for c in cols:
            k = 0.25 + 0.2 * math.sin(t * 0.9 + r * 1.7 + c * 2.3) + 0.35 * busy
            cv[r][c] = scale(HL_NET_RGB, max(0.08, min(1.0, k)))


def _hl_pc(cv, ctx, st):
    t = ctx["t"]
    claude = ctx.get("claude")
    cols = range(HL_PC, HL_PC + 10)
    if claude is None:  # Agent Town is quiet: the PC is off or the town is stopped
        k = 0.04 + 0.12 * pulse(t, 0.3)
        fill(cv, scale((140, 70, 220), k), cols=cols)
        return
    pc = claude.get("pc") or {}
    fill(cv, scale(LEVEL.get(pc.get("overall", "ok"), LEVEL["ok"]), 1.0), cols=[HL_PC])
    for i, level in enumerate((pc.get("apps") or [])[:9]):
        k, rgb = _hl_flash_k(st, ("app", i), t)
        cv[0][HL_PC + 1 + i] = mix(LEVEL.get(level, LEVEL["idle"]), rgb, k * 0.8)
    load = (pc.get("cpu") or 0) / 100
    sessions = claude["sessions"][:4]
    for i in range(4):
        row = 1 + i
        base = (4 + int(30 * load), 4 + int(8 * load), 10)  # warmer as the PC's CPU works harder
        if i < len(sessions):
            s = sessions[i]
            if s["state"] == "waiting":
                base = scale(AMBER, 0.15 + 0.6 * pulse(t, 0.9))
            elif s["state"] == "working":
                base = (0, 26, 34)
        for c in range(HL_PC + 1, HL_PC + 10):
            cv[row][c] = base
        if i < len(sessions) and sessions[i]["state"] == "working":  # a thinking glint sweeps the row
            x = HL_PC + 1 + (t * 6 + i * 2.3) % 9
            for c in range(HL_PC + 1, HL_PC + 10):
                add(cv, row, c, scale((0, 160, 200), max(0.0, 1 - abs(c - x) / 1.6)))
        for j in range(min(sessions[i]["subs"], 4) if i < len(sessions) else 0):
            cv[row][HL_PC + 9 - j] = scale(KIND_RGB["agent"], 0.4 + 0.6 * pulse(t + j * 0.4, 1.4))
        k, rgb = _hl_flash_k(st, ("row", i), t)
        if k:
            for c in range(HL_PC + 1, HL_PC + 10):
                cv[row][c] = mix(cv[row][c], rgb, k)


def _hl_pi(cv, ctx, st):
    t, (a, b) = ctx["t"], HL_PI
    pi = ctx.get("pi") or {}
    temp = pi.get("temp")
    heat = max(0.0, min(1.0, ((temp or 50) - 55) / 25))  # 55 C raspberry ... 80 C orange
    body = mix(RASPBERRY, (255, 120, 0), heat)
    load = max(0.0, min(1.0, (pi.get("load") or 0) / 4))
    k, frgb = _hl_flash_k(st, "pi", t)
    for r in range(ROWS):
        for c in range(a, b + 1):
            if (r in (0, ROWS - 1)) and c in (a, b):
                continue  # rounded corners
            core = 1 <= r <= 3 and a + 2 <= c <= b - 2
            lv = (0.32 + 0.12 * load if core else 0.13) + 0.08 * pulse(t, 0.25)
            cv[r][c] = mix(scale(body, lv), frgb, k * (0.55 if core else 0.25))
    if ctx.get("laptops") is None:  # the poller on the Pi itself has died: blink its core blue
        if int(t * 2) % 2 == 0:
            for r in (1, 2, 3):
                for c in range(a + 2, b - 1):
                    cv[r][c] = (0, 40, 220)


def _hl_lap(cv, ctx, st, slot, info):
    t, (r0, r1) = ctx["t"], HL_LAP_ROWS[slot]
    a, b = HL_LAP
    width = b - a + 1
    state = info.get("overall", "down")
    if state == "down":
        k = 0.1 + 0.5 * pulse(t, 0.5)
        fill(cv, scale(LEVEL["down"], k), rows=(r0, r1), cols=range(a, b + 1))
        return
    services, apps = info.get("services") or [], info.get("apps") or []
    running = set(info.get("running") or [])
    fk, frgb = _hl_flash_k(st, ("lap", slot), t)
    if not services and not apps:  # a box on standby: dim, with the status feed's heartbeat
        fill(cv, scale(LEVEL.get(state, LEVEL["ok"]), 0.25), rows=(r0, r1), cols=range(a, b + 1))
        x = a + (t * 1.5) % width
        for c in range(a, b + 1):
            for r in (r0, r1):
                add(cv, r, c, scale(LEVEL.get(state, LEVEL["ok"]), max(0.0, 1 - abs(c - x)) * 1.5))
    else:
        blink = int(t * 3) % 2 == 0
        for row, items in ((r0, sorted(services)), (r1, apps)):
            for c in range(a, b + 1):
                cv[row][c] = scale(LEVEL["idle"], 0.15)
            for k, (name, level) in enumerate(items[:width]):
                rgb = LEVEL.get(level, LEVEL["warn"])
                if level == "bad" and not blink:
                    rgb = scale(rgb, 0.25)
                if row == r0 and name in running:  # mid-run: twinkles white
                    rgb = mix(rgb, (255, 255, 255), 0.3 + 0.5 * pulse(t + k * 0.3, 2.0))
                sk, srgb = _hl_flash_k(st, ("svc", slot, name), t)
                cv[row][a + k] = mix(rgb, srgb, sk)
    if fk:
        for r in (r0, r1):
            for c in range(a, b + 1):
                cv[r][c] = mix(cv[r][c], frgb, fk * 0.5)


def homelab(cv, ctx):
    """The homelab map: the PC, the Pi and both laptops as nodes, and the real traffic between them
    (see the block comment above)."""
    t, dt = ctx["t"], ctx["dt"]
    st = ctx["state"].setdefault("homelab", {"packets": [], "flash": {}, "acc": {}, "at": {}, "runs": {},
                                             "written": None, "conns": None})
    claude, laptops = ctx.get("claude"), ctx.get("laptops")
    labels = sorted(laptops)[:2] if laptops else []

    # ---- turn what changed since the last frame into packets
    if claude is not None:
        sessions = claude["sessions"]
        path = [(HL_WIRE_PC[0], c) for c in range(HL_WIRE_PC[1], HL_WIRE_PC[2] + 1)]
        for ev in ctx["events"]:
            rgb = KIND_RGB.get(ev["k"], KIND_RGB["other"])
            i = _lane_of(sessions, ev["s"]) if sessions else 0
            if i < 4:
                _hl_flash(st, ("row", i), rgb, t, 0.5)
            _hl_packet(st, path, rgb, 16 + ctx["speed"], tail=4, then=("flash", "pi", rgb))
        written = claude.get("written")
        if written != st["written"]:
            if st["written"] is not None and not ctx["events"]:  # a plain heartbeat push
                _hl_packet(st, path, (30, 30, 50), 14, tail=2)
            st["written"] = written
        conns = (claude.get("pc") or {}).get("conns")
        if isinstance(conns, int):
            if st["conns"] is not None and conns > st["conns"]:  # apps on the PC talking to each other
                n_apps = len((claude.get("pc") or {}).get("apps") or [])
                for _ in range(min(conns - st["conns"], 4)):
                    if n_apps:
                        _hl_flash(st, ("app", random.randrange(min(n_apps, 9))), (255, 255, 255), t, 0.35)
            st["conns"] = conns
    for slot, label in enumerate(labels):
        info = laptops[label]
        at = info.get("at")
        if at != st["at"].get(label):
            if label in st["at"]:  # the poller just heard from this laptop (or gave up on it)
                row, c0, c1 = HL_WIRE_LAP[slot]
                out = [(row, c) for c in range(c0, c1 + 1)]
                if info.get("overall") == "down":
                    _hl_packet(st, out[:len(out) // 2], HL_PING, 26, tail=3, then=("lost", out[len(out) // 2]))
                else:
                    _hl_packet(st, out, HL_PING, 34, tail=3, then=("reply", slot, label))
            st["at"][label] = at
        runs = info.get("runs") or {}
        seen = st["runs"].setdefault(label, dict(runs))
        for name, last in runs.items():
            if last and seen.get(name) and last != seen[name]:  # a task ran since the last poll
                _hl_flash(st, ("svc", slot, name), (255, 255, 255), t, 3.0)
                st["acc"]["R"] = st["acc"].get("R", 0.0) + (6 if slot == 0 else 0)
            seen[name] = last

    # ---- streams to and from the internet
    working = sum(1 for s in claude["sessions"] if s["state"] == "working") if claude else 0
    pc_tasks = ((claude or {}).get("pc") or {}).get("tasks_running") or 0
    _hl_stream(st, "L", 1.2 * min(working, 4) + 2.0 * min(pc_tasks, 3), dt, both_ways=True)
    hp = laptops.get(labels[0]) if labels else None
    hp_running = len((hp or {}).get("running") or []) if hp and hp.get("overall") != "down" else 0
    _hl_stream(st, "R", 3.0 * min(hp_running, 3), dt)

    # ---- the scene
    busy_l = min(1.0, (working + pc_tasks) / 3)
    _hl_net(cv, t, (0, 1), busy_l)
    _hl_net(cv, t, (58, 59), min(1.0, hp_running / 2))
    row, c0, c1 = HL_WIRE_PC
    fill(cv, HL_WIRE_RGB if claude is not None else BLACK, rows=[row], cols=range(c0, c1 + 1))
    for slot in range(2):
        row, c0, c1 = HL_WIRE_LAP[slot]
        info = laptops.get(labels[slot]) if slot < len(labels) else None
        if info is None:
            continue
        down = info.get("overall") == "down"
        for c in range(c0, c1 + 1):
            cv[row][c] = ((45, 0, 0) if c % 2 == 0 else BLACK) if down else HL_WIRE_RGB
    _hl_pc(cv, ctx, st)
    _hl_pi(cv, ctx, st)
    for slot, label in enumerate(labels):
        _hl_lap(cv, ctx, st, slot, laptops[label])
    if laptops is None:  # no poll data at all: the laptop nodes pulse blue like the other monitors
        k = 0.1 + 0.4 * pulse(t, 0.32)
        for r0, r1 in HL_LAP_ROWS:
            fill(cv, scale((0, 40, 220), k), rows=(r0, r1), cols=range(HL_LAP[0], HL_LAP[1] + 1))

    # ---- packets on top
    for p in st["packets"]:
        path, head = p["path"], int(p["pos"])
        for tail in range(p["tail"]):
            idx = head - tail
            if 0 <= idx < len(path):
                k = (1 - tail / p["tail"]) ** 1.5
                add(cv, path[idx][0], path[idx][1], scale(p["rgb"], k))
        p["pos"] += p["speed"] * dt
        if not p["done"] and p["pos"] >= len(path):
            p["done"] = True
            then = p["then"]
            if not then:
                continue
            if then[0] == "flash":
                _hl_flash(st, then[1], then[2], t)
            elif then[0] == "lost":
                _hl_flash(st, ("lost", then[1]), (255, 0, 0), t, 0.8)
            elif then[0] == "reply":
                slot, label = then[1], then[2]
                info = (laptops or {}).get(label, {})
                rgb = TRACE.get(info.get("overall", "ok"), TRACE["ok"])
                _hl_flash(st, ("lap", slot), rgb, t, 0.5)
                row, c0, c1 = HL_WIRE_LAP[slot]
                back = [(row, c) for c in range(c1, c0 - 1, -1)]
                _hl_packet(st, back, rgb, 26, tail=5, then=("flash", "pi", rgb))
    st["packets"] = [p for p in st["packets"] if p["pos"] - p["tail"] < len(p["path"])][-200:]
    for key in [k for k in st["flash"] if k[0] == "lost"]:  # a ping that never got an answer
        k, rgb = _hl_flash_k(st, key, t)
        if k:
            r, c = key[1]
            for dc in (-1, 0, 1):
                add(cv, r, c + dc, scale(rgb, k * (1 if dc == 0 else 0.4)))


# ---------------------------------------------------------------- data pipelines
#
# ctx["claude"]["pc"]["pipe"] (from Agent Town's collectors/pipeline.py) lists each data pipeline on
# the PC: {"k": lane, "st": ok|late|fail|off, "run": task mid-run, "ticks"/"stored"/"picks"/"posts"/
# "errors": today's counts, "last": {"id": run start (epoch s), "stage", "picks", "err"} or None}.
# A run's stage climbs tick (started) -> skip (nothing due) or stored -> built -> picks -> posted while
# Agent Town re-reads its log every 5 s, so both modes see it happen live.

PIPE_LANES = ("nba", "ncaab", "nhl", "cfb", "td", "parlay")
PIPE_RGB = {"nba": (255, 110, 0), "ncaab": (40, 90, 255), "nhl": (110, 220, 255), "cfb": (40, 220, 60),
            "td": (255, 40, 160), "parlay": (255, 190, 0)}
PIPE_STAGES = ("tick", "skip", "stored", "built", "picks", "posted")
ERR_RGB = (255, 0, 0)
SPARK_RGB = (255, 255, 255)
GREY = (90, 90, 100)


def _pipe(ctx):
    """The pipe rows in lane order, or None when Agent Town isn't sending them."""
    pc = (ctx.get("claude") or {}).get("pc") or {}
    rows = pc.get("pipe")
    if not isinstance(rows, list):
        return None
    by_k = {r.get("k"): r for r in rows if isinstance(r, dict)}
    return [by_k.get(k) or {"k": k, "st": "off", "last": None} for k in PIPE_LANES]


def _pipe_changes(st, rows):
    """What happened since the last frame: [(lane index, "new" | "advance", last, previous key)], where a
    key is (run id, stage, err) and is None for a new run. The first sight of a lane is remembered, not
    replayed."""
    seen = st.setdefault("seen", {})
    out = []
    for i, row in enumerate(rows):
        last = row.get("last")
        if not last:
            continue
        key = (last.get("id"), last.get("stage"), bool(last.get("err")))
        prev = seen.get(row["k"])
        seen[row["k"]] = key
        if prev is None or prev == key:
            continue
        if prev[0] != key[0]:
            out.append((i, "new", last, None))
        else:
            out.append((i, "advance", last, prev))
    return out


def _stage_at_least(stage, other):
    return PIPE_STAGES.index(stage) >= PIPE_STAGES.index(other)


def no_pipe(cv, ctx):
    """Agent Town isn't sending pipeline data: six faint lane-coloured dots breathing on the middle row."""
    k = 0.04 + 0.2 * pulse(ctx["t"], 0.3)
    for i, lane in enumerate(PIPE_LANES):
        cv[2][i * 10 + 4] = scale(PIPE_RGB[lane], k)


# ---- rain: six lanes of sky over a reservoir

RAIN_W = 10  # columns per lane; the last one is a dark divider
RAIN_SKY = (0, 1, 2)
RAIN_POOL = (3, 4)


def _rain_drop(st, i, rgb, kind, speed=5.0):
    col = i * RAIN_W + random.randrange(1, RAIN_W - 2)
    st["drops"].append({"i": i, "c": col, "y": -0.5, "rgb": rgb, "kind": kind, "v": speed})


def rain(cv, ctx):
    """Collector rain: each pipeline is a lane of sky over its reservoir. A run that finds nothing due
    drops a thin grey drizzle, a stored snapshot a bright drop in the lane's colour that splashes into
    the reservoir, new picks white sparks, a failed run a red drop and a red ripple. The reservoir holds
    one cell per snapshot stored today. A late lane's sky goes dark and blinks dim red (the missed beat);
    the cloud on the top row glows while that lane's task runs."""
    rows = _pipe(ctx)
    if rows is None:
        no_pipe(cv, ctx)
        return alert_overlay(cv, ctx)
    t, dt = ctx["t"], ctx["dt"]
    st = ctx["state"].setdefault("rain", {"drops": [], "sparks": [], "flash": {}, "amb": {}})

    for i, kind, last, prev_key in _pipe_changes(st, rows):
        lane = rows[i]["k"]
        stage, err = last["stage"], last.get("err")
        prev = prev_key[1] if prev_key else None
        if err:
            if not (prev_key and prev_key[2]):  # one red drop when the run first shows an error
                _rain_drop(st, i, ERR_RGB, "err", 4.0)
            continue
        if stage == "skip":
            _rain_drop(st, i, mix(PIPE_RGB[lane], GREY, 0.7), "skip", 4.0)
        elif stage in ("stored", "built") and (kind == "new" or not _stage_at_least(prev or "tick", "stored")):
            _rain_drop(st, i, PIPE_RGB[lane], "stored", 6.0)
        elif stage == "picks" and (kind == "new" or prev != "picks"):
            if kind == "new" or not _stage_at_least(prev or "tick", "stored"):
                _rain_drop(st, i, PIPE_RGB[lane], "stored", 6.0)
            _rain_drop(st, i, SPARK_RGB, "picks", 5.0)
        elif stage == "posted":
            _rain_drop(st, i, SPARK_RGB, "picks", 5.0)

    for i, row in enumerate(rows):
        lane, c0 = row["k"], i * RAIN_W
        rgb, status = PIPE_RGB[lane], row.get("st", "off")
        cols = range(c0, c0 + RAIN_W - 1)
        if status == "off":
            fill(cv, scale(LEVEL["idle"], 0.25), cols=cols)
            continue
        # the sky: a faint tint of the lane, dark red blinking when the lane missed its beat
        if status == "late":
            fill(cv, scale((90, 0, 0), 0.1 + 0.6 * pulse(t, 0.35)), rows=RAIN_SKY, cols=cols)
        else:
            fill(cv, scale(rgb, 0.02), rows=RAIN_SKY, cols=cols)
            running = row.get("run") or ((row.get("last") or {}).get("stage") == "tick")
            if running:  # the cloud: the top row glows while the task runs
                for c in cols:
                    cv[0][c] = scale(mix(rgb, (200, 200, 220), 0.5), 0.12 + 0.2 * pulse(t + c * 0.15, 0.9))
            # ambient drizzle: barely there, so a real drop always stands out
            acc = st["amb"].get(lane, 0.0) + 0.25 * dt
            if acc >= 1:
                acc -= 1
                _rain_drop(st, i, scale(rgb, 0.12), "amb", 3.0)
            st["amb"][lane] = acc
        # the reservoir: one cell per snapshot stored today, bottom row first; today's errors in red from the right
        cells = [(r, c) for r in (4, 3) for c in cols]
        stored, errors = min(row.get("stored") or 0, len(cells)), min(row.get("errors") or 0, len(cells))
        for n, (r, c) in enumerate(cells):
            if n < stored:
                k = 0.3 + (0.15 * pulse(t * 0.5 + c * 0.3, 0.4) if n == stored - 1 else 0.0)
                cv[r][c] = scale(rgb, k)
            else:
                cv[r][c] = scale(rgb, 0.03)
        for n in range(errors):
            r, c = cells[len(cells) - 1 - n]
            cv[r][c] = scale(ERR_RGB, 0.35)
        if row.get("st") == "fail":  # the reservoir's rim blinks red while the task's last run failed
            k = 0.15 + 0.85 * pulse(t, 1.2)
            cv[3][c0], cv[3][c0 + RAIN_W - 2] = scale(ERR_RGB, k), scale(ERR_RGB, k)
        fk, frgb = _hl_flash_k(st, ("pool", i), t)
        if fk:
            for r in RAIN_POOL:
                for c in cols:
                    cv[r][c] = mix(cv[r][c], frgb, fk * (0.6 if r == 3 else 0.3))

    # drops fall to the reservoir's surface (row 3)
    for d in st["drops"]:
        d["y"] += d["v"] * dt
        head = int(d["y"])
        for tail in range(3 if d["kind"] != "amb" else 1):
            r = head - tail
            if 0 <= r <= 2:
                k = (1 - tail / 3) ** 1.5
                add(cv, r, d["c"], scale(d["rgb"], k))
                if d["kind"] == "stored" and tail == 0:
                    add(cv, r, d["c"] + 1, scale(d["rgb"], 0.6))  # a fat drop
        if d["y"] >= 3 and not d.get("landed"):
            d["landed"] = True
            if d["kind"] == "stored":
                _hl_flash(st, ("pool", d["i"]), d["rgb"], t, 0.8)
            elif d["kind"] == "err":
                _hl_flash(st, ("pool", d["i"]), ERR_RGB, t, 1.6)
            elif d["kind"] == "picks":
                for _ in range(5):
                    st["sparks"].append({"x": d["c"] + random.uniform(-1.5, 1.5), "y": 2.8,
                                         "vx": random.uniform(-3, 3), "vy": -random.uniform(3, 6), "life": 1.0})
            elif d["kind"] == "skip":
                add(cv, 3, d["c"], scale(GREY, 0.8))
    st["drops"] = [d for d in st["drops"] if d["y"] < 5][-120:]
    for s in st["sparks"]:
        s["x"] += s["vx"] * dt
        s["y"] += s["vy"] * dt
        s["vy"] += 9 * dt  # they arc back down
        s["life"] -= dt * 0.9
        if s["life"] > 0:
            plot(cv, s["x"], s["y"], scale(SPARK_RGB, s["life"]))
    st["sparks"] = [s for s in st["sparks"] if s["life"] > 0 and s["y"] < 4][-60:]
    # dark dividers between the lanes
    for i in range(1, len(PIPE_LANES)):
        fill(cv, BLACK, cols=[i * RAIN_W - 1])
    return alert_overlay(cv, ctx)


# ---- conveyor: collect -> build -> picks -> post

BELT_STATIONS = ((0, 7), (17, 24), (34, 41), (52, 59))  # first and last column of each station
STATION_RGB = ((0, 150, 170), (120, 70, 220), (230, 170, 0), (88, 101, 242))  # post = Discord blurple
STAGE_STATION = {"tick": 0, "skip": 0, "stored": 1, "built": 1, "picks": 2, "posted": 3}
PACKET_SPEED = 12.0  # columns per second
PACKET_ROW = 2
REST_S = 8.0  # a finished run's packet waits at its last station this long, then fades


def _slot(station, i):
    """The column a lane's packet rests on inside a station."""
    return BELT_STATIONS[station][0] + 1 + i


def conveyor(cv, ctx):
    """Conveyor belt: every run is a packet in its pipeline's colour that rides collect -> build ->
    picks -> post as far as the run really got, live (grey and fading out in collect when nothing was
    due). The station it reaches flashes; post flashes Discord blurple. A failed run's packet turns red
    and stays jammed at that station until the lane's next run. The bottom row of each station keeps
    one dot per pipeline for how far its last run got there. The belt runs faster while any run is in
    flight."""
    rows = _pipe(ctx)
    if rows is None:
        no_pipe(cv, ctx)
        return alert_overlay(cv, ctx)
    t, dt = ctx["t"], ctx["dt"]
    st = ctx["state"].setdefault("conveyor", {"packets": {}, "flash": {}, "belt": 0.0})
    packets = st["packets"]  # lane -> packet

    for i, kind, last, _ in _pipe_changes(st, rows):
        lane = rows[i]["k"]
        target = STAGE_STATION[last["stage"]]
        p = packets.get(lane)
        if kind == "new" or p is None:
            p = packets[lane] = {"i": i, "x": float(BELT_STATIONS[0][0]), "target": 0, "at": None,
                                 "skip": False, "err": False, "fade": 1.0}
        p["target"] = max(p["target"], target)
        p["skip"] = last["stage"] == "skip"
        p["err"] = bool(last.get("err"))
        p["at"] = None  # moving again (or about to re-arrive)

    busy = any(r.get("run") for r in rows) or any(
        p["x"] != _slot(p["target"], p["i"]) for p in packets.values())
    st["belt"] += dt * (6.0 if busy else 1.5)

    # the belt between the stations: rails on rows 0 and 4, faint chevrons on rows 1-3
    for (_, a_end), (b_start, _) in zip(BELT_STATIONS, BELT_STATIONS[1:]):
        for c in range(a_end + 1, b_start):
            cv[0][c] = cv[4][c] = (8, 8, 12)
            for r in (1, 2, 3):
                on = int(c - st["belt"] - abs(r - 2)) % 4 == 0  # a ">" chevron
                cv[r][c] = (22, 22, 30) if on else (3, 3, 5)

    # the stations: a dim frame in the station's colour, flashing as packets arrive
    for s, (a, b) in enumerate(BELT_STATIONS):
        base = STATION_RGB[s]
        fk, frgb = _hl_flash_k(st, ("st", s), t)
        for r in range(4):
            for c in range(a, b + 1):
                edge = r == 0 or c in (a, b)
                cv[r][c] = mix(scale(base, 0.22 if edge else 0.03), frgb, fk * (0.9 if edge else 0.35))
        # bottom row: one dot per pipeline, lit if its last run got this far
        cv[4][a] = cv[4][b] = scale(base, 0.22)
        for i, row in enumerate(rows):
            last, c = row.get("last"), _slot(s, i)
            if not last or row.get("st") == "off":
                cv[4][c] = (2, 2, 4)
                continue
            reached = STAGE_STATION[last["stage"]]
            if last.get("err") and reached == s:
                cv[4][c] = scale(ERR_RGB, 0.25 + 0.5 * pulse(t, 1.0))
            elif last["stage"] == "skip":
                cv[4][c] = scale(GREY, 0.25) if s == 0 else (2, 2, 4)
            elif reached >= s:
                cv[4][c] = scale(PIPE_RGB[row["k"]], 0.35)
            else:
                cv[4][c] = (2, 2, 4)
            if row.get("st") == "late" and s == 0:  # missed its beat: the collect dot blinks dim red
                cv[4][c] = scale((120, 0, 0), pulse(t, 0.35))

    # the packets
    for lane, p in list(packets.items()):
        goal = _slot(p["target"], p["i"])
        if p["x"] < goal:
            p["x"] = min(goal, p["x"] + PACKET_SPEED * dt)
        elif p["x"] > goal:  # back to the start of collect for a new run
            p["x"] = max(goal, p["x"] - PACKET_SPEED * 2 * dt)
        if p["x"] == goal and p["at"] is None:
            p["at"] = t
            if not p["skip"] and p["target"] > 0:
                _hl_flash(st, ("st", p["target"]), ERR_RGB if p["err"] else
                          (STATION_RGB[3] if p["target"] == 3 else PIPE_RGB[lane]), t, 0.7)
        rgb = ERR_RGB if p["err"] else mix(PIPE_RGB[lane], GREY, 0.7) if p["skip"] else PIPE_RGB[lane]
        row_running = rows[p["i"]].get("run")
        if p["at"] is not None and not p["err"] and not row_running:
            idle = t - p["at"]
            hold = 2.0 if p["skip"] else REST_S
            if idle > hold:
                p["fade"] = max(0.0, 1 - (idle - hold) / 2)
                if p["fade"] == 0:
                    del packets[lane]
                    continue
        k = p["fade"] * ((0.55 + 0.45 * pulse(t, 1.5)) if p["err"] else 1.0)
        x = int(round(p["x"]))
        for tail in range(3):
            if p["at"] is not None and tail:
                break  # resting: just the dot
            add(cv, PACKET_ROW, x - tail, scale(rgb, k * (1 - tail / 3) ** 1.5))
    return alert_overlay(cv, ctx)


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
    """The banner text, in the chosen style: scrolling round and round, or held still and centred
    (text_static) when it fits on the wall."""
    cols = text_columns(ctx.get("text") or "HELLO")
    style = ctx.get("text_style") if ctx.get("text_style") in SAY_STYLES else "plain"
    _say_background(cv, style, ctx["t"])
    width = len(cols) - 1  # the last column is only the gap after the final letter
    if ctx.get("text_static") and width <= COLS:
        x0 = (COLS - width) // 2
    else:
        x0 = COLS - int(ctx["t"] * (8 + ctx["speed"] * 3)) % (len(cols) + COLS)
    _draw_text(cv, cols, x0, tuple(ctx["rgb"]), style, ctx["t"])


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
MONITORS = {"homelab": homelab, "monitor": monitor, "rack": rack, "vitals": vitals, "rain": rain,
            "conveyor": conveyor}
CLAUDE = {"claude_lanes": claude_lanes, "claude_drones": claude_drones, "claude_meter": claude_meter}
MODES = {**EFFECTS, **MONITORS, **CLAUDE, "text": banner}
