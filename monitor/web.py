"""Read-only HTTP server for the monitor page.

    /              the page (web/index.html)
    /apple-touch-icon.png, /icon.svg   the home-screen icon and favicon
    /api/state     latest status of each laptop
    /api/events    event feed; ?since=<id> returns only newer events (oldest first)
    /control       phone remote for the LED strip (web/control.html)
    /api/strip     GET the strip's control settings; POST JSON to change them (LAN only, no login)
Standard library only.
"""
import json
import os
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
MODES = ("monitor", "solid", "rainbow", "chase", "breathe", "off", "calibrate")
ROWS, COLS = 5, 60
LAYOUT_KEYS = ("flip_rows", "serpentine", "reverse")
DEFAULT_CONTROL = {"mode": "monitor", "color": [255, 255, 255], "brightness": 80, "speed": 5,
                   "cal": [], "layout": {k: False for k in LAYOUT_KEYS}}


def read_control():
    try:
        with open(CONTROL_FILE) as f:
            return {**DEFAULT_CONTROL, **json.load(f)}
    except (OSError, ValueError):
        return dict(DEFAULT_CONTROL)


def update_control(patch):
    """Validate a posted change, merge it into the saved settings (atomic write), return them."""
    ctl = read_control()
    if patch.get("mode") in MODES:
        ctl["mode"] = patch["mode"]
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
    if "speed" in patch:
        ctl["speed"] = max(1, min(10, int(patch["speed"])))
    ctl["changed"] = time.time()
    tmp = CONTROL_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(ctl, f)
    os.replace(tmp, CONTROL_FILE)
    return ctl


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
            if urlparse(self.path).path != "/api/strip":
                self._send(404, b"not found", "text/plain")
                return
            try:
                size = min(int(self.headers.get("Content-Length", "0")), 4096)
                patch = json.loads(self.rfile.read(size) or b"{}")
                if not isinstance(patch, dict):
                    raise ValueError("expected an object")
                self._json(update_control(patch))
            except (ValueError, TypeError, OSError) as exc:
                self._send(400, str(exc).encode(), "text/plain")

        def log_message(self, fmt, *args):
            pass  # the page polls every few seconds; keep the journal quiet

    return ThreadingHTTPServer(("0.0.0.0", port), Handler)
