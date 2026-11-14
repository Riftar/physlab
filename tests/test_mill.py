"""The Machine Works, Hall 3 (Millbrook Mill, wooden ball): every station, every knob.

The knob / adjusted-object test plan of docs/game/IMPLEMENTATION-hall3.md:

  * the station table is complete and sane; every knob has a yellow handle
    in the hall's painter (www/js/hall_mill.js)
  * knob validation (refused with a reason, snapped to the slider grid)
  * EACH KNOB DOES WHAT IT SAYS - and the physics behind it is the textbook
    law: Archimedes + the level rise dh = V / A (3.1), drag pushes through
    the wind (3.2), the thin-lens equation and the blur circle (3.3), the
    principle of moments and I alpha = tau (3.4)
  * the defaults are not an answer; the reference answers pass; the common
    mistakes fail with the right explanation
  * the SAVED settings (physlab/game/data/mill.json) work for every variant,
    the thresholds mean what they say, the file is up to date
  * every lab deep link is a valid set-up and the lab reproduces the
    station (same float height, same landing, same light share, same hoist)
  * scores, determinism, the machine A -> B
"""

import json
import math
import os
import re
import sys
import unittest
from urllib.parse import parse_qs, unquote, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab import spec  # noqa: E402
from physlab.game import HALLS, HALL_MODULES  # noqa: E402
from physlab.game import common as C  # noqa: E402
from physlab.game import mill as ML  # noqa: E402
from physlab.server import validate, RUNNERS  # noqa: E402
from physlab.topics import buoyancy, optics  # noqa: E402

NOM = C.NOMINAL
ST = ML.BY_ID
DATA = ML.table()["stations"]


def run(sid, step=NOM, **knobs):
    st = ST[sid]
    k, err = C.validate_knobs(st, knobs)
    assert err is None, err
    return ML.run_station(st, k, step)


def fx(sid, step=NOM):
    return C.facts_for(ST[sid], step)


class TestStationTable(unittest.TestCase):
    def test_the_third_hall(self):
        self.assertEqual([h["id"] for h in HALLS][-1], "mill")
        self.assertIs(HALL_MODULES["mill"], ML)
        self.assertEqual((ML.HALL["status"], ML.HALL["ball"]), ("ready", "wood"))
        self.assertEqual(ML.BALL["mass"], 0.16)
        self.assertAlmostEqual(ML.BALL["mass"] / (math.pi * ML.BALL["d"] ** 3 / 6), ML.WOOD["rho"], delta=0.5)

    def test_four_stations_in_order_with_everything(self):
        self.assertEqual([s["id"] for s in ML.STATIONS], ["3.1", "3.2", "3.3", "3.4"])
        for st in ML.STATIONS:
            for key in ("title", "intro", "goal", "hook", "knobs", "facts", "predict", "mastery", "hints", "par",
                        "formulas", "solutions", "wrong", "mastery_solutions", "learn", "run", "score_rule"):
                self.assertIn(key, st, (st["id"], key))
            self.assertEqual(st["hall"], "mill")
            self.assertEqual(len(st["hints"]), 2)
            self.assertEqual(sum(1 for f in st["facts"] if "vary" in f), 1, st["id"])
            self.assertIn(st["learn"], ("buoyancy", "motion", "optics", "levers"))
            for expr in st["formulas"]:                         # every formula is explained in its lab
                self.assertIn(expr, [f["expr"] for f in spec(st["learn"])["formulas"]] + [
                    "F = 1/2 * rho * C_d * A * (w - v)^2", "dx = 1/2 * (F/m) * t^2"], (st["id"], expr))

    def test_knob_specs_are_sane(self):
        for st in ML.STATIONS:
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
                    self.assertEqual(C.snap(k, k["default"]), k["default"], k)

    def test_the_defaults_are_not_already_an_answer(self):
        for st in ML.STATIONS:
            for step in range(C.VARIANT_STEPS):
                self.assertFalse(ML.run_station(st, C.defaults(st), step)["ok"], (st["id"], step))

    def test_every_knob_has_a_handle_in_the_scene(self):
        with open(os.path.join(ROOT, "www", "js", "hall_mill.js"), encoding="utf8") as f:
            js = f.read()
        keys = set(re.findall(r'"(\d\.\d\.[a-z_]+)"', js))
        want = {"%s.%s" % (st["id"], k["id"]) for st in ML.STATIONS for k in st["knobs"]}
        self.assertEqual(keys, want)                                          # every knob, nothing else
        self.assertIn("PL.gameHalls.mill", js)

    def test_the_layout_places_every_station(self):
        L = ML.LAYOUT
        for sid in ST:
            v = L["stations"][sid]["view"]
            self.assertTrue(L["bounds"]["x0"] <= v["x0"] < v["x1"] <= L["bounds"]["x1"], sid)
            self.assertTrue(L["bounds"]["y0"] <= v["y0"] < v["y1"] <= L["bounds"]["y1"], sid)
        self.assertEqual(L["ball"]["r"], 0.04)


class TestKnobValidation(unittest.TestCase):
    def test_refused_with_a_reason(self):
        for sid, raw, words in (("3.1", {"item": "cork"}, "not a choice"), ("3.1", {"count": 41}, "between"),
                                ("3.1", {"count": 1.5}, "whole number"), ("3.1", {"count": "9"}, "whole number"),
                                ("3.2", {"wind": 20.5}, "between"), ("3.2", {"wind": float("nan")}, "number"),
                                ("3.2", {"speed": 3}, "not a setting"), ("3.3", {"d_o": 4.5}, "between"),
                                ("3.3", {"d_o": 96}, "between"), ("3.4", {"hook": 0.1}, "between"),
                                ("3.4", {"water": 2.5}, "between"), ("3.4", {"water": None}, "number")):
            clean, err = C.validate_knobs(ST[sid], raw)
            self.assertIsNone(clean, (sid, raw))
            self.assertIn(words, err, (sid, raw))

    def test_snapped_to_the_slider_grid(self):
        for sid, raw, want in (("3.1", {"count": 9}, {"item": "block", "count": 9}),
                               ("3.2", {"wind": 15.3}, {"wind": 15.5}),
                               ("3.3", {"d_o": 74.2}, {"d_o": 74.0}),
                               ("3.4", {"hook": 0.52, "water": 0.374}, {"hook": 0.5, "water": 0.37})):
            clean, err = C.validate_knobs(ST[sid], raw)
            self.assertIsNone(err)
            self.assertEqual(clean, want)


class TestEachKnobDoesWhatItSays(unittest.TestCase):
    def test_3_1_more_drops_float_the_ball_higher_sinkers_more_than_floaters(self):
        for item in ("stone", "bearing", "block"):
            hs = [ML.well_centre_cm({"item": item, "count": n}, fx("3.1"))[0] for n in (0, 5, 10, 20)]
            self.assertEqual(hs, sorted(hs), item)
        c = lambda item, n: ML.well_centre_cm({"item": item, "count": n}, fx("3.1"))[0]
        base = c("stone", 0)
        # a floating pine block and a bearing are about the same size, but the block raises the water half as much
        self.assertAlmostEqual((c("block", 10) - base) / (c("bearing", 10) - base), 0.51 * 64 / 65.45, delta=0.02)
        self.assertIn("floats at", run("3.1", item="block", count=40)["reason"])
        self.assertIn("half its size", run("3.1", item="block", count=40)["reason"])

    def test_3_2_more_wind_blows_it_further(self):
        lands = [ML.fly(w)["x"] for w in (0.0, 5.0, 10.0, 15.0, 20.0)]
        self.assertEqual(lands, sorted(lands))
        self.assertIn("Splash", run("3.2", wind=0.0)["reason"])
        self.assertIn("hedge", run("3.2", wind=20.0)["reason"])

    def test_3_3_the_lens_position_decides_the_light_on_the_cell(self):
        shares = {d: run("3.3", d_o=d)["viz"]["share"] for d in (19.0, 26.0, 50.0, 74.0)}
        self.assertEqual(shares[74.0], 1.0)
        self.assertTrue(all(shares[d] < 0.1 for d in (19.0, 26.0, 50.0)), shares)
        self.assertIn("IS in focus", run("3.3", d_o=26.0)["reason"])        # the trap: sharp but big
        self.assertIn("focal length", run("3.3", d_o=19.0)["reason"])

    def test_3_4_more_water_lifts_faster_and_harder(self):
        vs = [run("3.4", hook=0.5, water=w)["viz"]["speed"] for w in (0.34, 0.37, 0.40, 0.42)]
        ts = [run("3.4", hook=0.5, water=w)["viz"]["t_up"] for w in (0.34, 0.37, 0.40, 0.42)]
        self.assertEqual(vs, sorted(vs))
        self.assertEqual(ts, sorted(ts, reverse=True))
        self.assertIn("budge", run("3.4", hook=0.5, water=0.3)["reason"])
        self.assertIn("Flung", run("3.4", hook=0.5, water=0.6)["reason"])
        # the hook's distance: further out needs less water for the same lift
        self.assertLess(DATA["3.4"]["variants"][NOM]["window"]["b=1"][0][1],
                        DATA["3.4"]["variants"][NOM]["window"]["b=0.5"][0][0])


class TestThePhysics(unittest.TestCase):
    def test_3_1_level_rise_and_archimedes(self):
        f = fx("3.1")
        for item, n in (("stone", 9), ("bearing", 28), ("block", 20)):
            c, level = ML.well_centre_cm({"item": item, "count": n}, f)
            v_ball = math.pi * 8.0 ** 3 / 6.0                                  # cm^3
            v_sub = v_ball * ML.WOOD["rho"] / ML.WATER["rho"]
            expect = f["depth"] + (ML.displaced_cm3(item, n) + v_sub) / ML.WELL_CM2
            self.assertAlmostEqual(level, expect, places=3)                  # dh = V_pushed / A
            h_sub = buoyancy.float_depth("sphere", 0.08, ML.WOOD["rho"] / ML.WATER["rho"]) * 100
            self.assertAlmostEqual(c, level - h_sub + 4.0, places=6)        # it floats 60 % under
        r = run("3.1", item="stone", count=9)
        self.assertAlmostEqual(r["frames"][-1]["lv"], r["viz"]["level_cm"] / 100, delta=0.002)   # the run settles there

    def test_3_2_no_wind_no_push(self):
        out = ML.fly(0.0)                                                      # only drag slows it a little
        th = math.radians(ML.FJ_ANGLE)
        vx, vy = ML.FJ_U0 * math.cos(th), ML.FJ_U0 * math.sin(th)
        t = (vy + math.sqrt(vy * vy + 2 * 9.81 * ML.FJ_DROP)) / 9.81
        self.assertAlmostEqual(out["x"], vx * t, delta=0.02)
        steel = ML.tracer.trace(0.0, 0.0, vx, vy, 0.51, 0.025, ML.tracer.drag_constant(0.05), wind=15.0, dt=5e-4,
                                tmax=3.0, zones=[("d", lambda x, y, a, b: y < -ML.FJ_DROP)])
        steel0 = ML.tracer.trace(0.0, 0.0, vx, vy, 0.51, 0.025, ML.tracer.drag_constant(0.05), dt=5e-4, tmax=3.0,
                                 zones=[("d", lambda x, y, a, b: y < -ML.FJ_DROP)])
        self.assertLess(steel["x"] - steel0["x"], 0.12)                       # the steel ball hardly notices
        self.assertGreater(ML.fly(15.0)["x"] - ML.fly(0.0)["x"], 0.4)         # the wooden ball does

    def test_3_3_thin_lens_and_two_sharp_positions(self):
        f = ML.LG_F
        self.assertAlmostEqual(f, 20.0 / (2 * (1.52 - 1)), places=6)        # lensmaker
        bench = fx("3.3")["bench"]
        disc = math.sqrt(bench * bench - 4 * bench * f)
        near, far = (bench - disc) / 2, (bench + disc) / 2                    # d_o + d_i = bench, 1/d_o + 1/d_i = 1/f
        self.assertAlmostEqual(near, 26.0, delta=0.3)
        self.assertAlmostEqual(far, 74.0, delta=0.3)
        for d in (near, far):
            light = ML.gate_light(d, bench)
            self.assertLess(abs(light["defocus"]), 1e-6)                      # both sharp...
        self.assertLess(ML.gate_light(near, bench)["share"], 0.05)           # ...only one small enough
        self.assertEqual(ML.gate_light(far, bench)["share"], 1.0)
        self.assertAlmostEqual(ML.gate_light(far, bench)["geo"], 2.0 * (bench - far) / far, places=6)

    def test_3_4_principle_of_moments(self):
        a = fx("3.4")["arm"]
        for b in (0.3, 0.5, 0.7, 1.0):
            w_bal = 0.26 * a / b - 0.2                                       # (0.2 + w) b = 0.26 a
            r_under = run("3.4", hook=b, water=max(0.0, math.floor(w_bal * 100 - 1) / 100))
            self.assertFalse(r_under["viz"]["moves"], b)                      # at or below balance: it stays
            win = DATA["3.4"]["variants"][NOM]["window"].get("b=%g" % b)
            if win:
                self.assertGreater(win[0][0], w_bal)                        # it only works a little past balance

    def test_3_4_energy(self):
        """The bucket's drop pays for the scoop's rise, the beam's spin and the pivot's friction."""
        r = run("3.4", hook=0.5, water=0.4)
        p = ML.hoist_params({"hook": 0.5, "water": 0.4}, fx("3.4"))
        om = r["viz"]["speed"] / p["d1"]
        dth = math.radians(50.0)
        drop = p["m2"] * 9.81 * p["d2"] * 2 * math.sin(math.radians(25))
        rise = p["m1"] * 9.81 * p["d1"] * 2 * math.sin(math.radians(25))
        ke = 0.5 * r["viz"]["inertia"] * om * om
        self.assertAlmostEqual(drop - rise - p["friction"] * dth, ke, delta=0.003 * drop)


class TestAnswers(unittest.TestCase):
    def test_reference_answers_pass_and_mistakes_fail_with_the_right_reason(self):
        for st in ML.STATIONS:
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
        extra = {"3.1": {"lv"}, "3.2": set(), "3.3": {"bridge"}, "3.4": {"th"}}
        for st in ML.STATIONS:
            for k in st["solutions"][:1] + [w for w, _ in st["wrong"]]:
                r = run(st["id"], **k)
                for key in ("ok", "reason", "metric", "unit", "mastery", "predicted", "frames", "viz", "formula",
                            "lab", "score", "score_parts"):
                    self.assertIn(key, r)
                self.assertTrue(r["frames"])
                for f in r["frames"]:
                    self.assertTrue({"t", "x", "y"} <= set(f) <= {"t", "x", "y"} | extra[st["id"]], (st["id"], f))
                ts = [f["t"] for f in r["frames"]]
                self.assertEqual(ts, sorted(ts))
                json.dumps(r)

    def test_deterministic(self):
        for st in ML.STATIONS:
            a = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            b = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            self.assertEqual(a, b, st["id"])

    def test_the_bridge_only_comes_down_when_the_gate_is_armed(self):
        ok, bad = run("3.3", d_o=74.0), run("3.3", d_o=26.0)
        self.assertEqual(ok["frames"][-1]["bridge"], 1.0)
        self.assertEqual(max(f["bridge"] for f in bad["frames"]), 0.0)
        self.assertLess(bad["frames"][-1]["x"], ML.BRIDGE[0])               # it waits at the raised bridge
        self.assertAlmostEqual(ok["frames"][-1]["x"], ML.BRIDGE[1], places=3)

    def test_the_flung_ball_flies_off(self):
        r = run("3.4", hook=1.0, water=2.0)
        top = ML.scoop_at(fx("3.4")["arm"], math.radians(25))
        self.assertGreater(max(f["y"] for f in r["frames"]), top[1] + 0.2)   # up out of the scoop
        ok = run("3.4", hook=0.5, water=0.37)
        self.assertLess(abs(ok["frames"][-1]["x"] - ML.HOPPER[0]), 0.01)       # gently into the hopper


class TestSavedSolutions(unittest.TestCase):
    def test_every_variant_has_a_working_a_mastery_and_a_top_setting(self):
        for st in ML.STATIONS:
            vs = DATA[st["id"]]["variants"]
            self.assertEqual([v["step"] for v in vs], list(range(C.VARIANT_STEPS)))
            for v in vs:
                self.assertEqual(v["facts"], C.facts_for(st, v["step"]))
                for key in ("solution", "mastery_solution", "score_solution"):
                    clean, err = C.validate_knobs(st, v[key])
                    self.assertIsNone(err)
                    self.assertEqual(clean, v[key])
                r = ML.run_station(st, v["solution"], v["step"])
                self.assertTrue(r["ok"], (st["id"], v["step"], r["reason"]))
                self.assertEqual(r["metric"], v["metric"])
                m = ML.run_station(st, v["mastery_solution"], v["step"])
                self.assertTrue(m["ok"] and m["mastery"], (st["id"], v["step"]))
                top = ML.run_station(st, v["score_solution"], v["step"])
                self.assertEqual(top["score"], 1000, (st["id"], v["step"]))
                self.assertEqual(top["score"], v["best_score"])
                self.assertTrue(v["why"])

    def test_thresholds_mean_what_they_say(self):
        for v in DATA["3.1"]["variants"]:
            n = v["thresholds"]["fewest"]
            self.assertIsInstance(n, int)
            for item in ("stone", "bearing", "block"):                    # nothing works with fewer drops
                for m in range(0, n):
                    c, lv = ML.well_centre_cm({"item": item, "count": m}, v["facts"])
                    self.assertGreater(abs(c - 45.0), 2.5, (item, m))
                self.assertFalse(ML.run_station(ST["3.1"], {"item": item, "count": n - 1}, v["step"])["ok"])
        for v in DATA["3.2"]["variants"]:
            th = v["thresholds"]
            self.assertTrue(ML.run_station(ST["3.2"], {"wind": th["w_lo"]}, v["step"])["ok"])
            self.assertFalse(ML.run_station(ST["3.2"], {"wind": th["w_lo"] - 0.5}, v["step"])["ok"])
            self.assertEqual(th["breeze"], th["w_lo"] + 1.0)
        for v in DATA["3.3"]["variants"]:
            top = ML.run_station(ST["3.3"], v["score_solution"], v["step"])
            self.assertAlmostEqual(abs(top["viz"]["defocus"]), v["thresholds"]["defocus_min"], places=3)
            lo, hi = v["window"][0]
            for d in (lo - 0.5, hi + 0.5):
                self.assertFalse(ML.run_station(ST["3.3"], {"d_o": d}, v["step"])["ok"])

    def test_game_links_preload_the_solution(self):
        for sid, s in DATA.items():
            for v in s["variants"]:
                for link, key in (("game", "solution"), ("game_mastery", "mastery_solution"),
                                  ("game_best", "score_solution")):
                    u = urlparse(v[link][1:])
                    self.assertEqual(u.path, "/game/mill/" + sid)
                    q = parse_qs(u.query)
                    self.assertEqual((q["practice"], int(q["v"][0])), (["1"], v["step"]))
                    self.assertEqual(json.loads(unquote(q["k"][0])), v[key])

    def test_the_solutions_page_lists_every_variant(self):
        with open(os.path.join(ROOT, "docs", "game", "hall3-solutions.md"), encoding="utf8") as f:
            md = f.read()
        for sid, s in DATA.items():
            for v in s["variants"]:
                self.assertIn(v["game"], md)


class TestLabLinks(unittest.TestCase):
    """Each station's "Open in the lab" link is a real set-up that reproduces what the station measured."""

    def lab(self, route):
        u = urlparse(route[1:])
        topic, q = u.path.strip("/"), parse_qs(u.query)
        p, err = validate(spec(topic), q)
        self.assertIsNone(err, route)
        for k, v in q.items():                                  # nothing was clamped away
            sp = next(x for x in spec(topic)["params"] if x["id"] == k)
            if sp["kind"] == "number":
                self.assertAlmostEqual(p[k], float(v[0]), places=9, msg=route)
            elif sp["kind"] == "boolean":
                self.assertEqual(p[k], v[0] in ("1", "true"), route)
            else:
                self.assertEqual(str(p[k]), v[0], route)
        return topic, p, RUNNERS[topic](p)

    def test_every_link_of_every_saved_solution_is_valid(self):
        for sid, s in DATA.items():
            for v in s["variants"]:
                self.assertTrue(v["lab"], sid)
                for link in v["lab"]:
                    self.lab(link["route"])

    def test_3_1_the_buoyancy_lab_floats_it_at_the_same_height(self):
        for item, n in (("stone", 9), ("bearing", 28), ("block", 40), ("stone", 12)):
            r = run("3.1", item=item, count=n)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "buoyancy")
            ro = {x["label"]: x["value"] for x in lab["readouts"]}
            self.assertAlmostEqual(ro["Centre of the object at rest"], r["metric"], delta=0.02, msg=(item, n))
            self.assertAlmostEqual(lab["frames"][-1]["level"] * 100, r["viz"]["level_cm"], delta=0.05)

    def test_3_2_the_motion_lab_lands_it_at_the_same_place(self):
        for w in (0.0, 15.5, 20.0):
            r = run("3.2", wind=w)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "motion")
            self.assertAlmostEqual(lab["frames"][-1]["x"], r["viz"]["land"], delta=0.005, msg=w)

    def test_3_3_the_optics_lab_puts_the_same_light_on_the_cell(self):
        for d in (26.0, 50.0, 74.0):
            r = run("3.3", d_o=d)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "optics")
            self.assertAlmostEqual(lab["viz"]["screen"]["share"], r["viz"]["share"], places=3)
            self.assertAlmostEqual(lab["viz"]["screen"]["patch"], r["viz"]["patch"], places=2)

    def test_3_4_the_levers_lab_lifts_the_same(self):
        for b, w in ((0.5, 0.37), (1.0, 0.1), (1.0, 2.0), (0.5, 0.2)):
            r = run("3.4", hook=b, water=w)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "levers")
            self.assertEqual(lab["viz"]["moves"], r["viz"]["moves"])
            if r["viz"]["t_up"] is not None:
                self.assertAlmostEqual(lab["viz"]["t_hit"], r["viz"]["t_up"], places=3)
                self.assertAlmostEqual(lab["viz"]["v1"], r["viz"]["speed"], places=3)


class TestVariantsAndCards(unittest.TestCase):
    def test_facts_span_the_vary_range(self):
        for st in ML.STATIONS:
            f = next(x for x in st["facts"] if "vary" in x)
            self.assertEqual(C.facts_for(st, 0)[f["id"]], f["vary"][0])
            self.assertEqual(C.facts_for(st, C.VARIANT_STEPS - 1)[f["id"]], f["vary"][1])
            self.assertEqual(C.facts_for(st, C.NOMINAL)[f["id"]], f["value"])

    def test_public_card_never_leaks_the_answer(self):
        for st in ML.STATIONS:
            blob = json.dumps(C.public_station(st, NOM))
            for key in ("solutions", "wrong", "mastery_solutions", '"run"', "thresholds", '"window"'):
                self.assertNotIn(key, blob, (st["id"], key))

    def test_hints_fill_in_this_players_numbers(self):
        for sid, key in (("3.1", "depth"), ("3.2", "cart"), ("3.3", "bench"), ("3.4", "arm")):
            f = fx(sid, 0)
            self.assertIn("%g" % f[key], ML.hint_text(ST[sid], 2, f, 0), sid)
            bp = ML.hint_text(ST[sid], 3, f, 0)
            self.assertIn("Blueprint", bp)
            for k, v in DATA[sid]["variants"][0]["solution"].items():
                self.assertIn("%s = %s" % (k, v), bp)

    def test_mastery_texts(self):
        self.assertIn("(%d)" % DATA["3.1"]["variants"][0]["thresholds"]["fewest"], ML.mastery_text(ST["3.1"], 0))
        self.assertIn("%.2f" % DATA["3.2"]["variants"][0]["thresholds"]["breeze"], ML.mastery_text(ST["3.2"], 0))
        for sid in ST:
            self.assertNotIn("{", ML.mastery_text(ST[sid], 2))


class TestScores(unittest.TestCase):
    def test_bounds_and_failures(self):
        for st in ML.STATIONS:
            for k in st["solutions"] + st["mastery_solutions"]:
                r = run(st["id"], **k)
                self.assertTrue(ML.kit.SCORE_FLOOR <= r["score"] <= ML.kit.SCORE_MAX, (st["id"], k, r["score"]))
                self.assertTrue(r["score_parts"])
            for k, _ in st["wrong"]:
                r = run(st["id"], **k)
                self.assertEqual((r["score"], r["score_parts"]), (0, []))

    def test_3_1_aim_and_effort(self):
        v = DATA["3.1"]["variants"][NOM]
        r = run("3.1", item="bearing", count=28)
        cost = ML.well_cost(r["metric"], 28)
        self.assertAlmostEqual(r["score"], 1000 - (cost - v["thresholds"]["cost_min"]), delta=1)
        self.assertGreater(run("3.1", item="stone", count=9)["score"], r["score"])   # fewer drops, close enough

    def test_3_2_aim_and_fan_power(self):
        v = DATA["3.2"]["variants"][NOM]
        lo, hi = v["window"][0]
        self.assertGreater(run("3.2", wind=v["score_solution"]["wind"])["score"], run("3.2", wind=hi)["score"])

    def test_3_3_sharper_scores_higher(self):
        v = DATA["3.3"]["variants"][NOM]
        lo, hi = v["window"][0]
        best = v["score_solution"]["d_o"]
        self.assertEqual(run("3.3", d_o=best)["score"], 1000)
        self.assertLess(run("3.3", d_o=lo)["score"], 1000)
        self.assertLess(run("3.3", d_o=hi)["score"], 1000)

    def test_3_4_quick_and_gentle_pull_in_opposite_directions(self):
        v = DATA["3.4"]["variants"][NOM]
        gentle = run("3.4", **v["mastery_solution"])
        top = run("3.4", **v["score_solution"])
        self.assertTrue(gentle["mastery"])
        self.assertFalse(top["mastery"])                                      # the best score isn't the gentlest
        self.assertGreater(top["score"], gentle["score"])


class TestMachine(unittest.TestCase):
    knobs = {sid: DATA[sid]["variants"][NOM]["solution"] for sid in DATA}

    def test_the_whole_machine_runs_from_a_to_b(self):
        m = ML.run_machine(self.knobs, {s: NOM for s in self.knobs})
        self.assertTrue(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["3.1", "3.2", "3.3", "3.4"])
        t = [f["t"] for f in m["frames"]]
        self.assertEqual(t, sorted(t))
        for a, b in zip(m["frames"], m["frames"][1:]):                           # one continuous path
            self.assertLess(math.hypot(b["x"] - a["x"], b["y"] - a["y"]), 0.5, (a, b))
        for prev, nxt in zip(m["stations"], m["stations"][1:]):
            self.assertLess(prev["t1"], nxt["t0"])
        last = m["frames"][-1]
        self.assertLess(abs(last["x"] - ML.HOPPER[0]), 0.01)                     # into the millstone hopper

    def test_the_machine_stops_at_the_first_failure(self):
        knobs = dict(self.knobs, **{"3.3": {"d_o": 26.0}})
        m = ML.run_machine(knobs, {s: NOM for s in knobs})
        self.assertFalse(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["3.1", "3.2", "3.3"])

    def test_stations_line_up_in_the_hall(self):
        r1 = run("3.1", **self.knobs["3.1"])
        self.assertAlmostEqual(r1["frames"][-1]["y"], ML.WELL[1] + ML.PADDLE, places=3)   # swept out at the paddles
        r3 = run("3.3", **self.knobs["3.3"])
        self.assertAlmostEqual(r3["frames"][0]["y"], ML.PATH_Y + ML.BALL_R, places=4)


if __name__ == "__main__":
    unittest.main()
