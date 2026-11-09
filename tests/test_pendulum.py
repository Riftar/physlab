"""Pendulum: every formula and calculation, checked against independent
references (known constants, series, conservation laws)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import pendulum as P


def params(**kw):
    base = {"length": 1.0, "amplitude": 20.0, "mass": 1.0, "g": 9.81, "drag": 0.0}
    base.update(kw)
    return base


class TestFormulas(unittest.TestCase):
    def test_small_angle_period(self):
        self.assertAlmostEqual(P.small_angle_period(1.0, 9.81), 2 * math.pi / math.sqrt(9.81), places=12)
        # four times the length -> twice the period; a quarter of g -> twice too
        self.assertAlmostEqual(P.small_angle_period(4.0, 9.81), 2 * P.small_angle_period(1.0, 9.81), places=12)
        self.assertAlmostEqual(P.small_angle_period(1.0, 9.81 / 4), 2 * P.small_angle_period(1.0, 9.81), places=12)

    def test_agm_known_values(self):
        self.assertAlmostEqual(P.agm(1.0, 1.0), 1.0, places=15)
        # Gauss: AGM(1, sqrt 2) = 1.19814023473559...
        self.assertAlmostEqual(P.agm(1.0, math.sqrt(2.0)), 1.1981402347355922, places=13)
        self.assertAlmostEqual(P.agm(3.0, 7.0), P.agm(7.0, 3.0), places=14)

    def test_exact_period_at_90_degrees(self):
        # T/T0 = 2 K(1/sqrt2) / pi = 1.18034059901...
        r = P.exact_period(1.0, 9.81, math.pi / 2) / P.small_angle_period(1.0, 9.81)
        self.assertAlmostEqual(r, 1.1803405990161, places=10)

    def test_exact_period_matches_series_for_moderate_angles(self):
        for deg in (1, 5, 10, 20, 30):
            th = math.radians(deg)
            series = (1 + th ** 2 / 16 + 11 * th ** 4 / 3072 + 173 * th ** 6 / 737280
                      + 22931 * th ** 8 / 1321205760)
            r = P.exact_period(2.0, 9.81, th) / P.small_angle_period(2.0, 9.81)
            self.assertAlmostEqual(r, series, delta=1e-8)

    def test_exact_period_grows_with_angle(self):
        prev = 0.0
        for deg in (2, 10, 30, 60, 90):
            t = P.exact_period(1.0, 9.81, math.radians(deg))
            self.assertGreater(t, prev)
            prev = t

    def test_max_speed_from_energy(self):
        L, g, th = 1.5, 9.81, math.radians(40)
        v = P.max_speed(L, g, th)
        self.assertAlmostEqual(0.5 * v * v, g * L * (1 - math.cos(th)), places=12)

    def test_tension_restoring_energies_position(self):
        m, g, L = 2.0, 9.81, 1.2
        self.assertAlmostEqual(P.tension(m, g, L, 0.0, 0.0), m * g, places=12)
        self.assertAlmostEqual(P.tension(m, g, L, 0.3, 1.1), m * (g * math.cos(0.3) + L * 1.21), places=12)
        self.assertAlmostEqual(P.restoring_force(m, g, math.pi / 6), m * g * 0.5, places=12)
        ke, pe = P.energies(m, g, L, math.pi / 3, 2.0)
        self.assertAlmostEqual(ke, 0.5 * m * (L * 2.0) ** 2, places=12)
        self.assertAlmostEqual(pe, m * g * L * 0.5, places=12)
        x, y = P.bob_position(L, 0.7)
        self.assertAlmostEqual(x * x + y * y, L * L, places=12)
        self.assertLess(y, 0)

    def test_measured_period_helper(self):
        ts = [i * 0.001 for i in range(5000)]
        ys = [math.sin(2 * math.pi * t / 0.8 + 0.3) for t in ts]
        self.assertAlmostEqual(P.measured_period(ts, ys), 0.8, delta=1e-6)
        self.assertIsNone(P.measured_period([0, 1], [1, 2]))


class TestSimulation(unittest.TestCase):
    def test_measured_period_matches_exact_formula(self):
        for deg in (5, 45, 90):
            r = P.run(params(amplitude=float(deg)))
            exact = P.exact_period(1.0, 9.81, math.radians(deg))
            meas = r["readouts"][2]["value"]
            self.assertAlmostEqual(meas, exact, delta=2e-4 * exact)

    def test_energy_conserved_without_drag(self):
        frames = P.run(params(amplitude=70.0))["frames"]
        e = [f["ke"] + f["pe"] for f in frames]
        self.assertLess(max(e) - min(e), 1e-6 * e[0])

    def test_drag_removes_energy_monotonically(self):
        frames = P.run(params(amplitude=60.0, drag=0.01))["frames"]
        e = [f["ke"] + f["pe"] for f in frames]
        self.assertTrue(all(b <= a + 2e-6 for a, b in zip(e, e[1:])))     # frames round to 1e-6 J
        self.assertLess(e[-1], 0.9 * e[0])

    def test_mass_does_not_change_the_swing_without_drag(self):
        a = [f["theta"] for f in P.run(params(mass=0.1))["frames"]]
        b = [f["theta"] for f in P.run(params(mass=5.0))["frames"]]
        self.assertEqual(a, b)

    def test_with_drag_the_heavier_bob_keeps_swinging_longer(self):
        light = P.run(params(mass=0.1, drag=0.01, amplitude=40.0))["frames"][-1]
        heavy = P.run(params(mass=5.0, drag=0.01, amplitude=40.0))["frames"][-1]
        e_light = (light["ke"] + light["pe"]) / (0.1 * 9.81 * (1 - math.cos(math.radians(40))))
        e_heavy = (heavy["ke"] + heavy["pe"]) / (5.0 * 9.81 * (1 - math.cos(math.radians(40))))
        self.assertGreater(e_heavy, e_light)

    def test_frame_fields_are_consistent(self):
        p = params(amplitude=50.0, drag=0.005)
        for f in P.run(p)["frames"]:
            self.assertAlmostEqual(f["v"], p["length"] * f["omega"], delta=2e-5)
            self.assertAlmostEqual(f["x"], p["length"] * math.sin(f["theta"]), delta=2e-5)
            self.assertAlmostEqual(f["tension"], P.tension(1.0, 9.81, 1.0, f["theta"], f["omega"]), delta=2e-4)
            self.assertAlmostEqual(f["f_restore"], 9.81 * math.sin(f["theta"]), delta=2e-4)
            self.assertAlmostEqual(f["f_drag"], -0.005 * f["v"] * abs(f["v"]), delta=2e-5)

    def test_tension_at_the_bottom_is_mg_3_minus_2cos(self):
        th0 = math.radians(60)
        frames = P.run(params(amplitude=60.0))["frames"]
        peak = max(f["tension"] for f in frames)
        self.assertAlmostEqual(peak, 9.81 * (3 - 2 * math.cos(th0)), delta=0.02)

    def test_swings_are_counted(self):
        r = P.run(params())
        self.assertEqual(r["frames"][-1]["swings"], 2 * P.PERIODS)

    def test_notes(self):
        self.assertEqual(P.run(params())["notes"], [])
        self.assertIn("Big swing", " ".join(P.run(params(amplitude=60.0))["notes"]))
        self.assertIn("drag", " ".join(P.run(params(drag=0.01))["notes"]))



class TestWind(unittest.TestCase):
    """Sandbox weather: wind blowing from the left (+x) pushes on the bob."""
    K = 0.5 * 1.225 * 0.50 * math.pi * 0.02 ** 2          # ping-pong ball: 1/2 rho Cd A

    def test_air_force_without_wind_is_plain_drag(self):
        for th, om in ((0.3, 1.2), (-0.7, -2.0), (0.0, 0.5)):
            ft, fr = P.air_force(0.01, 1.5, th, om, 0.0)
            v = 1.5 * om
            self.assertAlmostEqual(ft, -0.01 * v * abs(v), places=12)
            self.assertAlmostEqual(fr, 0.0, places=12)

    def test_air_force_on_a_bob_at_rest(self):
        ft, fr = P.air_force(0.02, 1.0, 0.0, 0.0, 10.0)      # hanging straight down: wind is along the swing
        self.assertAlmostEqual(ft, 0.02 * 100.0, places=12)
        self.assertAlmostEqual(fr, 0.0, places=12)
        th = math.radians(40)                                 # tilted: part of the push is along the string
        ft, fr = P.air_force(0.02, 1.0, th, 0.0, 10.0)
        self.assertAlmostEqual(ft, 2.0 * math.cos(th), places=12)
        self.assertAlmostEqual(fr, 2.0 * math.sin(th), places=12)

    def test_lean_angle(self):
        self.assertAlmostEqual(P.lean_angle(0.02, 10.0, 1.0, 9.81), math.atan2(2.0, 9.81), places=12)
        self.assertAlmostEqual(P.lean_angle(0.02, -10.0, 1.0, 9.81), -math.atan2(2.0, 9.81), places=12)

    def test_zero_wind_is_the_ordinary_pendulum(self):
        a = P.run(params(drag=0.01))
        b = P.run(params(drag=0.01, wind=0.0))
        self.assertEqual(a, b)

    def test_light_bob_settles_at_the_lean_angle(self):
        m, g, w = 0.0027, 9.81, 15.0
        r = P.run(params(mass=m, drag=self.K, wind=w))
        lean = P.lean_angle(self.K, w, m, g)
        self.assertAlmostEqual(math.degrees(lean), 73.0, delta=0.1)
        self.assertAlmostEqual(r["frames"][-1]["theta"], lean, delta=math.radians(0.5))
        self.assertAlmostEqual(r["viz"]["lean"], lean, places=5)

    def test_period_about_the_lean_uses_the_effective_gravity(self):
        m, g, w = 0.0027, 9.81, 8.0
        r = P.run(params(mass=m, drag=self.K, wind=w, amplitude=5.0))
        g_eff = math.hypot(g, self.K * w * w / m)
        t_est = 2 * math.pi * math.sqrt(1.0 / g_eff)
        self.assertAlmostEqual(r["viz"]["period_wind"], t_est, places=5)
        measured = [x["value"] for x in r["readouts"] if x["label"] == "Period, measured in the run"][0]
        # the wind also damps the swing, which lengthens the period a little
        self.assertGreater(measured, t_est)
        self.assertLess(measured, 1.1 * t_est)

    def test_heavy_bob_hardly_notices(self):
        k = 0.5 * 1.225 * 0.47 * math.pi * 0.03 ** 2      # brass bob, 6 cm
        self.assertLess(math.degrees(P.lean_angle(k, 15.0, 0.96, 9.81)), 1.2)

    def test_tension_includes_the_wind_push_along_the_string(self):
        r = P.run(params(mass=0.0027, drag=self.K, wind=15.0))
        for f in r["frames"][::25]:
            base = P.tension(0.0027, 9.81, 1.0, f["theta"], f["omega"])
            self.assertAlmostEqual(f["tension"], base + f["f_air_r"], delta=2e-5)


if __name__ == "__main__":
    unittest.main()
