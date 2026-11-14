"""Hall 3 - Millbrook Mill (wooden ball). GDD section 6.3.

Four stations, each a thin adapter around a physlab engine (and each with a
lab link that reproduces it):

    3.1 Crow's Well   topics/buoyancy.py (the narrow well + stones)   -> #/buoyancy?vessel=well
    3.2 Fan Jump      topics/tracer.py (drag + wind)                  -> #/motion?height=2.5&wind=...
    3.3 Light Gate    topics/optics.py (thin lens + a photocell)      -> #/optics?screen=...
    3.4 Mill Hoist    topics/levers.py (moments + rotation)           -> #/levers

The wooden ball floats, the wind pushes it around, and it does NOT
conduct: it floats up a narrow well when the student drops stones in,
gets blown across the mill race by the winnowing fan, breaks a light beam
(the old Foundry contact plates can't see it) and rides a counterweight
hoist up to the millstone hopper.

Stations work in local coordinates; LAYOUT places them in the hall. Runs
return world frames {t, x, y, + the station fields the scene draws: the
well's water level lv, the drawbridge's opening `bridge`, the hoist's beam
angle th}.
"""

import math
import os

from .. import BOUNCE_BALLS, FLUIDS, GLASSES, SOLIDS
from ..topics import buoyancy, levers, optics, tracer
from . import kit
from .common import choice, fact, integer, num

G = 9.81
BALL = dict(next(b for b in BOUNCE_BALLS if b["id"] == "wood"))       # the sandbox's wooden ball (0.16 kg, 8 cm)
BALL_R = BALL["d"] / 2.0
BALL_K = tracer.drag_constant(BALL["d"], BALL["cd"])                  # 1.45e-3 kg/m
WOOD = dict(next(s for s in SOLIDS if s["id"] == "woodball"))         # 597 kg/m^3 (the lab's "toy-ball wood")
WATER = dict(next(f for f in FLUIDS if f["id"] == "water"))
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "mill.json")

# ---------------------------------------------------------------- the hall layout (world metres)
# (matches docs/game/img/level3_mill.png)
WELL = (1.0, 2.90)              # 3.1: the well's axis and its floor
WELL_H = buoyancy.VESSELS["well"]["h"]           # 0.70 m deep, 10 cm across
WELL_A = buoyancy.VESSELS["well"]["area"]        # m^2
PADDLE = 0.45                   # 3.1: the paddle wheel sweeps the ball out here (centre height above the floor)
PADDLE_BAND = 0.025
LIP = (2.45, 3.02)              # 3.2: the ski-jump lip at the end of the chute
FJ_U0, FJ_ANGLE, FJ_DROP = 2.0, 10.0, 2.5        # m/s off the lip, degrees up, m down to the cart's rim
CART_HALF = 0.125               # 3.2: half the hay cart
PATH_Y = 0.25                   # 3.3: the path's deck
PATH_X0 = 4.85                  # 3.3: where the ball joins the path
GATE_X = 6.25                   # 3.3: the light beam (the lamp above, the photocell in the path)
BRIDGE = (7.35, 8.05)             # 3.3: the drawbridge
ROLL = 0.6                      # m/s: the ball rolls along the path
PIVOT = (9.45, 0.72)             # 3.4: the hoist's pivot
SCOOP_LIFT = 0.055              # 3.4: the ball's centre sits this far above the beam end (in the scoop)
SHELF = (8.14, 8.45, 1.14)      # 3.4: the millstone shelf (x0, x1, top): the scoop tips the ball onto it
HOPPER = (7.95, 0.93)           # B: the millstone hopper (its rim level with the shelf), on the mill floor

LAYOUT = {
    "bounds": {"x0": -0.4, "x1": 10.8, "y0": -0.3, "y1": 5.9},        # (room above for the HUD)
    "A": [0.30, 4.75], "chute": [[0.30, 4.45], [0.96, 3.72]],
    "stations": {
        "3.1": {"well": list(WELL), "h": WELL_H, "w": buoyancy.WELL_D, "paddle": PADDLE, "band": PADDLE_BAND,
                "wheel": [WELL[0] + 0.20, WELL[1] + PADDLE], "wheel_r": 0.15,
                "view": {"x0": 0.1, "x1": 1.8, "y0": 2.75, "y1": 4.0}},
        "3.2": {"lip": list(LIP), "angle": FJ_ANGLE, "drop": FJ_DROP, "cart_half": CART_HALF,
                "fan": [2.08, 3.45], "fan_r": 0.25, "race": [2.7, 4.2], "slot": [WELL[0] + 0.06, WELL[1] + PADDLE],
                "view": {"x0": 1.55, "x1": 5.0, "y0": -0.05, "y1": 4.0}},
        "3.3": {"path_y": PATH_Y, "x0": PATH_X0, "gate_x": GATE_X, "plates": [5.35, 5.65], "bridge": list(BRIDGE),
                "lens_r": 0.05, "view": {"x0": 4.55, "x1": 8.65, "y0": -0.1, "y1": 1.7}},
        "3.4": {"pivot": list(PIVOT), "beam": levers.BEAM_L, "stop": levers.STOP, "lift": SCOOP_LIFT,
                "shelf": list(SHELF), "hopper": list(HOPPER),
                "view": {"x0": 7.35, "x1": 10.8, "y0": -0.1, "y1": 1.95}},
    },
    "ball": {"r": BALL_R, "color": BALL["color"]},
}


# ================================================================ 3.1 Crow's Well
DROP_ITEMS = [
    {"id": "stone", "label": "River stones", "icon": "🪨", "V": 200.0, "rho": 2600.0,
     "desc": "200 cm³ each, 2600 kg/m³ - they sink"},
    {"id": "bearing", "label": "Steel bearings", "icon": "⚙️", "V": round(math.pi * 5.0 ** 3 / 6.0, 2), "rho": 7792.0,
     "desc": "65.45 cm³ each (5 cm, left over from the Foundry) - they sink"},
    {"id": "block", "label": "Pine blocks", "icon": "🪵", "V": 64.0, "rho": 510.0,
     "desc": "4 cm cubes, 64 cm³ each, pine 510 kg/m³ - they float"},
]
ITEM = {it["id"]: it for it in DROP_ITEMS}
WELL_CM2 = WELL_A * 1e4
WELL_COST_CM, WELL_COST_ITEM = 150.0, 10.0


def displaced_cm3(item_id, n):
    """Sinkers push aside their whole volume; floaters only their own weight of water."""
    it = ITEM[item_id]
    per = it["V"] if it["rho"] > WATER["rho"] else it["V"] * it["rho"] / WATER["rho"]
    return n * per


def well_params(k, fx):
    """The buoyancy lab's set-up for this well (the station and its lab link use the same)."""
    extra = round(displaced_cm3(k["item"], k["count"]), 2)
    fill_cm = fx["depth"] + extra / WELL_CM2
    start = max(5.0, min(30.0, round(66.0 - fill_cm)))                 # dropped in from near the rim
    return {"shape": "sphere", "material": WOOD["id"], "size": BALL["d"] * 100.0, "fluid": "water", "g": G,
            "start": start, "salt": 0.0, "vessel": "well", "depth": fx["depth"], "extra": extra}


def well_centre_cm(k, fx):
    """Where the ball's centre floats (cm above the well floor) and the water level (cm)."""
    p = well_params(k, fx)
    fill = p["depth"] / 100.0 + p["extra"] * 1e-6 / WELL_A
    eq = buoyancy.equilibrium("sphere", BALL["d"], WOOD["rho"], WATER["rho"], fill, WELL_A)
    return (eq["y"] + BALL_R) * 100.0, eq["level"] * 100.0


def well_cost(centre, count):
    return WELL_COST_CM * abs(centre - PADDLE * 100.0) + WELL_COST_ITEM * count


def run_crows_well(k, fx, thresholds=None):
    p = well_params(k, fx)
    res = buoyancy.simulate(p, WOOD, WATER, t_max=8.0)
    centre, level = well_centre_cm(k, fx)
    off = centre - PADDLE * 100.0
    spill = level > WELL_H * 100.0
    ok = not spill and abs(off) <= PADDLE_BAND * 100.0 + 1e-9
    top = WELL_H - BALL_R                                          # it can't float above the rim (it spills)
    frames = [{"t": f["t"], "x": 0.0, "y": round(min(f["y"] + BALL_R, top), 5),
               "lv": round(min(f["level"], WELL_H), 5)} for f in kit.thin(res["frames"], 220)]
    last = frames[-1]
    if ok:                                                         # the paddles sweep it out through the slot
        for i in range(1, 9):
            frames.append({"t": round(last["t"] + 0.06 * i, 4), "x": round(0.02 * i, 4),
                           "y": round(last["y"] + (PADDLE - last["y"]) * i / 8.0, 5), "lv": last["lv"]})
    it = ITEM[k["item"]]
    if spill:
        reason = "The water overflows the well: %d %s would push it up to %.0f cm - the well is only %.0f cm deep." % (
            k["count"], it["label"].lower(), level, WELL_H * 100)
    elif ok:
        reason = "The paddle wheel sweeps it out: its centre floats at %.1f cm (the paddles sweep at %.0f ± %.1f cm)." \
                 % (centre, PADDLE * 100, PADDLE_BAND * 100)
    elif off < 0:
        reason = "The ball floats at %.1f cm - the paddles sweep at %.0f cm. The water must rise more." % (
            centre, PADDLE * 100)
        if k["item"] == "block" and k["count"] > 0:
            reason += " (A floating block only pushes aside its own weight of water - half its size.)"
    else:
        reason = "Too high: the ball floats at %.1f cm and the paddles sweep under it (at %.0f cm)." % (
            centre, PADDLE * 100)
    cost = well_cost(centre, k["count"])
    cost_min = (thresholds or {}).get("cost_min", cost)
    per = displaced_cm3(k["item"], 1)
    return {
        "ok": ok, "reason": reason, "metric": round(centre, 2), "unit": "cm", "predicted": round(centre, 2),
        "mastery": bool(ok and k["count"] <= (thresholds or {}).get("fewest", -1)),
        "score": kit.score(ok, kit.SCORE_MAX - (cost - cost_min)) if ok else 0,
        "score_parts": [{"label": "aim", "value": "%.1f cm off the paddles' 45 cm" % abs(off),
                         "note": "%.1f x 150 = %d" % (abs(off), round(WELL_COST_CM * abs(off)))},
                        {"label": "drops", "value": "%d %s" % (k["count"], it["label"].lower()),
                         "note": "%d x 10 = %d" % (k["count"], WELL_COST_ITEM * k["count"])},
                        {"label": "cost", "value": "%d" % round(cost),
                         "note": "1000 minus how much more it cost than the best way for your well"}] if ok else [],
        "frames": kit.world(frames, WELL, extra=("lv",)),
        "viz": {"centre_cm": round(centre, 2), "level_cm": round(level, 2), "extra_cm3": p["extra"],
                "per_item_cm3": round(per, 2), "spill": spill},
        "formula": [{"expr": "dh = V_pushed / A",
                     "values": {"V_pushed (%s)" % it["label"].lower(): "%d x %.1f = %.0f cm³" % (
                         k["count"], per, p["extra"]), "A": "%.1f cm²" % WELL_CM2,
                         "dh": "%.1f cm" % (p["extra"] / WELL_CM2)}},
                    {"expr": "V_sub / V = rho_obj / rho_fluid",
                     "values": {"rho_ball": WOOD["rho"], "rho_water": WATER["rho"],
                                "under": "%.0f%%" % (100 * WOOD["rho"] / WATER["rho"]),
                                "centre": "%.1f cm" % centre}}],
        "lab": [{"title": "Floating & Sinking: this well with these %s%s" % (
                    it["label"].lower(), " (a floating block counts as its own weight of water: %.1f cm³)" % per
                    if it["rho"] < WATER["rho"] else ""),
                 "route": "#/buoyancy?" + kit.query(sorted(p.items()))}],
    }


def fewest_drops(fx):
    """The smallest number of drops (of any one item) that floats the ball to the paddles."""
    best = None
    for it in DROP_ITEMS:
        for n in range(0, 41):
            c, lv = well_centre_cm({"item": it["id"], "count": n}, fx)
            if lv <= WELL_H * 100.0 and abs(c - PADDLE * 100.0) <= PADDLE_BAND * 100.0 + 1e-9:
                best = n if best is None else min(best, n)
                break
    return best


# ================================================================ 3.2 Fan Jump
FAN_AIM, FAN_POWER = 700.0, 300.0


def fly(wind):
    """The ball off the lip with the fan blowing `wind` m/s from behind: the shared tracer (motion's drag and
    wind). Returns the trace down to the cart's rim."""
    th = math.radians(FJ_ANGLE)
    return tracer.trace(0.0, 0.0, FJ_U0 * math.cos(th), FJ_U0 * math.sin(th), BALL["mass"], BALL_R, BALL_K,
                        wind=wind, dt=5e-4, tmax=3.0, zones=[("down", lambda x, y, vx, vy: y < -FJ_DROP)])


def fan_raw(land, cart, wind, w_lo):
    aim = max(0.0, 1.0 - ((land - cart) / (CART_HALF - BALL_R)) ** 2)
    power = (w_lo / wind) ** 3 if wind > 0 else 0.0
    return FAN_AIM * aim + FAN_POWER * min(1.0, power)


def run_fan_jump(k, fx, thresholds=None):
    w, c = k["wind"], fx["cart"]
    out = fly(w)
    land = out["x"]
    lo, hi = c - CART_HALF + BALL_R, c + CART_HALF - BALL_R
    ok = lo <= land <= hi
    frames = [{"t": f["t"], "x": f["x"], "y": f["y"]} for f in out["frames"]]
    t0 = frames[-1]["t"]
    if ok:                                                       # it sinks into the hay
        frames.append({"t": round(t0 + 0.15, 4), "x": round(land, 5), "y": round(-FJ_DROP - 0.10, 5)})
    else:                                                        # on down to the water (or the hedge)
        water = -(LIP[1] - 0.12) + BALL_R
        rest = tracer.trace(out["x"], out["y"], out["vx"], out["vy"], BALL["mass"], BALL_R, BALL_K, wind=w,
                            dt=5e-4, tmax=2.0, zones=[("water", lambda x, y, vx, vy: y < water)])
        frames += [{"t": round(t0 + f["t"], 4), "x": f["x"], "y": f["y"]} for f in rest["frames"][1:]]
    if ok:
        reason = "Into the hay cart at %.2f m (the cart spans %.2f-%.2f m)." % (land, c - CART_HALF, c + CART_HALF)
    elif land < lo:
        reason = "Splash! It landed in the mill race %.2f m out - the cart is at %.2f m. (The wooden ball floats " \
                 "back down the race to the well - no harm done.)" % (land, c)
    else:
        reason = "Blown past the cart into the hedge (%.2f m) - the cart is at %.2f m." % (land, c)
    w_lo = (thresholds or {}).get("w_lo", w)
    raw = fan_raw(land, c, w, w_lo)
    raw_best = (thresholds or {}).get("raw_best", raw)
    return {
        "ok": ok, "reason": reason, "metric": round(land, 3), "unit": "m", "predicted": round(land, 3),
        "mastery": bool(ok and w <= (thresholds or {}).get("breeze", -1) + 1e-9),
        "score": kit.score(ok, kit.SCORE_MAX * raw / raw_best) if ok else 0,
        "score_parts": [{"label": "aim", "value": "%d cm from the middle of the cart" % round(100 * abs(land - c)),
                         "note": "up to 700 for the middle"},
                        {"label": "fan power", "value": "%.1f m/s" % w,
                         "note": "up to 300: a fan's power grows with the wind cubed - the weakest wind that "
                                 "works saves the most"}] if ok else [],
        "frames": kit.world(frames, LIP),
        "viz": {"land": round(land, 4), "t_air": round(out["t"], 4), "no_fan": round(fly(0.0)["x"], 4)},
        "formula": [{"expr": "F = 1/2 * rho * C_d * A * (w - v)^2",
                     "values": {"rho": tracer.RHO_AIR, "C_d": BALL["cd"], "A": "%.4f m²" % (math.pi * BALL_R ** 2),
                                "w (fan)": w, "F at the lip": "%.2f N" % (BALL_K * (w - FJ_U0 * math.cos(
                                    math.radians(FJ_ANGLE))) ** 2)}},
                    {"expr": "dx = 1/2 * (F/m) * t^2",
                     "values": {"m": BALL["mass"], "t (in the air)": "%.2f s" % out["t"],
                                "gain": "%.2f m" % (land - fly(0.0)["x"])}}],
        "lab": [{"title": "Projectile Motion: the same throw, launched 2.5 m up into a %g m/s wind" % w,
                 "route": "#/motion?" + kit.query([("v0", FJ_U0), ("angle", FJ_ANGLE), ("mass", BALL["mass"]),
                                                   ("drag", round(BALL_K, 6)), ("wind", w), ("g", G),
                                                   ("height", FJ_DROP)])}],
    }


# ================================================================ 3.3 Light Gate
LG_LENS = {"kind": "converging", "material": "crown", "radius": 20.0}
LG_LAMP = 2.0                   # cm: the lamp's glowing window
LG_ARM = 0.5                    # the cell arms when it gets at least half the light
LG_SHARP = 0.5                  # cm: mastery - the cell within this of the sharp image
LG_COST = 400.0                 # points per cm out of focus (40 per mm)
N_CROWN = next(g for g in GLASSES if g["id"] == "crown")["n"]
LG_F = optics.focal_length(N_CROWN, LG_LENS["radius"], LG_LENS["kind"])      # 19.23 cm


def gate_light(d_o, bench):
    return optics.screen_patch(LG_F, d_o, LG_LAMP, bench - d_o)


def run_light_gate(k, fx, thresholds=None):
    d_o, bench = k["d_o"], fx["bench"]
    scr = gate_light(d_o, bench)
    share, defocus = scr["share"], scr["defocus"]
    d_i = optics.image_distance(LG_F, d_o)
    armed = share >= LG_ARM
    x_beam, x_bridge, x_end = GATE_X - PATH_X0, BRIDGE[0] - PATH_X0, BRIDGE[1] - PATH_X0
    t_beam = x_beam / ROLL
    frames = []
    stop = x_end if armed else x_bridge - BALL_R - 0.005
    n = int(stop / 0.05)
    for i in range(n + 1):
        x = stop * i / n
        t = x / ROLL
        b = 0.0 if not armed else max(0.0, min(1.0, (t - t_beam) / 1.0))
        frames.append({"t": round(t, 4), "x": round(x, 4), "y": BALL_R, "bridge": round(b, 3)})
    if not armed:
        frames.append({"t": round(frames[-1]["t"] + 1.0, 4), "x": frames[-1]["x"], "y": BALL_R, "bridge": 0.0})
    if armed:
        reason = "%.0f%% of the lamp's light on the cell - the gate was armed, the ball broke the beam and the " \
                 "drawbridge came down." % (100 * share)
    else:
        reason = "Only %.0f%% of the light reaches the cell (it needs %.0f%%)" % (100 * share, 100 * LG_ARM)
        if defocus is not None and abs(defocus) < 1.0:
            reason += " - it IS in focus, but the image is %.1f cm wide (magnified x%.1f) and the cell is 1 cm." % (
                scr["geo"], abs(d_i / d_o))
        elif d_i is not None and d_i < 0:
            reason += " - the lamp is inside the focal length: there's no real image, the light spreads out."
        elif d_i is None or d_i > 5 * bench:
            reason += " - the lamp is at the focal point: the light leaves the lens as a wide beam."
        else:
            reason += " - the sharp image is %.1f cm %s the cell." % (abs(defocus), "in front of" if defocus > 0
                                                                     else "behind")
        reason += " The ball rolled through the beam, but the gate wasn't armed."
    dfc = abs(defocus) if defocus is not None else 1e9
    dmin = (thresholds or {}).get("defocus_min", dfc)
    return {
        "ok": armed, "reason": reason, "metric": round(100 * share, 1), "unit": "% of the light",
        "predicted": round(100 * share, 1),
        "mastery": bool(armed and dfc <= LG_SHARP + 1e-9),
        "score": kit.score(armed, kit.SCORE_MAX - LG_COST * (dfc - dmin)) if armed else 0,
        "score_parts": [{"label": "focus", "value": "the sharp image is %.1f mm from the cell" % (10 * dfc),
                         "note": "-40 for every mm more than the sharpest your bench allows"}] if armed else [],
        "frames": kit.world(frames, (PATH_X0, PATH_Y), extra=("bridge",)),
        "viz": {"share": round(share, 4), "patch": round(scr["patch"], 3), "blur": round(scr["blur"], 3),
                "image": round(scr["geo"], 3), "d_i": round(d_i, 3) if d_i is not None else None,
                "defocus": round(defocus, 3) if defocus is not None else None, "f": round(LG_F, 3)},
        "formula": [{"expr": "1/f = 1/d_o + 1/d_i",
                     "values": {"f": round(LG_F, 2), "d_o": d_o, "d_i": round(d_i, 2) if d_i is not None else None,
                                "the cell at": bench - d_o}},
                    {"expr": "m = -d_i / d_o = h_i / h_o",
                     "values": {"h_o (lamp)": LG_LAMP, "image on the cell": "%.2f cm" % scr["geo"]}},
                    {"expr": "blur = D * |s - d_i| / d_i",
                     "values": {"D": 10.0, "s": bench - d_o, "blur": round(scr["blur"], 2),
                                "patch": round(scr["patch"], 2), "share": "%.0f%%" % (100 * share)}}],
        "lab": [{"title": "Lenses: this lens, the lamp as a 2 cm candle, the cell as a screen %g cm behind" % (
                    bench - d_o),
                 "route": "#/optics?" + kit.query([("kind", LG_LENS["kind"]), ("material", LG_LENS["material"]),
                                                   ("radius", LG_LENS["radius"]), ("d_o", d_o), ("h_o", LG_LAMP),
                                                   ("screen", round(bench - d_o, 2))])}],
    }


# ================================================================ 3.4 Mill Hoist
SCOOP_M = 0.10                  # kg: the scoop (+ the ball's 0.16)
BUCKET_M = 0.20                 # kg: the empty bucket
BEAM_M, PIVOT_F = 1.0, 0.03
GENTLE, FEATHER = 1.0, 0.5      # m/s: faster than GENTLE and the ball is flung; mastery: FEATHER or slower
SLOW = 15.0                     # s: the miller won't wait longer
HOIST_T_COST, HOIST_V_COST = 200.0, 500.0


def hoist_params(k, fx):
    return {"m1": round(BALL["mass"] + SCOOP_M, 4), "d1": fx["arm"], "m2": round(BUCKET_M + k["water"], 4),
            "d2": k["hook"], "beam": BEAM_M, "friction": PIVOT_F, "start": -levers.STOP, "g": G}


def scoop_at(a, th):
    """The ball's centre in the scoop at the left end (d = a) when the beam is at angle th."""
    return (PIVOT[0] - a * math.cos(th), PIVOT[1] + a * math.sin(th) + SCOOP_LIFT)


def hoist_cost(t_up, v):
    return HOIST_T_COST * t_up + HOIST_V_COST * v


def run_mill_hoist(k, fx, thresholds=None):
    p = hoist_params(k, fx)
    res = levers.run(p)
    vz = res["viz"]
    a = fx["arm"]
    hit_top = vz["hit"] == 1
    v = vz["v1"] if hit_top else 0.0
    t_up = vz["t_hit"] if hit_top else None
    ok = hit_top and t_up <= SLOW and v <= GENTLE + 1e-9
    frames = []
    for f in kit.thin(res["frames"], 250):
        x, y = scoop_at(a, f["theta"])
        frames.append({"t": f["t"], "x": round(x, 5), "y": round(y, 5), "th": f["theta"]})
    th_top = math.radians(levers.STOP)
    if hit_top:
        frames = [f for f in frames if f["t"] <= t_up + 1e-9]
        x0, y0 = scoop_at(a, th_top)
        if v <= GENTLE + 1e-9:                               # it tips onto the shelf and rolls into the hopper
            pts = [(x0, y0), (SHELF[1] - 0.04, SHELF[2] + BALL_R), (SHELF[0] + 0.02, SHELF[2] + BALL_R),
                   (HOPPER[0], SHELF[2] - 0.06)]
            tw, _ = kit.tween(pts, 0.0, 0.8)
            frames += [{"t": round(t_up + 0.25 + f["t"], 4), "x": f["x"], "y": f["y"], "th": round(th_top, 6)}
                       for f in tw]
        else:                                                # flung out of the scoop
            om = vz["omega_hit"]
            vx, vy = a * math.sin(th_top) * om, a * math.cos(th_top) * om
            fl = tracer.trace(x0, y0, vx, vy, BALL["mass"], BALL_R, BALL_K, dt=5e-4, tmax=3.0,
                              zones=[("floor", lambda x_, y_, vx_, vy_: y_ < BALL_R and vy_ < 0)])
            frames += [{"t": round(t_up + f["t"], 4), "x": f["x"], "y": f["y"], "th": round(th_top, 6)}
                       for f in fl["frames"][1:]]
    if not vz["moves"]:
        reason = "The hoist doesn't budge: bucket %.3f kg·m < scoop %.3f kg·m (plus the pivot's friction)." % (
            p["m2"] * p["d2"], p["m1"] * p["d1"])
    elif not hit_top or t_up > SLOW:
        reason = "Too slow - it's still creeping up after %.0f s. Just a little more water." % SLOW
    elif v > GENTLE:
        reason = "Flung! The scoop hit the top stop at %.2f m/s and the light wooden ball flew out." % v
    else:
        reason = "Onto the millstone shelf: the scoop arrived at %.2f m/s after %.1f s." % (v, t_up)
    cost = hoist_cost(t_up, v) if ok else None
    cost_min = (thresholds or {}).get("cost_min", cost)
    return {
        "ok": ok, "reason": reason, "metric": round(v, 3), "unit": "m/s", "predicted": round(v, 3),
        "mastery": bool(ok and v <= FEATHER + 1e-9),
        "score": kit.score(ok, kit.SCORE_MAX - (cost - cost_min)) if ok else 0,
        "score_parts": [{"label": "time to the top", "value": "%.1f s" % t_up, "note": "%.1f x 200" % t_up},
                        {"label": "arrival speed", "value": "%.2f m/s" % v, "note": "%.2f x 500" % v},
                        {"label": "cost", "value": "%d" % round(cost),
                         "note": "1000 minus how much more it cost than the best lift for your hoist"}] if ok else [],
        "frames": kit.world(frames, (0.0, 0.0), extra=("th",)),
        "viz": {"moves": vz["moves"], "t_up": t_up, "speed": round(v, 4), "balance_water": round(
            max(0.0, p["m1"] * p["d1"] / p["d2"] - BUCKET_M), 4), "inertia": vz["inertia"]},
        "formula": [{"expr": "m1 * d1 = m2 * d2",
                     "values": {"scoop + ball": "%.2f kg x %.2f m = %.3f kg·m" % (p["m1"], p["d1"], p["m1"] * p["d1"]),
                                "bucket": "%.2f kg x %.2f m = %.3f kg·m" % (p["m2"], p["d2"], p["m2"] * p["d2"])}},
                    {"expr": "alpha = tau_net / I",
                     "values": {"I": round(vz["inertia"], 3), "arrival": "%.2f m/s" % v}}],
        "lab": [{"title": "Levers & Moments: this hoist (scoop + ball on the left, the bucket on the right)",
                 "route": "#/levers?" + kit.query([(key, p[key]) for key in ("m1", "d1", "m2", "d2", "beam",
                                                                           "friction", "start", "g")])}],
    }


# ================================================================ the station table

STATIONS = [
    {"id": "3.1", "hall": "mill", "title": "Crow's Well", "scene": "crows_well", "par": 2, "learn": "buoyancy",
     "run": run_crows_well,
     "intro": "The grain chute drops the wooden ball into a narrow well (10 cm across) with a little water in it. "
              "It floats - but far below the paddle wheel that sweeps it out. The pump is broken; three piles of "
              "things lie around the mill.",
     "goal": "Drop things in until the ball floats at the paddles: its centre at 45 ± 2.5 cm.",
     "hook": "Only a floater rides the water up. Rubber and steel would sit on the bottom.",
     "knobs": [choice("item", "Drop in", DROP_ITEMS, "block"), integer("count", "How many", 0, 40, 0)],
     "facts": [fact("depth", "Water in the well at first", 20.0, "cm", vary=(18.0, 22.0)),
               fact("well_d", "Well diameter", 10.0, "cm"),
               fact("paddle", "The paddles sweep the ball's centre at", 45.0, "cm"),
               fact("ball", "Ball: wood 597 kg/m³, 8 cm", 0.16, "kg"),
               fact("under", "The ball floats this much under (by volume)", 60.0, "%"),
               fact("stone_v", "A river stone", 200.0, "cm³"),
               fact("bearing_v", "A steel bearing", ITEM["bearing"]["V"], "cm³"),
               fact("block_v", "A pine block (510 kg/m³)", 64.0, "cm³")],
     "predict": {"label": "How high will the ball's centre float?", "kind": "number", "unit": "cm", "tol": 0.03,
                 "abs": 1.0},
     "mastery": {"id": "aesop", "text": "Aesop's Crow: use the fewest drops that work ({fewest})."},
     "score_rule": "Score: aim and effort. Each cm the ball floats off the paddles' 45 cm costs 150, each thing "
                   "you drop in costs 10. The best way for your well scores 1000.",
     "formulas": ["dh = V_pushed / A", "V_sub / V = rho_obj / rho_fluid"],
     "hints": ["Stones and bearings sink and push aside their WHOLE volume. A floating block only pushes aside its "
               "own weight of water. Which raises the well more?",
               "The water rises by V / A with A = π × 5² = 78.5 cm². The ball floats 60 % under (160 cm³) and its "
               "centre sits 0.6 cm below the surface, so the water must reach about 45.6 cm: (45.6 − {depth}) × "
               "78.5 − 160 cm³ of sinkers."],
     "solutions": [{"item": "stone", "count": 9}, {"item": "bearing", "count": 28}],
     "mastery_solutions": [{"item": "stone", "count": 9}],
     "wrong": [({"item": "block", "count": 40}, "floats at"), ({"item": "stone", "count": 12}, "Too high"),
               ({"item": "bearing", "count": 9}, "floats at"), ({"item": "stone", "count": 40}, "overflows")]},
    {"id": "3.2", "hall": "mill", "title": "Fan Jump", "scene": "fan_jump", "par": 3, "learn": "motion",
     "run": run_fan_jump,
     "intro": "The paddle chute ends in a ski-jump lip: the ball leaves at 2.0 m/s, 10° up, 2.5 m above a hay cart "
              "on the far side of the mill race. On its own it splashes into the race. The mill's big winnowing "
              "fan can blow from behind.",
     "goal": "Set the fan so the ball lands in the hay cart.",
     "hook": "The wooden ball has the most drag per kilogram of the three balls: the same wind would move the steel "
             "ball only a few centimetres.",
     "knobs": [num("wind", "Fan wind", 0.0, 20.0, 0.0, "m/s", 0.5)],
     "facts": [fact("cart", "Hay cart (its middle) from the lip", 1.975, "m", vary=(1.90, 2.05)),
               fact("cart_len", "Hay cart length", 2 * CART_HALF, "m"),
               fact("drop", "From the lip down to the cart", FJ_DROP, "m"),
               fact("u0", "Off the lip", FJ_U0, "m/s"),
               fact("angle", "Lip angle", FJ_ANGLE, "°"),
               fact("mass", "Ball mass", BALL["mass"], "kg"),
               fact("d", "Ball diameter", BALL["d"], "m"),
               fact("cd", "Drag coefficient C_d", BALL["cd"], ""),
               fact("rho_air", "Air density", tracer.RHO_AIR, "kg/m³")],
     "predict": {"label": "How far from the lip will it land?", "kind": "number", "unit": "m", "tol": 0.02,
                 "abs": 0.03},
     "mastery": {"id": "breeze", "text": "Gentle Breeze: the weakest wind that works - {breeze} m/s or less."},
     "score_rule": "Score: up to 700 for landing in the middle of the cart, plus up to 300 for saving the fan's "
                   "power (it grows with the wind cubed). The best for your cart scores 1000.",
     "formulas": ["F = 1/2 * rho * C_d * A * (w - v)^2", "dx = 1/2 * (F/m) * t^2"],
     "hints": ["With no fan it lands about 1.47 m out - short. The fan's wind pushes through drag: the faster the "
               "air rushes past the ball, the harder it pushes.",
               "Drag F = ½·1.225·0.47·(π·0.04²)·(w − v)². It's in the air about 0.75 s, so Δx ≈ ½·(F/0.16)·0.75² must "
               "make up {cart} − 1.47 m. The ball speeds up with the wind, so F shrinks: estimate, then let the "
               "simulation decide."],
     "solutions": [{"wind": 15.5}, {"wind": 16.5}], "mastery_solutions": [{"wind": 15.0}],
     "wrong": [({"wind": 0.0}, "Splash"), ({"wind": 20.0}, "hedge"), ({"wind": 10.0}, "Splash")]},
    {"id": "3.3", "hall": "mill", "title": "Light Gate", "scene": "light_gate", "par": 2, "learn": "optics",
     "run": run_light_gate,
     "intro": "The path crosses the old Foundry contact plates - and the wooden ball rolls over them without a "
              "spark: wood doesn't conduct. So the drawbridge ahead listens to a light gate instead: a lamp shines "
              "down onto a 1 cm photocell in the path. The gate is armed when the cell gets at least half the "
              "lamp's light; then the ball breaks the beam and the bridge comes down.",
     "goal": "Slide the lens along the beam so the photocell gets at least half the light.",
     "hook": "The ball is an insulator - that's why this station exists: the contact switch can't see it.",
     "knobs": [num("d_o", "Lens distance from the lamp", 5.0, 95.0, 50.0, "cm", 0.5)],
     "facts": [fact("bench", "Lamp to photocell", 100.0, "cm", vary=(95.0, 105.0)),
               fact("f", "Lens focal length (crown glass, R = 20 cm)", round(LG_F, 1), "cm"),
               fact("lamp", "The lamp's glowing window", LG_LAMP, "cm"),
               fact("cell", "Photocell", optics.CELL, "cm"),
               fact("lens_d", "Lens diameter", 2 * optics.APERTURE, "cm"),
               fact("arm", "The gate arms at", 100 * LG_ARM, "% of the light")],
     "predict": {"label": "What share of the light will reach the cell?", "kind": "number", "unit": "%",
                 "tol": 0.05, "abs": 5.0},
     "mastery": {"id": "sharp", "text": "Sharp Eye: put the cell within 0.5 cm of the sharp image."},
     "score_rule": "Score: focus. 1000 for the sharpest image your bench allows on the slider; every mm the sharp "
                   "image misses the cell costs 40.",
     "formulas": ["1/f = 1/d_o + 1/d_i", "m = -d_i / d_o = h_i / h_o", "blur = D * |s - d_i| / d_i"],
     "hints": ["On a fixed bench there are TWO places where the image is sharp. Both are in focus - but only one "
               "makes an image small enough for a 1 cm cell.",
               "d_o + d_i = {bench} cm and 1/d_o + 1/d_i = 1/19.2. The image is 2 cm × d_i/d_o wide: pick the sharp "
               "position with the lens far from the lamp (d_o big, d_i small)."],
     "solutions": [{"d_o": 74.0}, {"d_o": 73.5}], "mastery_solutions": [{"d_o": 74.0}],
     "wrong": [({"d_o": 26.0}, "IS in focus"), ({"d_o": 50.0}, "in front of"), ({"d_o": 19.0}, "focal length")]},
    {"id": "3.4", "hall": "mill", "title": "Mill Hoist", "scene": "mill_hoist", "par": 3, "learn": "levers",
     "run": run_mill_hoist,
     "intro": "The ball rolls off the drawbridge into a scoop on the long arm of a wooden beam. On the other arm "
              "hangs a bucket you fill from the mill race and hook at any distance. Too little water and the hoist "
              "doesn't move; too much and it slams into the top stop and flings the light ball away.",
     "goal": "Lift the scoop to the millstone shelf, arriving at 1.0 m/s or slower.",
     "hook": "The wooden ball is so light that extra turning effect throws it - the steel ball would have just sat "
             "there.",
     "knobs": [num("hook", "Bucket hook distance b", 0.20, 1.00, 0.50, "m", 0.05),
               num("water", "Water in the bucket", 0.0, 2.00, 0.0, "L", 0.01)],
     "facts": [fact("arm", "Scoop arm a", 1.0, "m", vary=(0.9, 1.1)),
               fact("scoop", "Ball + scoop", round(BALL["mass"] + SCOOP_M, 2), "kg"),
               fact("bucket", "Empty bucket", BUCKET_M, "kg"),
               fact("beam", "Beam (2.2 m, pivot in the middle)", BEAM_M, "kg"),
               fact("friction", "Pivot friction", PIVOT_F, "N·m"),
               fact("stop", "It swings between", levers.STOP, "± °"),
               fact("gentle", "The ball stays in the scoop up to", GENTLE, "m/s"),
               fact("litre", "1 L of water", 1.0, "kg")],
     "predict": {"label": "How fast will the scoop arrive at the top?", "kind": "number", "unit": "m/s",
                 "tol": 0.1, "abs": 0.05},
     "mastery": {"id": "feather", "text": "Feather Touch: the scoop arrives at 0.5 m/s or slower."},
     "score_rule": "Score: quick AND gentle. Each second to the top costs 200, each m/s of arrival speed costs 500. "
                   "The best lift for your hoist scores 1000.",
     "formulas": ["m1 * d1 = m2 * d2", "alpha = tau_net / I"],
     "hints": ["First make it balance: the bucket's mass × its distance must match the scoop's 0.26 kg × {arm} m. "
               "Then add just a little more.",
               "Balance: (0.20 kg + water) × b = 0.26 × {arm} - plus a tiny bit for the pivot's friction. Then about "
               "10-25 % more water: too much and the beam slams the light ball out."],
     "solutions": [{"hook": 0.5, "water": 0.38}, {"hook": 1.0, "water": 0.1}],
     "mastery_solutions": [{"hook": 0.5, "water": 0.35}],
     "wrong": [({"hook": 0.5, "water": 0.2}, "budge"), ({"hook": 1.0, "water": 2.0}, "Flung")]},
]
BY_ID = {s["id"]: s for s in STATIONS}

HALL = {"id": "mill", "title": "Millbrook Mill", "ball": "wood", "status": "ready",
        "blurb": "An old water mill: a narrow well, a winnowing fan, a light gate and a counterweight hoist. Get the "
                 "wooden ball from the grain chute to the millstone hopper.",
        "stations": STATIONS, "layout": LAYOUT}

VIA = {"3.1": lambda last, nxt: [(LIP[0] - 0.30, LIP[1] + 0.08)],
       "3.2": lambda last, nxt: [(last["x"] + 0.16, PATH_Y + 0.32), (PATH_X0 - 0.05, PATH_Y + BALL_R)],
       "3.3": lambda last, nxt: [(8.40, PATH_Y + BALL_R)]}                # the fixed deck, then into the scoop
KIT = kit.Hall(HALL, STATIONS, DATA, VIA, 1.2)
table, variant_data, thresholds = KIT.table, KIT.variant_data, KIT.thresholds
mastery_text, hint_text, run_station, run_machine = KIT.mastery_text, KIT.hint_text, KIT.run_station, KIT.run_machine
