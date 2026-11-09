"""API + static edges on a loopback server, plus determinism gates."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.server import Handler

PORT = 8641
READY = ("circuits", "motion", "heat", "buoyancy", "waves", "pendulum", "optics", "pressure", "energy")
BASE = "http://127.0.0.1:%d" % PORT


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        e.close()
        return e.code, body


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", PORT), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_topics_registry_lists_ready_and_placeholders(self):
        code, body = get("/api/topics")
        self.assertEqual(code, 200)
        topics = json.loads(body)["topics"]
        ready = {t["id"] for t in topics if t["status"] == "ready"}
        ph = [t for t in topics if t["status"] == "placeholder"]
        self.assertEqual(ready, set(READY))
        for t in ph:
            self.assertTrue(t["formulas"])

    def test_run_each_ready_topic(self):
        for tid in READY:
            code, body = get("/api/run?topic=" + tid)
            self.assertEqual(code, 200, body)
            out = json.loads(body)
            self.assertTrue(out["frames"])
            self.assertTrue(out["formula"])

    def test_run_is_deterministic(self):
        for tid in READY:
            _, a = get("/api/run?topic=" + tid)
            _, b = get("/api/run?topic=" + tid)
            self.assertEqual(a, b, tid)

    def test_frames_carry_what_the_renderer_draws(self):
        need = {"circuits": {"t", "current", "brightness", "filament_k", "lumens", "color"},
                "motion": {"t", "x", "y", "vx", "vy", "fdx", "fdy"},
                "heat": {"t", "temp_a", "temp_b", "flow", "leak_a", "leak_b", "q"},
                "buoyancy": {"t", "y", "v", "level", "h", "vsub", "fb", "fd", "fn", "zb", "p_top", "p_bot"},
                "waves": {"t", "y", "driver", "bead_y", "bead_v", "crest_x"},
                "pendulum": {"t", "theta", "omega", "x", "y", "v", "tension", "f_restore", "f_drag",
                             "ke", "pe", "swings"},
                "optics": {"t"},
                "pressure": {"t", "x1", "x2", "v1", "v2", "p1", "p2", "f_hand", "f_lift", "w_in", "w_load",
                             "w_liquid", "w_loss", "ke"},
                "energy": {"t", "x", "y", "v", "phi", "N", "friction", "ke", "ker", "pe", "heat", "land",
                           "fly", "spin"}}
        for tid, keys in need.items():
            out = json.loads(get("/api/run?topic=" + tid)[1])
            for f in out["frames"]:
                self.assertTrue(keys <= set(f), (tid, keys - set(f)))
            self.assertIsInstance(out.get("notes"), list, tid)

    def test_formula_values_match_registry_expressions(self):
        # the client matches formula values to cards by expression
        topics = {t["id"]: t for t in json.loads(get("/api/topics")[1])["topics"]}
        for tid in READY:
            exprs = {f["expr"] for f in topics[tid]["formulas"]}
            out = json.loads(get("/api/run?topic=" + tid)[1])
            for f in out["formula"]:
                self.assertIn(f["expr"], exprs, tid)

    def test_motion_supports_compare_and_heat_materials_differ(self):
        topics = {t["id"]: t for t in json.loads(get("/api/topics")[1])["topics"]}
        self.assertEqual(topics["motion"].get("compare"), "ball")
        out = json.loads(get("/api/run?topic=heat&material_a=copper&material_b=water")[1])
        self.assertEqual(out["materials"]["a"]["id"], "copper")
        self.assertEqual(out["materials"]["b"]["id"], "water")

    def test_learning_content_and_figures_served(self):
        topics = json.loads(get("/api/topics")[1])["topics"]
        for t in topics:
            if t["id"] not in READY:
                self.assertNotIn("learn", t)
                continue
            self.assertTrue(t["learn"]["formulas"], t["id"])
            for fig in t["learn"]["figures"]:
                code, body = get("/" + fig["img"])
                self.assertEqual(code, 200, fig["img"])
                self.assertTrue(body.startswith(b"\x89PNG"), fig["img"])
        for js in ("core.js", "widgets.js", "stage.js", "player.js", "scene_optics.js",
                   "scene_pressure.js", "scene_energy.js"):
            code, _ = get("/js/" + js)
            self.assertEqual(code, 200, js)
        code, body = get("/js/core.js")
        self.assertEqual(code, 200)
        self.assertIn(b"PL.route", body)

    def test_placeholder_topic_rejected(self):
        from physlab import TOPICS
        TOPICS.append({"id": "magnetism", "title": "Magnets", "status": "placeholder", "icon": "bolt",
                       "blurb": "", "formulas": [{"expr": "F = q v B", "legend": ""}]})
        try:
            self.assertEqual(get("/api/run?topic=magnetism")[0], 400)
        finally:
            TOPICS.pop()

    def test_new_topics_validate_their_params(self):
        self.assertEqual(get("/api/run?topic=buoyancy&material=unobtainium")[0], 400)
        self.assertEqual(get("/api/run?topic=waves&end=sideways")[0], 400)
        self.assertEqual(get("/api/run?topic=pendulum&length=abc")[0], 400)
        code, body = get("/api/run?topic=pendulum&amplitude=170")      # clamped: string goes slack past 90
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["params"]["amplitude"], 90.0)
        topics = {t["id"]: t for t in json.loads(get("/api/topics")[1])["topics"]}
        self.assertEqual(topics["pendulum"].get("compare"), "pendulum")

    def test_unknown_topic_rejected(self):
        code, _ = get("/api/run?topic=nope")
        self.assertEqual(code, 400)

    def test_bad_and_out_of_range_params(self):
        self.assertEqual(get("/api/run?topic=motion&v0=abc")[0], 400)
        self.assertEqual(get("/api/run?topic=motion&bogus=1")[0], 400)
        self.assertEqual(get("/api/run?topic=circuits&lamps=2.5")[0], 400)
        # clamping, not rejection
        code, body = get("/api/run?topic=motion&v0=9999")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["params"]["v0"], 50.0)

    def test_static_non_root_file_served(self):
        code, body = get("/js/ui.js")
        self.assertEqual(code, 200)
        self.assertIn(b"physlab", body)

    def test_topic_icons_served(self):
        for icon in ("battery", "ball", "flame", "water", "pendulum",
                     "eye", "press", "bolt", "wave"):
            code, body = get("/icons/icon_%s.png" % icon)
            self.assertEqual(code, 200, icon)
            self.assertTrue(body.startswith(b"\x89PNG"), icon)

    def test_sim_sprites_served(self):
        for name in ("lamp", "battery", "switch", "resistor", "block",
                     "ball", "ramp", "wire", "bob", "clamp", "oscillator", "hand",
                     "candle", "eye", "car", "crate"):
            code, body = get("/sprites/item_%s.png" % name)
            self.assertEqual(code, 200, name)
            self.assertTrue(body.startswith(b"\x89PNG"), name)

    def test_traversal_blocked(self):
        for probe in ("/../physlab/server.py", "/%2e%2e/physlab/server.py",
                      "/js/../../physlab/__init__.py"):
            self.assertEqual(get(probe)[0], 404, probe)


class TestGoldenFixtures(unittest.TestCase):
    """Regenerating fixtures must reproduce the committed goldens exactly."""

    def test_fixture_regen_byte_identical(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp = tempfile.mkdtemp()
        try:
            subprocess.run([sys.executable, os.path.join(repo, "tests", "gen_fixtures.py"), tmp],
                           check=True, cwd=tmp, capture_output=True)
            committed = os.path.join(repo, "tests", "fixtures")
            self.assertEqual(sorted(os.listdir(committed)), sorted(os.listdir(tmp)))
            for name in os.listdir(committed):
                with open(os.path.join(committed, name), "rb") as a, \
                        open(os.path.join(tmp, name), "rb") as b:
                    self.assertEqual(a.read(), b.read(), name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()


def post(path, body, port, raw=None, headers=None):
    data = raw if raw is not None else json.dumps(body).encode()
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (port, path), data=data, method="POST",
                                 headers=headers or {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read()
        e.close()
        return e.code, json.loads(body or b"{}")


class TestQuizAPI(unittest.TestCase):
    PORT = 8643

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.old = os.environ.get("PHYSLAB_DB")
        os.environ["PHYSLAB_DB"] = os.path.join(cls.dir, "quiz.sqlite")
        cls.srv = HTTPServer(("127.0.0.1", cls.PORT), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        if cls.old is None:
            os.environ.pop("PHYSLAB_DB", None)
        else:
            os.environ["PHYSLAB_DB"] = cls.old
        shutil.rmtree(cls.dir, ignore_errors=True)

    def get(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.PORT, path), timeout=30) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read()
            e.close()
            return e.code, json.loads(body or b"{}")

    def post(self, path, body, **kw):
        return post(path, body, self.PORT, **kw)

    def new_player(self, name="Ada"):
        code, body = self.post("/api/quiz/player", {"name": name})
        self.assertEqual(code, 200, body)
        return body["player"]["id"]

    def test_catalogue_without_and_with_a_player(self):
        code, body = self.get("/api/quiz")
        self.assertEqual(code, 200)
        self.assertEqual(len(body["modules"]), 9)
        self.assertEqual(body["count"], 27)
        self.assertEqual(body["max_score"], 9 * (10 + 20 + 30))
        self.assertIsNone(body["player"])
        for m in body["modules"]:
            self.assertEqual([q["difficulty"] for q in m["questions"]], ["easy", "medium", "hard"])
        pid = self.new_player()
        code, body = self.get("/api/quiz?player=" + pid)
        self.assertEqual(body["player"]["name"], "Ada")
        self.assertEqual(body["modules"][0]["questions"][0]["progress"]["attempts"], 0)

    def test_answer_flow_scores_and_history(self):
        pid = self.new_player()
        code, q = self.get("/api/quiz/question?id=motion-easy&player=" + pid)
        self.assertEqual(code, 200)
        self.assertNotIn("solution", q)
        self.assertNotIn("explanation", q)                           # not before the first try
        code, r = self.post("/api/quiz/answer", {"player": pid, "question": "motion-easy", "inputs": {"v0": 20}})
        self.assertEqual(code, 200, r)
        self.assertFalse(r["correct"])
        self.assertIsNone(r["solution"])
        self.assertTrue(r["explanation"])
        self.assertIn("frames", r["run"])                             # the browser plays this run
        self.assertEqual(r["run"]["params"]["v0"], 20.0)
        code, r = self.post("/api/quiz/answer", {"player": pid, "question": "motion-easy", "inputs": {"v0": 14}})
        self.assertTrue(r["correct"])
        self.assertEqual((r["points"], r["score"]), (8, 8))
        self.assertTrue(r["solution"])
        code, q = self.get("/api/quiz/question?id=motion-easy&player=" + pid)
        self.assertIn("solution", q)
        code, h = self.get("/api/quiz/history?player=" + pid)
        self.assertEqual([x["correct"] for x in h["history"]], [1, 0])
        self.assertEqual(h["history"][0]["unit"], "m")
        self.assertEqual(h["player"]["score"], 8)

    def test_reveal_is_gated(self):
        pid = self.new_player("Ben")
        body = {"player": pid, "question": "pendulum-easy"}
        self.assertEqual(self.post("/api/quiz/reveal", body)[0], 400)
        for length in (2.0, 0.5):
            self.post("/api/quiz/answer", dict(body, inputs={"length": length}))
        code, r = self.post("/api/quiz/reveal", body)
        self.assertEqual(code, 200, r)
        self.assertTrue(r["solution"])
        self.assertTrue(r["progress"]["revealed"])

    def test_bad_requests(self):
        pid = self.new_player("Cy")
        ok = {"player": pid, "question": "motion-easy", "inputs": {"v0": 14}}
        self.assertEqual(self.post("/api/quiz/answer", dict(ok, player="ghost"))[0], 404)
        self.assertEqual(self.post("/api/quiz/answer", dict(ok, question="nope"))[0], 404)
        self.assertEqual(self.post("/api/quiz/answer", dict(ok, question=["x"]))[0], 404)
        code, r = self.post("/api/quiz/answer", dict(ok, inputs={"v0": 14, "g": 1.6}))
        self.assertEqual(code, 400)
        self.assertIn("can't change", r["error"])
        self.assertEqual(self.post("/api/quiz/answer", dict(ok, inputs={"v0": 500}))[0], 400)
        self.assertEqual(self.post("/api/quiz/answer", None, raw=b"{not json")[0], 400)
        self.assertEqual(self.post("/api/quiz/answer", None, raw=b"[1, 2]")[0], 400)
        self.assertEqual(self.post("/api/quiz/answer", None, raw=b"x" * (20 * 1024))[0], 400)
        self.assertEqual(self.post("/api/quiz/player", {"name": "   "})[0], 400)
        self.assertEqual(self.post("/api/nope", {})[0], 404)
        self.assertEqual(self.get("/api/quiz/history?player=ghost")[0], 404)
        self.assertEqual(self.get("/api/quiz/question?id=nope")[0], 404)
        # a request without Content-Length is refused
        conn = __import__("http.client").client.HTTPConnection("127.0.0.1", self.PORT, timeout=10)
        conn.putrequest("POST", "/api/quiz/player")
        conn.endheaders()
        self.assertEqual(conn.getresponse().status, 400)
        conn.close()

    def test_recent_players(self):
        self.new_player("Dee")
        code, body = self.get("/api/quiz/players")
        self.assertEqual(code, 200)
        self.assertIn("Dee", [p["name"] for p in body["players"]])


class TestSandboxAPI(unittest.TestCase):
    PORT = 8644

    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", cls.PORT), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def post(self, body, raw=None):
        return post("/api/sandbox/run", body, self.PORT, raw=raw)

    def test_catalog(self):
        with urllib.request.urlopen("http://127.0.0.1:%d/api/sandbox" % self.PORT, timeout=10) as r:
            body = json.loads(r.read())
        self.assertEqual(set(body["sandbox"]), set(READY))
        motion = body["sandbox"]["motion"]
        balls = [f for f in motion["fields"] if f["id"] == "balls"][0]
        self.assertIn("tennis", [it["id"] for it in balls["items"]])
        self.assertTrue(motion["presets"])

    def test_run_every_default_world(self):
        for tid in READY:
            code, body = self.post({"topic": tid, "world": {}})
            self.assertEqual(code, 200, body)
            self.assertTrue(body["runs"][0]["result"]["frames"])
            self.assertEqual(body["topic"], tid)

    def test_the_clean_world_comes_back(self):
        code, body = self.post({"topic": "motion", "world": {"balls": ["tennis", "soccer"], "v0": 15}})
        self.assertEqual(code, 200)
        self.assertEqual(body["world"]["balls"], ["tennis", "soccer"])
        self.assertEqual(body["world"]["planet"], "earth")                    # defaults filled in
        self.assertEqual([r["label"] for r in body["runs"]], ["Tennis ball", "Football"])

    def test_refusals(self):
        for payload, word in (({"topic": "alchemy", "world": {}}, "no sandbox"),
                              ({"topic": ["motion"], "world": {}}, "no sandbox"),
                              ({"topic": "motion", "world": {"planet": "pluto"}}, "pluto"),
                              ({"topic": "motion", "world": {"v0": 1e9}}, "between"),
                              ({"topic": "motion", "world": "earth"}, "object"),
                              ({"topic": "energy", "world": {"track": [8, 5.5, 3, 0.6, 0, 0, 0]}}, "ground"),
                              ({"topic": "heat", "world": {"thing_a": "tea", "source_a": "oven"}}, "oven"),
                              ({"topic": "circuits", "world": {"parts": [{"part": "wire", "a": [0, 0],
                                                                          "b": [2, 0]}]}}, "neighbouring")):
            code, body = self.post(payload)
            self.assertEqual(code, 400, payload)
            self.assertIn(word, body["error"])
        self.assertEqual(self.post(None, raw=b"{oops")[0], 400)
        self.assertEqual(self.post(None, raw=b"x" * (20 * 1024))[0], 400)
