"""Client-side calculations (www/js/core.js: frame interpolation, deep
links, sandbox links and the ramp spline), unit tested with Node. Skipped
when Node is not installed - the app itself needs no Node."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab import TOPICS, sandbox  # noqa: E402
from physlab.topics import energy  # noqa: E402
from physlab.game import bounce_factory as BF, common as GC, foundry as FD, mill as ML  # noqa: E402

NODE = shutil.which("node")


@unittest.skipUnless(NODE, "node not installed")
class TestClientCore(unittest.TestCase):
    def test_core_js(self):
        figs = []
        for t in TOPICS:
            for f in t.get("learn", {}).get("figures", []):
                figs.append({"topic": t["id"], "route": f["route"], "params": f.get("params", {}),
                             "b": f.get("b"), "view": f.get("view", {}), "at": f.get("at")})
        # the sandbox ramp: the browser previews a dragged ramp with its own
        # spline - it must be the server's spline to the last digit
        xs = sandbox.TRACK_X
        shapes = [sandbox.defaults("energy")["track"]]
        shapes += [p["world"]["track"] for p in sandbox.SANDBOX["energy"]["presets"] if "track" in p["world"]]
        shapes += [[8.0, 5.5, 3.0, 0.6, 0.0, 0.0, 0.0], [0, 10, 1, 10, 6, 8, 4], [1, 1, 1, 10, 1, 1, 1]]
        refs = []
        for ys in shapes:
            tr = energy.SplineTrack(xs, ys)
            samples = [[x] + list(tr.eval(x)) for x in [i * 0.37 for i in range(82)] + xs]
            refs.append({"xs": xs, "ys": ys, "samples": samples, "max_slope": sandbox.TRACK_LIMITS["max_slope"],
                         "check": tr.check(sandbox.TRACK_LIMITS["max_slope"])})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(figs, fh)
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh2:
            json.dump(refs, fh2)
        try:
            out = subprocess.run([NODE, os.path.join(ROOT, "tests", "js", "test_core.js"), fh.name, fh2.name],
                                 capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(fh.name)
            os.unlink(fh2.name)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("client tests", out.stdout)


    def test_game_js(self):
        camel = []
        for top, hump in ((1.5, 1.0), (1.4, 0.3), (1.6, 1.55), (2.0, 0.84)):
            tr = energy.CamelTrack(top, hump)
            camel.append({"top": top, "hump": hump,
                          "samples": [[x] + list(tr.eval(x)) for x in [i * 0.13 for i in range(51)] + [3.5, 0.25]]})
        knobs = []
        for st in BF.STATIONS + FD.STATIONS + ML.STATIONS:
            for k in st["knobs"]:
                if k["kind"] == "choice":
                    raws = [c["id"] for c in k["choices"]]
                elif k["kind"] == "integer":           # the server refuses fractions; the client rounds first
                    raws = [k["min"], k["max"], k["default"], (k["min"] + k["max"]) // 2]
                else:
                    raws = [k["min"], k["max"], k["default"], (k["min"] + k["max"]) / 3.0, k["min"] + 1.37 * k["step"],
                            k["max"] - 0.49 * k["step"], k["min"] + 0.5000001 * k["step"]]
                for raw in raws:
                    clean, err = GC.validate_knobs(st, {k["id"]: raw})
                    self.assertIsNone(err)
                    knobs.append({"spec": k, "raw": raw, "expect": clean[k["id"]]})
        links = [{"hall": mod.HALL["id"], "station": sid, "step": v["step"], "game": v[key], "solution": v[sol]}
                 for mod in (BF, FD, ML) for sid, s in mod.table()["stations"].items() for v in s["variants"]
                 for key, sol in (("game", "solution"), ("game_mastery", "mastery_solution"),
                                  ("game_best", "score_solution")) if v.get(key)]
        # a real run's frames and time-lapse zones: the scene's field lookup must hold/interpolate them
        kn = {sid: FD.table()["stations"][sid]["variants"][2]["solution"] for sid in FD.BY_ID}
        m = FD.run_machine(kn, {sid: 2 for sid in kn})
        probe = []
        for t in (0.0, 3.3, m["stations"][0]["t1"] + 0.5, m["stations"][1]["t0"] + 0.3, m["stations"][2]["t1"],
                  m["frames"][-1]["t"] + 1):
            got = {}
            for key in ("T", "door", "x2", "th"):
                tr = [(f["t"], f[key]) for f in m["frames"] if key in f]
                if t < tr[0][0]:
                    got[key] = None
                elif t >= tr[-1][0]:
                    got[key] = tr[-1][1]
                else:
                    i = max(j for j in range(len(tr)) if tr[j][0] <= t)
                    (ta, a), (tb, b) = tr[i], tr[i + 1]
                    got[key] = a + (b - a) * (t - ta) / ((tb - ta) or 1)
            probe.append({"t": t, "fields": got})
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump({"camel": camel, "knobs": knobs, "links": links,
                       "machine": {"frames": m["frames"], "timelapse": m["timelapse"], "probe": probe}}, fh)
        try:
            out = subprocess.run([NODE, os.path.join(ROOT, "tests", "js", "test_game.js"), fh.name],
                                 capture_output=True, text=True, timeout=60)
        finally:
            os.unlink(fh.name)
        self.assertEqual(out.returncode, 0, out.stderr + out.stdout)
        self.assertIn("game client tests", out.stdout)


if __name__ == "__main__":
    unittest.main()
