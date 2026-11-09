"""Quiz storage: a small SQLite database (stdlib sqlite3, one file).

Tables
  questions  the question catalogue (seeded from physlab/quiz.py on open;
             the Python definitions stay the source of truth)
  players    a nickname + a random id kept by the browser (no accounts,
             no passwords: this runs offline on a classroom machine)
  attempts   every answer ever given: inputs, measured outcome, correct?,
             points earned - the history, and the source of every score
  reveals    "show me the answer" (after 2 wrong tries; no points after)

The score is never stored separately: it is the sum of attempt points,
so it can't drift from the history.

Location: $PHYSLAB_DB, else <repo>/data/physlab.sqlite.
"""

import json
import os
import sqlite3
import time
import uuid

from . import quiz

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME_MAX = 24

SCHEMA = """
CREATE TABLE IF NOT EXISTS questions (
    id         TEXT PRIMARY KEY,
    topic      TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    position   INTEGER NOT NULL,
    title      TEXT NOT NULL,
    prompt     TEXT NOT NULL,
    points     INTEGER NOT NULL,
    spec       TEXT NOT NULL            -- full definition as JSON (goal, inputs, solution ...)
);
CREATE TABLE IF NOT EXISTS players (
    id      TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    created REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS attempts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id),
    inputs      TEXT NOT NULL,          -- JSON of the values the student entered
    value       REAL,                   -- measured outcome (NULL if it failed a precondition)
    correct     INTEGER NOT NULL,
    points      INTEGER NOT NULL,
    created     REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_by_player ON attempts (player_id, question_id, id);
CREATE TABLE IF NOT EXISTS reveals (
    player_id   TEXT NOT NULL REFERENCES players(id) ON DELETE CASCADE,
    question_id TEXT NOT NULL REFERENCES questions(id),
    created     REAL NOT NULL,
    PRIMARY KEY (player_id, question_id)
);
"""


def default_path():
    return os.environ.get("PHYSLAB_DB") or os.path.join(ROOT, "data", "physlab.sqlite")


class QuizDB(object):
    def __init__(self, path=None):
        self.path = path or default_path()
        d = os.path.dirname(self.path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self.seed()

    def close(self):
        self.db.close()

    # ---------- catalogue ----------
    def seed(self):
        order = {lvl: i for i, lvl in enumerate(quiz.LEVELS)}
        with self.db:
            for q in quiz.QUESTIONS:
                self.db.execute(
                    "INSERT INTO questions (id, topic, difficulty, position, title, prompt, points, spec) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET topic = excluded.topic, "
                    "difficulty = excluded.difficulty, position = excluded.position, title = excluded.title, "
                    "prompt = excluded.prompt, points = excluded.points, spec = excluded.spec",
                    (q["id"], q["topic"], q["difficulty"], order[q["difficulty"]], q["title"], q["prompt"],
                     q["points"], json.dumps(q, sort_keys=True)))

    def questions(self):
        return [dict(r) for r in self.db.execute(
            "SELECT id, topic, difficulty, position, title, points FROM questions ORDER BY topic, position")]

    # ---------- players ----------
    @staticmethod
    def clean_name(name):
        if not isinstance(name, str):
            return None
        name = " ".join(name.split())[:NAME_MAX]
        return name or None

    def create_player(self, name):
        name = self.clean_name(name)
        if not name:
            raise ValueError("please type a name")
        pid = uuid.uuid4().hex
        with self.db:
            self.db.execute("INSERT INTO players (id, name, created) VALUES (?, ?, ?)", (pid, name, time.time()))
        return self.player(pid)

    def player(self, pid):
        if not isinstance(pid, str) or len(pid) > 64:
            return None
        row = self.db.execute("SELECT id, name, created FROM players WHERE id = ?", (pid,)).fetchone()
        if not row:
            return None
        out = dict(row)
        out["score"] = self.score(pid)
        out["solved"] = self.db.execute(
            "SELECT COUNT(DISTINCT question_id) FROM attempts WHERE player_id = ? AND correct = 1",
            (pid,)).fetchone()[0]
        return out

    def players(self, limit=20):
        rows = self.db.execute(
            "SELECT p.id, p.name, COALESCE(SUM(a.points), 0) AS score, MAX(a.created) AS last "
            "FROM players p LEFT JOIN attempts a ON a.player_id = p.id GROUP BY p.id "
            "ORDER BY COALESCE(MAX(a.created), p.created) DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]

    # ---------- progress ----------
    def score(self, pid):
        return self.db.execute("SELECT COALESCE(SUM(points), 0) FROM attempts WHERE player_id = ?",
                               (pid,)).fetchone()[0]

    def progress(self, pid, qid):
        """State of one question for one player."""
        rows = self.db.execute("SELECT correct, points FROM attempts WHERE player_id = ? AND question_id = ? "
                               "ORDER BY id", (pid, qid)).fetchall()
        solved, wrong_before, earned = False, 0, 0
        for r in rows:
            earned += r["points"]
            if r["correct"]:
                solved = True
            elif not solved:
                wrong_before += 1
        revealed = self.db.execute("SELECT 1 FROM reveals WHERE player_id = ? AND question_id = ?",
                                   (pid, qid)).fetchone() is not None
        return {"attempts": len(rows), "solved": solved, "wrong_before": wrong_before, "earned": earned,
                "revealed": revealed,
                "can_reveal": (not solved) and (not revealed) and wrong_before >= quiz.REVEAL_AFTER}

    def record(self, pid, q, inputs, graded):
        """Store an answer and award points for a first correct one."""
        st = self.progress(pid, q["id"])
        pts = quiz.points_for(q, st["wrong_before"], st["solved"], st["revealed"]) if graded["correct"] else 0
        with self.db:
            self.db.execute(
                "INSERT INTO attempts (player_id, question_id, inputs, value, correct, points, created) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pid, q["id"], json.dumps(inputs, sort_keys=True), graded["value"],
                 1 if graded["correct"] else 0, pts, time.time()))
        return pts

    def reveal(self, pid, q):
        st = self.progress(pid, q["id"])
        if not (st["can_reveal"] or st["revealed"] or st["solved"]):
            raise ValueError("try at least %d times before revealing the answer" % quiz.REVEAL_AFTER)
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO reveals (player_id, question_id, created) VALUES (?, ?, ?)",
                            (pid, q["id"], time.time()))

    def history(self, pid, limit=200):
        rows = self.db.execute(
            "SELECT a.id, a.question_id, q.topic, q.difficulty, q.title, a.inputs, a.value, a.correct, "
            "a.points, a.created FROM attempts a JOIN questions q ON q.id = a.question_id "
            "WHERE a.player_id = ? ORDER BY a.id DESC LIMIT ?", (pid, limit))
        out = []
        for r in rows:
            d = dict(r)
            d["inputs"] = json.loads(d["inputs"])
            out.append(d)
        return out
