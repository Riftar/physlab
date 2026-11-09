"""Waves on a rope: every formula and calculation. The solver is checked
against d'Alembert's exact solution (to rounding) and the damped
steady-state formula."""

import cmath
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import waves as W


def params(**kw):
    base = {"f": 2.5, "amplitude": 3.0, "tension": 20.0, "mu": 200.0, "length": 4.0,
            "end": "fixed", "damping": 1.0}
    base.update(kw)
    return base


class TestFormulas(unittest.TestCase):
    def test_wave_speed_and_wavelength(self):
        self.assertAlmostEqual(W.wave_speed(20.0, 0.2), 10.0, places=12)
        self.assertAlmostEqual(W.wave_speed(80.0, 0.2), 20.0, places=12)     # 4x tension -> 2x speed
        self.assertAlmostEqual(W.wave_speed(20.0, 0.8), 5.0, places=12)      # 4x heavier -> half speed
        self.assertAlmostEqual(W.wavelength(10.0, 2.5), 4.0, places=12)

    def test_resonance_series(self):
        self.assertEqual([round(x, 9) for x in W.resonances(10.0, 4.0, "fixed", 3)], [1.25, 2.5, 3.75])
        self.assertEqual([round(x, 9) for x in W.resonances(10.0, 4.0, "free", 3)], [0.625, 1.875, 3.125])
        self.assertEqual(W.resonances(10.0, 4.0, "open"), [])

    def test_complex_wavenumber(self):
        k = W.complex_k(2.0, 10.0, 0.0)
        self.assertAlmostEqual(k.real, 2 * math.pi * 2.0 / 10.0, places=12)
        self.assertAlmostEqual(k.imag, 0.0, places=12)
        self.assertLess(W.complex_k(2.0, 10.0, 1.0).imag, 0.0)       # damped: decays along the rope
        k = W.complex_k(1.3, 7.0, 0.8)
        w = 2 * math.pi * 1.3
        self.assertAlmostEqual(abs(k * k * 49.0 - (w * w - 1j * w * 0.8)), 0.0, places=9)

    def test_steady_profile_boundary_conditions(self):
        for end in ("fixed", "free", "open"):
            self.assertAlmostEqual(abs(W.steady_profile(0.0, 1.7, 9.0, 0.6, 3.0, end) - 1.0), 0.0, places=12)
        self.assertAlmostEqual(abs(W.steady_profile(3.0, 1.7, 9.0, 0.6, 3.0, "fixed")), 0.0, places=12)
        h = 1e-6   # free end: zero slope
        d = (W.steady_profile(3.0, 1.7, 9.0, 0.6, 3.0, "free") -
             W.steady_profile(3.0 - h, 1.7, 9.0, 0.6, 3.0, "free")) / h
        self.assertLess(abs(d), 1e-4)

    def test_dalembert_reflection_signs(self):
        # just after the first reflection, fixed ends invert and free ends don't
        t = 0.5
        fx = W.dalembert(4.0, t, 2.5, 0.03, 10.0, 4.0, "fixed")
        fr = W.dalembert(4.0, t, 2.5, 0.03, 10.0, 4.0, "free")
        inc = W.dalembert(4.0, t, 2.5, 0.03, 10.0, 4.0, "open")
        self.assertAlmostEqual(fx, 0.0, places=12)
        self.assertAlmostEqual(fr, 2 * inc, places=12)

    def test_grid_is_courant_one_with_enough_steps(self):
        for p in (params(), params(f=5.0, tension=1.0, mu=1000.0, length=8.0),
                  params(f=0.2, tension=100.0, mu=20.0, length=1.0)):
            n, dt, v = W.grid(p)
            self.assertAlmostEqual(v * dt, p["length"] / n, places=12)     # dx = v dt
            if n < W.MAX_CELLS:
                self.assertLessEqual(dt, 1.0 / (W.STEPS_PER_PERIOD * p["f"]) + 1e-12)

    def test_envelope_and_nodes_helpers(self):
        xs = [i * 0.01 for i in range(401)]
        shapes = [[math.sin(math.pi * x) * math.cos(ph) for x in xs] for ph in (0.0, 1.0, 2.0, 3.0)]
        env = W.envelope(shapes)
        self.assertAlmostEqual(max(env), 1.0, delta=1e-3)
        self.assertEqual([round(x, 2) for x in W.find_nodes(xs, env)], [1.0, 2.0, 3.0])

    def test_crest_tracker(self):
        # crests leave the driver at t = (k + 1/4) / f and move at v
        x = W._crest(0.35, 2.5, 10.0, 4.0)
        self.assertAlmostEqual(x, 10.0 * (0.35 - 0.1), places=12)
        self.assertIsNone(W._crest(0.05, 2.5, 10.0, 4.0))
        for t in (0.5, 1.3, 2.7):
            x = W._crest(t, 2.5, 10.0, 4.0)
            self.assertTrue(x is None or 0.0 <= x <= 4.0)


class TestSolver(unittest.TestCase):
    def test_undamped_scheme_is_exact_before_the_echo_returns(self):
        for end in ("fixed", "free", "open"):
            p = params(end=end, damping=0.0)
            n, dt, v = W.grid(p)
            xs, dt, rec = W.simulate(p, t_end=0.75)          # 2L/v = 0.8 s
            err = max(abs(y[i] - W.dalembert(xs[i], t, p["f"], 0.03, v, p["length"], end))
                      for t, y, _ in rec for i in range(len(xs)))
            self.assertLess(err, 1e-12, end)

    def test_nothing_moves_ahead_of_the_front(self):
        p = params(end="open", damping=0.0)
        n, dt, v = W.grid(p)
        xs, dt, rec = W.simulate(p, t_end=0.3)
        for t, y, _ in rec:
            for x, yy in zip(xs, y):
                if x > v * t + 1e-9:
                    self.assertEqual(yy, 0.0)

    def test_velocity_is_the_time_derivative(self):
        p = params(end="open", damping=0.0)
        n, dt, v = W.grid(p)
        xs, dt, rec = W.simulate(p, t_end=0.3)
        w = 2 * math.pi * p["f"]
        t, y, vel = rec[-1]
        for x, u in zip(xs, vel):
            tau = t - x / v
            if tau > 2 * dt:
                self.assertAlmostEqual(u, 0.03 * w * math.cos(w * tau), delta=0.03 * w * 0.05)

    def test_damped_steady_state_matches_the_formula(self):
        for end, f in (("fixed", 2.5), ("fixed", 1.9), ("free", 1.9), ("open", 1.3)):
            p = params(end=end, f=f)
            n, dt, v = W.grid(p)
            xs, dt, rec = W.simulate(p, t_end=10.0)
            last = [y for t, y, _ in rec if t >= rec[-1][0] - 1.0 / f]
            env = W.envelope(last)
            exact = [0.03 * abs(W.steady_profile(x, f, v, 1.0, 4.0, end)) for x in xs]
            self.assertLess(max(abs(a - b) for a, b in zip(env, exact)), 0.03 * max(exact), (end, f))

    def test_resonance_builds_a_much_bigger_wave(self):
        on = W.run(params(f=2.5))          # f_2 for the fixed end
        off = W.run(params(f=1.9))         # between f_1 and f_2
        amp_on = max(on["viz"]["envelope"])
        amp_off = max(off["viz"]["envelope"])
        self.assertGreater(amp_on, 3 * amp_off)
        # near resonance the gain is ~ 2 v / (gamma L) = 5
        self.assertAlmostEqual(amp_on / 0.03, 5.0, delta=0.3)
        self.assertIn("Resonance", " ".join(on["notes"]))

    def test_nodes_are_half_a_wavelength_apart(self):
        r = W.run(params(f=3.75))          # f_3, lambda = 10/3.75 m
        nodes = r["viz"]["nodes"]
        lam = 10.0 / 3.75
        self.assertGreaterEqual(len(nodes), 2)
        for a, b in zip(nodes, nodes[1:]):
            self.assertAlmostEqual(b - a, lam / 2, delta=0.12)

    def test_open_end_has_no_nodes_and_no_resonance(self):
        r = W.run(params(end="open"))
        self.assertEqual(r["viz"]["nodes"], [])
        self.assertIn("Open end", " ".join(r["notes"]))

    def test_run_output_is_consistent(self):
        r = W.run(params())
        vz = r["viz"]
        for f in r["frames"]:
            self.assertEqual(len(f["y"]), len(vz["xs"]))
            self.assertAlmostEqual(f["y"][0] * vz["unit"], f["driver"], delta=vz["unit"])
        ts = [f["t"] for f in r["frames"]]
        self.assertTrue(all(b > a for a, b in zip(ts, ts[1:])))
        self.assertAlmostEqual(vz["v"], 10.0, places=6)
        self.assertAlmostEqual(vz["lambda"], 4.0, places=6)
        self.assertAlmostEqual(r["readouts"][0]["value"], 10.0)
        self.assertAlmostEqual(r["readouts"][1]["value"], 4.0)

    def test_slow_shaking_runs_at_least_four_periods(self):
        r = W.run(params(f=0.2))
        self.assertGreaterEqual(r["frames"][-1]["t"], 4.0 / 0.2 - 0.5)


if __name__ == "__main__":
    unittest.main()
