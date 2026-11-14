"""Bounces: drop a ball onto a surface and watch each bounce come back lower.

    coefficient of restitution   e = v_after / v_before     (0 = splat, 1 = perfect)
    impact speed from a drop h   v = sqrt(2 g h)
    bounce height                h1 = e^2 h0                (height ~ speed^2)
    after n bounces              h_n = e^(2n) h0
    energy kept per bounce       e^2                        (the rest: heat, sound, squish)

e belongs to the PAIR ball x surface, not to the ball alone: a rubber ball
keeps e = 0.85 of its speed on a steel plate but only 0.10 in sand. The
values are typical published ones (bounce tests of balls on hard floors,
sports-ball regulations, e.g. a tennis ball dropped 254 cm must rebound
135-147 cm on concrete: e ~ 0.73-0.76).

The ball is flown by the shared tracer (topics/tracer.py): gravity + air
drag (k = 1/2 rho C_d A, switchable), and the floor reverses the ball's
speed x e on every contact. So with air the bounces come out a few percent
lower than e^2 h0 - the readouts show both. Same inputs -> same frames.
"""

import math

from . import tracer

# restitution e: ball x surface (typical published values)
RESTITUTION = {
    "rubber": {"steel_plate": 0.85, "hardwood": 0.75, "foam_mat": 0.45, "sand": 0.10},
    "tennis": {"steel_plate": 0.78, "hardwood": 0.73, "foam_mat": 0.40, "sand": 0.08},
    "steel":  {"steel_plate": 0.90, "hardwood": 0.50, "foam_mat": 0.20, "sand": 0.05},
    "wood":   {"steel_plate": 0.60, "hardwood": 0.50, "foam_mat": 0.25, "sand": 0.05},
}
BOUNCES = 6            # contacts recorded (then the run ends)
T_MAX = 12.0
REST = 0.002           # m: a bounce lower than this counts as "stopped bouncing"


def ball_spec(ball_id):
    from .. import BOUNCE_BALLS
    return next(b for b in BOUNCE_BALLS if b["id"] == ball_id)


def surface_spec(surface_id):
    from .. import BOUNCE_SURFACES
    return next(s for s in BOUNCE_SURFACES if s["id"] == surface_id)


def ideal_heights(h0, e, n=BOUNCES):
    """h_n = e^(2n) h0, no air."""
    return [h0 * e ** (2 * i) for i in range(1, n + 1)]


def run(p):
    ball, surface = ball_spec(p["ball"]), surface_spec(p["surface"])
    return simulate(ball, surface, p["height"], p["g"], tracer.RHO_AIR if p["air"] else 0.0)


def simulate(ball, surface, h0, g, rho_air, label=None):
    """Drop `ball` (dict: id, mass, d, cd, color, label) from h0 metres (its
    bottom above the floor) onto `surface` (dict: id, label, color)."""
    m, d = ball["mass"], ball["d"]
    r = d / 2.0
    e = RESTITUTION[ball["id"]][surface["id"]]
    k = tracer.drag_constant(d, ball.get("cd", 0.47), rho_air)
    floor = [(-5.0, 0.0, 5.0, 0.0, e, "floor")]
    out = tracer.trace(0.0, h0 + r, 0.0, 0.0, m, r, k, segs=floor, g=g, tmax=T_MAX, record=1.0 / 120.0,
                       stop_hits=BOUNCES + 1)
    e0 = m * g * h0
    frames = []
    for f in out["frames"]:
        h = f["y"] - r
        v2 = f["vx"] ** 2 + f["vy"] ** 2
        pe, ke = m * g * h, 0.5 * m * v2
        frames.append({"t": f["t"], "y": round(h, 5), "v": round(f["vy"], 4),
                       "pe": round(pe, 6), "ke": round(ke, 6), "heat": round(max(0.0, e0 - pe - ke), 6)})
    # each bounce's top: the highest point between two contacts (from the
    # recorded path, refined with the local parabola)
    hit_t = [h["t"] for h in out["hits"]]
    apexes = []
    for i in range(len(hit_t) - 1):
        seg = [f for f in frames if hit_t[i] < f["t"] < hit_t[i + 1]]
        if not seg:
            continue
        top = max(seg, key=lambda f: f["y"])
        h_top = top["y"] + top["v"] * top["v"] / (2.0 * g)     # tiny correction: v is ~0 at the top
        if h_top < REST:
            break
        apexes.append({"t": top["t"], "h": round(h_top, 4)})
    impact = out["hits"][0]["speed"] if out["hits"] else 0.0
    ideal = ideal_heights(h0, e)
    h1 = apexes[0]["h"] if apexes else 0.0
    notes = []
    if rho_air == 0.0:
        notes.append("No air: every bounce reaches exactly e² of the one before (%.0f%%)." % (100 * e * e))
    else:
        notes.append("The air takes a little on the way down and up, so the first bounce reaches %.2f m instead "
                     "of e² × h0 = %.2f m." % (h1, ideal[0]))
    if e <= 0.1:
        notes.append("%s hardly bounces on %s: the surface soaks up the energy." % (
            ball["label"].split(" (")[0], surface["label"].lower()))
    viz = {"ball": {k_: ball[k_] for k_ in ("id", "label", "color", "d", "mass")},
           "surface": dict(surface), "e": e, "h0": h0, "r": r, "apexes": apexes,
           "ideal": [round(h, 4) for h in ideal], "hits": [h["t"] for h in out["hits"]], "g": g,
           "air": rho_air > 0}
    return {
        "frames": frames,
        "viz": viz,
        "notes": notes,
        "readouts": [
            {"label": "Restitution e (%s on %s)" % (ball["label"].split(" (")[0].lower(), surface["label"].lower()),
             "value": e, "unit": ""},
            {"label": "Drop height h0", "value": round(h0, 3), "unit": "m"},
            {"label": "Speed hitting the floor", "value": round(impact, 3), "unit": "m/s"},
            {"label": "First bounce height h1", "value": round(h1, 3), "unit": "m"},
            {"label": "First bounce, no air (e² h0)", "value": round(ideal[0], 3), "unit": "m"},
            {"label": "Energy kept by the first bounce", "value": round(100.0 * h1 / h0, 1) if h0 else 0.0,
             "unit": "%"},
            {"label": "Bounces higher than 1 cm", "value": sum(1 for a in apexes if a["h"] >= 0.01), "unit": ""},
        ],
        "formula": [
            {"expr": "v = sqrt(2*g*h)", "values": {"g": round(g, 2), "h": round(h0, 3),
                                                   "v": round(math.sqrt(2 * g * h0), 3)}},
            {"expr": "v_after = e * v_before", "values": {"e": e, "v_before": round(impact, 3),
                                                         "v_after": round(e * impact, 3)}},
            {"expr": "h1 = e^2 * h0", "values": {"e^2": round(e * e, 4), "h0": round(h0, 3),
                                                 "h1 (no air)": round(ideal[0], 3), "h1 (measured)": round(h1, 3)}},
        ],
    }
