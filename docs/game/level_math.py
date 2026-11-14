"""Design calculator for "The Machine Works" - the Rube Goldberg game in
docs/game/GDD-machine-works.md.

Every number the design document quotes for a station (success windows,
reference answers, common wrong answers, mastery windows, how guessable a
puzzle is) comes from THIS script, so the design and the physics can't
drift apart. It is the game's version of tests/test_quiz.py: when the
stations are built for real, these checks become unit tests.

Where physlab already has the physics, the real engine runs:

    energy.simulate     1.3 Camel Hump (with a new analytic track shape)
    buoyancy            1.2 Salt Canal, 3.1 Crow's Well
    heat.run            2.1 Hot Ring
    circuitlab.solve    2.2 Trapdoor Latch
    pressure helpers    2.3 Hydraulic Gate
    pendulum.run        2.4 Magnet Swing
    optics.run          3.3 Light Gate
    motion (same Heun   1.1, 1.4, 2.4, 3.2 - the ball tracer below adds
    + drag + wind)      launch height, obstacles and bounces

Mechanics physlab does NOT have yet are small PROTOTYPE models here, each
marked "PROTOTYPE -> <where it should live>". They are the specification
for the simulation-module work listed in the GDD (section 9).

Usage:
    python3 docs/game/level_math.py            # every station (a few minutes)
    python3 docs/game/level_math.py --quick    # fewer samples
    python3 docs/game/level_math.py 1.4 2.2    # only these stations
    python3 docs/game/level_math.py --json out.json
"""

import json
import math
import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from physlab.sandbox import BY_ID, FRICTION                              # noqa: E402
from physlab.topics import energy, buoyancy, heat, circuitlab, pressure, pendulum, optics  # noqa: E402

G = 9.81
RHO_AIR = 1.225          # Earth, sea level (sandbox PLANETS["earth"])
RHO_WATER = 998.0

# The three level balls are the sandbox's own bobs: same mass, size, drag.
BALLS = {k: dict(BY_ID["bobs"][k]) for k in ("rubber", "steel", "wood")}
for _b in BALLS.values():
    _b["r"] = _b["d"] / 2.0
    _b["V"] = math.pi / 6.0 * _b["d"] ** 3
    _b["rho"] = _b["mass"] / _b["V"]
    _b["k"] = 0.5 * RHO_AIR * _b["cd"] * math.pi * _b["r"] ** 2      # drag constant, kg/m


# ---------------------------------------------------------------------------
# PROTOTYPE -> physlab/topics/collisions.py ("Bounces & Collisions" topic)
# Proposed catalog: coefficient of restitution e for ball x surface pairs
# (typical published values; e = rebound speed / impact speed).
RESTITUTION = {
    "rubber": {"steel_plate": 0.85, "hardwood": 0.75, "foam_mat": 0.45, "sand": 0.10},
    "steel":  {"steel_plate": 0.90, "hardwood": 0.50, "foam_mat": 0.20, "sand": 0.05},
    "wood":   {"steel_plate": 0.60, "hardwood": 0.50, "foam_mat": 0.25, "sand": 0.05},
}
E_WOOD_WALL = 0.75       # rubber ball on a wooden board / wall
E_FELT = 0.5             # felt-lined funnel


def _closest(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2)) if L2 else 0.0
    return ax + t * dx, ay + t * dy


def trace(x, y, vx, vy, ball, segs=(), zones=(), wind=0.0, dt=4e-4, tmax=6.0, max_hits=40):
    """PROTOTYPE -> physlab/topics/tracer.py (shared by collisions + motion).

    The projectile engine of physlab.topics.motion - Heun steps of
    a = -g - (k/m) v_air |v_air|, v_air = v - wind - plus what the game
    needs: any launch point, line-segment obstacles with restitution e
    (normal speed x e, tangential speed kept, no spin) and named zones
    that end the run. segs: [(ax, ay, bx, by, e, name)];
    zones: [(name, fn(x, y, vx, vy) -> bool)].
    Returns (outcome, (t, x, y, vx, vy), path, hits)."""
    m, k, r = ball["mass"], ball["k"], ball["r"]
    path, hits = [(0.0, x, y)], []

    def acc(vx_, vy_):
        rx = vx_ - wind
        s = math.hypot(rx, vy_)
        return -k / m * rx * s, -G - k / m * vy_ * s
    t, n = 0.0, 0
    while t < tmax:
        ax1, ay1 = acc(vx, vy)
        ax2, ay2 = acc(vx + ax1 * dt, vy + ay1 * dt)
        nvx, nvy = vx + 0.5 * (ax1 + ax2) * dt, vy + 0.5 * (ay1 + ay2) * dt
        x += 0.5 * (vx + nvx) * dt
        y += 0.5 * (vy + nvy) * dt
        vx, vy = nvx, nvy
        t += dt
        n += 1
        for (ax_, ay_, bx_, by_, e, name) in segs:
            cx, cy = _closest(x, y, ax_, ay_, bx_, by_)
            dx, dy = x - cx, y - cy
            d = math.hypot(dx, dy)
            if 1e-12 < d < r:
                nx_, ny_ = dx / d, dy / d
                vn = vx * nx_ + vy * ny_
                x, y = cx + nx_ * r, cy + ny_ * r
                if vn < 0.0:
                    vx -= (1.0 + e) * vn * nx_
                    vy -= (1.0 + e) * vn * ny_
                    hits.append((round(t, 3), name, round(-vn, 3)))
                    if len(hits) > max_hits:
                        return "stuck", (t, x, y, vx, vy), path, hits
        if n % 20 == 0:
            path.append((round(t, 3), round(x, 4), round(y, 4)))
        for name, fn in zones:
            if fn(x, y, vx, vy):
                path.append((round(t, 3), round(x, 4), round(y, 4)))
                return name, (t, x, y, vx, vy), path, hits
    return "timeout", (t, x, y, vx, vy), path, hits


def result(ok, reason, metric=None, unit="", mastery=False, **extra):
    d = {"ok": bool(ok), "reason": reason, "metric": metric, "unit": unit, "mastery": bool(ok and mastery)}
    d.update(extra)
    return d


# ===========================================================================
# LEVEL 1 - THE BOUNCE FACTORY (rubber ball)
# ===========================================================================

# 1.1 Bounce Flap ------------------------------------------------------------
BF_U = 0.20          # m/s: the feed belt nudges the ball off the hatch ledge
BF_FLAP = (0.18, 0.65)   # m: the one-way flap in the shelf above the pad (x range)
BF_DUCT = (0.20, 1.20)   # m: the hot duct above the shelf (x range), clear of the drop shaft


def bounce_flap(k, v):
    """PROTOTYPE (collisions topic): drop onto a pad, bounce UP through a
    one-way flap in the shelf above (it opens upwards only), and don't
    touch the hot duct above the shelf. Vertically this is exactly
    h1 = e^2 h0 (minus a few % of air drag)."""
    ball = BALLS["rubber"]
    r, h0, e = ball["r"], k["hatch"], RESTITUTION["rubber"][k["pad"]]
    hf, hp = v["flap"], v["flap"] + v["duct_gap"]
    x0, x1 = BF_FLAP
    segs = [(-0.3, 0.0, 1.5, 0.0, e, "pad"),
            (BF_DUCT[0], hp, BF_DUCT[1], hp, 0.8, "duct"),
            (-0.08, 0.0, -0.08, 5.0, E_WOOD_WALL, "hatch wall")]
    state = {"above": False}

    def through(x, y, vx, vy):
        if y - r > hf and x0 < x < x1 and vy > 0:
            state["above"] = True
        return state["above"] and vy < 0                    # at the top, above the flap: it lands on it
    zones = [("through", through), ("down", lambda x, y, vx, vy: y < -0.1)]
    # the falling ball passes the shelf level LEFT of the flap (x < x0): nothing to hit on the way down
    out, st, path, hits = trace(0.0, h0 + r, BF_U, 0.0, ball, segs, zones, tmax=4.0)
    names = [h[1] for h in hits]
    apex = None
    if "pad" in names:
        t_pad = next(h[0] for h in hits if h[1] == "pad")
        ys = [p[2] for p in path if p[0] >= t_pad]
        apex = round(max(ys) - r, 3) if ys else None      # height of the ball's BOTTOM at the top of the bounce
    if "duct" in names:
        return result(False, "hit the hot duct - bounced too high", apex, "m", path=path)
    if out != "through":
        return result(False, "didn't get up through the flap - the bounce was too low", apex, "m", path=path)
    return result(True, "up through the flap onto the shelf", apex, "m", mastery=h0 <= v["low_drop"], path=path)


# 1.2 Salt Canal -------------------------------------------------------------
# NaCl(aq) at 20 C (CRC Handbook): mass-% -> density kg/m^3. Saturation 26.4 %.
BRINE = [(0, 998.2), (1, 1005.3), (2, 1012.5), (4, 1026.8), (6, 1041.3), (8, 1055.9), (10, 1070.7),
         (12, 1085.7), (14, 1100.9), (16, 1116.2), (18, 1131.9), (20, 1147.8), (22, 1164.0),
         (24, 1180.4), (26, 1197.2)]
SALT_SAT = 359.0     # g of salt that dissolve in 1 kg (~1 L) of water at 20 C


def brine_density(g_per_l):
    """PROTOTYPE -> physlab catalog "salt water" (buoyancy extension)."""
    s = min(g_per_l, SALT_SAT)
    w = 100.0 * s / (1000.0 + s)
    for (w0, r0), (w1, r1) in zip(BRINE, BRINE[1:]):
        if w <= w1:
            return r0 + (r1 - r0) * (w - w0) / (w1 - w0)
    return BRINE[-1][1]


def salt_canal(k, v):
    ball = BALLS["rubber"]
    s = k["bags"] * 1000.0 / v["litres"]                       # 1 kg bags
    rho = brine_density(s)
    mu = 1.0e-3 * (1.0 + 0.9 * min(s, SALT_SAT) / SALT_SAT)   # brine gets ~2x as thick
    res = buoyancy.simulate({"shape": "sphere", "size": ball["d"] * 100.0, "g": G, "start": 10.0},
                            {"id": "rubber", "label": ball["label"], "rho": ball["rho"], "color": ball["color"]},
                            {"id": "brine", "label": "salt water", "rho": rho, "mu": mu, "color": "#3d8fe0"})
    floats = res["viz"]["eq"]["state"] == "floats"
    wasted = max(0.0, s - SALT_SAT) * v["litres"] / 1000.0
    need = min_bags(v["litres"])
    if not floats:
        return result(False, "sank to the bottom - salt water %.1f kg/m3 is still less dense than rubber (%.0f)"
                      % (rho, ball["rho"]), round(rho, 1), "kg/m3")
    return result(True, "floats" + (" (%.1f kg of salt didn't dissolve)" % wasted if wasted else ""),
                  round(rho, 1), "kg/m3", mastery=k["bags"] == need)


def min_bags(litres):
    return next(n for n in range(0, 60) if brine_density(n * 1000.0 / litres) > BALLS["rubber"]["rho"])


# 1.3 Camel Hump -------------------------------------------------------------
class BumpTrack(energy.Track):
    """PROTOTYPE -> physlab/topics/energy.py "track kit" (analytic pieces).

    A start ramp and one hump whose crest has a FIXED radius of curvature:
        y = base + drop exp(-x^2 / 2 s0^2) + a exp(-(x - xc)^2 / 2 s^2),
        s = sqrt(R a)  ->  y''(crest) = -1/R.
    The hump height is the student's knob; the crest radius R is the
    track piece. energy.simulate() runs it unchanged (it only needs
    eval(x) -> y, y', y'')."""

    def __init__(self, h0, hump, R=0.8, base=0.10, xc=3.5, s0=0.9, x1=6.5):
        self.kind = "custom"
        self.x0, self.x1 = 0.0, x1
        self.base, self.drop, self.s0, self.xc = base, h0 - base, s0, xc
        self.a = max(hump - base, 1e-6)
        self.s = math.sqrt(R * self.a)

    def eval(self, x):
        g1 = math.exp(-x * x / (2 * self.s0 ** 2))
        u = x - self.xc
        g2 = math.exp(-u * u / (2 * self.s ** 2))
        y = self.base + self.drop * g1 + self.a * g2
        d1 = self.drop * g1 * (-x / self.s0 ** 2) + self.a * g2 * (-u / self.s ** 2)
        d2 = (self.drop * g1 * (x * x / self.s0 ** 4 - 1 / self.s0 ** 2)
              + self.a * g2 * (u * u / self.s ** 4 - 1 / self.s ** 2))
        return y, d1, d2

    def start_x(self, h=None):
        return 0.0

    def lowest(self, n=600):
        return min(self.f(self.x1 * i / n) for i in range(n + 1))


HUMP_R = 0.8          # m, crest radius of the hump piece
HUMP_START_X = 0.25   # m, where the canal's outflow drops the ball
HUMP_GOAL_X = 5.0     # m, the cannon's breech starts here
MU_RUBBER_WOOD = FRICTION["rubber"]["wood"]      # rolling resistance, rubber on a wooden track


def camel_hump(k, v):
    ball = BALLS["rubber"]
    tr = BumpTrack(v["h0"], k["hump"], HUMP_R)
    res = energy.simulate(tr, HUMP_START_X, ball["mass"], energy.K["solid_ball"], MU_RUBBER_WOOD, G,
                          kind="custom", obj="solid_ball")
    fr = res["frames"]
    fly = next((f for f in fr if f["fly"]), None)
    near = [f for f in fr if abs(f["x"] - tr.xc) < 0.15 and not f["fly"]]
    v_top = round(min(abs(f["v"]) for f in near), 2) if near else None      # speed over the crest
    if fly:
        return result(False, "flew off the top of the hump at %.1f m/s - faster than sqrt(gR) = %.1f m/s"
                      % (abs(fly["v"]), math.sqrt(G * HUMP_R)), round(abs(fly["v"]), 2), "m/s",
                      path=_hump_path(tr, fr))
    if not any(f["x"] > tr.xc for f in fr):
        return result(False, "rolled back - the hump is higher than the ball can climb", 0.0, "m/s",
                      path=_hump_path(tr, fr))
    t_goal = next((f["t"] for f in fr if f["x"] >= HUMP_GOAL_X), None)
    if t_goal is None:
        return result(False, "stopped before the cannon", v_top, "m/s", path=_hump_path(tr, fr))
    return result(True, "over the hump at %.2f m/s, at the cannon after %.2f s" % (v_top, t_goal), v_top, "m/s",
                  mastery=t_goal <= v["speed_run"], t_goal=t_goal, path=_hump_path(tr, fr))


def _hump_path(tr, frames):
    return [(f["t"], f["x"], f["y"]) for f in frames[::3] if f["t"] < 6.0]


# 1.4 Spring Cannon ----------------------------------------------------------
SPRING_K = 300.0      # N/m
FUNNEL_MOUTH = 0.35   # m, half-width of the funnel mouth
FUNNEL_THROAT = 0.06
FUNNEL_DEPTH = 0.30
BANK_WALL = 1.2       # m behind the funnel: the rubber bumper wall


def launch_speed(x_cm, angle, m):
    """PROTOTYPE -> energy topic extension: 1/2 k x^2 = 1/2 m v^2 + m g x sin(angle)."""
    x = x_cm / 100.0
    e = 0.5 * SPRING_K * x * x - m * G * x * math.sin(math.radians(angle))
    return math.sqrt(2 * e / m) if e > 0 else 0.0


def spring_cannon(k, v):
    ball = BALLS["rubber"]
    r = ball["r"]
    tx, ty = v["dx"], v["dy"]
    speed = launch_speed(k["compression"], k["angle"], ball["mass"])
    if speed <= 0:
        return result(False, "the spring can't even lift the ball up the barrel", 0.0, "m/s")
    th = math.radians(k["angle"])
    wall = tx + BANK_WALL
    segs = [(tx - FUNNEL_MOUTH, ty, tx - FUNNEL_THROAT, ty - FUNNEL_DEPTH, E_FELT, "funnel"),
            (tx + FUNNEL_MOUTH, ty, tx + FUNNEL_THROAT, ty - FUNNEL_DEPTH, E_FELT, "funnel"),
            (tx - FUNNEL_MOUTH - 0.01, -1.0, tx - FUNNEL_MOUTH, ty, E_WOOD_WALL, "stand"),
            (wall, ty - 0.6, wall, 5.0, E_WOOD_WALL, "bumper wall")]
    zones = [("in", lambda x, y, vx, vy: tx - FUNNEL_THROAT < x < tx + FUNNEL_THROAT and
              ty - FUNNEL_DEPTH - 0.3 < y < ty - FUNNEL_DEPTH + 0.02),
             ("miss", lambda x, y, vx, vy: y < -0.3)]
    out, st, path, hits = trace(0.0, 0.0, speed * math.cos(th), speed * math.sin(th), ball, segs, zones,
                                tmax=5.0)
    bank = any(h[1] == "bumper wall" for h in hits)
    if out == "in":
        return result(True, "in the toy box" + (" - off the bumper wall!" if bank else ""), round(speed, 2),
                      "m/s", mastery=bank, path=path)
    # where the shot arrives at the box's height, on its way down (same flight, no obstacles)
    _, arr, _, _ = trace(0.0, 0.0, speed * math.cos(th), speed * math.sin(th), ball, (),
                         [("arrive", lambda x, y, vx, vy: vy < 0 and y < ty)], tmax=5.0)
    lo, hi = tx - FUNNEL_MOUTH, tx + FUNNEL_MOUTH
    where = "arrives at %.2f m, the box spans %.2f-%.2f m" % (arr[1], lo, hi)
    if lo <= arr[1] <= hi:
        return result(False, "bounced off the rim of the toy box - it came in too %s (your shot %s)"
                      % ("flat" if k["angle"] < 40 else "close to the edge", where), round(speed, 2), "m/s", path=path)
    return result(False, "missed the toy box: too %s (your shot %s)" % ("short" if arr[1] < lo else "far", where),
                  round(speed, 2), "m/s", path=path)


def _descending(path, p):
    i = path.index(p)
    return i > 0 and path[i - 1][2] > p[2]


# ===========================================================================
# LEVEL 2 - THE FOUNDRY (steel ball)
# ===========================================================================

# 2.1 Hot Ring ---------------------------------------------------------------
ALPHA = {"aluminum": 23.1e-6, "steel": 12.0e-6}     # linear expansion, 1/K
BALL_D_MM = 50.00
RING_MASS = 0.30       # kg of aluminium
KETTLE = 95.0          # C
ROOM = 20.0
CUP_LOSS = 0.1         # W/K: the ring sits in a foam-insulated cup (sandbox: towel 0.5, thermos 0.05)


def ring_bore(gap_um):
    return BALL_D_MM - gap_um / 1000.0


def hot_ring(k, v):
    """heat.run (two blocks in contact) + PROTOTYPE expansion
    D(T) = D0 (1 + alpha (T - 20))  -> heat topic extension."""
    if k["water"] <= 0.0:
        return result(False, "no hot water, nothing changes", ROOM, "C")
    bore0 = ring_bore(v["gap_um"])
    if k["target"] == "ring":
        mat_b, mass_b = "aluminum", RING_MASS
    elif k["target"] == "ball":
        mat_b, mass_b = "iron", BALLS["steel"]["mass"]                 # steel ~ iron, c = 450
    else:   # both in the bath: one block with their combined heat capacity
        mat_b, mass_b = "aluminum", RING_MASS + BALLS["steel"]["mass"] * 450.0 / 900.0
    res = heat.run({"material_a": "water", "mass_a": k["water"], "temp_a": KETTLE,
                    "material_b": mat_b, "mass_b": mass_b, "temp_b": ROOM,
                    "ambient": ROOM, "loss": CUP_LOSS})
    best, t_drop = -1e9, None
    for f in res["frames"]:
        if f["t"] > 120.0:
            break
        tb = f["temp_b"]
        t_ring = tb if k["target"] in ("ring", "both") else ROOM
        t_ball = tb if k["target"] in ("ball", "both") else ROOM
        bore = bore0 * (1 + ALPHA["aluminum"] * (t_ring - ROOM))
        dball = BALL_D_MM * (1 + ALPHA["steel"] * (t_ball - ROOM))
        gap = bore - dball
        best = max(best, gap)
        if gap >= 0.0 and t_drop is None:
            t_drop = f["t"]
    peak = max(f["temp_b"] for f in res["frames"] if f["t"] <= 120.0)
    if t_drop is None:
        why = {"ring": "the ring got to %.0f C - not hot enough to open %.0f um" % (peak, v["gap_um"]),
               "ball": "you heated the BALL - it got bigger and is stuck even harder",
               "both": "both grew: the gap only opens by the DIFFERENCE in expansion - it needs %.0f C"
                       % (ROOM + v["gap_um"] / 1000.0 / (bore0 * ALPHA["aluminum"] - BALL_D_MM * ALPHA["steel"]))}
        return result(False, why[k["target"]], round(peak, 1), "C")
    return result(True, "the ring opened after %.1f s" % t_drop, round(peak, 1), "C",
                  mastery=k["water"] <= v["thrifty"], t_drop=t_drop)


def ring_needs(gap_um):
    """Ring temperature that opens the gap (ring heated alone)."""
    return ROOM + gap_um / 1000.0 / (ring_bore(gap_um) * ALPHA["aluminum"])


# 2.2 Trapdoor Latch ---------------------------------------------------------
R_BALL = 0.05          # ohm: the steel ball between the contact plates
R_FUSE = 0.05
FUSE_A = 1.0
COIL_HOT_W = 1.5       # mastery: keep the latch coil below this


def trapdoor(k, v):
    """physlab.topics.circuitlab.solve on a loop: battery - dial resistor -
    fuse - latch coil - ball contact. PROTOTYPE (circuitlab extension):
    fuse part (opens above its rating), relay coil (acts above pull-in),
    ball-contact part (a conductor only while a metal ball sits on it)."""
    bat = BY_ID["parts"][k["battery"]]
    parts = [
        {"kind": "battery", "a": (0, 1), "b": (0, 0), "emf": bat["emf"], "r_int": bat["r_int"]},
        {"kind": "resistor", "a": (0, 0), "b": (1, 0), "R": max(k["R"], 1e-4)},
        {"kind": "resistor", "a": (1, 0), "b": (2, 0), "R": R_FUSE},
        {"kind": "resistor", "a": (2, 0), "b": (2, 1), "R": v["coil_ohm"]},
        {"kind": "resistor", "a": (2, 1), "b": (1, 1), "R": R_BALL},
        {"kind": "wire", "a": (1, 1), "b": (0, 1)},
    ]
    sol = circuitlab.solve(parts, 3, 2)
    i = abs(sol["parts"][3]["current"])
    p_coil = i * i * v["coil_ohm"]
    if i > FUSE_A:
        return result(False, "%.2f A - the 1 A fuse blew" % i, round(i, 3), "A")
    if i < v["pull_in"]:
        return result(False, "%.2f A - too weak to pull the latch (needs %.2f A)" % (i, v["pull_in"]),
                      round(i, 3), "A")
    return result(True, "%.2f A - the latch pulls, the trapdoor opens" % i, round(i, 3), "A",
                  mastery=p_coil <= COIL_HOT_W, coil_w=round(p_coil, 3))


# 2.3 Hydraulic Gate ---------------------------------------------------------
HG_D1 = 2.0            # cm, small piston (the ball rides it down)
HG_STROKE = 0.30       # m
HG_NEED = 0.06         # m the gate must rise (ball 5 cm + 1 cm)
HG_PLUNGER = 0.05      # kg
HG_PISTON = 0.10       # kg, big piston under the gate
HG_OIL = 870.0


def hydraulic_gate(k, v):
    """physlab.topics.pressure's model with a DEAD-WEIGHT push instead of a
    person (PROTOTYPE -> pressure extension "push: a weight"):
        (m_push + M (A1/A2)^2) x1'' = m_push g - c v - needed_push(x1)."""
    a1, a2 = pressure.area(HG_D1), pressure.area(k["d2"])
    m_push = BALLS["steel"]["mass"] + HG_PLUNGER
    M = v["gate_kg"] + HG_PISTON
    m_eff = m_push + M * (a1 / a2) ** 2
    f = m_push * G

    def acc(x, vel):
        return (f - pressure.C_LOSS * vel - pressure.needed_push(M, G, a1, a2, HG_OIL, x)) / m_eff
    lift_full = HG_STROKE * a1 / a2
    if f <= pressure.needed_push(M, G, a1, a2, HG_OIL, 0.0):
        return result(False, "nothing moves - the ball's weight can't hold up the gate through this piston",
                      0.0, "cm")
    x = vel = t = 0.0
    dt = 0.0005
    while t < 10.0:
        k1 = (vel, acc(x, vel))
        k2 = (vel + 0.5 * dt * k1[1], acc(x + 0.5 * dt * k1[0], vel + 0.5 * dt * k1[1]))
        k3 = (vel + 0.5 * dt * k2[1], acc(x + 0.5 * dt * k2[0], vel + 0.5 * dt * k2[1]))
        k4 = (vel + dt * k3[1], acc(x + dt * k3[0], vel + dt * k3[1]))
        x += dt / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        vel += dt / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        t += dt
        if x >= HG_STROKE:
            break
        if vel < 1e-5 and t > 0.5:
            lift = 100 * x * a1 / a2
            return result(False, "stalled %.0f cm down - the oil column's own weight now pushes back as hard "
                          "as the ball" % (100 * x), round(lift, 2), "cm")
    lift = 100 * lift_full
    if x < HG_STROKE:
        return result(False, "still creeping %.0f cm down after 10 s - the oil column's own weight almost "
                      "balances the ball" % (100 * x), round(100 * x * a1 / a2, 2), "cm")
    if lift_full < HG_NEED:
        return result(False, "the ball reached the bottom but the gate only rose %.1f cm (needs %.0f)"
                      % (lift, 100 * HG_NEED), round(lift, 2), "cm")
    return result(True, "gate up %.1f cm, ball out in %.1f s" % (lift, t), round(lift, 2), "cm",
                  mastery=lift_full >= v["high_gate"], t_down=round(t, 2))


# 2.4 Magnet Swing -----------------------------------------------------------
MS_HOLD = 12.0         # N: the crane magnet's grip on the ball
MS_GENTLE = 9.0        # N: mastery - never load the magnet past 75 %
MS_DROP = 1.2          # m from the swing's bottom to the ladle's rim
MS_LADLE = 0.10        # m half-width of the ladle mouth


def magnet_swing(k, v):
    """physlab.topics.pendulum.run (tension m(g cos th + L w^2) is already
    in every frame) + PROTOTYPE magnet rule: the grip lets go if the
    tension exceeds MS_HOLD; a trip wire cuts the magnet at the bottom.
    Then the tracer flies the ball (steel drag) into the ladle."""
    ball = BALLS["steel"]
    L, th0 = k["length"], k["angle"]
    res = pendulum.run({"length": L, "amplitude": th0, "mass": ball["mass"], "g": G, "drag": ball["k"]})
    fr = res["frames"]
    # release from the LEFT (theta = -th0), swinging right towards the pit
    peak_t = 0.0
    for a, b in zip(fr, fr[1:]):
        peak_t = max(peak_t, a["tension"])
        if a["tension"] > MS_HOLD:                       # magnet loses its grip early
            th, om = -a["theta"], -a["omega"]
            x = L * math.sin(th)
            y = L * (1 - math.cos(th))
            vx, vy = L * om * math.cos(th), L * om * math.sin(th)
            return result(False, "the magnet lost its grip at %.0f deg (the ball pulled %.1f N, the magnet "
                          "holds %.0f N)" % (abs(math.degrees(th)), a["tension"], MS_HOLD), round(a["tension"], 2),
                          "N", path=[(0, x, y)])
        if a["theta"] > 0 >= b["theta"] or a["theta"] < 0 <= b["theta"]:
            break
    speed = max(abs(f["v"]) for f in fr[:fr.index(b) + 1])
    d, ty = v["ladle"], -MS_DROP
    r = ball["r"]
    out, st, path, hits = trace(0.0, 0.0, speed, 0.0, ball, [],
                                [("down", lambda x, y, vx, vy: y < ty)], tmax=3.0)
    land = st[1]
    ok = d - MS_LADLE + r <= land <= d + MS_LADLE - r
    if not ok:
        return result(False, "landed at %.2f m - the ladle is at %.2f m" % (land, d), round(peak_t, 2), "N",
                      land=round(land, 3), path=path)
    return result(True, "into the ladle (landed %.2f m out)" % land, round(peak_t, 2), "N",
                  mastery=peak_t <= MS_GENTLE, land=round(land, 3), path=path)


# ===========================================================================
# LEVEL 3 - MILLBROOK MILL (wooden ball)
# ===========================================================================

# 3.1 Crow's Well ------------------------------------------------------------
WELL_D = 10.0          # cm inside diameter
WELL_AREA = math.pi * (WELL_D / 2) ** 2        # cm^2
PADDLE_Y = 45.0        # cm: the paddle wheel sweeps the ball out here
PADDLE_BAND = 2.5      # cm: the ball's centre must be within +- this
DROP_ITEMS = {         # what's lying around the mill (volume cm^3, density kg/m^3)
    "stone": {"label": "River stone", "V": 200.0, "rho": 2600.0},
    "bearing": {"label": "Steel bearing (from the Foundry)", "V": BALLS["steel"]["V"] * 1e6, "rho": 7792.0},
    "block": {"label": "Pine block (4 cm)", "V": 64.0, "rho": 510.0},
}


def displaced_cm3(item, n):
    """Sinkers push aside their whole volume; floaters only their own weight of water."""
    it = DROP_ITEMS[item]
    per = it["V"] if it["rho"] > RHO_WATER else it["V"] * it["rho"] / RHO_WATER
    return n * per


def crows_well(k, v):
    """buoyancy (float depth of the wooden sphere, V_sub/V = rho_wood/rho_water)
    + the level rise of the tank (PROTOTYPE -> buoyancy extension: extra
    sunk objects and a custom tank area)."""
    ball = BALLS["wood"]
    frac = ball["rho"] / RHO_WATER
    h_sub = buoyancy.float_depth("sphere", ball["d"], frac) * 100.0     # cm
    v_sub = ball["V"] * frac * 1e6                                      # cm^3
    level = v["depth0"] + (v_sub + displaced_cm3(k["item"], k["count"])) / WELL_AREA
    centre = level - h_sub + ball["r"] * 100.0
    off = centre - PADDLE_Y
    if off < -PADDLE_BAND:
        return result(False, "the ball floats at %.1f cm - the paddles sweep at %.0f cm" % (centre, PADDLE_Y),
                      round(centre, 2), "cm")
    if off > PADDLE_BAND:
        return result(False, "too high: the ball is pressed against the grate (%.1f cm)" % centre,
                      round(centre, 2), "cm")
    return result(True, "the paddle wheel sweeps it out (centre at %.1f cm)" % centre, round(centre, 2), "cm",
                  mastery="_best" not in v and k["count"] <= fewest_drops(v))


def fewest_drops(v):
    """The smallest number of drops (of any one item) that floats the ball to the paddles."""
    best = 10 ** 9
    for item in DROP_ITEMS:
        n = next((n for n in range(0, 41) if crows_well({"item": item, "count": n}, dict(v, _best=0))["ok"]), None)
        if n is not None:
            best = min(best, n)
    return best


# 3.2 Fan Jump ---------------------------------------------------------------
FJ_U0 = 2.0            # m/s off the ski-jump lip (measured from the chute)
FJ_ANGLE = 10.0        # deg
FJ_DROP = 2.5          # m from the lip down to the hay cart
FJ_CART_HALF = 0.125   # m


def fan_jump(k, v, ball_id="wood"):
    ball = BALLS[ball_id]
    th = math.radians(FJ_ANGLE)
    out, st, path, hits = trace(0.0, 0.0, FJ_U0 * math.cos(th), FJ_U0 * math.sin(th), ball, [],
                                [("down", lambda x, y, vx, vy: y < -FJ_DROP + ball["r"])],
                                wind=k["wind"], tmax=3.0, dt=5e-4)
    land, c, r = st[1], v["cart"], ball["r"]
    if land < c - FJ_CART_HALF + r:
        return result(False, "splash! landed in the mill race %.2f m out (the cart is at %.2f m)" % (land, c),
                      round(land, 3), "m", path=path)
    if land > c + FJ_CART_HALF - r:
        return result(False, "blown past the cart into the hedge (%.2f m)" % land, round(land, 3), "m", path=path)
    return result(True, "in the hay cart at %.2f m" % land, round(land, 3), "m",
                  mastery=k["wind"] <= v["breeze"], path=path)


# 3.3 Light Gate -------------------------------------------------------------
LG_LENS = {"kind": "converging", "material": "crown", "radius": 20.0}   # f = 19.2 cm
LG_LAMP = 2.0          # cm: the lamp's glowing window
LG_APERTURE = 2 * optics.APERTURE                                       # 10 cm lens
LG_CELL = 1.0          # cm: photocell size
LG_ARM = 0.5           # share of the collected light the cell needs to arm
LG_SHARP = 0.5         # cm: mastery - the cell within this of the sharp image


def light_gate(k, v):
    """optics.run (thin-lens image) + PROTOTYPE photocell: the light patch at
    the cell = the lamp's image scaled to the cell plane + the blur circle
    of an out-of-focus cone; the cell catches (cell / patch)^2 of it."""
    d_o = k["d_o"]
    res = optics.run(dict(LG_LENS, d_o=d_o, h_o=LG_LAMP))
    d_i, f = res["viz"]["d_i"], res["viz"]["f"]
    s = v["bench"] - d_o                                   # lens -> photocell
    if s <= 0:
        return result(False, "the lens can't sit behind the cell", 0.0, "")
    if d_i is None or not math.isfinite(d_i):
        blur = LG_APERTURE
        defocus = float("inf")
    else:
        blur = LG_APERTURE * abs(s - d_i) / abs(d_i)
        defocus = s - d_i
    patch = LG_LAMP * s / d_o + blur
    share = min(1.0, (LG_CELL / patch) ** 2)
    if share < LG_ARM:
        why = "only %.0f%% of the light reaches the cell" % (100 * share)
        if math.isfinite(defocus) and abs(defocus) < 1.0:
            why += " - it IS in focus, but the image is %.1f cm wide (magnified x%.1f) and the cell is %.0f cm" % (
                abs(res["viz"]["h_i"]), abs(res["viz"]["m"]), LG_CELL)
        elif d_i < 0:
            why += " - the lamp is inside the focal length: no real image, the light spreads out"
        elif d_i > 5 * v["bench"]:
            why += " - the lamp is at the focal point: the light leaves the lens as a wide parallel beam"
        elif math.isfinite(defocus):
            why += " - the sharp image is %.1f cm %s the cell" % (abs(defocus), "in front of" if defocus > 0 else "behind")
        return result(False, why, round(share, 3), "share", f=f)
    return result(True, "%.0f%% of the light on the cell - the gate is armed" % (100 * share), round(share, 3),
                  "share", mastery=abs(defocus) <= LG_SHARP, f=f, d_i=d_i)


# 3.4 Mill Hoist -------------------------------------------------------------
MH_BEAM_L, MH_BEAM_M = 2.2, 1.0    # m, kg (uniform, pivot in the middle)
MH_SCOOP = 0.10        # kg
MH_BUCKET = 0.20       # kg (empty)
MH_STOP = 25.0         # deg: the beam swings from -25 to +25
MH_FRICTION = 0.03     # N m at the pivot
MH_GENTLE = 1.0        # m/s: faster than this at the top stop and the ball is flung
MH_FEATHER = 0.5       # m/s: mastery


def mill_hoist(k, v):
    """PROTOTYPE -> new topic "Levers & Moments" (levers.py): a rigid beam
    on a pivot, principle of moments + rotation: I alpha = tau.
        tau = g cos(th) (M b - m a) - friction,   I = I_beam + m a^2 + M b^2"""
    a, b = v["arm"], k["hook"]
    m = BALLS["wood"]["mass"] + MH_SCOOP
    M = MH_BUCKET + k["water"]          # 1 L of water = 1 kg
    inertia = MH_BEAM_M * MH_BEAM_L ** 2 / 12.0 + m * a * a + M * b * b
    moment_ratio = (M * b) / (m * a)

    def tau(th):
        return G * math.cos(th) * (M * b - m * a) - MH_FRICTION
    th, om, t, dt = -math.radians(MH_STOP), 0.0, 0.0, 0.001
    if tau(th) <= 0.0:
        return result(False, "the hoist doesn't budge: bucket %.3f kg m < scoop %.3f kg m (+ friction)"
                      % (M * b, m * a), round(moment_ratio, 3), "x balance")
    while th < math.radians(MH_STOP):
        om += tau(th) / inertia * dt
        th += om * dt
        t += dt
        if t > 15.0:
            return result(False, "too slow - still creeping up after 15 s", round(moment_ratio, 3), "x balance")
    speed = om * a
    if speed > MH_GENTLE:
        return result(False, "flung! the scoop hit the top stop at %.2f m/s and the light ball flew out" % speed,
                      round(moment_ratio, 3), "x balance", speed=speed)
    return result(True, "onto the millstone shelf at %.2f m/s after %.1f s" % (speed, t), round(moment_ratio, 3),
                  "x balance", mastery=speed <= MH_FEATHER, speed=speed, t_up=t)


# ===========================================================================
# the station table
# ===========================================================================

def num(id_, lo, hi, step, unit=""):
    return {"id": id_, "kind": "number", "min": lo, "max": hi, "step": step, "unit": unit}


def integer(id_, lo, hi):
    return {"id": id_, "kind": "integer", "min": lo, "max": hi, "step": 1}


def choice(id_, ids):
    return {"id": id_, "kind": "choice", "choices": list(ids)}


STATIONS = [
    {"id": "1.1", "title": "Bounce Flap", "fn": bounce_flap,
     "knobs": [num("hatch", 1.0, 4.0, 0.05, "m"), choice("pad", RESTITUTION["rubber"])],
     "variant": {"flap": 1.5, "duct_gap": 0.8, "low_drop": None},
     "vary": {"flap": (1.4, 1.6)},
     "solutions": [{"hatch": 2.7, "pad": "steel_plate"}, {"hatch": 3.4, "pad": "hardwood"}],
     "wrong": [{"hatch": 1.6, "pad": "steel_plate"}, {"hatch": 4.0, "pad": "steel_plate"},
               {"hatch": 4.0, "pad": "foam_mat"}, {"hatch": 2.7, "pad": "hardwood"}]},
    {"id": "1.2", "title": "Salt Canal", "fn": salt_canal,
     "knobs": [integer("bags", 0, 20)],
     "variant": {"litres": 40.0},
     "vary": {"litres": (36.0, 44.0)},
     "solutions": [{"bags": 11}, {"bags": 14}], "wrong": [{"bags": 0}, {"bags": 1}, {"bags": 10}]},
    {"id": "1.3", "title": "Camel Hump", "fn": camel_hump,
     "knobs": [num("hump", 0.20, 1.60, 0.01, "m")],
     "variant": {"h0": 1.5, "speed_run": 2.12},
     "vary": {"h0": (1.4, 1.6)},
     "solutions": [{"hump": 1.0}, {"hump": 1.2}], "wrong": [{"hump": 0.5}, {"hump": 1.5}]},
    {"id": "1.4", "title": "Spring Cannon", "fn": spring_cannon,
     "knobs": [num("compression", 2.0, 20.0, 0.1, "cm"), num("angle", 15.0, 75.0, 1.0, "deg")],
     "variant": {"dx": 2.6, "dy": 0.8},
     "vary": {"dx": (2.4, 2.8)},
     "probes": [("compression", {"angle": 45.0}), ("compression", {"angle": 60.0})],
     "solutions": [{"compression": 13.0, "angle": 45.0}, {"compression": 12.9, "angle": 60.0}],
     "wrong": [{"compression": 10.0, "angle": 45.0}, {"compression": 20.0, "angle": 20.0}]},

    {"id": "2.1", "title": "Hot Ring", "fn": hot_ring,
     "knobs": [choice("target", ["ring", "ball", "both"]), num("water", 0.0, 0.50, 0.01, "kg")],
     "variant": {"gap_um": 60.0, "thrifty": 0.18},
     "vary": {"gap_um": (50.0, 70.0)},
     "solutions": [{"target": "ring", "water": 0.20}, {"target": "ring", "water": 0.50}],
     "wrong": [{"target": "ball", "water": 0.50}, {"target": "both", "water": 0.50},
               {"target": "ring", "water": 0.10}]},
    {"id": "2.2", "title": "Trapdoor Latch", "fn": trapdoor,
     "knobs": [choice("battery", ["aa", "lantern", "nine_v", "car_battery"]), num("R", 0.0, 50.0, 0.5, "ohm")],
     "variant": {"coil_ohm": 8.0, "pull_in": 0.30},
     "vary": {"coil_ohm": (7.0, 9.0), "pull_in": (0.28, 0.32)},
     "solutions": [{"battery": "lantern", "R": 0.0}, {"battery": "car_battery", "R": 20.0}],
     "wrong": [{"battery": "aa", "R": 0.0}, {"battery": "car_battery", "R": 0.0},
               {"battery": "lantern", "R": 20.0}]},
    {"id": "2.3", "title": "Hydraulic Gate", "fn": hydraulic_gate,
     "knobs": [num("d2", 2.0, 10.0, 0.1, "cm")],
     "variant": {"gate_kg": 1.0, "high_gate": 0.075},
     "vary": {"gate_kg": (0.9, 1.1)},
     "solutions": [{"d2": 3.9}, {"d2": 4.2}], "wrong": [{"d2": 2.9}, {"d2": 6.0}]},
    {"id": "2.4", "title": "Magnet Swing", "fn": magnet_swing,
     "knobs": [num("length", 0.40, 2.00, 0.05, "m"), num("angle", 10.0, 90.0, 1.0, "deg")],
     "variant": {"ladle": 1.5},
     "vary": {"ladle": (1.4, 1.6)},
     "probes": [("angle", {"length": L_}) for L_ in (0.6, 0.8, 1.0, 1.5, 2.0)],
     "solutions": [{"length": 1.0, "angle": 58.0}, {"length": 2.0, "angle": 40.0}],
     "wrong": [{"length": 0.6, "angle": 78.0}, {"length": 1.0, "angle": 30.0}]},

    {"id": "3.1", "title": "Crow's Well", "fn": crows_well,
     "knobs": [choice("item", list(DROP_ITEMS)), integer("count", 0, 40)],
     "variant": {"depth0": 20.0},
     "vary": {"depth0": (18.0, 22.0)},
     "solutions": [{"item": "stone", "count": 9}, {"item": "bearing", "count": 28}],
     "wrong": [{"item": "block", "count": 40}, {"item": "stone", "count": 12}, {"item": "bearing", "count": 9}]},
    {"id": "3.2", "title": "Fan Jump", "fn": fan_jump,
     "knobs": [num("wind", 0.0, 20.0, 0.5, "m/s")],
     "variant": {"cart": 1.975, "breeze": None},
     "vary": {"cart": (1.9, 2.05)},
     "solutions": [{"wind": 15.0}], "wrong": [{"wind": 0.0}, {"wind": 20.0}]},
    {"id": "3.3", "title": "Light Gate", "fn": light_gate,
     "knobs": [num("d_o", 5.0, 95.0, 0.5, "cm")],
     "variant": {"bench": 100.0},
     "vary": {"bench": (95.0, 105.0)},
     "solutions": [{"d_o": 74.0}], "wrong": [{"d_o": 26.0}, {"d_o": 50.0}, {"d_o": 19.0}]},
    {"id": "3.4", "title": "Mill Hoist", "fn": mill_hoist,
     "knobs": [num("hook", 0.20, 1.00, 0.05, "m"), num("water", 0.0, 2.0, 0.01, "L")],
     "variant": {"arm": 1.0},
     "vary": {"arm": (0.9, 1.1)},
     "probes": [("water", {"hook": b_}) for b_ in (0.3, 0.5, 0.7, 1.0)],
     "solutions": [{"hook": 0.5, "water": 0.40}], "wrong": [{"hook": 0.5, "water": 0.2}, {"hook": 1.0, "water": 2.0}]},
]
BY_STATION = {s["id"]: s for s in STATIONS}


def grid(knob):
    if knob["kind"] == "choice":
        return list(knob["choices"])
    n = int(round((knob["max"] - knob["min"]) / knob["step"]))
    vals = [knob["min"] + i * knob["step"] for i in range(n + 1)]
    return [int(round(x)) for x in vals] if knob["kind"] == "integer" else [round(x, 4) for x in vals]


def knob_space(st):
    out = [{}]
    for kn in st["knobs"]:
        out = [dict(o, **{kn["id"]: v}) for o in out for v in grid(kn)]
    return out


def par_for(bits):
    """Test runs allowed for the efficiency star: fewer than a systematic
    search (bisection) needs on average (~ bits + 1 runs), at least 2
    (one calculated run + one correction)."""
    return max(2, int(math.floor(bits))) if bits else 2


def analyse(st, samples, rng):
    """Solution density over the whole knob space (what a student who
    guesses at random hits), windows along each knob, mastery density."""
    space = knob_space(st)
    pick = space if len(space) <= samples else rng.sample(space, samples)
    runs = [(k, st["fn"](k, st["variant"])) for k in pick]
    ok = [k for k, r in runs if r["ok"]]
    mast = [k for k, r in runs if r["mastery"]]
    p = len(ok) / float(len(runs))
    pm = len(mast) / float(len(runs))
    return {"space": len(space), "sampled": len(runs), "p": p, "bits": (-math.log2(p) if p > 0 else None),
            "p_mastery": pm, "bits_mastery": (-math.log2(pm) if pm > 0 else None), "ok": ok, "runs": runs}


def windows_1d(st, fixed=None, knob=None):
    """Contiguous success ranges along one numeric knob (others fixed)."""
    kn = knob or next(k for k in st["knobs"] if k["kind"] != "choice")
    spans, cur = [], None
    for x in grid(kn):
        k = dict(fixed or {}, **{kn["id"]: x})
        ok = st["fn"](k, st["variant"])["ok"]
        if ok and cur is None:
            cur = [x, x]
        elif ok:
            cur[1] = x
        elif cur is not None:
            spans.append(tuple(cur))
            cur = None
    if cur is not None:
        spans.append(tuple(cur))
    return spans


def solvable(st, variant, rng, tries=400):
    space = knob_space(st)
    pick = space if len(space) <= tries else rng.sample(space, tries)
    return next((k for k in pick if st["fn"](k, variant)["ok"]), None)


def finish_variants():
    """Fill in the mastery thresholds that depend on the station's own physics."""
    bf = BY_STATION["1.1"]
    lo = min(k["hatch"] for k in knob_space(bf)
             if k["pad"] == "steel_plate" and bounce_flap(k, dict(bf["variant"], low_drop=0))["ok"])
    bf["variant"]["low_drop"] = round(lo + 0.15, 2)          # within 15 cm of the lowest possible drop
    fj = BY_STATION["3.2"]
    lo = min(k["wind"] for k in knob_space(fj) if fan_jump(k, dict(fj["variant"], breeze=99))["ok"])
    fj["variant"]["breeze"] = lo + 1.0


def report(ids, samples, as_json=None):
    rng = random.Random(20240607)
    finish_variants()
    out = {}
    for st in STATIONS:
        if ids and st["id"] not in ids:
            continue
        t0 = time.time()
        print("=" * 78)
        print("%s  %s   knobs: %s" % (st["id"], st["title"], ", ".join(k["id"] for k in st["knobs"])))
        for k in st["solutions"]:
            r = st["fn"](k, st["variant"])
            print("  reference %-40s -> %s  %s" % (k, "PASS" if r["ok"] else "** FAIL **", r["reason"]))
        for k in st["wrong"]:
            r = st["fn"](k, st["variant"])
            print("  wrong     %-40s -> %s  %s" % (k, "fails" if not r["ok"] else "** PASSES **", r["reason"]))
        a = analyse(st, samples, rng)
        print("  solution density %.1f%% of %d settings (%d sampled) -> %.1f bits;  mastery %.1f%% -> %s bits"
              % (100 * a["p"], a["space"], a["sampled"], a["bits"] or float("nan"), 100 * a["p_mastery"],
                 "%.1f" % a["bits_mastery"] if a["bits_mastery"] else "-"))
        win = {}
        choices = [k for k in st["knobs"] if k["kind"] == "choice"]
        nums = [k for k in st["knobs"] if k["kind"] != "choice"]
        if len(nums) == 1:
            for c in (grid(choices[0]) if choices else [None]):
                fixed = {choices[0]["id"]: c} if c is not None else {}
                w = windows_1d(st, fixed)
                win[str(c)] = w
                print("  window %s%s = %s" % (nums[0]["id"], (" | %s=%s" % (choices[0]["id"], c)) if c else "", w))
        for kid, fixed in st.get("probes", []):
            kn = next(k for k in st["knobs"] if k["id"] == kid)
            w = windows_1d(st, fixed, kn)
            win["%s | %s" % (kid, fixed)] = w
            print("  window %s | %s = %s" % (kid, fixed, w))
        vr = {}
        for key, (lo, hi) in st.get("vary", {}).items():
            for val in (lo, hi):
                var = dict(st["variant"], **{key: val})
                ex = solvable(st, var, rng)
                vr["%s=%s" % (key, val)] = ex
                print("  variant %s=%s: %s" % (key, val, "solvable, e.g. %s" % ex if ex else "** UNSOLVABLE **"))
        par = par_for(a["bits"])
        print("  par (efficiency star): %d test runs" % par)
        out[st["id"]] = {"title": st["title"], "p": a["p"], "bits": a["bits"], "p_mastery": a["p_mastery"],
                         "bits_mastery": a["bits_mastery"], "windows": win, "space": a["space"],
                         "variants": vr, "par": par}
        print("  (%.0f s)" % (time.time() - t0))
    if as_json:
        with open(as_json, "w") as f:
            json.dump(out, f, indent=1, default=str)
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    js = None
    if "--json" in args:
        i = args.index("--json")
        js = args[i + 1]
        del args[i:i + 2]
    quick = "--quick" in args
    ids = [a for a in args if not a.startswith("--")]
    report(ids, 150 if quick else 500, js)
