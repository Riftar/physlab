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

    # --- real-lamp model: colorimetry validated against independent references ---
    def test_blackbody_luminance_matches_old_candela_definition(self):
        # 1948-1979 candela: a black body at the platinum freezing point
        # (2042 K) has a luminance of 60 cd/cm^2 = 6.0e5 cd/m^2
        self.assertAlmostEqual(circuits.luminance(2042.0), 6.0e5, delta=6.0e5 * 0.01)

    def test_blackbody_chromaticity_matches_cie_illuminant_a(self):
        x, y = circuits.chromaticity(2856.0)      # CIE Illuminant A: (0.4476, 0.4074)
        self.assertAlmostEqual(x, 0.4476, delta=0.003)
        self.assertAlmostEqual(y, 0.4074, delta=0.003)

    def test_rated_voltage_gives_rated_filament_temperature(self):
        s = circuits.solve(self.p(voltage=circuits.LAMP_V_RATED, internal_r=0.0))
        self.assertAlmostEqual(s["filament_k"], circuits.T_RATED, places=6)
        self.assertAlmostEqual(s["lamp_power"], s["rated_power"], places=9)

    def test_series_lamps_get_dimmer_and_cooler(self):
        prev_t, prev_b = float("inf"), float("inf")
        for n in (1, 2, 3):
            s = circuits.solve(self.p(lamps=n))
            self.assertLess(s["filament_k"], prev_t)
            self.assertLess(s["brightness"], prev_b)
            prev_t, prev_b = s["filament_k"], s["brightness"]

    def test_light_is_strongly_nonlinear_in_power(self):
        # a quarter of the power (half the voltage) gives FAR less than a
        # quarter of the light, because the filament runs cooler and redder
        full = circuits.solve(self.p(voltage=6.0, internal_r=0.0))
        half_v = circuits.solve(self.p(voltage=3.0, internal_r=0.0))
        self.assertAlmostEqual(half_v["lamp_power"], full["lamp_power"] / 4, places=9)
        self.assertLess(half_v["lumens"], full["lumens"] / 10)

    def test_two_lamps_on_double_voltage_match_one_lamp(self):
        one = circuits.solve(self.p(voltage=6.0, lamps=1, internal_r=0.0))
        two = circuits.solve(self.p(voltage=12.0, lamps=2, internal_r=0.0))
        self.assertAlmostEqual(one["lumens"], two["lumens"], places=9)
        self.assertEqual(one["color"], two["color"])

    def test_brightness_never_clips_inside_the_spec(self):
        top = circuits.solve(self.p(voltage=12.0, lamp_r=5.0, internal_r=0.0))
        self.assertAlmostEqual(top["brightness"], 1.0, places=9)
        near = circuits.solve(self.p(voltage=11.5, lamp_r=5.0, internal_r=0.0))
        self.assertLess(near["brightness"], top["brightness"])

    def test_glow_colour_warms_as_filament_cools(self):
        def rgb(hexs):
            return [int(hexs[i:i + 2], 16) for i in (1, 3, 5)]
        hot = rgb(circuits.glow_color(3400.0))
        warm = rgb(circuits.glow_color(2000.0))
        dull = rgb(circuits.glow_color(1200.0))
        # blue share falls, red dominates as temperature drops
        self.assertGreater(hot[2], warm[2])
        self.assertGreater(warm[1], dull[1])
        self.assertEqual(dull[0], 255)

    def test_final_frame_is_exact_steady_state(self):
        r = circuits.run(self.p())
        s = circuits.solve(self.p())
        self.assertEqual(r["frames"][-1]["filament_k"], round(s["filament_k"], 1))
        self.assertEqual(r["frames"][-1]["color"], s["color"])

    def test_notes_flag_overvolt_melt_and_open(self):
        self.assertIn("Over-volted", " ".join(circuits.run(self.p(voltage=8.0, internal_r=0.0))["notes"]))
        self.assertIn("melting", " ".join(circuits.run(self.p(voltage=12.0))["notes"]))
        self.assertIn("Switch open", " ".join(circuits.run(self.p(closed=False))["notes"]))
        self.assertEqual(circuits.run(self.p())["notes"], [])

    def test_formula_values_satisfy_the_formula(self):
        v = circuits.run(self.p(resistor=10.0))["formula"][0]["values"]
        self.assertAlmostEqual(v["V"] / (v["R"] + v["r"]), v["I"], places=4)

    def test_drift_speed_is_i_over_n_e_a(self):
        s = circuits.solve(self.p())
        expect = s["current"] / (8.49e28 * 1.602176634e-19 * 0.5e-6) * 1000.0
        self.assertAlmostEqual(s["drift_mm_s"], expect, places=12)


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

    def test_landing_point_is_precise(self):
        r = motion.run(self.p())
        ideal_range = 18.0 ** 2 / 9.81
        ideal_time = 2 * 18.0 * math.sin(math.radians(45.0)) / 9.81
        self.assertAlmostEqual(r["frames"][-1]["x"], ideal_range, delta=1e-3)
        self.assertAlmostEqual(r["frames"][-1]["t"], ideal_time, delta=1e-3)

    def test_long_low_gravity_lob_is_not_cut_off(self):
        # 50 m/s at 85 deg on the Moon flies for ~62 s
        r = motion.run(self.p(v0=50.0, angle=85.0, g=1.6))
        self.assertTrue(r["landed"])
        self.assertEqual(r["frames"][-1]["y"], 0.0)
        self.assertAlmostEqual(r["frames"][-1]["t"], 2 * 50 * math.sin(math.radians(85)) / 1.6, delta=0.01)

    def test_drag_force_opposes_motion_through_the_air(self):
        p = self.p(drag=0.05, wind=-6.0)
        for f in motion.run(p)["frames"]:
            vax, vay = f["vx"] - p["wind"], f["vy"]
            vair = math.hypot(vax, vay)
            fd = math.hypot(f["fdx"], f["fdy"])
            self.assertAlmostEqual(fd, p["drag"] * vair * vair, delta=1e-3 + 1e-3 * fd)
            self.assertLessEqual(f["fdx"] * vax + f["fdy"] * vay, 1e-6)

    def test_no_drag_means_no_drag_force(self):
        for f in motion.run(self.p(wind=9.0))["frames"]:
            self.assertEqual((f["fdx"], f["fdy"]), (0.0, 0.0))

    def test_vacuum_path_is_the_closed_form_parabola(self):
        r = motion.run(self.p(drag=0.1))
        vac = r["vacuum"]
        self.assertEqual(vac[0], [0.0, 0.0])
        self.assertAlmostEqual(vac[-1][0], 18.0 ** 2 / 9.81, delta=1e-3)
        self.assertAlmostEqual(max(q[1] for q in vac),
                               (18.0 * math.sin(math.radians(45))) ** 2 / (2 * 9.81), delta=0.01)

    def test_headwind_can_blow_a_draggy_ball_backwards(self):
        r = motion.run(self.p(drag=0.2, wind=-8.0))
        self.assertTrue(r["landed"])
        self.assertLess(r["frames"][-1]["x"], 0.0)


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

    def test_each_block_uses_its_own_material(self):
        base = dict(mass_a=1.0, mass_b=1.0, temp_a=90.0, temp_b=20.0, loss=0.0)
        ca_al = heat.run(self.p(material_a="copper", material_b="aluminum", **base))
        al_ca = heat.run(self.p(material_a="aluminum", material_b="copper", **base))
        t1 = (385.0 * 90 + 900.0 * 20) / (385.0 + 900.0)
        t2 = (900.0 * 90 + 385.0 * 20) / (900.0 + 385.0)
        self.assertAlmostEqual(ca_al["frames"][-1]["temp_a"], t1, delta=0.05)
        self.assertAlmostEqual(al_ca["frames"][-1]["temp_a"], t2, delta=0.05)
        self.assertEqual(ca_al["materials"]["a"]["id"], "copper")
        self.assertEqual(ca_al["materials"]["b"]["id"], "aluminum")
        self.assertNotEqual(ca_al["materials"]["a"]["rho"], ca_al["materials"]["b"]["rho"])

    def test_heat_packets_data_is_consistent(self):
        p = self.p()
        r = heat.run(p)
        last = r["frames"][-1]
        # with no leak, the heat moved A->B equals what B gained (m c dT)
        self.assertAlmostEqual(last["q"], 2.0 * 450.0 * (last["temp_b"] - 20.0),
                               delta=abs(last["q"]) * 2e-3 + 2.0)
        for f in r["frames"]:
            self.assertAlmostEqual(f["flow"], heat.G_CONTACT * (f["temp_a"] - f["temp_b"]), delta=0.05)

    def test_frames_are_time_ordered_and_end_settled(self):
        frames = heat.run(self.p())["frames"]
        ts = [f["t"] for f in frames]
        self.assertTrue(all(b > a for a, b in zip(ts, ts[1:])))
        self.assertLess(abs(frames[-1]["temp_a"] - frames[-1]["temp_b"]), heat.SETTLE_K + 0.002)

    def test_fast_small_blocks_are_resolved(self):
        # 0.1 kg copper pairs settle in seconds: the old fixed 2 s frame
        # spacing showed that as one jump
        r = heat.run(self.p(material_a="copper", material_b="copper", mass_a=0.1, mass_b=0.1))
        frames = r["frames"]
        self.assertLess(r["tau"], 1.5)
        early = [f for f in frames if f["t"] <= 3 * r["tau"]]
        self.assertGreaterEqual(len(early), 20)

    def test_equal_temperatures_give_one_frame(self):
        r = heat.run(self.p(temp_a=40.0, temp_b=40.0))
        self.assertEqual(len(r["frames"]), 1)

    def test_water_outside_liquid_range_is_flagged(self):
        self.assertEqual(heat.run(self.p())["notes"], [])
        self.assertIn("steam", heat.run(self.p(temp_a=140.0))["notes"][0])
        self.assertIn("ice", heat.run(self.p(material_a="iron", material_b="water",
                                              temp_a=90.0, temp_b=-15.0))["notes"][0])

    def test_ambient_leak_drags_both_toward_room(self):
        f = heat.run(self.p(loss=1.0))["frames"]
        self.assertLess(f[-1]["temp_a"], 90.0)
        self.assertGreater(f[-1]["temp_b"], 20.0)
        self.assertGreater(f[-1]["temp_a"], f[-1]["temp_b"])  # not fully settled yet


if __name__ == "__main__":
    unittest.main()
