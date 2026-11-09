"""Floating and sinking: a block (cube) or ball (sphere) released in a
glass tank of liquid.

Forces on the object (up is +):

    weight        W   = -rho_obj V g
    buoyancy      F_b = rho_liq V_sub g        (Archimedes), acting at the
                                               centroid of the submerged part
    liquid drag   F_d = -1/2 rho_liq C_d(Re) A |v| v  while wet, with the
                        Haider-Levenspiel (1989) drag correlation for a
                        particle of sphericity phi (sphere 1, cube 0.806):
                        C_d = 24/Re (1 + a Re^b) + c / (1 + d/Re),
                        Re = rho |v| d_eq / mu, A = pi d_eq^2 / 4.
                        It tends to Stokes' 3 pi mu d v when slow (honey)
                        and to constant-C_d form drag when fast (water).
    wave damping  F_w = -c v while the object crosses the surface (surface
                        waves carry energy away; c = 2 zeta sqrt(k m_eff),
                        zeta = 0.08 - an empirical model, it only shortens
                        the bobbing, never moves the resting point)
    floor         N   >= 0, a partly elastic bounce (e = 0.3) then rest

    (m + C_a rho_liq V_sub) a = W + F_b + F_d + F_w      C_a = 0.5 added mass

Geometry (s = side or diameter, h = submerged height from the bottom):
    cube    V_sub = s^2 h,                 centroid h/2
    sphere  V_sub = pi h^2 (3r - h) / 3,   centroid h (8r - 3h) / (4 (3r - h))

The tank's water level rises by V_sub / A_tank (water is conserved), and
the submerged height depends on that level - solved by Newton iteration
at every force evaluation.

At rest a floater displaces exactly its own weight of liquid:
    V_sub / V = rho_obj / rho_liq
and its small bobbing has stiffness k = rho g A_w / (1 - A_w / A_tank)
(pushing it down also raises the water), period 2 pi sqrt(m_eff / k).
Note g cancels in V_sub / V: gravity changes how fast things move, never
how deep a floater sits.

RK4 with a step set by the fastest time scale. Same validated params ->
byte-identical frames.
"""

import math

TANK_W = 1.0            # m, inside width (on screen)
TANK_D = 0.4            # m, depth into the screen
TANK_AREA = TANK_W * TANK_D
FILL = 0.40             # m, liquid depth before the object goes in
TANK_H = 0.75           # m
SPHERICITY = {"cube": math.pi ** (1.0 / 3.0) * 6.0 ** (2.0 / 3.0) / 6.0, "sphere": 1.0}
C_A = 0.5
ZETA = 0.08
RESTITUTION = 0.3
T_MAX = 20.0
SETTLE_HOLD = 0.3       # s the object must stay settled before the run ends


# ---------------- geometry ----------------

def volume(shape, s):
    return s ** 3 if shape == "cube" else math.pi * s ** 3 / 6.0


def sub_volume(shape, s, h):
    """Submerged volume for submerged height h (clamped to 0..s)."""
    h = max(0.0, min(s, h))
    if shape == "cube":
        return s * s * h
    r = s / 2.0
    return math.pi * h * h * (3.0 * r - h) / 3.0


def waterplane(shape, s, h):
    """Area cut by the liquid surface (0 when fully out or fully under)."""
    if h <= 0.0 or h >= s:
        return 0.0
    if shape == "cube":
        return s * s
    r = s / 2.0
    return math.pi * (2.0 * r * h - h * h)


def sub_centroid(shape, s, h):
    """Height of the centre of buoyancy above the object's bottom."""
    h = max(0.0, min(s, h))
    if h == 0.0:
        return 0.0
    if shape == "cube":
        return h / 2.0
    r = s / 2.0
    return h * (8.0 * r - 3.0 * h) / (4.0 * (3.0 * r - h))


def frontal_area(shape, s):
    return s * s if shape == "cube" else math.pi * s * s / 4.0


def equivalent_diameter(shape, s):
    """Diameter of the sphere with the same volume (for Stokes drag)."""
    return (6.0 * volume(shape, s) / math.pi) ** (1.0 / 3.0)


# ---------------- forces + hydrostatics ----------------

def buoyant_force(rho_liq, v_sub, g):
    return rho_liq * v_sub * g


def weight(rho_obj, vol, g):
    return rho_obj * vol * g


def gauge_pressure(rho_liq, g, depth):
    """p = rho g depth (zero above the surface)."""
    return rho_liq * g * max(0.0, depth)


def hl_coefficients(phi):
    """Haider & Levenspiel (1989) coefficients (a, b, c, d) for sphericity phi."""
    return (math.exp(2.3288 - 6.4581 * phi + 2.4486 * phi ** 2),
            0.0964 + 0.5565 * phi,
            math.exp(4.905 - 13.8944 * phi + 18.4222 * phi ** 2 - 10.2599 * phi ** 3),
            math.exp(1.4681 + 12.2584 * phi - 20.7322 * phi ** 2 + 15.8855 * phi ** 3))


def drag_coefficient(re, shape):
    a, b, c, d = hl_coefficients(SPHERICITY[shape])
    return 24.0 / re * (1.0 + a * re ** b) + c / (1.0 + d / re)


def reynolds(rho_liq, v, d, mu):
    return rho_liq * abs(v) * d / mu


def drag_force(v, shape, s, rho_liq, mu):
    """Liquid drag in N, opposing v."""
    if v == 0.0:
        return 0.0
    d = equivalent_diameter(shape, s)
    re = reynolds(rho_liq, v, d, mu)
    # C_d * v^2 written as 24 mu v/(rho d) (...) to stay finite as v -> 0
    area = math.pi * d * d / 4.0
    return -0.5 * rho_liq * area * drag_coefficient(re, shape) * abs(v) * v


def solve_level(shape, s, y_bottom, fill=FILL, tank_area=TANK_AREA):
    """Liquid level with the object's bottom at y_bottom.
    Returns (level, submerged height h, V_sub). Newton on
    F(L) = L - fill - V_sub(L - y_bottom) / A_tank (F' = 1 - A_w / A_tank > 0)."""
    level = fill + sub_volume(shape, s, fill - y_bottom) / tank_area
    for _ in range(8):
        h = level - y_bottom
        f = level - fill - sub_volume(shape, s, h) / tank_area
        fp = 1.0 - waterplane(shape, s, h) / tank_area
        step = f / fp
        level -= step
        if abs(step) < 1e-13:
            break
    h = max(0.0, min(s, level - y_bottom))
    return level, h, sub_volume(shape, s, h)


def float_depth(shape, s, fraction):
    """Submerged height h with V_sub = fraction * V (0 < fraction < 1)."""
    if shape == "cube":
        return fraction * s
    target, lo, hi = fraction * volume(shape, s), 0.0, s
    for _ in range(80):                     # bisection: V_sub(h) is monotone
        mid = (lo + hi) / 2.0
        if sub_volume(shape, s, mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def verdict(rho_obj, rho_liq):
    if abs(rho_obj - rho_liq) <= 1e-9 * rho_liq:
        return "neutral"
    return "floats" if rho_obj < rho_liq else "sinks"


def equilibrium(shape, s, rho_obj, rho_liq):
    """Resting state: verdict, submerged fraction, h, level, bottom height."""
    v = volume(shape, s)
    state = verdict(rho_obj, rho_liq)
    if state == "floats":
        frac = rho_obj / rho_liq
        h = float_depth(shape, s, frac)
        level = FILL + frac * v / TANK_AREA
        return {"state": state, "fraction": frac, "h": h, "level": level, "y": level - h}
    level = FILL + v / TANK_AREA
    return {"state": state, "fraction": 1.0, "h": s, "level": level,
            "y": 0.0 if state == "sinks" else None}


def bob_stiffness(shape, s, h, rho_liq, g, tank_area=TANK_AREA):
    aw = waterplane(shape, s, h)
    return rho_liq * g * aw / (1.0 - aw / tank_area)


def bob_period(shape, s, rho_obj, rho_liq, g):
    """Small-oscillation (undamped) bobbing period of a floater."""
    eq = equilibrium(shape, s, rho_obj, rho_liq)
    if eq["state"] != "floats":
        return None
    m_eff = rho_obj * volume(shape, s) + C_A * rho_liq * eq["fraction"] * volume(shape, s)
    return 2.0 * math.pi * math.sqrt(m_eff / bob_stiffness(shape, s, eq["h"], rho_liq, g))


def terminal_speed(shape, s, rho_obj, rho_liq, mu, g):
    """Steady speed fully under the liquid, where drag balances
    |W - F_b| = |rho_obj - rho_liq| V g. Drag grows monotonically with
    speed, so bisection in log-space is robust."""
    f = abs(rho_obj - rho_liq) * volume(shape, s) * g
    if f == 0.0:
        return 0.0
    lo, hi = 1e-9, 1e3
    for _ in range(200):
        mid = math.sqrt(lo * hi)
        if -drag_force(mid, shape, s, rho_liq, mu) < f:
            lo = mid
        else:
            hi = mid
    return math.sqrt(lo * hi)


# ---------------- dynamics ----------------

class _Body(object):
    def __init__(self, p, solid, liquid):
        self.shape, self.s, self.g = p["shape"], p["size"] / 100.0, p["g"]
        self.rho_o, self.rho_l, self.mu = solid["rho"], liquid["rho"], liquid["mu"]
        self.vol = volume(self.shape, self.s)
        self.m = self.rho_o * self.vol

    def state(self, y, v):
        """All forces at bottom height y, velocity v."""
        level, h, vsub = solve_level(self.shape, self.s, y)
        fb = buoyant_force(self.rho_l, vsub, self.g)
        m_eff = self.m + C_A * self.rho_l * vsub
        fd = drag_force(v, self.shape, self.s, self.rho_l, self.mu) if h > 0.0 else 0.0
        if 0.0 < h < self.s:
            k = bob_stiffness(self.shape, self.s, h, self.rho_l, self.g)
            fd += -2.0 * ZETA * math.sqrt(k * m_eff) * v
        fw = -self.m * self.g
        return {"level": level, "h": h, "vsub": vsub, "fb": fb, "fd": fd, "fw": fw,
                "m_eff": m_eff, "net": fw + fb + fd}

    def accel(self, y, v):
        st = self.state(y, v)
        return st["net"] / st["m_eff"]


def _rk4(body, y, v, dt):
    a1 = body.accel(y, v)
    a2 = body.accel(y + 0.5 * dt * v, v + 0.5 * dt * a1)
    v2 = v + 0.5 * dt * a1
    a3 = body.accel(y + 0.5 * dt * v2, v + 0.5 * dt * a2)
    v3 = v + 0.5 * dt * a2
    a4 = body.accel(y + dt * v3, v + dt * a3)
    v4 = v + dt * a3
    return (y + dt / 6.0 * (v + 2 * v2 + 2 * v3 + v4),
            v + dt / 6.0 * (a1 + 2 * a2 + 2 * a3 + a4))


def drag_rate(body, v):
    """Relaxation rate |dF_d/dv| / m (1/s) at speed v - how stiff drag is."""
    u = max(abs(v), 1e-4)
    df = abs(drag_force(u * 1.001, body.shape, body.s, body.rho_l, body.mu)
             - drag_force(u, body.shape, body.s, body.rho_l, body.mu))
    return df / (0.001 * u) / body.m


def time_step(body, v):
    """Step that resolves the fastest process right now: the bobbing
    oscillation and the drag relaxation at the current speed."""
    aw = frontal_area(body.shape, body.s)          # largest waterplane
    w_max = math.sqrt(body.rho_l * body.g * aw / ((1.0 - aw / TANK_AREA) * body.m))
    return min(0.002, 0.05 / w_max, 0.3 / drag_rate(body, v))


def _frame(t, y, v, body, st, fn):
    top = y + body.s
    return {"t": round(t, 4), "y": round(y, 7), "v": round(v, 5),
            "level": round(st["level"], 9), "h": round(st["h"], 7),
            "vsub": round(st["vsub"], 9), "fb": round(st["fb"], 5),
            "fd": round(st["fd"], 5), "fn": round(fn, 5),
            "zb": round(y + sub_centroid(body.shape, body.s, st["h"]), 6),
            "p_top": round(gauge_pressure(body.rho_l, body.g, st["level"] - top), 3),
            "p_bot": round(gauge_pressure(body.rho_l, body.g, st["level"] - y), 3)}


def run(p):
    from .. import SOLIDS, FLUIDS
    solid = next(m for m in SOLIDS if m["id"] == p["material"])
    liquid = next(m for m in FLUIDS if m["id"] == p["fluid"])
    return simulate(p, solid, liquid)


def simulate(p, solid, liquid):
    """p: shape, size (cm), g, start (cm); solid: {id, label, rho, color};
    liquid: {id, label, rho, mu, color}. The sandbox passes catalog objects."""
    body = _Body(p, solid, liquid)
    s, g = body.s, body.g
    eq = equilibrium(body.shape, s, body.rho_o, body.rho_l)
    t_bob = bob_period(body.shape, s, body.rho_o, body.rho_l, g)

    interval = min(0.02, max(0.004, (t_bob or 1.0) / 30.0))
    y = max(0.0, FILL + p["start"] / 100.0 - s / 2.0)     # start: centre vs surface
    v, t, held, next_rec = 0.0, 0.0, 0.0, interval
    st = body.state(y, v)
    fn = 0.0
    frames = [_frame(0.0, y, v, body, st, fn)]
    while t < T_MAX:
        dt = time_step(body, v)
        if body.state(y, v)["h"] == 0.0 and y > FILL:        # in the air: only gravity
            dt = min(dt, 0.002)
        y, v = _rk4(body, y, v, dt)
        t += dt
        fn = 0.0
        if y <= 0.0:                          # the tank floor
            y = 0.0
            if v < 0.0:
                v = -RESTITUTION * v
            st0 = body.state(0.0, 0.0)
            if st0["net"] <= 0.0 and v < 0.02:
                v, fn = 0.0, -st0["net"]       # resting: floor pushes back
        st = body.state(y, v)
        settled = abs(v) < 2e-4 and abs(st["net"] + fn) < 2e-3 * body.m * g + 1e-9
        held = held + dt if settled else 0.0
        if t >= next_rec - 1e-12 or held >= SETTLE_HOLD:
            frames.append(_frame(t, y, v, body, st, fn))
            next_rec += interval * math.floor((t - next_rec) / interval + 1.0)
        if held >= SETTLE_HOLD:
            break

    w = weight(body.rho_o, body.vol, g)
    fb_full = buoyant_force(body.rho_l, body.vol, g)
    rise = (eq["level"] - FILL) * 100.0
    readouts = [
        {"label": "Object density", "value": solid["rho"], "unit": "kg/m\u00b3 (%s)" % solid["label"]},
        {"label": "Liquid density", "value": liquid["rho"], "unit": "kg/m\u00b3 (%s)" % liquid["label"]},
        {"label": "Result", "value": {"floats": "FLOATS", "sinks": "SINKS", "neutral": "HOVERS"}[eq["state"]],
         "unit": ("- %.1f%% under the surface" % (100 * eq["fraction"])) if eq["state"] == "floats" else ""},
        {"label": "Weight W = m g", "value": round(w, 3), "unit": "N (m = %.3f kg)" % body.m},
        {"label": "Buoyancy if fully under", "value": round(fb_full, 3), "unit": "N"},
        {"label": "Buoyancy at rest", "value": round(min(w, fb_full), 3), "unit": "N"},
        {"label": "Liquid pushed aside at rest", "value": round(eq["fraction"] * body.vol * 1000.0, 3),
         "unit": "litres"},
        {"label": "Liquid level rise", "value": round(rise, 2), "unit": "cm"},
    ]
    if eq["state"] == "floats":
        readouts.append({"label": "Bobbing period (small bobs)", "value": round(t_bob, 3), "unit": "s"})
    else:
        vt = terminal_speed(body.shape, s, body.rho_o, body.rho_l, body.mu, g)
        readouts.append({"label": "Top sinking speed" if eq["state"] == "sinks" else "Drift speed",
                         "value": round(vt, 3), "unit": "m/s"})
        if eq["state"] == "sinks":
            readouts.append({"label": "Apparent weight on the floor", "value": round(w - fb_full, 3),
                             "unit": "N (feels %.0f%% lighter)" % (100 * fb_full / w)})

    notes = []
    if eq["state"] == "floats":
        notes.append("It floats %.0f%% under: the fraction under the surface is exactly "
                     "rho_obj / rho_liquid = %.0f / %.0f." % (100 * eq["fraction"], solid["rho"], liquid["rho"]))
    elif eq["state"] == "sinks":
        notes.append("It sinks: even completely under, the %s can only push up %.2f N - less than "
                     "the %.2f N weight." % (liquid["label"].lower(), fb_full, w))
    if liquid["id"] == "mercury":
        notes.append("Mercury is 13.5x denser than water, so even iron floats on it - only very "
                     "dense metals like gold sink. (Real mercury is toxic: this is a thought experiment.)")
    if liquid["mu"] > 1.0:
        notes.append("Honey is very thick (viscous): it brakes every movement, so things creep "
                     "and the bobbing dies almost at once.")
    if abs(g - 9.81) > 0.3:
        notes.append("Gravity scales the weight AND the buoyancy the same way, so the floating depth "
                     "is the same as on Earth - only the speed of the motion changes.")

    return {
        "frames": frames,
        "notes": notes,
        "viz": {"tank": {"w": TANK_W, "h": TANK_H, "fill": FILL, "depth": TANK_D},
                "shape": body.shape, "size": s, "mass": round(body.m, 6), "volume": body.vol,
                "weight": round(w, 6), "fb_full": round(fb_full, 6),
                "solid": solid, "liquid": liquid, "eq": eq,
                "p_floor": round(gauge_pressure(body.rho_l, g, eq["level"]), 3)},
        "readouts": readouts,
        "formula": [
            {"expr": "F_b = rho_fluid * V_sub * g",
             "values": {"rho_fluid": liquid["rho"], "V_sub": round(eq["fraction"] * body.vol, 7),
                        "g": round(g, 2), "F_b": round(min(w, fb_full), 3)}},
            {"expr": "W = rho_obj * V * g",
             "values": {"rho_obj": solid["rho"], "V": round(body.vol, 7), "g": round(g, 2),
                        "W": round(w, 3)}},
            {"expr": "V_sub / V = rho_obj / rho_fluid",
             "values": {"ratio": round(solid["rho"] / liquid["rho"], 4),
                        "result": eq["state"]}},
        ],
    }
