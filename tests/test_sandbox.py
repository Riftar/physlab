"""Sandbox mode: the catalogs (fixed, realistic items), strict validation of
student-built worlds, and the mapping of a world onto the physics engines."""

import copy
import json
import math
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import sandbox as S
from physlab import TOPICS
from physlab.topics import energy, pendulum

READY = [t["id"] for t in TOPICS if t["status"] == "ready"]


def ok(topic, world):
    clean, err = S.validate(topic, world)
    if err:
        raise AssertionError("%s %s rejected: %s" % (topic, world, err))
    return clean


def bad(test, topic, world, *words):
    clean, err = S.validate(topic, world)
    test.assertIsNone(clean, "%s should be rejected: %s" % (topic, world))
    test.assertIsInstance(err, str)
    for w in words:
        test.assertIn(w, err)


def first_amount(desc, units):
    """first '<number> <unit>' in a description (thin spaces in numbers allowed)"""
    m = re.search(r"(\d[\d ]*(?:\.\d+)?)\s*(%s)(?![/\w])" % "|".join(units), desc)
    return (float(m.group(1).replace(" ", "")), m.group(2)) if m else None


class TestCatalogs(unittest.TestCase):
    def test_ids_unique_and_items_complete(self):
        for name, items in S.CATALOGS.items():
            ids = [it["id"] for it in items]
            self.assertEqual(len(ids), len(set(ids)), name)
            for it in items:
                for k in ("id", "label", "icon", "desc"):
                    self.assertTrue(isinstance(it[k], str) and it[k], (name, it["id"], k))

    def test_descriptions_match_the_numbers_used(self):
        """what the student reads on a card is what the physics uses"""
        for name in ("balls", "bobs", "ramp_objects", "things"):
            for it in S.CATALOGS[name]:
                got = first_amount(it["desc"], ["kg", "g"])
                self.assertIsNotNone(got, (name, it["id"]))
                kg = got[0] / (1000.0 if got[1] == "g" else 1.0)
                self.assertAlmostEqual(kg, it["mass"], delta=0.01 * it["mass"], msg=(name, it["id"]))
        for name in ("balls", "bobs"):
            for it in S.CATALOGS[name]:
                cm = first_amount(it["desc"], ["cm"])
                self.assertAlmostEqual(cm[0] / 100.0, it["d"], delta=0.005 * it["d"] + 1e-9, msg=it["id"])
        for it in S.FLOATERS:
            rho = re.search(r"(\d[\d ]*) kg/m³", it["desc"]).group(1)
            self.assertEqual(float(rho.replace(" ", "")), it["rho"], it["id"])
            self.assertEqual(first_amount(it["desc"], ["cm"])[0], it["size"], it["id"])
        for it in S.LIQUIDS:
            rho = re.search(r"(\d[\d ]*) kg/m³", it["desc"]).group(1)
            self.assertEqual(float(rho.replace(" ", "")), it["rho"], it["id"])
        for it in S.SOURCES + S.ROOMS:
            self.assertEqual(float(re.search(r"(-?\d+) °C", it["desc"]).group(1)), it["temp"], it["id"])
        for it in S.PARTS:
            if it["kind"] == "lamp":      # "V W" rating <-> hot resistance R = V^2 / P
                v, w = re.search(r"([\d.]+) V ([\d.]+) W", it["short"]).groups()
                self.assertAlmostEqual(float(v) ** 2 / float(w), it["R"], places=9, msg=it["id"])
                self.assertEqual(float(v), it["v_rated"])
            if it["kind"] == "battery":
                self.assertEqual(float(re.search(r"([\d.]+) V", it["short"]).group(1)), it["emf"])

    def test_values_are_physical(self):
        for it in S.PLANETS:
            self.assertGreater(it["g"], 0.5)
            self.assertGreaterEqual(it["rho_air"], 0.0)
        for it in S.BALLS + S.BOBS:
            self.assertGreater(it["mass"], 0)
            self.assertTrue(0.1 <= it["cd"] <= 1.2, it["id"])
            rho = it["mass"] / (math.pi / 6 * it["d"] ** 3)
            self.assertTrue(1.5 < rho < 9000, (it["id"], rho))          # beach ball (mostly air) ... shot put
        for row in S.FRICTION.values():
            self.assertEqual(set(row), {s["id"] for s in S.SURFACES})
            for mu in row.values():
                self.assertTrue(0 < mu < 1)
        self.assertEqual({o["contact"] for o in S.RAMP_OBJECTS}, set(S.FRICTION))
        for it in S.RAMP_OBJECTS:
            self.assertIn(it["kind"], energy.K)
        for it in S.THINGS:
            for src in it["sources"]:
                self.assertIn(src, S.BY_ID["sources"])
        for it in S.PARTS:
            self.assertIn(it["kind"], ("wire", "switch", "lamp", "resistor", "battery"))
            if it["kind"] == "battery":
                self.assertGreater(it["r_int"], 0)

    def test_water_cant_go_in_the_oven_and_metal_cant_go_in_the_kettle(self):
        for it in S.THINGS:
            if it["material"] == "water":
                self.assertNotIn("oven", it["sources"])
                self.assertNotIn("freezer", it["sources"])       # it would be ice, not water
            else:
                self.assertNotIn("kettle", it["sources"])


class TestFieldsAndPresets(unittest.TestCase):
    def test_every_ready_topic_has_a_sandbox(self):
        self.assertEqual(set(S.SANDBOX), set(READY))

    def test_defaults_are_valid_and_run(self):
        for t in S.SANDBOX:
            world = ok(t, {})
            self.assertEqual(world, S.defaults(t))
            out = S.run(t, world)
            self.assertTrue(out["runs"], t)
            for r in out["runs"]:
                self.assertTrue(r["result"]["frames"], t)
                self.assertIn("params", r["result"])
                json.dumps(r["result"])

    def test_presets_are_valid_and_run(self):
        for t, sb in S.SANDBOX.items():
            titles = [p["title"] for p in sb["presets"]]
            self.assertEqual(len(titles), len(set(titles)), t)
            fields = {f["id"] for f in sb["fields"]}
            for pr in sb["presets"]:
                self.assertTrue(set(pr["world"]) <= fields, (t, pr["title"]))
                world = ok(t, pr["world"])
                self.assertTrue(S.run(t, world)["runs"], (t, pr["title"]))

    def test_field_defaults_within_their_limits(self):
        for t, sb in S.SANDBOX.items():
            for f in sb["fields"]:
                if f["kind"] == "number":
                    self.assertTrue(f["min"] <= f["default"] <= f["max"], (t, f["id"]))
                    self.assertGreater(f["step"], 0)
                elif f["kind"] in ("choice", "object"):
                    d = f["default"] if isinstance(f["default"], list) else [f["default"]]
                    for x in d:
                        self.assertIn(x, S.BY_ID[f["catalog"]], (t, f["id"]))

    def test_defaults_are_copies(self):
        a = S.defaults("energy")
        a["track"][0] = 99.0
        self.assertNotEqual(S.defaults("energy")["track"][0], 99.0)

    def test_catalog_view(self):
        view = S.catalog_view()
        json.dumps(view)
        self.assertEqual(set(view), set(S.SANDBOX))
        self.assertEqual(view["circuits"]["scene"], "circuitlab")
        self.assertEqual(view["motion"]["scene"], "motion")
        for t, v in view.items():
            for f in v["fields"]:
                if "catalog" in f:
                    self.assertEqual(f["items"], S.CATALOGS[f["catalog"]])
            self.assertEqual(v["defaults"], S.defaults(t))


class TestValidation(unittest.TestCase):
    def test_topic_and_shape(self):
        bad(self, "chemistry", {}, "no sandbox")
        bad(self, "motion", [], "object")
        bad(self, "motion", {"colour": "red"}, "'colour' is not part")

    def test_choices_and_objects(self):
        bad(self, "motion", {"planet": "jupiter"}, "jupiter")
        bad(self, "motion", {"planet": 3})
        bad(self, "motion", {"balls": []}, "pick 1 to 2")
        bad(self, "motion", {"balls": ["tennis", "soccer", "baseball"]}, "pick 1 to 2")
        bad(self, "motion", {"balls": ["bowling_pin"]}, "not in the")
        bad(self, "motion", {"balls": "tennis"})                       # 2-pick fields take a list ...
        self.assertEqual(ok("buoyancy", {"object": "apple"})["object"], "apple")
        bad(self, "buoyancy", {"object": ["apple"]}, "pick one")     # ... 1-pick fields a single id
        self.assertEqual(ok("motion", {"balls": ["tennis", "tennis"]})["balls"], ["tennis", "tennis"])

    def test_numbers(self):
        self.assertEqual(ok("motion", {"v0": 12})["v0"], 12.0)
        self.assertIsInstance(ok("motion", {"v0": 12})["v0"], float)
        for v in (0.5, 51, "20", True, None, float("nan"), float("inf")):
            bad(self, "motion", {"v0": v}, "between")

    def test_heat_sources_follow_the_thing(self):
        bad(self, "heat", {"thing_a": "tea", "source_a": "oven"}, "mug of tea", "oven")
        bad(self, "heat", {"thing_b": "pan", "source_b": "kettle"}, "pan", "kettle")
        ok("heat", {"thing_a": "pan", "source_a": "oven", "thing_b": "bucket", "source_b": "fridge"})

    def test_track(self):
        bad(self, "energy", {"track": [1, 2, 3]}, "exactly 7")
        bad(self, "energy", {"track": "flat"}, "exactly 7")
        bad(self, "energy", {"track": [8, 5, 3, 2, 1, 1, 11]}, "between 0 m and 10 m")
        bad(self, "energy", {"track": [8, 5, 3, 2, 1, 1, -1]}, "between")
        bad(self, "energy", {"track": [8, 5, 3, 2, 1, 1, "x"]}, "between")
        bad(self, "energy", {"track": [8.0, 5.5, 3.0, 0.6, 0.0, 0.0, 0.0]}, "below the ground")
        bad(self, "energy", {"track": [0, 10, 1, 10, 6, 8, 4]}, "too steep")
        t = ok("energy", {"track": [8, 5, 3, 2, 1.5, 1.5, 2]})["track"]
        self.assertTrue(all(isinstance(y, float) for y in t))

    def circuit(self, parts):
        return S.validate("circuits", {"parts": parts})

    def test_circuit(self):
        good = S.defaults("circuits")["parts"]
        self.assertEqual(len(ok("circuits", {"parts": good})["parts"]), len(good))
        bad(self, "circuits", {"parts": "loop"}, "list")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0]}]}, "needs")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [1, 0], "colour": "red"}]}, "needs")
        bad(self, "circuits", {"parts": [{"part": "fuse", "a": [0, 0], "b": [1, 0]}]}, "not in the parts box")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [1.0, 0]}]}, "[column, row]")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [True, 0]}]}, "[column, row]")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [6, 0], "b": [7, 0]}]}, "off the board")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, -1], "b": [0, 0]}]}, "off the board")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [1, 1]}]}, "neighbouring")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [0, 0]}]}, "neighbouring")
        bad(self, "circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [1, 0]},
                                         {"part": "lamp_6v", "a": [1, 0], "b": [0, 0]}]}, "same spot")
        bad(self, "circuits", {"parts": [{"part": "switch", "a": [0, 0], "b": [1, 0], "on": "yes"}]}, "true or false")
        bats = [{"part": "aa", "a": [i, 0], "b": [i + 1, 0]} for i in range(4)]
        bad(self, "circuits", {"parts": bats}, "at most 3 batteries")
        lamps = [{"part": "lamp_6v", "a": [i % 6, i // 6], "b": [i % 6 + 1, i // 6]} for i in range(9)]
        bad(self, "circuits", {"parts": lamps}, "at most 8 lamps")
        many = [{"part": "wire", "a": [c, r], "b": [c + 1, r]} for r in range(5) for c in range(6)] + \
               [{"part": "wire", "a": [c, r], "b": [c, r + 1]} for r in range(4) for c in range(7)]
        self.assertEqual(len(many), 58)
        bad(self, "circuits", {"parts": many}, "at most 40 parts")
        clean = ok("circuits", {"parts": [{"part": "wire", "a": [0, 0], "b": [1, 0]}]})["parts"][0]
        self.assertEqual(clean, {"part": "wire", "a": [0, 0], "b": [1, 0], "on": True, "flip": False})

    def test_input_is_not_modified(self):
        w = {"balls": ["tennis"], "v0": 10}
        before = copy.deepcopy(w)
        ok("motion", w)
        self.assertEqual(w, before)


class TestMapping(unittest.TestCase):
    def run_one(self, topic, world):
        return S.run(topic, ok(topic, world))

    def test_motion_drag_constant_from_the_ball_and_the_air(self):
        out = self.run_one("motion", {"balls": ["tennis"]})
        p = out["runs"][0]["result"]["params"]
        b = S.BY_ID["balls"]["tennis"]
        self.assertAlmostEqual(p["drag"], 0.5 * 1.225 * b["cd"] * math.pi * (b["d"] / 2) ** 2, places=12)
        self.assertEqual(p["mass"], b["mass"])
        self.assertEqual(p["wind"], 0.0)
        out = self.run_one("motion", {"balls": ["tennis"], "weather": "windy", "wind_dir": "behind"})
        self.assertEqual(out["runs"][0]["result"]["params"]["wind"], 8.0)
        out = self.run_one("motion", {"balls": ["tennis"], "weather": "windy", "wind_dir": "ahead"})
        self.assertEqual(out["runs"][0]["result"]["params"]["wind"], -8.0)

    def test_on_the_moon_every_ball_flies_the_same(self):
        out = self.run_one("motion", {"balls": ["ping_pong", "shot_put"], "planet": "moon", "weather": "storm"})
        a, b = (r["result"] for r in out["runs"])
        self.assertEqual(a["params"]["drag"], 0.0)
        self.assertEqual([f["x"] for f in a["frames"]], [f["x"] for f in b["frames"]])
        self.assertTrue(out["notes"])
        g = 1.62
        v0, ang = 20.0, math.radians(45)
        self.assertAlmostEqual(a["frames"][-1]["x"], v0 * v0 * math.sin(2 * ang) / g, delta=0.05)

    def test_in_air_the_heavy_small_ball_goes_further(self):
        out = self.run_one("motion", {"balls": ["ping_pong", "shot_put"]})
        a, b = (r["result"]["frames"][-1]["x"] for r in out["runs"])
        self.assertLess(a, 0.6 * b)

    def test_pendulum_wind_and_planet(self):
        out = self.run_one("pendulum", {"bobs": ["ping_pong"], "weather": "storm"})
        r = out["runs"][0]["result"]
        self.assertEqual(r["params"]["wind"], 15.0)
        self.assertGreater(math.degrees(r["viz"]["lean"]), 70)
        moon = self.run_one("pendulum", {"bobs": ["ping_pong"], "weather": "storm", "planet": "moon"})
        self.assertEqual(moon["runs"][0]["result"]["params"]["wind"], 0.0)      # no air, no wind
        self.assertEqual(moon["runs"][0]["result"]["params"]["g"], 1.62)

    def test_energy_friction_from_the_table(self):
        out = self.run_one("energy", {"objects": ["ice_block", "bowling"], "surface": "concrete", "planet": "mars"})
        a, b = (r["result"] for r in out["runs"])
        self.assertEqual(a["params"]["friction"], S.FRICTION["ice"]["concrete"])
        self.assertEqual(b["params"]["friction"], S.FRICTION["hard"]["concrete"])
        self.assertEqual(a["params"]["g"], 3.71)
        self.assertEqual(b["viz"]["k"], energy.K["solid_ball"])
        self.assertEqual(a["viz"]["points"], [[x, y] for x, y in zip(S.TRACK_X, S.defaults("energy")["track"])])
        self.assertEqual(a["viz"]["kind"], "custom")

    def test_energy_start_is_the_left_end_of_the_ramp(self):
        out = self.run_one("energy", {"track": [9.5, 5, 3, 2, 1.5, 1.5, 2]})
        f0 = out["runs"][0]["result"]["frames"][0]
        self.assertEqual((f0["x"], f0["y"]), (0.0, 9.5))

    def test_buoyancy_heat_waves_optics_pressure(self):
        r = self.run_one("buoyancy", {"object": "egg", "liquid": "dead_sea"})["runs"][0]["result"]
        self.assertEqual(dict((x["label"], x["value"]) for x in r["readouts"])["Result"], "FLOATS")
        r = self.run_one("buoyancy", {"object": "egg", "liquid": "water"})["runs"][0]["result"]
        self.assertEqual(dict((x["label"], x["value"]) for x in r["readouts"])["Result"], "SINKS")
        r = self.run_one("buoyancy", {"object": "gold_bar", "liquid": "mercury"})["runs"][0]["result"]
        self.assertEqual(dict((x["label"], x["value"]) for x in r["readouts"])["Result"], "SINKS")
        p = self.run_one("heat", {"thing_a": "pan", "source_a": "oven"})["runs"][0]["result"]["params"]
        self.assertEqual((p["material_a"], p["mass_a"], p["temp_a"]), ("iron", 1.5, 150.0))
        p = self.run_one("waves", {"rope": "chain", "pull": "tug"})["runs"][0]["result"]["params"]
        self.assertEqual((p["mu"], p["tension"]), (1000.0, 100.0))
        p = self.run_one("optics", {"candle": "tall", "lens": "gem"})["runs"][0]["result"]["params"]
        self.assertEqual((p["h_o"], p["material"], p["radius"]), (8.0, "diamond", 10.0))
        p = self.run_one("pressure", {"pusher": "child", "load": "van"})["runs"][0]["result"]["params"]
        self.assertEqual((p["force"], p["mass"]), (80.0, 2000.0))

    def test_circuit_world_reaches_the_solver(self):
        out = self.run_one("circuits", {})
        r = out["runs"][0]["result"]
        self.assertEqual(len(r["viz"]["parts"]), len(S.defaults("circuits")["parts"]))
        lamp = [x for x in r["viz"]["parts"] if x["kind"] == "lamp"][0]
        self.assertGreater(lamp["brightness"], 0.2)
        out = self.run_one("circuits", {"parts": S.SANDBOX["circuits"]["presets"][3]["world"]["parts"]})
        self.assertTrue(any("blew" in n for n in out["runs"][0]["result"]["notes"]))


if __name__ == "__main__":
    unittest.main()
