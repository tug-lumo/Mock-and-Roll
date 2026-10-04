"""Lumostage local server.

    python serve.py            -> http://127.0.0.1:8137/

Serves ONLY the app (index.html, vendor/, brand/, assets/, layouts/) and the published
layout/models (published/) — never the rest of the project folder (docs, .claude, reference).

Publishing (the desktop app's "Publish to phone" button) writes published/layout.json and
published/models/<id>.glb. Publishing is accepted only from this PC directly: requests that
arrive through Tailscale Serve carry Tailscale identity / forwarding headers and are refused,
so phones and other remote viewers are read-only.

Remote viewing (private to your Tailscale devices):
    tailscale serve --bg 8137
"""
import json
import os
import re
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

# Under pythonw (no console) stderr is None and the request logger would crash every request.
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")

ROOT = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.join(ROOT, "published")
PORT = 8137
MAX_LAYOUT = 5 * 1024 * 1024        # 5 MB of JSON is far beyond any real layout
MAX_MODEL = 200 * 1024 * 1024       # imported .glb cap
ALLOWED = re.compile(r"^/(?:index\.html|published/[\w.\-/]+|assets/[\w.\-/]+|vendor/[\w.\-/]+|brand/[\w.\-/]+|layouts/[\w.\-/]+)?$")
MODEL_ID = re.compile(r"^glb_[a-z0-9]{1,24}$")
REMOTE_HEADERS = ("Tailscale-User-Login", "Tailscale-User-Name", "X-Forwarded-For", "X-Forwarded-Host")


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def _path(self):
        return self.path.split("?", 1)[0].split("#", 1)[0]

    def end_headers(self):
        # The app and the published layout change often — always revalidate.
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_GET(self):
        p = self._path()
        if ".." in p or not ALLOWED.match(p):
            self.send_error(404)
            return
        super().do_GET()

    def do_HEAD(self):
        self.do_GET()

    def _is_local(self):
        return self.client_address[0] in ("127.0.0.1", "::1") and not any(self.headers.get(h) for h in REMOTE_HEADERS)

    def _reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if not self._is_local():
            self._reply(403, {"error": "publishing is only allowed from this PC"})
            return
        n = int(self.headers.get("Content-Length") or 0)
        p = self._path()
        if p == "/api/publish/layout":
            if n <= 0 or n > MAX_LAYOUT:
                self._reply(413, {"error": "layout size out of range"})
                return
            try:
                data = json.loads(self.rfile.read(n))
            except ValueError:
                self._reply(400, {"error": "not JSON"})
                return
            if not isinstance(data, dict) or not isinstance(data.get("placedAssets"), list):
                self._reply(400, {"error": "not a Lumostage layout"})
                return
            os.makedirs(PUB, exist_ok=True)
            tmp = os.path.join(PUB, "layout.json.tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f)
            os.replace(tmp, os.path.join(PUB, "layout.json"))
            self._reply(200, {"ok": True})
            return
        m = re.match(r"^/api/publish/model/([\w]+)$", p)
        if m and MODEL_ID.match(m.group(1)):
            if n <= 0 or n > MAX_MODEL:
                self._reply(413, {"error": "model size out of range"})
                return
            buf = self.rfile.read(n)
            if buf[:4] != b"glTF":
                self._reply(400, {"error": "not a .glb"})
                return
            d = os.path.join(PUB, "models")
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, m.group(1) + ".glb"), "wb") as f:
                f.write(buf)
            self._reply(200, {"ok": True})
            return
        self._reply(404, {"error": "unknown endpoint"})


if __name__ == "__main__":
    # Loopback only: other devices reach it through Tailscale Serve, not the LAN.
    print("Lumostage serving on http://127.0.0.1:%d/" % PORT)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
