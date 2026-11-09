"""The quiz: "set the right parameter to make the simulation do X".

Each experiment has three questions - easy, medium, hard:
  easy    one input, the simplest model, one formula gets you there
  medium  one input, but a second step or a twist (other gravity, spin,
          internal resistance, a different sign convention ...)
  hard    usually two inputs that depend on each other, or physics no
          single formula covers (air drag, big swings, friction on a
          hilly track) - the simulation itself becomes the tool

A question is graded by RUNNING THE SIMULATION with the student's inputs
and measuring the outcome (where the ball landed, the measured period,
the image distance ...). So the grade always matches what the student
sees, and every valid answer counts (30 deg and 60 deg both hit the
mark). Each question lists reference solutions and common mistakes,
which the tests run through the same grader.

Points: easy 10, medium 20, hard 30, earned once; every wrong try
before the first correct one costs 25% (never below half). Revealing
the answer (allowed after 2 wrong tries) means no points.
"""

import math

POINTS = {"easy": 10, "medium": 20, "hard": 30}
LEVELS = ("easy", "medium", "hard")
REVEAL_AFTER = 2          # wrong tries before "show me the answer" unlocks


# ---------------- outcome metrics: (result, params) -> value or None ----------------
# None means a precondition failed; the metric's "fail" text explains why.

def _landing_x(res, p):
    return res["frames"][-1]["x"] if res.get("landed") else None


def _readout(label):
    def f(res, p):
        for r in res["readouts"]:
            if r["label"].startswith(label):
                return r["value"] if isinstance(r["value"], (int, float)) else None
        return None
    return f


def _final_temp(res, p):
    f = res["frames"][-1]
    return (f["temp_a"] + f["temp_b"]) / 2.0


def _floats(res, p):
    return 1.0 if res["viz"]["eq"]["state"] == "floats" else 0.0


def _level_rise_cm(res, p):
    from .topics import buoyancy
    return (res["frames"][-1]["level"] - buoyancy.FILL) * 100.0


def _floating_buoyancy(res, p):
    return res["frames"][-1]["fb"] if res["viz"]["eq"]["state"] == "floats" else None


def _wavelength(res, p):
    return res["viz"]["lambda"]


def _half_waves(res, p):
    """How many half-wavelengths fit on the rope (fixed end resonates at whole numbers)."""
    return p["f"] * 2.0 * p["length"] / res["viz"]["v"]


def _quarter_waves(res, p):
    """How many quarter-wavelengths fit (a free end resonates at odd numbers)."""
    return p["f"] * 4.0 * p["length"] / res["viz"]["v"]


def _image_distance(res, p):
    return res["viz"]["d_i"]


def _magnification(res, p):
    return res["viz"]["m"]


def _push_if_lifted(res, p):
    return p["force"] if res["viz"]["lifted"] else None


def _d2_if_lifted(res, p):
    return p["d2"] if res["viz"]["lifted"] else None


def _lift_mm(res, p):
    return res["frames"][-1]["x2"] * 1000.0 if res["viz"]["lifted"] else None


def _max_speed(res, p):
    return max(abs(f["v"]) for f in res["frames"])


def _height_if_over_hill(res, p):
    return p["height"] if res["frames"][-1]["x"] > 14.0 else None


METRICS = {
    "landing_x": {"fn": _landing_x, "label": "landing point", "unit": "m",
                  "fail": "The ball never landed inside the time we watched."},
    "current": {"fn": _readout("Current"), "label": "current", "unit": "A"},
    "lamp_voltage": {"fn": _readout("Voltage across each lamp"), "label": "voltage across each lamp", "unit": "V"},
    "lamp_power": {"fn": _readout("Lamp power"), "label": "power in each lamp", "unit": "W"},
    "final_temp": {"fn": _final_temp, "label": "final temperature", "unit": "°C"},
    "floats": {"fn": _floats, "label": "floats? (1 = yes, 0 = no)", "unit": ""},
    "level_rise_cm": {"fn": _level_rise_cm, "label": "water level rise", "unit": "cm"},
    "floating_buoyancy": {"fn": _floating_buoyancy, "label": "buoyant force while floating", "unit": "N",
                          "fail": "It sank, so it isn't floating at all."},
    "wavelength": {"fn": _wavelength, "label": "wavelength", "unit": "m"},
    "half_waves": {"fn": _half_waves, "label": "half-waves on the rope", "unit": ""},
    "quarter_waves": {"fn": _quarter_waves, "label": "quarter-waves on the rope", "unit": ""},
    "period": {"fn": _readout("Period, measured"), "label": "measured period", "unit": "s",
               "fail": "The pendulum didn't complete a full swing."},
    "image_distance": {"fn": _image_distance, "label": "image distance", "unit": "cm",
                       "fail": "No image: the candle is exactly at the focal point, so the rays leave parallel."},
    "magnification": {"fn": _magnification, "label": "magnification", "unit": "x",
                      "fail": "No image: the candle is exactly at the focal point."},
    "push_if_lifted": {"fn": _push_if_lifted, "label": "your push", "unit": "N",
                       "fail": "The car didn't move - that push is too weak."},
    "d2_if_lifted": {"fn": _d2_if_lifted, "label": "big piston diameter", "unit": "cm",
                     "fail": "The car didn't move - the big piston is too small for that push."},
    "lift_mm": {"fn": _lift_mm, "label": "car's rise", "unit": "mm",
                "fail": "The car didn't move - the push is too weak for that small piston."},
    "max_speed": {"fn": _max_speed, "label": "top speed", "unit": "m/s"},
    "height_if_over_hill": {"fn": _height_if_over_hill, "label": "start height", "unit": "m",
                            "fail": "The box never made it over the hill."},
}


def Q(**kw):
    kw.setdefault("points", POINTS[kw["difficulty"]])
    return kw


# ---------------- the questions ----------------

QUESTIONS = [
    # ---------------- projectile motion ----------------
    Q(id="motion-easy", topic="motion", difficulty="easy", title="Hit the 20 m mark",
      prompt="No air (drag 0), launch angle 45°, normal gravity. What launch speed makes the ball land "
             "on the 20 m mark?",
      setup={"angle": 45.0, "drag": 0.0, "wind": 0.0, "g": 9.81, "mass": 1.0},
      inputs=[{"param": "v0", "start": 10.0}],
      goal={"metric": "landing_x", "min": 19.5, "max": 20.5, "target": 20.0},
      feedback={"low": "It fell short - it needs more launch speed.",
                "high": "It flew too far - try a smaller launch speed."},
      explanation="Without air, Range = v0² · sin(2·angle) / g. At 45°, sin(90°) = 1, so Range = v0² / g. "
                  "Turn it round to find the speed: v0 = √(Range · g).",
      solution="v0 = √(20 m × 9.81 m/s²) = √196.2 ≈ 14.0 m/s.",
      solutions=[{"v0": 14.0}], wrong=[{"v0": 20.0}, {"v0": 10.0}]),
    Q(id="motion-medium", topic="motion", difficulty="medium", title="Golf on the Moon",
      prompt="On the Moon (g = 1.62 m/s², no air) you launch at 10 m/s. Which launch angle lands the ball "
             "50 m away?",
      setup={"v0": 10.0, "drag": 0.0, "wind": 0.0, "g": 1.62, "mass": 1.0},
      inputs=[{"param": "angle", "start": 45.0}],
      goal={"metric": "landing_x", "min": 49.0, "max": 51.0, "target": 50.0},
      feedback={"low": "Short of the mark. At 45° it would fly 61.7 m, so move your angle closer to 45°.",
                "high": "Too far - move the angle further away from 45° (either lower or higher)."},
      explanation="Range = v0² · sin(2·angle) / g, so sin(2·angle) = Range · g / v0². There are TWO angles "
                  "that work, adding up to 90° - a low fast one and a high slow one.",
      solution="sin(2θ) = 50 × 1.62 / 10² = 0.81 → 2θ = 54.1° or 125.9° → θ ≈ 27° or ≈ 63°. Both land at 50 m.",
      solutions=[{"angle": 27.0}, {"angle": 63.0}], wrong=[{"angle": 45.0}, {"angle": 15.0}]),
    Q(id="motion-hard", topic="motion", difficulty="hard", title="Into the wind",
      prompt="A light ball (0.5 kg, air drag k = 0.01 kg/m) is thrown into a 4 m/s headwind (wind = -4). "
             "Choose the launch speed AND angle so it lands on the 30 m mark.",
      setup={"drag": 0.01, "wind": -4.0, "g": 9.81, "mass": 0.5},
      inputs=[{"param": "v0", "start": 20.0}, {"param": "angle", "start": 45.0}],
      goal={"metric": "landing_x", "min": 29.0, "max": 31.0, "target": 30.0},
      feedback={"low": "Short - the drag and the headwind steal a lot of distance. Throw faster (or flatter).",
                "high": "Too far - ease off the speed a little."},
      explanation="With air, no simple formula gives the answer: drag grows with the square of the speed "
                  "through the air, and the headwind makes that speed even bigger. The no-air formula "
                  "(v0 = √(30 × 9.81) ≈ 17 m/s) falls well short - use it as a first guess, then let the "
                  "simulation guide you. Lower angles than 45° lose less to drag.",
      solution="For example 26 m/s at 40° lands at about 29.6 m (26 m/s at 30° also works). Many pairs work.",
      solutions=[{"v0": 26.0, "angle": 40.0}, {"v0": 26.0, "angle": 30.0}],
      wrong=[{"v0": 17.2, "angle": 45.0}]),

    # ---------------- electric circuits ----------------
    Q(id="circuits-easy", topic="circuits", difficulty="easy", title="Exactly 0.2 A",
      prompt="A 6 V battery (no internal resistance) lights one 20 Ω lamp. What extra series resistor makes "
             "the current exactly 0.2 A?",
      setup={"voltage": 6.0, "lamps": 1, "lamp_r": 20.0, "internal_r": 0.0, "closed": True},
      inputs=[{"param": "resistor", "start": 0.0}],
      goal={"metric": "current", "min": 0.195, "max": 0.205, "target": 0.2},
      feedback={"low": "Too little current - that's too much resistance.",
                "high": "Too much current - add more resistance."},
      explanation="Ohm's law for the whole loop: I = V / R_total. The total resistance needed is "
                  "R_total = V / I; the lamp already gives 20 Ω of it.",
      solution="R_total = 6 V / 0.2 A = 30 Ω, so the resistor is 30 Ω - 20 Ω = 10 Ω.",
      solutions=[{"resistor": 10.0}], wrong=[{"resistor": 30.0}, {"resistor": 0.0}]),
    Q(id="circuits-medium", topic="circuits", difficulty="medium", title="4 V per lamp",
      prompt="Two 20 Ω lamps in series on a battery with 0.5 Ω internal resistance. What battery voltage gives "
             "each lamp exactly 4 V?",
      setup={"lamps": 2, "lamp_r": 20.0, "internal_r": 0.5, "resistor": 0.0, "closed": True},
      inputs=[{"param": "voltage", "start": 6.0}],
      goal={"metric": "lamp_voltage", "min": 3.9, "max": 4.1, "target": 4.0},
      feedback={"low": "The lamps get less than 4 V - raise the voltage.",
                "high": "The lamps get more than 4 V - lower the voltage."},
      explanation="4 V across a 20 Ω lamp means I = 4 / 20 = 0.2 A. That current flows through EVERYTHING in "
                  "the loop - both lamps and the battery's own 0.5 Ω - so V = I × (R + R + r).",
      solution="I = 0.2 A, V = 0.2 A × (20 + 20 + 0.5) Ω = 8.1 V (8 V is not quite enough: 3.95 V per lamp).",
      solutions=[{"voltage": 8.1}], wrong=[{"voltage": 4.0}, {"voltage": 12.0}]),
    Q(id="circuits-hard", topic="circuits", difficulty="hard", title="Three 1-watt lamps",
      prompt="A 12 V battery (internal resistance 0.5 Ω) runs three lamps in series. Choose the lamp resistance "
             "AND an extra resistor so that each lamp uses exactly 1 W.",
      setup={"voltage": 12.0, "lamps": 3, "internal_r": 0.5, "closed": True},
      inputs=[{"param": "lamp_r", "start": 20.0}, {"param": "resistor", "start": 0.0}],
      goal={"metric": "lamp_power", "min": 0.95, "max": 1.05, "target": 1.0},
      feedback={"low": "Each lamp gets less than 1 W - too much total resistance, or lamps that are too big.",
                "high": "Each lamp gets more than 1 W - add resistance."},
      explanation="P = I² × R_lamp, and the current is I = V / (3·R_lamp + R_extra + r). Pick a lamp "
                  "resistance, work out the current it needs for 1 W (I = √(1 W / R_lamp)), then add the "
                  "resistor that brings the total to V / I. Lamps above about 15.7 Ω can't reach 1 W at all "
                  "(the resistor would have to be negative).",
      solution="For example R_lamp = 10 Ω: I = √(1/10) = 0.316 A, total = 12 / 0.316 = 37.9 Ω, so "
               "R_extra = 37.9 - 30 - 0.5 ≈ 7.4 Ω. (5 Ω with 11.3 Ω also works.)",
      solutions=[{"lamp_r": 10.0, "resistor": 7.4}, {"lamp_r": 5.0, "resistor": 11.3}],
      wrong=[{"lamp_r": 20.0, "resistor": 0.0}, {"lamp_r": 10.0, "resistor": 0.0}]),

    # ---------------- heat ----------------
    Q(id="heat-easy", topic="heat", difficulty="easy", title="Meet at 50 °C",
      prompt="Block A is 1 kg of water at 80 °C. Block B is 1 kg of water too. What starting temperature for "
             "B makes them meet at 50 °C (no heat leak)?",
      setup={"material_a": "water", "mass_a": 1.0, "temp_a": 80.0, "material_b": "water", "mass_b": 1.0,
             "loss": 0.0},
      inputs=[{"param": "temp_b", "start": 40.0}],
      goal={"metric": "final_temp", "min": 49.5, "max": 50.5, "target": 50.0},
      feedback={"low": "They met below 50 °C - B should start warmer.",
                "high": "They met above 50 °C - B should start colder."},
      explanation="Two equal blocks of the same material have the same heat capacity m·c, so they meet "
                  "exactly halfway between their starting temperatures.",
      solution="50 °C is halfway between 80 °C and 20 °C, so B starts at 20 °C.",
      solutions=[{"temp_b": 20.0}], wrong=[{"temp_b": 50.0}, {"temp_b": 0.0}]),
    Q(id="heat-medium", topic="heat", difficulty="medium", title="How much iron?",
      prompt="1 kg of water at 90 °C touches a block of iron at 20 °C. How many kg of iron make them meet at "
             "70 °C?",
      setup={"material_a": "water", "mass_a": 1.0, "temp_a": 90.0, "material_b": "iron", "temp_b": 20.0,
             "loss": 0.0},
      inputs=[{"param": "mass_b", "start": 1.0}],
      goal={"metric": "final_temp", "min": 69.5, "max": 70.5, "target": 70.0},
      feedback={"low": "They met below 70 °C - that's too much iron.",
                "high": "They met above 70 °C - you need more iron to cool the water down."},
      explanation="Heat lost by the water = heat gained by the iron: m_w c_w (90 - 70) = m_i c_i (70 - 20). "
                  "Water's c is 4186 J/(kg·K), iron's only 450, so you need a lot of iron.",
      solution="m_i = 1 × 4186 × 20 / (450 × 50) ≈ 3.7 kg.",
      solutions=[{"mass_b": 3.7}], wrong=[{"mass_b": 1.0}, {"mass_b": 0.4}]),
    Q(id="heat-hard", topic="heat", difficulty="hard", title="Any material will do",
      prompt="2 kg of water at 60 °C touches block B at 10 °C. Choose B's material AND mass so that they meet "
             "at exactly 50 °C.",
      setup={"material_a": "water", "mass_a": 2.0, "temp_a": 60.0, "temp_b": 10.0, "loss": 0.0},
      inputs=[{"param": "material_b", "start": "iron"}, {"param": "mass_b", "start": 1.0}],
      goal={"metric": "final_temp", "min": 49.5, "max": 50.5, "target": 50.0},
      feedback={"low": "They met below 50 °C - block B soaks up too much heat (less mass, or a smaller c).",
                "high": "They met above 50 °C - block B needs more heat capacity (more mass, or a bigger c)."},
      explanation="The water gives 2 × 4186 × (60 - 50) = 83 720 J. Block B must take exactly that while "
                  "warming 40 °C, so m_B × c_B = 83 720 / 40 = 2093 J/K. Any material works if the mass "
                  "fits: m_B = 2093 / c_B.",
      solution="Water 0.5 kg, aluminum 2.33 kg, iron 4.65 kg or copper 5.44 kg - all give m·c = 2093 J/K.",
      solutions=[{"material_b": "water", "mass_b": 0.5}, {"material_b": "iron", "mass_b": 4.65},
                 {"material_b": "aluminum", "mass_b": 2.35}],
      wrong=[{"material_b": "iron", "mass_b": 0.5}, {"material_b": "copper", "mass_b": 2.0}]),

    # ---------------- floating & sinking ----------------
    Q(id="buoyancy-easy", topic="buoyancy", difficulty="easy", title="Make iron float",
      prompt="A 12 cm iron block (7874 kg/m³) is dropped into the tank. Choose a liquid that makes it FLOAT.",
      setup={"shape": "cube", "material": "iron", "size": 12.0, "g": 9.81, "start": 15.0},
      inputs=[{"param": "fluid", "start": "water"}],
      goal={"metric": "floats", "min": 1.0, "max": 1.0, "target": 1.0, "text": "The iron block must float."},
      feedback={"low": "It sank: this liquid is less dense than iron."},
      explanation="Something floats when it is less dense than the liquid. Iron is 7874 kg/m³ - much denser "
                  "than water (998), sea water (1025), oil or honey.",
      solution="Only mercury (13 534 kg/m³) is denser than iron, so iron floats on it.",
      solutions=[{"fluid": "mercury"}], wrong=[{"fluid": "water"}, {"fluid": "honey"}]),
    Q(id="buoyancy-medium", topic="buoyancy", difficulty="medium", title="Raise the water 1 cm",
      prompt="A pine cube (510 kg/m³) floats in the water tank (1 m × 0.4 m of water surface). What side length "
             "makes the water level rise by exactly 1 cm?",
      setup={"shape": "cube", "material": "pine", "fluid": "water", "g": 9.81, "start": 15.0},
      inputs=[{"param": "size", "start": 12.0}],
      goal={"metric": "level_rise_cm", "min": 0.95, "max": 1.05, "target": 1.0},
      feedback={"low": "The water rose less than 1 cm - use a bigger block.",
                "high": "The water rose more than 1 cm - use a smaller block."},
      explanation="A floater pushes aside its own weight of water: V_sub = (ρ_pine / ρ_water) × V. That water "
                  "spreads over the tank: rise = V_sub / (1 m × 0.4 m). So the block's volume must be "
                  "V = 0.01 m × 0.4 m² × 998 / 510.",
      solution="V = 0.004 × 998 / 510 = 0.00783 m³, side = ∛0.00783 ≈ 0.199 m ≈ 19.9 cm.",
      solutions=[{"size": 19.9}], wrong=[{"size": 15.9}, {"size": 25.0}]),
    Q(id="buoyancy-hard", topic="buoyancy", difficulty="hard", title="Float with a 20 N push",
      prompt="In sea water, choose a material AND cube size so that the object floats and the water pushes up "
             "on it with exactly 20 N.",
      setup={"shape": "cube", "fluid": "seawater", "g": 9.81, "start": 15.0},
      inputs=[{"param": "material", "start": "pine"}, {"param": "size", "start": 12.0}],
      goal={"metric": "floating_buoyancy", "min": 19.0, "max": 21.0, "target": 20.0},
      feedback={"low": "Floating, but the push is less than 20 N - the object is too light (bigger block).",
                "high": "Floating, but the push is more than 20 N - the object is too heavy (smaller block)."},
      explanation="For anything FLOATING, the buoyant force equals its weight: F_b = ρ_obj × s³ × g. So you "
                  "need a material that floats in sea water (cork, pine or ice) and s³ = 20 N / (ρ_obj × g).",
      solution="Cork: s = ∛(20 / (240 × 9.81)) ≈ 20.4 cm; pine: ≈ 15.9 cm; ice: ≈ 13.0 cm.",
      solutions=[{"material": "cork", "size": 20.5}, {"material": "pine", "size": 16.0},
                 {"material": "ice", "size": 13.0}],
      wrong=[{"material": "iron", "size": 6.5}, {"material": "pine", "size": 20.0}]),

    # ---------------- waves ----------------
    Q(id="waves-easy", topic="waves", difficulty="easy", title="2-metre waves",
      prompt="The rope carries waves at 10 m/s (tension 20 N, 200 g/m). What shaking frequency makes waves "
             "exactly 2 m long?",
      setup={"tension": 20.0, "mu": 200.0, "length": 4.0, "end": "open", "amplitude": 3.0, "damping": 1.0},
      inputs=[{"param": "f", "start": 1.0}],
      goal={"metric": "wavelength", "min": 1.95, "max": 2.05, "target": 2.0},
      feedback={"low": "The waves are shorter than 2 m - shake more slowly.",
                "high": "The waves are longer than 2 m - shake faster."},
      explanation="v = f × λ, and the rope fixes v. So f = v / λ.",
      solution="f = 10 m/s ÷ 2 m = 5 Hz.",
      solutions=[{"f": 5.0}], wrong=[{"f": 2.0}, {"f": 1.0}]),
    Q(id="waves-medium", topic="waves", difficulty="medium", title="Three loops",
      prompt="A 4 m rope tied to a wall (200 g/m) is shaken at 2.5 Hz. What tension makes it resonate with "
             "exactly 3 loops?",
      setup={"f": 2.5, "mu": 200.0, "length": 4.0, "end": "fixed", "amplitude": 3.0, "damping": 1.0},
      inputs=[{"param": "tension", "start": 20.0}],
      goal={"metric": "half_waves", "min": 2.94, "max": 3.06, "target": 3.0,
            "text": "Exactly 3 half-waves (loops) on the rope."},
      feedback={"low": "Fewer than 3 loops - the waves are too long, so the rope is too tight (less tension).",
                "high": "More than 3 loops - the waves are too short, so the rope needs more tension."},
      explanation="A rope fixed at the far end resonates when it holds a whole number of half-waves: "
                  "f_n = n × v / (2L). For n = 3 the wave speed must be v = 2 L f / 3, and v = √(T/μ) "
                  "gives the tension T = μ v².",
      solution="v = 2 × 4 × 2.5 / 3 = 6.67 m/s, T = 0.2 kg/m × 6.67² ≈ 8.9 N.",
      solutions=[{"tension": 8.9}], wrong=[{"tension": 20.0}, {"tension": 4.5}]),
    Q(id="waves-hard", topic="waves", difficulty="hard", title="Free end, second mode",
      prompt="A 3 m rope with a FREE end (a ring on a pole) is shaken at 2 Hz. Choose the tension AND the mass "
             "per metre so it resonates in its second mode.",
      setup={"f": 2.0, "length": 3.0, "end": "free", "amplitude": 3.0, "damping": 1.0},
      inputs=[{"param": "tension", "start": 20.0}, {"param": "mu", "start": 200.0}],
      goal={"metric": "quarter_waves", "min": 2.94, "max": 3.06, "target": 3.0,
            "text": "Second mode of a free end: exactly 3 quarter-waves on the rope."},
      feedback={"low": "Not enough wave on the rope - the wave speed is too high (less tension or a heavier rope).",
                "high": "Too much wave on the rope - the wave speed is too low (more tension or a lighter rope)."},
      explanation="A free end makes a loop's peak at the end, so the rope holds an ODD number of quarter-waves: "
                  "f_n = (2n - 1) v / (4L). The second mode has 3 quarter-waves, so v = 4 L f / 3 = 8 m/s. "
                  "Any tension and mass per metre with √(T/μ) = 8 m/s, i.e. T/μ = 64, works.",
      solution="v = 4 × 3 × 2 / 3 = 8 m/s → T = 64 × μ: e.g. μ = 200 g/m with T = 12.8 N, or μ = 500 g/m "
               "with T = 32 N.",
      solutions=[{"tension": 12.8, "mu": 200.0}, {"tension": 32.0, "mu": 500.0}],
      wrong=[{"tension": 28.8, "mu": 200.0}, {"tension": 20.0, "mu": 200.0}]),

    # ---------------- pendulum ----------------
    Q(id="pendulum-easy", topic="pendulum", difficulty="easy", title="A 2-second pendulum",
      prompt="Small swings (10°) on Earth. What string length makes one full swing take exactly 2.0 s?",
      setup={"amplitude": 10.0, "mass": 1.0, "g": 9.81, "drag": 0.0},
      inputs=[{"param": "length", "start": 0.5}],
      goal={"metric": "period", "min": 1.98, "max": 2.02, "target": 2.0},
      feedback={"low": "The swing is too quick - make the string longer.",
                "high": "The swing is too slow - make the string shorter."},
      explanation="T = 2π √(L / g), so L = g × (T / 2π)².",
      solution="L = 9.81 × (2 / 2π)² ≈ 0.99 m - the famous 'seconds pendulum' of grandfather clocks.",
      solutions=[{"length": 0.99}], wrong=[{"length": 2.0}, {"length": 0.5}]),
    Q(id="pendulum-medium", topic="pendulum", difficulty="medium", title="A clock on Mars",
      prompt="On Mars gravity is only 3.71 m/s². With small swings, what length makes one full swing take "
             "exactly 3.0 s?",
      setup={"amplitude": 10.0, "mass": 1.0, "g": 3.71, "drag": 0.0},
      inputs=[{"param": "length", "start": 1.0}],
      goal={"metric": "period", "min": 2.98, "max": 3.02, "target": 3.0},
      feedback={"low": "Too quick - a longer string.", "high": "Too slow - a shorter string."},
      explanation="Same formula, different g: L = g × (T / 2π)². Weaker gravity means a shorter string for "
                  "the same period.",
      solution="L = 3.71 × (3 / 2π)² ≈ 0.85 m.",
      solutions=[{"length": 0.85}], wrong=[{"length": 2.24}, {"length": 1.0}]),
    Q(id="pendulum-hard", topic="pendulum", difficulty="hard", title="2 seconds with big swings",
      beyond_formula=True,
      prompt="Now it is released from 70°. What length makes one full swing take exactly 2.0 s?",
      setup={"amplitude": 70.0, "mass": 1.0, "g": 9.81, "drag": 0.0},
      inputs=[{"param": "length", "start": 0.99}],
      goal={"metric": "period", "min": 1.985, "max": 2.015, "target": 2.0},
      feedback={"low": "Too quick - a little longer string.",
                "high": "Too slow: big swings take longer than the small-angle formula says - shorten it."},
      explanation="The small-angle answer (0.99 m) is too slow here: at 70° the swing takes about 10% "
                  "longer. Use the exact formula T = 2π √(L/g) / AGM(1, cos(θ0/2)) (AGM ≈ 0.907 at 70°), "
                  "or experiment with the simulation.",
      solution="L = g × (T × AGM / 2π)² = 9.81 × (2 × 0.907 / 2π)² ≈ 0.82 m.",
      solutions=[{"length": 0.82}], wrong=[{"length": 0.99}, {"length": 0.7}]),

    # ---------------- lenses ----------------
    Q(id="optics-easy", topic="optics", difficulty="easy", title="Focus on the screen",
      prompt="A crown-glass lens (R = 20 cm, so f = 19.2 cm) should make a sharp image on a screen 40 cm "
             "behind it. Where do you put the candle?",
      setup={"kind": "converging", "material": "crown", "radius": 20.0, "h_o": 4.0},
      inputs=[{"param": "d_o", "start": 60.0}],
      goal={"metric": "image_distance", "min": 39.0, "max": 41.0, "target": 40.0},
      feedback={"low": "The image forms too close to the lens - move the candle closer to the lens.",
                "high": "The image forms too far away - move the candle further from the lens."},
      explanation="Thin-lens equation: 1/f = 1/d_o + 1/d_i. Solve for the candle: 1/d_o = 1/f - 1/d_i.",
      solution="1/d_o = 1/19.23 - 1/40 = 0.0270 → d_o ≈ 37 cm.",
      solutions=[{"d_o": 37.0}], wrong=[{"d_o": 40.0}, {"d_o": 21.0}]),
    Q(id="optics-medium", topic="optics", difficulty="medium", title="A 3x magnifier",
      prompt="Use the same lens (f = 19.2 cm) as a magnifying glass: where must the candle be for an upright "
             "image 3 times bigger?",
      setup={"kind": "converging", "material": "crown", "radius": 20.0, "h_o": 2.0},
      inputs=[{"param": "d_o", "start": 30.0}],
      goal={"metric": "magnification", "min": 2.85, "max": 3.15, "target": 3.0},
      feedback={"low": "Less than 3x (or upside down) - move the candle a little closer to the focal point "
                       "from inside it.",
                "high": "More than 3x - move the candle a bit closer to the lens."},
      explanation="Upright and bigger means a virtual image: the candle is inside the focal length. With "
                  "m = -d_i/d_o = 3 the image is at d_i = -3 d_o; put that into 1/f = 1/d_o + 1/d_i.",
      solution="1/f = 1/d_o - 1/(3 d_o) = 2/(3 d_o) → d_o = 2f/3 = 2 × 19.23 / 3 ≈ 12.8 cm.",
      solutions=[{"d_o": 12.8}], wrong=[{"d_o": 25.6}, {"d_o": 6.4}]),
    Q(id="optics-hard", topic="optics", difficulty="hard", title="Design the lens",
      prompt="The candle stands 30 cm from the lens. Choose the lens material AND the curvature R so that a "
             "real image forms exactly 60 cm behind the lens.",
      setup={"kind": "converging", "d_o": 30.0, "h_o": 4.0},
      inputs=[{"param": "material", "start": "crown"}, {"param": "radius", "start": 30.0}],
      goal={"metric": "image_distance", "min": 58.5, "max": 61.5, "target": 60.0},
      feedback={"low": "The image is too close - the lens is too strong (flatter faces or less dense material).",
                "high": "The image is too far (or virtual) - the lens is too weak or too strong for a real image "
                        "at 60 cm; aim for f = 20 cm."},
      explanation="First the thin-lens equation: 1/f = 1/30 + 1/60 = 1/20, so f = 20 cm. Then the lensmaker's "
                  "equation for a symmetric lens, f = R / (2(n - 1)), gives R = 2 f (n - 1) = 40 cm × (n - 1).",
      solution="Crown glass (n = 1.52): R ≈ 20.8 cm; acrylic: 19.6 cm; flint: 24.8 cm; water: 13.3 cm; "
               "diamond: 56.7 cm.",
      solutions=[{"material": "crown", "radius": 20.8}, {"material": "flint", "radius": 24.8},
                 {"material": "acrylic", "radius": 19.6}],
      wrong=[{"material": "crown", "radius": 20.0}, {"material": "diamond", "radius": 20.8}]),

    # ---------------- pressure ----------------
    Q(id="pressure-easy", topic="pressure", difficulty="easy", title="Just enough push",
      prompt="A 1000 kg car sits on a 30 cm piston; you push on a 3 cm piston. What is the SMALLEST push that "
             "still lifts the car? (Within 10 N.)",
      setup={"d1": 3.0, "d2": 30.0, "mass": 1000.0, "stroke": 25.0, "fluid": "oil"},
      inputs=[{"param": "force", "start": 50.0}],
      goal={"metric": "push_if_lifted", "min": 98.2, "max": 108.0, "target": 100.0,
            "text": "Lift the car with a push of at most 108 N."},
      feedback={"high": "It lifts, but you're pushing harder than you need to - find the smallest push."},
      explanation="The car weighs 1000 × 9.81 = 9810 N. The pistons' areas differ by (30 / 3)² = 100x, so "
                  "the push needed is only 1/100 of the weight.",
      solution="9810 N ÷ 100 = 98.1 N, so a 100 N push (or anything from about 99 N) lifts the car.",
      solutions=[{"force": 100.0}], wrong=[{"force": 90.0}, {"force": 200.0}]),
    Q(id="pressure-medium", topic="pressure", difficulty="medium", title="How big a piston?",
      prompt="You can push with 100 N on a 2 cm piston. The car is 1500 kg. What is the smallest big-piston "
             "diameter that lifts it? (Within 2 cm.)",
      setup={"force": 100.0, "d1": 2.0, "mass": 1500.0, "stroke": 25.0, "fluid": "oil"},
      inputs=[{"param": "d2", "start": 10.0}],
      goal={"metric": "d2_if_lifted", "min": 24.3, "max": 26.3, "target": 25.0,
            "text": "Lift the car with a big piston no wider than 26.3 cm."},
      feedback={"high": "It lifts, but the piston is bigger than it needs to be - find the smallest."},
      explanation="You need A2 / A1 ≥ weight / push = 14 715 / 100 = 147. Areas go with diameter squared, so "
                  "d2 / d1 ≥ √147.",
      solution="d2 ≥ 2 cm × √147.15 ≈ 24.3 cm.",
      solutions=[{"d2": 25.0}], wrong=[{"d2": 24.0}, {"d2": 40.0}]),
    Q(id="pressure-hard", topic="pressure", difficulty="hard", title="Lift it exactly 5 mm",
      prompt="Pushing with 200 N, lift the 1000 kg car on its 30 cm piston by exactly 5 mm in one push of at "
             "most 40 cm. Choose the small piston's diameter AND how far you push.",
      setup={"force": 200.0, "d2": 30.0, "mass": 1000.0, "fluid": "oil"},
      inputs=[{"param": "d1", "start": 3.0}, {"param": "stroke", "start": 25.0}],
      goal={"metric": "lift_mm", "min": 4.9, "max": 5.1, "target": 5.0},
      feedback={"low": "The car rose less than 5 mm - push further, or use a wider small piston.",
                "high": "The car rose more than 5 mm - push less far, or use a thinner small piston."},
      explanation="Two conditions. To lift at all: 200 N ≥ 9810 N × (d1/30)², so d1 ≤ 4.28 cm. To rise "
                  "5 mm: push distance × (d1/30)² = 5 mm, with the push no more than 40 cm, so d1 ≥ 3.35 cm. "
                  "Near 4.28 cm the push barely beats the car, so your hand can only move very slowly - "
                  "watch the simulation.",
      solution="For example d1 = 4 cm: (4/30)² = 1/56.25, push = 5 mm × 56.25 ≈ 28.1 cm. (3.5 cm with a "
               "36.7 cm push works too.)",
      solutions=[{"d1": 4.0, "stroke": 28.1}, {"d1": 3.5, "stroke": 36.7}],
      wrong=[{"d1": 3.0, "stroke": 25.0}, {"d1": 5.0, "stroke": 18.0}]),

    # ---------------- energy ramp ----------------
    Q(id="energy-easy", topic="energy", difficulty="easy", title="8 m/s at the bottom",
      prompt="A box slides in the half-pipe with no friction. From what height must you let go so it reaches "
             "8 m/s at the bottom?",
      setup={"track": "halfpipe", "object": "box", "mass": 20.0, "friction": 0.0, "g": 9.81},
      inputs=[{"param": "height", "start": 2.0}],
      goal={"metric": "max_speed", "min": 7.85, "max": 8.15, "target": 8.0},
      feedback={"low": "Too slow at the bottom - start higher.", "high": "Too fast - start lower."},
      explanation="Height energy turns into motion energy: m g h = ½ m v². The mass cancels, so "
                  "h = v² / (2 g).",
      solution="h = 8² / (2 × 9.81) ≈ 3.26 m (3.3 m works).",
      solutions=[{"height": 3.3}], wrong=[{"height": 8.0}, {"height": 6.5}]),
    Q(id="energy-medium", topic="energy", difficulty="medium", title="Rolling to 8 m/s",
      prompt="Now a SOLID BALL rolls in the half-pipe (no friction). From what height does it reach 8 m/s at "
             "the bottom?",
      setup={"track": "halfpipe", "object": "solid_ball", "mass": 20.0, "friction": 0.0, "g": 9.81},
      inputs=[{"param": "height", "start": 3.3}],
      goal={"metric": "max_speed", "min": 7.85, "max": 8.15, "target": 8.0},
      feedback={"low": "Too slow - part of the energy goes into spinning, so start higher.",
                "high": "Too fast - start lower."},
      explanation="A rolling ball also spins: m g h = ½ m v² (1 + k) with k = 2/5 for a solid ball. So it "
                  "needs a higher start than a sliding box: h = v² (1 + k) / (2 g).",
      solution="h = 64 × 1.4 / 19.62 ≈ 4.57 m (4.6 m works). The box only needed 3.26 m.",
      solutions=[{"height": 4.6}], wrong=[{"height": 3.3}, {"height": 8.0}]),
    Q(id="energy-hard", topic="energy", difficulty="hard", title="Just over the hill",
      beyond_formula=True,
      prompt="On the drop-and-hill track, a box slides with friction μ = 0.1. What is the LOWEST start height "
             "(to within 0.3 m) that still gets it over the 3 m hill?",
      setup={"track": "hill", "object": "box", "mass": 20.0, "friction": 0.1, "g": 9.81},
      inputs=[{"param": "height", "start": 3.5}],
      goal={"metric": "height_if_over_hill", "min": 5.0, "max": 5.4, "target": 5.2,
            "text": "Get over the hill, starting no higher than 5.4 m."},
      feedback={"high": "It made it over, but you started higher than you need - go lower."},
      explanation="Without friction, anything above 3 m would make it. But friction turns energy into heat "
                  "on the long way down and up (heat = μ N × distance), so you need extra height - and "
                  "the normal force changes along the curves, so no simple formula gives it. Experiment: "
                  "the energy bar's grey part shows the heat.",
      solution="About 5.1 m: from 5.0 m the box just fails, from 5.1 m it makes it over.",
      solutions=[{"height": 5.2}, {"height": 5.1}], wrong=[{"height": 3.5}, {"height": 6.0}]),
]

BY_ID = {q["id"]: q for q in QUESTIONS}


# ---------------- grading ----------------

def goal_text(q):
    g = q["goal"]
    if g.get("text"):
        return g["text"]
    m = METRICS[g["metric"]]
    return ("The %s should be between %s and %s %s." % (m["label"], _fmt(g["min"]), _fmt(g["max"]),
                                                          m["unit"])).replace(" .", ".")


def _fmt(x):
    return ("%.3f" % x).rstrip("0").rstrip(".")


def check_inputs(q, raw):
    """Validate a student's inputs against the question: only the allowed
    parameters, numbers inside the experiment's range, valid choices.
    Returns (values, error)."""
    from . import spec
    if not isinstance(raw, dict):
        return None, "inputs must be an object"
    specs = {p["id"]: p for p in spec(q["topic"])["params"]}
    allowed = [i["param"] for i in q["inputs"]]
    extra = [k for k in raw if k not in allowed]
    if extra:
        return None, "you can't change '%s' in this question" % str(extra[0])[:40]
    out = {}
    for pid in allowed:
        if pid not in raw:
            return None, "missing an answer for '%s'" % pid
        sp, v = specs[pid], raw[pid]
        if sp["kind"] == "select":
            if v not in [c["id"] for c in sp["choices"]]:
                return None, "'%s' is not one of the choices" % str(v)[:40]
            out[pid] = v
        else:
            try:
                x = float(v)
            except (TypeError, ValueError):
                return None, "'%s' must be a number" % pid
            if not math.isfinite(x) or x < sp["min"] or x > sp["max"]:
                return None, "'%s' must be between %s and %s" % (pid, _fmt(sp["min"]), _fmt(sp["max"]))
            out[pid] = int(round(x)) if sp["kind"] == "integer" else round(x, 4)
    return out, None


def build_params(q, inputs):
    from . import spec
    p = {x["id"]: x["default"] for x in spec(q["topic"])["params"]}
    p.update(q["setup"])
    p.update(inputs)
    return p


def grade(q, inputs):
    """Run the experiment with the student's (validated) inputs and judge
    the outcome. Returns {correct, value, message, params, result}."""
    from .server import validate, RUNNERS
    from . import spec
    params = build_params(q, inputs)
    query = {k: [("1" if v else "0") if isinstance(v, bool) else str(v)] for k, v in params.items()}
    params, err = validate(spec(q["topic"]), query)
    if err:
        raise ValueError(err)
    result = RUNNERS[q["topic"]](params)
    g, m = q["goal"], METRICS[q["goal"]["metric"]]
    value = m["fn"](result, params)
    if value is None:
        correct, message = False, m.get("fail", "That didn't work.")
    else:
        correct = g["min"] - 1e-9 <= value <= g["max"] + 1e-9
        if correct:
            message = "Spot on: the %s is %s %s." % (m["label"], _fmt(value), m["unit"])
        else:
            side = "low" if value < g["min"] else "high"
            hint = q["feedback"].get(side, "")
            message = "The %s came out at %s %s (goal: %s to %s %s). %s" % (
                m["label"], _fmt(value), m["unit"], _fmt(g["min"]), _fmt(g["max"]), m["unit"], hint)
    return {"correct": correct, "value": value, "message": message.strip(), "params": params,
            "result": dict(result, topic=q["topic"], params=params)}


def points_for(q, wrong_before, already_solved, revealed):
    """Points for a correct answer."""
    if already_solved or revealed:
        return 0
    # round half UP (Python's round() would turn 22.5 into 22)
    return int(q["points"] * max(0.5, 1.0 - 0.25 * wrong_before) + 0.5)


def public(q):
    """What the browser may see before solving: no solutions."""
    from . import spec
    specs = {p["id"]: p for p in spec(q["topic"])["params"]}
    setup = []
    for k, v in q["setup"].items():
        sp = specs[k]
        if sp["kind"] == "select":
            v = next(c["label"] for c in sp["choices"] if c["id"] == v)
        elif sp["kind"] == "boolean":
            v = "yes" if v else "no"
        setup.append({"id": k, "label": sp["label"], "value": v, "unit": sp.get("unit", "")})
    inputs = []
    for i in q["inputs"]:
        sp = dict(specs[i["param"]])
        sp["start"] = i["start"]
        inputs.append(sp)
    g = q["goal"]
    return {"id": q["id"], "topic": q["topic"], "difficulty": q["difficulty"], "title": q["title"],
            "prompt": q["prompt"], "points": q["points"], "setup": setup, "setup_values": q["setup"],
            "inputs": inputs,
            "goal": {"metric": g["metric"], "min": g["min"], "max": g["max"], "target": g.get("target"),
                     "unit": METRICS[g["metric"]]["unit"], "text": goal_text(q)}}
