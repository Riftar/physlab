"""The Machine Works, Hall 1 (the Bounce Factory): every station, every knob.

What is checked - the knob/adjusted-object test plan of
docs/game/IMPLEMENTATION-hall1.md:

  * the station table is complete and sane (knobs, facts, variants, hints)
  * knob validation: unknown / wrong type / NaN / out of range / not a
    choice are refused; numbers are snapped to the slider grid
  * EACH KNOB DOES WHAT IT SAYS: moving it changes the outcome the right
    way (monotonic where the physics is monotonic)
  * the defaults are not already an answer; the reference answers pass,
    the common mistakes fail with the right explanation
  * the SAVED correct settings (physlab/game/data/bounce_factory.json) work
    for every variant, the mastery settings earn mastery, and the file is
    what tools/make_game_solutions.py produces today
  * every lab deep link is a valid set-up of its experiment and the lab
    reproduces the station's result
  * runs are deterministic; the whole machine runs A -> B; the star rules
"""

import json
import math
import os
import subprocess
import sys
import unittest
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab import spec, sandbox  # noqa: E402
from physlab.game import bounce_factory as BF  # noqa: E402
from physlab.game import common as C  # noqa: E402
from physlab.server import validate, RUNNERS  # noqa: E402
from physlab.topics import tracer  # noqa: E402

NOM = C.NOMINAL
ST = BF.BY_ID


def run(sid, step=NOM, **knobs):
    st = ST[sid]
    k, err = C.validate_knobs(st, knobs)
    assert err is None, err
    return BF.run_station(st, k, step)


def lab_params(route):
    """'#/topic?a=1&b=2' -> (topic, {a: ['1'], ...})"""
    u = urlparse(route[1:])
    return u.path.strip("/"), parse_qs(u.query)


class TestStationTable(unittest.TestCase):
    def test_four_stations_in_order_with_everything(self):
        self.assertEqual([s["id"] for s in BF.STATIONS], ["1.1", "1.2", "1.3", "1.4"])
        for st in BF.STATIONS:
            for key in ("title", "intro", "goal", "hook", "knobs", "facts", "predict", "mastery", "hints", "par",
                        "formulas", "solutions", "wrong", "mastery_solutions", "learn", "run"):
                self.assertIn(key, st, (st["id"], key))
            self.assertGreaterEqual(st["par"], 2)
            self.assertEqual(len(st["hints"]), 2)                       # tier 3 is the Blueprint from the data file
            self.assertEqual(sum(1 for f in st["facts"] if "vary" in f), 1, st["id"])
            self.assertIn(st["predict"]["kind"], ("number", "boolean"))

    def test_knob_specs_are_sane(self):
        for st in BF.STATIONS:
            ids = [k["id"] for k in st["knobs"]]
            self.assertEqual(len(ids), len(set(ids)))
            for k in st["knobs"]:
                if k["kind"] == "choice":
                    cids = [c["id"] for c in k["choices"]]
                    self.assertEqual(len(cids), len(set(cids)))
                    self.assertIn(k["default"], cids)
                    for c in k["choices"]:
                        self.assertTrue(c["label"] and c.get("desc"), c)
                else:
                    self.assertLess(k["min"], k["max"])
                    self.assertTrue(k["min"] <= k["default"] <= k["max"], k)
                    self.assertEqual(C.snap(k, k["default"]), k["default"], k)   # the default sits on the grid

    def test_the_defaults_are_not_already_an_answer(self):
        for st in BF.STATIONS:
            for step in range(C.VARIANT_STEPS):
                self.assertFalse(BF.run_station(st, C.defaults(st), step)["ok"], (st["id"], step))

    def test_every_knob_the_scene_can_drag_exists(self):
        with open(os.path.join(ROOT, "www", "js", "hall_bounce.js"), encoding="utf8") as f:
            js = f.read()
        for key in ("1.1.hatch", "1.2.bags", "1.3.hump", "1.4.angle"):
            sid, kid = key.split(".")[0] + "." + key.split(".")[1], key.split(".")[2]
            self.assertIn(kid, [k["id"] for k in ST[sid]["knobs"]])
            self.assertIn('"%s' % key, js)


class TestKnobValidation(unittest.TestCase):
    def test_refused_with_a_reason(self):
        st = ST["1.1"]
        for raw, words in (({"hatch": 2.0, "speed": 3}, "not a setting"), ({"hatch": "high"}, "number"),
                           ({"hatch": float("nan")}, "number"), ({"hatch": True}, "number"),
                           ({"hatch": 9.0}, "between"), ({"hatch": 0.5}, "between"), ({"pad": "ice"}, "not a choice"),
                           ({"pad": 3}, "not a choice"), ([2.0], "object")):
            clean, err = C.validate_knobs(st, raw)
            self.assertIsNone(clean, raw)
            self.assertIn(words, err, raw)
        clean, err = C.validate_knobs(ST["1.2"], {"bags": 2.5})
        self.assertIn("whole number", err)

    def test_snapped_to_the_slider_grid_and_defaults_filled_in(self):
        clean, err = C.validate_knobs(ST["1.1"], {"hatch": 2.7312})
        self.assertIsNone(err)
        self.assertEqual(clean, {"hatch": 2.75, "pad": "hardwood"})
        clean, _ = C.validate_knobs(ST["1.4"], {"compression": 13.04, "angle": 44.6})
        self.assertEqual(clean, {"compression": 13.0, "angle": 45.0})
        clean, _ = C.validate_knobs(ST["1.2"], {"bags": 20})
        self.assertEqual(clean, {"bags": 20})
        clean, _ = C.validate_knobs(ST["1.3"], {})
        self.assertEqual(clean, {"hump": 0.5})


class TestEachKnobDoesWhatItSays(unittest.TestCase):
    """Move one knob, hold the rest: the outcome must move the right way."""

    def test_1_1_hatch_raises_the_bounce_and_the_pad_sets_how_much(self):
        hs = [1.0, 1.5, 2.0, 2.5, 3.0]
        apex = [run("1.1", hatch=h, pad="steel_plate")["viz"]["apex"] for h in hs]
        self.assertEqual(apex, sorted(apex))
        for a, h in zip(apex, hs):
            self.assertAlmostEqual(a, 0.85 ** 2 * h, delta=0.06 * h)          # h1 = e^2 h0, minus a bit of air
        by_pad = [run("1.1", hatch=2.0, pad=p)["viz"]["apex"] for p in ("steel_plate", "hardwood", "foam_mat", "sand")]
        self.assertEqual(by_pad, sorted(by_pad, reverse=True))

    def test_1_2_each_bag_makes_the_water_denser_until_it_is_saturated(self):
        fx = C.facts_for(ST["1.2"], NOM)
        rho = [BF.brine(b, fx["litres"])[1]["rho"] for b in range(0, 21)]
        for a, b in zip(rho, rho[1:]):
            self.assertGreaterEqual(b, a)
        sat = int(math.ceil(40 * BF.buoyancy.SALT_SAT / 1000.0))
        self.assertEqual(rho[sat], rho[20])                                      # more salt doesn't dissolve
        need = BF.min_bags(fx["litres"])
        self.assertFalse(run("1.2", bags=need - 1)["ok"])
        self.assertTrue(run("1.2", bags=need)["ok"])
        for b in range(0, 21):                                                   # the quick verdict = the engine's
            self.assertEqual(BF.floats_in(b, fx["litres"]), run("1.2", bags=b)["ok"], b)

    def test_1_3_a_higher_hump_is_crossed_slower(self):
        v = [run("1.3", hump=h)["viz"]["v_top"] for h in (0.9, 1.0, 1.1, 1.2, 1.3)]
        self.assertEqual(v, sorted(v, reverse=True))
        lim = math.sqrt(9.81 * 0.8)
        for h in (0.9, 1.1, 1.3):
            self.assertLessEqual(run("1.3", hump=h)["viz"]["v_top"], lim + 0.01)

    def test_1_4_compression_speeds_it_up_the_angle_aims_it(self):
        sp = [run("1.4", compression=c, angle=45.0)["metric"] for c in (6.0, 10.0, 14.0, 18.0)]
        self.assertEqual(sp, sorted(sp))
        self.assertAlmostEqual(sp[1], 0.10 * math.sqrt(300 / 0.13), delta=0.15)   # ~ x sqrt(k/m), minus the lift
        steep = run("1.4", compression=13.0, angle=70.0)["metric"]
        self.assertLess(steep, run("1.4", compression=13.0, angle=20.0)["metric"])  # lifting costs spring energy
        lands = []
        for a in (30.0, 45.0, 60.0):                                             # the angle changes where it comes down
            r = run("1.4", compression=13.0, angle=a)
            lands.append(r["frames"][-1]["x"])
        self.assertEqual(len(set(round(x, 2) for x in lands)), 3)


class TestAnswers(unittest.TestCase):
    def test_reference_answers_pass_and_mistakes_fail_with_the_right_reason(self):
        for st in BF.STATIONS:
            for k in st["solutions"]:
                r = run(st["id"], **k)
                self.assertTrue(r["ok"], (st["id"], k, r["reason"]))
            for k in st["mastery_solutions"]:
                r = run(st["id"], **k)
                self.assertTrue(r["ok"] and r["mastery"], (st["id"], k, r["reason"]))
            for k, why in st["wrong"]:
                r = run(st["id"], **k)
                self.assertFalse(r["ok"], (st["id"], k))
                self.assertIn(why, r["reason"], (st["id"], k))

    def test_results_are_complete_and_json(self):
        for st in BF.STATIONS:
            r = run(st["id"], **st["solutions"][0])
            for key in ("ok", "reason", "metric", "unit", "mastery", "predicted", "frames", "viz", "formula", "lab",
                        "score", "score_parts"):
                self.assertIn(key, r)
            self.assertTrue(r["frames"] and all(set(f) == {"t", "x", "y"} for f in r["frames"]))
            ts = [f["t"] for f in r["frames"]]
            self.assertEqual(ts, sorted(ts))
            json.dumps(r)

    def test_deterministic(self):
        for st in BF.STATIONS:
            a = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            b = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            self.assertEqual(a, b, st["id"])


class TestSavedSolutions(unittest.TestCase):
    data = BF.table()

    def test_every_variant_has_a_working_and_a_mastery_setting(self):
        for st in BF.STATIONS:
            vs = self.data["stations"][st["id"]]["variants"]
            self.assertEqual([v["step"] for v in vs], list(range(C.VARIANT_STEPS)))
            for v in vs:
                self.assertEqual(v["facts"], C.facts_for(st, v["step"]))
                clean, err = C.validate_knobs(st, v["solution"])
                self.assertIsNone(err)
                self.assertEqual(clean, v["solution"])                       # exactly what a slider can show
                r = BF.run_station(st, v["solution"], v["step"])
                self.assertTrue(r["ok"], (st["id"], v["step"], r["reason"]))
                self.assertEqual(r["metric"], v["metric"])
                if v.get("mastery_solution"):
                    m = BF.run_station(st, v["mastery_solution"], v["step"])
                    self.assertTrue(m["ok"] and m["mastery"], (st["id"], v["step"]))
                self.assertTrue(v["why"])

    def test_thresholds_mean_what_they_say(self):
        for v in self.data["stations"]["1.1"]["variants"]:
            low = v["thresholds"]["low_drop"]
            self.assertTrue(BF.run_station(ST["1.1"], {"hatch": round(low, 2), "pad": "steel_plate"}, v["step"])["mastery"])
            over = round(low + 0.05, 2)
            r = BF.run_station(ST["1.1"], {"hatch": over, "pad": "steel_plate"}, v["step"])
            self.assertFalse(r["mastery"])
        for v in self.data["stations"]["1.3"]["variants"]:
            fastest = BF.run_station(ST["1.3"], v["mastery_solution"], v["step"])
            self.assertLessEqual(fastest["viz"]["t_goal"], v["thresholds"]["speed_run"])
            slow = BF.run_station(ST["1.3"], {"hump": round(v["window"][0][1], 2)}, v["step"])
            self.assertFalse(slow["mastery"])                                 # the highest hump is too slow

    def test_game_links_preload_the_solution(self):
        for sid, s in self.data["stations"].items():
            for v in s["variants"]:
                u = urlparse(v["game"][1:])
                self.assertEqual(u.path, "/game/bounce/" + sid)
                q = parse_qs(u.query)
                self.assertEqual(q["practice"], ["1"])
                self.assertEqual(int(q["v"][0]), v["step"])
                self.assertEqual(json.loads(unquote(q["k"][0])), v["solution"])

    def test_the_saved_file_is_up_to_date(self):
        out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "make_game_solutions.py"), "--check"],
                             capture_output=True, text=True, timeout=600)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)


class TestLabLinks(unittest.TestCase):
    """Each station's "Open in the lab" links are real set-ups that
    reproduce what the station measured."""

    def lab(self, route):
        topic, q = lab_params(route)
        p, err = validate(spec(topic), q)
        self.assertIsNone(err, route)
        for k, v in q.items():                                  # nothing was clamped away
            sp = next(x for x in spec(topic)["params"] if x["id"] == k)
            if sp["kind"] == "number":
                self.assertAlmostEqual(p[k], float(v[0]), places=9, msg=route)
        return topic, p, RUNNERS[topic](p)

    def test_every_link_of_every_saved_solution_is_valid(self):
        for sid, s in BF.table()["stations"].items():
            for v in s["variants"]:
                for link in v["lab"]:
                    if link["route"].startswith("#/sandbox/"):
                        topic = link["route"].split("?")[0].split("/")[2]
                        world = json.loads(unquote(link["route"].split("w=")[1]))
                        self.assertIsNone(sandbox.validate(topic, world)[1], link["route"])
                    else:
                        self.lab(link["route"])

    def test_the_lab_reproduces_the_station(self):
        r = run("1.1", hatch=2.7, pad="steel_plate")
        _, _, lab = self.lab(r["lab"][0]["route"])
        self.assertAlmostEqual(lab["viz"]["apexes"][0]["h"], r["metric"], delta=0.01)      # same bounce
        for bags in (10, 11):
            r = run("1.2", bags=bags)
            _, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(lab["viz"]["eq"]["state"] == "floats", r["ok"], bags)         # same verdict
            self.assertAlmostEqual(lab["viz"]["liquid"]["rho"], r["metric"], delta=0.01)
        for hump in (0.6, 1.0):
            r = run("1.3", hump=hump)
            _, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(any(f["fly"] for f in lab["frames"]), r["viz"]["flew"], hump)  # same fly-off
        r = run("1.4", compression=13.0, angle=45.0)
        _, p, lab = self.lab(r["lab"][0]["route"])
        fx = C.facts_for(ST["1.4"], NOM)
        fr = lab["frames"]                                     # the lab's throw crosses the box's height...
        cross = next(f for a, f in zip(fr, fr[1:]) if a["vy"] < 0 and a["y"] >= fx["dy"] > f["y"])
        arrive = tracer.trace(0, 0, p["v0"] * math.cos(math.radians(45)), p["v0"] * math.sin(math.radians(45)),
                              0.13, BF.BALL_R, BF.BALL_K, zones=[("a", lambda x, y, vx, vy: vy < 0 and y < fx["dy"])])
        self.assertAlmostEqual(cross["x"], arrive["x"], delta=0.06)               # ...where the station's ball does
        self.assertTrue(fx["dx"] - 0.35 < cross["x"] < fx["dx"] + 0.35)


class TestVariants(unittest.TestCase):
    def test_seeded_stable_and_in_range(self):
        a = C.variant_steps(BF.HALL, "player-one")
        self.assertEqual(a, C.variant_steps(BF.HALL, "player-one"))
        self.assertTrue(all(0 <= s < C.VARIANT_STEPS for s in a.values()))
        self.assertEqual(set(C.variant_steps(BF.HALL, None).values()), {C.NOMINAL})
        seen = set()
        for i in range(40):
            seen |= set(C.variant_steps(BF.HALL, "p%d" % i).values())
        self.assertEqual(seen, set(range(C.VARIANT_STEPS)))                     # everyone doesn't get the same

    def test_facts_span_the_vary_range(self):
        for st in BF.STATIONS:
            f = next(x for x in st["facts"] if "vary" in x)
            self.assertEqual(C.facts_for(st, 0)[f["id"]], f["vary"][0])
            self.assertEqual(C.facts_for(st, C.VARIANT_STEPS - 1)[f["id"]], f["vary"][1])
            self.assertEqual(C.facts_for(st, C.NOMINAL)[f["id"]], f["value"])

    def test_public_card_never_leaks_the_answer(self):
        for st in BF.STATIONS:
            pub = C.public_station(st, NOM)
            blob = json.dumps(pub)
            for key in ("solutions", "wrong", "mastery_solutions", '"run"', "thresholds", "window"):
                self.assertNotIn(key, blob, (st["id"], key))


class TestStarsAndMachine(unittest.TestCase):
    def test_star_rules(self):
        st = ST["1.1"]
        ok = {"ok": True, "mastery": False, "predicted": 1.9}
        best = {"ok": True, "mastery": True, "predicted": 1.9}
        self.assertEqual(C.stars_for_run(st, {"ok": False, "mastery": False}, [], set()), [])
        self.assertEqual(C.stars_for_run(st, ok, [], set()), ["works", "efficient"])
        self.assertEqual(C.stars_for_run(st, ok, [{}, {}], set()), ["works"])          # past par
        self.assertEqual(C.stars_for_run(st, ok, [], {2}), ["works"])                  # used the formula hint
        self.assertEqual(C.stars_for_run(st, best, [], {1}), ["works", "efficient", "mastery"])
        self.assertEqual(C.stars_for_run(st, best, [], {3}), ["works"])             # Blueprint: no mastery, no efficiency
        self.assertEqual(C.stars_for_run(st, best, [], {2}), ["works", "mastery"])     # formula hint: mastery still open

    def test_insight_is_first_run_only_and_within_tolerance(self):
        st = ST["1.1"]
        res = {"predicted": 2.0}
        self.assertTrue(C.insight(st, res, 1.85, True))
        self.assertFalse(C.insight(st, res, 1.7, True))
        self.assertFalse(C.insight(st, res, 2.0, False))
        self.assertFalse(C.insight(st, res, None, True))
        self.assertTrue(C.insight(ST["1.2"], {"predicted": False}, False, True))
        self.assertFalse(C.insight(ST["1.2"], {"predicted": False}, True, True))

    def test_blueprint_only_after_two_failures(self):
        self.assertTrue(C.hint_allowed(1, 0) and C.hint_allowed(2, 0))
        self.assertFalse(C.hint_allowed(3, 1))
        self.assertTrue(C.hint_allowed(3, 2))

    def test_the_whole_machine_runs_from_a_to_b(self):
        knobs = {st["id"]: st["solutions"][0] for st in BF.STATIONS}
        m = BF.run_machine(knobs, {s: NOM for s in knobs})
        self.assertTrue(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["1.1", "1.2", "1.3", "1.4"])
        t = [f["t"] for f in m["frames"]]
        self.assertEqual(t, sorted(t))
        for a, b in zip(m["frames"], m["frames"][1:]):                           # one continuous path
            self.assertLess(math.hypot(b["x"] - a["x"], b["y"] - a["y"]), 0.5, (a, b))
        for prev, nxt in zip(m["stations"], m["stations"][1:]):
            self.assertLess(prev["t1"], nxt["t0"])

    def test_the_machine_stops_at_the_first_failure(self):
        knobs = {st["id"]: st["solutions"][0] for st in BF.STATIONS}
        knobs["1.2"] = {"bags": 0}
        m = BF.run_machine(knobs, {s: NOM for s in knobs})
        self.assertFalse(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["1.1", "1.2"])

    def test_hints_fill_in_this_players_numbers(self):
        fx = C.facts_for(ST["1.2"], 0)
        self.assertIn("36 L", BF.hint_text(ST["1.2"], 2, fx, 0))
        self.assertIn("Blueprint", BF.hint_text(ST["1.2"], 3, fx, 0))
        self.assertIn(str(BF.table()["stations"]["1.2"]["variants"][0]["solution"]["bags"]),
                      BF.hint_text(ST["1.2"], 3, fx, 0))


if __name__ == "__main__":
    unittest.main()


class TestScores(unittest.TestCase):
    """Each working run scores 0-1000 (1000 = the best possible for the
    player's variant); a failed run scores 0. The salt canal's score makes
    salt AND time matter, so more salt is not always better."""
    data = BF.table()["stations"]

    def test_bounds_and_failures(self):
        for st in BF.STATIONS:
            for k in st["solutions"]:
                r = run(st["id"], **k)
                self.assertTrue(BF.SCORE_FLOOR <= r["score"] <= BF.SCORE_MAX, (st["id"], k, r["score"]))
                self.assertTrue(r["score_parts"])
            for k, _ in st["wrong"]:
                self.assertEqual(run(st["id"], **k)["score"], 0)

    def test_the_top_score_setting_of_every_variant(self):
        for sid, s in self.data.items():
            for v in s["variants"]:
                r = BF.run_station(ST[sid], v["score_solution"], v["step"])
                self.assertEqual(r["score"], v["best_score"], (sid, v["step"]))
                if sid != "1.4":                                   # 1.1-1.3: the best possible is exactly 1000
                    self.assertEqual(r["score"], 1000, (sid, v["step"]))

    def test_1_1_a_lower_drop_scores_higher(self):
        sc = [run("1.1", hatch=h, pad="steel_plate")["score"] for h in (2.2, 2.5, 2.8, 3.1)]
        self.assertEqual(sc, sorted(sc, reverse=True))
        # the pad matters through the drop it needs: hardwood's lowest working drop can't reach 1000
        wood_low = self.data["1.1"]["variants"][NOM]["window"]["hardwood"][0][0]
        self.assertTrue(run("1.1", hatch=wood_low, pad="hardwood")["ok"])
        self.assertLess(run("1.1", hatch=wood_low, pad="hardwood")["score"], 1000)

    def test_1_2_salt_and_time_both_count(self):
        for v in self.data["1.2"]["variants"]:
            n_min, n_best = v["mastery_solution"]["bags"], v["score_solution"]["bags"]
            self.assertGreater(n_best, n_min, v["step"])            # the cheapest delivery is NOT the fewest bags...
            low = BF.run_station(ST["1.2"], {"bags": n_min}, v["step"])
            high = BF.run_station(ST["1.2"], {"bags": 20}, v["step"])
            self.assertTrue(low["ok"] and high["ok"])
            self.assertLess(low["score"], 1000)                     # ...too little salt is slow...
            self.assertLess(high["score"], 1000)                    # ...too much salt is wasted
            self.assertGreater(low["viz"]["t_arrive"], high["viz"]["t_arrive"])   # more salt: it pops up sooner
        r = run("1.2", bags=13)
        self.assertEqual(r["score"], round(1000 - (BF.delivery_cost(13, r["viz"]["t_arrive"]) -
                                                  self.data["1.2"]["variants"][NOM]["thresholds"]["cost_min"])))

    def test_1_3_faster_is_better(self):
        sc = [run("1.3", hump=h)["score"] for h in (0.9, 1.0, 1.2, 1.35)]
        self.assertEqual(sc, sorted(sc, reverse=True))

    def test_1_4_aim_and_trick_shots(self):
        direct = run("1.4", compression=13.1, angle=45.0)
        trick = run("1.4", compression=16.0, angle=45.0)
        self.assertTrue(trick["viz"]["bank"] and not direct["viz"]["bank"])
        off = abs(direct["viz"]["x_cross"] - C.facts_for(ST["1.4"], NOM)["dx"])
        self.assertEqual(direct["score"], max(BF.SCORE_FLOOR, round(800 * (1 - (off / 0.35) ** 2))))
        self.assertLessEqual(direct["score"], 800)                  # only a trick shot can beat 800

    def test_scores_are_deterministic(self):
        for st in BF.STATIONS:
            self.assertEqual(run(st["id"], **st["solutions"][0])["score"], run(st["id"], **st["solutions"][0])["score"])


class TestHallProgress(unittest.TestCase):
    halls = [{"id": "a", "stations": [{"id": "a1"}, {"id": "a2"}]}, {"id": "b", "stations": [{"id": "b1"}]},
             {"id": "c"}]

    def test_a_hall_opens_when_every_station_of_the_one_before_works(self):
        p = C.hall_progress(self.halls, {})
        self.assertEqual([(p[h]["unlocked"], p[h]["cleared"]) for h in "abc"], [(True, False), (False, False), (False, False)])
        p = C.hall_progress(self.halls, {"a1": {"works", "mastery"}})
        self.assertFalse(p["b"]["unlocked"])                        # one station is not enough
        p = C.hall_progress(self.halls, {"a1": {"works"}, "a2": {"works"}})
        self.assertTrue(p["a"]["cleared"] and p["b"]["unlocked"] and not p["c"]["unlocked"])
        p = C.hall_progress(self.halls, {"a1": {"works"}, "a2": {"works"}, "b1": {"works"}})
        self.assertTrue(p["c"]["unlocked"])
        self.assertFalse(p["c"]["cleared"])                         # a hall that isn't built is never "cleared"
