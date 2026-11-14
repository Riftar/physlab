"""Shared machinery for every hall: knob specs and their validation, per-
student variants, the star rules, and what the browser may see.

A KNOB is one tunable setting of a station's object (a hatch height, bags
of salt, a spring's compression ...). Knobs use the sandbox's field kinds:

    number   a slider: min, max, step    -> the value is snapped to the step grid
    integer  whole numbers: min, max
    choice   one of a list of ids (chips)

validate_knobs() is the only way a value reaches the physics: unknown knobs,
wrong types, NaN, out-of-range numbers and unknown choices are refused with
a reason (like sandbox.validate); numbers are snapped to the slider grid so
the browser and the server always talk about the same setting.

A FACT is a fixed number on the station card (the flap's height, the canal's
volume). Facts with a "vary" range are the per-student VARIANT: each player
gets one of `steps` evenly spaced values per hall, seeded from the player's
id, so neighbours get different numbers but the same method works. Practice
mode (no player) uses the middle step - the nominal design.
"""

import hashlib
import math

VARIANT_STEPS = 5
NOMINAL = VARIANT_STEPS // 2
INSIGHT_POINTS = 5
STAR_POINTS = 10
GOLDEN_POINTS = 30
BLUEPRINT_AFTER = 2          # failed runs of a station before hint tier 3 (like quiz.REVEAL_AFTER)
STARS = ("works", "efficient", "mastery")


# ---------------------------------------------------------------- knob specs

def num(id_, label, lo, hi, default, unit, step):
    return {"id": id_, "kind": "number", "label": label, "min": lo, "max": hi, "default": default,
            "unit": unit, "step": step}


def integer(id_, label, lo, hi, default, unit=""):
    return {"id": id_, "kind": "integer", "label": label, "min": lo, "max": hi, "default": default,
            "unit": unit, "step": 1}


def choice(id_, label, items, default):
    """items: [{id, label, icon?, desc?, ...}] - the chips."""
    return {"id": id_, "kind": "choice", "label": label, "choices": items, "default": default}


def fact(id_, label, value, unit="", vary=None):
    """A number on the station card. vary=(lo, hi): this fact is the variant."""
    f = {"id": id_, "label": label, "value": value, "unit": unit}
    if vary:
        f["vary"] = [float(vary[0]), float(vary[1])]
    return f


def _is_num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def snap(knob, v):
    """Snap a number onto the knob's slider grid (min + n * step)."""
    n = round((v - knob["min"]) / knob["step"])
    return round(knob["min"] + n * knob["step"], 6)


def defaults(station):
    return {k["id"]: k["default"] for k in station["knobs"]}


def validate_knobs(station, raw):
    """-> (clean knobs, None) or (None, reason). Missing knobs take their default."""
    if not isinstance(raw, dict):
        return None, "the settings must be an object"
    specs = {k["id"]: k for k in station["knobs"]}
    for key in raw:
        if key not in specs:
            return None, "'%s' is not a setting of %s" % (str(key)[:40], station["title"])
    out = defaults(station)
    for kid, v in raw.items():
        k = specs[kid]
        if k["kind"] == "choice":
            ids = [c["id"] for c in k["choices"]]
            if not isinstance(v, str) or v not in ids:
                return None, "'%s' is not a choice for %s" % (str(v)[:40], k["label"].lower())
            out[kid] = v
        elif k["kind"] == "integer":
            if not _is_num(v) or float(v) != int(v):
                return None, "%s must be a whole number" % k["label"].lower()
            if not k["min"] <= v <= k["max"]:
                return None, "%s must be between %g and %g" % (k["label"].lower(), k["min"], k["max"])
            out[kid] = int(v)
        else:
            if not _is_num(v):
                return None, "%s must be a number" % k["label"].lower()
            if not k["min"] - 1e-9 <= v <= k["max"] + 1e-9:
                return None, "%s must be between %g and %g %s" % (k["label"].lower(), k["min"], k["max"], k["unit"])
            out[kid] = min(k["max"], max(k["min"], snap(k, float(v))))
    return out, None


# ---------------------------------------------------------------- variants

def variant_steps(hall, player_id):
    """{station_id: step} for a player (seeded, stable); NOMINAL for everyone
    in practice mode (player_id None)."""
    out = {}
    for st in hall["stations"]:
        if player_id is None:
            out[st["id"]] = NOMINAL
        else:
            h = hashlib.sha256(("%s|%s|%s" % (player_id, hall["id"], st["id"])).encode()).digest()
            out[st["id"]] = h[0] % VARIANT_STEPS
    return out


def facts_for(station, step):
    """The station's facts for one variant step: {id: value}."""
    out = {}
    for f in station["facts"]:
        if "vary" in f:
            lo, hi = f["vary"]
            out[f["id"]] = round(lo + (hi - lo) * step / (VARIANT_STEPS - 1), 6)
        else:
            out[f["id"]] = f["value"]
    return out


# ---------------------------------------------------------------- public views

def public_station(station, step):
    """What the browser may see: knobs, the card (with THIS player's facts),
    the goal and mastery texts - never windows, solutions or thresholds."""
    fx = facts_for(station, step)
    return {
        "id": station["id"], "title": station["title"], "hall": station["hall"],
        "scene": station["scene"], "intro": station["intro"], "goal": station["goal"],
        "hook": station["hook"], "mastery": station["mastery"]["text"],
        "knobs": station["knobs"],
        "facts": [dict(f, value=fx[f["id"]], vary=None) for f in station["facts"]],
        "fact_values": fx, "predict": station["predict"], "par": station["par"],
        "formulas": station["formulas"], "hints": len(station["hints"]) + 1,
        "score_rule": station.get("score_rule", ""), "variant_step": step,
        "learn": station.get("learn"),
    }


# ---------------------------------------------------------------- stars

def stars_for_run(station, result, history, hints_used):
    """Which stars THIS run earns (before removing the ones already held).
    history: earlier runs of this station by this player (oldest first,
    each {ok}); hints_used: set of hint tiers used BEFORE this run."""
    earned = []
    if not result["ok"]:
        return earned
    earned.append("works")
    runs_so_far = len(history) + 1
    if runs_so_far <= station["par"] and not any(t >= 2 for t in hints_used):
        earned.append("efficient")
    if result["mastery"] and 3 not in hints_used:
        earned.append("mastery")
    return earned


def insight(station, result, prediction, first_run):
    """A prediction scores only on the station's FIRST run ("call your
    shot") and only within the station's tolerance: tol (relative) or
    abs (absolute, default 0.02 in the station's unit - so predicting a
    tiny bounce isn't held to a tiny window)."""
    pr = station["predict"]
    if prediction is None or not first_run or result.get("predicted") is None:
        return False
    actual = result["predicted"]
    if pr["kind"] == "boolean":
        return bool(prediction) == bool(actual)
    if not _is_num(prediction):
        return False
    return abs(prediction - actual) <= max(pr["tol"] * abs(actual), pr.get("abs", 0.02))


def hall_progress(halls, stars):
    """Which halls are CLEARED (every station has the 'works' star) and which
    are UNLOCKED (the first hall, and every hall whose previous hall is
    cleared). halls: in order, playable ones with "stations", coming ones
    without; stars: {station_id: set of stars}. -> {hall_id: {cleared, unlocked}}"""
    out, prev_cleared = {}, True
    for h in halls:
        sts = h.get("stations") or []
        cleared = bool(sts) and all("works" in stars.get(s["id"], ()) for s in sts)
        out[h["id"]] = {"cleared": cleared, "unlocked": prev_cleared}
        prev_cleared = cleared
    return out


def hint_allowed(tier, failed_runs):
    if tier in (1, 2):
        return True
    return tier == 3 and failed_runs >= BLUEPRINT_AFTER


def fmt(x, nd=2):
    if isinstance(x, float):
        return ("%." + str(nd) + "f") % x
    return str(x)
