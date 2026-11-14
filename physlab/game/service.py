"""The game's API logic (physlab/server.py routes /api/game* here).

    catalog(player)          halls (playable + coming), stars, score
    hall_view(id, player, v) layout + every station's public card for THIS
                             player's variant, progress, last settings
    run(body)                validate -> run (test: one station, machine: A ->
                             B) -> judge -> stars/points (recorded only for a
                             player; practice mode records nothing)
    hint(body)               tier 1-2 any time, tier 3 (the Blueprint) after 2
                             failed runs - and never in practice mode

Errors are raised as GameError(message, http_code).
"""

import copy
import json
from collections import OrderedDict

from . import BY_ID, COMING, HALLS, HALL_MODULES, STATIONS, locks_on
from .common import (NOMINAL, VARIANT_STEPS, facts_for, hall_progress, hint_allowed, insight, public_station,
                     stars_for_run, variant_steps, validate_knobs)

ALL_HALLS = HALLS + COMING            # the map order: each hall opens when the one before it is cleared
from .db import GameDB


class GameError(Exception):
    def __init__(self, msg, code=400):
        Exception.__init__(self, msg)
        self.code = code


# ---------------------------------------------------------------- a small cache of station runs
# (runs are deterministic: same station, knobs and variant -> same result)
_CACHE, _CACHE_MAX = OrderedDict(), 256


def run_cached(station, knobs, step):
    key = json.dumps([station["id"], knobs, step], sort_keys=True)
    if key in _CACHE:
        _CACHE.move_to_end(key)
        return copy.deepcopy(_CACHE[key])
    mod = HALL_MODULES[station["hall"]]
    res = mod.run_station(station, knobs, step)
    _CACHE[key] = res
    if len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)
    return copy.deepcopy(res)


def _open(db):
    db = db or GameDB()
    old = db.unscored()
    if old:                   # runs from before scores existed: the physics is deterministic and the
        done = []             # variant comes from the player id, so the score can be recomputed exactly
        for rid, pid, sid, knobs in old:
            st = STATIONS.get(sid)
            if not st:
                continue
            step = variant_steps(BY_ID[st["hall"]], pid)[sid]
            done.append((rid, run_cached(st, knobs, step)["score"]))
        db.set_scores(done)
    return db


def _player(db, pid):
    if pid is None:
        return None
    if not isinstance(pid, str):
        raise GameError("unknown player", 404)
    p = db.player(pid)
    if not p:
        raise GameError("unknown player", 404)
    return p


def _practice_step(v):
    if v is None:
        return NOMINAL
    try:
        v = int(v)
    except (TypeError, ValueError):
        raise GameError("v must be a variant step 0-%d" % (VARIANT_STEPS - 1))
    if not 0 <= v < VARIANT_STEPS:
        raise GameError("v must be a variant step 0-%d" % (VARIANT_STEPS - 1))
    return v


def _steps(hall, player, v):
    if player:
        return variant_steps(hall, player["id"])
    step = _practice_step(v)
    return {st["id"]: step for st in hall["stations"]}


# ---------------------------------------------------------------- reads

def _progress(db, player):
    """{hall_id: {cleared, unlocked}} - everything is open in practice mode, and for everyone while the
    classroom locks are off (testing)."""
    if not player:
        return {h["id"]: {"cleared": False, "unlocked": True} for h in ALL_HALLS}
    prog = hall_progress(ALL_HALLS, db.stars(player["id"]))
    if not locks_on():
        for h in ALL_HALLS:
            prog[h["id"]]["unlocked"] = prog[h["id"]]["unlocked"] or bool(h.get("stations"))
    return prog


def _requires(i):
    return ("Clear every station of %s to open it." % ALL_HALLS[i - 1]["title"]) if i else ""


def catalog(pid=None, db=None):
    db = _open(db)
    try:
        player = _player(db, pid)
        stars = db.stars(player["id"]) if player else {}
        bests = db.bests(player["id"]) if player else {}
        # the map shows a newcomer's progression when nobody is playing (practice mode can still open any built hall)
        prog = _progress(db, player) if player else hall_progress(ALL_HALLS, stars)
        if not player and not locks_on():
            for h in ALL_HALLS:
                prog[h["id"]]["unlocked"] = prog[h["id"]]["unlocked"] or bool(h.get("stations"))
        halls = []
        for i, h in enumerate(ALL_HALLS):
            entry = {"id": h["id"], "title": h["title"], "ball": h["ball"], "status": h["status"], "blurb": h["blurb"],
                     "unlocked": prog[h["id"]]["unlocked"], "cleared": prog[h["id"]]["cleared"],
                     "requires": _requires(i)}
            if h.get("stations"):
                entry["stations"] = [{"id": s["id"], "title": s["title"], "stars": sorted(stars.get(s["id"], [])),
                                      "best": bests.get(s["id"])} for s in h["stations"]]
                entry["golden"] = bool(player) and h["id"] in db.golden(player["id"])
                entry["score"] = sum(bests.get(s["id"]) or 0 for s in h["stations"])
                entry["max_score"] = 1000 * len(h["stations"])
            halls.append(entry)
        return {"player": player, "halls": halls, "score": db.score(player["id"]) if player else 0,
                "max_stars": 3 * sum(len(h["stations"]) for h in HALLS), "locks": locks_on()}
    finally:
        db.close()


def _check_open(db, player, hall_id):
    if not player:
        return
    prog = _progress(db, player)
    if not prog[hall_id]["unlocked"]:
        i = [h["id"] for h in ALL_HALLS].index(hall_id)
        raise GameError("%s is still locked. %s" % (ALL_HALLS[i]["title"], _requires(i)), 403)


def hall_view(hall_id, pid=None, v=None, db=None):
    hall = BY_ID.get(hall_id)
    if not hall:
        coming = next((h for h in COMING if h["id"] == hall_id), None)
        raise GameError("%s isn't built yet - coming soon." % coming["title"] if coming else "unknown hall", 404)
    db = _open(db)
    try:
        player = _player(db, pid)
        _check_open(db, player, hall_id)
        steps = _steps(hall, player, None if player else v)
        mod = HALL_MODULES[hall_id]
        stations = []
        for st in hall["stations"]:
            pub = public_station(st, steps[st["id"]])
            pub["mastery"] = mod.mastery_text(st, steps[st["id"]])
            if st.get("table"):
                pub["table"] = st["table"]
            pub["progress"] = db.progress(player["id"], st["id"]) if player else None
            pub["leaderboard"] = db.leaderboard(st["id"])
            pub["rank"] = db.rank(player["id"], st["id"]) if player else None
            stations.append(pub)
        unlocked, prev_ok = [], True
        for pub in stations:                # a station unlocks when the one before it works (classroom locks)
            unlocked.append(prev_ok or not player or not locks_on())
            prev_ok = bool(pub["progress"] and "works" in pub["progress"]["stars"])
        for pub, u in zip(stations, unlocked):
            pub["unlocked"] = u
        idx = [h["id"] for h in ALL_HALLS].index(hall_id)
        nxt = ALL_HALLS[idx + 1] if idx + 1 < len(ALL_HALLS) else None
        prog = _progress(db, player)
        return {"hall": {k: hall[k] for k in ("id", "title", "ball", "blurb", "layout")},
                "cleared": bool(player) and prog[hall_id]["cleared"],
                "next_hall": {"id": nxt["id"], "title": nxt["title"], "status": nxt["status"],
                              "unlocked": prog[nxt["id"]]["unlocked"]} if nxt else None,
                "stations": stations, "player": player, "practice": player is None,
                "variant": None if player else _practice_step(v),
                "score": db.score(player["id"]) if player else 0,
                "golden": bool(player) and hall_id in db.golden(player["id"]), "locks": locks_on()}
    finally:
        db.close()


# ---------------------------------------------------------------- runs

def _clean_prediction(station, raw):
    if raw is None:
        return None
    kind = station["predict"]["kind"]
    if kind == "boolean":
        if not isinstance(raw, bool):
            raise GameError("the prediction for %s is yes or no (true / false)" % station["title"])
        return raw
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw != raw or abs(raw) > 1e6:
        raise GameError("the prediction must be a number")
    return float(raw)


def _public_result(res):
    return {k: res[k] for k in ("ok", "reason", "metric", "unit", "mastery", "viz", "formula", "lab", "score",
                                "score_parts")}


def run(body, db=None):
    if not isinstance(body, dict):
        raise GameError("body must be a JSON object")
    extra = set(body) - {"player", "hall", "station", "mode", "knobs", "prediction", "v"}
    if extra:
        raise GameError("'%s' is not part of a run" % sorted(extra)[0][:40])
    hall = BY_ID.get(body.get("hall") if isinstance(body.get("hall"), str) else "")
    if not hall:
        raise GameError("unknown hall", 404)
    mode = body.get("mode", "test")
    if mode not in ("test", "machine"):
        raise GameError("mode must be 'test' or 'machine'")
    knobs_in = body.get("knobs", {})
    if not isinstance(knobs_in, dict):
        raise GameError("knobs must be an object: {station id: {knob: value}}")
    if mode == "test":
        sid = body.get("station")
        if not isinstance(sid, str) or sid not in STATIONS or STATIONS[sid]["hall"] != hall["id"]:
            raise GameError("unknown station", 404)
        todo = [STATIONS[sid]]
    else:
        todo = hall["stations"]
    for k in knobs_in:
        if not isinstance(k, str) or k not in {s["id"] for s in todo}:
            raise GameError("'%s' is not a station of this run" % str(k)[:20])
    clean = {}
    for st in todo:
        c, err = validate_knobs(st, knobs_in.get(st["id"], {}))
        if err:
            raise GameError("%s: %s" % (st["title"], err))
        clean[st["id"]] = c
    if "prediction" in body and mode != "test":
        raise GameError("predictions go with a single-station test run")

    db = _open(db)
    try:
        player = _player(db, body.get("player"))
        if player and "v" in body:
            raise GameError("the variant comes from the player (v is for practice mode only)")
        steps = _steps(hall, player, body.get("v"))
        mod = HALL_MODULES[hall["id"]]
        _check_open(db, player, hall["id"])
        was_cleared = bool(player) and _progress(db, player)[hall["id"]]["cleared"]
        if player and locks_on():                  # locked stations can't be run yet (classroom locks)
            for i, st in enumerate(hall["stations"]):
                if st in todo and i > 0 and "works" not in db.stars(player["id"], hall["stations"][i - 1]["id"]) \
                        and mode == "test":
                    raise GameError("%s is still locked - get %s working first" % (
                        st["title"], hall["stations"][i - 1]["title"]), 403)
        if mode == "test":
            st = todo[0]
            res = run_cached(st, clean[st["id"]], steps[st["id"]])
            parts = [{"id": st["id"], "result": res, "t0": 0.0, "t1": res["frames"][-1]["t"]}]
            frames, ok_all, zones = res["frames"], res["ok"], res.get("timelapse", [])
        else:
            m = mod.run_machine(clean, steps)
            parts, frames, ok_all, zones = m["stations"], m["frames"], m["ok"], m.get("timelapse", [])
        prediction = _clean_prediction(todo[0], body.get("prediction")) if mode == "test" else None
        out_st = []
        for part in parts:
            st, res = STATIONS[part["id"]], part["result"]
            entry = dict(_public_result(res), id=st["id"], t0=part["t0"], t1=part["t1"],
                         facts=facts_for(st, steps[st["id"]]), knobs=clean[st["id"]], new_stars=[], insight=False)
            if player:
                best_before = db.best(player["id"], st["id"])
                history = db.runs(player["id"], st["id"])
                hints = db.hints(player["id"], st["id"])
                pred = prediction if (mode == "test" and not history) else None
                ins = insight(st, res, pred, not history)
                earned = stars_for_run(st, res, history, hints)
                _, new = db.record_run(player["id"], hall["id"], st["id"], mode, clean[st["id"]], pred, res, earned,
                                       ins)
                entry.update(new_stars=new, insight=ins, progress=db.progress(player["id"], st["id"]),
                             prediction_counted=pred is not None,
                             new_best=bool(res["ok"] and (best_before is None or res["score"] > best_before)),
                             best=db.best(player["id"], st["id"]), rank=db.rank(player["id"], st["id"]),
                             leaderboard=db.leaderboard(st["id"]))
            else:
                entry["insight"] = insight(st, res, prediction, True) if mode == "test" else False
            out_st.append(entry)
        golden_new = False
        if player and mode == "machine" and ok_all:
            have = db.stars(player["id"])
            if all("works" in have.get(s["id"], ()) for s in hall["stations"]):
                golden_new = db.add_golden(player["id"], hall["id"])
        cleared_new, next_hall = False, None
        if player:
            prog = _progress(db, player)
            cleared_new = prog[hall["id"]]["cleared"] and not was_cleared
            idx = [h["id"] for h in ALL_HALLS].index(hall["id"])
            if idx + 1 < len(ALL_HALLS):
                nh = ALL_HALLS[idx + 1]
                next_hall = {"id": nh["id"], "title": nh["title"], "status": nh["status"],
                             "unlocked": prog[nh["id"]]["unlocked"]}
        return {"mode": mode, "hall": hall["id"], "ok": ok_all, "stations": out_st, "frames": frames, "timelapse": zones,
                "practice": player is None, "variant": None if player else steps[todo[0]["id"]],
                "golden_new": golden_new, "score": db.score(player["id"]) if player else 0,
                "hall_cleared_new": cleared_new, "next_hall": next_hall}
    finally:
        db.close()


def hint(body, db=None):
    if not isinstance(body, dict):
        raise GameError("body must be a JSON object")
    st = STATIONS.get(body.get("station") if isinstance(body.get("station"), str) else "")
    if not st:
        raise GameError("unknown station", 404)
    tier = body.get("tier")
    if tier not in (1, 2, 3) or isinstance(tier, bool):
        raise GameError("tier must be 1, 2 or 3")
    hall = BY_ID[st["hall"]]
    mod = HALL_MODULES[hall["id"]]
    db = _open(db)
    try:
        player = _player(db, body.get("player"))
        if player:
            step = variant_steps(hall, player["id"])[st["id"]]
            failed = sum(1 for r in db.runs(player["id"], st["id"]) if not r["ok"])
            if not hint_allowed(tier, failed):
                raise GameError("the Blueprint opens after %d runs that didn't work" % 2, 403)
            db.add_hint(player["id"], st["id"], tier)
            progress = db.progress(player["id"], st["id"])
        else:
            if tier == 3:
                raise GameError("no Blueprints in practice mode - pick a player to play for real", 403)
            step = _practice_step(body.get("v"))
            progress = None
        text = mod.hint_text(st, tier, facts_for(st, step), step)
        costs = {1: "free", 2: "costs the Efficient star for this station (if you don't have it yet)",
                 3: "costs the Efficient and Mastery stars for this station (if you don't have them yet)"}[tier]
        return {"station": st["id"], "tier": tier, "text": text, "costs": costs, "progress": progress}
    finally:
        db.close()
