"""Hall 2 - The Foundry (steel ball). GDD section 6.2.

Four stations, each a thin adapter around a physlab engine (and each with a
lab link that reproduces it):

    2.1 Hot Ring        topics/heat.py (+ thermal expansion)      -> #/heat
    2.2 Trapdoor Latch  topics/circuitlab.py (nodal solver)       -> #/circuits (the same loop)
    2.3 Hydraulic Gate  topics/pressure.py (a weight pushes)      -> #/pressure?push=weight
    2.4 Magnet Swing    topics/pendulum.py + tracer (the flight)  -> #/pendulum

The steel ball falls floor by floor: it hangs in a ring that is 60 um too
small, drops onto two copper plates (it IS the switch of the trapdoor's
latch), rides a hydraulic piston down while the oil lifts a gate, and a
crane's electromagnet swings it out over the casting pit into the ladle.

Stations work in local coordinates; LAYOUT places them in the hall. Runs
return world frames {t, x, y, + station fields the scene draws: the ring's
temperature T, the trapdoor's opening, the pistons, the cable angle} and
optional time-lapse zones [t0, t1, speed] for slow physics (heating).
"""

import math
import os

from .. import BOUNCE_BALLS
from ..sandbox import BY_ID as SB
from ..topics import circuitlab, heat, pendulum, pressure, tracer
from . import kit
from .common import choice, fact, num

G = 9.81
BALL = dict(next(b for b in BOUNCE_BALLS if b["id"] == "steel"))      # the sandbox's steel ball
BALL_R = BALL["d"] / 2.0
BALL_K = tracer.drag_constant(BALL["d"], BALL["cd"])                  # 5.7e-4 kg/m
WEIGHT = BALL["mass"] * G                                             # 5.0 N
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "foundry.json")

# ---------------------------------------------------------------- the hall layout (world metres)
# (matches docs/game/img/level2_foundry.png)
RING = (1.0, 6.0)               # 2.1: the ring's plane, the ball resting in it
CHUTE_Y = 5.1                   # 2.1: the ball falls through the ring down to here
TRAP = (2.6, 4.6)               # 2.2: top of the copper plates on the trapdoor
CYL_TOP = 4.05                  # 2.3: the small piston's top at the start (stroke goes down)
SMALL_X, GATE_X = 2.6, 3.9      # 2.3: the small cylinder (the ball's shaft); the gate (the big cylinder sits on it)
TUNNEL_Y = 3.75                 # 2.3: the tunnel floor = the small piston's top at the end of the stroke
TUNNEL_END = 4.35               # 2.3: x where the ball leaves the tunnel
PICKUP = (5.3, 2.62)            # the crane's magnet picks the ball up here
SWING = (6.2, 2.5)              # 2.4: bottom of the swing (the magnet lets go here)
DROP = 1.2                      # 2.4: from the bottom of the swing down to the ladle's rim
LADLE_HALF = 0.10               # 2.4: half the ladle's mouth
GATE_HALF = 0.015               # 2.3: half the gate plate's thickness

# What the scene draws (www/js/hall_foundry.js): decks are slabs (top y), the
# rest is each station's furniture. Cylinders are drawn `vis` metres wide per
# cm of diameter (4x real size) so a 2 cm piston is visible next to the ball.
LAYOUT = {
    "bounds": {"x0": -0.4, "x1": 8.6, "y0": -0.2, "y1": 9.2},          # (room above for the HUD)
    "decks": [{"x0": -0.4, "x1": 2.2, "y": 5.75}, {"x0": 1.55, "x1": 2.04, "y": 4.57},
              {"x0": 2.84, "x1": 3.4, "y": 4.57}, {"x0": 4.4, "x1": 6.3, "y": 2.45}],
    "A": [0.35, 6.62], "cart": [0.35, 6.03],
    "stations": {
        "2.1": {"ring": list(RING), "chute_y": CHUTE_Y, "floor": 5.75, "kettle": [1.62, 6.5],
                "gauge": [1.95, 6.05, 6.65], "water_max": 0.5,
                "view": {"x0": 0.1, "x1": 2.2, "y0": 5.0, "y1": 7.2}},
        "2.2": {"trap": list(TRAP), "plates": [2.38, 2.82], "door_y": 4.57, "hinges": [2.36, 2.84],
                "coil": [2.15, 4.505], "panel": [0.2, 3.6, 1.95, 4.3], "ramp": [[1.0, CHUTE_Y], [2.3, TRAP[1] + 0.1]],
                "view": {"x0": 0.1, "x1": 3.4, "y0": 3.5, "y1": 5.3}},
        "2.3": {"small_x": SMALL_X, "gate_x": GATE_X, "top": CYL_TOP, "floor": TUNNEL_Y, "roof": 3.92,
                "stroke": 0.30, "d1": 2.0, "vis": 0.04, "big_y0": 3.95, "big_h": 0.30, "gate_half": GATE_HALF,
                "gate_h": 0.2, "tunnel_end": TUNNEL_END, "need": 0.06,
                "view": {"x0": 2.0, "x1": 4.7, "y0": 3.2, "y1": 4.7}},
        "2.4": {"swing": list(SWING), "pickup": list(PICKUP), "drop": DROP, "ladle_half": LADLE_HALF,
                "girder_y": 4.75, "chute": [[TUNNEL_END, TUNNEL_Y], [PICKUP[0], PICKUP[1] - BALL_R]],
                "view": {"x0": 4.1, "x1": 8.4, "y0": 0.2, "y1": 5.3}},
    },
    "ball": {"r": BALL_R, "color": BALL["color"]},
}

# ---------------------------------------------------------------- scores (1000 = the best possible for the variant)
WATER_COST = 4000.0             # 2.1: points per kg of hot water (40 per 10 g)
WAIT_COST = 40.0                # 2.1: points per second until the ring lets go
POWER_COST = 400.0              # 2.2: points per watt of battery power above the least that works (40 per 0.1 W)
RIDE_COST = 200.0               # 2.3: points per second slower than the fastest ride (20 per 0.1 s)
AIM_POINTS, SAFE_POINTS = 700, 300   # 2.4: aim into the ladle, + how much grip the magnet had to spare


# ================================================================ 2.1 Hot Ring
ALPHA = {"aluminum": 23.1e-6, "steel": 12.0e-6}
BALL_D_MM = 50.00
RING_MASS = 0.30                # kg of aluminium
KETTLE = 95.0
ROOM = 20.0
CUP_LOSS = 0.1                  # W/K: the ring's cup is foam-insulated
SHIFT = 120.0                   # s: the ring must let go within the shift
SEAT = 0.012                    # m: the ball's centre sits this far above the ring's plane (it rests in the hole)
HEAT_SECONDS = 3.0              # the heating is shown as a time-lapse lasting about this long
TARGETS = [{"id": "ring", "label": "the ring", "icon": "⭕", "desc": "pour the hot water into the ring's cup"},
           {"id": "ball", "label": "the ball", "icon": "⚪", "desc": "pour it over the steel ball"},
           {"id": "both", "label": "both", "icon": "♨️", "desc": "dunk the ring and the ball together"}]


def heat_params(k):
    """What sits in the hot water, as the heat lab's block B."""
    if k["target"] == "ring":
        mat, mass = "aluminum", RING_MASS
    elif k["target"] == "ball":
        mat, mass = "iron", BALL["mass"]                            # steel ~ iron: c = 450
    else:                                                            # both: one block, their heat capacities added
        mat, mass = "aluminum", round(RING_MASS + BALL["mass"] * 450.0 / 900.0, 4)
    return {"material_a": "water", "mass_a": k["water"], "temp_a": KETTLE, "material_b": mat, "mass_b": mass,
            "temp_b": ROOM, "ambient": ROOM, "loss": CUP_LOSS}


def ring_needs(gap_um):
    """Ring temperature that opens the gap, ring heated alone: gap = bore alpha dT."""
    return ROOM + gap_um / 1000.0 / ((BALL_D_MM - gap_um / 1000.0) * ALPHA["aluminum"])


def heat_cost(water, t_drop):
    return WATER_COST * water + WAIT_COST * t_drop


def run_hot_ring(k, fx, thresholds=None):
    gap_um = fx["gap_um"]
    bore0 = BALL_D_MM - gap_um / 1000.0
    res = heat.run(heat_params(k)) if k["water"] > 0 else None
    on_ring, on_ball = k["target"] in ("ring", "both"), k["target"] in ("ball", "both")

    def state(f):
        tb = f["temp_b"]
        tr, tball = (tb if on_ring else ROOM), (tb if on_ball else ROOM)
        gap = bore0 * (1 + ALPHA["aluminum"] * (tr - ROOM)) - BALL_D_MM * (1 + ALPHA["steel"] * (tball - ROOM))
        return tr, tball, gap
    seq = [f for f in res["frames"] if f["t"] <= SHIFT] if res else [{"t": 0.0, "temp_b": ROOM}]
    if res and seq[-1]["t"] < SHIFT:
        seq.append(dict(seq[-1], t=SHIFT))                           # it has settled: hold the last state
    # the heated part's temperature over the whole shift (it keeps warming after the ball has gone: that's the
    # `metric` - the heat balance's answer, a little lower because the cup leaks); the frames stop at the drop
    t_drop, peak, best_gap, worst_gap, frames, prev = None, ROOM, None, 0.0, [], None
    for f in seq:
        tr, tball, gap = state(f)
        peak = max(peak, tr if on_ring else tball)
        best_gap = gap if best_gap is None else max(best_gap, gap)
        worst_gap = min(worst_gap, gap)
        if t_drop is not None:
            continue
        if gap >= 0.0:
            if prev is None:
                t_drop, tr_d, tb_d = f["t"], tr, tball
            else:                                                     # interpolate the moment it opens
                t0, g0, tr0, tb0 = prev
                u = (-g0) / (gap - g0) if gap != g0 else 1.0
                t_drop, tr_d, tb_d = t0 + (f["t"] - t0) * u, tr0 + (tr - tr0) * u, tb0 + (tball - tb0) * u
            frames.append({"t": round(t_drop, 3), "x": 0.0, "y": SEAT, "T": round(tr_d, 2), "Tb": round(tb_d, 2)})
            continue
        frames.append({"t": round(f["t"], 3), "x": 0.0, "y": SEAT, "T": round(tr, 2), "Tb": round(tball, 2)})
        prev = (f["t"], gap, tr, tball)
    ok = t_drop is not None
    zones, frames = [], kit.thin(frames, 200)                       # (the heating; thin() keeps the moment it opens)
    if ok:                                      # it drops through the ring and down the tube
        out = tracer.trace(0.0, SEAT, 0.0, 0.0, BALL["mass"], BALL_R, BALL_K,
                           zones=[("down", lambda x, y, vx, vy: y <= CHUTE_Y - RING[1])], tmax=2.0)
        last = frames[-1]
        frames += [{"t": round(t_drop + f["t"], 3), "x": 0.0, "y": f["y"], "T": last["T"], "Tb": last["Tb"]}
                   for f in out["frames"][1:]]
        zones.append([0.0, round(t_drop, 3), max(1.0, t_drop / HEAT_SECONDS)])
    else:
        zones.append([0.0, SHIFT, SHIFT / (HEAT_SECONDS * 2)])
    need = ring_needs(gap_um)
    if ok:
        reason = "The ring opened after %.1f s: at %.1f °C the aluminium grew past the %.0f µm gap." % (
            t_drop, tr_d, gap_um)
    elif k["water"] <= 0:
        reason = "No hot water - nothing changes."
    elif k["target"] == "ball":
        reason = "You heated the BALL: it got bigger and is stuck even harder (%.0f µm too big now)." % (-worst_gap * 1000)
    elif k["target"] == "both":
        reason = ("Both grew: the gap only opens by the DIFFERENCE in expansion - that needs %.0f °C, hotter than "
                  "boiling water." % (ROOM + gap_um / 1000.0 / (bore0 * ALPHA["aluminum"] - BALL_D_MM * ALPHA["steel"])))
    else:
        reason = "The ring only got to %.0f °C - it needs %.0f °C to open %.0f µm. More hot water!" % (peak, need, gap_um)
    cost = heat_cost(k["water"], t_drop) if ok else None
    cost_min = (thresholds or {}).get("cost_min", cost)
    hp = heat_params(k)
    return {
        "ok": ok, "reason": reason, "metric": round(peak, 1), "unit": "°C", "predicted": round(peak, 1),
        "mastery": bool(ok and k["target"] == "ring" and k["water"] <= (thresholds or {}).get("thrifty", -1) + 1e-9),
        "score": kit.score(ok, kit.SCORE_MAX - (cost - cost_min)) if ok else 0,
        "score_parts": [{"label": "hot water", "value": "%.2f kg" % k["water"],
                         "note": "%.2f x 4000 = %d" % (k["water"], WATER_COST * k["water"])},
                        {"label": "waiting", "value": "%.1f s" % t_drop,
                         "note": "%.1f x 40 = %d" % (t_drop, round(WAIT_COST * t_drop))},
                        {"label": "cost", "value": "%d" % round(cost),
                         "note": "1000 minus how much more it cost than the cheapest way to open the ring"}]
        if ok else [],
        "frames": kit.world(frames, RING, extra=("T", "Tb")),
        "timelapse": zones,
        "viz": {"t_drop": round(t_drop, 2) if ok else None, "T_peak": round(peak, 1), "T_need": round(need, 1),
                "T_drop": round(tr_d, 2) if ok else None,
                "short_um": round(max(0.0, -best_gap) * 1000, 1),          # the closest it came to opening
                "worst_um": round(-worst_gap * 1000, 1)},                   # the tightest it got
        "formula": [{"expr": "T_eq = (m_w c_w T_w + m_r c_r T_r) / (m_w c_w + m_r c_r)",
                     "values": {"m_w": k["water"], "c_w": 4186, "T_w": KETTLE, "m_r": hp["mass_b"],
                                "c_r": 900 if hp["material_b"] == "aluminum" else 450, "T_r": ROOM,
                                "reached": round(peak, 1)}},
                    {"expr": "dL = alpha * L * dT",
                     "values": {"alpha (aluminium)": "23.1e-6", "L (hole)": "%.2f mm" % bore0,
                                "dT needed": "%.1f K" % (need - ROOM), "dL needed": "%.0f um" % gap_um}}],
        "lab": [{"title": "Heat Transfer: this water and this %s (see 'grows')" % (
                    {"ring": "ring", "ball": "ball", "both": "ring + ball"}[k["target"]]),
                 "route": "#/heat?" + kit.query(sorted(hp.items()))}] if k["water"] > 0 else [],
    }


# ================================================================ 2.2 Trapdoor Latch
R_BALL, R_FUSE, FUSE_A = 0.05, 0.05, 1.0
COIL_HOT_W = 1.5
BATTERIES = [dict(SB["parts"][b], desc="%g V, internal %g Ω" % (SB["parts"][b]["emf"], SB["parts"][b]["r_int"]))
             for b in ("aa", "lantern", "nine_v", "car_battery")]


def loop_current(battery_id, r_dial, coil_ohm):
    """The latch loop solved by physlab's circuit lab (nodal analysis):
    battery -> resistor dial -> 1 A fuse -> latch coil -> the steel ball -> wire."""
    bat = SB["parts"][battery_id]
    parts = [{"kind": "battery", "a": (0, 1), "b": (0, 0), "emf": bat["emf"], "r_int": bat["r_int"]},
             {"kind": "resistor", "a": (0, 0), "b": (1, 0), "R": max(r_dial, 1e-4)},
             {"kind": "resistor", "a": (1, 0), "b": (2, 0), "R": R_FUSE},
             {"kind": "resistor", "a": (2, 0), "b": (2, 1), "R": coil_ohm},
             {"kind": "resistor", "a": (2, 1), "b": (1, 1), "R": R_BALL},
             {"kind": "wire", "a": (1, 1), "b": (0, 1)}]
    return abs(circuitlab.solve(parts, 3, 2)["parts"][3]["current"])


DOOR_LEN = 0.24                 # m: each leaf of the trapdoor (two leaves, hinged at the outer edges)


def door_open(t):
    """How far the released trapdoor has swung (0 shut .. 1 hanging down) after
    t seconds: each leaf is a uniform board on a hinge, theta'' = 3g/(2l)
    cos(theta). The leaves meet under the ball and their free ends start
    down at 1.5 g - faster than the ball - so the ball falls freely."""
    th, om, dt, tt = 0.0, 0.0, 0.001, 0.0
    while tt < t - 1e-12 and th < math.pi / 2:
        om += 1.5 * G / DOOR_LEN * math.cos(th) * dt
        th += om * dt
        tt += dt
    return min(1.0, th / (math.pi / 2))


def run_trapdoor(k, fx, thresholds=None):
    bat = SB["parts"][k["battery"]]
    i = loop_current(k["battery"], k["R"], fx["coil_ohm"])
    p_coil, p_bat = i * i * fx["coil_ohm"], bat["emf"] * i
    blown, weak = i > FUSE_A, i < fx["pull_in"]
    ok = not blown and not weak
    frames = [{"t": 0.0, "x": 0.0, "y": BALL_R, "door": 0.0, "I": round(i, 4)}]     # current flows as it lands
    if ok:                                   # the latch pulls (faster with more current), then the door falls away
        t_pull = 0.15 + 0.25 * (fx["pull_in"] / i) ** 2                              # and the ball drops with it
        out = tracer.trace(0.0, BALL_R, 0.0, 0.0, BALL["mass"], BALL_R, BALL_K,
                           zones=[("in", lambda x, y, vx, vy: y <= CYL_TOP - TRAP[1] + BALL_R)], tmax=2.0)
        frames += [{"t": round(t_pull + f["t"], 3), "x": 0.0, "y": f["y"], "door": round(door_open(f["t"]), 3),
                    "I": round(i, 4)} for f in out["frames"]]
        reason = "%.2f A - the latch pulls and the trapdoor drops open." % i
    else:
        if blown:
            frames.append({"t": 0.05, "x": 0.0, "y": BALL_R, "door": 0.0, "I": 0.0})
        frames.append({"t": 1.5, "x": 0.0, "y": BALL_R, "door": 0.0, "I": 0.0 if blown else round(i, 4)})
        reason = ("%.2f A - POP! The 1 A fuse blew." % i) if blown else (
            "%.2f A - too weak to pull the latch (it needs %.2f A)." % (i, fx["pull_in"]))
    p_min = (thresholds or {}).get("p_min", p_bat)
    return {
        "ok": ok, "reason": reason, "metric": round(i, 3), "unit": "A", "predicted": round(i, 3),
        "mastery": bool(ok and p_coil <= COIL_HOT_W + 1e-9),
        "score": kit.score(ok, kit.SCORE_MAX - POWER_COST * (p_bat - p_min)) if ok else 0,
        "score_parts": [{"label": "battery power", "value": "%.2f W" % p_bat,
                         "note": "P = V x I = %g x %.3f; -40 for every 0.1 W above the least that works" % (
                             bat["emf"], i)}] if ok else [],
        "frames": kit.world(frames, TRAP, extra=("door", "I")),
        "viz": {"I": round(i, 4), "blown": blown, "p_coil": round(p_coil, 3), "p_battery": round(p_bat, 3)},
        "formula": [{"expr": "I = V / (R + r + R_coil + R_fuse + R_ball)",
                     "values": {"V": bat["emf"], "R": k["R"], "r": bat["r_int"], "R_coil": fx["coil_ohm"],
                                "R_fuse + R_ball": R_FUSE + R_BALL, "I": round(i, 3)}},
                    {"expr": "P = I^2 * R_coil", "values": {"I": round(i, 3), "P_coil": round(p_coil, 2)}},
                    {"expr": "P = V * I", "values": {"P_battery": round(p_bat, 2)}}],
        "lab": [{"title": "Electric Circuits: the same loop (its lamp stands in for the latch coil)",
                 "route": "#/circuits?" + kit.query([("voltage", bat["emf"]), ("lamps", 1),
                                                    ("lamp_r", fx["coil_ohm"]),
                                                    ("internal_r", round(bat["r_int"] + R_FUSE + R_BALL +
                                                                         circuitlab.R_WIRE, 4)),
                                                    ("resistor", k["R"]), ("closed", 1)])}],
    }


# ================================================================ 2.3 Hydraulic Gate
HG = {"d1": 2.0, "stroke": 30.0, "piston": 0.10, "need": 0.06}
HIGH_GATE = 0.075               # m: mastery - lift the gate at least this high


def gate_params(k, fx):
    return {"force": round(WEIGHT, 4), "d1": HG["d1"], "d2": k["d2"], "mass": round(fx["gate_kg"] + HG["piston"], 4),
            "stroke": HG["stroke"], "fluid": "oil", "push": "weight"}


def run_hydraulic_gate(k, fx, thresholds=None):
    p = gate_params(k, fx)
    res = pressure.run(p)
    fr = res["frames"]
    last = fr[-1]
    reached = res["viz"]["reached"]
    lift = HG["stroke"] / 100.0 * res["viz"]["a1"] / res["viz"]["a2"]          # the gate's rise at the bottom
    top = CYL_TOP - TRAP[1]                                                       # local: relative to station origin
    frames = [{"t": f["t"], "x": 0.0, "y": round(top + BALL_R - f["x1"], 5), "x1": f["x1"], "x2": f["x2"]}
              for f in kit.thin(fr, 300)]
    clear = lift >= HG["need"]
    ok = reached and clear
    t_down = last["t"] if reached else None
    if reached:                              # roll along the tunnel floor to the gate (and under it, if it's up)
        stop = (TUNNEL_END - SMALL_X) if clear else (GATE_X - GATE_HALF - SMALL_X - BALL_R - 0.005)
        n = 12
        for i in range(1, n + 1):
            frames.append({"t": round(t_down + 0.08 * i, 4), "x": round(stop * i / n, 4),
                           "y": round(top + BALL_R - HG["stroke"] / 100.0, 5), "x1": last["x1"], "x2": last["x2"]})
    if not res["viz"]["lifted"]:
        reason = "Nothing moves: the ball's %.1f N can't hold up the gate through a %.1f cm piston." % (WEIGHT, k["d2"])
    elif not reached:
        reason = ("Stalled %.0f cm down: the oil column's own weight pushes back as hard as the ball." %
                  (100 * last["x1"]))
    elif not clear:
        reason = ("The ball reached the bottom, but the gate only rose %.1f cm - it needs %.0f cm to let the ball "
                  "through." % (100 * lift, 100 * HG["need"]))
    else:
        reason = "The gate rose %.1f cm and the ball rolled out after %.1f s." % (100 * lift, t_down)
    t_best = (thresholds or {}).get("t_best", t_down)
    return {
        "ok": ok, "reason": reason, "metric": round(100 * lift, 2) if reached else round(100 * last["x2"], 2),
        "unit": "cm", "predicted": round(100 * lift, 2),
        "mastery": bool(ok and lift >= HIGH_GATE - 1e-9),
        "score": kit.score(ok, kit.SCORE_MAX - RIDE_COST * (t_down - t_best)) if ok else 0,
        "score_parts": [{"label": "ride down", "value": "%.2f s" % t_down,
                         "note": "-20 for every 0.1 s slower than the fastest ride that still lifts the gate"}]
        if ok else [],
        "frames": kit.world(frames, TRAP, extra=("x1", "x2")),
        "viz": {"lift_cm": round(100 * lift, 2), "t_down": t_down, "reached": reached,
                "ratio": round(res["viz"]["ratio"], 3)},
        "formula": [{"expr": "F2 = F1 * (A2 / A1)",
                     "values": {"F1 (ball)": round(WEIGHT, 2), "A2/A1": round(res["viz"]["ratio"], 2),
                                "F2": round(WEIGHT * res["viz"]["ratio"], 1),
                                "gate + piston": round((fx["gate_kg"] + HG["piston"]) * G, 1)}},
                    {"expr": "x2 = x1 * (A1 / A2)",
                     "values": {"x1 (ball's ride)": "30 cm", "A1/A2": round(1 / res["viz"]["ratio"], 3),
                                "x2 (gate's rise)": "%.1f cm" % (100 * lift)}}],
        "lab": [{"title": "Pressure: the same lift, pushed by the ball's weight",
                 "route": "#/pressure?" + kit.query(sorted(p.items()))}],
    }


# ================================================================ 2.4 Magnet Swing
HOLD = 12.0                    # N: the magnet's grip
GENTLE = 9.0                   # N: mastery - never load it past 75 %


def ladle_x(fx):
    return fx["ladle"]


def run_magnet_swing(k, fx, thresholds=None):
    L, th0 = k["length"], k["angle"]
    res = pendulum.run({"length": L, "amplitude": th0, "mass": BALL["mass"], "g": G, "drag": round(BALL_K, 6)})
    fr = res["frames"]
    r = BALL_R
    pivot = (0.0, L)                                                  # local: the bottom of the swing is (0, 0)
    frames, peak, let_go, release = [], 0.0, None, None
    for a, b in zip(fr, fr[1:]):                                      # swing from the left to the bottom
        th = a["theta"]
        frames.append({"t": a["t"], "x": round(-L * math.sin(th), 5), "y": round(L - L * math.cos(th), 5),
                       "th": round(th, 5)})
        peak = max(peak, a["tension"])
        if a["tension"] > HOLD:
            let_go = a
            break
        if a["theta"] > 0 >= b["theta"]:
            u = a["theta"] / (a["theta"] - b["theta"])               # the trip wire: exactly at the bottom
            release = {"t": a["t"] + u * (b["t"] - a["t"]), "omega": a["omega"] + u * (b["omega"] - a["omega"])}
            peak = max(peak, b["tension"])
            break
    if let_go is not None:                                           # it tears off early and flies off the arc
        th, om = let_go["theta"], let_go["omega"]
        x0, y0 = -L * math.sin(th), L - L * math.cos(th)
        vx, vy = -L * om * math.cos(th), -L * om * math.sin(th)
        t0 = let_go["t"]
    else:
        x0, y0, vx, vy, t0 = 0.0, 0.0, -L * release["omega"], 0.0, release["t"]
        frames.append({"t": round(t0, 5), "x": 0.0, "y": 0.0, "th": 0.0})
    d, ty = ladle_x(fx), -DROP
    out = tracer.trace(x0, y0, vx, vy, BALL["mass"], r, BALL_K, tmax=3.0,
                       zones=[("down", lambda x, y, vx_, vy_: vy_ < 0 and y <= ty)])
    land = out["x"]
    speed = math.hypot(vx, vy)
    th_hang = frames[-1]["th"]
    frames += [{"t": round(t0 + f["t"], 5), "x": f["x"], "y": f["y"], "th": th_hang} for f in out["frames"][1:]]
    if out["outcome"] == "down":                                     # settle into the ladle
        frames.append({"t": round(frames[-1]["t"] + 0.2, 5), "x": round(land, 5), "y": round(ty - 0.12, 5),
                       "th": th_hang})
    inside = let_go is None and d - LADLE_HALF + r <= land <= d + LADLE_HALF - r
    if let_go is not None:
        reason = ("The magnet lost its grip at %.0f° - the ball pulled %.1f N and it holds %.0f N." %
                  (abs(math.degrees(let_go["theta"])), let_go["tension"], HOLD))
    elif not inside:
        reason = "Released at %.2f m/s it landed %.2f m out - the ladle is at %.2f m (± %.0f cm)." % (
            speed, land, d, 100 * LADLE_HALF)
    else:
        reason = "Into the ladle! Released at %.2f m/s, landed %.2f m out; the magnet carried %.1f N at most." % (
            speed, land, peak)
    aim = max(0.0, 1.0 - (abs(land - d) / LADLE_HALF) ** 2) if inside else 0.0
    safe = max(0.0, min(1.0, (HOLD - peak) / (HOLD - WEIGHT)))
    return {
        "ok": inside, "reason": reason, "metric": round(peak, 2), "unit": "N", "predicted": round(speed, 3),
        "mastery": bool(inside and peak <= GENTLE),
        "score": kit.score(inside, AIM_POINTS * aim + SAFE_POINTS * safe) if inside else 0,
        "score_parts": [{"label": "aim", "value": "%d cm from the middle" % round(100 * abs(land - d)),
                         "note": "up to 700 for the middle of the ladle"},
                        {"label": "magnet load", "value": "%.1f N of %d" % (peak, HOLD),
                         "note": "up to 300 for grip to spare"}] if inside else [],
        "frames": kit.world(frames, SWING, extra=("th",)),
        "viz": {"land": round(land, 3), "speed": round(speed, 3), "peak": round(peak, 2), "let_go": let_go is not None},
        "formula": [{"expr": "T = m*g*(3 - 2*cos(theta))",
                     "values": {"m": BALL["mass"], "theta": th0, "T (no air)": round(
                         BALL["mass"] * G * (3 - 2 * math.cos(math.radians(th0))), 2), "T (measured)": round(peak, 2),
                         "grip": HOLD}},
                    {"expr": "D = 2 * sqrt(L * (1 - cos(theta)) * H)",
                     "values": {"L": L, "H": DROP, "D": round(2 * math.sqrt(L * (1 - math.cos(math.radians(th0))) * DROP), 3),
                                "ladle": d}}],
        "lab": [{"title": "Pendulum: the same swing ('String tension at the bottom' = the magnet's load)",
                 "route": "#/pendulum?" + kit.query([("length", L), ("amplitude", th0), ("mass", BALL["mass"]),
                                                     ("g", G), ("drag", round(BALL_K, 6))])}],
    }


# ================================================================ the station table

STATIONS = [
    {"id": "2.1", "hall": "foundry", "title": "Hot Ring", "scene": "hot_ring", "par": 2, "learn": "heat",
     "run": run_hot_ring,
     "intro": "The ore cart tips the steel ball onto an aluminium ring - and it sticks: the ring's hole is a few "
              "hundredths of a millimetre too small. A kettle of 95 °C water stands ready.",
     "goal": "Make the ball drop through the ring within the shift (2 minutes).",
     "hook": "Metals grow when they are hot - but aluminium grows almost twice as much as steel.",
     "knobs": [choice("target", "Pour the hot water on", TARGETS, "ball"),
               num("water", "Hot water (95 °C)", 0.0, 0.50, 0.10, "kg", 0.01)],
     "facts": [fact("gap_um", "The ring's hole is too small by", 60.0, "µm", vary=(50.0, 70.0)),
               fact("ball_d", "Ball diameter (steel)", BALL_D_MM, "mm"),
               fact("ring_mass", "Ring mass (aluminium)", RING_MASS, "kg"),
               fact("alpha_al", "Aluminium grows per kelvin (α)", 23.1, "µm per m"),
               fact("alpha_steel", "Steel grows per kelvin (α)", 12.0, "µm per m"),
               fact("c_al", "Aluminium specific heat", 900.0, "J/(kg·K)"),
               fact("c_w", "Water specific heat", 4186.0, "J/(kg·K)"),
               fact("kettle", "Kettle water", KETTLE, "°C")],
     "predict": {"label": "How hot will the part you pour on get (its highest temperature)?", "kind": "number",
                 "unit": "°C", "tol": 0.05, "abs": 2.0},
     "mastery": {"id": "thrifty", "text": "Waste Not: open the ring with {thrifty} kg of hot water or less."},
     "score_rule": "Score: hot water and time both cost. Each 10 g of hot water costs 40, each second until the "
                   "ring lets go costs 40 (more water heats the ring faster). The cheapest way scores 1000.",
     "formulas": ["T_eq = (m_w c_w T_w + m_r c_r T_r) / (m_w c_w + m_r c_r)", "dL = alpha * L * dT"],
     "hints": ["Heat makes metals grow. Which part should grow - the ring or the ball? (And what if both do?)",
               "The hole must grow by {gap_um} µm: ΔL = α·L·ΔT with α = 23.1e-6 and L = 50 mm gives the ring's ΔT. "
               "Then heat balance: m_w·4186·(95 − T) = 0.30·900·(T − 20) gives the water. The cup leaks a little, so "
               "add a bit."],
     "solutions": [{"target": "ring", "water": 0.2}, {"target": "ring", "water": 0.5}],
     "mastery_solutions": [{"target": "ring", "water": 0.17}],
     "wrong": [({"target": "ball", "water": 0.5}, "heated the BALL"), ({"target": "both", "water": 0.5}, "DIFFERENCE"),
               ({"target": "ring", "water": 0.1}, "More hot water")]},
    {"id": "2.2", "hall": "foundry", "title": "Trapdoor Latch", "scene": "trapdoor", "par": 2, "learn": "circuits",
     "run": run_trapdoor,
     "intro": "The ball lands on two copper plates on a trapdoor and joins them - the steel ball IS the switch. "
              "Current then flows through the latch coil; strong enough, and the latch lets the trapdoor drop.",
     "goal": "Get between the latch's pull-in current and the fuse's limit.",
     "hook": "Only a metal ball closes this circuit - a rubber or wooden ball would just sit there.",
     "knobs": [choice("battery", "Battery", BATTERIES, "aa"),
               num("R", "Resistor dial", 0.0, 50.0, 0.0, "Ω", 0.5)],
     "facts": [fact("coil_ohm", "Latch coil resistance", 8.0, "Ω", vary=(7.0, 9.0)),
               fact("pull_in", "The latch pulls at", 0.30, "A"),
               fact("fuse", "The fuse blows above", FUSE_A, "A"),
               fact("contacts", "Fuse + steel ball + wire", R_FUSE + R_BALL + circuitlab.R_WIRE, "Ω")],
     "predict": {"label": "What current will flow?", "kind": "number", "unit": "A", "tol": 0.05, "abs": 0.02},
     "mastery": {"id": "cool_coil", "text": "Cool Coil: keep the latch coil below 1.5 W (P = I²·R)."},
     "score_rule": "Score: save the battery! 1000 for the least battery power (P = V·I) that still pulls the latch; "
                   "every 0.1 W more costs 40.",
     "formulas": ["I = V / (R + r + R_coil + R_fuse + R_ball)", "P = I^2 * R_coil", "P = V * I"],
     "hints": ["It's one loop: the same current flows through the battery, the dial, the fuse, the coil and the ball. "
               "Two limits: enough for the latch, not so much the fuse blows.",
               "I = V / (R + r + {coil_ohm} + 0.11). You need 0.30 A ≤ I ≤ 1 A. Try each battery: what R keeps I in "
               "the window? (The AA can't.)"],
     "solutions": [{"battery": "lantern", "R": 0.0}, {"battery": "car_battery", "R": 20.0}],
     "mastery_solutions": [{"battery": "lantern", "R": 8.0}],
     "wrong": [({"battery": "aa", "R": 0.0}, "too weak"), ({"battery": "car_battery", "R": 0.0}, "fuse blew"),
               ({"battery": "lantern", "R": 20.0}, "too weak")]},
    {"id": "2.3", "hall": "foundry", "title": "Hydraulic Gate", "scene": "hydraulic_gate", "par": 2,
     "learn": "pressure", "run": run_hydraulic_gate,
     "intro": "The ball lands on a small piston (2 cm across) and rides it 30 cm down. The oil pushes up a big "
              "piston that lifts the gate blocking the tunnel at the bottom.",
     "goal": "Size the big piston so the ball's weight gets all the way down AND the gate rises at least 6 cm.",
     "hook": "Only the heavy steel ball (5 N) can drive it - a wooden ball weighs just 1.6 N.",
     "knobs": [num("d2", "Big piston diameter", 2.0, 10.0, 6.0, "cm", 0.1)],
     "facts": [fact("gate_kg", "Gate mass", 1.0, "kg", vary=(0.9, 1.1)),
               fact("piston", "Big piston's own mass", HG["piston"], "kg"),
               fact("ball_n", "The ball's weight", round(WEIGHT, 2), "N"),
               fact("d1", "Small piston diameter", HG["d1"], "cm"),
               fact("stroke", "The ball rides down", HG["stroke"], "cm"),
               fact("need", "The gate must rise at least", 100 * HG["need"], "cm"),
               fact("oil", "Oil density", 870.0, "kg/m³")],
     "predict": {"label": "How high will the gate rise?", "kind": "number", "unit": "cm", "tol": 0.05, "abs": 0.2},
     "mastery": {"id": "high_gate", "text": "High Gate: lift the gate 7.5 cm or more."},
     "score_rule": "Score: speed! 1000 for the fastest ride down that still lifts the gate 6 cm; every 0.1 s slower "
                   "costs 20.",
     "formulas": ["F2 = F1 * (A2 / A1)", "x2 = x1 * (A1 / A2)"],
     "hints": ["A wider big piston pushes harder (more area) but moves less (the oil's volume is shared). You need "
               "both: enough force AND enough rise.",
               "Force: 5.0 N × (d2/2)² must beat ({gate_kg} + 0.1) kg × 9.81 - and the oil column's weight adds a bit. "
               "Rise: 30 cm × (2/d2)² must be ≥ 6 cm."],
     "solutions": [{"d2": 3.9}, {"d2": 4.2}], "mastery_solutions": [{"d2": 3.7}],
     "wrong": [({"d2": 2.9}, "Nothing moves"), ({"d2": 6.0}, "only rose")]},
    {"id": "2.4", "hall": "foundry", "title": "Magnet Swing", "scene": "magnet_swing", "par": 3, "learn": "pendulum",
     "run": run_magnet_swing,
     "intro": "A crane's electromagnet picks the ball up and swings it on a cable. At the bottom of the swing a trip "
              "wire cuts the magnet and the ball flies off over the casting pit, into the ladle.",
     "goal": "Choose the cable length and the release angle so the ball lands in the ladle - without the magnet "
             "losing its grip on the way.",
     "hook": "Only a magnetic ball can be carried like this.",
     "knobs": [num("length", "Cable length", 0.40, 2.00, 1.00, "m", 0.05),
               num("angle", "Release angle", 10.0, 90.0, 30.0, "°", 1.0)],
     "facts": [fact("ladle", "Ladle distance from the bottom of the swing", 1.5, "m", vary=(1.4, 1.6)),
               fact("drop", "Ladle rim below the bottom of the swing", DROP, "m"),
               fact("mouth", "Ladle mouth width", 2 * LADLE_HALF, "m"),
               fact("hold", "The magnet holds up to", HOLD, "N"),
               fact("ball_n", "The ball's weight", round(WEIGHT, 2), "N")],
     "predict": {"label": "How fast will it leave the magnet?", "kind": "number", "unit": "m/s", "tol": 0.05,
                 "abs": 0.05},
     "mastery": {"id": "gentle", "text": "Gentle Grip: never load the magnet past 9 N."},
     "score_rule": "Score: up to 700 for landing in the middle of the ladle, plus up to 300 for how much grip the "
                   "magnet still had to spare.",
     "formulas": ["T = m*g*(3 - 2*cos(theta))", "D = 2 * sqrt(L * (1 - cos(theta)) * H)"],
     "hints": ["Two things to get right: the speed at the bottom decides how far it flies, and the pull on the magnet "
               "is biggest at the bottom of the swing.",
               "At the bottom the magnet carries T = m·g·(3 − 2cos θ), whatever the cable length - so θ ≤ 72° for 12 N. "
               "The flight: v = √(2gL(1−cos θ)), D = v·√(2H/g) = 2√(L(1−cos θ)H) = {ladle} m."],
     "solutions": [{"length": 1.0, "angle": 58.0}, {"length": 2.0, "angle": 40.0}],
     "mastery_solutions": [{"length": 1.5, "angle": 47.0}],
     "wrong": [({"length": 0.6, "angle": 78.0}, "lost its grip"), ({"length": 1.0, "angle": 30.0}, "landed")]},
]
BY_ID = {s["id"]: s for s in STATIONS}

HALL = {"id": "foundry", "title": "The Foundry", "ball": "steel", "status": "ready",
        "blurb": "A foundry: hot water, a latch circuit, hydraulics and a crane magnet. Get the steel ball from the "
                 "ore cart to the ladle.",
        "stations": STATIONS, "layout": LAYOUT}

VIA = {"2.1": lambda last, nxt: [(RING[0], CHUTE_Y), (2.3, TRAP[1] + 0.1)],
       "2.2": lambda last, nxt: [],
       "2.3": lambda last, nxt: [(PICKUP[0], PICKUP[1])]}         # the magnet pulls it up from the pickup
KIT = kit.Hall(HALL, STATIONS, DATA, VIA, 1.2)
table, variant_data, thresholds = KIT.table, KIT.variant_data, KIT.thresholds
mastery_text, hint_text, run_station, run_machine = KIT.mastery_text, KIT.hint_text, KIT.run_station, KIT.run_machine
