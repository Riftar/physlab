"""Lenses: every formula and calculation. Thin-lens results are checked
against classic cases; the Snell's-law tracer against the law itself and
against exact paraxial thick-lens (matrix) optics."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import optics as O


def params(**kw):
    base = {"kind": "converging", "material": "crown", "radius": 20.0, "d_o": 30.0, "h_o": 4.0}
    base.update(kw)
    return base


def thick_lens_image(n, r, t, d_o):
    """Paraxial image distance (from the back vertex) of a thick lens by
    ray-transfer matrices: refraction at R1, travel t in glass, R2."""
    def mul(a, b):
        return [[a[0][0] * b[0][0] + a[0][1] * b[1][0], a[0][0] * b[0][1] + a[0][1] * b[1][1]],
                [a[1][0] * b[0][0] + a[1][1] * b[1][0], a[1][0] * b[0][1] + a[1][1] * b[1][1]]]
    r1, r2 = r, -r
    ref1 = [[1, 0], [-(n - 1) / r1, 1]]          # reduced-angle convention (n*u)
    tr = [[1, t / n], [0, 1]]
    ref2 = [[1, 0], [-(1 - n) / r2, 1]]
    m = mul(ref2, mul(tr, ref1))
    # object at distance d_o before the front vertex: y' = A y + B u, u' = C y + D u
    (a, b), (c, d) = mul(m, [[1, d_o], [0, 1]])
    return -b / d                                  # where y' = 0 for all rays from the axis point


class TestFormulas(unittest.TestCase):
    def test_lensmaker(self):
        self.assertAlmostEqual(O.lensmaker(1.5, 20.0, -20.0), 0.05, places=12)
        self.assertAlmostEqual(O.focal_length(1.5, 20.0, "converging"), 20.0, places=12)
        self.assertAlmostEqual(O.focal_length(1.5, 20.0, "diverging"), -20.0, places=12)
        # denser glass or tighter curves -> shorter focal length
        self.assertLess(O.focal_length(2.417, 20.0, "converging"), O.focal_length(1.333, 20.0, "converging"))
        self.assertLess(O.focal_length(1.52, 10.0, "converging"), O.focal_length(1.52, 30.0, "converging"))

    def test_thin_lens_classic_cases(self):
        f = 20.0
        self.assertAlmostEqual(O.image_distance(f, 40.0), 40.0, places=12)          # 2f -> 2f
        self.assertAlmostEqual(O.magnification(40.0, 40.0), -1.0, places=12)
        self.assertIsNone(O.image_distance(f, 20.0))                                  # at f: infinity
        di = O.image_distance(f, 10.0)                                                # inside f: virtual
        self.assertAlmostEqual(di, -20.0, places=12)
        self.assertAlmostEqual(O.magnification(10.0, di), 2.0, places=12)
        di = O.image_distance(-20.0, 30.0)                                            # diverging
        self.assertLess(di, 0)
        self.assertTrue(0 < O.magnification(30.0, di) < 1)
        for d_o in (25.0, 33.0, 70.0):
            di = O.image_distance(f, d_o)
            self.assertAlmostEqual(1 / d_o + 1 / di, 1 / f, places=12)

    def test_power_and_light_speed(self):
        self.assertAlmostEqual(O.power_dioptres(50.0), 2.0, places=12)
        self.assertAlmostEqual(O.power_dioptres(-25.0), -4.0, places=12)
        self.assertAlmostEqual(O.light_speed(1.5), 299792.458 / 1.5, places=9)


class TestGeometryAndRays(unittest.TestCase):
    def test_lens_shape(self):
        g = O.geometry(20.0, "converging")
        self.assertAlmostEqual(g["sag"], 20.0 - math.sqrt(400.0 - 25.0), places=12)
        self.assertAlmostEqual(g["t"], 2 * g["sag"] + O.EDGE, places=12)
        d = O.geometry(20.0, "diverging")
        self.assertAlmostEqual(d["edge"], O.CENTRE_THIN + 2 * d["sag"], places=12)
        for q in g["outline"]:                   # every outline point is on one of the two spheres
            on1 = abs(math.hypot(q[0] - g["c1"], q[1]) - 20.0) < 1e-3
            on2 = abs(math.hypot(q[0] - g["c2"], q[1]) - 20.0) < 1e-3
            self.assertTrue(on1 or on2, q)

    def test_principal_rays_meet_at_the_image(self):
        for kw in ({}, {"d_o": 12.0}, {"kind": "diverging"}, {"d_o": 70.0, "h_o": 7.0}):
            p = params(**kw)
            r = O.run(p)
            vz = r["viz"]
            target = (vz["d_i"], vz["h_i"])
            for ray in vz["rays"]:
                if vz["d_i"] > 0:                 # real: the emerging ray passes the image tip
                    (x1, y1), (x2, y2) = ray["pts"][1], ray["pts"][2]
                else:                             # virtual: its backwards extension does
                    (x1, y1), (x2, y2) = ray["virt"]
                y_at = y1 + (y2 - y1) * (target[0] - x1) / (x2 - x1)
                self.assertAlmostEqual(y_at, target[1], delta=2e-3, msg=(kw, ray["name"]))

    def test_snell_law_holds_at_every_refraction(self):
        n = 1.52
        for ang in (0.0, 0.2, 0.6, 1.0):
            d = (math.cos(ang), math.sin(ang))
            nrm = (-1.0, 0.0)
            out, refl = O.refract(d, nrm, 1.0, n)
            self.assertFalse(refl)
            sin_i = abs(d[1])
            sin_r = abs(out[1]) / math.hypot(*out)
            self.assertAlmostEqual(1.0 * sin_i, n * sin_r, places=12)
            self.assertAlmostEqual(math.hypot(*out), 1.0, places=12)

    def test_total_internal_reflection(self):
        # from glass (n = 1.52) into air, beyond the critical angle 41.1 deg
        d = (math.cos(math.radians(60)), math.sin(math.radians(60)))
        out, refl = O.refract(d, (-1.0, 0.0), 1.52, 1.0)
        self.assertTrue(refl)
        self.assertAlmostEqual(out[0], -d[0], places=12)
        self.assertAlmostEqual(out[1], d[1], places=12)

    def test_traced_rays_refract_at_both_surfaces(self):
        geo = O.geometry(20.0, "converging")
        r = O.trace((-30.0, 4.0), (geo["x1"] + 30.0, 1.0 - 4.0), geo, 1.52, 200.0)
        self.assertTrue(r["exits"])
        self.assertEqual(r["n"], [1.0, 1.52, 1.0])
        self.assertEqual(len(r["pts"]), 4)

    def test_paraxial_real_rays_agree_with_thick_lens_optics(self):
        n, R, d_o = 1.52, 20.0, 30.0
        geo = O.geometry(R, "converging")
        start = (-d_o, 0.0)                       # axis point: rays close to the axis
        lines = []
        for y in (-0.2, -0.1, 0.1, 0.2):
            tr = O.trace(start, (geo["x1"] - start[0], y), geo, n, 300.0)
            a, b = tr["pts"][-2], tr["pts"][-1]
            lines.append(((a[0], a[1]), (b[0] - a[0], b[1] - a[1])))
        x_cross = O.crossing(lines)[0]
        expect = geo["x2"] + thick_lens_image(n, R, geo["t"], d_o + geo["x1"])
        self.assertAlmostEqual(x_cross, expect, delta=0.02 * expect)

    def test_thin_lens_formula_is_close_for_a_distant_candle(self):
        # near d_o ~ 1.5 f the image distance is very sensitive to f, so the
        # real lens's slightly longer focal length and its principal planes
        # (it has 1.6 cm of thickness) shift the image by ~6%; for a far
        # object the thin-lens answer is within ~3% of the real lens
        n, R, d_o = 1.52, 20.0, 200.0
        geo = O.geometry(R, "converging")
        lines = []
        for y in (-0.2, 0.2):
            tr = O.trace((-d_o, 0.0), (geo["x1"] + d_o, y), geo, n, 300.0)
            a, b = tr["pts"][-2], tr["pts"][-1]
            lines.append(((a[0], a[1]), (b[0] - a[0], b[1] - a[1])))
        thin = O.image_distance(O.focal_length(n, R, "converging"), d_o)
        self.assertAlmostEqual(O.crossing(lines)[0] / thin, 1.0, delta=0.03)

    def test_spherical_aberration_edge_rays_focus_closer(self):
        n, R = 1.52, 20.0
        geo = O.geometry(R, "converging")
        start = (-200.0, 0.0)

        def cross(y_pair):
            lines = []
            for y in y_pair:
                tr = O.trace(start, (geo["x1"] - start[0], y), geo, n, 300.0)
                a, b = tr["pts"][-2], tr["pts"][-1]
                lines.append(((a[0], a[1]), (b[0] - a[0], b[1] - a[1])))
            return O.crossing(lines)[0]
        self.assertLess(cross((-4.5, 4.5)), cross((-0.3, 0.3)))

    def test_crossing_helper(self):
        p = O.crossing([((0, 0), (1, 1)), ((2, 0), (-1, 1))])
        self.assertAlmostEqual(p[0], 1.0, places=12)
        self.assertAlmostEqual(p[1], 1.0, places=12)
        self.assertIsNone(O.crossing([((0, 0), (1, 0)), ((0, 1), (1, 0))]))


class TestRun(unittest.TestCase):
    def test_readouts_and_notes(self):
        r = O.run(params())
        self.assertEqual(r["viz"]["image"], "real")
        self.assertAlmostEqual(r["viz"]["f"], 20.0 / (2 * 0.52), places=3)
        self.assertIn("Real image", r["notes"][0])
        self.assertEqual(O.run(params(d_o=12.0))["viz"]["image"], "virtual")
        self.assertEqual(O.run(params(kind="diverging"))["viz"]["image"], "virtual")
        rf = O.run(params(material="water", radius=13.33, d_o=20.0))   # f = 20.01: nearly at F
        self.assertTrue(rf["viz"]["image"] in ("real", "virtual", "none"))

    def test_diamond_shows_total_internal_reflection(self):
        r = O.run(params(material="diamond", radius=6.0, d_o=10.0))
        self.assertTrue(any(ray["tir"] for ray in r["viz"]["fan"]))
        self.assertIn("total internal reflection", " ".join(r["notes"]))

    def test_world_box_contains_candle_lens_and_image(self):
        for kw in ({}, {"d_o": 12.0}, {"kind": "diverging"}):
            vz = O.run(params(**kw))["viz"]
            b = vz["box"]
            self.assertLess(b["x0"], -vz["d_o"])
            self.assertGreater(b["x1"], 0)
            if vz["d_i"] is not None and abs(vz["d_i"]) < 400:
                self.assertTrue(b["x0"] < vz["d_i"] < b["x1"])


if __name__ == "__main__":
    unittest.main()
