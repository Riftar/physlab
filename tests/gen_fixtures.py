"""Generate golden fixtures deterministically. Run: python3 tests/gen_fixtures.py"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import spec
from physlab.server import validate
from physlab.topics import circuits, motion, heat, buoyancy, waves, pendulum, optics, pressure, energy, bounce, levers

FIX = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
# optional argv[1]: alternate output dir (used by the regen test)

GOLDEN = {
    "circuits": {"voltage": 6.0, "lamps": 2, "lamp_r": 20.0,
                 "internal_r": 0.5, "resistor": 10.0, "closed": True},
    "motion": {"v0": 18.0, "angle": 45.0, "mass": 1.0, "drag": 0.1,
               "wind": -3.0, "g": 9.81},
    "heat": {"material_a": "water", "mass_a": 1.0, "temp_a": 90.0,
             "material_b": "iron", "mass_b": 2.0, "temp_b": 20.0,
             "ambient": 25.0, "loss": 0.0},
    "buoyancy": {"shape": "sphere", "material": "ice", "size": 10.0, "fluid": "seawater",
                 "g": 9.81, "start": 10.0},
    "waves": {"f": 1.25, "amplitude": 2.0, "tension": 20.0, "mu": 200.0, "length": 2.0,
              "end": "free", "damping": 1.0},
    "pendulum": {"length": 0.8, "amplitude": 45.0, "mass": 0.5, "g": 9.81, "drag": 0.002},
    "optics": {"kind": "converging", "material": "flint", "radius": 15.0, "d_o": 25.0, "h_o": 3.0},
    "pressure": {"force": 120.0, "d1": 2.5, "d2": 20.0, "mass": 500.0, "stroke": 20.0, "fluid": "water"},
    "energy": {"track": "hill", "object": "solid_ball", "height": 6.0, "mass": 10.0, "friction": 0.02,
               "g": 9.81},
    "bounce": {"ball": "tennis", "surface": "hardwood", "height": 2.5, "g": 9.81, "air": True},
    "levers": {"m1": 0.25, "d1": 1.0, "m2": 0.55, "d2": 0.5, "beam": 1.0, "friction": 0.03, "start": -25.0,
               "g": 9.81},
}
RUNNERS = {"circuits": circuits.run, "motion": motion.run, "heat": heat.run,
           "buoyancy": buoyancy.run, "waves": waves.run, "pendulum": pendulum.run,
           "optics": optics.run, "pressure": pressure.run, "energy": energy.run,
           "bounce": bounce.run, "levers": levers.run}


def main():
    fix = sys.argv[1] if len(sys.argv) > 1 else FIX
    os.makedirs(fix, exist_ok=True)
    for tid, params in GOLDEN.items():
        topic = spec(tid)
        q = {k: [str(v).lower() if isinstance(v, bool) else str(v)]
             for k, v in params.items()}
        p, err = validate(topic, q)
        assert err is None, err
        out = RUNNERS[tid](p)
        with open(os.path.join(fix, tid + ".json"), "w") as f:
            json.dump(out, f, sort_keys=True, indent=1)
    print("fixtures written:", sorted(GOLDEN))


if __name__ == "__main__":
    main()
