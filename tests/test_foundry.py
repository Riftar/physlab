"""The Machine Works, Hall 2 (the Foundry, steel ball): every station, every knob.

The knob / adjusted-object test plan of docs/game/IMPLEMENTATION-hall2.md:

  * the station table is complete and sane; every knob has a yellow handle
    in the hall's painter (www/js/hall_foundry.js)
  * knob validation (refused with a reason, snapped to the slider grid)
  * EACH KNOB DOES WHAT IT SAYS - and the physics behind it is the textbook
    law: thermal expansion + heat balance (2.1), Ohm's law in one loop
    (2.2), Pascal + incompressible oil (2.3), the pendulum's tension at the
    bottom and the flight after it (2.4)
  * the defaults are not an answer; the reference answers pass; the common
    mistakes fail with the right explanation
  * the SAVED settings (physlab/game/data/foundry.json) work for every
    variant, the thresholds mean what they say, the file is up to date
  * every lab deep link is a valid set-up and the lab reproduces the
    station (same temperature, same current, same lift, same tension)
  * scores, determinism, time-lapse zones, the machine A -> B
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
from physlab.game import HALLS, HALL_MODULES, COMING  # noqa: E402
from physlab.game import common as C  # noqa: E402
from physlab.game import foundry as FD  # noqa: E402
from physlab.server import validate, RUNNERS  # noqa: E402

NOM = C.NOMINAL
ST = FD.BY_ID
DATA = FD.table()["stations"]


def run(sid, step=NOM, **knobs):
    st = ST[sid]
    k, err = C.validate_knobs(st, knobs)
    assert err is None, err
    return FD.run_station(st, k, step)


def fx(sid, step=NOM):
    return C.facts_for(ST[sid], step)


class TestStationTable(unittest.TestCase):
    def test_registered_after_the_bounce_factory(self):
        self.assertEqual([h["id"] for h in HALLS], ["bounce", "foundry", "mill"])
        self.assertIs(HALL_MODULES["foundry"], FD)
        self.assertEqual(COMING, [])
        self.assertEqual(FD.HALL["status"], "ready")
        self.assertEqual(FD.HALL["ball"], "steel")

    def test_four_stations_in_order_with_everything(self):
        self.assertEqual([s["id"] for s in FD.STATIONS], ["2.1", "2.2", "2.3", "2.4"])
        for st in FD.STATIONS:
            for key in ("title", "intro", "goal", "hook", "knobs", "facts", "predict", "mastery", "hints", "par",
                        "formulas", "solutions", "wrong", "mastery_solutions", "learn", "run", "score_rule"):
                self.assertIn(key, st, (st["id"], key))
            self.assertEqual(st["hall"], "foundry")
            self.assertEqual(len(st["hints"]), 2)
            self.assertEqual(sum(1 for f in st["facts"] if "vary" in f), 1, st["id"])   # one variant fact
            self.assertIn(st["learn"], ("heat", "circuits", "pressure", "pendulum"))
            ids = [k["id"] for k in st["knobs"]]
            self.assertEqual(len(ids), len(set(ids)))

    def test_knob_specs_are_sane(self):
        for st in FD.STATIONS:
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
        for st in FD.STATIONS:
            for step in range(C.VARIANT_STEPS):
                self.assertFalse(FD.run_station(st, C.defaults(st), step)["ok"], (st["id"], step))

    def test_every_knob_has_a_handle_in_the_scene(self):
        with open(os.path.join(ROOT, "www", "js", "hall_foundry.js"), encoding="utf8") as f:
            js = f.read()
        keys = set(re.findall(r'key: "(\d\.\d\.\w+)"', js))
        want = {"%s.%s" % (st["id"], k["id"]) for st in FD.STATIONS for k in st["knobs"]}
        self.assertEqual(keys, want)                                          # every knob, nothing else
        self.assertIn("PL.gameHalls.foundry", js)

    def test_the_layout_places_every_station(self):
        L = FD.LAYOUT
        for sid in ST:
            v = L["stations"][sid]["view"]
            self.assertTrue(L["bounds"]["x0"] <= v["x0"] < v["x1"] <= L["bounds"]["x1"], sid)
            self.assertTrue(L["bounds"]["y0"] <= v["y0"] < v["y1"] <= L["bounds"]["y1"], sid)
        self.assertEqual(L["ball"]["r"], 0.025)


class TestKnobValidation(unittest.TestCase):
    def test_refused_with_a_reason(self):
        for sid, raw, words in (("2.1", {"target": "kettle"}, "not a choice"), ("2.1", {"water": 0.6}, "between"),
                                ("2.1", {"water": "lots"}, "number"), ("2.1", {"water": float("inf")}, "number"),
                                ("2.2", {"battery": "lemon"}, "not a choice"), ("2.2", {"R": -1}, "between"),
                                ("2.2", {"R": 51}, "between"), ("2.2", {"volts": 9}, "not a setting"),
                                ("2.3", {"d2": 1.0}, "between"), ("2.3", {"d2": True}, "number"),
                                ("2.4", {"angle": 95}, "between"), ("2.4", {"length": 0.3}, "between"),
                                ("2.4", {"angle": None}, "number")):
            clean, err = C.validate_knobs(ST[sid], raw)
            self.assertIsNone(clean, (sid, raw))
            self.assertIn(words, err, (sid, raw))

    def test_snapped_to_the_slider_grid(self):
        for sid, raw, want in (("2.1", {"water": 0.123}, {"target": "ball", "water": 0.12}),
                               ("2.2", {"R": 6.3}, {"battery": "aa", "R": 6.5}),
                               ("2.3", {"d2": 3.94}, {"d2": 3.9}),
                               ("2.4", {"angle": 57.6, "length": 1.02}, {"length": 1.0, "angle": 58.0})):
            clean, err = C.validate_knobs(ST[sid], raw)
            self.assertIsNone(err)
            self.assertEqual(clean, want)


class TestEachKnobDoesWhatItSays(unittest.TestCase):
    def test_2_1_more_hot_water_on_the_ring_heats_it_more_and_opens_it_sooner(self):
        peaks, drops = [], []
        for w in (0.16, 0.2, 0.3, 0.4, 0.5):
            r = run("2.1", target="ring", water=w)
            self.assertTrue(r["ok"], w)
            peaks.append(r["metric"])
            drops.append(r["viz"]["t_drop"])
        self.assertEqual(peaks, sorted(peaks))
        self.assertEqual(drops, sorted(drops, reverse=True))
        self.assertFalse(run("2.1", target="ring", water=0.1)["ok"])            # too little: it never gets there

    def test_2_1_the_target_decides_which_part_grows(self):
        for w in (0.1, 0.3, 0.5):
            self.assertFalse(run("2.1", target="ball", water=w)["ok"])          # the ball grows: tighter
            self.assertFalse(run("2.1", target="both", water=w)["ok"])          # both grow: not hot enough
        tight = run("2.1", target="ball", water=0.5)
        self.assertIn("heated the BALL", tight["reason"])
        self.assertGreater(tight["viz"]["worst_um"], fx("2.1")["gap_um"] + 30)  # more stuck than before

    def test_2_2_the_dial_turns_the_current_down_the_battery_up(self):
        cur = [run("2.2", battery="nine_v", R=r)["viz"]["I"] for r in (0.0, 5.0, 10.0, 20.0, 40.0)]
        self.assertEqual(cur, sorted(cur, reverse=True))
        by_bat = [run("2.2", battery=b, R=10.0)["viz"]["I"] for b in ("aa", "lantern", "nine_v", "car_battery")]
        self.assertEqual(by_bat, sorted(by_bat))
        self.assertIn("too weak", run("2.2", battery="aa", R=0.0)["reason"])   # 1.5 V can't reach 0.30 A
        self.assertIn("fuse blew", run("2.2", battery="car_battery", R=0.0)["reason"])

    def test_2_3_a_wider_big_piston_pushes_harder_but_lifts_less(self):
        lifts, rides = [], []
        for d in (3.4, 3.7, 4.0, 4.4, 6.0, 10.0):
            r = run("2.3", d2=d)
            self.assertTrue(r["viz"]["reached"], d)
            lifts.append(r["viz"]["lift_cm"])
            rides.append(r["viz"]["t_down"])
        self.assertEqual(lifts, sorted(lifts, reverse=True))
        self.assertEqual(rides, sorted(rides, reverse=True))                    # more force to spare: faster
        self.assertIn("Nothing moves", run("2.3", d2=2.9)["reason"])
        self.assertIn("only rose", run("2.3", d2=6.0)["reason"])

    def test_2_4_length_and_angle_set_the_speed_the_angle_sets_the_pull(self):
        v_len = [run("2.4", length=L, angle=40.0)["predicted"] for L in (0.5, 1.0, 1.5, 2.0)]
        v_ang = [run("2.4", length=1.0, angle=a)["predicted"] for a in (20.0, 40.0, 60.0)]
        self.assertEqual(v_len, sorted(v_len))
        self.assertEqual(v_ang, sorted(v_ang))
        pulls = [run("2.4", length=1.0, angle=a)["metric"] for a in (20.0, 40.0, 60.0)]
        self.assertEqual(pulls, sorted(pulls))
        same_angle = [run("2.4", length=L, angle=50.0)["metric"] for L in (0.6, 1.2, 2.0)]
        self.assertLess(max(same_angle) - min(same_angle), 0.3)                # T = mg(3 - 2cos) whatever the length
        self.assertIn("lost its grip", run("2.4", length=1.0, angle=80.0)["reason"])


class TestThePhysics(unittest.TestCase):
    """The station numbers are the textbook laws (with the small real-world
    extras the engines add: a leaky cup, wire resistance, air drag)."""

    def test_2_1_expansion_and_heat_balance(self):
        f = fx("2.1")
        r = run("2.1", target="ring", water=0.3)
        self.assertAlmostEqual(r["viz"]["T_need"], FD.ring_needs(f["gap_um"]), places=1)
        # it lets go when the ring is hot enough to open the gap: dL = alpha L dT
        self.assertAlmostEqual(r["viz"]["T_drop"], r["viz"]["T_need"], delta=0.05)
        seated = [x for x in r["frames"] if x["y"] == round(FD.RING[1] + FD.SEAT, 4)]      # the last frame in the ring
        self.assertAlmostEqual(seated[-1]["t"], r["viz"]["t_drop"], delta=0.005)
        self.assertEqual(seated[-1]["T"], r["viz"]["T_drop"])
        # ...and it never gets hotter than the no-loss mixing temperature
        cw, ca = 4186.0, 900.0
        t_mix = (0.3 * cw * 95 + 0.3 * ca * 20) / (0.3 * cw + 0.3 * ca)
        self.assertLess(r["metric"], t_mix)

    def test_2_2_ohms_law_in_one_loop(self):
        f = fx("2.2")
        for b in FD.BATTERIES:
            for R in (0.0, 7.5, 30.0):
                r = run("2.2", battery=b["id"], R=R)
                i = b["emf"] / (R + b["r_int"] + f["coil_ohm"] + f["contacts"])
                self.assertAlmostEqual(r["viz"]["I"], i, delta=2e-3 * i + 1e-4, msg=(b["id"], R))
                self.assertAlmostEqual(r["viz"]["p_coil"], r["viz"]["I"] ** 2 * f["coil_ohm"], delta=2e-3)

    def test_2_3_pascal_and_incompressible_oil(self):
        for d in (3.5, 4.0, 4.4):
            r = run("2.3", d2=d)
            self.assertAlmostEqual(r["viz"]["lift_cm"], 30.0 * (2.0 / d) ** 2, places=1)
            self.assertAlmostEqual(r["viz"]["ratio"], (d / 2.0) ** 2, places=2)
        # it can only move if F1 * A2/A1 beats the gate + piston
        gate_w = (fx("2.3")["gate_kg"] + FD.HG["piston"]) * FD.G
        d_min = 2.0 * math.sqrt(gate_w / FD.WEIGHT)
        self.assertFalse(run("2.3", d2=math.floor(d_min * 10) / 10 - 0.1)["viz"]["reached"])

    def test_2_4_tension_at_the_bottom_and_the_flight(self):
        for L, a in ((1.0, 58.0), (1.5, 47.0), (2.0, 40.0)):
            r = run("2.4", length=L, angle=a)
            t_ideal = FD.WEIGHT * (3 - 2 * math.cos(math.radians(a)))
            self.assertAlmostEqual(r["metric"], t_ideal, delta=0.03 * t_ideal)       # drag takes a little
            d_ideal = 2 * math.sqrt(L * (1 - math.cos(math.radians(a))) * FD.DROP)
            self.assertAlmostEqual(r["viz"]["land"], d_ideal, delta=0.05 * d_ideal)

    def test_the_trapdoor_leaves_fall_away_from_the_ball(self):
        opens = [FD.door_open(t) for t in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3)]
        self.assertEqual(opens, sorted(opens))
        self.assertEqual(opens[0], 0.0)
        self.assertEqual(FD.door_open(0.5), 1.0)
        for t in (0.02, 0.05, 0.1):                                              # the free end drops faster than g
            tip = FD.DOOR_LEN * math.sin(FD.door_open(t) * math.pi / 2)
            self.assertGreater(tip, 0.5 * FD.G * t * t)


class TestAnswers(unittest.TestCase):
    def test_reference_answers_pass_and_mistakes_fail_with_the_right_reason(self):
        for st in FD.STATIONS:
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
        extra = {"2.1": {"T", "Tb"}, "2.2": {"door", "I"}, "2.3": {"x1", "x2"}, "2.4": {"th"}}
        for st in FD.STATIONS:
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
        for st in FD.STATIONS:
            a = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            b = json.dumps(run(st["id"], **st["solutions"][0]), sort_keys=True)
            self.assertEqual(a, b, st["id"])

    def test_the_slow_heating_comes_with_a_time_lapse(self):
        r = run("2.1", target="ring", water=0.3)
        (t0, t1, speed), = r["timelapse"]
        self.assertEqual(t0, 0.0)
        self.assertAlmostEqual(t1, r["viz"]["t_drop"], places=2)
        self.assertAlmostEqual(t1 / speed, FD.HEAT_SECONDS, places=2)           # ~3 s to watch, whatever it takes
        miss = run("2.1", target="ball", water=0.3)
        self.assertEqual(miss["timelapse"][0][1], FD.SHIFT)                    # the whole shift, fast
        for sid in ("2.2", "2.3", "2.4"):
            self.assertEqual(run(sid, **ST[sid]["solutions"][0]).get("timelapse", []), [])


class TestSavedSolutions(unittest.TestCase):
    def test_every_variant_has_a_working_a_mastery_and_a_top_setting(self):
        for st in FD.STATIONS:
            vs = DATA[st["id"]]["variants"]
            self.assertEqual([v["step"] for v in vs], list(range(C.VARIANT_STEPS)))
            for v in vs:
                self.assertEqual(v["facts"], C.facts_for(st, v["step"]))
                for key in ("solution", "mastery_solution", "score_solution"):
                    clean, err = C.validate_knobs(st, v[key])
                    self.assertIsNone(err)
                    self.assertEqual(clean, v[key])                              # exactly what a slider can show
                r = FD.run_station(st, v["solution"], v["step"])
                self.assertTrue(r["ok"], (st["id"], v["step"], r["reason"]))
                self.assertEqual(r["metric"], v["metric"])
                m = FD.run_station(st, v["mastery_solution"], v["step"])
                self.assertTrue(m["ok"] and m["mastery"], (st["id"], v["step"]))
                top = FD.run_station(st, v["score_solution"], v["step"])
                self.assertEqual(top["score"], v["best_score"])
                self.assertTrue(v["why"])

    def test_thresholds_mean_what_they_say(self):
        for v in DATA["2.1"]["variants"]:
            th, s = v["thresholds"], v["step"]
            self.assertTrue(FD.run_station(ST["2.1"], {"target": "ring", "water": th["water_min"]}, s)["ok"])
            self.assertFalse(FD.run_station(ST["2.1"], {"target": "ring", "water": round(th["water_min"] - 0.01, 2)},
                                            s)["ok"])
            self.assertTrue(FD.run_station(ST["2.1"], {"target": "ring", "water": th["thrifty"]}, s)["mastery"])
            self.assertFalse(FD.run_station(ST["2.1"], {"target": "ring", "water": round(th["thrifty"] + 0.01, 2)},
                                            s)["mastery"])
        for v in DATA["2.2"]["variants"]:                      # nothing that works uses less battery power
            for b in FD.BATTERIES:
                for i in range(101):
                    r = FD.run_station(ST["2.2"], {"battery": b["id"], "R": i * 0.5}, v["step"])
                    if r["ok"]:
                        self.assertGreaterEqual(r["viz"]["p_battery"], v["thresholds"]["p_min"] - 1e-9)
        for v in DATA["2.3"]["variants"]:
            top = FD.run_station(ST["2.3"], v["score_solution"], v["step"])
            self.assertEqual(top["viz"]["t_down"], v["thresholds"]["t_best"])
            self.assertEqual(v["score_solution"]["d2"], v["window"][0][1])     # the widest piston that still works

    def test_game_links_preload_the_solution(self):
        for sid, s in DATA.items():
            for v in s["variants"]:
                for link, key in (("game", "solution"), ("game_mastery", "mastery_solution"),
                                  ("game_best", "score_solution")):
                    u = urlparse(v[link][1:])
                    self.assertEqual(u.path, "/game/foundry/" + sid)
                    q = parse_qs(u.query)
                    self.assertEqual(q["practice"], ["1"])
                    self.assertEqual(int(q["v"][0]), v["step"])
                    self.assertEqual(json.loads(unquote(q["k"][0])), v[key])

    def test_the_solutions_page_lists_every_variant(self):
        with open(os.path.join(ROOT, "docs", "game", "hall2-solutions.md"), encoding="utf8") as f:
            md = f.read()
        for sid, s in DATA.items():
            for v in s["variants"]:
                self.assertIn(v["game"], md)


class TestLabLinks(unittest.TestCase):
    """Each station's "Open in the lab" link is a real set-up that reproduces
    what the station measured."""

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

    def test_2_1_the_heat_lab_reaches_the_same_temperature(self):
        for tgt, w in (("ring", 0.33), ("ring", 0.2), ("ball", 0.4), ("both", 0.5)):
            r = run("2.1", target=tgt, water=w)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "heat")
            peak = max(f["temp_b"] for f in lab["frames"] if f["t"] <= FD.SHIFT)
            self.assertAlmostEqual(peak, r["metric"], delta=0.1, msg=(tgt, w))
        self.assertEqual(run("2.1", target="ring", water=0.0)["lab"], [])          # no water: nothing to show

    def test_2_2_the_circuit_lab_carries_the_same_current(self):
        for b, R in (("lantern", 6.0), ("car_battery", 20.0), ("aa", 0.0), ("nine_v", 2.5)):
            r = run("2.2", battery=b, R=R)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "circuits")
            self.assertAlmostEqual(lab["frames"][0]["current"], r["viz"]["I"], delta=1e-3, msg=(b, R))

    def test_2_3_the_pressure_lab_lifts_the_same(self):
        for d in (3.4, 3.9, 4.4, 6.0):
            r = run("2.3", d2=d)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "pressure")
            last = lab["frames"][-1]
            self.assertTrue(lab["viz"]["reached"])
            self.assertAlmostEqual(100 * last["x2"], r["viz"]["lift_cm"], delta=0.01)
            self.assertAlmostEqual(last["t"], r["viz"]["t_down"], delta=0.02)

    def test_2_4_the_pendulum_lab_pulls_the_same(self):
        for L, a in ((1.0, 58.0), (2.0, 40.0), (0.6, 70.0)):
            r = run("2.4", length=L, angle=a)
            topic, _, lab = self.lab(r["lab"][0]["route"])
            self.assertEqual(topic, "pendulum")
            ro = {x["label"]: x["value"] for x in lab["readouts"]}
            self.assertAlmostEqual(ro["String tension at the bottom"], r["metric"], delta=0.05)
            self.assertAlmostEqual(ro["Top speed (at the bottom)"], r["predicted"], delta=0.02)


class TestVariantsAndCards(unittest.TestCase):
    def test_facts_span_the_vary_range(self):
        for st in FD.STATIONS:
            f = next(x for x in st["facts"] if "vary" in x)
            self.assertEqual(C.facts_for(st, 0)[f["id"]], f["vary"][0])
            self.assertEqual(C.facts_for(st, C.VARIANT_STEPS - 1)[f["id"]], f["vary"][1])
            self.assertEqual(C.facts_for(st, C.NOMINAL)[f["id"]], f["value"])

    def test_public_card_never_leaks_the_answer(self):
        for st in FD.STATIONS:
            blob = json.dumps(C.public_station(st, NOM))
            for key in ("solutions", "wrong", "mastery_solutions", '"run"', "thresholds", "window"):
                self.assertNotIn(key, blob, (st["id"], key))

    def test_hints_fill_in_this_players_numbers(self):
        for sid, key in (("2.1", "gap_um"), ("2.2", "coil_ohm"), ("2.3", "gate_kg"), ("2.4", "ladle")):
            f = fx(sid, 0)
            self.assertIn("%g" % f[key], FD.hint_text(ST[sid], 2, f, 0), sid)
            bp = FD.hint_text(ST[sid], 3, f, 0)
            self.assertIn("Blueprint", bp)
            for k, v in DATA[sid]["variants"][0]["solution"].items():
                self.assertIn("%s = %s" % (k, v), bp)

    def test_mastery_text_uses_this_variants_threshold(self):
        txt = FD.mastery_text(ST["2.1"], 0)
        self.assertIn("%.2f" % DATA["2.1"]["variants"][0]["thresholds"]["thrifty"], txt)
        self.assertNotIn("{", txt)


class TestScores(unittest.TestCase):
    def test_bounds_and_failures(self):
        for st in FD.STATIONS:
            for k in st["solutions"] + st["mastery_solutions"]:
                r = run(st["id"], **k)
                self.assertTrue(FD.kit.SCORE_FLOOR <= r["score"] <= FD.kit.SCORE_MAX, (st["id"], k, r["score"]))
                self.assertTrue(r["score_parts"])
            for k, _ in st["wrong"]:
                r = run(st["id"], **k)
                self.assertEqual((r["score"], r["score_parts"]), (0, []))

    def test_the_top_score_setting_of_every_variant(self):
        for sid, s in DATA.items():
            for v in s["variants"]:
                r = FD.run_station(ST[sid], v["score_solution"], v["step"])
                if sid != "2.4":                                     # 2.1-2.3: the best possible is exactly 1000
                    self.assertEqual(r["score"], 1000, (sid, v["step"]))
                else:                                                # 2.4: aim AND grip - a perfect 1000 is out of reach
                    self.assertTrue(800 < r["score"] < 1000)

    def test_2_1_water_and_time_both_cost(self):
        v = DATA["2.1"]["variants"][NOM]
        least, best = v["mastery_solution"]["water"], v["score_solution"]["water"]
        self.assertGreater(best, least)                              # the cheapest is NOT the least water...
        self.assertLess(run("2.1", target="ring", water=least)["score"], 1000)      # ...it waits too long
        self.assertLess(run("2.1", target="ring", water=0.5)["score"], 1000)        # ...that's wasted water
        r = run("2.1", target="ring", water=0.3)
        cost = FD.heat_cost(0.3, r["viz"]["t_drop"])
        self.assertAlmostEqual(r["score"], 1000 - (cost - v["thresholds"]["cost_min"]), delta=1)

    def test_2_2_less_battery_power_scores_higher(self):
        sc = [run("2.2", battery="lantern", R=r)["score"] for r in (0.0, 4.0, 8.0, 11.5)]
        self.assertEqual(sc, sorted(sc))
        self.assertLess(run("2.2", battery="car_battery", R=25.0)["score"], run("2.2", battery="lantern", R=11.5)["score"])

    def test_2_3_a_faster_ride_scores_higher(self):
        sc = [run("2.3", d2=d)["score"] for d in (3.4, 3.7, 4.0, 4.4)]
        self.assertEqual(sc, sorted(sc))

    def test_2_4_aim_and_grip(self):
        r = run("2.4", length=2.0, angle=40.0)
        land, d = r["viz"]["land"], fx("2.4")["ladle"]
        aim = 1 - (abs(land - d) / FD.LADLE_HALF) ** 2
        safe = (FD.HOLD - r["metric"]) / (FD.HOLD - FD.WEIGHT)
        self.assertEqual(r["score"], round(FD.AIM_POINTS * aim + FD.SAFE_POINTS * safe))
        gentle, rough = run("2.4", length=2.0, angle=40.0), run("2.4", length=0.8, angle=66.0)
        self.assertTrue(gentle["ok"] and rough["ok"])
        self.assertGreater(gentle["score"], rough["score"])           # a gentle swing keeps the grip


class TestMachine(unittest.TestCase):
    knobs = {sid: DATA[sid]["variants"][NOM]["solution"] for sid in DATA}

    def test_the_whole_machine_runs_from_a_to_b(self):
        m = FD.run_machine(self.knobs, {s: NOM for s in self.knobs})
        self.assertTrue(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["2.1", "2.2", "2.3", "2.4"])
        t = [f["t"] for f in m["frames"]]
        self.assertEqual(t, sorted(t))
        for a, b in zip(m["frames"], m["frames"][1:]):                           # one continuous path
            self.assertLess(math.hypot(b["x"] - a["x"], b["y"] - a["y"]), 0.5, (a, b))
        for prev, nxt in zip(m["stations"], m["stations"][1:]):
            self.assertLess(prev["t1"], nxt["t0"])
        first, last = m["frames"][0], m["frames"][-1]
        self.assertAlmostEqual(first["x"], FD.RING[0])                           # from the ring under the ore cart...
        ladle = FD.SWING[0] + fx("2.4")["ladle"]
        self.assertLess(abs(last["x"] - ladle), FD.LADLE_HALF)                  # ...into the ladle
        self.assertLess(last["y"], FD.SWING[1] - FD.DROP)
        (z0, z1, sp), = m["timelapse"]                                           # the heating, played fast
        self.assertEqual((z0, z1), (0.0, round(m["stations"][0]["result"]["timelapse"][0][1], 4)))

    def test_the_machine_stops_at_the_first_failure(self):
        knobs = dict(self.knobs, **{"2.3": {"d2": 8.0}})
        m = FD.run_machine(knobs, {s: NOM for s in knobs})
        self.assertFalse(m["ok"])
        self.assertEqual([s["id"] for s in m["stations"]], ["2.1", "2.2", "2.3"])

    def test_stations_line_up_in_the_hall(self):
        """each station starts where the one before it hands the ball over"""
        r1 = run("2.1", **self.knobs["2.1"])
        r2 = run("2.2", **self.knobs["2.2"])
        r3 = run("2.3", **self.knobs["2.3"])
        self.assertAlmostEqual(r1["frames"][-1]["y"], FD.CHUTE_Y, delta=0.02)      # down the tube
        self.assertAlmostEqual(r2["frames"][-1]["y"], r3["frames"][0]["y"], delta=0.002)   # onto the small piston
        self.assertAlmostEqual(r3["frames"][-1]["x"], FD.TUNNEL_END, places=3)       # out of the tunnel


if __name__ == "__main__":
    unittest.main()
