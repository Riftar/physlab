"""Projectile motion: gravity + quadratic air drag + wind.

    F_drag = -k * |v_air| * v_air,   v_air = v - wind   (k in kg/m)
    a      = g_vec + F_drag / m

Wind only acts THROUGH drag: with k = 0 the air can blow all it likes and
the ball does not care (a teaching point the scene makes visible).

Heun (trapezoidal, 2nd order) steps at fixed dt: exact for constant
gravity, 2nd-order accurate with drag. Same validated params ->
byte-equal frames. With drag 0 the path matches the closed form to
rounding (verified in tests). Each frame carries the drag
force so the client can draw the free-body arrows without re-deriving
physics, and the result carries the no-air parabola for comparison.
"""

import math

DT = 0.001
# frame spacing: ~120 frames per (no-air) flight, between 5 ms and 50 ms,
# so a 0.3 s hop is as smooth on screen as a 60 s lob
FRAMES_PER_FLIGHT = 120
RECORD_MIN, RECORD_MAX = 5, 50      # in steps of DT
# longest vacuum flight the spec allows is 2 * 50 m/s / 1.6 m/s^2 = 62.5 s;
# drag can lengthen the fall, so leave generous headroom
MAX_T = 120.0
VACUUM_POINTS = 60


def _accel(vx, vy, p):
    rvx, rvy = vx - p["wind"], vy
    speed = math.sqrt(rvx * rvx + rvy * rvy)
    k = p["drag"] / p["mass"]
    return (-k * rvx * speed, -p["g"] - k * rvy * speed)


def drag_force(vx, vy, p):
    """Drag force in newtons on the ball moving at (vx, vy) through wind."""
    rvx, rvy = vx - p["wind"], vy
    speed = math.sqrt(rvx * rvx + rvy * rvy)
    return (-p["drag"] * rvx * speed, -p["drag"] * rvy * speed)


def _frame(t, x, y, vx, vy, p):
    fx, fy = drag_force(vx, vy, p)
    return {"t": round(t, 4), "x": round(x, 4), "y": round(y, 4),
            "vx": round(vx, 4), "vy": round(vy, 4),
            "fdx": round(fx, 4), "fdy": round(fy, 4)}


def vacuum_path(p):
    """Closed-form no-air parabola for the same launch: [[x, y], ...]."""
    rad = math.radians(p["angle"])
    vx, vy = p["v0"] * math.cos(rad), p["v0"] * math.sin(rad)
    t_f = 2.0 * vy / p["g"]
    pts = []
    for i in range(VACUUM_POINTS + 1):
        t = t_f * i / VACUUM_POINTS
        pts.append([round(vx * t, 4), round(max(0.0, vy * t - 0.5 * p["g"] * t * t), 4)])
    return pts


def run(p):
    rad = math.radians(p["angle"])
    vx, vy = p["v0"] * math.cos(rad), p["v0"] * math.sin(rad)
    x, y, t = 0.0, 0.0, 0.0
    frames = [_frame(0.0, 0.0, 0.0, vx, vy, p)]
    peak = 0.0
    max_drag = math.hypot(*drag_force(vx, vy, p))
    landed = False
    t_vac = 2.0 * vy / p["g"]
    record_every = max(RECORD_MIN, min(RECORD_MAX, int(t_vac / FRAMES_PER_FLIGHT / DT)))
    n = 0
    while n * DT < MAX_T:
        vx0, vy0, x0, y0 = vx, vy, x, y
        ax1, ay1 = _accel(vx0, vy0, p)
        ax2, ay2 = _accel(vx0 + ax1 * DT, vy0 + ay1 * DT, p)
        vx = vx0 + 0.5 * (ax1 + ax2) * DT
        vy = vy0 + 0.5 * (ay1 + ay2) * DT
        x = x0 + 0.5 * (vx0 + vx) * DT
        y = y0 + 0.5 * (vy0 + vy) * DT
        n += 1
        t = n * DT
        peak = max(peak, y)
        max_drag = max(max_drag, math.hypot(*drag_force(vx, vy, p)))
        if y >= 0.0:
            if n % record_every == 0:
                frames.append(_frame(t, x, y, vx, vy, p))
        else:
            # crossed the ground inside this step: interpolate the crossing
            # (error O(dt^2), ~1e-6 m) for time, position and velocity
            s = y0 / (y0 - y)
            frames.append(_frame(t - (1.0 - s) * DT, x0 + s * (x - x0), 0.0,
                                 vx0 + s * (vx - vx0), vy0 + s * (vy - vy0), p))
            landed = True
            break
    last = frames[-1]
    speed = math.hypot(last["vx"], last["vy"])
    ideal = p["v0"] * p["v0"] * math.sin(2.0 * rad) / p["g"]
    weight = p["mass"] * p["g"]
    return {
        "frames": frames,
        "landed": landed,
        "vacuum": vacuum_path(p),
        "notes": [] if landed else
        ["Still flying after %.0f s - the run was stopped there." % MAX_T],
        "readouts": [
            {"label": "Distance", "value": last["x"], "unit": "m"},
            {"label": "Flight time", "value": last["t"], "unit": "s"},
            {"label": "Peak height", "value": round(peak, 3), "unit": "m"},
            {"label": "Landing speed", "value": round(speed, 3), "unit": "m/s"},
            {"label": "Distance with no air", "value": round(ideal, 3), "unit": "m"},
            {"label": "Biggest drag force", "value": round(max_drag, 3),
             "unit": "N (%.1f x weight)" % (max_drag / weight)},
        ],
        "formula": [
            {"expr": "a = -g - (k/m) * v_air * |v_air|",
             "values": {"g": round(p["g"], 2), "k": round(p["drag"], 3),
                        "m": round(p["mass"], 2), "wind": round(p["wind"], 2)}},
            {"expr": "Range = v0^2 * sin(2*angle) / g",
             "values": {"v0": round(p["v0"], 2), "angle": round(p["angle"], 1),
                        "g": round(p["g"], 2),
                        "Range": round(ideal, 3) if p["drag"] == 0.0 else None}},
        ],
    }
