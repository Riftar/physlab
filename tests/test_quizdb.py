"""Quiz database: players, attempts, scores, reveals and history."""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import quiz  # noqa: E402
from physlab.quizdb import QuizDB  # noqa: E402


def answer(db, pid, qid, raw):
    q = quiz.BY_ID[qid]
    vals, err = quiz.check_inputs(q, raw)
    assert err is None
    g = quiz.grade(q, vals)
    return db.record(pid, q, vals, g), g


class TestQuizDB(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "sub", "quiz.sqlite")     # directory is created on open
        self.db = QuizDB(self.path)
        self.pid = self.db.create_player("  Ada   Lovelace  ")["id"]

    def tearDown(self):
        self.db.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_catalogue_is_seeded_and_idempotent(self):
        self.assertEqual(len(self.db.questions()), len(quiz.QUESTIONS))
        self.db.close()
        self.db = QuizDB(self.path)                                    # reopen: upsert, no duplicates
        self.assertEqual(len(self.db.questions()), len(quiz.QUESTIONS))
        row = self.db.db.execute("SELECT difficulty, points FROM questions WHERE id = 'pendulum-hard'").fetchone()
        self.assertEqual((row[0], row[1]), ("hard", 30))

    def test_players(self):
        p = self.db.player(self.pid)
        self.assertEqual(p["name"], "Ada Lovelace")                   # whitespace tidied
        self.assertEqual((p["score"], p["solved"]), (0, 0))
        self.assertEqual(len(self.pid), 32)
        with self.assertRaises(ValueError):
            self.db.create_player("   ")
        with self.assertRaises(ValueError):
            self.db.create_player(42)
        self.assertEqual(len(self.db.create_player("x" * 100)["name"]), 24)
        self.assertIsNone(self.db.player("nope"))
        self.assertIsNone(self.db.player("x" * 500))
        self.assertEqual(self.db.players()[0]["name"], "x" * 24)      # most recent first

    def test_scoring_first_correct_only_with_penalty(self):
        pts, g = answer(self.db, self.pid, "motion-easy", {"v0": 20.0})
        self.assertEqual((pts, g["correct"]), (0, False))
        pts, g = answer(self.db, self.pid, "motion-easy", {"v0": 14.0})
        self.assertEqual((pts, g["correct"]), (8, True))               # 1 wrong try: 75%
        pts, _ = answer(self.db, self.pid, "motion-easy", {"v0": 14.0})
        self.assertEqual(pts, 0)                                        # no double points
        pts, _ = answer(self.db, self.pid, "motion-hard", {"v0": 26.0, "angle": 40.0})
        self.assertEqual(pts, 30)                                       # first try: full points
        self.assertEqual(self.db.score(self.pid), 38)
        st = self.db.progress(self.pid, "motion-easy")
        self.assertEqual((st["attempts"], st["solved"], st["wrong_before"], st["earned"]), (3, True, 1, 8))
        self.assertEqual(self.db.player(self.pid)["solved"], 2)

    def test_reveal_needs_two_wrong_tries_and_costs_the_points(self):
        q = quiz.BY_ID["pendulum-easy"]
        with self.assertRaises(ValueError):
            self.db.reveal(self.pid, q)
        answer(self.db, self.pid, "pendulum-easy", {"length": 2.0})
        self.assertFalse(self.db.progress(self.pid, q["id"])["can_reveal"])
        answer(self.db, self.pid, "pendulum-easy", {"length": 0.5})
        self.assertTrue(self.db.progress(self.pid, q["id"])["can_reveal"])
        self.db.reveal(self.pid, q)
        self.db.reveal(self.pid, q)                                     # idempotent
        st = self.db.progress(self.pid, q["id"])
        self.assertTrue(st["revealed"])
        self.assertFalse(st["can_reveal"])
        pts, g = answer(self.db, self.pid, "pendulum-easy", {"length": 0.99})
        self.assertTrue(g["correct"])
        self.assertEqual(pts, 0)

    def test_history_newest_first_with_inputs(self):
        answer(self.db, self.pid, "heat-easy", {"temp_b": 0.0})
        answer(self.db, self.pid, "heat-hard", {"material_b": "water", "mass_b": 0.5})
        h = self.db.history(self.pid)
        self.assertEqual([x["question_id"] for x in h], ["heat-hard", "heat-easy"])
        self.assertEqual(h[0]["inputs"], {"material_b": "water", "mass_b": 0.5})
        self.assertEqual(h[0]["correct"], 1)
        self.assertEqual(h[1]["correct"], 0)
        self.assertAlmostEqual(h[1]["value"], 40.0, delta=0.5)           # measured outcome stored
        self.assertEqual(self.db.history("someone-else"), [])

    def test_scores_are_per_player_and_never_stored_twice(self):
        other = self.db.create_player("Ben")["id"]
        answer(self.db, self.pid, "waves-easy", {"f": 5.0})
        answer(self.db, other, "waves-easy", {"f": 2.0})
        self.assertEqual(self.db.score(self.pid), 10)
        self.assertEqual(self.db.score(other), 0)
        total = self.db.db.execute("SELECT SUM(points) FROM attempts").fetchone()[0]
        self.assertEqual(total, 10)

    def test_foreign_keys_are_enforced(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with self.db.db:
                self.db.db.execute("INSERT INTO attempts (player_id, question_id, inputs, value, correct, points, "
                                   "created) VALUES ('ghost', 'motion-easy', '{}', NULL, 0, 0, 0)")


if __name__ == "__main__":
    unittest.main()
