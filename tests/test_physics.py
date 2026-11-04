"""Physics postconditions: closed forms, conservation, monotonicity."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import circuits, motion, heat


class TestCircuits(unittest.TestCase):
    def p(self, **kw):
        base = {"voltage": 6.0, "lamps": 1, "lamp_r": 20.0,
                "internal_r": 0.5, "resistor": 0.0, "closed": True}
        base.update(kw)
        return base

    def test_ohms_law_single_loop(self):
        s = circuits.solve(self.p())
        self.assertAlmostEqual(s["current"], 6.0 / 20.5, places=9)

    def test_series_lamps_reduce_current(self):
        one = circuits.solve(self.p(lamps=1))["current"]
        two = circuits.solve(self.p(lamps=2))["current"]
        three = circuits.solve(self.p(lamps=3))["current"]
        self.assertTrue(one > two > three > 0)
        self.assertAlmostEqual(two, one * 20.5 / 40.5, places=9)

    def test_open_switch_means_zero_current(self):
        s = circuits.solve(self.p(closed=False))
        self.assertEqual(s["current"], 0.0)
        self.assertEqual(s["brightness"], 0.0)

    def test_brightness_bounded_and_monotonic_in_voltage(self):
        prev = -1.0
        for v in (1.5, 3.0, 6.0, 9.0, 12.0):
            b = circuits.solve(self.p(voltage=v))["brightness"]
            self.assertLessEqual(b, 1.0)
            self.assertGreaterEqual(b, 0.0)
            self.assertGreater(b, prev)
            prev = b

    def test_transient_ramps_to_steady_state(self):
        r = circuits.run(self.p())
        last = r["frames"][-1]
        s = circuits.solve(self.p())
        self.assertAlmostEqual(last["brightness"], s["brightness"], delta=0.005)
        self.assertLess(r["frames"][1]["brightness"], last["brightness"])


class TestMotion(unittest.TestCase):
    def p(self, **kw):
        base = {"v0": 18.0, "angle": 45.0, "mass": 1.0, "drag": 0.0,
                "wind": 0.0, "g": 9.81}
        base.update(kw)
        return base

    def test_no_drag_matches_closed_form(self):
        r = motion.run(self.p())["frames"]
        ideal_range = 18.0 ** 2 * math.sin(math.radians(90.0)) / 9.81
        ideal_height = (18.0 * math.sin(math.radians(45.0))) ** 2 / (2 * 9.81)
        peak = max(f["y"] for f in r)
        self.assertAlmostEqual(r[-1]["x"], ideal_range, delta=0.05)
        self.assertAlmostEqual(peak, ideal_height, delta=0.05)
        # time symmetry: vy sign flips halfway
        self.assertGreater(r[0]["vy"], 0)
        self.assertLess(r[-1]["vy"], 0)

    def test_drag_shortens_range_and_lands_slower_than_launch(self):
        free = motion.run(self.p())["frames"][-1]["x"]
        dragged = motion.run(self.p(drag=0.2))["frames"]
        self.assertLess(dragged[-1]["x"], free)
        self.assertLess(math.hypot(dragged[-1]["vx"], dragged[-1]["vy"]), 18.0)

    def test_wind_pushes_landing_downwind(self):
        # wind only acts THROUGH drag: with drag=0 wind does nothing (itself
        # a teaching point). Compare three runs that all have drag.
        calm = motion.run(self.p(drag=0.05))["frames"][-1]["x"]
        tail = motion.run(self.p(drag=0.05, wind=8.0))["frames"][-1]["x"]
        head = motion.run(self.p(drag=0.05, wind=-8.0))["frames"][-1]["x"]
        self.assertGreater(tail, calm)
        self.assertLess(head, calm)
        # and with zero drag the wind is exactly irrelevant
        self.assertEqual(motion.run(self.p(wind=8.0))["frames"][-1]["x"],
                         motion.run(self.p(wind=-8.0))["frames"][-1]["x"])

    def test_trajectory_stays_nonnegative_then_lands_at_zero(self):
        for f in motion.run(self.p())["frames"]:
            self.assertGreaterEqual(f["y"], 0.0)
        self.assertEqual(motion.run(self.p())["frames"][-1]["y"], 0.0)


class TestHeat(unittest.TestCase):
    def p(self, **kw):
        base = {"material_a": "water", "mass_a": 1.0, "temp_a": 90.0,
                "material_b": "iron", "mass_b": 2.0, "temp_b": 20.0,
                "ambient": 25.0, "loss": 0.0}
        base.update(kw)
        return base

    def test_equilibrium_is_weighted_mean(self):
        r = heat.run(self.p())["frames"]
        t_eq = (1.0 * 4186.0 * 90.0 + 2.0 * 450.0 * 20.0) / (1.0 * 4186.0 + 2.0 * 450.0)
        self.assertAlmostEqual(r[-1]["temp_a"], t_eq, delta=0.05)
        self.assertAlmostEqual(r[-1]["temp_b"], t_eq, delta=0.05)

    def test_hot_cools_cold_warms_never_cross(self):
        frames = heat.run(self.p())["frames"]
        ta = [f["temp_a"] for f in frames]
        tb = [f["temp_b"] for f in frames]
        self.assertTrue(all(a >= b for a, b in zip(ta, tb)))
        self.assertLess(ta[-1], ta[0])
        self.assertGreater(tb[-1], tb[0])

    def test_energy_conserves_without_leak(self):
        cap_a, cap_b = 1.0 * 4186.0, 2.0 * 450.0
        f = heat.run(self.p())["frames"]
        e0 = cap_a * 90.0 + cap_b * 20.0
        e1 = cap_a * f[-1]["temp_a"] + cap_b * f[-1]["temp_b"]
        self.assertAlmostEqual(e0, e1, delta=abs(e0) * 1e-4)

    def test_ambient_leak_drags_both_toward_room(self):
        f = heat.run(self.p(loss=1.0))["frames"]
        self.assertLess(f[-1]["temp_a"], 90.0)
        self.assertGreater(f[-1]["temp_b"], 20.0)
        self.assertGreater(f[-1]["temp_a"], f[-1]["temp_b"])  # not fully settled yet


if __name__ == "__main__":
    unittest.main()
