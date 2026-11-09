"""Waves on a rope: one end shaken up and down, the other end fixed,
free, or open (a rope so long that nothing comes back).

The rope obeys the damped wave equation

    y_tt + gamma y_t = v^2 y_xx,     v = sqrt(T / mu)

* wave speed          v = sqrt(T / mu)       (tension, mass per metre)
* wavelength          lambda = v / f
* resonances          fixed far end:  f_n = n v / (2 L)
                      free far end:   f_n = (2n - 1) v / (4 L)
* steady state (exact, used by the tests and for the node markers):
      y(x, t) = Re[ A S(x) e^(i w t) ],  k = sqrt(w^2 - i w gamma) / v
      fixed: S = sin(k (L - x)) / sin(k L)
      free:  S = cos(k (L - x)) / cos(k L)
      open:  S = e^(-i k x)

Numerics: explicit leapfrog finite differences at Courant number exactly
1 (dx = v dt). On that grid the undamped scheme is EXACT - it reproduces
d'Alembert's solution at the grid points with no numerical dispersion
(verified in the tests). Boundaries: driven y(0, t) = A sin(w t); fixed
y(L) = 0; free y_x(L) = 0 (mirror ghost point); open y_t + v y_x = 0,
which at Courant 1 is the exact one-step shift y_N^(n+1) = y_(N-1)^n.

The grid has at least 16 time steps per shake period, so frames are
recorded every step or few steps; the client loops the last period once
the run is in steady state.
"""

import cmath
import math

T_SIM = 10.0             # seconds of rope motion simulated
MIN_CELLS = 40
MAX_CELLS = 400
STEPS_PER_PERIOD = 16    # time resolution of the shake
MAX_POINTS = 161         # rope points sent per frame
BEAD_AT = 0.6            # the marked bead sits at 60% of the rope
UNIT = 1e4               # shapes are sent as integers in 0.1 mm


def wave_speed(tension, mu):
    """v = sqrt(T / mu), mu in kg/m."""
    return math.sqrt(tension / mu)


def wavelength(v, f):
    return v / f


def resonances(v, length, end, count=5):
    """First `count` resonance frequencies for a rope driven at x = 0."""
    if end == "fixed":
        return [n * v / (2.0 * length) for n in range(1, count + 1)]
    if end == "free":
        return [(2 * n - 1) * v / (4.0 * length) for n in range(1, count + 1)]
    return []


def complex_k(f, v, gamma):
    w = 2.0 * math.pi * f
    return cmath.sqrt(w * w - 1j * w * gamma) / v


def steady_profile(x, f, v, gamma, length, end):
    """Complex steady-state amplitude S(x) per unit drive amplitude."""
    k = complex_k(f, v, gamma)
    if end == "fixed":
        return cmath.sin(k * (length - x)) / cmath.sin(k * length)
    if end == "free":
        return cmath.cos(k * (length - x)) / cmath.cos(k * length)
    return cmath.exp(-1j * k * x)


def dalembert(x, t, f, amp, v, length, end, reflections=True):
    """Exact undamped solution before the reflection returns to the
    driver (t < 2L/v): incident wave plus one reflection."""
    w = 2.0 * math.pi * f

    def inc(tau):
        return amp * math.sin(w * tau) if tau > 0.0 else 0.0
    y = inc(t - x / v)
    if reflections and end in ("fixed", "free"):
        sign = -1.0 if end == "fixed" else 1.0
        y += sign * inc(t - (2.0 * length - x) / v)
    return y


def grid(p):
    """Cells N and step dt for Courant number 1 with >= 16 steps/period."""
    v = wave_speed(p["tension"], p["mu"] / 1000.0)
    n = int(math.ceil(STEPS_PER_PERIOD * p["f"] * p["length"] / v))
    n = max(MIN_CELLS, min(MAX_CELLS, n))
    return n, p["length"] / (n * v), v


def simulate(p, t_end=T_SIM, record=None):
    """Run the scheme; returns (xs, dt, [(t, y_list, ydot_list), ...]) for
    every time level j with record(j) true (all levels if record is None)."""
    n, dt, v = grid(p)
    amp, w, gamma, end = p["amplitude"] / 100.0, 2.0 * math.pi * p["f"], p["damping"], p["end"]
    a = 1.0 / (1.0 + gamma * dt / 2.0)
    b = 1.0 - gamma * dt / 2.0
    prev = [0.0] * (n + 1)
    cur = [0.0] * (n + 1)
    out = []
    steps = int(round(t_end / dt))
    if record is None or record(0):
        out.append((0.0, cur[:], [0.0] * (n + 1)))
    for s in range(1, steps + 1):
        nxt = [0.0] * (n + 1)
        nxt[1:n] = [a * (cur[i + 1] + cur[i - 1] - b * prev[i]) for i in range(1, n)]
        nxt[0] = amp * math.sin(w * s * dt)
        if end == "fixed":
            nxt[n] = 0.0
        elif end == "free":
            nxt[n] = a * (2.0 * cur[n - 1] - b * prev[n])
        else:
            nxt[n] = cur[n - 1]
        lvl = s - 1                      # cur holds time level s - 1
        if lvl > 0 and (record is None or record(lvl)):
            # centred velocity at that level needs the levels either side
            vel = [(nxt[i] - prev[i]) / (2.0 * dt) for i in range(n + 1)]
            out.append((lvl * dt, cur[:], vel))
        prev, cur = cur, nxt
    xs = [i * p["length"] / n for i in range(n + 1)]
    return xs, dt, out


def envelope(shapes):
    """Largest |y| reached at each point over a list of shapes."""
    return [max(abs(s[i]) for s in shapes) for i in range(len(shapes[0]))]


def find_nodes(xs, env, rel=0.25):
    """Interior local minima of the envelope below rel * max: the nodes."""
    top = max(env) or 1.0
    nodes = []
    for i in range(1, len(env) - 1):
        if env[i] <= env[i - 1] and env[i] < env[i + 1] and env[i] < rel * top:
            nodes.append(xs[i])
    return nodes


def _crest(t, f, v, length):
    """Position of the most recently launched crest still on the rope
    (the incident wave; crests leave the driver at t = (k + 1/4) / f)."""
    k = math.floor(t * f - 0.25)
    while k >= 0:
        x = v * (t - (k + 0.25) / f)
        if x > length:
            return None
        if x >= 0.0:
            return x
        k -= 1
    return None


def _round_or_none(x, nd):
    return None if x is None else round(x, nd)


def run(p):
    n, dt, v = grid(p)
    f, length, end, amp = p["f"], p["length"], p["end"], p["amplitude"] / 100.0
    lam = wavelength(v, f)
    every = max(1, int(math.floor(1.0 / (STEPS_PER_PERIOD * f) / dt)))
    stride = max(1, int(math.ceil((n + 1) / float(MAX_POINTS))))
    idx = list(range(0, n + 1, stride))
    if idx[-1] != n:
        idx.append(n)
    bead = int(round(BEAD_AT * n))
    # at least 4 shakes, so slow shaking still shows its steady state
    xs, dt, rec = simulate(p, max(T_SIM, 4.0 / f), record=lambda s: s % every == 0)

    frames = []
    for t, y, vel in rec:
        frames.append({"t": round(t, 5),
                       "y": [int(round(y[i] * UNIT)) for i in idx],
                       "driver": round(y[0], 6),
                       "bead_y": round(y[bead], 6), "bead_v": round(vel[bead], 6),
                       "crest_x": _round_or_none(_crest(t, f, v, length), 4)})

    period = 1.0 / f
    t_last = rec[-1][0]
    last = [y for t, y, _ in rec if t >= t_last - period - 1e-9]
    env = envelope(last)
    env_out = [round(env[i], 6) for i in idx]
    nodes = [round(x, 4) for x in find_nodes(xs, env)] if end != "open" else []
    res = resonances(v, length, end)
    near = min(res, key=lambda r: abs(r - f)) if res else None
    n_near = res.index(near) + 1 if res else None
    gain = max(env) / amp if amp else 0.0

    notes = []
    if near is not None and abs(near - f) / near < 0.03:
        notes.append("Resonance! %.2f Hz matches the rope's mode n = %d, so every reflection "
                     "arrives in step with the shaking and the wave piles up into a standing "
                     "wave %.1fx taller than the hand moves." % (f, n_near, gain))
    if end == "open":
        notes.append("Open end: the wave runs off and never comes back, so there are no "
                     "reflections, no standing wave and no resonance.")
    if max(env) > 0.15 * length:
        notes.append("The wave is very tall compared with the rope's length: a real rope would "
                     "behave less simply (this linear model exaggerates the peak).")

    return {
        "frames": frames,
        "notes": notes,
        "viz": {"xs": [round(xs[i], 5) for i in idx], "length": length, "unit": 1.0 / UNIT,
                "envelope": env_out, "nodes": nodes, "period": period,
                "bead_x": round(xs[bead], 5), "v": round(v, 6), "lambda": round(lam, 6),
                "amp": amp, "end": end, "t_end": round(t_last, 5)},
        "readouts": [
            {"label": "Wave speed v = sqrt(T/mu)", "value": round(v, 3), "unit": "m/s"},
            {"label": "Wavelength lambda = v/f", "value": round(lam, 3), "unit": "m"},
            {"label": "Period (one shake)", "value": round(period, 4), "unit": "s"},
            {"label": "Waves that fit on the rope (L/lambda)", "value": round(length / lam, 3), "unit": ""},
            {"label": "Time to travel the rope (L/v)", "value": round(length / v, 4), "unit": "s"},
            {"label": "Nearest resonance", "value": ("f_%d = %.3f" % (n_near, near)) if near else "none",
             "unit": "Hz" if near else "(open end)"},
            {"label": "Biggest swing on the rope (steady)", "value": round(max(env) * 100.0, 2),
             "unit": "cm (%.1fx the hand)" % gain},
        ],
        "formula": [
            {"expr": "v = sqrt(T / mu)",
             "values": {"T": round(p["tension"], 2), "mu": round(p["mu"] / 1000.0, 4),
                        "v": round(v, 3)}},
            {"expr": "v = f * lambda",
             "values": {"f": round(f, 3), "lambda": round(lam, 3), "v": round(v, 3)}},
            {"expr": "f_n = n * v / (2 * L)",
             "values": dict([("f_%d" % (i + 1), round(r, 3)) for i, r in enumerate(res[:4])]
                            + [("end", end)])},
        ],
    }
