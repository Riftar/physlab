"""Learning content stays complete and TRUE: every formula is explained,
every figure's set-up is a valid simulation, its screenshot exists, its
callouts sit inside the picture - and the key numbers quoted in the text
match what the physics engine actually computes."""

import glob
import math
import os
import struct
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab import TOPICS, spec  # noqa: E402
from physlab.learn import LEARN, CANVAS_W, CANVAS_H, figure_route  # noqa: E402
from physlab.server import validate, RUNNERS  # noqa: E402
from physlab.topics import circuits, motion, heat, buoyancy, waves, pendulum, optics, pressure, energy  # noqa: E402

READY = [t for t in TOPICS if t["status"] == "ready"]
JS = "\n".join(open(p, encoding="utf8").read() for p in glob.glob(os.path.join(ROOT, "www", "js", "*.js")))


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    assert head[:8] == b"\x89PNG\r\n\x1a\n", path
    return struct.unpack(">II", head[16:24])


def run_set(topic, params):
    p, err = validate(spec(topic), {k: [str(v).lower() if isinstance(v, bool) else str(v)]
                                    for k, v in params.items()})
    assert err is None, err
    return RUNNERS[topic](p)


class TestStructure(unittest.TestCase):
    def test_every_ready_topic_has_content(self):
        for t in READY:
            self.assertIn("learn", t, t["id"])
            L = t["learn"]
            self.assertGreater(len(L["big_idea"]), 80, t["id"])
            self.assertGreaterEqual(len(L["figures"]), 3, t["id"])
            self.assertGreaterEqual(len(L["real_life"]), 4, t["id"])

    def test_every_formula_is_explained_and_nothing_stale(self):
        for t in READY:
            exprs = {f["expr"] for f in t["formulas"]}
            self.assertEqual(set(LEARN[t["id"]]["formulas"]), exprs, t["id"])
            for expr, x in LEARN[t["id"]]["formulas"].items():
                for key in ("say", "explain", "try_it"):
                    self.assertTrue(x.get(key, "").strip(), (t["id"], expr, key))
                self.assertGreaterEqual(len(x["symbols"]), 2, expr)
                for row in x["symbols"]:
                    self.assertEqual(len(row), 3, row)
                    self.assertTrue(row[0].strip() and row[1].strip(), row)

    def test_real_life_links_point_at_real_formulas(self):
        for t in READY:
            exprs = {f["expr"] for f in t["formulas"]}
            for u in t["learn"]["real_life"]:
                self.assertTrue(u["icon"] and u["title"] and len(u["text"]) > 40, u)
                if u.get("formula"):
                    self.assertIn(u["formula"], exprs, (t["id"], u["title"]))


class TestFigures(unittest.TestCase):
    def test_images_exist_with_canvas_size(self):
        for t in READY:
            for i, fig in enumerate(t["learn"]["figures"]):
                path = os.path.join(ROOT, "www", fig["img"])
                self.assertTrue(os.path.isfile(path), path)
                self.assertEqual(png_size(path), (CANVAS_W, CANVAS_H), path)
                self.assertEqual(fig["img"], "learn/%s_%d.png" % (t["id"], i + 1))

    def test_callouts_inside_the_picture(self):
        for t in READY:
            for fig in t["learn"]["figures"]:
                self.assertGreaterEqual(len(fig["callouts"]), 3, fig["title"])
                self.assertTrue(fig["title"] and fig["caption"])
                for c in fig["callouts"]:
                    self.assertTrue(0 <= c["x"] <= CANVAS_W and 0 <= c["y"] <= CANVAS_H, (fig["title"], c))
                    self.assertTrue(len(c["text"]) > 10)

    def test_set_ups_are_valid_and_unclamped(self):
        for t in READY:
            for fig in t["learn"]["figures"]:
                for params in [fig.get("params", {})] + ([dict(fig["params"], **fig["b"])] if "b" in fig else []):
                    q = {k: [str(v)] for k, v in params.items()}
                    p, err = validate(spec(t["id"]), q)
                    self.assertIsNone(err, (t["id"], fig["title"]))
                    for k, v in params.items():
                        self.assertEqual(p[k], v, (t["id"], fig["title"], k))   # not clamped
                if "b" in fig:
                    self.assertTrue(t.get("compare"), t["id"])

    def test_moments_exist_in_the_run(self):
        for t in READY:
            for fig in t["learn"]["figures"]:
                sets = [fig.get("params", {})]
                if "b" in fig:
                    sets.append(dict(fig["params"], **fig["b"]))
                end = max(run_set(t["id"], s)["frames"][-1]["t"] for s in sets)
                self.assertGreaterEqual(fig["at"], 0.0)
                self.assertLessEqual(fig["at"], end + 1.0, (t["id"], fig["title"], end))

    def test_view_options_exist_in_the_scenes(self):
        for t in READY:
            for fig in t["learn"]["figures"]:
                for k, v in fig.get("view", {}).items():
                    self.assertIn('id: "%s"' % k, JS, (t["id"], k))
                    self.assertIn('id: "%s"' % v, JS, (t["id"], v))

    def test_routes(self):
        r = figure_route("motion", {"params": {"angle": 30.0}, "b": {"angle": 60.0}, "view": {}, "at": 3.2})
        self.assertEqual(r, "#/motion?angle=30.0&cmp=1&b.angle=60.0&at=3.2")
        for t in READY:
            for fig in t["learn"]["figures"]:
                self.assertTrue(fig["route"].startswith("#/" + t["id"]))


class TestPresets(unittest.TestCase):
    def test_every_topic_has_presets_that_run_unclamped_on_the_slider_grid(self):
        for t in READY:
            pres = t["learn"]["presets"]
            self.assertGreaterEqual(len(pres), 4, t["id"])
            titles = [p["title"] for p in pres]
            self.assertEqual(len(titles), len(set(titles)), t["id"])
            routes = [p["route"] for p in pres]
            self.assertEqual(len(routes), len(set(routes)), (t["id"], "duplicate set-ups"))
            specs = {p["id"]: p for p in t["params"]}
            for pr in pres:
                self.assertNotIn("at=", pr["route"])
                sets = [pr.get("params", {})] + ([dict(pr["params"], **pr["b"])] if "b" in pr else [])
                for params in sets:
                    q = {k: [("1" if v else "0") if isinstance(v, bool) else str(v)] for k, v in params.items()}
                    p, err = validate(spec(t["id"]), q)
                    self.assertIsNone(err, (t["id"], pr["title"]))
                    for k, v in params.items():
                        self.assertEqual(p[k], v, (t["id"], pr["title"], k))
                        sp = specs[k]
                        if sp["kind"] == "number":          # a slider can show exactly this value
                            steps = (v - sp["min"]) / sp["step"]
                            self.assertAlmostEqual(steps, round(steps), delta=1e-6,
                                                   msg=(t["id"], pr["title"], k, v))
                for k, v in pr.get("view", {}).items():
                    self.assertIn('id: "%s"' % v, JS)


class TestTheTextIsTrue(unittest.TestCase):
    """Numbers quoted in explanations and callouts, recomputed."""

    def test_circuits_numbers(self):
        base = {"voltage": 6.0, "lamps": 1, "lamp_r": 20.0, "internal_r": 0.5, "resistor": 0.0, "closed": True}
        one = circuits.solve(base)
        two = circuits.solve(dict(base, lamps=2))
        three = circuits.solve(dict(base, lamps=3))
        hot = circuits.solve(dict(base, voltage=12.0))
        self.assertEqual(round(one["current"], 3), 0.293)
        self.assertEqual(round(one["lamp_power"], 2), 1.71)
        self.assertEqual(round(two["current"], 3), 0.148)
        self.assertEqual(round(two["lamp_power"], 2), 0.44)
        self.assertEqual(round(two["filament_k"]), 1898)
        self.assertAlmostEqual(two["lumens"] / one["lumens"], 0.02, delta=0.005)     # "about 2%"
        self.assertEqual(round(three["current"], 3), 0.099)
        self.assertAlmostEqual(three["filament_k"], 1550, delta=10)
        self.assertEqual(round(hot["filament_k"]), 3771)
        self.assertEqual(round(hot["lumens"]), 322)
        self.assertAlmostEqual(hot["lumens"] / one["lumens"], 16, delta=0.5)          # "16x the light"

    def test_motion_numbers(self):
        base = {"v0": 18.0, "angle": 45.0, "mass": 1.0, "drag": 0.0, "wind": 0.0, "g": 9.81}
        a = motion.run(dict(base, angle=30.0))["frames"][-1]
        b = motion.run(dict(base, angle=60.0))["frames"][-1]
        self.assertEqual(round(a["x"], 2), 28.60)
        self.assertEqual(round(b["x"], 2), 28.60)
        self.assertEqual(round(a["t"], 2), 1.83)
        self.assertEqual(round(b["t"], 2), 3.18)
        self.assertAlmostEqual(18 * math.cos(math.radians(45)), 12.7, delta=0.05)

    def test_heat_numbers(self):
        r = heat.run({"material_a": "water", "mass_a": 1.0, "temp_a": 90.0, "material_b": "iron",
                      "mass_b": 1.0, "temp_b": 20.0, "ambient": 25.0, "loss": 0.0})
        self.assertEqual(round(r["readouts"][2]["value"], 1), 83.2)
        self.assertEqual(round(90 - r["frames"][-1]["temp_a"], 1), 6.8)
        self.assertAlmostEqual(r["frames"][-1]["temp_b"] - 20, 63, delta=0.5)

    def test_buoyancy_numbers(self):
        pine = buoyancy.equilibrium("cube", 0.12, 510.0, 998.0)
        ice = buoyancy.equilibrium("sphere", 0.25, 917.0, 998.0)
        self.assertEqual(round(100 * pine["fraction"]), 51)
        self.assertEqual(round(100 * ice["fraction"]), 92)
        self.assertEqual(round(100 * 917.0 / 1025.0), 89)                             # iceberg in sea water
        self.assertEqual(round(100 * buoyancy.equilibrium("cube", 0.12, 510.0, 1420.0)["fraction"]), 36)
        self.assertAlmostEqual(7874.0 / 240.0, 33, delta=0.5)                         # "cork 33x less dense"
        self.assertAlmostEqual(7874.0 / 510.0, 15, delta=0.5)                         # "weight jumps 15x"

    def test_waves_numbers(self):
        v = waves.wave_speed(20.0, 0.2)
        self.assertEqual(v, 10.0)
        self.assertEqual(waves.wavelength(v, 2.5), 4.0)
        self.assertAlmostEqual(waves.resonances(v, 4.0, "fixed")[1], 2.5)
        r = waves.run({"f": 2.5, "amplitude": 3.0, "tension": 20.0, "mu": 200.0, "length": 4.0,
                       "end": "fixed", "damping": 1.0})
        self.assertAlmostEqual(max(r["viz"]["envelope"]) / 0.03, 5.0, delta=0.3)     # "five times"
        self.assertEqual(r["viz"]["nodes"], [2.0])

    def test_optics_numbers(self):
        f = optics.focal_length(1.52, 20.0, "converging")
        self.assertEqual(round(f, 1), 19.2)
        self.assertEqual(round(optics.image_distance(f, 30.0), 1), 53.6)
        self.assertEqual(round(optics.magnification(30.0, optics.image_distance(f, 30.0)), 2), -1.79)
        di = optics.image_distance(f, 12.0)
        self.assertEqual(round(di, 1), -31.9)
        self.assertEqual(round(optics.magnification(12.0, di), 2), 2.66)
        self.assertEqual(round(optics.run({"kind": "converging", "material": "crown", "radius": 20.0,
                                           "d_o": 30.0, "h_o": 4.0})["viz"]["focus"][0], 1), 51.5)
        self.assertAlmostEqual(100 / 1.52, 66, delta=0.5)                              # "66% of its top speed"
        self.assertAlmostEqual(optics.focal_length(1.333, 20.0, "converging") /
                               optics.focal_length(2.417, 20.0, "converging"), 4.26, delta=0.01)  # "more than 4x"
        self.assertAlmostEqual(optics.magnification(38.5, optics.image_distance(f, 38.5)), -1.0, delta=0.01)

    def test_pressure_numbers(self):
        base = {"force": 150.0, "d1": 3.0, "d2": 30.0, "mass": 1000.0, "stroke": 25.0, "fluid": "oil"}
        r = pressure.run(base)
        self.assertEqual(round(r["viz"]["p_push"] / 1000, 0), 212)
        self.assertEqual(round(r["viz"]["f2"]), 15000)
        self.assertEqual(round(r["frames"][-1]["x2"] * 1000, 1), 2.5)
        w = r["frames"][-1]
        self.assertEqual(round(w["w_in"], 1), 25.2)
        weak = pressure.run(dict(base, force=80.0))["viz"]
        self.assertEqual(round(weak["p_push"] / 1000), 113)
        self.assertEqual(round(weak["need"] / pressure.area(3.0) / 1000), 139)
        eq = pressure.run({"force": 100.0, "d1": 10.0, "d2": 12.0, "mass": 10.0, "stroke": 25.0, "fluid": "oil"})
        self.assertEqual(round(eq["viz"]["ratio"], 2), 1.44)
        f15 = [f for f in eq["frames"] if abs(f["t"] - 1.5) < 0.011][0]
        self.assertAlmostEqual(f15["x1"] * 100, 10.7, delta=0.1)
        self.assertAlmostEqual(f15["x2"] * 1000, 74, delta=1)
        self.assertAlmostEqual(f15["w_in"], 8.1, delta=0.05)

    def test_energy_numbers(self):
        base = {"track": "halfpipe", "object": "box", "height": 5.0, "mass": 20.0, "friction": 0.0, "g": 9.81}
        self.assertEqual(round(energy.run(base)["viz"]["e0"]), 981)
        self.assertAlmostEqual(0.4 / 1.4, 2.0 / 7.0, places=12)                       # "2/7 into spinning"
        six = energy.run(dict(base, height=6.0))
        ball = energy.run(dict(base, height=6.0, object="solid_ball"))
        pick = lambda r: [f for f in r["frames"] if abs(f["t"] - 1.2) < 0.02][0]
        self.assertAlmostEqual(abs(pick(six)["v"]), 9.57, delta=0.05)
        self.assertAlmostEqual(abs(pick(ball)["v"]), 7.01, delta=0.05)
        self.assertTrue(energy.run(dict(base, track="hill", height=8.0))["viz"]["detached"])

    def test_pendulum_numbers(self):
        t1 = pendulum.exact_period(1.0, 9.81, math.radians(20))
        tq = pendulum.exact_period(0.25, 9.81, math.radians(20))
        self.assertAlmostEqual(t1 / tq, 2.0, places=9)
        self.assertEqual(round(t1, 3), 2.021)
        self.assertEqual(round(tq, 3), 1.011)
        t0 = pendulum.small_angle_period(1.0, 9.81)
        for deg, pct in ((20, 0.8), (60, 7), (90, 18)):
            self.assertAlmostEqual(100 * (pendulum.exact_period(1.0, 9.81, math.radians(deg)) / t0 - 1), pct,
                                   delta=0.5)
        self.assertAlmostEqual(pendulum.small_angle_period(1.0, 1.62), 5.0, delta=0.1)   # "about 5 s on the Moon"
        self.assertAlmostEqual(pendulum.max_speed(1.0, 9.81, math.radians(40)), 2.14, delta=0.01)


if __name__ == "__main__":
    unittest.main()
