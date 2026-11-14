"""The game's HTTP API on a loopback server with a throw-away database:
catalog, hall views (practice and player variants), runs (test / machine),
strict validation, locking, stars, points, hints and the Golden Run.

TestGameAPI runs with the classroom locks ON (PHYSLAB_GAME_LOCKS=on: halls
and stations open one after another); TestTestingModeAPI checks the
default, where every hall and station is open for everyone."""

import json
import os
import shutil
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.server import Handler  # noqa: E402
from physlab.game import bounce_factory as BF  # noqa: E402
from physlab.game import common as C  # noqa: E402
from physlab.game import foundry as FD  # noqa: E402
from physlab.game import mill as ML  # noqa: E402

SOL = BF.table()["stations"]
SOL2 = FD.table()["stations"]
SOL3 = ML.table()["stations"]


class TestGameAPI(unittest.TestCase):
    PORT = 8645
    LOCKS = "on"

    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.mkdtemp()
        cls.old = os.environ.get("PHYSLAB_DB")
        cls.old_locks = os.environ.get("PHYSLAB_GAME_LOCKS")
        os.environ["PHYSLAB_DB"] = os.path.join(cls.dir, "game.sqlite")
        if cls.LOCKS is None:
            os.environ.pop("PHYSLAB_GAME_LOCKS", None)
        else:
            os.environ["PHYSLAB_GAME_LOCKS"] = cls.LOCKS
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
        if cls.old_locks is None:
            os.environ.pop("PHYSLAB_GAME_LOCKS", None)
        else:
            os.environ["PHYSLAB_GAME_LOCKS"] = cls.old_locks
        shutil.rmtree(cls.dir, ignore_errors=True)

    def get(self, path):
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d%s" % (self.PORT, path), timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read()
            e.close()
            return e.code, json.loads(body or b"{}")

    def post(self, path, body, raw=None):
        data = raw if raw is not None else json.dumps(body).encode()
        req = urllib.request.Request("http://127.0.0.1:%d%s" % (self.PORT, path), data=data, method="POST",
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            body = e.read()
            e.close()
            return e.code, json.loads(body or b"{}")

    def new_player(self, name):
        code, body = self.post("/api/quiz/player", {"name": name})
        self.assertEqual(code, 200, body)
        return body["player"]["id"]

    def station_run(self, sid, knobs, player=None, **extra):
        body = dict({"hall": "bounce", "station": sid, "mode": "test", "knobs": {sid: knobs}}, **extra)
        if player:
            body["player"] = player
        return self.post("/api/game/run", body)

    # ---------------- reads ----------------
    def test_catalog(self):
        code, body = self.get("/api/game")
        self.assertEqual(code, 200)
        self.assertEqual([h["id"] for h in body["halls"]], ["bounce", "foundry", "mill"])
        self.assertEqual(body["halls"][0]["status"], "ready")
        self.assertEqual([s["id"] for s in body["halls"][0]["stations"]], ["1.1", "1.2", "1.3", "1.4"])
        self.assertEqual(body["halls"][1]["status"], "ready")
        self.assertEqual([s["id"] for s in body["halls"][1]["stations"]], ["2.1", "2.2", "2.3", "2.4"])
        self.assertEqual(body["halls"][2]["status"], "ready")
        self.assertEqual([s["id"] for s in body["halls"][2]["stations"]], ["3.1", "3.2", "3.3", "3.4"])
        self.assertEqual(body["max_stars"], 36)
        self.assertTrue(body["locks"])
        self.assertIsNone(body["player"])
        self.assertEqual(self.get("/api/game?player=nobody")[0], 404)

    def test_hall_practice_and_variants(self):
        code, body = self.get("/api/game/hall?id=bounce")
        self.assertEqual(code, 200)
        self.assertTrue(body["practice"])
        self.assertEqual(body["variant"], C.NOMINAL)
        st = {s["id"]: s for s in body["stations"]}
        self.assertEqual(st["1.1"]["fact_values"]["flap"], 1.5)
        self.assertTrue(all(s["unlocked"] for s in body["stations"]))
        self.assertIn("2.30", st["1.1"]["mastery"])                          # this variant's threshold, in words
        code, body = self.get("/api/game/hall?id=bounce&v=0")
        self.assertEqual({s["id"]: s for s in body["stations"]}["1.1"]["fact_values"]["flap"], 1.4)
        self.assertEqual(self.get("/api/game/hall?id=bounce&v=9")[0], 400)
        self.assertEqual(self.get("/api/game/hall?id=bounce&v=x")[0], 400)
        self.assertEqual(self.get("/api/game/hall?id=nowhere")[0], 404)
        blob = json.dumps(self.get("/api/game/hall?id=bounce")[1])
        for secret in ('"solution', '"window"', '"thresholds"', '"wrong"', '"mastery_solution'):
            self.assertNotIn(secret, blob)

    # ---------------- practice runs ----------------
    def test_practice_runs_and_machine(self):
        code, body = self.station_run("1.1", SOL["1.1"]["variants"][2]["solution"], prediction=1.9)
        self.assertEqual(code, 200, body)
        r = body["stations"][0]
        self.assertTrue(body["ok"] and r["ok"] and body["practice"])
        self.assertTrue(r["insight"])
        self.assertEqual(r["new_stars"], [])                                   # practice records nothing
        self.assertTrue(body["frames"] and r["lab"] and r["formula"])
        code, body = self.station_run("1.1", {"hatch": 1.2}, v=0)
        self.assertFalse(body["ok"])
        self.assertIn("not high enough", body["stations"][0]["reason"])
        self.assertEqual(body["stations"][0]["facts"]["flap"], 1.4)
        knobs = {sid: SOL[sid]["variants"][2]["solution"] for sid in SOL}
        code, body = self.post("/api/game/run", {"hall": "bounce", "mode": "machine", "knobs": knobs})
        self.assertEqual(code, 200, body)
        self.assertTrue(body["ok"])
        self.assertEqual([s["id"] for s in body["stations"]], ["1.1", "1.2", "1.3", "1.4"])

    def test_validation(self):
        ok = {"hall": "bounce", "station": "1.1", "mode": "test", "knobs": {"1.1": {"hatch": 2.0}}}
        for bad, code, word in (
                (dict(ok, extra=1), 400, "not part of a run"),
                (dict(ok, hall="nowhere"), 404, "hall"),
                (dict(ok, hall="foundry"), 404, "station"),                    # 1.1 is not a Foundry station
                (dict(ok, hall="mill"), 404, "station"),
                (dict(ok, mode="sprint"), 400, "mode"),
                (dict(ok, station="2.1"), 404, "station"),
                (dict(ok, knobs={"1.2": {"bags": 3}}), 400, "not a station"),
                (dict(ok, knobs={"1.1": {"hatch": 12}}), 400, "between"),
                (dict(ok, knobs={"1.1": {"pad": "lava"}}), 400, "not a choice"),
                (dict(ok, knobs={"1.1": {"hatch": "tall"}}), 400, "number"),
                (dict(ok, knobs=[1]), 400, "knobs"),
                (dict(ok, prediction="high"), 400, "number"),
                (dict(ok, station="1.2", knobs={"1.2": {"bags": 11}}, prediction=1.0), 400, "yes or no"),
                (dict(ok, mode="machine", prediction=1.0, knobs={}), 400, "single-station"),
                (dict(ok, player="ghost"), 404, "player")):
            c, body = self.post("/api/game/run", bad)
            self.assertEqual(c, code, (bad, body))
            self.assertIn(word, body["error"], (bad, body))
        self.assertEqual(self.post("/api/game/run", None, raw=b"not json")[0], 400)
        self.assertEqual(self.post("/api/game/run", None, raw=b"x" * 20000)[0], 400)

    # ---------------- a player ----------------
    def test_player_stars_points_hints_and_golden_run(self):
        pid = self.new_player("Marie")
        code, hall = self.get("/api/game/hall?id=bounce&player=" + pid)
        self.assertFalse(hall["practice"])
        steps = C.variant_steps(BF.HALL, pid)
        st = {s["id"]: s for s in hall["stations"]}
        for sid in SOL:                                                         # the card shows THIS player's facts
            self.assertEqual(st[sid]["fact_values"], C.facts_for(BF.BY_ID[sid], steps[sid]))
        self.assertEqual([s["unlocked"] for s in hall["stations"]], [True, False, False, False])
        code, body = self.station_run("1.2", {"bags": 11}, player=pid)
        self.assertEqual(code, 403)
        self.assertIn("locked", body["error"])
        self.assertEqual(self.station_run("1.1", {}, player=pid, v=1)[0], 400)   # no choosing your own variant

        # 1.1: a miss with a good prediction, then the saved solution for this player's variant
        sol = SOL["1.1"]["variants"][steps["1.1"]]
        code, body = self.station_run("1.1", {"hatch": 1.0, "pad": "steel_plate"}, player=pid, prediction=0.7)
        r = body["stations"][0]
        self.assertFalse(r["ok"])
        self.assertTrue(r["insight"] and r["prediction_counted"])             # predicting a miss counts too
        self.assertEqual(self.post("/api/game/hint", {"player": pid, "station": "1.1", "tier": 3})[0], 403)
        code, body = self.station_run("1.1", sol["solution"], player=pid, prediction=5.0)
        r = body["stations"][0]
        self.assertTrue(r["ok"])
        self.assertEqual(r["new_stars"], ["works", "efficient"])               # 2 runs <= par 2
        self.assertFalse(r["prediction_counted"])                              # only the first run may predict
        self.assertEqual(body["score"], 2 * C.STAR_POINTS + C.INSIGHT_POINTS)
        code, body = self.station_run("1.1", sol["mastery_solution"], player=pid)
        self.assertEqual(body["stations"][0]["new_stars"], ["mastery"])
        code, body = self.station_run("1.1", sol["solution"], player=pid)
        self.assertEqual(body["stations"][0]["new_stars"], [])                 # stars are earned once

        # 1.2: two misses open the Blueprint; the Blueprint costs efficiency and mastery
        for _ in range(2):
            self.station_run("1.2", {"bags": 0}, player=pid)
        code, h = self.post("/api/game/hint", {"player": pid, "station": "1.2", "tier": 3})
        self.assertEqual(code, 200, h)
        sol2 = SOL["1.2"]["variants"][steps["1.2"]]
        self.assertIn(str(sol2["solution"]["bags"]), h["text"])
        self.assertEqual(h["progress"]["hints"], [3])
        code, body = self.station_run("1.2", sol2["mastery_solution"], player=pid)
        self.assertTrue(body["stations"][0]["ok"] and body["stations"][0]["mastery"])
        self.assertEqual(body["stations"][0]["new_stars"], ["works"])

        # 1.3 and 1.4 with the formula hint: efficiency is gone, mastery is still possible
        for sid in ("1.3", "1.4"):
            self.post("/api/game/hint", {"player": pid, "station": sid, "tier": 2})
            v = SOL[sid]["variants"][steps[sid]]
            code, body = self.station_run(sid, v["mastery_solution"], player=pid)
            self.assertEqual(body["stations"][0]["new_stars"], ["works", "mastery"], sid)

        # the whole machine, A -> B: the Golden Run, once
        knobs = {sid: SOL[sid]["variants"][steps[sid]]["solution"] for sid in SOL}
        code, body = self.post("/api/game/run", {"player": pid, "hall": "bounce", "mode": "machine", "knobs": knobs})
        self.assertTrue(body["ok"], body["stations"][-1]["reason"])
        self.assertTrue(body["golden_new"])
        code, again = self.post("/api/game/run", {"player": pid, "hall": "bounce", "mode": "machine", "knobs": knobs})
        self.assertFalse(again["golden_new"])
        # the score is derived from the records: 3 + 1 + 2 + 2 stars, 1 insight, 1 golden run
        code, cat = self.get("/api/game?player=" + pid)
        self.assertEqual(cat["score"], 8 * C.STAR_POINTS + C.INSIGHT_POINTS + C.GOLDEN_POINTS)
        self.assertTrue(cat["halls"][0]["golden"])
        self.assertEqual(sorted(cat["halls"][0]["stations"][0]["stars"]), ["efficient", "mastery", "works"])

    def test_scores_bests_and_the_leaderboard(self):
        a, b = self.new_player("Ana"), self.new_player("Ben")
        sa, sb = C.variant_steps(BF.HALL, a)["1.1"], C.variant_steps(BF.HALL, b)["1.1"]
        code, r1 = self.station_run("1.1", SOL["1.1"]["variants"][sa]["solution"], player=a)
        e = r1["stations"][0]
        self.assertTrue(e["ok"] and 100 <= e["score"] < 1000 and e["new_best"])
        self.assertEqual(e["best"], e["score"])
        above = sum(1 for x in e["leaderboard"] if x["best"] > e["score"])   # other tests share this database
        self.assertEqual(e["rank"]["rank"], above + 1)
        self.assertTrue(e["score_parts"])
        code, r2 = self.station_run("1.1", SOL["1.1"]["variants"][sa]["score_solution"], player=a)
        self.assertEqual((r2["stations"][0]["score"], r2["stations"][0]["new_best"]), (1000, True))
        code, r3 = self.station_run("1.1", SOL["1.1"]["variants"][sa]["solution"], player=a)
        self.assertFalse(r3["stations"][0]["new_best"])                       # a worse run keeps the best
        self.assertEqual(r3["stations"][0]["best"], 1000)
        code, rb = self.station_run("1.1", SOL["1.1"]["variants"][sb]["solution"], player=b)
        eb = rb["stations"][0]
        self.assertEqual(eb["rank"]["rank"], 1 + sum(1 for x in eb["leaderboard"] if x["best"] > eb["score"]))
        self.assertEqual(r2["stations"][0]["rank"]["rank"], 1)                # nobody beats 1000
        names = [x["name"] for x in eb["leaderboard"]]
        self.assertLess(names.index("Ana"), names.index("Ben"))
        code, miss = self.station_run("1.1", {"hatch": 1.0}, player=b)
        self.assertEqual(miss["stations"][0]["score"], 0)
        code, hall = self.get("/api/game/hall?id=bounce&player=" + a)
        st = {x["id"]: x for x in hall["stations"]}
        self.assertEqual(st["1.1"]["progress"]["best"], 1000)
        self.assertTrue(st["1.1"]["leaderboard"] and st["1.1"]["score_rule"])
        self.assertEqual(st["1.1"]["variant_step"], sa)
        code, cat = self.get("/api/game?player=" + a)
        self.assertEqual(cat["halls"][0]["score"], 1000)
        self.assertEqual(cat["halls"][0]["max_score"], 4000)
        code, pr = self.station_run("1.1", SOL["1.1"]["variants"][2]["solution"])  # practice: a score, nothing kept
        self.assertTrue(pr["stations"][0]["score"] > 0 and "best" not in pr["stations"][0])

    def test_the_next_hall_opens_when_this_one_is_cleared(self):
        pid = self.new_player("Cleo")
        code, cat = self.get("/api/game?player=" + pid)
        foundry = next(h for h in cat["halls"] if h["id"] == "foundry")
        self.assertFalse(foundry["unlocked"])
        self.assertIn("Bounce Factory", foundry["requires"])
        steps = C.variant_steps(BF.HALL, pid)
        cleared = []
        for sid in ("1.1", "1.2", "1.3", "1.4"):
            code, body = self.station_run(sid, SOL[sid]["variants"][steps[sid]]["solution"], player=pid)
            self.assertTrue(body["ok"], sid)
            cleared.append(body["hall_cleared_new"])
        self.assertEqual(cleared, [False, False, False, True])               # exactly when the last station works
        self.assertEqual(body["next_hall"]["id"], "foundry")
        self.assertTrue(body["next_hall"]["unlocked"])
        code, again = self.station_run("1.4", SOL["1.4"]["variants"][steps["1.4"]]["solution"], player=pid)
        self.assertFalse(again["hall_cleared_new"])                           # announced once
        code, cat = self.get("/api/game?player=" + pid)
        halls = {h["id"]: h for h in cat["halls"]}
        self.assertTrue(halls["bounce"]["cleared"] and halls["foundry"]["unlocked"])
        self.assertFalse(halls["mill"]["unlocked"])
        code, hall = self.get("/api/game/hall?id=bounce&player=" + pid)
        self.assertTrue(hall["cleared"])
        code, body = self.get("/api/game/hall?id=foundry&player=" + pid)
        self.assertEqual(code, 200, body)                                      # the Foundry is open now
        self.assertFalse(body["practice"])
        self.assertEqual([s["unlocked"] for s in body["stations"]], [True, False, False, False])
        self.assertEqual(body["next_hall"], {"id": "mill", "title": "Millbrook Mill", "status": "ready",
                                             "unlocked": False})
        code, body = self.get("/api/game/hall?id=mill&player=" + pid)
        self.assertEqual(code, 403)                                            # the Mill waits for the Foundry
        self.assertIn("Foundry", body["error"])

    def test_the_foundry_is_locked_until_the_bounce_factory_is_cleared(self):
        pid = self.new_player("Faraday")
        code, body = self.get("/api/game/hall?id=foundry&player=" + pid)
        self.assertEqual(code, 403)
        self.assertIn("Bounce Factory", body["error"])
        code, body = self.post("/api/game/run", {"player": pid, "hall": "foundry", "station": "2.1", "mode": "test",
                                                 "knobs": {"2.1": {"target": "ring", "water": 0.4}}})
        self.assertEqual(code, 403)
        code, body = self.post("/api/game/hint", {"player": pid, "station": "2.1", "tier": 1})
        self.assertEqual(code, 200)                                             # hints are free to read
        # practice mode: the Foundry can always be tried
        code, body = self.get("/api/game/hall?id=foundry")
        self.assertEqual(code, 200)
        self.assertTrue(body["practice"] and all(s["unlocked"] for s in body["stations"]))
        self.assertEqual(body["hall"]["layout"]["ball"]["color"], FD.BALL["color"])

    def test_the_foundry_for_a_player(self):
        pid = self.new_player("Curie")
        steps = C.variant_steps(BF.HALL, pid)
        for sid in ("1.1", "1.2", "1.3", "1.4"):                                # clear Hall 1 first
            self.assertTrue(self.station_run(sid, SOL[sid]["variants"][steps[sid]]["solution"], player=pid)[1]["ok"])
        steps2 = C.variant_steps(FD.HALL, pid)
        code, hall = self.get("/api/game/hall?id=foundry&player=" + pid)
        st = {s["id"]: s for s in hall["stations"]}
        for sid in SOL2:                                                        # THIS player's numbers
            self.assertEqual(st[sid]["fact_values"], C.facts_for(FD.BY_ID[sid], steps2[sid]))
            self.assertEqual(st[sid]["variant_step"], steps2[sid])
        self.assertIn("%.2f" % SOL2["2.1"]["variants"][steps2["2.1"]]["thresholds"]["thrifty"], st["2.1"]["mastery"])

        def foundry_run(sid, knobs, **extra):
            return self.post("/api/game/run", dict({"player": pid, "hall": "foundry", "station": sid, "mode": "test",
                                                    "knobs": {sid: knobs}}, **extra))
        code, body = foundry_run("2.2", {"battery": "lantern"})
        self.assertEqual(code, 403)                                             # one station after the other
        code, body = foundry_run("2.1", {"target": "ball", "water": 0.5})
        self.assertFalse(body["ok"])
        self.assertIn("BALL", body["stations"][0]["reason"])
        self.assertEqual(body["timelapse"][0][1], FD.SHIFT)                     # the whole shift, played fast
        cleared = []
        for sid in ("2.1", "2.2", "2.3", "2.4"):
            v = SOL2[sid]["variants"][steps2[sid]]
            code, body = foundry_run(sid, v["solution"])
            self.assertEqual(code, 200, body)
            r = body["stations"][0]
            self.assertTrue(r["ok"], (sid, r["reason"]))
            self.assertEqual(r["metric"], v["metric"])
            self.assertEqual(r["facts"], v["facts"])
            self.assertIn("works", r["new_stars"])
            self.assertTrue(r["lab"] and r["formula"] and r["score_parts"])
            cleared.append(body["hall_cleared_new"])
            if sid == "2.1":
                (z0, z1, sp), = body["timelapse"]
                self.assertTrue(z0 == 0.0 and z1 > 5 and sp > 1)
        self.assertEqual(cleared, [False, False, False, True])
        self.assertEqual(body["next_hall"]["id"], "mill")
        code, best = foundry_run("2.3", SOL2["2.3"]["variants"][steps2["2.3"]]["score_solution"])
        self.assertEqual((best["stations"][0]["score"], best["stations"][0]["new_best"]), (1000, True))
        knobs = {sid: SOL2[sid]["variants"][steps2[sid]]["solution"] for sid in SOL2}
        code, body = self.post("/api/game/run", {"player": pid, "hall": "foundry", "mode": "machine", "knobs": knobs})
        self.assertTrue(body["ok"], body["stations"][-1]["reason"])
        self.assertTrue(body["golden_new"])
        self.assertEqual(len(body["timelapse"]), 1)
        code, cat = self.get("/api/game?player=" + pid)
        fh = next(h for h in cat["halls"] if h["id"] == "foundry")
        self.assertTrue(fh["cleared"] and fh["golden"])
        self.assertEqual(fh["max_score"], 4000)

    def test_foundry_practice_runs_and_hints(self):
        for sid in SOL2:
            v = SOL2[sid]["variants"][0]
            code, body = self.post("/api/game/run", {"hall": "foundry", "station": sid, "mode": "test", "v": 0,
                                                     "knobs": {sid: v["solution"]}})
            self.assertEqual(code, 200, body)
            self.assertTrue(body["ok"] and body["practice"], sid)
            self.assertEqual(body["stations"][0]["facts"], v["facts"])
        code, h = self.post("/api/game/hint", {"station": "2.4", "tier": 2, "v": 4})
        self.assertIn("%g" % C.facts_for(FD.BY_ID["2.4"], 4)["ladle"], h["text"])
        code, body = self.post("/api/game/run", {"hall": "foundry", "station": "2.3", "mode": "test",
                                                 "knobs": {"2.3": {"d2": 12}}})
        self.assertEqual(code, 400)
        self.assertIn("between", body["error"])
        code, body = self.post("/api/game/run", {"hall": "foundry", "station": "2.2", "mode": "test",
                                                 "knobs": {"2.2": {"battery": "potato"}}})
        self.assertEqual(code, 400)
        code, body = self.post("/api/game/run", {"hall": "foundry", "station": "2.2", "mode": "test", "prediction": 0.42,
                                                 "knobs": {"2.2": {"battery": "lantern", "R": 6.0}}})
        self.assertTrue(body["stations"][0]["insight"])                         # called the current

    def test_a_locked_hall_is_refused(self):
        from physlab.game import service
        fake = {"id": "prep", "title": "Prep Hall", "ball": "clay", "status": "ready", "blurb": "",
                "stations": [{"id": "0.1"}]}
        old = service.ALL_HALLS
        service.ALL_HALLS = [fake] + old
        try:
            pid = self.new_player("Dee")
            with self.assertRaises(service.GameError) as cm:
                service.hall_view("bounce", pid)
            self.assertEqual(cm.exception.code, 403)
            self.assertIn("Prep Hall", str(cm.exception))
            with self.assertRaises(service.GameError):
                service.run({"player": pid, "hall": "bounce", "station": "1.1", "mode": "test", "knobs": {}})
            self.assertTrue(service.hall_view("bounce", None)["practice"])    # practice mode: everything is open
        finally:
            service.ALL_HALLS = old

    def test_hints_in_practice(self):
        code, h = self.post("/api/game/hint", {"station": "1.4", "tier": 2, "v": 0})
        self.assertEqual(code, 200)
        self.assertIn("2.4", h["text"])                                        # this variant's box distance
        self.assertEqual(self.post("/api/game/hint", {"station": "1.4", "tier": 3})[0], 403)
        self.assertEqual(self.post("/api/game/hint", {"station": "1.4", "tier": 4})[0], 400)
        self.assertEqual(self.post("/api/game/hint", {"station": "9.9", "tier": 1})[0], 404)


class TestTestingModeAPI(unittest.TestCase):
    """The default (PHYSLAB_GAME_LOCKS unset): every hall and every station is open for everyone, so a tester
    can jump straight into Millbrook Mill."""
    PORT = 8646
    LOCKS = None
    setUpClass = classmethod(TestGameAPI.setUpClass.__func__)
    tearDownClass = classmethod(TestGameAPI.tearDownClass.__func__)
    get, post, new_player = TestGameAPI.get, TestGameAPI.post, TestGameAPI.new_player

    def test_every_hall_is_open(self):
        code, body = self.get("/api/game")
        self.assertFalse(body["locks"])
        self.assertTrue(all(h["unlocked"] for h in body["halls"]))
        pid = self.new_player("Tess")
        code, body = self.get("/api/game?player=" + pid)
        self.assertTrue(all(h["unlocked"] and not h["cleared"] for h in body["halls"]))
        code, hall = self.get("/api/game/hall?id=mill&player=" + pid)
        self.assertEqual(code, 200, hall)
        self.assertFalse(hall["practice"] or hall["locks"])
        self.assertEqual([s["unlocked"] for s in hall["stations"]], [True] * 4)       # the stations too
        self.assertIsNone(hall["next_hall"])                                          # the last hall

    def test_a_new_player_can_run_the_last_station_of_the_last_hall(self):
        pid = self.new_player("Jump")
        step = C.variant_steps(ML.HALL, pid)["3.4"]
        v = SOL3["3.4"]["variants"][step]
        code, body = self.post("/api/game/run", {"player": pid, "hall": "mill", "station": "3.4", "mode": "test",
                                                 "knobs": {"3.4": v["solution"]}})
        self.assertEqual(code, 200, body)
        r = body["stations"][0]
        self.assertTrue(r["ok"], r["reason"])
        self.assertEqual(r["metric"], v["metric"])
        self.assertIn("works", r["new_stars"])
        self.assertFalse(body["hall_cleared_new"])
        self.assertIsNone(body["next_hall"])

    def test_clearing_the_last_hall(self):
        pid = self.new_player("Mira")
        steps = C.variant_steps(ML.HALL, pid)
        cleared = []
        for sid in ("3.1", "3.2", "3.3", "3.4"):
            code, body = self.post("/api/game/run", {"player": pid, "hall": "mill", "station": sid, "mode": "test",
                                                     "knobs": {sid: SOL3[sid]["variants"][steps[sid]]["solution"]}})
            self.assertTrue(body["ok"], (sid, body["stations"][0]["reason"]))
            cleared.append(body["hall_cleared_new"])
        self.assertEqual(cleared, [False, False, False, True])
        self.assertIsNone(body["next_hall"])
        knobs = {sid: SOL3[sid]["variants"][steps[sid]]["solution"] for sid in SOL3}
        code, body = self.post("/api/game/run", {"player": pid, "hall": "mill", "mode": "machine", "knobs": knobs})
        self.assertTrue(body["ok"], body["stations"][-1]["reason"])
        self.assertTrue(body["golden_new"])
        code, cat = self.get("/api/game?player=" + pid)
        mill = next(h for h in cat["halls"] if h["id"] == "mill")
        self.assertTrue(mill["cleared"] and mill["golden"])

    def test_mill_practice_runs_validation_and_hints(self):
        for sid in SOL3:
            for step in (0, 4):
                v = SOL3[sid]["variants"][step]
                code, body = self.post("/api/game/run", {"hall": "mill", "station": sid, "mode": "test", "v": step,
                                                         "knobs": {sid: v["solution"]}})
                self.assertEqual(code, 200, body)
                self.assertTrue(body["ok"] and body["practice"], (sid, step))
                self.assertEqual(body["stations"][0]["facts"], v["facts"])
        for knobs, word in (({"3.1": {"item": "pebble"}}, "not a choice"), ({"3.1": {"count": 41}}, "between"),
                            ({"3.1": {"count": 2.5}}, "whole number"), ({"3.2": {"wind": 25}}, "between"),
                            ({"3.3": {"d_o": 2}}, "between"), ({"3.4": {"water": -1}}, "between"),
                            ({"3.4": {"hook": "far"}}, "number")):
            sid = list(knobs)[0]
            code, body = self.post("/api/game/run", {"hall": "mill", "station": sid, "mode": "test", "knobs": knobs})
            self.assertEqual(code, 400, knobs)
            self.assertIn(word, body["error"], knobs)
        code, h = self.post("/api/game/hint", {"station": "3.3", "tier": 2, "v": 0})
        self.assertIn("95", h["text"])                                                # this variant's bench
        code, hall = self.get("/api/game/hall?id=mill&v=4")
        st = {s["id"]: s for s in hall["stations"]}
        self.assertEqual(st["3.4"]["fact_values"]["arm"], 1.1)
        self.assertIn(str(SOL3["3.1"]["variants"][4]["thresholds"]["fewest"]), st["3.1"]["mastery"])
        blob = json.dumps(hall)
        for secret in ('"solution', '"window"', '"thresholds"', '"wrong"', '"mastery_solution'):
            self.assertNotIn(secret, blob)


if __name__ == "__main__":
    unittest.main()


class TestOldDatabase(unittest.TestCase):
    """A database made before scores existed gets the column, and its
    working runs get their scores back (runs are deterministic and the
    variant comes from the player id, so the score is recomputed exactly)."""

    def test_migration_and_backfill(self):
        import sqlite3
        from physlab.quizdb import QuizDB
        from physlab.game import service
        tmp = tempfile.mkdtemp()
        old_env = os.environ.get("PHYSLAB_DB")
        path = os.path.join(tmp, "old.sqlite")
        os.environ["PHYSLAB_DB"] = path
        try:
            q = QuizDB(path)
            pid = q.create_player("Old-timer")["id"]
            q.close()
            con = sqlite3.connect(path)
            con.executescript("""CREATE TABLE game_runs (id INTEGER PRIMARY KEY AUTOINCREMENT, player_id TEXT NOT NULL,
                hall_id TEXT NOT NULL, station_id TEXT NOT NULL, mode TEXT NOT NULL, knobs TEXT NOT NULL,
                prediction TEXT, ok INTEGER NOT NULL, metric REAL, mastery INTEGER NOT NULL, insight INTEGER NOT NULL,
                created REAL NOT NULL);""")
            step = C.variant_steps(BF.HALL, pid)["1.3"]
            good = SOL["1.3"]["variants"][step]["score_solution"]
            for knobs, ok in ((good, 1), ({"hump": 0.3}, 0)):
                con.execute("INSERT INTO game_runs (player_id, hall_id, station_id, mode, knobs, ok, mastery, insight, "
                            "created) VALUES (?, 'bounce', '1.3', 'test', ?, ?, 0, 0, 1.0)", (pid, json.dumps(knobs), ok))
            con.commit()
            con.close()
            cat = service.catalog(pid)
            st = next(s for s in cat["halls"][0]["stations"] if s["id"] == "1.3")
            self.assertEqual(st["best"], 1000)
            self.assertEqual(sorted(r[0] for r in sqlite3.connect(path).execute("SELECT score FROM game_runs")),
                             [0, 1000])
        finally:
            if old_env is None:
                os.environ.pop("PHYSLAB_DB", None)
            else:
                os.environ["PHYSLAB_DB"] = old_env
            shutil.rmtree(tmp, ignore_errors=True)
