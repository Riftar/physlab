"""Hall 3's simulation-module work (the lab teaches first):

  N2  Levers & Moments (topics/levers.py): the principle of moments, the
      pivot's friction, I alpha = tau, energy, stops, determinism
  X1  motion: a launch height (the Fan Jump's lip is 2.5 m up) and winds up
      to 20 m/s
  X3  buoyancy: a narrow well, any starting depth, stones on the bottom
  X8  optics: a screen / photocell behind the lens: blur circle, light patch
      and the share a 1 cm cell catches
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import spec, SOLIDS, FLUIDS  # noqa: E402
from physlab.server import validate  # noqa: E402
from physlab.topics import buoyancy, levers, motion, optics  # noqa: E402

G = 9.81


def lev(**kw):
    p = dict(m1=2.0, d1=0.5, m2=1.0, d2=0.8, beam=1.0, friction=0.03, start=0.0, g=G)
    p.update(kw)
    return levers.run(p)


class TestLevers(unittest.TestCase):
    def test_principle_of_moments(self):
        for m1, d1, m2, d2 in ((2.0, 0.5, 1.0, 1.0), (3.0, 0.4, 2.0, 0.6), (0.25, 1.0, 0.5, 0.5)):
            r = lev(m1=m1, d1=d1, m2=m2, d2=d2, friction=0.0)
            self.assertFalse(r["viz"]["moves"], (m1, d1, m2, d2))               # m1 d1 = m2 d2: it stays level
            self.assertEqual(r["frames"][-1]["theta"], 0.0)
            self.assertAlmostEqual(r["viz"]["balance_m2"], m2, places=9)
            self.assertIn("balanced", r["viz"]["state"])

    def test_the_heavier_turning_effect_wins(self):
        self.assertEqual(lev(d2=0.8)["viz"]["hit"], -1)                         # left 1.0 > right 0.8 kg m
        self.assertEqual(lev(d2=1.05)["viz"]["hit"], 1)
        r = lev(d2=1.05)
        self.assertAlmostEqual(r["frames"][-2]["theta"], math.radians(levers.STOP), places=6)   # stops at the stop

    def test_friction_holds_a_small_difference(self):
        # 0.02 kg m x 9.81 = 0.196 N m: less than 0.5 N m of friction -> it stays; with 0.1 N m it turns
        self.assertFalse(lev(m2=1.2, d2=0.85, friction=0.5)["viz"]["moves"])
        self.assertTrue(lev(m2=1.2, d2=0.85, friction=0.1)["viz"]["moves"])

    def test_moment_of_inertia_and_the_first_acceleration(self):
        r = lev()
        inert = 1.0 * 2.2 ** 2 / 12 + 2.0 * 0.25 + 1.0 * 0.64
        self.assertAlmostEqual(r["viz"]["inertia"], inert, places=6)
        f1 = r["frames"][1]                                                    # after 0.01 s: theta = alpha t^2 / 2
        alpha = (abs(G * (1.0 * 0.8 - 2.0 * 0.5)) - 0.03) / inert
        self.assertAlmostEqual(abs(f1["theta"]), 0.5 * alpha * f1["t"] ** 2, delta=1e-6)

    def test_energy_is_conserved(self):
        for kw in (dict(d2=1.05), dict(m1=0.26, d1=1.0, m2=0.6, d2=0.5, start=-25.0), dict(beam=5.0, d2=1.1)):
            r = lev(**kw)
            p = dict(m1=2.0, d1=0.5, m2=1.0, d2=0.8, beam=1.0, friction=0.03, start=0.0)
            p.update(kw)
            th0, th1 = math.radians(p["start"]), r["frames"][-2]["theta"]
            # the right side goes down: the right load loses m2 g d2 (sin th1 - sin th0), the left gains the same form
            dpe = G * (p["m2"] * p["d2"] - p["m1"] * p["d1"]) * (math.sin(th1) - math.sin(th0))
            ke = 0.5 * r["viz"]["inertia"] * r["viz"]["omega_hit"] ** 2
            self.assertAlmostEqual(abs(dpe) - p["friction"] * abs(th1 - th0), ke, delta=1e-3 * abs(dpe), msg=kw)

    def test_gravity_cancels_in_the_balance_but_sets_the_pace(self):
        earth, moon = lev(d2=1.05), lev(d2=1.05, g=1.62, friction=0.0)
        earth0 = lev(d2=1.05, friction=0.0)
        self.assertEqual(moon["viz"]["hit"], earth["viz"]["hit"])
        self.assertAlmostEqual(moon["viz"]["t_hit"] / earth0["viz"]["t_hit"], math.sqrt(G / 1.62), places=2)

    def test_deterministic_and_valid(self):
        self.assertEqual(lev(d2=1.05), lev(d2=1.05))
        p, err = validate(spec("levers"), {"m1": ["9"]})
        self.assertIsNone(err)
        self.assertEqual(p["m1"], 5.0)                                         # clamped to the slider
        self.assertIsNotNone(validate(spec("levers"), {"mass": ["1"]})[1])    # unknown parameter


class TestMotionLaunchHeight(unittest.TestCase):
    base = dict(v0=10.0, angle=30.0, mass=1.0, drag=0.0, wind=0.0, g=G)

    def test_height_zero_is_the_old_throw(self):
        a = motion.run(dict(self.base))
        b = motion.run(dict(self.base, height=0.0))
        self.assertEqual(a["frames"], b["frames"])
        self.assertEqual(a["readouts"], b["readouts"])

    def test_no_air_from_a_tower_matches_the_formula(self):
        for h in (2.5, 10.0, 20.0):
            r = motion.run(dict(self.base, height=h))
            vx, vy = 10 * math.cos(math.radians(30)), 10 * math.sin(math.radians(30))
            x = vx * (vy + math.sqrt(vy * vy + 2 * G * h)) / G
            self.assertAlmostEqual(r["frames"][-1]["x"], x, delta=0.002)
            self.assertEqual(r["frames"][0]["y"], h)
            self.assertAlmostEqual(r["readouts"][4]["value"], x, delta=0.001)
            self.assertAlmostEqual(r["vacuum"][-1][0], x, delta=0.001)

    def test_a_strong_tailwind_pushes_a_light_ball(self):
        calm = motion.run(dict(self.base, v0=2.0, angle=10.0, mass=0.16, drag=0.001447, height=2.5))
        gale = motion.run(dict(self.base, v0=2.0, angle=10.0, mass=0.16, drag=0.001447, height=2.5, wind=20.0))
        self.assertGreater(gale["frames"][-1]["x"] - calm["frames"][-1]["x"], 0.7)
        self.assertIsNone(validate(spec("motion"), {"wind": ["-20"], "height": ["20"]})[1])


class TestBuoyancyWell(unittest.TestCase):
    wood = next(s for s in SOLIDS if s["id"] == "woodball")
    water = next(f for f in FLUIDS if f["id"] == "water")

    def test_the_default_tank_is_unchanged(self):
        p = {"shape": "cube", "size": 12.0, "g": G, "start": 15.0}
        pine = next(s for s in SOLIDS if s["id"] == "pine")
        a = buoyancy.simulate(p, pine, self.water)
        b = buoyancy.simulate(dict(p, vessel="tank", depth=40.0, extra=0.0), pine, self.water)
        self.assertEqual(a["frames"], b["frames"])

    def test_the_well_rises_by_v_over_a(self):
        area = buoyancy.VESSELS["well"]["area"]
        for depth, extra in ((20.0, 0.0), (20.0, 1800.0), (18.0, 600.0)):
            r = buoyancy.simulate({"shape": "sphere", "size": 8.0, "g": G, "start": 10.0, "vessel": "well",
                                   "depth": depth, "extra": extra}, self.wood, self.water, t_max=10.0)
            v_sub = math.pi * 0.08 ** 3 / 6 * self.wood["rho"] / self.water["rho"]
            level = depth / 100 + (extra * 1e-6 + v_sub) / area
            self.assertAlmostEqual(r["frames"][-1]["level"], level, delta=2e-4, msg=(depth, extra))
            self.assertAlmostEqual(r["viz"]["tank"]["pile"], extra * 1e-6 / area, places=9)

    def test_too_big_for_the_well_and_overflow(self):
        p, err = validate(spec("buoyancy"), {"vessel": ["well"], "size": ["20"], "depth": ["60"],
                                             "extra": ["4000"]})
        self.assertIsNone(err)
        from physlab.topics.buoyancy import run
        r = run(p)
        self.assertTrue(any("fits down" in n for n in r["notes"]))
        self.assertTrue(any("spill" in n for n in r["notes"]))
        self.assertLessEqual(r["viz"]["size"], buoyancy.WELL_FIT["cube"] + 1e-12)


class TestOpticsScreen(unittest.TestCase):
    base = dict(kind="converging", material="crown", radius=20.0, h_o=2.0)

    def test_no_screen_no_patch(self):
        r = optics.run(dict(self.base, d_o=30.0))
        self.assertIsNone(r["viz"]["screen"])
        self.assertEqual(optics.run(dict(self.base, d_o=30.0, screen=0.0))["viz"], r["viz"])

    def test_in_focus_the_patch_is_the_image(self):
        r = optics.run(dict(self.base, d_o=30.0))
        d_i, h_i = r["viz"]["d_i"], abs(r["viz"]["h_i"])
        s = optics.run(dict(self.base, d_o=30.0, screen=d_i))["viz"]["screen"]
        self.assertLess(s["blur"], 1e-3)
        self.assertAlmostEqual(s["patch"], h_i, places=3)
        self.assertAlmostEqual(s["share"], min(1.0, (1.0 / h_i) ** 2), places=4)

    def test_blur_grows_with_the_focus_error(self):
        d_i = optics.run(dict(self.base, d_o=30.0))["viz"]["d_i"]
        blurs = [optics.run(dict(self.base, d_o=30.0, screen=d_i + e))["viz"]["screen"]["blur"] for e in (2, 5, 10)]
        self.assertEqual(blurs, sorted(blurs))
        self.assertAlmostEqual(blurs[1], 10.0 * 5 / d_i, places=3)           # D |s - d_i| / d_i
        self.assertIsNone(validate(spec("optics"), {"screen": ["26"]})[1])


if __name__ == "__main__":
    unittest.main()
