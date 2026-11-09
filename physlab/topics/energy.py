"""Energy ramp: let go of a box or a ball on a track and follow where its
energy goes - height (potential), motion (kinetic), spin (for balls) and
heat (friction, rough landings).

    E = 1/2 m v^2 + 1/2 I w^2 + m g h        I w^2 = k m v^2 for rolling
    k = I / (m r^2): box 0 (slides), solid ball 2/5, hollow ball 2/3
    frictionless drop h  ->  v = sqrt(2 g h / (1 + k))
    normal force          N = m (g cos(phi) + kappa v^2)     (kappa = curvature)
    friction / rolling resistance  F = mu N, heat = integral F ds

Tracks (fixed shapes, metres) are curves y = f(x); the start height picks
WHERE on the track the object is let go. On the track the motion is one
dimensional along the curve:

    (1 + k) m dv/dt = -m g sin(phi) - mu N sign(v)

A box stays put if mu >= tan(slope) (static friction). If the track
would have to PULL the object (N < 0, going fast over a hill crest) it
flies off: a projectile until it lands on the track again, where the
velocity across the track is lost in the bump (booked as heat).

RK4 at 1 ms. Energy is conserved to integration error (tested).
"""

import math

G_DEFAULT = 9.81
DT = 0.001
RECORD = 1.0 / 30.0
BALL_R = 0.4                      # m: drawn ball radius (its spin angle = distance / r)
K = {"box": 0.0, "solid_ball": 0.4, "hollow_ball": 2.0 / 3.0}


# ---------------- tracks ----------------

class Track(object):
    """y = f(x) built from smooth pieces; gives f, f', f'' analytically."""

    def __init__(self, kind):
        self.kind = kind
        if kind == "halfpipe":
            self.x0, self.x1 = 0.0, 16.0
        else:
            self.x0, self.x1 = 0.0, 30.0

    def f(self, x):
        return self.eval(x)[0]

    def eval(self, x):
        """(y, y', y'') at x."""
        if self.kind == "halfpipe":                # y = 8 ((x - 8) / 8)^2
            u = (x - 8.0) / 8.0
            return 8.0 * u * u, 2.0 * u, 0.25
        pi = math.pi
        if x < 8.0:                                # drop: 8 m -> 0.5 m, steep at the top
            u = x / 8.0
            return (0.5 + 7.5 * (1.0 - math.sin(pi * u / 2.0)),
                    -7.5 * (pi / 2.0) * math.cos(pi * u / 2.0) / 8.0,
                    7.5 * (pi / 2.0) ** 2 * math.sin(pi * u / 2.0) / 64.0)
        if x < 14.0:                               # up the hill to 3 m
            u = (x - 8.0) / 6.0
            return (0.5 + 1.25 * (1.0 - math.cos(pi * u)),
                    1.25 * pi * math.sin(pi * u) / 6.0,
                    1.25 * pi * pi * math.cos(pi * u) / 36.0)
        if x < 20.0:                               # down into the valley
            u = (x - 14.0) / 6.0
            return (0.5 + 1.25 * (1.0 + math.cos(pi * u)),
                    -1.25 * pi * math.sin(pi * u) / 6.0,
                    -1.25 * pi * pi * math.cos(pi * u) / 36.0)
        u = (x - 20.0) / 10.0                      # final climb to 8 m
        return (0.5 + 7.5 * (1.0 - math.cos(pi * u / 2.0)),
                7.5 * (pi / 2.0) * math.sin(pi * u / 2.0) / 10.0,
                7.5 * (pi / 2.0) ** 2 * math.cos(pi * u / 2.0) / 100.0)

    def start_x(self, h):
        """Where on the left side of the track the height is h."""
        if self.kind == "halfpipe":
            return 8.0 - 8.0 * math.sqrt(min(h, 8.0) / 8.0)
        h = min(max(h, 0.5), 8.0)
        return 8.0 * (2.0 / math.pi) * math.asin(1.0 - (h - 0.5) / 7.5)

    def polyline(self, n=300):
        return [[round(self.x0 + (self.x1 - self.x0) * i / n, 4),
                 round(self.f(self.x0 + (self.x1 - self.x0) * i / n), 4)] for i in range(n + 1)]

    def lowest(self):
        return 0.0 if self.kind == "halfpipe" else 0.5


class SplineTrack(Track):
    """A track the student shapes: a natural cubic spline through control
    points (x_i, y_i). Natural splines are C2, so the curvature - and the
    normal force - change smoothly; y, y', y'' come straight from the
    cubic pieces."""

    def __init__(self, xs, ys):
        self.kind = "custom"
        self.xs, self.ys = [float(x) for x in xs], [float(y) for y in ys]
        self.x0, self.x1 = self.xs[0], self.xs[-1]
        self.m = _natural_spline_moments(self.xs, self.ys)

    def eval(self, x):
        xs, ys, m = self.xs, self.ys, self.m
        x = min(max(x, self.x0), self.x1)
        i = min(len(xs) - 2, max(0, _bisect(xs, x)))
        h = xs[i + 1] - xs[i]
        a, b = (xs[i + 1] - x) / h, (x - xs[i]) / h
        y = a * ys[i] + b * ys[i + 1] + ((a ** 3 - a) * m[i] + (b ** 3 - b) * m[i + 1]) * h * h / 6.0
        d1 = (ys[i + 1] - ys[i]) / h - (3 * a * a - 1) * h / 6.0 * m[i] + (3 * b * b - 1) * h / 6.0 * m[i + 1]
        d2 = a * m[i] + b * m[i + 1]
        return y, d1, d2

    def start_x(self, h=None):
        return self.x0

    def lowest(self, n=600):
        return min(self.f(self.x0 + (self.x1 - self.x0) * i / n) for i in range(n + 1))

    def check(self, max_slope):
        """Reasons the shape is not allowed (empty if fine)."""
        bad = []
        for i in range(601):
            y, d1, _ = self.eval(self.x0 + (self.x1 - self.x0) * i / 600)
            if y < -1e-6 and "ground" not in bad:
                bad.append("ground")
            if abs(d1) > max_slope and "steep" not in bad:
                bad.append("steep")
        return bad


def _bisect(xs, x):
    lo, hi = 0, len(xs) - 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if xs[mid] <= x:
            lo = mid
        else:
            hi = mid
    return lo


def _natural_spline_moments(xs, ys):
    """Second derivatives M_i of the natural cubic spline (M_0 = M_n = 0),
    from the standard tridiagonal system, solved by the Thomas algorithm."""
    n = len(xs)
    m = [0.0] * n
    if n < 3:
        return m
    a, b, c, d = [0.0] * n, [1.0] * n, [0.0] * n, [0.0] * n
    for i in range(1, n - 1):
        h0, h1 = xs[i] - xs[i - 1], xs[i + 1] - xs[i]
        a[i], b[i], c[i] = h0 / 6.0, (h0 + h1) / 3.0, h1 / 6.0
        d[i] = (ys[i + 1] - ys[i]) / h1 - (ys[i] - ys[i - 1]) / h0
    for i in range(1, n):                     # forward sweep
        w = a[i] / b[i - 1]
        b[i] -= w * c[i - 1]
        d[i] -= w * d[i - 1]
    m[n - 1] = d[n - 1] / b[n - 1]
    for i in range(n - 2, -1, -1):            # back substitution
        m[i] = (d[i] - c[i] * m[i + 1]) / b[i]
    m[0] = m[n - 1] = 0.0
    return m


# ---------------- formulas ----------------

def speed_after_drop(g, drop, k):
    """Frictionless: m g h = 1/2 (1 + k) m v^2."""
    return math.sqrt(2.0 * g * max(drop, 0.0) / (1.0 + k))


def normal_force(m, g, slope, curv, v):
    """N = m (g cos(phi) + kappa v^2), kappa = y'' / (1 + y'^2)^(3/2)."""
    sec = math.sqrt(1.0 + slope * slope)
    return m * (g / sec + curv / sec ** 3 * v * v)


def energies(m, g, k, y, v):
    """(translational KE, rotational KE, potential) in joules."""
    return 0.5 * m * v * v, 0.5 * k * m * v * v, m * g * y


def sticks(mu, slope):
    """A box at rest stays put when static friction can hold it."""
    return mu >= abs(slope)


# ---------------- simulation ----------------

WALL_E = 0.5          # the padded walls at both track ends bounce back half the speed


def run(p):
    track = Track(p["track"])
    return simulate(track, track.start_x(p["height"]), p["mass"], K[p["object"]], p["friction"], p["g"],
                    kind=p["track"], obj=p["object"])


def simulate(track, x, m, k, mu, g, kind, obj, label=None, viz_extra=None):
    """Release an object (mass m, spin share k) at x on `track` with
    friction / rolling resistance mu. Returns the full run result."""
    y0 = track.f(x)
    x_start = x
    e0 = m * g * y0
    v, t = 0.0, 0.0
    heat = land_heat = 0.0
    spin = 0.0                                     # distance rolled (for the drawn spin)
    flying, fx, fy, fvx, fvy = False, 0.0, 0.0, 0.0, 0.0
    omega_fly = 0.0
    t_end = min(50.0, 20.0 * math.sqrt(G_DEFAULT / g))
    frames, next_rec, at_rest, detached, flights = [], 0.0, False, False, 0

    def accel(x_, v_):
        y, d1, d2 = track.eval(x_)
        sec = math.sqrt(1.0 + d1 * d1)
        n = normal_force(m, g, d1, d2, v_)
        fric = mu * max(n, 0.0) * (1.0 if v_ > 0 else -1.0 if v_ < 0 else 0.0)
        return v_ / sec, (-m * g * d1 / sec - fric) / (m * (1.0 + k)), mu * max(n, 0.0) * abs(v_)

    def record(t_, x_, y_, v_, d1, n, fly):
        ket, ker, pe = energies(m, g, k, y_, v_)
        phi = math.atan(d1)
        return {"t": round(t_, 4), "x": round(x_, 5), "y": round(y_, 5), "v": round(v_, 5),
                "phi": round(phi, 5), "N": round(n, 4),
                "friction": round(mu * max(n, 0.0) if abs(v_) > 1e-9 and not fly else 0.0, 4),
                "ke": round(ket, 5), "ker": round(ker, 5), "pe": round(pe, 5),
                "heat": round(heat, 5), "land": round(land_heat, 5), "fly": 1 if fly else 0,
                "spin": round(spin / BALL_R, 4)}

    # does a box even start?
    slope0 = track.eval(x)[1]
    if k == 0.0 and sticks(mu, slope0):
        at_rest = True

    while t <= t_end:
        if flying:
            ket = 0.5 * m * (fvx * fvx + fvy * fvy)
            if t >= next_rec - 1e-12:
                ker = 0.5 * k * m * (omega_fly * BALL_R) ** 2
                frames.append({"t": round(t, 4), "x": round(fx, 5), "y": round(fy, 5),
                               "v": round(math.hypot(fvx, fvy) * (1 if fvx >= 0 else -1), 5),
                               "phi": round(math.atan2(fvy, fvx) if fvx >= 0 else math.atan2(-fvy, -fvx), 5),
                               "N": 0.0, "friction": 0.0, "ke": round(ket, 5), "ker": round(ker, 5),
                               "pe": round(m * g * fy, 5), "heat": round(heat, 5), "land": round(land_heat, 5),
                               "fly": 1, "spin": round(spin / BALL_R, 4)})
                next_rec += RECORD
            # exact ballistic step, then check for landing
            nx, ny = fx + fvx * DT, fy + fvy * DT - 0.5 * g * DT * DT
            nvy = fvy - g * DT
            spin += omega_fly * BALL_R * DT
            if ny <= track.f(nx) or nx <= track.x0 or nx >= track.x1:
                lo, hi = 0.0, DT                       # bisect the moment of landing
                for _ in range(50):
                    mid = (lo + hi) / 2.0
                    mx, my = fx + fvx * mid, fy + fvy * mid - 0.5 * g * mid * mid
                    if my <= track.f(mx):
                        hi = mid
                    else:
                        lo = mid
                tl = hi
                fx, fy = fx + fvx * tl, fy + fvy * tl - 0.5 * g * tl * tl
                fvy -= g * tl
                fx = min(max(fx, track.x0), track.x1)
                y, d1, _ = track.eval(fx)
                sec = math.sqrt(1.0 + d1 * d1)
                v_along = (fvx + fvy * d1) / sec        # velocity component along the track
                e_before = 0.5 * m * (fvx * fvx + fvy * fvy) + 0.5 * k * m * (omega_fly * BALL_R) ** 2
                e_after = 0.5 * (1.0 + k) * m * v_along * v_along
                land_heat += e_before - e_after
                heat += e_before - e_after
                x, v, flying = fx, v_along, False
                t += tl
                continue
            fx, fy, fvy = nx, ny, nvy
            t += DT
            continue

        y, d1, d2 = track.eval(x)
        n = normal_force(m, g, d1, d2, v)
        if t >= next_rec - 1e-12 or at_rest:
            frames.append(record(t, x, y, v, d1, n, False))
            next_rec += RECORD
        if at_rest:
            break
        if n < 0.0:                                  # the track would have to pull: it flies off
            sec = math.sqrt(1.0 + d1 * d1)
            fx, fy, fvx, fvy = x, y, v / sec, v * d1 / sec
            omega_fly = v / BALL_R
            flying, detached = True, True
            flights += 1
            continue
        # RK4 on (x, v), heat with the same weights
        k1 = accel(x, v)
        k2 = accel(x + 0.5 * DT * k1[0], v + 0.5 * DT * k1[1])
        k3 = accel(x + 0.5 * DT * k2[0], v + 0.5 * DT * k2[1])
        k4 = accel(x + DT * k3[0], v + DT * k3[1])
        nx = x + DT / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nv = v + DT / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        dheat = DT / 6.0 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        if mu > 0.0 and v != 0.0 and nv * v < 0.0:
            # turning point with friction: stop there, then static friction decides
            frac = v / (v - nv)
            nx = x + frac * (nx - x)
            dheat *= frac
            nv = 0.0
            if sticks(mu, track.eval(nx)[1]) if k == 0.0 else mu >= abs(track.eval(nx)[1]):
                at_rest = True
        spin += abs(nx - x) * math.sqrt(1.0 + d1 * d1) * (1 if nv >= 0 else -1)
        if (nx <= track.x0 and nv < 0.0) or (nx >= track.x1 and nv > 0.0):
            # the padded wall at the end of the track: half the speed comes back
            dheat += 0.5 * (1.0 + k) * m * nv * nv * (1.0 - WALL_E * WALL_E)
            nv = -WALL_E * nv
        x, v = min(max(nx, track.x0), track.x1), nv
        heat += dheat
        t += DT

    last = frames[-1]
    k_name = {"box": "a sliding box", "solid_ball": "a rolling solid ball", "hollow_ball": "a rolling hollow ball"}
    label = label or k_name.get(obj, obj)
    y_min = min(f["y"] for f in frames)
    base = track.lowest()
    v_bottom = speed_after_drop(g, y0 - base, k)
    max_speed = max(abs(f["v"]) for f in frames)
    max_h_after = max([f["y"] for f in frames if f["t"] > 0.5] or [y0])
    notes = []
    if at_rest and len(frames) <= 2:
        notes.append("The box doesn't move: friction (mu = %.2f) can hold it on a slope this gentle "
                     "(it needs mu < %.2f to slide)." % (mu, abs(slope0)))
    if detached:
        notes.append("Too fast over the hill! The track would have to PULL the object down to keep it "
                     "on the curve (N < 0), so it flies through the air and bumps back down, losing "
                     "energy. Real roller coasters have wheels under the rail to stop this.")
    if mu == 0.0 and not detached:
        notes.append("No friction: the total energy stays %.1f J. The object always climbs back to its "
                     "start height - never higher." % e0)
    if k > 0.0:
        notes.append("A rolling ball spins as well as moves: %.0f%% of its motion energy goes into "
                     "spinning, so it is slower than a sliding box (v = sqrt(2gh/(1+k)))." % (100 * k / (1 + k)))
    viz = {"track": track.polyline(), "kind": kind, "x0": track.x0, "x1": track.x1,
           "start": [round(x_start, 5), round(y0, 5)],
           "e0": round(e0, 5), "k": k, "ball_r": BALL_R, "object": obj, "mass": m,
           "g": g, "detached": detached}
    viz.update(viz_extra or {})
    return {
        "frames": frames,
        "notes": notes,
        "viz": viz,
        "readouts": [
            {"label": "Start height h", "value": round(y0, 3), "unit": "m"},
            {"label": "Energy at the start (m g h)", "value": round(e0, 2), "unit": "J"},
            {"label": "Fastest speed", "value": round(max_speed, 2), "unit": "m/s"},
            {"label": "Speed at the bottom, no friction", "value": round(v_bottom, 2),
             "unit": "m/s for %s" % label},
            {"label": "Highest point after the start", "value": round(max_h_after, 3), "unit": "m"},
            {"label": "Turned into heat", "value": round(last["heat"], 2),
             "unit": "J (%.0f%%)" % (100.0 * last["heat"] / e0 if e0 else 0.0)},
            {"label": "Lowest point", "value": round(y_min, 3), "unit": "m"},
        ],
        "formula": [
            {"expr": "E = 0.5*m*v^2 + m*g*h",
             "values": {"m": m, "g": round(g, 2), "h": round(y0, 3), "E": round(e0, 2)}},
            {"expr": "v = sqrt(2*g*h / (1 + k))",
             "values": {"k": round(k, 3), "h": round(y0 - base, 3),
                        "v": round(v_bottom, 3)}},
            {"expr": "N = m*(g*cos(phi) + v^2/r)",
             "values": {"N_max": round(max(f["N"] for f in frames), 2),
                        "N_min": round(min(f["N"] for f in frames if not f["fly"]), 2),
                        "weight": round(m * g, 2)}},
            {"expr": "E_heat = mu * N * distance",
             "values": {"mu": mu, "E_heat": round(last["heat"], 2)}},
        ],
    }
