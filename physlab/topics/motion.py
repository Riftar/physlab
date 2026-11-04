"""Projectile motion: gravity + quadratic air drag + wind.

Semi-implicit Euler at fixed dt. Same validated params -> byte-equal
frames. When drag is 0 the trajectory matches the closed form exactly
(verified in tests to integrator tolerance).
"""

import math

DT = 0.001
RECORD_EVERY = 50       # one frame per 0.05 s
MAX_T = 30.0


def _accel(vx, vy, p):
    rvx, rvy = vx - p["wind"], vy
    speed = math.sqrt(rvx * rvx + rvy * rvy)
    k = p["drag"] / p["mass"]
    return (-k * rvx * speed, -p["g"] - k * rvy * speed)


def run(p):
    rad = math.radians(p["angle"])
    vx, vy = p["v0"] * math.cos(rad), p["v0"] * math.sin(rad)
    x, y, t = 0.0, 0.0, 0.0
    frames = [{"t": 0.0, "x": 0.0, "y": 0.0, "vx": round(vx, 4), "vy": round(vy, 4)}]
    peak = 0.0
    while t < MAX_T:
        ax, ay = _accel(vx, vy, p)
        vx += ax * DT
        vy += ay * DT
        x += vx * DT
        y += vy * DT
        t += DT
        peak = max(peak, y)
        if y >= 0.0:
            if abs(round(t / DT) % RECORD_EVERY) < 1e-9 and t > 0:
                frames.append({"t": round(t, 4), "x": round(x, 4), "y": round(y, 4),
                               "vx": round(vx, 4), "vy": round(vy, 4)})
        else:
            # interpolate the landing point between the last two steps
            frac = (y + vy * DT) / (vy * DT) if vy * DT != 0 else 0.0
            frames.append({"t": round(t, 4), "x": round(x - vx * DT * (1.0 - frac), 4),
                           "y": 0.0, "vx": round(vx, 4), "vy": round(vy, 4)})
            break
    speed = math.hypot(frames[-1]["vx"], frames[-1]["vy"])
    ideal = p["v0"] * p["v0"] * math.sin(2.0 * rad) / p["g"]
    return {
        "frames": frames,
        "readouts": [
            {"label": "Distance", "value": frames[-1]["x"], "unit": "m"},
            {"label": "Flight time", "value": frames[-1]["t"], "unit": "s"},
            {"label": "Peak height", "value": round(peak, 3), "unit": "m"},
            {"label": "Landing speed", "value": round(speed, 3), "unit": "m/s"},
        ],
        "formula": [
            {"expr": "Range = v0^2 * sin(2*angle) / g",
             "values": {"v0": round(p["v0"], 2), "angle": round(p["angle"], 1),
                        "g": round(p["g"], 2),
                        "Range": round(ideal, 3) if p["drag"] == 0.0 else None}},
            {"expr": "a = -g - (k/m) * v * |v|",
             "values": {"g": round(p["g"], 2), "k": round(p["drag"], 3),
                        "m": round(p["mass"], 2)}},
        ],
    }
