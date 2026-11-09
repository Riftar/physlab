"""Floating & sinking: every formula and calculation. Geometry is checked
by numerical integration, hydrostatics by conservation laws, drag by its
known limits."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import buoyancy as B


def params(**kw):
    base = {"shape": "cube", "material": "pine", "size": 12.0, "fluid": "water",
            "g": 9.81, "start": 15.0}
    base.update(kw)
    return base


def integrate(fn, a, b, n=20000):
    h = (b - a) / n
    return sum(fn(a + (i + 0.5) * h) for i in range(n)) * h


class TestGeometry(unittest.TestCase):
    def test_volumes(self):
        self.assertAlmostEqual(B.volume("cube", 0.1), 1e-3, places=15)
        self.assertAlmostEqual(B.volume("sphere", 0.2), 4.0 / 3.0 * math.pi * 0.1 ** 3, places=15)

    def test_submerged_volume_limits_and_cap_formula(self):
        for shape in ("cube", "sphere"):
            self.assertEqual(B.sub_volume(shape, 0.2, -1.0), 0.0)
            self.assertAlmostEqual(B.sub_volume(shape, 0.2, 5.0), B.volume(shape, 0.2), places=15)
        self.assertAlmostEqual(B.sub_volume("sphere", 0.2, 0.1), B.volume("sphere", 0.2) / 2, places=15)
        r = 0.1
        for h in (0.013, 0.07, 0.15):
            num = integrate(lambda z: math.pi * (2 * r * z - z * z), 0.0, h)
            self.assertAlmostEqual(B.sub_volume("sphere", 2 * r, h), num, delta=1e-9)

    def test_waterplane(self):
        self.assertAlmostEqual(B.waterplane("sphere", 0.2, 0.1), math.pi * 0.01, places=14)
        self.assertAlmostEqual(B.waterplane("cube", 0.2, 0.05), 0.04, places=14)
        for shape in ("cube", "sphere"):
            self.assertEqual(B.waterplane(shape, 0.2, 0.0), 0.0)
            self.assertEqual(B.waterplane(shape, 0.2, 0.2), 0.0)

    def test_centre_of_buoyancy(self):
        self.assertAlmostEqual(B.sub_centroid("cube", 0.2, 0.08), 0.04, places=14)
        r = 0.1
        self.assertAlmostEqual(B.sub_centroid("sphere", 2 * r, 2 * r), r, places=14)
        self.assertAlmostEqual(B.sub_centroid("sphere", 2 * r, r), 5 * r / 8, places=14)   # hemisphere
        for h in (0.02, 0.09, 0.17):
            area = lambda z: math.pi * (2 * r * z - z * z)
            num = integrate(lambda z: z * area(z), 0, h) / integrate(area, 0, h)
            self.assertAlmostEqual(B.sub_centroid("sphere", 2 * r, h), num, delta=1e-8)

    def test_equivalent_diameter_and_sphericity(self):
        self.assertAlmostEqual(B.equivalent_diameter("sphere", 0.3), 0.3, places=14)
        d = B.equivalent_diameter("cube", 0.1)
        self.assertAlmostEqual(math.pi * d ** 3 / 6, 1e-3, places=15)
        # sphericity = sphere surface / actual surface at equal volume
        self.assertAlmostEqual(B.SPHERICITY["cube"], math.pi * d * d / (6 * 0.01), places=12)


class TestHydrostatics(unittest.TestCase):
    def test_archimedes_weight_pressure(self):
        self.assertAlmostEqual(B.buoyant_force(1000.0, 1e-3, 9.81), 9.81, places=12)
        self.assertAlmostEqual(B.weight(510.0, 1e-3, 9.81), 5.0031, places=12)
        self.assertAlmostEqual(B.gauge_pressure(1000.0, 9.81, 0.5), 4905.0, places=9)
        self.assertEqual(B.gauge_pressure(1000.0, 9.81, -0.1), 0.0)

    def test_level_conserves_liquid(self):
        for shape in ("cube", "sphere"):
            for yb in (0.0, 0.2, 0.33, 0.39, 0.6):
                level, h, vs = B.solve_level(shape, 0.25, yb)
                self.assertAlmostEqual((level - B.FILL) * B.TANK_AREA, vs, delta=1e-12)
                self.assertAlmostEqual(h, max(0.0, min(0.25, level - yb)), delta=1e-12)

    def test_float_depth_and_verdict(self):
        for shape in ("cube", "sphere"):
            for frac in (0.1, 0.5, 0.92):
                h = B.float_depth(shape, 0.2, frac)
                self.assertAlmostEqual(B.sub_volume(shape, 0.2, h), frac * B.volume(shape, 0.2), delta=1e-12)
        self.assertEqual(B.verdict(510.0, 998.0), "floats")
        self.assertEqual(B.verdict(7874.0, 998.0), "sinks")
        self.assertEqual(B.verdict(998.0, 998.0), "neutral")

    def test_equilibrium(self):
        eq = B.equilibrium("cube", 0.1, 510.0, 998.0)
        self.assertAlmostEqual(eq["fraction"], 510.0 / 998.0, places=14)
        self.assertAlmostEqual(eq["h"], 0.1 * 510.0 / 998.0, places=14)
        self.assertAlmostEqual(eq["level"], B.FILL + 510.0 / 998.0 * 1e-3 / B.TANK_AREA, places=14)
        self.assertAlmostEqual(eq["y"], eq["level"] - eq["h"], places=14)
        # at rest the liquid pushed aside weighs exactly the object's weight
        self.assertAlmostEqual(B.buoyant_force(998.0, eq["fraction"] * 1e-3, 9.81),
                               B.weight(510.0, 1e-3, 9.81), places=12)
        self.assertEqual(B.equilibrium("cube", 0.1, 7874.0, 998.0)["y"], 0.0)

    def test_bob_stiffness_includes_the_rising_level(self):
        k = B.bob_stiffness("cube", 0.2, 0.1, 1000.0, 9.81)
        self.assertAlmostEqual(k, 1000.0 * 9.81 * 0.04 / (1 - 0.04 / B.TANK_AREA), places=9)


class TestDrag(unittest.TestCase):
    def test_haider_levenspiel_sphere_coefficients(self):
        a, b, c, d = B.hl_coefficients(1.0)          # published: 0.1806, 0.6459, 0.4251, 6880.95
        self.assertAlmostEqual(a, 0.1806, delta=0.01)
        self.assertAlmostEqual(b, 0.6459, delta=0.01)
        self.assertAlmostEqual(c, 0.4251, delta=0.015)
        self.assertAlmostEqual(d / 6880.95, 1.0, delta=0.06)

    def test_sphere_drag_curve(self):
        # standard sphere drag curve, within the correlation's ~10%
        for re, ref in ((0.1, 244.0), (1.0, 26.5), (10.0, 4.1), (100.0, 1.07), (1e3, 0.46), (1e4, 0.40)):
            self.assertAlmostEqual(B.drag_coefficient(re, "sphere") / ref, 1.0, delta=0.11)
        self.assertGreater(B.drag_coefficient(1e4, "cube"), B.drag_coefficient(1e4, "sphere"))

    def test_stokes_limit_and_direction(self):
        d, mu, v = 0.05, 6.0, 1e-6
        self.assertAlmostEqual(-B.drag_force(v, "sphere", d, 1420.0, mu) / (3 * math.pi * mu * d * v), 1.0, delta=1e-3)
        self.assertGreater(B.drag_force(-0.5, "cube", 0.1, 998.0, 1e-3), 0.0)
        self.assertEqual(B.drag_force(0.0, "cube", 0.1, 998.0, 1e-3), 0.0)
        self.assertAlmostEqual(B.reynolds(1000.0, -2.0, 0.1, 1e-3), 2e5, places=6)

    def test_terminal_speed_balances_drag(self):
        vt = B.terminal_speed("sphere", 0.12, 7874.0, 1420.0, 6.0, 9.81)
        f = (7874.0 - 1420.0) * B.volume("sphere", 0.12) * 9.81
        self.assertAlmostEqual(-B.drag_force(vt, "sphere", 0.12, 1420.0, 6.0), f, delta=1e-6 * f)
        # creeping flow: Stokes' law v = 2 (drho) g r^2 / (9 mu)
        r = 0.0025
        vs = 2 * (1420.0 - 1100.0) * 9.81 * r * r / (9 * 6.0)
        self.assertAlmostEqual(B.terminal_speed("sphere", 2 * r, 1100.0, 1420.0, 6.0, 9.81) / vs, 1.0, delta=0.01)


class TestSimulation(unittest.TestCase):
    def test_floaters_come_to_rest_at_the_archimedes_depth(self):
        for kw in ({}, {"shape": "sphere"}, {"material": "cork", "size": 4.0, "fluid": "mercury"},
                   {"material": "iron", "fluid": "mercury"}, {"material": "rubber", "fluid": "honey", "start": -25.0}):
            r = B.run(params(**kw))
            last, eq = r["frames"][-1], r["viz"]["eq"]
            self.assertEqual(eq["state"], "floats", kw)
            self.assertAlmostEqual(last["y"], eq["y"], delta=2e-4, msg=str(kw))
            self.assertAlmostEqual(last["fb"], r["viz"]["weight"], delta=0.01 * r["viz"]["weight"])

    def test_sinkers_rest_on_the_floor_with_apparent_weight(self):
        for kw in ({"material": "iron"}, {"material": "gold", "fluid": "mercury", "shape": "sphere", "size": 30.0},
                   {"material": "aluminum", "fluid": "honey"}):
            r = B.run(params(**kw))
            last, vz = r["frames"][-1], r["viz"]
            self.assertEqual(last["y"], 0.0)
            self.assertAlmostEqual(last["fn"], vz["weight"] - vz["fb_full"], delta=1e-3 * vz["weight"])

    def test_liquid_is_conserved_in_every_frame(self):
        for f in B.run(params(shape="sphere", material="ice", size=25.0))["frames"]:
            self.assertAlmostEqual((f["level"] - B.FILL) * B.TANK_AREA, f["vsub"], delta=2e-9)

    def test_pressure_difference_is_the_buoyancy(self):
        # fully under: (p_bottom - p_top) x face area = rho V g exactly
        r = B.run(params(material="iron"))
        s = 0.12
        for f in r["frames"]:
            if f["h"] >= s - 1e-9 and f["p_top"] > 0:
                self.assertAlmostEqual((f["p_bot"] - f["p_top"]) * s * s, f["fb"], delta=2e-3)

    def test_centre_of_buoyancy_sits_in_the_submerged_part(self):
        for f in B.run(params(shape="sphere"))["frames"]:
            if f["h"] > 0:
                self.assertGreaterEqual(f["zb"], f["y"] - 1e-9)
                self.assertLessEqual(f["zb"], f["y"] + f["h"] + 1e-9)

    def test_gravity_does_not_change_the_floating_depth(self):
        earth = B.run(params())["frames"][-1]["y"]
        moon = B.run(params(g=1.6))["frames"][-1]["y"]
        self.assertAlmostEqual(earth, moon, delta=3e-4)

    def test_small_bobs_follow_the_bobbing_period(self):
        eq = B.equilibrium("cube", 0.12, 510.0, 998.0)
        start = (eq["y"] + 0.06 - B.FILL) * 100.0 + 0.5        # 5 mm above rest
        r = B.run(params(start=start))
        fr = r["frames"]
        ups = []
        for a, b in zip(fr, fr[1:]):
            da, db = a["y"] - eq["y"], b["y"] - eq["y"]
            if da < 0 <= db:
                ups.append(a["t"] + (b["t"] - a["t"]) * (-da / (db - da)))
        measured = (ups[-1] - ups[0]) / (len(ups) - 1)
        t0 = B.bob_period("cube", 0.12, 510.0, 998.0, 9.81)
        self.assertAlmostEqual(measured / t0, 1.0, delta=0.03)

    def test_frames_in_time_order_and_readouts(self):
        r = B.run(params())
        ts = [f["t"] for f in r["frames"]]
        self.assertTrue(all(b > a for a, b in zip(ts, ts[1:])))
        self.assertEqual(r["readouts"][2]["value"], "FLOATS")
        self.assertEqual(B.run(params(material="iron"))["readouts"][2]["value"], "SINKS")

    def test_notes(self):
        self.assertIn("Mercury", " ".join(B.run(params(fluid="mercury"))["notes"]))
        self.assertIn("Honey", " ".join(B.run(params(fluid="honey"))["notes"]))
        self.assertIn("Gravity", " ".join(B.run(params(g=1.6))["notes"]))
        self.assertIn("sinks", " ".join(B.run(params(material="iron"))["notes"]))


if __name__ == "__main__":
    unittest.main()
