"""Game storage: the same SQLite file and the same players as the quiz
(physlab/quizdb.py), plus the game's own tables.

    game_runs     every run: player, station, mode, the knobs, a prediction,
                  the verdict, the measured metric and the run's SCORE
                  (0-1000; the history, and the source of every star, point,
                  personal best and leaderboard)
    game_stars    (player, station, star) - works / efficient / mastery
    game_hints    (player, station, tier) - which hints were opened
    game_golden   (player, hall) - the whole machine ran A -> B in one go

Like the quiz, the score is never stored: it is summed from stars, golden
runs and insight runs, so it can't drift from the history. Variants are not
stored either - they are a pure function of the player id (common.py).
"""

import json
import time

from ..quizdb import QuizDB, default_path
from .common import STAR_POINTS, GOLDEN_POINTS, INSIGHT_POINTS

SCHEMA = """
CREATE TABLE IF NOT EXISTS game_runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    hall_id     TEXT NOT NULL,
    station_id  TEXT NOT NULL,
    mode        TEXT NOT NULL CHECK (mode IN ('test', 'machine')),
    knobs       TEXT NOT NULL,           -- JSON of the station's settings
    prediction  TEXT,                    -- JSON, only on a station's first run
    ok          INTEGER NOT NULL,
    metric      REAL,
    mastery     INTEGER NOT NULL,
    insight     INTEGER NOT NULL,
    score       INTEGER,                 -- 0-1000 (NULL for runs recorded before scores existed)
    created     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS game_runs_by_player ON game_runs (player_id, station_id, id);
CREATE TABLE IF NOT EXISTS game_stars (
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    station_id  TEXT NOT NULL,
    star        TEXT NOT NULL CHECK (star IN ('works', 'efficient', 'mastery')),
    run_id      INTEGER NOT NULL REFERENCES game_runs(id),
    created     REAL NOT NULL,
    PRIMARY KEY (player_id, station_id, star)
);
CREATE TABLE IF NOT EXISTS game_hints (
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    station_id  TEXT NOT NULL,
    tier        INTEGER NOT NULL CHECK (tier IN (1, 2, 3)),
    created     REAL NOT NULL,
    PRIMARY KEY (player_id, station_id, tier)
);
CREATE TABLE IF NOT EXISTS game_golden (
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    hall_id     TEXT NOT NULL,
    created     REAL NOT NULL,
    PRIMARY KEY (player_id, hall_id)
);
"""


class GameDB(object):
    def __init__(self, path=None):
        self.q = QuizDB(path or default_path())        # players + the shared connection
        self.db = self.q.db
        self.db.executescript(SCHEMA)
        self._migrate()

    def _migrate(self):
        """Databases made before scores existed get the column (old runs keep NULL)."""
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(game_runs)").fetchall()}
        if "score" not in cols:
            self.db.execute("ALTER TABLE game_runs ADD COLUMN score INTEGER")
            self.db.commit()

    def close(self):
        self.q.close()

    def player(self, pid):
        return self.q.player(pid)

    # ---------------- reads ----------------
    def runs(self, player_id, station_id):
        rows = self.db.execute("SELECT * FROM game_runs WHERE player_id = ? AND station_id = ? ORDER BY id",
                               (player_id, station_id)).fetchall()
        return [dict(r) for r in rows]

    def stars(self, player_id, station_id=None):
        if station_id:
            rows = self.db.execute("SELECT star FROM game_stars WHERE player_id = ? AND station_id = ?",
                                   (player_id, station_id)).fetchall()
            return {r["star"] for r in rows}
        rows = self.db.execute("SELECT station_id, star FROM game_stars WHERE player_id = ?", (player_id,)).fetchall()
        out = {}
        for r in rows:
            out.setdefault(r["station_id"], set()).add(r["star"])
        return out

    def hints(self, player_id, station_id):
        rows = self.db.execute("SELECT tier FROM game_hints WHERE player_id = ? AND station_id = ?",
                               (player_id, station_id)).fetchall()
        return {r["tier"] for r in rows}

    def golden(self, player_id):
        return {r["hall_id"] for r in self.db.execute("SELECT hall_id FROM game_golden WHERE player_id = ?",
                                                       (player_id,)).fetchall()}

    def score(self, player_id):
        n_stars = self.db.execute("SELECT COUNT(*) FROM game_stars WHERE player_id = ?", (player_id,)).fetchone()[0]
        n_gold = self.db.execute("SELECT COUNT(*) FROM game_golden WHERE player_id = ?", (player_id,)).fetchone()[0]
        n_ins = self.db.execute("SELECT COUNT(*) FROM game_runs WHERE player_id = ? AND insight = 1",
                                (player_id,)).fetchone()[0]
        return STAR_POINTS * n_stars + GOLDEN_POINTS * n_gold + INSIGHT_POINTS * n_ins

    def unscored(self):
        """Working runs from before scores existed: [(run id, player, station, knobs)]."""
        rows = self.db.execute("SELECT id, player_id, station_id, knobs FROM game_runs WHERE score IS NULL AND ok = 1")
        return [(r["id"], r["player_id"], r["station_id"], json.loads(r["knobs"])) for r in rows.fetchall()]

    def set_scores(self, scores):
        """scores: [(run id, score)]; failed runs of that era simply score 0."""
        self.db.executemany("UPDATE game_runs SET score = ? WHERE id = ?", [(sc, rid) for rid, sc in scores])
        self.db.execute("UPDATE game_runs SET score = 0 WHERE score IS NULL AND ok = 0")
        self.db.commit()

    # ---------------- scores ----------------
    def best(self, player_id, station_id):
        r = self.db.execute("SELECT MAX(score) FROM game_runs WHERE player_id = ? AND station_id = ? AND ok = 1",
                            (player_id, station_id)).fetchone()[0]
        return r

    def bests(self, player_id):
        rows = self.db.execute("SELECT station_id, MAX(score) AS best FROM game_runs WHERE player_id = ? AND ok = 1 "
                               "AND score IS NOT NULL GROUP BY station_id", (player_id,)).fetchall()
        return {r["station_id"]: r["best"] for r in rows}

    def leaderboard(self, station_id, limit=5):
        """The best score of each player on this machine, highest first (ties: who got there first)."""
        rows = self.db.execute(
            "SELECT p.id AS player_id, p.name AS name, MAX(r.score) AS best, MIN(r.created) AS first "
            "FROM game_runs r JOIN players p ON p.id = r.player_id "
            "WHERE r.station_id = ? AND r.ok = 1 AND r.score IS NOT NULL "
            "GROUP BY p.id ORDER BY best DESC, first ASC LIMIT ?", (station_id, limit)).fetchall()
        return [{"player_id": r["player_id"], "name": r["name"], "best": r["best"]} for r in rows]

    def rank(self, player_id, station_id):
        mine = self.best(player_id, station_id)
        if mine is None:
            return None
        higher = self.db.execute(
            "SELECT COUNT(*) FROM (SELECT player_id, MAX(score) AS b FROM game_runs WHERE station_id = ? AND ok = 1 "
            "AND score IS NOT NULL GROUP BY player_id) WHERE b > ?", (station_id, mine)).fetchone()[0]
        players = self.db.execute("SELECT COUNT(DISTINCT player_id) FROM game_runs WHERE station_id = ? AND ok = 1 "
                                  "AND score IS NOT NULL", (station_id,)).fetchone()[0]
        return {"rank": higher + 1, "of": players}

    def progress(self, player_id, station_id):
        runs = self.runs(player_id, station_id)
        return {"runs": len(runs), "failed": sum(1 for r in runs if not r["ok"]),
                "stars": sorted(self.stars(player_id, station_id)), "hints": sorted(self.hints(player_id, station_id)),
                "last_knobs": json.loads(runs[-1]["knobs"]) if runs else None,
                "best": self.best(player_id, station_id)}

    # ---------------- writes ----------------
    def record_run(self, player_id, hall_id, station_id, mode, knobs, prediction, result, stars, insight):
        """Store one station run and the stars it earned. Returns (run_id, new_stars)."""
        now = time.time()
        metric = result.get("metric")
        metric = float(metric) if isinstance(metric, (int, float)) else None
        cur = self.db.execute(
            "INSERT INTO game_runs (player_id, hall_id, station_id, mode, knobs, prediction, ok, metric, mastery, "
            "insight, score, created) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (player_id, hall_id, station_id, mode, json.dumps(knobs, sort_keys=True),
             None if prediction is None else json.dumps(prediction), int(bool(result["ok"])), metric,
             int(bool(result["mastery"])), int(bool(insight)), int(result.get("score") or 0), now))
        run_id = cur.lastrowid
        have = self.stars(player_id, station_id)
        new = [s for s in stars if s not in have]
        for s in new:
            self.db.execute("INSERT INTO game_stars (player_id, station_id, star, run_id, created) "
                            "VALUES (?, ?, ?, ?, ?)", (player_id, station_id, s, run_id, now))
        self.db.commit()
        return run_id, new

    def add_hint(self, player_id, station_id, tier):
        self.db.execute("INSERT OR IGNORE INTO game_hints (player_id, station_id, tier, created) VALUES (?, ?, ?, ?)",
                        (player_id, station_id, tier, time.time()))
        self.db.commit()

    def add_golden(self, player_id, hall_id):
        cur = self.db.execute("INSERT OR IGNORE INTO game_golden (player_id, hall_id, created) VALUES (?, ?, ?)",
                              (player_id, hall_id, time.time()))
        self.db.commit()
        return cur.rowcount == 1
