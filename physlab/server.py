"""Static + API server. Loopback-only in tests by construction.

GET /                     -> www/index.html
GET /api/topics           -> topic registry JSON
GET /api/run?topic=ID&... -> validated params -> frames + formulas
"""

import json
import math
import os
import posixpath
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from . import TOPICS, spec
from .topics import circuits, motion, heat

RUNNERS = {"circuits": circuits.run, "motion": motion.run, "heat": heat.run}
WWW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")
MAX_BODY = 0  # GET-only API


def _bad(handler, code, msg):
    body = json.dumps({"error": msg}).encode()
    handler.send_response(code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def validate(topic, query):
    """Return (params, error). Params are clamped into their spec range;
    anything malformed or unknown is rejected outright."""
    params = {}
    known = {p["id"]: p for p in topic.get("params", [])}
    for key in query:
        if key not in known:
            return None, "unknown parameter '%s'" % key[:64]
    for p in topic.get("params", []):
        raw = query.get(p["id"], [None])[0]
        if raw is None:
            params[p["id"]] = p["default"]
            continue
        if p["kind"] == "number":
            try:
                v = float(raw)
            except ValueError:
                return None, "parameter '%s' must be a number" % p["id"]
            if not math.isfinite(v):
                return None, "parameter '%s' must be finite" % p["id"]
            params[p["id"]] = min(max(v, p["min"]), p["max"])
        elif p["kind"] == "integer":
            try:
                v = float(raw)
            except ValueError:
                return None, "parameter '%s' must be a number" % p["id"]
            if not (math.isfinite(v) and float(v).is_integer()):
                return None, "parameter '%s' must be a whole number" % p["id"]
            params[p["id"]] = int(min(max(v, p["min"]), p["max"]))
        elif p["kind"] == "boolean":
            if raw not in ("0", "1", "true", "false"):
                return None, "parameter '%s' must be true/false" % p["id"]
            params[p["id"]] = raw in ("1", "true")
        elif p["kind"] == "select":
            ids = [c["id"] for c in p["choices"]]
            if raw not in ids:
                return None, "parameter '%s' must be one of %s" % (p["id"], ", ".join(ids))
            params[p["id"]] = raw
    return params, None


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # quiet by default
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, sort_keys=True).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/topics":
            return self._json({"topics": TOPICS})
        if parsed.path == "/api/run":
            q = parse_qs(parsed.query)
            tid = q.pop("topic", [None])[0]
            if not tid or len(tid) > 32 or not tid.isidentifier():
                return _bad(self, 400, "bad topic")
            topic = spec(tid)
            if topic is None:
                return _bad(self, 400, "unknown topic")
            if topic["status"] != "ready":
                return _bad(self, 400, "topic not ready: %s" % tid)
            params, err = validate(topic, q)
            if err:
                return _bad(self, 400, err)
            return self._json({"topic": tid, "params": params,
                               **RUNNERS[tid](params)})
        # static
        path = parsed.path.lstrip("/") or "index.html"
        path = posixpath.normpath(path)
        if path.startswith("..") or path.startswith("/") or "\x00" in path:
            return _bad(self, 404, "not found")
        fpath = os.path.join(WWW, path)
        if not os.path.abspath(fpath).startswith(os.path.abspath(WWW) + os.sep) \
                or not os.path.isfile(fpath):
            return _bad(self, 404, "not found")
        ctype = "text/html" if fpath.endswith(".html") else \
            "text/css" if fpath.endswith(".css") else \
            "application/javascript" if fpath.endswith(".js") else \
            "application/octet-stream"
        with open(fpath, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(port=8600):
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    import sys
    serve(int(sys.argv[1]) if len(sys.argv) > 1 else 8600)
