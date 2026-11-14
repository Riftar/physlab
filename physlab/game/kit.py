"""What every hall module shares: the generated per-variant data table, the
mastery/hint texts, scoring helpers, scripted connectors and the machine run.

A hall module (bounce_factory.py, foundry.py ...) defines STATIONS (data +
a run(knobs, facts, thresholds) function each), a LAYOUT, VIA (waypoints
between stations) and makes a Hall(...) from them; the Hall object then
provides table(), thresholds(), mastery_text(), hint_text(), run_station()
and run_machine() for the service and the tools.
"""

import json
import math

from .common import facts_for

SCORE_MAX, SCORE_FLOOR = 1000, 100


def score(ok, raw):
    """0 for a failed run; a working run scores SCORE_FLOOR..SCORE_MAX."""
    return int(max(SCORE_FLOOR, min(SCORE_MAX, round(raw)))) if ok else 0


def world(frames, origin, t0=0.0, extra=()):
    """Station-local frames -> world frames {t, x, y, + extra fields}."""
    ox, oy = origin
    out = []
    for f in frames:
        g = {"t": round(t0 + f["t"], 4), "x": round(ox + f["x"], 4), "y": round(oy + f["y"], 4)}
        for k in extra:
            if k in f:
                g[k] = f[k]
        out.append(g)
    return out


def query(params):
    return "&".join("%s=%s" % (k, v) for k, v in params)


def tween(points, t0, speed):
    """Scripted connector: straight pieces at `speed` m/s -> frames from t0."""
    frames, t = [], t0
    for (xa, ya), (xb, yb) in zip(points, points[1:]):
        d = math.hypot(xb - xa, yb - ya)
        n = max(1, int(d / (speed / 30.0)))
        for i in range(1, n + 1):
            u = i / float(n)
            frames.append({"t": round(t + u * d / speed, 4), "x": round(xa + (xb - xa) * u, 4),
                           "y": round(ya + (yb - ya) * u, 4)})
        t += d / speed
    return frames, t


def thin(frames, most=400):
    """Keep at most `most` frames (always the last one)."""
    if len(frames) <= most:
        return frames
    step = int(math.ceil(len(frames) / float(most)))
    out = frames[::step]
    if out[-1] is not frames[-1]:
        out.append(frames[-1])
    return out


class Hall(object):
    def __init__(self, hall, stations, data_path, via, connector_speed=1.2):
        self.hall, self.stations, self.data_path = hall, stations, data_path
        self.by_id = {s["id"]: s for s in stations}
        self.via, self.connector_speed = via, connector_speed
        self._table = None

    # ---------------- the generated table ----------------
    def table(self):
        if self._table is None:
            with open(self.data_path) as f:
                self._table = json.load(f)
        return self._table

    def variant_data(self, station_id, step):
        return self.table()["stations"][station_id]["variants"][step]

    def thresholds(self, station_id, step):
        return self.variant_data(station_id, step).get("thresholds", {})

    # ---------------- texts ----------------
    def mastery_text(self, station, step):
        th = self.thresholds(station["id"], step)
        txt = station["mastery"]["text"]
        for key, v in th.items():
            txt = txt.replace("{%s}" % key, ("%d" % v) if isinstance(v, int) else "%.2f" % v)
        return txt

    def hint_text(self, station, tier, fx, step):
        if tier <= len(station["hints"]):
            txt = station["hints"][tier - 1]
            for key, v in fx.items():
                txt = txt.replace("{%s}" % key, "%g" % v)
            return txt
        vd = self.variant_data(station["id"], step)                # tier 3: the Blueprint
        return "Blueprint: %s works - %s" % (
            ", ".join("%s = %s" % (kk, vv) for kk, vv in vd["solution"].items()), vd["why"])

    # ---------------- runs ----------------
    def run_station(self, station, knobs, step):
        return station["run"](knobs, facts_for(station, step), self.thresholds(station["id"], step))

    def run_machine(self, knobs_by_station, steps):
        """Run the stations in order from A, each with its knobs; stop at the
        first failure. Returns {ok, stations: [{id, result, t0, t1}], frames}:
        one continuous world path, connectors included."""
        results = []
        for st in self.stations:
            res = self.run_station(st, knobs_by_station[st["id"]], steps[st["id"]])
            results.append((st, res))
            if not res["ok"]:
                break
        frames, out, t, zones = [], [], 0.0, []
        for i, (st, res) in enumerate(results):
            if i > 0:                                              # connector from the previous station
                prev = results[i - 1][1]["frames"][-1]
                first = res["frames"][0]
                way = self.via.get(results[i - 1][0]["id"], lambda last, nxt: [])
                pts = [(prev["x"], prev["y"])] + way(prev, first) + [(first["x"], first["y"])]
                tw, t = tween(pts, t, self.connector_speed)
                frames += tw
            t0 = t
            zones += [[round(a + t0, 4), round(b + t0, 4), k] for a, b, k in res.get("timelapse", [])]
            shifted = [dict(f, t=round(f["t"] + t0, 4)) for f in res["frames"]]
            frames += shifted
            t = shifted[-1]["t"]
            out.append({"id": st["id"], "result": res, "t0": round(t0, 4), "t1": round(t, 4)})
        ok = len(results) == len(self.stations) and all(r["ok"] for _, r in results)
        return {"ok": ok, "stations": out, "frames": frames, "timelapse": zones}
