"""Pressure (hydraulic lift): every formula and calculation, plus the
conservation laws the simulation must respect."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import pressure as P


def params(**kw):
    base = {"force": 150.0, "d1": 3.0, "d2": 30.0, "mass": 1000.0, "stroke": 25.0, "fluid": "oil"}
    base.update(kw)
    return base


class TestFormulas(unittest.TestCase):
    def test_area_and_pressure(self):
        self.assertAlmostEqual(P.area(2.0), math.pi * 0.01 ** 2, places=15)
        self.assertAlmostEqual(P.pressure(100.0, 0.5), 200.0, places=12)

    def test_pascal_force_and_distance(self):
        a1, a2 = P.area(3.0), P.area(30.0)
        self.assertAlmostEqual(a2 / a1, 100.0, places=9)
        self.assertAlmostEqual(P.output_force(150.0, a1, a2), 15000.0, places=6)
        self.assertAlmostEqual(P.output_distance(0.25, a1, a2), 0.0025, places=12)
        # force x distance is the same on both sides
        self.assertAlmostEqual(150.0 * 0.25, P.output_force(150.0, a1, a2) * P.output_distance(0.25, a1, a2),
                               places=9)

    def test_hand_force_model(self):
        self.assertEqual(P.hand_force(200.0, 0.0), 200.0)
        self.assertAlmostEqual(P.hand_force(200.0, P.V_HAND / 2), 100.0, places=12)
        self.assertEqual(P.hand_force(200.0, 2 * P.V_HAND), 0.0)
        self.assertEqual(P.hand_force(200.0, -1.0), 200.0)

    def test_needed_push_includes_the_liquid_weight(self):
        a1, a2 = P.area(3.0), P.area(30.0)
        self.assertAlmostEqual(P.needed_push(1000.0, 9.81, a1, a2, 870.0, 0.0), 9810.0 * a1 / a2, places=9)
        more = P.needed_push(1000.0, 9.81, a1, a2, 870.0, 0.2)
        x2 = 0.2 * a1 / a2
        self.assertAlmostEqual(more - 9810.0 * a1 / a2, a1 * 870.0 * 9.81 * (0.2 + x2), places=9)

    def test_liquid_lift_energy(self):
        a1, a2 = P.area(3.0), P.area(30.0)
        x1, x2 = 0.2, 0.2 * a1 / a2
        # a slug of volume A1 x1 rises from the middle of the small column's lost
        # part to the middle of the big column's gained part
        expect = 870.0 * 9.81 * a1 * x1 * ((P.H0 + x2 / 2) - (P.H0 - x1 / 2))
        self.assertAlmostEqual(P.liquid_lift_energy(870.0, 9.81, a1, x1, a2), expect, places=12)


class TestSimulation(unittest.TestCase):
    def test_big_piston_moves_d1_A1_over_A2_in_every_frame(self):
        r = P.run(params())
        a1, a2 = P.area(3.0), P.area(30.0)
        for f in r["frames"]:
            self.assertAlmostEqual(f["x2"], f["x1"] * a1 / a2, delta=1e-8)
        self.assertAlmostEqual(r["frames"][-1]["x1"], 0.25, places=9)
        self.assertAlmostEqual(r["frames"][-1]["x2"], 0.0025, places=9)

    def test_energy_is_booked_exactly(self):
        for kw in ({}, {"mass": 0.0}, {"force": 600.0, "mass": 2000.0, "d1": 1.0, "d2": 60.0},
                   {"force": 500.0, "mass": 10.0, "d1": 10.0, "d2": 12.0}, {"fluid": "water"}):
            f = P.run(params(**kw))["frames"][-1]
            out = f["w_load"] + f["w_liquid"] + f["w_loss"] + f["ke"]
            self.assertAlmostEqual(f["w_in"], out, delta=1e-6 * max(1.0, f["w_in"]), msg=str(kw))

    def test_too_weak_a_push_moves_nothing(self):
        need = P.needed_push(1000.0, 9.81, P.area(3.0), P.area(30.0), 870.0, 0.0)
        r = P.run(params(force=math.floor(need) - 1.0))
        self.assertEqual(r["frames"][-1]["x1"], 0.0)
        self.assertFalse(r["viz"]["lifted"])
        self.assertIn("Not enough push", r["notes"][0])
        self.assertTrue(P.run(params(force=math.ceil(need) + 5.0))["viz"]["lifted"])

    def test_pressure_at_rest_is_the_same_on_both_pistons(self):
        r = P.run(params(force=80.0))              # stalled: the liquid carries the load
        f = r["frames"][-1]
        self.assertAlmostEqual(f["p1"], 1000.0 * 9.81 / P.area(30.0), places=3)
        self.assertAlmostEqual(f["p2"] * P.area(30.0), 1000.0 * 9.81, places=3)

    def test_pushing_while_moving(self):
        r = P.run(params())
        mid = r["frames"][len(r["frames"]) // 2]
        self.assertGreater(mid["v1"], 0.0)
        self.assertLess(mid["v1"], P.V_HAND)
        # the hand pushes harder than what just holds the load, the extra goes into motion + friction
        self.assertGreater(mid["f_hand"], P.needed_push(1000.0, 9.81, P.area(3.0), P.area(30.0), 870.0, mid["x1"]))

    def test_readouts_match_formulas(self):
        r = P.run(params())
        vals = {x["label"]: x["value"] for x in r["readouts"]}
        self.assertAlmostEqual(vals["Pressure your push makes p = F1/A1"], 150.0 / P.area(3.0) / 1000.0, places=2)
        self.assertAlmostEqual(vals["Force on the big piston F2 = p·A2"], 15000.0, places=1)
        self.assertAlmostEqual(vals["Area ratio A2/A1 (force multiplier)"], 100.0, places=2)


if __name__ == "__main__":
    unittest.main()
