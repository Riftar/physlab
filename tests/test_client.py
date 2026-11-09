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


if __name__ == "__main__":
    unittest.main()
