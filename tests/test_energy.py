"""Energy ramp: every formula and calculation, and energy conservation
through sliding, rolling, friction and flights."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import energy as E


def params(**kw):
    base = {"track": "halfpipe", "object": "box", "height": 5.0, "mass": 20.0, "friction": 0.0, "g": 9.81}
    base.update(kw)
    return base


class TestFormulas(unittest.TestCase):
    def test_speed_after_a_drop(self):
        self.assertAlmostEqual(E.speed_after_drop(9.81, 5.0, 0.0), math.sqrt(2 * 9.81 * 5.0), places=12)
        self.assertAlmostEqual(E.speed_after_drop(9.81, 5.0, 0.4), math.sqrt(2 * 9.81 * 5.0 / 1.4), places=12)
        self.assertEqual(E.speed_after_drop(9.81, -1.0, 0.0), 0.0)

    def test_normal_force(self):
        self.assertAlmostEqual(E.normal_force(2.0, 9.81, 0.0, 0.0, 5.0), 19.62, places=12)      # flat, straight
        self.assertAlmostEqual(E.normal_force(2.0, 9.81, 0.0, 0.5, 3.0), 2.0 * (9.81 + 0.5 * 9), places=12)
        s = 1.0                                                                                  # 45 deg slope
        self.assertAlmostEqual(E.normal_force(1.0, 9.81, s, 0.0, 0.0), 9.81 / math.sqrt(2), places=12)

    def test_energies_and_sticking(self):
        ket, ker, pe = E.energies(2.0, 9.81, 0.4, 3.0, 4.0)
        self.assertAlmostEqual(ket, 16.0, places=12)
        self.assertAlmostEqual(ker, 6.4, places=12)
        self.assertAlmostEqual(pe, 58.86, places=12)
        self.assertTrue(E.sticks(0.5, 0.4))
        self.assertFalse(E.sticks(0.3, 0.4))

    def test_tracks(self):
        hp, hill = E.Track("halfpipe"), E.Track("hill")
        for tr in (hp, hill):
            for x in (tr.x0 + 0.3, (tr.x0 + tr.x1) / 3, tr.x1 - 0.3):   # analytic derivatives are right
                y, d1, d2 = tr.eval(x)
                e = 1e-5
                self.assertAlmostEqual(d1, (tr.f(x + e) - tr.f(x - e)) / (2 * e), places=5)
                self.assertAlmostEqual(d2, (tr.eval(x + e)[1] - tr.eval(x - e)[1]) / (2 * e), places=4)
            for h in (0.6, 3.0, 8.0):
                self.assertAlmostEqual(tr.f(tr.start_x(h)), h, places=9)
        for x in (7.999, 8.0, 13.999, 14.0, 19.999, 20.0):                # pieces join smoothly
            self.assertAlmostEqual(hill.f(x - 1e-6), hill.f(x + 1e-6), places=4)


class TestSimulation(unittest.TestCase):
    def test_frictionless_bottom_speed_for_every_object(self):
        for obj, k in E.K.items():
            frames = E.run(params(object=obj))["frames"]
            vmax = max(abs(f["v"]) for f in frames)
            self.assertAlmostEqual(vmax, math.sqrt(2 * 9.81 * 5.0 / (1 + k)), delta=0.01, msg=obj)

    def test_energy_conserved_including_flights(self):
        for kw in ({}, {"object": "solid_ball"}, {"friction": 0.1}, {"track": "hill", "height": 8.0},
                   {"track": "hill", "height": 8.0, "object": "hollow_ball", "friction": 0.05}, {"g": 1.62}):
            r = E.run(params(**kw))
            e0 = r["viz"]["e0"]
            for f in r["frames"]:
                total = f["ke"] + f["ker"] + f["pe"] + f["heat"]
                self.assertAlmostEqual(total, e0, delta=1e-4 * e0 + 1e-4, msg=str(kw))

    def test_without_friction_it_returns_to_the_start_height_never_higher(self):
        frames = E.run(params())["frames"]
        later = [f["y"] for f in frames if f["t"] > 1.0]
        self.assertLessEqual(max(later), 5.0 + 1e-4)
        self.assertAlmostEqual(max(later), 5.0, delta=0.01)

    def test_mass_does_not_matter(self):
        a = [f["x"] for f in E.run(params(mass=1.0))["frames"]]
        b = [f["x"] for f in E.run(params(mass=80.0))["frames"]]
        self.assertEqual(a, b)

    def test_static_friction_holds_a_box_on_a_gentle_slope(self):
        tr = E.Track("halfpipe")
        slope = abs(tr.eval(tr.start_x(0.5))[1])
        r = E.run(params(height=0.5, friction=round(slope + 0.01, 2)))
        self.assertEqual(len(r["frames"]), 1)
        self.assertIn("doesn't move", r["notes"][0])

    def test_friction_turns_energy_into_heat_and_stops_it(self):
        r = E.run(params(friction=0.2))
        last = r["frames"][-1]
        self.assertGreater(last["heat"], 0.9 * r["viz"]["e0"])
        self.assertLess(abs(last["v"]), 0.05)

    def test_too_fast_over_the_hill_it_flies_and_lands(self):
        r = E.run(params(track="hill", height=8.0))
        self.assertTrue(r["viz"]["detached"])
        fly = [f for f in r["frames"] if f["fly"]]
        self.assertTrue(fly)
        self.assertGreater(r["frames"][-1]["land"], 0.0)          # the bump lost some energy
        tr = E.Track("hill")
        self.assertTrue(any(f["y"] - tr.f(f["x"]) > 1.0 for f in fly))
        self.assertFalse(E.run(params(track="hill", height=3.0))["viz"]["detached"])

    def test_normal_force_in_frames_matches_the_formula(self):
        tr = E.Track("halfpipe")
        for f in E.run(params())["frames"][::20]:
            y, d1, d2 = tr.eval(f["x"])
            self.assertAlmostEqual(f["N"], E.normal_force(20.0, 9.81, d1, d2, f["v"]), delta=0.01)


XS = [0.0, 5.0, 10.0, 15.0, 20.0, 25.0, 30.0]


class TestSplineTrack(unittest.TestCase):
    """The sandbox's student-shaped ramp: a natural cubic spline."""

    def test_passes_through_every_control_point(self):
        ys = [8.0, 1.0, 4.0, 0.5, 3.0, 0.5, 6.0]
        tr = E.SplineTrack(XS, ys)
        for x, y in zip(XS, ys):
            self.assertAlmostEqual(tr.f(x), y, places=12)

    def test_derivatives_match_finite_differences(self):
        tr = E.SplineTrack(XS, [8.0, 1.0, 4.0, 0.5, 3.0, 0.5, 6.0])
        h = 1e-5
        for x in (0.3, 4.2, 7.7, 12.5, 16.0, 23.1, 29.4):
            y, d1, d2 = tr.eval(x)
            self.assertAlmostEqual(d1, (tr.f(x + h) - tr.f(x - h)) / (2 * h), places=6)
            self.assertAlmostEqual(d2, (tr.eval(x + h)[1] - tr.eval(x - h)[1]) / (2 * h), places=5)

    def test_natural_ends_and_smooth_joins(self):
        tr = E.SplineTrack(XS, [9.0, 4.5, 1.5, 2.5, 1.0, 0.6, 0.6])
        self.assertAlmostEqual(tr.eval(0.0)[2], 0.0, places=12)           # natural: no curvature at the ends
        self.assertAlmostEqual(tr.eval(30.0)[2], 0.0, places=12)
        for x in XS[1:-1]:                                                 # C2 at every knot
            a, b = tr.eval(x - 1e-9), tr.eval(x + 1e-9)
            self.assertAlmostEqual(a[1], b[1], places=6)
            self.assertAlmostEqual(a[2], b[2], places=6)

    def test_straight_line_stays_straight(self):
        tr = E.SplineTrack(XS, [9.0 - 0.3 * x for x in XS])
        for x in (1.0, 13.0, 27.0):
            y, d1, d2 = tr.eval(x)
            self.assertAlmostEqual(y, 9.0 - 0.3 * x, places=12)
            self.assertAlmostEqual(d1, -0.3, places=12)
            self.assertAlmostEqual(d2, 0.0, places=12)

    def test_limits(self):
        self.assertEqual(E.SplineTrack(XS, [8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0]).check(3.0), [])
        self.assertIn("ground", E.SplineTrack(XS, [8.0, 5.5, 3.0, 0.6, 0.0, 0.0, 0.0]).check(3.0))
        self.assertIn("steep", E.SplineTrack(XS, [10.0, 0.0, 10.0, 0.0, 10.0, 0.0, 10.0]).check(3.0))
        self.assertAlmostEqual(E.SplineTrack(XS, [8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0]).lowest(), 0.0, places=9)

    def run_custom(self, ys, k=0.0, mu=0.0, g=9.81, m=10.0):
        tr = E.SplineTrack(XS, ys)
        return E.simulate(tr, tr.x0, m, k, mu, g, kind="custom", obj="box")

    def test_energy_conserved_on_custom_tracks_with_walls_and_flights(self):
        cases = [([8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0], 0.0, 0.0),
                 ([9.0, 4.5, 1.5, 2.5, 1.0, 0.6, 0.6], 0.0, 0.05),          # ski jump: flies, hits the wall
                 ([8.0, 1.0, 4.0, 0.5, 3.0, 0.5, 6.0], 0.4, 0.01),
                 ([8.0, 5.5, 3.2, 1.4, 0.6, 0.3, 0.3], 2.0 / 3.0, 0.002)]
        for ys, k, mu in cases:
            r = self.run_custom(ys, k, mu)
            e0 = r["viz"]["e0"]
            for f in r["frames"]:
                total = f["ke"] + f["ker"] + f["pe"] + f["heat"]
                self.assertAlmostEqual(total, e0, delta=1e-4 * e0 + 1e-4, msg=str(ys))

    def test_frictionless_bowl_returns_to_the_start_height(self):
        r = self.run_custom([8.0, 3.5, 0.9, 0.0, 0.9, 3.5, 8.0])
        later = [f["y"] for f in r["frames"] if f["t"] > 1.0]
        self.assertAlmostEqual(max(later), 8.0, delta=0.01)
        self.assertLessEqual(max(later), 8.0 + 1e-4)
        vmax = max(abs(f["v"]) for f in r["frames"])
        self.assertAlmostEqual(vmax, math.sqrt(2 * 9.81 * 8.0), delta=0.02)

    def test_padded_end_wall_returns_half_the_speed(self):
        # a slope that ends low on the right: the box hits the right wall
        r = self.run_custom([8.0, 5.5, 3.2, 1.4, 0.6, 0.3, 0.3])
        fr = r["frames"]
        i = next(j for j in range(1, len(fr)) if fr[j - 1]["v"] > 0 >= fr[j]["v"] and fr[j - 1]["x"] > 29.0)
        v_in, v_out = fr[i - 1]["v"], fr[i]["v"]
        self.assertGreater(v_in, 5.0)
        self.assertAlmostEqual(-v_out / v_in, E.WALL_E, delta=0.05)
        self.assertGreater(fr[i]["heat"], fr[i - 1]["heat"])                # the lost speed became heat


if __name__ == "__main__":
    unittest.main()
