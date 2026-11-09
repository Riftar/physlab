"""Circuit lab (sandbox): any circuit built on a grid of connection dots.

Parts sit on the edges between neighbouring dots:
  wire / closed switch   0.01 ohm (short hook-up wire), open switch: no path
  lamp                   its hot resistance R = V_rated^2 / P_rated, and the
                         real filament model of the Electric Circuits topic
                         (temperature, light, colour) for ITS rating
  resistor               R
  battery                EMF E with internal resistance r, "+" at end b
                         (or a if flipped)

Solved by nodal analysis (Kirchhoff's current law at every dot). Every
part is a conductance G; a battery is its Norton equivalent - G = 1/r in
parallel with a current source E/r pushing towards "+". Each separate
piece of circuit gets its own ground, so unconnected parts just sit at 0 V.
A lamp hotter than tungsten's melting point BLOWS: it becomes an open
circuit and everything is solved again (one lamp at a time, hottest first).
"""

from . import circuits as lampphys

R_WIRE = 0.01
T_MELT = lampphys.T_MELT_W
LOOP = 4.0


def solve_network(n_nodes, elements, prefer=()):
    """elements: [(a, b, G, Is)] - conductance G between nodes a and b and a
    current source Is driving current from a to b (Norton). Returns node
    voltages (None for nodes that nothing touches). Each connected piece is
    grounded at the first node of `prefer` in it (e.g. a battery's "-"),
    else at its lowest-numbered node."""
    parent = list(range(n_nodes))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    used = set()
    for a, b, g, _ in elements:
        used.update((a, b))
        parent[find(a)] = find(b)
    ground = {}
    for i in [q for q in prefer if q in used] + sorted(used):   # one ground (0 V) per connected piece
        ground.setdefault(find(i), i)
    unknown = [i for i in sorted(used) if ground[find(i)] != i]
    idx = {node: k for k, node in enumerate(unknown)}
    n = len(unknown)
    A = [[0.0] * n for _ in range(n)]
    rhs = [0.0] * n
    for a, b, g, src in elements:
        ia, ib = idx.get(a), idx.get(b)
        if ia is not None:
            A[ia][ia] += g
            rhs[ia] -= src
        if ib is not None:
            A[ib][ib] += g
            rhs[ib] += src
        if ia is not None and ib is not None:
            A[ia][ib] -= g
            A[ib][ia] -= g
    x = _gauss(A, rhs)
    volts = [None] * n_nodes
    for node in used:
        volts[node] = 0.0
    for node, k in idx.items():
        volts[node] = x[k]
    return volts


def _gauss(A, b):
    """Gaussian elimination with partial pivoting (A is symmetric positive
    definite for these networks, so this is always well posed)."""
    n = len(b)
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(M[r][c]))
        M[c], M[p] = M[p], M[c]
        piv = M[c][c]
        if abs(piv) < 1e-15:
            continue
        for r in range(c + 1, n):
            f = M[r][c] / piv
            if f:
                for k in range(c, n + 1):
                    M[r][k] -= f * M[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        s = M[r][n] - sum(M[r][k] * x[k] for k in range(r + 1, n))
        x[r] = s / M[r][r] if abs(M[r][r]) > 1e-15 else 0.0
    return x


def solve(parts, cols, rows):
    """parts: [{kind, a: (c, r), b: (c, r), R | emf, r_int | v_rated, on, flip,
    label}]. Returns per-part results, node voltages and notes."""
    node = lambda p: p[1] * cols + p[0]
    blown = set()
    for _ in range(len(parts) + 1):
        elements, owner = [], []
        for i, p in enumerate(parts):
            a, b = node(p["a"]), node(p["b"])
            k = p["kind"]
            if k == "battery":
                neg, pos = (b, a) if p.get("flip") else (a, b)
                g = 1.0 / p["r_int"]
                elements.append((neg, pos, g, p["emf"] * g))
            elif k in ("wire", "switch"):
                if k == "switch" and not p.get("on", True):
                    continue
                elements.append((a, b, 1.0 / R_WIRE, 0.0))
            elif k in ("lamp", "resistor"):
                if i in blown:
                    continue
                elements.append((a, b, 1.0 / p["R"], 0.0))
            else:
                continue
            owner.append(i)
        minus = [node(p["b"] if p.get("flip") else p["a"]) for p in parts if p["kind"] == "battery"]
        volts = solve_network(cols * rows, elements, minus) if elements else [None] * (cols * rows)
        results = [_part_result(p, i, volts, node, i in blown) for i, p in enumerate(parts)]
        # the hottest lamp beyond tungsten's melting point blows, then solve again
        hot = [(r["filament_k"], i) for i, r in enumerate(results)
               if parts[i]["kind"] == "lamp" and i not in blown and r["filament_k"] >= T_MELT]
        if not hot:
            break
        blown.add(max(hot)[1])
    return {"parts": results, "volts": [None if v is None else round(v, 6) for v in volts],
            "blown": sorted(blown)}


def _part_result(p, i, volts, node, is_blown):
    va, vb = volts[node(p["a"])], volts[node(p["b"])]
    va, vb = va or 0.0, vb or 0.0
    k = p["kind"]
    out = {"i": i, "kind": k, "va": round(va, 6), "vb": round(vb, 6)}
    if k == "battery":
        neg, pos = (vb, va) if p.get("flip") else (va, vb)
        cur = (p["emf"] - (pos - neg)) / p["r_int"]          # inside: from "-" to "+"
        cur_ab = -cur if p.get("flip") else cur              # as current from a to b
        out.update({"current": round(cur_ab, 6), "terminal_v": round(pos - neg, 6),
                    "power_out": round(p["emf"] * cur - cur * cur * p["r_int"], 6),
                    "loss": round(cur * cur * p["r_int"], 6),
                    "short": abs(cur) * p["r_int"] > 0.8 * p["emf"]})
        return out
    if k in ("wire", "switch"):
        closed = not (k == "switch" and not p.get("on", True))
        cur = (va - vb) / R_WIRE if closed else 0.0
        out.update({"current": round(cur, 6), "power": round(cur * cur * R_WIRE, 6), "closed": closed})
        return out
    R = p["R"]
    cur = 0.0 if is_blown else (va - vb) / R
    out.update({"current": round(cur, 6), "voltage": round(va - vb, 6), "power": round(cur * cur * R, 6)})
    if k == "lamp":
        p_rated = p["v_rated"] ** 2 / R
        pw = cur * cur * R
        temp = lampphys.filament_temp(pw, p_rated)
        lm = lampphys.lumens(pw, temp)
        out.update({"filament_k": round(temp, 1), "lumens": round(lm, 4),
                    "brightness": round(lampphys.perceived(lm), 5), "color": lampphys.glow_color(temp),
                    "blown": is_blown,
                    "status": "blown" if is_blown else
                    "overvolted" if abs(va - vb) > 1.1 * p["v_rated"] else
                    "dark" if temp < 1000 else "ok"})
        if is_blown:
            out.update({"filament_k": round(lampphys.T_ROOM, 1), "lumens": 0.0, "brightness": 0.0})
    return out


def _closed_loop(parts, blown, i):
    """Is there a conducting path from one end of part i to the other
    through the REST of the circuit?"""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for j, p in enumerate(parts):
        if j == i or j in blown or (p["kind"] == "switch" and not p.get("on", True)):
            continue
        parent[find(tuple(p["a"]))] = find(tuple(p["b"]))
    return find(tuple(parts[i]["a"])) == find(tuple(parts[i]["b"]))


def run(parts, cols, rows):
    sol = solve(parts, cols, rows)
    res = sol["parts"]
    batteries = [r for r, p in zip(res, parts) if p["kind"] == "battery"]
    lamps = [(r, p) for r, p in zip(res, parts) if p["kind"] == "lamp"]
    notes, readouts = [], []
    for idx in sol["blown"]:
        notes.append("The %s blew! It got hotter than tungsten's melting point (3695 K) and broke, "
                     "so no current can pass through it any more." % parts[idx]["label"])
    if not batteries:
        notes.append("No battery yet - nothing can push the charges round. Add one from the parts box.")
    elif all(abs(r["current"]) < 1e-6 for r in res):
        if any(_closed_loop(parts, set(sol["blown"]), i) for i, p in enumerate(parts) if p["kind"] == "battery"):
            notes.append("The loop is complete, but no current flows: the batteries push against each other "
                         "and cancel out. Turn one round with the hand tool.")
        else:
            notes.append("No current anywhere: there is no complete loop from one end of a battery back to "
                         "the other (check for gaps, open switches%s)." % (" and the blown lamp" if sol["blown"] else ""))
    for r, p in zip(batteries, [p for p in parts if p["kind"] == "battery"]):
        if r["short"]:
            notes.append("SHORT CIRCUIT on the %s: a wire joins its ends with almost no resistance, so "
                         "%.1f A rushes through and %.0f W turns into heat INSIDE the battery (its own "
                         "resistance). Real wires and batteries get hot and drain fast - never do this "
                         "with real batteries!" % (p["label"], abs(r["current"]), r["loss"]))
    for r, p in lamps:
        if r["status"] == "overvolted":
            notes.append("The %s has %.1f V across it but is made for %.1f V - very bright, and it "
                         "won't last long." % (p["label"], abs(r["voltage"]), p["v_rated"]))
    formula = []
    bat_parts = [p for p in parts if p["kind"] == "battery"]
    if len(batteries) == 1 and abs(batteries[0]["current"]) > 1e-9:
        # one battery: whatever the network, it acts on the battery like ONE
        # resistor R = (terminal voltage) / I  (its equivalent resistance)
        r, p = batteries[0], bat_parts[0]
        i_abs = abs(r["current"])
        formula.append({"expr": "I = V / (R + r)",
                        "values": {"V": p["emf"], "R (whole circuit)": round(r["terminal_v"] / i_abs, 3),
                                   "r": p["r_int"], "I": round(i_abs, 4)}})
    lit = [(r, p) for r, p in lamps if not r["blown"] and abs(r["current"]) > 1e-9]
    if lit:
        r, p = max(lit, key=lambda rp: rp[0]["power"])
        formula.append({"expr": "P = I^2 * R_lamp",
                        "values": {"lamp": p["label"], "I": round(abs(r["current"]), 4), "R_lamp": round(p["R"], 2),
                                   "P": round(r["power"], 3)}})
        formula.append({"expr": "T^4 - T_room^4 ~ P",
                        "values": {"P/P_rated": round(r["power"] / (p["v_rated"] ** 2 / p["R"]), 3),
                                   "T": round(r["filament_k"]), "lm": round(r["lumens"], 2)}})
    total_out = sum(r["power_out"] for r in batteries)
    readouts.append({"label": "Batteries deliver", "value": round(total_out, 3), "unit": "W"})
    for r, p in lamps:
        readouts.append({"label": "%s (%s)" % (p["label"], "blown" if r["blown"] else
                                               "%.2f V, %.3f A" % (abs(r["voltage"]), abs(r["current"]))),
                         "value": round(r["power"], 3), "unit": "W"})
    for r, p in zip(batteries, [p for p in parts if p["kind"] == "battery"]):
        readouts.append({"label": p["label"] + " current", "value": round(abs(r["current"]), 4),
                         "unit": "A (terminal %.2f V)" % r["terminal_v"]})
    return {"frames": [{"t": 0.0}, {"t": LOOP}], "notes": notes, "readouts": readouts,
            "viz": {"cols": cols, "rows": rows, "parts": res, "volts": sol["volts"],
                    "specs": [{k: p[k] for k in ("kind", "a", "b", "label", "short") if k in p} |
                              {"on": p.get("on", True), "flip": p.get("flip", False), "id": p.get("id")}
                              for p in parts]},
            "formula": formula}
