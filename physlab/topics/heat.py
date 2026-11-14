"""Heat transfer: two blocks in thermal contact, optional leak to room.

Lumped model (each block has one uniform temperature):

    flow   = G * (T_a - T_b)                 W, A -> B when positive
    leak_i = loss * (T_i - T_room)           W, block i -> room
    m_a c_a dT_a/dt = -flow - leak_a
    m_b c_b dT_b/dt = +flow - leak_b

Contact conductance G = 20 W/K, ambient leak = params['loss'] W/K.
Each block uses ITS OWN material (specific heat c; density rho sets
its size on screen). With loss = 0 the pair converges exactly to the
energy-weighted mean temperature (asserted in tests): the exchange term
is antisymmetric, so forward Euler conserves m_a c_a T_a + m_b c_b T_b
to rounding.

The linear system has two relaxation rates (eigenvalues): a fast one
(the blocks agree with each other) and, with a leak, a slow one (the
pair drifts to room temperature). The step is 1/50 of the fast time
constant; frames are spaced max(tau/10, t/60) - dense while things
change quickly, sparser as they slow - so tiny copper blocks that
settle in seconds are resolved as well as 10 kg of water that takes an
hour, in at most a few hundred frames. The run ends once visibly
settled (within 0.02 C of each other and, with a leak, of the room) or
after one hour of lab time.
"""

import math

DT_MAX = 0.1
FRAMES_PER_TAU = 10     # frame spacing early on: tau / 10
FRAMES_PER_EFOLD = 60   # frame spacing later: t / 60
MAX_T = 3600.0          # one hour of lab time
G_CONTACT = 20.0
SETTLE_K = 0.02


def material(material_id):
    from .. import MATERIALS
    for m in MATERIALS:
        if m["id"] == material_id:
            return m
    return None


def relaxation_rates(cap_a, cap_b, loss):
    """Eigen-rates (1/s) of the 2-block system, (fast, slow).
    slow == 0 when there is no leak (the total energy is then conserved)."""
    g = G_CONTACT
    tr = (g + loss) * (1.0 / cap_a + 1.0 / cap_b)
    det = loss * (2.0 * g + loss) / (cap_a * cap_b)
    root = math.sqrt(max(0.0, tr * tr - 4.0 * det))
    return (tr + root) / 2.0, (tr - root) / 2.0


def _frame(t, ta, tb, flow, leak_a, leak_b, q):
    return {"t": round(t, 3), "temp_a": round(ta, 3), "temp_b": round(tb, 3),
            "flow": round(flow, 3), "leak_a": round(leak_a, 3),
            "leak_b": round(leak_b, 3), "q": round(q, 2)}


def _water_notes(label, temps):
    lo, hi = min(temps), max(temps)
    if lo >= 0.0 and hi <= 100.0:
        return []
    state = "ice" if hi <= 100.0 else "steam" if lo >= 0.0 else "ice or steam"
    return ["Block %s is water outside 0-100 C: real water would be %s there and "
            "would need extra (latent) heat to change state. This model keeps it "
            "liquid (c = 4186 J/kg/K) to stay simple." % (label, state)]


def run(p):
    mat_a, mat_b = material(p["material_a"]), material(p["material_b"])
    ca, cb = mat_a["c"], mat_b["c"]
    ta, tb = p["temp_a"], p["temp_b"]
    cap_a, cap_b = p["mass_a"] * ca, p["mass_b"] * cb
    amb, loss = p["ambient"], p["loss"]
    fast, _slow = relaxation_rates(cap_a, cap_b, loss)
    tau = 1.0 / fast
    dt = min(DT_MAX, tau / 50.0)        # keeps Euler's timing error ~1%
    steps_max = int(round(MAX_T / dt))

    def rates(ta, tb):
        return G_CONTACT * (ta - tb), loss * (ta - amb), loss * (tb - amb)

    frames = [_frame(0.0, ta, tb, *rates(ta, tb), q=0.0)]
    q_moved = 0.0
    n = n_rec = 0
    while n < steps_max:
        if (abs(ta - tb) < SETTLE_K and
                (loss == 0.0 or (abs(ta - amb) < SETTLE_K and abs(tb - amb) < SETTLE_K))):
            break
        flow, leak_a, leak_b = rates(ta, tb)
        ta += (-(flow + leak_a) / cap_a) * dt
        tb += ((flow - leak_b) / cap_b) * dt
        q_moved += flow * dt
        n += 1
        t = n * dt
        if t - n_rec * dt >= max(tau / FRAMES_PER_TAU, t / FRAMES_PER_EFOLD) - 1e-9:
            frames.append(_frame(t, ta, tb, *rates(ta, tb), q=q_moved))
            n_rec = n
    if n_rec != n:                  # always end on the true final state
        frames.append(_frame(n * dt, ta, tb, *rates(ta, tb), q=q_moved))

    t_eq = (cap_a * p["temp_a"] + cap_b * p["temp_b"]) / (cap_a + cap_b)
    last = frames[-1]
    q_a = cap_a * (last["temp_a"] - p["temp_a"])
    q_b = cap_b * (last["temp_b"] - p["temp_b"])
    notes = []
    if mat_a["id"] == "water":
        notes += _water_notes("A", [f["temp_a"] for f in frames])
    if mat_b["id"] == "water":
        notes += _water_notes("B", [f["temp_b"] for f in frames])

    def mat_info(m):
        return {"id": m["id"], "label": m["label"], "c": m["c"], "rho": m["rho"], "alpha": m.get("alpha")}

    # thermal expansion at the biggest temperature change of the run (a
    # heat leak later brings everything back to the room): dL = alpha L dT
    def swing(key, t0):
        return max((f[key] - t0 for f in frames), key=abs)
    dt_a, dt_b = swing("temp_a", p["temp_a"]), swing("temp_b", p["temp_b"])
    grow = []
    for lab, m_, dtx in (("A", mat_a, dt_a), ("B", mat_b, dt_b)):
        if m_.get("alpha"):
            grow.append({"label": "Block %s grows (at its biggest change, %+.1f K)" % (lab, dtx),
                         "value": round(m_["alpha"] * dtx * 1e6, 1),
                         "unit": "µm per metre (α = %.1f × 10⁻⁶ /K)" % (m_["alpha"] * 1e6)})
    expansion = {}
    for lab, m_, dtx in (("A", mat_a, dt_a), ("B", mat_b, dt_b)):
        if m_.get("alpha"):
            expansion.update({"alpha_%s" % lab: m_["alpha"], "dT_%s" % lab: round(dtx, 2),
                              "dL_%s (mm per m)" % lab: round(m_["alpha"] * dtx * 1000.0, 4)})

    return {
        "frames": frames,
        "notes": notes,
        "materials": {"a": mat_info(mat_a), "b": mat_info(mat_b)},
        "tau": round(tau, 3),
        "readouts": [
            {"label": "Block A (%s) now" % mat_a["label"], "value": last["temp_a"], "unit": "C"},
            {"label": "Block B (%s) now" % mat_b["label"], "value": last["temp_b"], "unit": "C"},
            {"label": "Predicted meeting point", "value": round(t_eq, 2), "unit": "C"},
            {"label": "Heat transferred A -> B", "value": round(q_moved / 1000.0, 3), "unit": "kJ"},
            {"label": "Heat capacity A (m x c)", "value": round(cap_a, 1), "unit": "J/K"},
            {"label": "Heat capacity B (m x c)", "value": round(cap_b, 1), "unit": "J/K"},
        ] + grow,
        "formula": [
            {"expr": "Q = m * c * dT",
             "values": {"c_A": int(ca), "dT_A": round(last["temp_a"] - p["temp_a"], 2),
                        "Q_A": round(q_a / 1000.0, 3),
                        "c_B": int(cb), "dT_B": round(last["temp_b"] - p["temp_b"], 2),
                        "Q_B": round(q_b / 1000.0, 3)}},
            {"expr": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)",
             "values": {"T_a": round(p["temp_a"], 1), "T_b": round(p["temp_b"], 1),
                        "T_eq": round(t_eq, 2)}},
            {"expr": "dL = alpha * L * dT", "values": expansion or {"note": "liquids: no length to grow"}},
        ],
    }
