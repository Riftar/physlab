"""Levers & moments: a beam on a pivot with a load hanging on each side.

The turning effect (moment, torque) of a weight about the pivot is

    tau = m g d cos(theta)          d = the hook's distance from the pivot along the beam

(g times the horizontal distance: as the beam tilts, the lever arm shrinks
by cos theta). The beam balances when the two turning effects are equal -
the principle of moments:

    m1 d1 = m2 d2                   (g and cos theta cancel)

If they are not equal, the beam turns. It is a rigid body on an axle, so
Newton's second law for turning is

    I alpha = tau_net,   I = M_beam L^2 / 12 + m1 d1^2 + m2 d2^2

(a uniform beam pivoted in its middle, the loads as point masses at their
hooks), with the pivot's friction tau_f acting against the motion: a beam
at rest only starts to move if |m2 d2 - m1 d1| g cos(theta) > tau_f.

The beam is L = 2.2 m long, pivoted in the middle, and rubber stops hold
it at +-25 degrees; theta > 0 means the RIGHT end is down. The run ends
when it hits a stop (it stops dead there), or after T_MAX. RK4 at a fixed
step, the stop crossing interpolated: same params -> byte-identical
frames. The game's Mill Hoist (Millbrook Mill, 3.4) is this beam.
"""

import math

BEAM_L = 2.2            # m
STOP = 25.0             # degrees either way
DT = 0.001
RECORD = 0.01           # s between frames
T_MAX = 20.0
HOLD = 0.6              # s recorded after it hits a stop (or when it can't start)


def moment(m, d, g, theta=0.0):
    """Turning effect of a load m (kg) hanging d (m) from the pivot, N m."""
    return m * g * d * math.cos(theta)


def inertia(beam_m, m1, d1, m2, d2, length=BEAM_L):
    return beam_m * length * length / 12.0 + m1 * d1 * d1 + m2 * d2 * d2


def balance_mass(m1, d1, d2):
    """The right-hand load that balances m1 at d1 (principle of moments)."""
    return m1 * d1 / d2


def balance_distance(m1, d1, m2):
    return m1 * d1 / m2 if m2 > 0 else None


def run(p):
    m1, d1, m2, d2 = p["m1"], p["d1"], p["m2"], p["d2"]
    g, mb, tf = p["g"], p["beam"], p["friction"]
    stop = math.radians(STOP)
    th = math.radians(p["start"])
    inert = inertia(mb, m1, d1, m2, d2)
    unbalance = round(m2 * d2 - m1 * d1, 12)            # kg m: > 0 turns clockwise (right end down)
    sgn = 1.0 if unbalance > 0 else -1.0

    def tau_load(t_):
        return g * math.cos(t_) * unbalance

    def acc(t_):                                        # while moving (in the direction of sgn)
        return (tau_load(t_) - sgn * tf) / inert

    def frame(t, th_, om):
        return {"t": round(t, 4), "theta": round(th_, 6), "omega": round(om, 6),
                "tau": round(tau_load(th_) - (sgn * tf if om != 0.0 else 0.0), 6)}

    at_stop = (th >= stop - 1e-12 and sgn > 0) or (th <= -stop + 1e-12 and sgn < 0)
    starts = abs(tau_load(th)) > tf and not at_stop and unbalance != 0.0
    frames = [frame(0.0, th, 0.0)]
    t, om, hit, t_hit, om_hit = 0.0, 0.0, 0, None, 0.0
    if starts:
        n, next_rec = 0, RECORD
        while t < T_MAX:
            k1t, k1o = om, acc(th)
            k2t, k2o = om + 0.5 * DT * k1o, acc(th + 0.5 * DT * k1t)
            k3t, k3o = om + 0.5 * DT * k2o, acc(th + 0.5 * DT * k2t)
            k4t, k4o = om + DT * k3o, acc(th + DT * k3t)
            nth = th + DT / 6.0 * (k1t + 2 * k2t + 2 * k3t + k4t)
            nom = om + DT / 6.0 * (k1o + 2 * k2o + 2 * k3o + k4o)
            n += 1
            if (sgn > 0 and nth >= stop) or (sgn < 0 and nth <= -stop):
                u = (sgn * stop - th) / (nth - th)                    # the moment it reaches the stop
                t_hit = t + u * DT
                om_hit = om + u * (nom - om)
                th, t, hit = sgn * stop, t_hit, int(sgn)
                frames.append(frame(t_hit, th, om_hit))
                break
            th, om, t = nth, nom, n * DT
            if t >= next_rec - 1e-12:
                frames.append(frame(t, th, om))
                next_rec += RECORD
    end = (t_hit if hit else t) + HOLD
    frames.append(frame(round(end, 4), th, 0.0))

    v1, v2 = abs(om_hit) * d1, abs(om_hit) * d2
    need = balance_mass(m1, d1, d2)
    if not starts:
        if at_stop:
            state = "resting on the stop - it is already turned as far as it goes"
        elif unbalance == 0.0:
            state = "balanced: m1 d1 = m2 d2, so it stays put"
        else:
            state = "stays put: the difference in turning effect (%.3f N m) can't beat the pivot's friction " \
                    "(%.2f N m)" % (abs(tau_load(th)), tf)
    else:
        state = "the %s end goes down%s" % ("right" if sgn > 0 else "left",
                                            " and hits the stop after %.2f s" % t_hit if hit else "")
    notes = []
    if starts and hit:
        notes.append("It turns because the turning effects don't match: %.2f kg m on the right vs %.2f kg m on "
                     "the left (mass x distance). It hit the stop after %.2f s with the %s end moving at %.2f m/s."
                     % (m2 * d2, m1 * d1, t_hit, "left" if d1 >= d2 else "right", max(v1, v2)))
    elif not starts and not at_stop:
        notes.append("Balance needs m1 d1 = m2 d2: with %.2f kg at %.2f m on the left, the right load at %.2f m "
                     "must be %.3f kg." % (m1, d1, d2, need))
    if starts and abs(unbalance) < 0.05 * max(m1 * d1, m2 * d2, 1e-9):
        notes.append("Only just out of balance: the net turning effect is small, so it starts slowly - then "
                     "speeds up all the way to the stop.")
    return {
        "frames": frames,
        "notes": notes,
        "viz": {"length": BEAM_L, "stop": STOP, "m1": m1, "d1": d1, "m2": m2, "d2": d2, "beam": mb,
                "friction": tf, "g": g, "inertia": round(inert, 6), "unbalance": round(unbalance, 6),
                "moves": starts, "hit": hit, "t_hit": round(t_hit, 4) if hit else None,
                "omega_hit": round(om_hit, 6), "v1": round(v1, 5), "v2": round(v2, 5),
                "balance_m2": round(need, 5), "state": state},
        "readouts": [
            {"label": "Turning effect, left (m1 g d1)", "value": round(moment(m1, d1, g), 3), "unit": "N m"},
            {"label": "Turning effect, right (m2 g d2)", "value": round(moment(m2, d2, g), 3), "unit": "N m"},
            {"label": "What happens", "value": state, "unit": ""},
            {"label": "Balances with a right load of", "value": round(need, 3), "unit": "kg at %.2f m" % d2},
            {"label": "Moment of inertia I", "value": round(inert, 4), "unit": "kg m²"},
            {"label": "Time to the stop", "value": round(t_hit, 3) if hit else "—", "unit": "s" if hit else ""},
            {"label": "Left load's speed at the stop", "value": round(v1, 3), "unit": "m/s"},
            {"label": "Right load's speed at the stop", "value": round(v2, 3), "unit": "m/s"},
        ],
        "formula": [
            {"expr": "m1 * d1 = m2 * d2",
             "values": {"m1*d1": round(m1 * d1, 4), "m2*d2": round(m2 * d2, 4),
                        "balanced": abs(unbalance) < 1e-9}},
            {"expr": "tau = m * g * d",
             "values": {"tau_left": round(moment(m1, d1, g), 3), "tau_right": round(moment(m2, d2, g), 3),
                        "tau_friction": tf}},
            {"expr": "alpha = tau_net / I",
             "values": {"tau_net": round(abs(tau_load(math.radians(p["start"]))) - tf, 4) if starts else 0.0,
                        "I": round(inert, 4),
                        "alpha": round((abs(tau_load(math.radians(p["start"]))) - tf) / inert, 4) if starts else 0.0}},
        ],
    }
