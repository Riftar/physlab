"""Ball tracer: a ball flying through air, bouncing off surfaces.

The projectile engine of physlab.topics.motion (Heun / trapezoidal steps of
gravity + quadratic air drag + wind),

    a = -g - (k/m) * v_air * |v_air|,     v_air = v - wind,   k = 1/2 rho C_d A

plus what machines need:

  * any launch point and velocity
  * line-segment obstacles (floors, walls, funnels...). On contact the
    velocity component INTO the surface is reversed and multiplied by the
    pair's coefficient of restitution e; the component along it is kept
    (a smooth, non-spinning ball):      v_n' = -e v_n,   v_t' = v_t
    so a drop from h0 bounces back to  h1 = e^2 h0  (minus air drag)
  * named zones that end the run (the goal, the floor...)

Fixed step, so the same inputs always give the same path (physlab rule 2).
Used by the Bounces topic and by the game's stations.
"""

import math

G = 9.81
RHO_AIR = 1.225


def drag_constant(d, cd=0.47, rho_air=RHO_AIR):
    """k = 1/2 rho C_d A for a sphere of diameter d (kg/m)."""
    return 0.5 * rho_air * cd * math.pi * (d / 2.0) ** 2


def closest_point(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    l2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / l2)) if l2 else 0.0
    return ax + t * dx, ay + t * dy


def trace(x, y, vx, vy, mass, radius, k, segs=(), zones=(), wind=0.0, g=G, dt=4e-4, tmax=6.0,
          record=1.0 / 120.0, max_hits=60, stop_hits=None):
    """Fly a ball (centre at x, y) until a zone fires or tmax.

    segs:  [(ax, ay, bx, by, e, name)] - obstacles, e = restitution
    zones: [(name, fn(x, y, vx, vy) -> bool)] - checked after every step
    stop_hits: end the run (outcome "hits") after this many contacts
    Returns {"outcome", "t", "x", "y", "vx", "vy", "frames", "hits"}; frames
    are {t, x, y, vx, vy} every `record` seconds (plus the last state), hits
    are {t, name, speed} (impact speed into the surface)."""
    frames = [_frame(0.0, x, y, vx, vy)]
    hits = []
    kk = k / mass if mass > 0 else 0.0

    def acc(vx_, vy_):
        rx = vx_ - wind
        s = math.sqrt(rx * rx + vy_ * vy_)
        return -kk * rx * s, -g - kk * vy_ * s

    t, n, next_rec, outcome = 0.0, 0, record, "timeout"
    steps = int(round(tmax / dt))
    while n < steps:
        ax1, ay1 = acc(vx, vy)
        ax2, ay2 = acc(vx + ax1 * dt, vy + ay1 * dt)
        nvx, nvy = vx + 0.5 * (ax1 + ax2) * dt, vy + 0.5 * (ay1 + ay2) * dt
        x += 0.5 * (vx + nvx) * dt
        y += 0.5 * (vy + nvy) * dt
        vx, vy = nvx, nvy
        n += 1
        t = n * dt
        for (ax_, ay_, bx_, by_, e, name) in segs:
            cx, cy = closest_point(x, y, ax_, ay_, bx_, by_)
            dx, dy = x - cx, y - cy
            d = math.sqrt(dx * dx + dy * dy)
            if 1e-12 < d < radius:
                nx, ny = dx / d, dy / d
                vn = vx * nx + vy * ny
                x, y = cx + nx * radius, cy + ny * radius      # back onto the surface
                if vn < 0.0:
                    vx -= (1.0 + e) * vn * nx
                    vy -= (1.0 + e) * vn * ny
                    hits.append({"t": round(t, 4), "name": name, "speed": round(-vn, 4)})
        if stop_hits is not None and len(hits) >= stop_hits:
            outcome = "hits"
            break
        if len(hits) > max_hits:
            outcome = "stuck"
            break
        fired = next((name for name, fn in zones if fn(x, y, vx, vy)), None)
        if fired:
            outcome = fired
            break
        if t >= next_rec - 1e-12:
            frames.append(_frame(t, x, y, vx, vy))
            next_rec += record
    if frames[-1]["t"] != round(t, 4):
        frames.append(_frame(t, x, y, vx, vy))
    return {"outcome": outcome, "t": t, "x": x, "y": y, "vx": vx, "vy": vy, "frames": frames, "hits": hits}


def _frame(t, x, y, vx, vy):
    return {"t": round(t, 4), "x": round(x, 5), "y": round(y, 5), "vx": round(vx, 4), "vy": round(vy, 4)}
