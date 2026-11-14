"""Bounces topic: physics postconditions of the drop-and-bounce engine, the
shared ball tracer it runs on, and the new lab hooks Hall 1 of the game
relies on (salt water in buoyancy, the camel track in energy)."""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import BOUNCE_BALLS, BOUNCE_SURFACES, spec  # noqa: E402
from physlab.server import validate  # noqa: E402
from physlab.topics import bounce, buoyancy, energy, tracer  # noqa: E402

BASE = {"ball": "rubber", "surface": "steel_plate", "height": 2.0, "g": 9.81, "air": True}


def run(**kw):
    return bounce.run(dict(BASE, **kw))


class TestTracer(unittest.TestCase):
    def test_free_fall_matches_the_formula_without_air(self):
        out = tracer.trace(0, 2.0, 0, 0, 1.0, 0.01, 0.0, zones=[("down", lambda x, y, vx, vy: y <= 0)])
        self.assertAlmostEqual(out["vy"], -math.sqrt(2 * 9.81 * 2.0), delta=0.01)
        self.assertAlmostEqual(out["t"], math.sqrt(2 * 2.0 / 9.81), delta=0.001)

    def test_projectile_range_without_air(self):
        v, a = 10.0, math.radians(30)
        out = tracer.trace(0, 0, v * math.cos(a), v * math.sin(a), 1.0, 0.01, 0.0,
                           zones=[("land", lambda x, y, vx, vy: vy < 0 and y <= 0)], dt=1e-4)
        self.assertAlmostEqual(out["x"], v * v * math.sin(2 * a) / 9.81, delta=0.01)

    def test_restitution_on_a_segment(self):
        out = tracer.trace(0, 1.0, 0, 0, 1.0, 0.02, 0.0, segs=[(-1, 0, 1, 0, 0.5, "floor")], stop_hits=2)
        self.assertEqual([h["name"] for h in out["hits"]], ["floor", "floor"])
        v1 = out["hits"][0]["speed"]
        self.assertAlmostEqual(v1, math.sqrt(2 * 9.81 * 0.98), delta=0.02)
        self.assertAlmostEqual(out["hits"][1]["speed"] / v1, 0.5, delta=0.01)   # it comes back with e x the speed

    def test_deterministic(self):
        a = tracer.trace(0, 1, 0.3, 2, 0.13, 0.03, 8e-4, segs=[(-1, 0, 3, 0, 0.8, "f")], stop_hits=4)
        b = tracer.trace(0, 1, 0.3, 2, 0.13, 0.03, 8e-4, segs=[(-1, 0, 3, 0, 0.8, "f")], stop_hits=4)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


class TestBounces(unittest.TestCase):
    def test_without_air_each_bounce_is_e_squared_of_the_last(self):
        for ball in ("rubber", "steel", "tennis"):
            r = run(ball=ball, air=False)
            e = r["viz"]["e"]
            for a, ideal in zip(r["viz"]["apexes"], r["viz"]["ideal"]):
                if ideal > 0.02:
                    self.assertAlmostEqual(a["h"], ideal, delta=0.005 * 2.0, msg=ball)
            self.assertAlmostEqual(r["viz"]["apexes"][0]["h"] / 2.0, e * e, delta=0.005)

    def test_air_takes_a_little_more(self):
        r = run()
        self.assertLess(r["viz"]["apexes"][0]["h"], r["viz"]["ideal"][0])
        self.assertGreater(r["viz"]["apexes"][0]["h"], 0.95 * r["viz"]["ideal"][0])

    def test_impact_speed_is_sqrt_2gh_and_mass_cancels(self):
        for ball in ("rubber", "steel"):
            v = next(x for x in run(ball=ball, air=False)["readouts"] if x["label"].startswith("Speed hitting"))
            self.assertAlmostEqual(v["value"], math.sqrt(2 * 9.81 * 2.0), delta=0.02)

    def test_the_pair_matters(self):
        h = {s["id"]: run(surface=s["id"])["viz"]["apexes"][0]["h"] for s in BOUNCE_SURFACES}
        self.assertGreater(h["steel_plate"], h["hardwood"])
        self.assertGreater(h["hardwood"], h["foam_mat"])
        self.assertGreater(h["foam_mat"], h["sand"])
        # a steel ball bounces well on steel, poorly on wood
        self.assertGreater(run(ball="steel")["viz"]["apexes"][0]["h"], 1.5)
        self.assertLess(run(ball="steel", surface="hardwood")["viz"]["apexes"][0]["h"], 0.55)

    def test_energy_is_booked(self):
        r = run()
        e0 = 0.13 * 9.81 * 2.0
        for f in r["frames"]:
            self.assertAlmostEqual(f["pe"] + f["ke"] + f["heat"], e0, delta=1e-3)
        self.assertGreater(r["frames"][-1]["heat"], 0.5 * e0)

    def test_restitution_table_is_complete_and_physical(self):
        self.assertEqual(set(bounce.RESTITUTION), {b["id"] for b in BOUNCE_BALLS})
        for row in bounce.RESTITUTION.values():
            self.assertEqual(set(row), {s["id"] for s in BOUNCE_SURFACES})
            for e in row.values():
                self.assertTrue(0 < e < 1)

    def test_registry_and_validation(self):
        p, err = validate(spec("bounce"), {"ball": ["steel"], "air": ["0"], "height": ["9"]})
        self.assertIsNone(err)
        self.assertEqual(p["height"], 4.0)                      # clamped like every topic
        self.assertFalse(p["air"])
        self.assertIsNotNone(validate(spec("bounce"), {"ball": ["lead"]})[1])


class TestLabHooksForTheGame(unittest.TestCase):
    def test_salt_water_density_and_saturation(self):
        self.assertEqual(buoyancy.brine_gain(0), 0.0)
        self.assertAlmostEqual(998.2 + buoyancy.brine_gain(250.0), 1147.6, delta=0.5)   # 20 % salt
        self.assertEqual(buoyancy.brine_gain(400.0), buoyancy.brine_gain(buoyancy.SALT_SAT))
        base = {"shape": "sphere", "material": "bouncy", "size": 6.0, "fluid": "water", "g": 9.81, "start": 10.0}
        self.assertEqual(buoyancy.run(dict(base, salt=250.0))["viz"]["eq"]["state"], "sinks")
        self.assertEqual(buoyancy.run(dict(base, salt=275.0))["viz"]["eq"]["state"], "floats")
        self.assertIn("dissolve", " ".join(buoyancy.run(dict(base, salt=400.0))["notes"]))
        oil = buoyancy.run(dict(base, fluid="oil", salt=100.0))
        self.assertIn("fresh water", " ".join(oil["notes"]))          # salt only goes into water

    def test_salt_defaults_leave_the_old_experiment_unchanged(self):
        p, err = validate(spec("buoyancy"), {})
        self.assertEqual(p["salt"], 0.0)

    def test_camel_track_crest_radius_and_flight(self):
        tr = energy.CamelTrack(1.5, 1.0)
        y, d1, d2 = tr.eval(tr.XC)
        self.assertAlmostEqual(y, 1.0, delta=0.002)
        self.assertAlmostEqual(-1.0 / d2, tr.R, delta=0.02)            # the crest's radius IS R
        p = {"track": "camel", "object": "solid_ball", "height": 1.5, "mass": 0.5, "friction": 0.01, "g": 9.81}
        fly = energy.run(dict(p, hump=0.5))
        stay = energy.run(dict(p, hump=1.0))
        self.assertTrue(any(f["fly"] for f in fly["frames"]))
        self.assertFalse(any(f["fly"] for f in stay["frames"]))
        self.assertTrue(stay["viz"]["kind"] == "camel" and stay["viz"]["crest"] == [3.5, 1.0])

    def test_spring_launch_speed(self):
        self.assertAlmostEqual(energy.spring_launch_speed(300, 0.1, 0.13, 0), 0.1 * math.sqrt(300 / 0.13), places=9)
        self.assertLess(energy.spring_launch_speed(300, 0.1, 0.13, 60), energy.spring_launch_speed(300, 0.1, 0.13, 0))
        self.assertEqual(energy.spring_launch_speed(1, 0.01, 1.0, 90), 0.0)


if __name__ == "__main__":
    unittest.main()
