"""Static + API server. Loopback-only in tests by construction.

GET  /                              -> www/index.html
GET  /api/topics                    -> topic registry JSON
GET  /api/run?topic=ID&...          -> validated params -> frames + formulas

Quiz (storage: physlab/quizdb.py, SQLite):
GET  /api/quiz?player=P             -> all questions by topic + P's progress
GET  /api/quiz/question?id=Q&player=P  one question (solution only once solved/revealed)
GET  /api/quiz/history?player=P     -> P's answers, newest first
GET  /api/quiz/players              -> recent players on this machine
POST /api/quiz/player  {name}       -> new player
POST /api/quiz/answer  {player, question, inputs}
                                    -> runs the experiment, grades, records; returns
                                       the run so the browser can play it
POST /api/quiz/reveal  {player, question}   (after 2 wrong tries, no points)

Sandbox (physlab/sandbox.py):
GET  /api/sandbox                   -> catalogs, fields, presets and defaults per topic
POST /api/sandbox/run  {topic, world}
                                    -> strictly validated world -> {world, runs: [{label,
                                       result}], notes}; 400 with a reason otherwise
"""

import json
import math
import os
import posixpath
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from . import TOPICS, spec, quiz, sandbox
from .quizdb import QuizDB
from .topics import circuits, motion, heat, buoyancy, waves, pendulum, optics, pressure, energy

RUNNERS = {"circuits": circuits.run, "motion": motion.run, "heat": heat.run,
           "buoyancy": buoyancy.run, "waves": waves.run, "pendulum": pendulum.run,
           "optics": optics.run, "pressure": pressure.run, "energy": energy.run}
WWW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "www")
MAX_BODY = 16 * 1024   # POST bodies (quiz answers, sandbox worlds) are small JSON objects


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

    # ---------------- quiz ----------------
    def _quiz_get(self, path, q):
        one = lambda k: (q.get(k) or [None])[0]
        db = QuizDB()
        try:
            pid = one("player")
            player = db.player(pid) if pid else None
            if path == "/api/quiz":
                mods = []
                for t in TOPICS:
                    qs = [x for x in quiz.QUESTIONS if x["topic"] == t["id"]]
                    if not qs:
                        continue
                    items = []
                    for x in sorted(qs, key=lambda x: quiz.LEVELS.index(x["difficulty"])):
                        st = db.progress(player["id"], x["id"]) if player else None
                        items.append({"id": x["id"], "difficulty": x["difficulty"], "title": x["title"],
                                      "points": x["points"], "progress": st})
                    mods.append({"topic": t["id"], "title": t["title"], "icon": t["icon"], "questions": items})
                total = sum(x["points"] for x in quiz.QUESTIONS)
                return self._json({"modules": mods, "player": player, "max_score": total,
                                   "count": len(quiz.QUESTIONS)})
            if path == "/api/quiz/question":
                qd = quiz.BY_ID.get(one("id") or "")
                if not qd:
                    return _bad(self, 404, "unknown question")
                out = quiz.public(qd)
                if player:
                    st = db.progress(player["id"], qd["id"])
                    out["progress"] = st
                    if st["attempts"]:
                        out["explanation"] = qd["explanation"]
                    if st["solved"] or st["revealed"]:
                        out["solution"] = qd["solution"]
                return self._json(out)
            if path == "/api/quiz/history":
                if not player:
                    return _bad(self, 404, "unknown player")
                hist = db.history(player["id"])
                for h in hist:                            # the unit of the measured outcome
                    qd = quiz.BY_ID.get(h["question_id"])
                    h["unit"] = quiz.METRICS[qd["goal"]["metric"]]["unit"] if qd else ""
                return self._json({"player": player, "history": hist})
            if path == "/api/quiz/players":
                return self._json({"players": db.players()})
            return _bad(self, 404, "not found")
        finally:
            db.close()

    def _read_json(self):
        try:
            n = int(self.headers.get("Content-Length", ""))
        except ValueError:
            return None, "Content-Length required"
        if n < 0 or n > MAX_BODY:
            return None, "body too large"
        try:
            body = json.loads(self.rfile.read(n).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return None, "body must be JSON"
        if not isinstance(body, dict):
            return None, "body must be a JSON object"
        return body, None

    def do_POST(self):
        path = urlparse(self.path).path
        if path == "/api/sandbox/run":
            body, err = self._read_json()
            if err:
                return _bad(self, 400, err)
            topic = body.get("topic")
            if not isinstance(topic, str) or topic not in sandbox.SANDBOX:
                return _bad(self, 400, "no sandbox for that topic")
            world, err = sandbox.validate(topic, body.get("world", {}))
            if err:
                return _bad(self, 400, err)
            return self._json({"topic": topic, "world": world, **sandbox.run(topic, world)})
        if path not in ("/api/quiz/player", "/api/quiz/answer", "/api/quiz/reveal"):
            return _bad(self, 404, "not found")
        body, err = self._read_json()
        if err:
            return _bad(self, 400, err)
        db = QuizDB()
        try:
            if path == "/api/quiz/player":
                try:
                    return self._json({"player": db.create_player(body.get("name"))})
                except ValueError as e:
                    return _bad(self, 400, str(e))
            player = db.player(body.get("player"))
            if not player:
                return _bad(self, 404, "unknown player")
            qd = quiz.BY_ID.get(body.get("question") if isinstance(body.get("question"), str) else "")
            if not qd:
                return _bad(self, 404, "unknown question")
            if path == "/api/quiz/reveal":
                try:
                    db.reveal(player["id"], qd)
                except ValueError as e:
                    return _bad(self, 400, str(e))
                return self._json({"solution": qd["solution"], "explanation": qd["explanation"],
                                   "progress": db.progress(player["id"], qd["id"])})
            inputs, err = quiz.check_inputs(qd, body.get("inputs"))
            if err:
                return _bad(self, 400, err)
            graded = quiz.grade(qd, inputs)
            pts = db.record(player["id"], qd, inputs, graded)
            st = db.progress(player["id"], qd["id"])
            return self._json({
                "correct": graded["correct"], "value": graded["value"], "message": graded["message"],
                "points": pts, "score": db.score(player["id"]), "progress": st,
                "explanation": qd["explanation"],
                "solution": qd["solution"] if (st["solved"] or st["revealed"]) else None,
                "goal": quiz.public(qd)["goal"], "run": graded["result"]})
        finally:
            db.close()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/topics":
            return self._json({"topics": TOPICS})
        if parsed.path == "/api/sandbox":
            return self._json({"sandbox": sandbox.catalog_view()})
        if parsed.path.startswith("/api/quiz"):
            return self._quiz_get(parsed.path, parse_qs(parsed.query))
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
