"""Read-only HTTP server for the monitor page.

    /              the page (web/index.html)
    /api/state     latest status of each laptop
    /api/events    event feed; ?since=<id> returns only newer events (oldest first)
Standard library only.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

PAGE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "index.html")


def make_server(store, port):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
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

        def log_message(self, fmt, *args):
            pass  # the page polls every few seconds; keep the journal quiet

    return ThreadingHTTPServer(("0.0.0.0", port), Handler)
