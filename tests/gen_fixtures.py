"""Generate golden fixtures deterministically. Run: python3 tests/gen_fixtures.py"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import spec
from physlab.server import validate
from physlab.topics import circuits, motion, heat

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
}
RUNNERS = {"circuits": circuits.run, "motion": motion.run, "heat": heat.run}


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
