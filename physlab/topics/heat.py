"""Heat transfer: two blocks in thermal contact, optional leak to room.

Block-to-block conductance G = 2 W/K, ambient leak = params['loss'] W/K.
With loss = 0 the pair converges exactly to the energy-weighted mean
temperature (asserted in tests).
"""

DT = 0.1
RECORD_EVERY = 20      # one frame per 2 s
MAX_T = 1200.0
G_CONTACT = 20.0


def _c(material_id):
    from .. import MATERIALS
    for m in MATERIALS:
        if m["id"] == material_id:
            return m["c"]
    return None


def run(p):
    ca, cb = _c(p["material_a"]), _c(p["material_b"])
    ta, tb, t = p["temp_a"], p["temp_b"], 0.0
    cap_a, cap_b = p["mass_a"] * ca, p["mass_b"] * cb
    frames = [{"t": 0.0, "temp_a": round(ta, 3), "temp_b": round(tb, 3)}]
    q_moved = 0.0
    while t < MAX_T:
        flow = G_CONTACT * (ta - tb)          # W, a -> b when positive
        leak_a = p["loss"] * (ta - p["ambient"])
        leak_b = p["loss"] * (tb - p["ambient"])
        ta += (-(flow + leak_a) / cap_a) * DT
        tb += ((flow - leak_b) / cap_b) * DT
        q_moved += flow * DT
        t += DT
        if abs(round(t / DT) % RECORD_EVERY) < 1e-9:
            frames.append({"t": round(t, 2), "temp_a": round(ta, 3), "temp_b": round(tb, 3)})
        if abs(flow) < 1e-4 and abs(leak_a) + abs(leak_b) < 1e-4:
            break
    t_eq = (cap_a * p["temp_a"] + cap_b * p["temp_b"]) / (cap_a + cap_b)
    return {
        "frames": frames,
        "readouts": [
            {"label": "Block A now", "value": frames[-1]["temp_a"], "unit": "C"},
            {"label": "Block B now", "value": frames[-1]["temp_b"], "unit": "C"},
            {"label": "Predicted meeting point", "value": round(t_eq, 2), "unit": "C"},
            {"label": "Heat transferred", "value": round(q_moved / 1000.0, 3), "unit": "kJ"},
        ],
        "formula": [
            {"expr": "Q = m * c * dT",
             "values": {"m": round(p["mass_a"], 2), "c": int(ca),
                        "dT": round(frames[-1]["temp_a"] - p["temp_a"], 2)}},
            {"expr": "T_eq = (m_a c_a T_a + m_b c_b T_b) / (m_a c_a + m_b c_b)",
             "values": {"T_a": round(p["temp_a"], 1), "T_b": round(p["temp_b"], 1),
                        "T_eq": round(t_eq, 2)}},
        ],
    }
