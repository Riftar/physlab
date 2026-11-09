"""Circuit lab (sandbox): nodal analysis of any circuit on the grid,
checked against Ohm's law by hand, Kirchhoff's current law at every dot,
energy conservation, and the lamp model of the Electric Circuits topic."""

import itertools
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab.topics import circuitlab as C
from physlab.topics import circuits as lampphys

COLS, ROWS = 7, 5
RW = C.R_WIRE


def wire(a, b):
    return {"kind": "wire", "a": a, "b": b, "label": "Wire"}


def switch(a, b, on=True):
    return {"kind": "switch", "a": a, "b": b, "on": on, "label": "Switch"}


def lamp(a, b, v=6.0, w=3.0, label="Lamp"):
    return {"kind": "lamp", "a": a, "b": b, "v_rated": v, "R": v * v / w, "label": label}


def res(a, b, r):
    return {"kind": "resistor", "a": a, "b": b, "R": r, "label": "R"}


def bat(a, b, emf=6.0, r=0.3, flip=False):
    return {"kind": "battery", "a": a, "b": b, "emf": emf, "r_int": r, "flip": flip, "label": "Battery"}


def loop(*middle):
    """battery (0,1)->(0,0) [+ at top], then the given parts along the top
    row from (0,0) to (k,0), and a return wire along row 1. Returns parts
    and the number of wires used."""
    parts = [bat((0, 1), (0, 0))]
    x = 0
    for p in middle:
        parts.append(dict(p, a=(x, 0), b=(x + 1, 0)))
        x += 1
    parts.append(wire((x, 0), (x, 1)))
    for i in range(x, 0, -1):
        parts.append(wire((i, 1), (i - 1, 1)))
    return parts, 1 + x


def kcl_residuals(parts, out):
    """net current out of every node (battery current is a->b too)"""
    net = {}
    for p, r in zip(parts, out["parts"]):
        net[p["a"]] = net.get(p["a"], 0.0) + r["current"]
        net[p["b"]] = net.get(p["b"], 0.0) - r["current"]
    return net


class TestNetwork(unittest.TestCase):
    def test_voltage_divider(self):
        # node 0 -- 1 ohm -- node 1 -- 3 ohm -- node 2; 4 A pushed from 2 to 0 through a 1e-9 S source
        volts = C.solve_network(3, [(0, 1, 1.0, 0.0), (1, 2, 1.0 / 3.0, 0.0), (0, 2, 1e-9, -4.0)])
        self.assertEqual(volts[0], 0.0)
        self.assertAlmostEqual(volts[1], -4.0 * 1.0, delta=1e-6)
        self.assertAlmostEqual(volts[2], -4.0 * 4.0, delta=1e-6)

    def test_unused_nodes_are_none_and_pieces_have_their_own_ground(self):
        volts = C.solve_network(6, [(0, 1, 1.0, 0.0), (3, 4, 2.0, 1.0)])
        self.assertIsNone(volts[2])
        self.assertIsNone(volts[5])
        self.assertEqual(volts[0], 0.0)
        self.assertEqual(volts[3], 0.0)
        self.assertAlmostEqual(volts[4], 0.5, places=12)          # 1 A into node 4 through 0.5 ohm

    def test_preferred_ground(self):
        volts = C.solve_network(3, [(0, 1, 1.0, 0.0), (1, 2, 1.0, 0.0)], prefer=[2])
        self.assertEqual(volts[2], 0.0)


class TestCircuits(unittest.TestCase):
    def solve(self, parts):
        return C.solve(parts, COLS, ROWS)

    def test_single_lamp_is_ohms_law(self):
        parts, nw = loop(lamp(None, None))
        out = self.solve(parts)
        i = 6.0 / (0.3 + 12.0 + nw * RW)
        for r in out["parts"]:
            self.assertAlmostEqual(abs(r["current"]), i, places=5)     # a series loop: one current
        lr = out["parts"][1]
        self.assertAlmostEqual(lr["power"], i * i * 12.0, places=6)
        self.assertAlmostEqual(out["parts"][0]["terminal_v"], 6.0 - 0.3 * i, places=6)

    def test_two_lamps_in_series_share_the_voltage(self):
        parts, nw = loop(lamp(None, None), lamp(None, None))
        out = self.solve(parts)
        i = 6.0 / (0.3 + 24.0 + nw * RW)
        self.assertAlmostEqual(abs(out["parts"][1]["current"]), i, places=5)
        self.assertAlmostEqual(abs(out["parts"][1]["voltage"]), abs(out["parts"][2]["voltage"]), places=5)
        one = self.solve(loop(lamp(None, None))[0])["parts"][1]
        self.assertLess(out["parts"][1]["brightness"], 0.5 * one["brightness"])   # much dimmer

    def test_two_lamps_in_parallel_each_get_the_full_voltage(self):
        parts = [bat((0, 2), (0, 1)), wire((0, 1), (1, 1)), lamp((1, 1), (2, 1)), wire((2, 1), (2, 2)),
                 wire((2, 2), (1, 2)), wire((1, 2), (0, 2)),
                 wire((1, 1), (1, 0)), lamp((1, 0), (2, 0)), wire((2, 0), (2, 1))]
        out = self.solve(parts)
        i_tot = abs(out["parts"][0]["current"])
        self.assertAlmostEqual(i_tot, 6.0 / (0.3 + 6.0), delta=0.01 * i_tot)       # R/2 in parallel
        a, b = abs(out["parts"][2]["current"]), abs(out["parts"][7]["current"])
        self.assertAlmostEqual(a + b, i_tot, places=5)
        self.assertAlmostEqual(a, b, delta=0.01 * a)
        self.assertGreater(abs(out["parts"][2]["voltage"]), 5.5)

    def test_kirchhoff_current_law_at_every_dot(self):
        parts = [bat((0, 4), (0, 3), 9.0, 1.5), wire((0, 3), (0, 2)), res((0, 2), (1, 2), 10.0),
                 lamp((1, 2), (2, 2)), res((1, 2), (1, 3), 47.0), wire((1, 3), (2, 3)), lamp((2, 3), (2, 2), 12.0, 5.0),
                 wire((2, 2), (3, 2)), bat((3, 2), (3, 3), 1.5, 0.15, flip=True), wire((3, 3), (3, 4)),
                 res((3, 4), (2, 4), 100.0), wire((2, 4), (1, 4)), wire((1, 4), (0, 4))]
        out = self.solve(parts)
        for node, net in kcl_residuals(parts, out).items():
            self.assertAlmostEqual(net, 0.0, delta=1e-5, msg=str(node))

    def test_energy_balance(self):
        parts = [bat((0, 4), (0, 3), 9.0, 1.5), wire((0, 3), (0, 2)), res((0, 2), (1, 2), 10.0),
                 lamp((1, 2), (2, 2)), res((1, 2), (1, 3), 47.0), wire((1, 3), (2, 3)), lamp((2, 3), (2, 2), 12.0, 5.0),
                 wire((2, 2), (3, 2)), wire((3, 2), (3, 3)), wire((3, 3), (3, 4)), bat((3, 4), (2, 4), 6.0, 0.3),
                 wire((2, 4), (1, 4)), wire((1, 4), (0, 4))]
        out = self.solve(parts)
        delivered = sum(r["power_out"] for r in out["parts"] if r["kind"] == "battery")
        used = sum(r["power"] for r in out["parts"] if r["kind"] != "battery")
        self.assertGreater(delivered, 0.1)
        self.assertAlmostEqual(delivered, used, delta=1e-4 * delivered)

    def test_short_circuit(self):
        parts = [bat((0, 1), (0, 0)), wire((0, 0), (1, 0)), wire((1, 0), (1, 1)), wire((1, 1), (0, 1))]
        out = C.run(parts, COLS, ROWS)
        b = out["viz"]["parts"][0]
        self.assertAlmostEqual(b["current"], 6.0 / (0.3 + 3 * RW), places=6)
        self.assertTrue(b["short"])
        self.assertAlmostEqual(b["loss"], b["current"] ** 2 * 0.3, places=3)
        self.assertTrue(any("SHORT CIRCUIT" in n for n in out["notes"]))

    def test_a_lamp_is_not_a_short(self):
        out = C.run(loop(lamp(None, None))[0], COLS, ROWS)
        self.assertFalse(out["viz"]["parts"][0]["short"])
        self.assertFalse(any("SHORT" in n for n in out["notes"]))

    def test_open_switch_stops_everything(self):
        parts, _ = loop(switch(None, None, on=False), lamp(None, None))
        out = C.run(parts, COLS, ROWS)
        self.assertTrue(all(abs(r["current"]) < 1e-12 for r in out["viz"]["parts"]))
        self.assertTrue(any("No current" in n for n in out["notes"]))
        lr = out["viz"]["parts"][2]
        self.assertEqual(lr["brightness"], 0.0)
        # the whole EMF appears across the open switch
        sw = out["viz"]["parts"][1]
        self.assertAlmostEqual(abs(sw["va"] - sw["vb"]), 6.0, places=6)

    def test_torch_bulb_on_a_car_battery_blows(self):
        parts, _ = loop(lamp(None, None, 2.5, 0.75, "Torch bulb"))
        parts[0] = bat((0, 1), (0, 0), 12.0, 0.02)
        out = C.run(parts, COLS, ROWS)
        lr = out["viz"]["parts"][1]
        self.assertTrue(lr["blown"])
        self.assertEqual(lr["status"], "blown")
        self.assertEqual(lr["current"], 0.0)
        self.assertAlmostEqual(abs(lr["voltage"]), 12.0, places=6)       # open circuit: all 12 V across the gap
        self.assertTrue(any("blew" in n for n in out["notes"]))
        # before blowing it WOULD have been hotter than tungsten's melting point
        i = 12.0 / (0.02 + 2.5 ** 2 / 0.75)
        self.assertGreater(lampphys.filament_temp(i * i * 2.5 ** 2 / 0.75, 0.75), C.T_MELT)

    def test_only_the_overloaded_lamp_blows(self):
        # torch bulb and car bulb in parallel on a car battery: the car bulb is fine
        parts = [bat((0, 2), (0, 1), 12.0, 0.02), wire((0, 1), (1, 1)), lamp((1, 1), (2, 1), 2.5, 0.75),
                 wire((2, 1), (2, 2)), wire((2, 2), (1, 2)), wire((1, 2), (0, 2)),
                 wire((1, 1), (1, 0)), lamp((1, 0), (2, 0), 12.0, 5.0), wire((2, 0), (2, 1))]
        out = C.run(parts, COLS, ROWS)
        self.assertEqual(out["viz"]["parts"][2]["status"], "blown")
        car = out["viz"]["parts"][7]
        self.assertFalse(car["blown"])
        self.assertGreater(car["brightness"], 0.3)

    def test_lamp_light_uses_the_circuits_topic_model(self):
        out = self.solve(loop(lamp(None, None, 12.0, 5.0))[0])
        lr = out["parts"][1]
        p_rated = 5.0
        t = lampphys.filament_temp(lr["power"], p_rated)
        self.assertAlmostEqual(lr["filament_k"], round(t, 1), places=6)
        self.assertAlmostEqual(lr["lumens"], round(lampphys.lumens(lr["power"], t), 4), places=6)
        self.assertEqual(lr["color"], lampphys.glow_color(t))

    def test_bigger_rated_lamps_at_their_voltage_are_brighter(self):
        def at_rated(v, w):
            parts, _ = loop(lamp(None, None, v, w))
            parts[0] = bat((0, 1), (0, 0), v, 1e-6)
            return self.solve(parts)["parts"][1]
        tiny, six, car = at_rated(6.0, 0.5), at_rated(6.0, 3.0), at_rated(12.0, 5.0)
        for r in (tiny, six, car):
            self.assertAlmostEqual(r["filament_k"], lampphys.T_RATED, delta=5)    # all run at their design heat
        self.assertLess(tiny["brightness"], six["brightness"])
        self.assertLess(six["brightness"], car["brightness"])

    def test_batteries_in_series_add_and_opposing_cancel(self):
        def two(flip):
            parts = [bat((0, 2), (0, 1), 1.5, 0.15), bat((0, 1), (0, 0), 1.5, 0.15, flip=flip),
                     wire((0, 0), (1, 0)), res((1, 0), (1, 1), 10.0), wire((1, 1), (1, 2)), wire((1, 2), (0, 2))]
            return self.solve(parts)["parts"]
        aiding = two(False)
        self.assertAlmostEqual(abs(aiding[3]["current"]), 3.0 / (10.0 + 0.3 + 3 * RW), places=5)
        opposing = two(True)
        self.assertAlmostEqual(abs(opposing[3]["current"]), 0.0, places=12)
        parts = [bat((0, 2), (0, 1), 1.5, 0.15), bat((0, 1), (0, 0), 1.5, 0.15, flip=True),
                 wire((0, 0), (1, 0)), res((1, 0), (1, 1), 10.0), wire((1, 1), (1, 2)), wire((1, 2), (0, 2))]
        notes = " ".join(C.run(parts, COLS, ROWS)["notes"])
        self.assertIn("cancel out", notes)                 # not "there is no complete loop"
        self.assertNotIn("no complete loop", notes)

    def test_closed_loop_detection(self):
        parts, _ = loop(lamp(None, None))
        self.assertTrue(C._closed_loop(parts, set(), 0))
        self.assertFalse(C._closed_loop(parts, {1}, 0))                      # the lamp blew
        parts[2] = switch(parts[2]["a"], parts[2]["b"], on=False)
        self.assertFalse(C._closed_loop(parts, set(), 0))

    def test_flipping_the_battery_reverses_the_current(self):
        parts, _ = loop(res(None, None, 10.0))
        a = self.solve(parts)["parts"][1]["current"]
        parts[0] = dict(parts[0], flip=True)
        b = self.solve(parts)["parts"][1]["current"]
        self.assertAlmostEqual(a, -b, places=12)
        self.assertGreater(abs(a), 0.1)

    def test_a_loose_part_carries_nothing(self):
        parts, _ = loop(lamp(None, None))
        parts.append(lamp((5, 3), (6, 3)))
        out = self.solve(parts)
        self.assertEqual(out["parts"][-1]["current"], 0.0)

    def test_voltages_are_measured_from_the_battery_minus(self):
        parts, _ = loop(lamp(None, None))
        out = self.solve(parts)
        self.assertEqual(out["volts"][1 * COLS + 0], 0.0)                   # battery "-" at (0, 1)
        self.assertGreater(out["volts"][0 * COLS + 0], 5.0)                 # "+" at (0, 0)

    def test_run_shape_and_formula_values(self):
        out = C.run(loop(lamp(None, None))[0], COLS, ROWS)
        self.assertEqual([f["t"] for f in out["frames"]], [0.0, C.LOOP])
        self.assertEqual(len(out["viz"]["specs"]), len(out["viz"]["parts"]))
        f = {x["expr"]: x["values"] for x in out["formula"]}
        v = f["I = V / (R + r)"]
        self.assertAlmostEqual(v["I"], round(v["V"] / (v["R (whole circuit)"] + v["r"]), 4), delta=2e-4)
        self.assertAlmostEqual(f["P = I^2 * R_lamp"]["P"], round(f["P = I^2 * R_lamp"]["I"] ** 2 * 12.0, 3), delta=2e-3)

    def test_no_battery_note(self):
        out = C.run([lamp((0, 0), (1, 0))], COLS, ROWS)
        self.assertTrue(any("No battery" in n for n in out["notes"]))
        self.assertEqual(C.run([], COLS, ROWS)["viz"]["parts"], [])


if __name__ == "__main__":
    unittest.main()
