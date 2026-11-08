"""Read-only HTTP server for the monitor page.

    /              the page (web/index.html)
    /apple-touch-icon.png, /icon.svg   the home-screen icon and favicon
    /api/state     latest status of each laptop
    /api/events    event feed; ?since=<id> returns only newer events (oldest first)
    /control       phone remote for the LED strip (web/control.html)
    /api/strip     GET the strip's control settings; POST JSON to change them (LAN only, no login)
    /api/claude    POST Claude Code activity from Agent Town (sessions + tool-call events); GET for debugging
Standard library only.
"""
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
PAGE = os.path.join(WEB_DIR, "index.html")
# URL path -> (file in web/, content type). iOS asks for the apple-touch-icon paths by default.
STATIC = {
    "/apple-touch-icon.png": ("apple-touch-icon.png", "image/png"),
    "/apple-touch-icon-precomposed.png": ("apple-touch-icon.png", "image/png"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
    "/strip-touch-icon.png": ("strip-touch-icon.png", "image/png"),
    "/strip-icon.svg": ("strip-icon.svg", "image/svg+xml"),
}


CONTROL_FILE = os.environ.get("STRIP_CONTROL", os.path.expanduser("~/hp-monitor/strip_control.json"))
# Keep in step with effects.MODES (the root daemon's list) plus off and calibrate.
MODES = ("monitor", "rack", "vitals", "claude_lanes", "claude_drones", "claude_meter", "text",
         "solid", "rainbow", "chase", "breathe", "plasma", "aurora", "wave", "scanner",
         "twinkle", "meteor", "fire", "matrix", "off", "calibrate")
SAY_STYLES = ("plain", "rainbow", "flash", "wave", "shake", "fire", "disco", "siren", "sparkle")  # as effects.py
ROWS, COLS = 5, 60
LAYOUT_KEYS = ("flip_rows", "serpentine", "reverse")
DEFAULT_CONTROL = {"mode": "monitor", "color": [255, 255, 255], "brightness": 80, "speed": 5,
                   "alerts": True, "text": "", "text_style": "plain", "text_static": False, "text_until": 0,
                   "prev_mode": "monitor", "say": None, "cal": [], "layout": {k: False for k in LAYOUT_KEYS}}


def _restore_target(ctl):
    """The mode to go back to when a banner ends: whatever was running before it."""
    prev = ctl.get("prev_mode")
    return prev if prev in MODES and prev != "text" else "monitor"


def _save(ctl):
    tmp = CONTROL_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(ctl, f)
    os.replace(tmp, CONTROL_FILE)


def read_control():
    try:
        with open(CONTROL_FILE) as f:
            ctl = {**DEFAULT_CONTROL, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULT_CONTROL)
    until = ctl.get("text_until")
    if ctl.get("mode") == "text" and until and time.time() > until:  # a timed banner has run out
        ctl["mode"], ctl["text_until"] = _restore_target(ctl), 0
        try:
            _save(ctl)
        except OSError:
            pass
    return ctl


def update_control(patch):
    """Validate a posted change, merge it into the saved settings (atomic write), return them."""
    ctl = read_control()
    if "mode" in patch:
        if patch["mode"] not in MODES:
            raise ValueError("unknown mode %r; reload the page" % (patch["mode"],))
        if patch["mode"] == "text" and ctl["mode"] != "text":
            ctl["prev_mode"] = ctl["mode"]  # so the banner can hand the wall back
        ctl["mode"] = patch["mode"]
    if patch.get("restore") and ctl["mode"] == "text":
        ctl["mode"], ctl["text_until"] = _restore_target(ctl), 0
    if "color" in patch:
        c = patch["color"]
        if isinstance(c, list) and len(c) == 3:
            ctl["color"] = [max(0, min(255, int(v))) for v in c]
    if "brightness" in patch:
        ctl["brightness"] = max(1, min(120, int(patch["brightness"])))
    if "cal" in patch and isinstance(patch["cal"], list):
        ctl["cal"] = [[int(r), int(c)] for r, c in patch["cal"][:ROWS * COLS]
                      if 0 <= int(r) < ROWS and 0 <= int(c) < COLS]
    if isinstance(patch.get("layout"), dict):
        ctl["layout"] = {**ctl.get("layout", {}),
                         **{k: bool(v) for k, v in patch["layout"].items() if k in LAYOUT_KEYS}}
    if "alerts" in patch:
        ctl["alerts"] = bool(patch["alerts"])
    if "text" in patch:
        ctl["text"] = str(patch["text"])[:160]
        # a banner lasts until changed, unless it was sent with a duration in seconds
        seconds = max(0, min(86400, int(patch.get("text_duration") or 0)))
        ctl["text_until"] = time.time() + seconds if seconds else 0
    if "text_style" in patch:
        ctl["text_style"] = patch["text_style"] if patch["text_style"] in SAY_STYLES else "plain"
    if "text_static" in patch:
        ctl["text_static"] = bool(patch["text_static"])
    if isinstance(patch.get("say"), dict) and str(patch["say"].get("text", "")).strip():
        say = patch["say"]
        rgb = say.get("rgb") if isinstance(say.get("rgb"), list) and len(say["rgb"]) == 3 else ctl["color"]
        # the id is how the daemon knows this is a new message to play
        ctl["say"] = {"text": str(say["text"]).strip()[:160], "id": int(time.time() * 1000),
                      "rgb": [max(0, min(255, int(v))) for v in rgb],
                      "style": say.get("style") if say.get("style") in SAY_STYLES else "plain",
                      "speed": max(1, min(10, int(say.get("speed") or ctl.get("speed", 5)))),
                      "repeat": max(1, min(5, int(say.get("repeat") or 1)))}
    if "speed" in patch:
        ctl["speed"] = max(1, min(10, int(patch["speed"])))
    ctl["changed"] = time.time()
    _save(ctl)
    return ctl


# Claude Code activity pushed from Agent Town on the Windows PC (see agent-town town/strip_bridge.py).
# The root daemon reads this file; events carry a seq so it only reacts to new ones.
CLAUDE_FILE = os.environ.get("STRIP_CLAUDE", os.path.expanduser("~/hp-monitor/claude_state.json"))
CLAUDE_KINDS = ("edit", "read", "shell", "web", "agent", "mcp", "other", "fail", "prompt", "done", "wait")
CLAUDE_STATES = ("working", "waiting", "idle")
_claude_lock = threading.Lock()


def read_claude():
    try:
        with open(CLAUDE_FILE) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def update_claude(patch):
    """Validate a push from Agent Town, append its events (new seq each), save atomically."""
    sessions = []
    for s in (patch.get("sessions") or [])[:8]:
        if isinstance(s, dict):
            sessions.append({"id": str(s.get("id", ""))[:64], "name": str(s.get("name", ""))[:30],
                             "state": s.get("state") if s.get("state") in CLAUDE_STATES else "idle",
                             "subs": max(0, min(20, int(s.get("subs") or 0)))})
    with _claude_lock:
        old = read_claude()
        seq, events = int(old.get("seq", 0)), list(old.get("events", []))
        for e in (patch.get("events") or [])[:50]:
            if isinstance(e, dict) and e.get("k") in CLAUDE_KINDS:
                seq = max(seq + 1, int(time.time() * 1000))
                events.append({"seq": seq, "s": str(e.get("s", ""))[:64], "k": e["k"]})
        state = {"written": time.time(), "seq": seq, "sessions": sessions, "events": events[-80:]}
        tmp = CLAUDE_FILE + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state, f)
        os.replace(tmp, CLAUDE_FILE)
    return state


def make_server(store, port):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype, cache="no-store"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", cache)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj):
            self._send(200, json.dumps(obj).encode(), "application/json")

        def do_GET(self):
            url = urlparse(self.path)
            if url.path in ("/", "/index.html"):
                try:
                    with open(PAGE, "rb") as f:
                        body = f.read()
                except OSError:
                    self._send(500, b"web/index.html is missing", "text/plain")
                    return
                self._send(200, body, "text/html; charset=utf-8")
            elif url.path in STATIC:
                name, ctype = STATIC[url.path]
                try:
                    with open(os.path.join(WEB_DIR, name), "rb") as f:
                        body = f.read()
                except OSError:
                    self._send(404, b"not found", "text/plain")
                    return
                self._send(200, body, ctype, cache="public, max-age=3600")
            elif url.path == "/control":
                try:
                    with open(os.path.join(WEB_DIR, "control.html"), "rb") as f:
                        body = f.read()
                except OSError:
                    self._send(500, b"web/control.html is missing", "text/plain")
                    return
                self._send(200, body, "text/html; charset=utf-8")
            elif url.path == "/api/strip":
                self._json(read_control())
            elif url.path == "/api/claude":
                self._json(read_claude())
            elif url.path == "/api/state":
                self._json(store.snapshot())
            elif url.path == "/api/events":
                try:
                    since = int(parse_qs(url.query).get("since", ["0"])[0])
                except ValueError:
                    since = 0
                self._json({"events": store.events(since), "last_id": store.snapshot()["last_event_id"]})
            else:
                self._send(404, b"not found", "text/plain")

        def do_POST(self):
            path = urlparse(self.path).path
            if path not in ("/api/strip", "/api/claude"):
                self._send(404, b"not found", "text/plain")
                return
            try:
                size = min(int(self.headers.get("Content-Length", "0")), 16384)
                patch = json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(patch, dict):
                    raise ValueError("expected an object")
                if path == "/api/claude":
                    update_claude(patch)
                    self._json({"ok": True})
                else:
                    self._json(update_control(patch))
            except (ValueError, TypeError, OSError) as exc:
                self._send(400, str(exc).encode(), "text/plain")

        def log_message(self, fmt, *args):
            pass  # the page polls every few seconds; keep the journal quiet

    return ThreadingHTTPServer(("0.0.0.0", port), Handler)
