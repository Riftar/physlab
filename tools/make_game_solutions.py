"""Compute and save the CORRECT settings for every Machine Works station.

    python3 tools/make_game_solutions.py                 # every hall: physlab/game/data/<hall>.json
                                                         #   + docs/game/hall<n>-solutions.md
    python3 tools/make_game_solutions.py foundry         # one hall
    python3 tools/make_game_solutions.py --check [hall]  # exit 1 if any file is out of date

For each station and each of its per-student variant steps this runs the
station's own physics (physlab/game/bounce_factory.py) over its knobs to
find the success window, then saves:

  solution           a robust working setting (the middle of the window) -
                     the hint-tier-3 "Blueprint" and the QA reference
  window             where it works (per choice, for choice knobs)
  mastery_solution   a setting that also earns the mastery star
  thresholds         the variant's mastery thresholds (1.1 lowest drop,
                     1.3 speed-run time) and score references (1.1 the
                     lowest drop that works, 1.2 the cheapest delivery, 1.3
                     the fastest safe run) that the runtime reads
  score_solution     a setting with the best score found (1000 = the best
                     possible for the variant; 1.4's best is searched at 45°)
  lab / game         deep links: the related lab simulations with the
                     solution's numbers, and the game station preloaded
                     with the solution (practice mode, this variant)

Deterministic: same physics -> byte-identical files (tests/test_game.py
regenerates and compares).
"""

import json
import math
import os
import sys
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from physlab.game import bounce_factory as BF  # noqa: E402
from physlab.game import foundry as FD  # noqa: E402
from physlab.game import mill as ML  # noqa: E402
from physlab.game.common import VARIANT_STEPS, NOMINAL, facts_for, validate_knobs  # noqa: E402

BASE = "http://127.0.0.1:8600/"          # `python3 -m physlab.server 8600`: the links in the .md open the running app


def grid(lo, hi, step):
    n = int(round((hi - lo) / step))
    return [round(lo + i * step, 6) for i in range(n + 1)]


def spans(xs, oks):
    out, cur = [], None
    for x, ok in zip(xs, oks):
        if ok and cur is None:
            cur = [x, x]
        elif ok:
            cur[1] = x
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out


def mid(span, step):
    return round(span[0] + round((span[1] - span[0]) / 2.0 / step) * step, 6)


def game_link(station_id, step, knobs, hall="bounce"):
    return "#/game/%s/%s?practice=1&v=%d&k=%s" % (hall, station_id, step,
                                                  quote(json.dumps(knobs, separators=(",", ":"), sort_keys=True)))


def check_knobs(st, knobs):
    """A saved setting must be exactly what the sliders can show."""
    clean, err = validate_knobs(st, knobs)
    assert err is None and clean == knobs, (st["id"], knobs, err)


# ---------------------------------------------------------------- per station

def solve_1_1(st, fx):
    hs = grid(1.0, 4.0, 0.05)
    windows = {}
    for pad in [p["id"] for p in BF.PADS]:
        top = BF.run_bounce_flap({"hatch": hs[-1], "pad": pad}, fx)
        if not top["ok"] and top["metric"] + 1e-9 < fx["flap"]:
            windows[pad] = []           # the bounce grows with the drop: not even the top of the rail gets there
            continue
        oks = [BF.run_bounce_flap({"hatch": h, "pad": pad}, fx)["ok"] for h in hs]
        windows[pad] = spans(hs, oks)
    steel = windows["steel_plate"][0]
    sol = {"hatch": mid(steel, 0.05), "pad": "steel_plate"}
    low = steel[0]
    res = BF.run_bounce_flap(sol, fx)
    why = ("on the steel pad e = 0.85, so h1 = 0.85² × %.2f = %.2f m without air; the air takes a little, it "
           "reaches %.2f m - above the flap (%.2f m), and its top stays under the duct (%.2f m)."
           % (sol["hatch"], 0.7225 * sol["hatch"], res["metric"], fx["flap"], fx["flap"] + fx["duct_gap"]))
    return {"solution": sol, "window": windows, "why": why,
            "thresholds": {"low_drop": round(low + 0.15, 2), "h_low": low},
            "mastery_solution": {"hatch": low, "pad": "steel_plate"},
            "score_solution": {"hatch": low, "pad": "steel_plate"}}


def solve_1_2(st, fx):
    need = BF.min_bags(fx["litres"])
    bags = list(range(0, 21))
    oks = [BF.floats_in(b, fx["litres"]) for b in bags]          # = run_salt_canal(...)["ok"] (asserted there)
    sol = {"bags": min(20, need + 1)}
    s, liquid = BF.brine(need, fx["litres"])
    why = ("%d bags make %.0f g of salt per litre, salt water of %.1f kg/m³ - denser than the rubber ball "
           "(1149), so it floats. (The fewest that work: %d.)" % (sol["bags"], sol["bags"] * 1000 / fx["litres"],
                                                                   BF.brine(sol["bags"], fx["litres"])[1]["rho"],
                                                                   need))
    costs = {b: BF.run_salt_canal({"bags": b}, fx)["viz"]["t_arrive"] for b in bags if oks[b]}
    costs = {b: BF.delivery_cost(b, t) for b, t in costs.items()}
    best = min(costs, key=lambda b: (costs[b], b))
    return {"solution": sol, "window": spans(bags, oks), "why": why,
            "thresholds": {"min_bags": need, "cost_min": round(costs[best], 4)},
            "mastery_solution": {"bags": need}, "score_solution": {"bags": best}}


def _camel_ok(h, fx):
    return BF.run_camel_hump({"hump": h}, fx)


def solve_1_3(st, fx):
    hs = grid(0.2, 1.6, 0.01)
    # the window is one piece: flies below it, rolls back above it -> bisect both edges
    inside = 1.0
    assert _camel_ok(inside, fx)["ok"], fx

    def edge(lo, hi, ok_at_hi):        # lo/hi are grid indices; return the first index where ok == ok_at_hi
        while hi - lo > 1:
            m = (lo + hi) // 2
            if _camel_ok(hs[m], fx)["ok"] == ok_at_hi:
                hi = m
            else:
                lo = m
        return hi
    i_in = hs.index(inside)
    first_ok = edge(0, i_in, True)
    # last ok: bisect for the first failing index above the inside point
    lo, hi = i_in, len(hs) - 1
    while hi - lo > 1:
        m = (lo + hi) // 2
        if _camel_ok(hs[m], fx)["ok"]:
            lo = m
        else:
            hi = m
    last_ok = lo
    window = [hs[first_ok], hs[last_ok]]
    fastest = _camel_ok(hs[first_ok], fx)
    t_best = fastest["viz"]["t_goal"]
    sol = {"hump": mid(window, 0.01)}
    res = _camel_ok(sol["hump"], fx)
    why = ("it crosses the top at %.2f m/s - under the √(g·R) = 2.80 m/s limit, so the track holds it - and it "
           "still has enough energy to climb over. (It works from %.2f to %.2f m.)" % (res["metric"], window[0],
                                                                                       window[1]))
    return {"solution": sol, "window": [window], "why": why,
            "thresholds": {"speed_run": round(t_best + 0.06, 2), "t_best": t_best},
            "mastery_solution": {"hump": hs[first_ok]}, "score_solution": {"hump": hs[first_ok]}}


def solve_1_4(st, fx):
    xs = grid(2.0, 20.0, 0.1)
    runs = [BF.run_spring_cannon({"compression": x, "angle": 45.0}, fx) for x in xs]
    direct = spans(xs, [r["ok"] and not r["mastery"] for r in runs])
    bank = spans(xs, [r["ok"] and r["mastery"] for r in runs])
    best = max(direct, key=lambda s: s[1] - s[0])
    sol = {"compression": mid(best, 0.1), "angle": 45.0}
    res = BF.run_spring_cannon(sol, fx)
    why = ("at 45° the box (%.2f m out, %.2f m up) needs about %.2f m/s; ½kx² = ½mv² + mgx·sin45° gives "
           "x ≈ %.1f cm. (Direct shots work from %.1f to %.1f cm at 45°.)"
           % (fx["dx"], fx["dy"], res["metric"], sol["compression"], best[0], best[1]))
    ms = {"compression": mid(max(bank, key=lambda s: s[1] - s[0]), 0.1), "angle": 45.0} if bank else None
    top = max(range(len(xs)), key=lambda i: (runs[i]["score"], -i))
    return {"solution": sol, "window": {"45": {"direct": direct, "bank": bank}}, "why": why, "thresholds": {},
            "mastery_solution": ms, "score_solution": {"compression": xs[top], "angle": 45.0}}


# ---------------------------------------------------------------- Hall 2: the Foundry

def solve_2_1(st, fx):
    ws = grid(0.0, 0.50, 0.01)
    runs = {w: FD.run_hot_ring({"target": "ring", "water": w}, fx) for w in ws}
    windows = {"ring": spans(ws, [runs[w]["ok"] for w in ws])}
    for tgt in ("ball", "both"):          # more water = hotter: if the most water fails, nothing works
        windows[tgt] = spans(ws, [FD.run_hot_ring({"target": tgt, "water": w}, fx)["ok"] for w in ws]) \
            if FD.run_hot_ring({"target": tgt, "water": ws[-1]}, fx)["ok"] else []
    ok = [w for w in ws if runs[w]["ok"]]
    w_min = ok[0]
    costs = {w: FD.heat_cost(w, runs[w]["viz"]["t_drop"]) for w in ok}
    best = min(ok, key=lambda w: (costs[w], w))
    sol = {"target": "ring", "water": mid(windows["ring"][0], 0.01)}
    r = runs[sol["water"]]
    why = ("pour it on the RING: %.2f kg of 95 °C water heats the 0.30 kg aluminium ring to %.0f °C (it needs %.0f °C), "
           "and the hole grows past the %.0f µm gap after %.0f s." % (sol["water"], r["metric"], r["viz"]["T_need"],
                                                                    fx["gap_um"], r["viz"]["t_drop"]))
    return {"solution": sol, "window": windows, "why": why,
            "thresholds": {"water_min": w_min, "thrifty": round(w_min + 0.02, 2), "cost_min": round(costs[best], 4)},
            "mastery_solution": {"target": "ring", "water": w_min}, "score_solution": {"target": "ring", "water": best}}


def solve_2_2(st, fx):
    rs = grid(0.0, 50.0, 0.5)
    windows, working = {}, []
    for b in FD.BATTERIES:
        res = [(r, FD.run_trapdoor({"battery": b["id"], "R": r}, fx)) for r in rs]
        windows[b["id"]] = spans(rs, [x[1]["ok"] for x in res])
        working += [(b["id"], r, x) for r, x in res if x["ok"]]
    p_min = min(x["viz"]["p_battery"] for _, _, x in working)
    best = min(working, key=lambda w: (w[2]["viz"]["p_battery"], w[1]))
    cool = [w for w in working if w[2]["mastery"] and w[0] == "lantern"] or [w for w in working if w[2]["mastery"]]
    lw = windows["lantern"][0]
    sol = {"battery": "lantern", "R": mid(lw, 0.5)}
    r = FD.run_trapdoor(sol, fx)
    why = ("the 6 V lantern battery with %.1f Ω: I = 6 / (%.1f + 0.3 + %.1f + 0.11) = %.2f A - above the 0.30 A the latch "
           "needs and below the 1 A fuse." % (sol["R"], sol["R"], fx["coil_ohm"], r["metric"]))
    mc = cool[len(cool) // 2]
    return {"solution": sol, "window": windows, "why": why, "thresholds": {"p_min": p_min},
            "mastery_solution": {"battery": mc[0], "R": mc[1]}, "score_solution": {"battery": best[0], "R": best[1]}}


def solve_2_3(st, fx):
    ds = grid(2.0, 10.0, 0.1)
    runs = [(d, FD.run_hydraulic_gate({"d2": d}, fx)) for d in ds]
    win = spans(ds, [r["ok"] for _, r in runs])
    ok = [(d, r) for d, r in runs if r["ok"]]
    t_best = min(r["viz"]["t_down"] for _, r in ok)
    fastest = min(ok, key=lambda x: (x[1]["viz"]["t_down"], -x[0]))
    high = [d for d, r in ok if r["mastery"]]
    sol = {"d2": mid(win[0], 0.1)}
    r = FD.run_hydraulic_gate(sol, fx)
    why = ("a %.1f cm big piston: it pushes %.1f times harder than the small one (enough for the gate), and moves %.1f "
           "times less, so the gate rises %.1f cm." % (sol["d2"], r["viz"]["ratio"], r["viz"]["ratio"], r["viz"]["lift_cm"]))
    return {"solution": sol, "window": win, "why": why, "thresholds": {"t_best": t_best},
            "mastery_solution": {"d2": high[len(high) // 2]}, "score_solution": {"d2": fastest[0]}}


def solve_2_4(st, fx):
    windows, best = {}, None
    for L in (0.6, 0.8, 1.0, 1.2, 1.5, 2.0):
        c = 1 - fx["ladle"] ** 2 / (4 * L * FD.DROP)              # the no-air aim: L (1 - cos th) = D^2 / 4H
        guess = math.degrees(math.acos(max(-1.0, min(1.0, c))))
        ths = [float(a) for a in range(max(10, int(guess) - 8), min(90, int(guess) + 9))]
        res = [(a, FD.run_magnet_swing({"length": L, "angle": a}, fx)) for a in ths]
        windows["L=%g" % L] = spans(ths, [x[1]["ok"] for x in res])
        for a, x in res:
            if x["ok"] and (best is None or x["score"] > best[2]):
                best = (L, a, x["score"])
    w1 = windows["L=1"][0]
    sol = {"length": 1.0, "angle": mid(w1, 1.0)}
    r = FD.run_magnet_swing(sol, fx)
    gw = [w for w in windows["L=1.5"]]
    why = ("a 1.0 m cable from %.0f°: at the bottom v = √(2·9.81·1.0·(1 − cos %.0f°)) ≈ %.2f m/s, and it flies "
           "D = 2√(L(1 − cos θ)·1.2) ≈ %.2f m; the magnet carries %.1f N (it holds 12)." % (
               sol["angle"], sol["angle"], r["viz"]["speed"], r["viz"]["land"], r["metric"]))
    return {"solution": sol, "window": windows, "why": why, "thresholds": {},
            "mastery_solution": {"length": 1.5, "angle": mid(gw[0], 1.0)} if gw else None,
            "score_solution": {"length": best[0], "angle": best[1]}}


# ---------------------------------------------------------------- Hall 3: Millbrook Mill

def solve_3_1(st, fx):
    windows, working = {}, []
    for it in ML.DROP_ITEMS:                  # the equilibrium decides (the runs only add the bobbing on the way)
        oks = []
        for n in range(0, 41):
            c, lv = ML.well_centre_cm({"item": it["id"], "count": n}, fx)
            ok = lv <= ML.WELL_H * 100.0 and abs(c - ML.PADDLE * 100.0) <= ML.PADDLE_BAND * 100.0 + 1e-9
            oks.append(ok)
            if ok:
                working.append((ML.well_cost(c, n), it["id"], n))
        windows[it["id"]] = spans(list(range(0, 41)), oks)
    fewest = ML.fewest_drops(fx)
    cost_min, b_item, b_n = min(working)
    widest = max((k for k in windows if windows[k]), key=lambda k: (windows[k][0][1] - windows[k][0][0], k))
    sol = {"item": widest, "count": int(mid(windows[widest][0], 1))}
    few = next((it["id"], w[0][0]) for it in ML.DROP_ITEMS for w in [windows[it["id"]]] if w and w[0][0] == fewest)
    c, _ = ML.well_centre_cm(sol, fx)
    why = ("%d %s: they push %.0f cm³ of water up the %.1f cm² well, so it rises %.1f cm and the ball's centre floats "
           "at %.1f cm - inside the paddles' 45 ± 2.5 cm." % (
               sol["count"], ML.ITEM[widest]["label"].lower(), ML.displaced_cm3(widest, sol["count"]), ML.WELL_CM2,
               ML.displaced_cm3(widest, sol["count"]) / ML.WELL_CM2, c))
    return {"solution": sol, "window": windows, "why": why,
            "thresholds": {"fewest": int(fewest), "cost_min": round(cost_min, 4)},
            "mastery_solution": {"item": few[0], "count": int(few[1])},
            "score_solution": {"item": b_item, "count": int(b_n)}}


def solve_3_2(st, fx):
    ws = grid(0.0, 20.0, 0.5)
    lands = {w: ML.fly(w)["x"] for w in ws}
    lo, hi = fx["cart"] - ML.CART_HALF + ML.BALL_R, fx["cart"] + ML.CART_HALF - ML.BALL_R
    oks = [lo <= lands[w] <= hi for w in ws]
    win = spans(ws, oks)
    w_lo = win[0][0]
    raws = {w: ML.fan_raw(lands[w], fx["cart"], w, w_lo) for w, ok in zip(ws, oks) if ok}
    best = max(raws, key=lambda w: (raws[w], -w))
    sol = {"wind": mid(win[0], 0.5)}
    why = ("a %.1f m/s fan: with no fan it lands %.2f m out; the wind rushing past the ball pushes it another %.2f m "
           "into the cart at %.2f m." % (sol["wind"], lands[0.0], lands[sol["wind"]] - lands[0.0], fx["cart"]))
    return {"solution": sol, "window": win, "why": why,
            "thresholds": {"w_lo": w_lo, "breeze": round(w_lo + 1.0, 2), "raw_best": round(raws[best], 6)},
            "mastery_solution": {"wind": w_lo}, "score_solution": {"wind": best}}


def solve_3_3(st, fx):
    ds = grid(5.0, 95.0, 0.5)
    lights = {d: ML.gate_light(d, fx["bench"]) for d in ds}
    oks = [lights[d]["share"] >= ML.LG_ARM for d in ds]
    win = spans(ds, oks)
    ok = [d for d, o in zip(ds, oks) if o]
    sharp = min(ok, key=lambda d: (abs(lights[d]["defocus"]), d))
    sol = {"d_o": mid(win[0], 0.5)}
    d_i = fx["bench"] - sharp
    why = ("the lens %.1f cm from the lamp: the sharp image forms near the cell %.1f cm below the lens, and it is only "
           "%.1f cm wide (2 cm × d_i/d_o) - the other sharp position (%.1f cm) makes a %.1f cm image and wastes the "
           "light." % (sol["d_o"], d_i, 2.0 * d_i / sharp, d_i, 2.0 * sharp / d_i))
    return {"solution": sol, "window": win, "why": why,
            "thresholds": {"defocus_min": round(abs(lights[sharp]["defocus"]), 6)},
            "mastery_solution": {"d_o": sharp}, "score_solution": {"d_o": sharp}}


def solve_3_4(st, fx):
    best, windows, feather = None, {}, {}
    for b in grid(0.20, 1.00, 0.05):
        w_bal = 0.26 * fx["arm"] / b - ML.BUCKET_M           # the water that balances (no friction)
        if w_bal > 2.0:
            continue
        start = max(0.0, round(math.floor(w_bal * 100) / 100.0, 2))
        ws, oks = [], []
        for i in range(0, 201):                               # just past balance: walk up until it's flung
            w = round(start + 0.01 * i, 2)
            if w > 2.0:
                break
            r = ML.run_mill_hoist({"hook": b, "water": w}, fx)
            ws.append(w)
            oks.append(r["ok"])
            if r["ok"]:
                cost = ML.hoist_cost(r["viz"]["t_up"], r["viz"]["speed"])
                if best is None or cost < best[0] - 1e-12:
                    best = (cost, b, w)
                if r["mastery"]:
                    feather.setdefault(b, []).append(w)
            elif any(oks):
                break
        windows["b=%g" % b] = spans(ws, oks)
    shown = {k: v for k, v in windows.items() if k in ("b=0.3", "b=0.5", "b=0.7", "b=1")}
    sol = {"hook": 0.5, "water": mid(windows["b=0.5"][0], 0.01)}
    fw = feather.get(0.5) or next(v for v in feather.values())
    fb = 0.5 if 0.5 in feather else next(k for k in feather)
    r = ML.run_mill_hoist(sol, fx)
    why = ("the bucket at 0.5 m with %.2f L: balance needs %.2f L (0.26 kg × %.2f m = (0.20 kg + water) × 0.5 m), a "
           "little more turns the beam; the scoop arrives at %.2f m/s after %.1f s." % (
               sol["water"], 0.26 * fx["arm"] / 0.5 - ML.BUCKET_M, fx["arm"], r["viz"]["speed"], r["viz"]["t_up"]))
    return {"solution": sol, "window": shown, "why": why, "thresholds": {"cost_min": round(best[0], 4)},
            "mastery_solution": {"hook": fb, "water": fw[len(fw) // 2]},
            "score_solution": {"hook": best[1], "water": best[2]}}


SOLVERS = {"1.1": solve_1_1, "1.2": solve_1_2, "1.3": solve_1_3, "1.4": solve_1_4,
           "2.1": solve_2_1, "2.2": solve_2_2, "2.3": solve_2_3, "2.4": solve_2_4,
           "3.1": solve_3_1, "3.2": solve_3_2, "3.3": solve_3_3, "3.4": solve_3_4}
HALLS = {"bounce": {"mod": BF, "md": "hall1-solutions.md", "title": "Hall 1 - The Bounce Factory"},
         "foundry": {"mod": FD, "md": "hall2-solutions.md", "title": "Hall 2 - The Foundry"},
         "mill": {"mod": ML, "md": "hall3-solutions.md", "title": "Hall 3 - Millbrook Mill"}}


def solve_variant(job):
    """One (station, variant step): find and check everything (runs in a worker process)."""
    hall, sid, step = job
    mod = HALLS[hall]["mod"]
    st = mod.BY_ID[sid]
    fx = facts_for(st, step)
    d = SOLVERS[st["id"]](st, fx)
    check_knobs(st, d["solution"])
    res = st["run"](d["solution"], fx, d["thresholds"])
    assert res["ok"], (st["id"], step, d["solution"], res["reason"])
    if d.get("mastery_solution"):
        check_knobs(st, d["mastery_solution"])
        mres = st["run"](d["mastery_solution"], fx, d["thresholds"])
        assert mres["ok"] and mres["mastery"], (st["id"], step, d["mastery_solution"], mres["reason"])
    d.update({"step": step, "facts": fx, "metric": res["metric"], "unit": res["unit"],
              "lab": res["lab"], "game": game_link(st["id"], step, d["solution"], hall)})
    d["score"] = res["score"]
    if d.get("mastery_solution"):
        d["game_mastery"] = game_link(st["id"], step, d["mastery_solution"], hall)
    check_knobs(st, d["score_solution"])
    top = st["run"](d["score_solution"], fx, d["thresholds"])
    assert top["ok"], (st["id"], step, d["score_solution"])
    d["best_score"] = top["score"]
    d["game_best"] = game_link(st["id"], step, d["score_solution"], hall)
    return hall, sid, step, d


def build(halls, workers=None):
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(h, st["id"], step) for h in halls for st in HALLS[h]["mod"].STATIONS for step in range(VARIANT_STEPS)]
    with ProcessPoolExecutor(max_workers=workers or min(8, os.cpu_count() or 1)) as ex:
        done = list(ex.map(solve_variant, jobs))
    out = {}
    for h in halls:
        mod = HALLS[h]["mod"]
        data = {"hall": h, "generated_by": "tools/make_game_solutions.py", "variant_steps": VARIANT_STEPS,
                "nominal": NOMINAL, "stations": {}}
        for st in mod.STATIONS:
            vs = [d for hh, sid, step, d in sorted(done, key=lambda r: r[2]) if hh == h and sid == st["id"]]
            data["stations"][st["id"]] = {"title": st["title"], "variants": vs}
        out[h] = data
    return out


def markdown(data):
    h = HALLS[data["hall"]]
    L = ["# %s: correct settings and deep links" % h["title"],
         "",
         "Generated by `python3 tools/make_game_solutions.py` from the stations' own physics "
         "(`physlab/game/%s.py`). Do not edit by hand: the tests fail when this file "
         "is out of date." % os.path.basename(h["mod"].__file__)[:-3],
         "",
         "Start the app with `python3 -m physlab.server 8600`, then the links below open it. Game links open the "
         "station in **practice mode** (nothing is recorded) with the given variant `v` (0-4; 2 = the nominal "
         "design) and the settings preloaded - press **Test station**. Lab links open the related simulation with "
         "the same numbers. (In the JSON file the same links are stored without the host.)",
         ""]
    for sid, s in data["stations"].items():
        L += ["## %s %s" % (sid, s["title"]), "",
              "| v | variant fact | correct setting | result | works for | mastery setting | top-score setting | game | lab |",
              "|---|---|---|---|---|---|---|---|---|"]
        st = h["mod"].BY_ID[sid]
        vary = [f for f in st["facts"] if "vary" in f][0]
        for d in s["variants"]:
            win = d["window"]
            if isinstance(win, dict) and "45" in win:
                wtxt = "45°: direct %s, bank %s" % (
                    ", ".join("%g-%g cm" % tuple(w) for w in win["45"]["direct"]),
                    ", ".join("%g-%g cm" % tuple(w) for w in win["45"]["bank"]) or "-")
            elif isinstance(win, dict):
                wtxt = "; ".join("%s %s" % (k, ", ".join("%g-%g" % tuple(w) for w in v) or "none")
                                 for k, v in win.items())
            else:
                wtxt = ", ".join("%g-%g" % tuple(w) for w in win)
            knobs = ", ".join("%s = %s" % kv for kv in d["solution"].items())
            ms = ", ".join("%s = %s" % kv for kv in (d.get("mastery_solution") or {}).items()) or "-"
            best = "%s -> **%d**" % (", ".join("%s = %s" % kv for kv in d["score_solution"].items()), d["best_score"])
            labs = " · ".join("[%s](%s%s)" % (l["title"].split(":")[0], BASE, l["route"]) for l in d["lab"])
            L.append("| %d%s | %s = %g %s | %s | %s %s | %s | %s | %s | [play](%s%s) | %s |" % (
                d["step"], " (nominal)" if d["step"] == data["nominal"] else "", vary["label"].lower(),
                d["facts"][vary["id"]], vary["unit"], knobs,
                ("%g" % d["metric"]) if isinstance(d["metric"], (int, float)) and not isinstance(d["metric"], bool)
                else d["metric"], d["unit"], wtxt, ms, best, BASE, d["game"], labs))
        L.append("")
    return "\n".join(L) + "\n"


def outputs(hall):
    mod = HALLS[hall]["mod"]
    return mod.DATA, os.path.join(ROOT, "docs", "game", HALLS[hall]["md"])


def main(argv):
    halls = [a for a in argv if not a.startswith("--")] or list(HALLS)
    for h in halls:
        if h not in HALLS:
            print("unknown hall:", h)
            return 2
    built = build(halls)
    files = []
    for h in halls:
        js_path, md_path = outputs(h)
        files += [(js_path, json.dumps(built[h], indent=1, sort_keys=True, ensure_ascii=False) + "\n"),
                  (md_path, markdown(built[h]))]
    if "--check" in argv:
        stale = [p for p, body in files if not os.path.exists(p) or open(p, encoding="utf8").read() != body]
        if stale:
            print("out of date:", stale)
            return 1
        print("up to date")
        return 0
    for p, body in files:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf8") as f:
            f.write(body)
        print("wrote", p)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
