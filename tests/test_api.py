"""API + static edges on a loopback server, plus determinism gates."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.error
from http.server import HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.server import Handler

PORT = 8641
BASE = "http://127.0.0.1:%d" % PORT


def get(path):
    try:
        with urllib.request.urlopen(BASE + path, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        body = e.read()
        e.close()
        return e.code, body


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", PORT), Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_topics_registry_lists_ready_and_placeholders(self):
        code, body = get("/api/topics")
        self.assertEqual(code, 200)
        topics = json.loads(body)["topics"]
        ready = {t["id"] for t in topics if t["status"] == "ready"}
        ph = [t for t in topics if t["status"] == "placeholder"]
        self.assertEqual(ready, {"circuits", "motion", "heat"})
        self.assertGreaterEqual(len(ph), 6)
        for t in ph:
            self.assertTrue(t["formulas"])

    def test_run_each_ready_topic(self):
        for tid in ("circuits", "motion", "heat"):
            code, body = get("/api/run?topic=" + tid)
            self.assertEqual(code, 200, body)
            out = json.loads(body)
            self.assertTrue(out["frames"])
            self.assertTrue(out["formula"])

    def test_run_is_deterministic(self):
        for tid in ("circuits", "motion", "heat"):
            _, a = get("/api/run?topic=" + tid)
            _, b = get("/api/run?topic=" + tid)
            self.assertEqual(a, b, tid)

    def test_placeholder_topic_rejected(self):
        code, _ = get("/api/run?topic=buoyancy")
        self.assertEqual(code, 400)

    def test_unknown_topic_rejected(self):
        code, _ = get("/api/run?topic=nope")
        self.assertEqual(code, 400)

    def test_bad_and_out_of_range_params(self):
        self.assertEqual(get("/api/run?topic=motion&v0=abc")[0], 400)
        self.assertEqual(get("/api/run?topic=motion&bogus=1")[0], 400)
        self.assertEqual(get("/api/run?topic=circuits&lamps=2.5")[0], 400)
        # clamping, not rejection
        code, body = get("/api/run?topic=motion&v0=9999")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["params"]["v0"], 50.0)

    def test_static_non_root_file_served(self):
        code, body = get("/js/ui.js")
        self.assertEqual(code, 200)
        self.assertIn(b"physlab", body)

    def test_topic_icons_served(self):
        for icon in ("battery", "ball", "flame", "water", "pendulum",
                     "eye", "press", "bolt", "wave"):
            code, body = get("/icons/icon_%s.png" % icon)
            self.assertEqual(code, 200, icon)
            self.assertTrue(body.startswith(b"\x89PNG"), icon)

    def test_traversal_blocked(self):
        for probe in ("/../physlab/server.py", "/%2e%2e/physlab/server.py",
                      "/js/../../physlab/__init__.py"):
            self.assertEqual(get(probe)[0], 404, probe)


class TestGoldenFixtures(unittest.TestCase):
    """Regenerating fixtures must reproduce the committed goldens exactly."""

    def test_fixture_regen_byte_identical(self):
        repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tmp = tempfile.mkdtemp()
        try:
            subprocess.run([sys.executable, os.path.join(repo, "tests", "gen_fixtures.py"), tmp],
                           check=True, cwd=tmp, capture_output=True)
            committed = os.path.join(repo, "tests", "fixtures")
            self.assertEqual(sorted(os.listdir(committed)), sorted(os.listdir(tmp)))
            for name in os.listdir(committed):
                with open(os.path.join(committed, name), "rb") as a, \
                        open(os.path.join(tmp, name), "rb") as b:
                    self.assertEqual(a.read(), b.read(), name)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
