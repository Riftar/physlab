"""Pendulum: a bob on a light, inextensible string - the FULL swing, not
just the small-angle approximation - with optional air drag on the bob.

Equation of motion (tangential Newton's law, v = L * omega):

    m L theta'' = -m g sin(theta) - k (L omega) |L omega|
    theta''     = -(g/L) sin(theta) - (k L / m) omega |omega|

* restoring force      F_r = m g sin(theta)       (gravity along the swing)
* string tension       T_s = m (g cos(theta) + L omega^2)   (radial Newton)
* small-angle period   T0  = 2 pi sqrt(L/g)
* exact period         T   = T0 / AGM(1, cos(theta0/2))
  (the complete elliptic integral K written with the arithmetic-geometric
  mean - exact for any release angle, no series truncation)
* energy               E = 1/2 m v^2 + m g L (1 - cos(theta))

Release angles are limited to 90 deg: beyond that, a STRING pendulum
released from rest goes slack (tension at the turning point is
m g cos(theta0) < 0) and stops being a pendulum.

Classic RK4, 2000 steps per small-angle period. Same validated params ->
byte-identical frames.
"""

import math

STEPS_PER_PERIOD = 2000
FRAMES_PER_PERIOD = 60
PERIODS = 8
MAX_T = 60.0


def small_angle_period(length, g):
    return 2.0 * math.pi * math.sqrt(length / g)


def agm(a, b):
    """Arithmetic-geometric mean (quadratically convergent)."""
    for _ in range(60):
        if abs(a - b) <= 1e-15 * max(abs(a), abs(b)):
            break
        a, b = (a + b) / 2.0, math.sqrt(a * b)
    return (a + b) / 2.0


def exact_period(length, g, theta0):
    """Period for release angle theta0 (radians) from rest, no drag."""
    return small_angle_period(length, g) / agm(1.0, math.cos(theta0 / 2.0))


def max_speed(length, g, theta0):
    """Speed at the bottom, from energy conservation."""
    return math.sqrt(2.0 * g * length * (1.0 - math.cos(theta0)))


def tension(m, g, length, theta, omega):
    return m * (g * math.cos(theta) + length * omega * omega)


def restoring_force(m, g, theta):
    """Component of gravity along the swing, pulling back to the middle."""
    return m * g * math.sin(theta)


def energies(m, g, length, theta, omega):
    """(kinetic, potential) in joules; potential is zero at the bottom."""
    v = length * omega
    return 0.5 * m * v * v, m * g * length * (1.0 - math.cos(theta))


def bob_position(length, theta):
    """(x, y) of the bob relative to the pivot, metres; y points up."""
    return length * math.sin(theta), -length * math.cos(theta)


def air_force(k, length, theta, omega, wind):
    """Air drag on the bob, F = k |u| u with u = wind - bob velocity (2-D).
    Returns (tangential, radial-outward) components in newtons. With no
    wind this is the usual -k v |v| along the swing."""
    tx, ty = math.cos(theta), math.sin(theta)          # +theta tangent
    vx, vy = length * omega * tx, length * omega * ty
    ux, uy = wind - vx, -vy
    sp = math.hypot(ux, uy)
    fx, fy = k * sp * ux, k * sp * uy
    return fx * tx + fy * ty, fx * math.sin(theta) - fy * math.cos(theta)


def lean_angle(k, wind, m, g):
    """Steady lean in a constant wind: m g sin(theta) = k w|w| cos(theta)."""
    return math.atan2(k * wind * abs(wind), m * g)


def _deriv(theta, omega, p):
    wind = p.get("wind", 0.0)
    if wind == 0.0:
        return omega, (-(p["g"] / p["length"]) * math.sin(theta)
                       - (p["drag"] * p["length"] / p["mass"]) * omega * abs(omega))
    ft, _ = air_force(p["drag"], p["length"], theta, omega, wind)
    return omega, -(p["g"] / p["length"]) * math.sin(theta) + ft / (p["mass"] * p["length"])


def _rk4(theta, omega, dt, p):
    k1t, k1w = _deriv(theta, omega, p)
    k2t, k2w = _deriv(theta + 0.5 * dt * k1t, omega + 0.5 * dt * k1w, p)
    k3t, k3w = _deriv(theta + 0.5 * dt * k2t, omega + 0.5 * dt * k2w, p)
    k4t, k4w = _deriv(theta + dt * k3t, omega + dt * k3w, p)
    return (theta + dt / 6.0 * (k1t + 2 * k2t + 2 * k3t + k4t),
            omega + dt / 6.0 * (k1w + 2 * k2w + 2 * k3w + k4w))


def measured_period(times, thetas):
    """Mean period from successive same-direction zero crossings, each
    located by linear interpolation between samples. None if < 1 period."""
    ups = []
    for i in range(1, len(thetas)):
        a, b = thetas[i - 1], thetas[i]
        if a < 0.0 <= b:
            ups.append(times[i - 1] + (times[i] - times[i - 1]) * (-a / (b - a)))
    if len(ups) < 2:
        return None
    return (ups[-1] - ups[0]) / (len(ups) - 1)


def _frame(t, theta, omega, p, swings):
    m, g, L = p["mass"], p["g"], p["length"]
    ke, pe = energies(m, g, L, theta, omega)
    x, y = bob_position(L, theta)
    v = L * omega
    wind = p.get("wind", 0.0)
    if wind == 0.0:
        f_t, f_r = -p["drag"] * v * abs(v), 0.0
    else:
        f_t, f_r = air_force(p["drag"], L, theta, omega, wind)
    out = {"t": round(t, 4), "theta": round(theta, 6), "omega": round(omega, 6),
           "x": round(x, 5), "y": round(y, 5), "v": round(v, 5),
           "tension": round(tension(m, g, L, theta, omega) + f_r, 5),
           "f_restore": round(restoring_force(m, g, theta), 5),
           "f_drag": round(f_t, 5),
           "ke": round(ke, 6), "pe": round(pe, 6), "swings": swings}
    if wind != 0.0:
        out["f_air_r"] = round(f_r, 5)               # the wind also pushes outwards on the string
    return out


def run(p):
    m, g, L = p["mass"], p["g"], p["length"]
    theta0 = math.radians(p["amplitude"])
    t0 = small_angle_period(L, g)
    t_exact = exact_period(L, g, theta0)
    dt = t0 / STEPS_PER_PERIOD
    record_every = STEPS_PER_PERIOD // FRAMES_PER_PERIOD       # 33 steps
    t_end = min(MAX_T, PERIODS * t_exact)
    n_steps = int(math.ceil(t_end / dt))

    theta, omega = theta0, 0.0
    swings = 0                       # completed half-swings (turning points)
    frames = [_frame(0.0, theta, omega, p, swings)]
    times, thetas = [0.0], [theta]
    for n in range(1, n_steps + 1):
        prev_omega = omega
        theta, omega = _rk4(theta, omega, dt, p)
        if (prev_omega < 0.0 <= omega) or (prev_omega > 0.0 >= omega):
            swings += 1
        times.append(n * dt)
        thetas.append(theta)
        if n % record_every == 0 or n == n_steps:
            frames.append(_frame(n * dt, theta, omega, p, swings))

    ke0, pe0 = energies(m, g, L, theta0, 0.0)
    e0 = ke0 + pe0
    wind = p.get("wind", 0.0)
    lean = lean_angle(p["drag"], wind, m, g) if wind else 0.0
    # in wind the bob swings about its lean angle, so count crossings of THAT
    meas = measured_period(times, [th - lean for th in thetas] if wind else thetas)
    v_max = max_speed(L, g, theta0)
    notes = []
    if p["amplitude"] > 30.0:
        notes.append("Big swing: T = 2 pi sqrt(L/g) only holds for small angles. At %.0f deg "
                     "the real period is %.1f%% longer." % (p["amplitude"], 100.0 * (t_exact / t0 - 1.0)))
    if p["drag"] > 0.0:
        notes.append("Air drag removes energy every swing, so the swings shrink - a light "
                     "bob slows down sooner than a heavy one with the same drag.")
    still = " in still air" if wind else ""
    viz = {"period_small": round(t0, 6), "period_exact": round(t_exact, 6), "energy0": round(e0, 6)}
    extra = []
    if wind:
        # a steady wind push k w|w| adds to gravity: the bob hangs at the lean
        # angle and small swings about it feel g_eff = sqrt(g^2 + (k w^2 / m)^2)
        g_eff = math.hypot(g, p["drag"] * wind * wind / m)
        t_wind = small_angle_period(L, g_eff)
        viz.update({"wind": wind, "lean": round(lean, 6), "period_wind": round(t_wind, 6)})
        extra = [{"label": "Lean in the wind (tan θ = k w² / m g)", "value": round(math.degrees(lean), 2),
                  "unit": "°"},
                 {"label": "Period about the lean, 2π√(L/g_eff)", "value": round(t_wind, 4),
                  "unit": "s (g_eff %.2f m/s²)" % g_eff}]
        notes.append("Wind pushes the bob sideways with about k w² = %.3g N (its weight is %.3g N), so it "
                     "hangs at %.1f° and swings about that angle. The push adds to gravity like a "
                     "stronger, tilted g." % (p["drag"] * wind * wind, m * g, math.degrees(lean)))
    return {
        "frames": frames,
        "notes": notes,
        "viz": viz,
        "readouts": [
            {"label": "Period, small-angle formula", "value": round(t0, 4), "unit": "s" + still},
            {"label": "Period, exact for this angle", "value": round(t_exact, 4), "unit": "s" + still},
            {"label": "Period, measured in the run", "value": round(meas, 4) if meas else "—", "unit": "s"},
            {"label": "Swings per second (f = 1/T)", "value": round(1.0 / t_exact, 4), "unit": "Hz" + still},
        ] + ([
            {"label": "Top speed (at the bottom)", "value": round(v_max, 3), "unit": "m/s"},
            {"label": "String tension at the bottom", "value": round(m * g * (3.0 - 2.0 * math.cos(theta0)), 3),
             "unit": "N (weight %.2f N)" % (m * g)},
        ] if not wind else [
            {"label": "Top speed (measured)", "value": round(max(abs(f["v"]) for f in frames), 3), "unit": "m/s"},
            {"label": "Highest string tension (measured)", "value": round(max(f["tension"] for f in frames), 3),
             "unit": "N (weight %.2f N)" % (m * g)},
        ]) + extra,
        "formula": [
            {"expr": "T = 2*pi * sqrt(L/g)",
             "values": {"L": round(L, 3), "g": round(g, 2), "T": round(t0, 4)}},
            {"expr": "T_exact = T / AGM(1, cos(theta0/2))",
             "values": {"theta0": round(p["amplitude"], 1), "T_exact": round(t_exact, 4),
                        "longer_by_%": round(100.0 * (t_exact / t0 - 1.0), 2)}},
            {"expr": "F_restore = m * g * sin(theta)",
             "values": {"m": round(m, 2), "g": round(g, 2),
                        "F_max": round(restoring_force(m, g, theta0), 3)}},
            {"expr": "E = 0.5*m*v^2 + m*g*h",
             "values": {"E": round(e0, 4), "h_max": round(L * (1 - math.cos(theta0)), 4),
                        "v_max": round(v_max, 3)}},
        ],
    }
