"""Pressure: a hydraulic lift. You push the small piston down; the liquid
carries the pressure to the big piston, which lifts a load.

* pressure                p = F / A
* Pascal's principle      the same pressure acts everywhere in the liquid
                          (plus rho g depth for the liquid's own weight), so
                          F2 = F1 * A2 / A1            force multiplied
* liquid doesn't squash   A1 d1 = A2 d2  ->  d2 = d1 * A1 / A2   distance divided
* energy                  F1 d1 = F2 d2 (+ losses)     no free lunch

Model (one degree of freedom, the small piston's push-down x1; the big
piston rises x2 = x1 A1/A2 exactly - incompressible liquid):

    (m_p + M (A1/A2)^2) x1'' = F_hand(v) - c v - A1 [M g / A2 + rho g (h2 - h1)]

  F_hand(v) = F1 (1 - v / V_HAND)  a person pushes hardest when slow: at
              V_HAND = 0.3 m/s their push has dropped to zero (a linear,
              Hill-type force-speed model)
  c v       seal and flow friction, c = 20 N s/m
  h2 - h1   the liquid stands higher under the big piston as it rises, so
            its own weight pushes back a little (rho g times the height gap)
The small piston starts against its top stop, so if the push is too weak
nothing moves (the stop holds the difference). The run ends at the bottom
of the stroke, or when everything has stalled.

Energy is booked exactly: work in = load lifted + liquid lifted +
friction heat + kinetic energy (checked in the tests).
"""

import math

G_DEFAULT = 9.81
V_HAND = 0.3          # m/s: fastest push a person manages (force -> 0)
C_LOSS = 20.0         # N s/m: seal + flow friction
M_PISTON = 0.5        # kg: small piston and rod
H0 = 0.30             # m: liquid height in both cylinders at the start
DT = 0.0005
T_MAX = 20.0
RECORD = 0.02
P_ATM = 101325.0


def area(d_cm):
    """Circle area in m^2 from a diameter in cm."""
    r = d_cm / 200.0
    return math.pi * r * r


def pressure(force, a):
    return force / a


def output_force(f1, a1, a2):
    return f1 * a2 / a1


def output_distance(d1, a1, a2):
    return d1 * a1 / a2


def hand_force(f1, v):
    return f1 * max(0.0, 1.0 - max(v, 0.0) / V_HAND)


def needed_push(m, g, a1, a2, rho, x1):
    """Push on the small piston that just holds the load at stroke x1."""
    x2 = x1 * a1 / a2
    dh = (H0 + x2) - (H0 - x1)                    # liquid higher on the big side
    return a1 * (m * g / a2 + rho * g * dh)


def liquid_lift_energy(rho, g, a1, x1, a2):
    """Potential energy gained by the liquid: a slug A1 x1 moves from the
    top of the small column to the top of the big one."""
    x2 = x1 * a1 / a2
    return rho * g * a1 * x1 * (x1 + x2) / 2.0


def run(p):
    from .. import HYDRAULIC_FLUIDS
    fluid = next(f for f in HYDRAULIC_FLUIDS if f["id"] == p["fluid"])
    rho, g = fluid["rho"], G_DEFAULT
    f1, m = p["force"], p["mass"]
    a1, a2 = area(p["d1"]), area(p["d2"])
    stroke = p["stroke"] / 100.0
    ratio = a2 / a1
    m_eff = M_PISTON + m * (a1 / a2) ** 2

    # the hand's force-speed slope makes the motion stiff when little mass
    # moves (tiny small piston): resolve that relaxation time
    dt = min(DT, 0.1 * m_eff / (f1 / V_HAND + C_LOSS))

    def accel(x, v):
        return (hand_force(f1, v) - C_LOSS * v - needed_push(m, g, a1, a2, rho, x)) / m_eff

    x = v = t = 0.0
    w_in = w_loss = 0.0
    held = 0.0
    frames = []
    stalled = False

    def frame(t, x, v, a):
        x2 = x * a1 / a2
        dh = (H0 + x2) - (H0 - x)
        fh = hand_force(f1, v)
        if x <= 0.0 and v == 0.0 and fh < needed_push(m, g, a1, a2, rho, 0.0):
            p1 = m * g / a2                          # stop holds the rest: liquid only carries the load
        else:
            p1 = (fh - C_LOSS * v - M_PISTON * a) / a1
        p2 = p1 - rho * g * dh
        return {"t": round(t, 4), "x1": round(x, 7), "x2": round(x2, 9), "v1": round(v, 6),
                "v2": round(v * a1 / a2, 8), "p1": round(p1, 3), "p2": round(p2, 3),
                "f_hand": round(fh, 4), "f_lift": round(p2 * a2, 4),
                "w_in": round(w_in, 6), "w_load": round(m * g * x2, 6),
                "w_liquid": round(liquid_lift_energy(rho, g, a1, x, a2), 8),
                "w_loss": round(w_loss, 6), "ke": round(0.5 * m_eff * v * v, 8)}

    frames.append(frame(0.0, 0.0, 0.0, 0.0))
    next_rec = RECORD
    while t < T_MAX:
        # RK4 on (x, v); work and losses integrated with the same weights
        def deriv(x_, v_):
            return v_, accel(x_, v_), hand_force(f1, v_) * v_, C_LOSS * v_ * v_
        k1 = deriv(x, v)
        k2 = deriv(x + 0.5 * dt * k1[0], v + 0.5 * dt * k1[1])
        k3 = deriv(x + 0.5 * dt * k2[0], v + 0.5 * dt * k2[1])
        k4 = deriv(x + dt * k3[0], v + dt * k3[1])
        nx = x + dt / 6.0 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        nv = v + dt / 6.0 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        dwin = dt / 6.0 * (k1[2] + 2 * k2[2] + 2 * k3[2] + k4[2])
        dwloss = dt / 6.0 * (k1[3] + 2 * k2[3] + 2 * k3[3] + k4[3])
        if nx <= 0.0 and nv <= 0.0:               # against the top stop: nothing moves
            nx, nv, dwin, dwloss = 0.0, 0.0, 0.0, 0.0
        done = nx >= stroke
        step = dt
        if done:                                  # reaches the bottom stop inside this step:
            s_ = (stroke - x) / (nx - x)          # cut the step at the stop, and the piston's
            step = s_ * dt                        # kinetic energy is lost in the bump
            dwin *= s_
            dwloss *= s_
            nv = v + s_ * (nv - v)
            dwloss += 0.5 * m_eff * nv * nv
            nx, nv = stroke, 0.0
        x, v = nx, nv
        w_in += dwin
        w_loss += dwloss
        t += step
        if abs(v) < 1e-6 and not done:
            held += step
        else:
            held = 0.0
        if held > 0.3:
            stalled = True
        if t >= next_rec - 1e-12 or done or stalled:
            frames.append(frame(t, x, v, accel(x, v) if not done else 0.0))
            next_rec += RECORD
        if done or stalled:
            break

    need = needed_push(m, g, a1, a2, rho, 0.0)
    p_push = pressure(f1, a1)
    f2 = output_force(f1, a1, a2)
    last = frames[-1]
    lifted = last["x1"] > 1e-6
    eff = last["w_load"] / last["w_in"] if last["w_in"] > 0 else 0.0
    notes = []
    if not lifted:
        notes.append("Not enough push: your %.0f N makes %.0f kPa, but holding the %.0f kg load needs "
                     "%.0f kPa (a %.0f N push). Push harder or use a thinner small piston."
                     % (f1, p_push / 1000.0, m, need / a1 / 1000.0, need))
    else:
        notes.append("The small piston went down %.0f cm but the big one rose only %.2f mm: %.0fx the "
                     "force, 1/%.0f of the distance. Real car jacks pump many short strokes, with valves "
                     "that stop the liquid flowing back." % (last["x1"] * 100.0, last["x2"] * 1000.0,
                                                             ratio, ratio))
    if m == 0.0:
        notes.append("No load: only the liquid's own weight pushes back.")

    return {
        "frames": frames,
        "notes": notes,
        "viz": {"a1": a1, "a2": a2, "d1": p["d1"] / 100.0, "d2": p["d2"] / 100.0, "ratio": ratio,
                "stroke": stroke, "h0": H0, "mass": m, "g": g, "rho": rho, "fluid": fluid,
                "need": round(need, 4), "p_push": round(p_push, 3), "f2": round(f2, 3),
                "weight": round(m * g, 4), "lifted": lifted},
        "readouts": [
            {"label": "Pressure your push makes p = F1/A1", "value": round(p_push / 1000.0, 2),
             "unit": "kPa (%.2fx air pressure)" % (p_push / P_ATM)},
            {"label": "Force on the big piston F2 = p·A2", "value": round(f2, 1), "unit": "N"},
            {"label": "Weight of the load", "value": round(m * g, 1), "unit": "N"},
            {"label": "Smallest push that lifts it", "value": round(need, 1), "unit": "N"},
            {"label": "Area ratio A2/A1 (force multiplier)", "value": round(ratio, 2), "unit": "x"},
            {"label": "Big piston rose", "value": round(last["x2"] * 1000.0, 3),
             "unit": "mm (small piston: %.1f cm)" % (last["x1"] * 100.0)},
            {"label": "Work in (F1·d1)", "value": round(last["w_in"], 3), "unit": "J"},
            {"label": "Work on the load (F2·d2)", "value": round(last["w_load"], 3),
             "unit": "J (%.0f%% of the work in)" % (100.0 * eff)},
        ],
        "formula": [
            {"expr": "P = F / A",
             "values": {"F1": round(f1, 1), "A1": round(a1, 6), "p": round(p_push, 1)}},
            {"expr": "F2 = F1 * (A2 / A1)",
             "values": {"F1": round(f1, 1), "A2/A1": round(ratio, 2), "F2": round(f2, 1)}},
            {"expr": "d2 = d1 * (A1 / A2)",
             "values": {"d1": round(last["x1"], 4), "A1/A2": round(1.0 / ratio, 5),
                        "d2": round(last["x2"], 6)}},
            {"expr": "F1 * d1 = F2 * d2",
             "values": {"work_in": round(last["w_in"], 3), "work_out": round(last["w_load"], 3),
                        "heat": round(last["w_loss"], 3)}},
        ],
    }
