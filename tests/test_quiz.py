"""Quiz: every question is well-formed, every reference answer is graded
correct BY RUNNING THE SIMULATION, every listed common mistake is graded
wrong, inputs are strictly validated, and the scoring rules hold."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from physlab import TOPICS, spec, quiz  # noqa: E402
from physlab.server import validate  # noqa: E402

READY = [t["id"] for t in TOPICS if t["status"] == "ready"]


def graded(q, raw):
    vals, err = quiz.check_inputs(q, raw)
    assert err is None, (q["id"], raw, err)
    return quiz.grade(q, vals)


class TestCatalogue(unittest.TestCase):
    def test_three_levels_per_experiment(self):
        self.assertEqual(len(quiz.QUESTIONS), 3 * len(READY))
        for tid in READY:
            levels = sorted(q["difficulty"] for q in quiz.QUESTIONS if q["topic"] == tid)
            self.assertEqual(levels, sorted(quiz.LEVELS), tid)
        ids = [q["id"] for q in quiz.QUESTIONS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_points_follow_difficulty(self):
        for q in quiz.QUESTIONS:
            self.assertEqual(q["points"], quiz.POINTS[q["difficulty"]], q["id"])

    def test_difficulty_means_something(self):
        for q in quiz.QUESTIONS:
            n = len(q["inputs"])
            if q["difficulty"] in ("easy", "medium"):
                self.assertEqual(n, 1, q["id"])
            else:                                    # hard: two inputs, or no simple formula
                self.assertTrue(n >= 2 or q.get("beyond_formula"), q["id"])

    def test_inputs_setup_and_goal_are_consistent(self):
        for q in quiz.QUESTIONS:
            specs = {p["id"]: p for p in spec(q["topic"])["params"]}
            ins = [i["param"] for i in q["inputs"]]
            for pid in ins:
                self.assertIn(pid, specs, q["id"])
                self.assertNotIn(pid, q["setup"], (q["id"], "an input can't also be fixed"))
            for k, v in q["setup"].items():                  # the fixed set-up is valid and unclamped
                self.assertIn(k, specs, q["id"])
                query = {k: [("1" if v else "0") if isinstance(v, bool) else str(v)]}
                p, err = validate(spec(q["topic"]), query)
                self.assertIsNone(err, (q["id"], k))
                self.assertEqual(p[k], v, (q["id"], k))
            start = {i["param"]: i["start"] for i in q["inputs"]}
            self.assertIsNone(quiz.check_inputs(q, start)[1], q["id"])
            g = q["goal"]
            self.assertIn(g["metric"], quiz.METRICS, q["id"])
            self.assertLessEqual(g["min"], g["max"])
            self.assertTrue(g["min"] <= g["target"] <= g["max"], q["id"])
            for key in ("title", "prompt", "explanation", "solution"):
                self.assertTrue(q[key].strip(), (q["id"], key))
            self.assertTrue(q["feedback"], q["id"])
            self.assertTrue(q["solutions"] and q["wrong"], q["id"])

    def test_public_view_never_leaks_the_answer(self):
        for q in quiz.QUESTIONS:
            pub = quiz.public(q)
            for key in ("solution", "solutions", "wrong", "explanation"):
                self.assertNotIn(key, pub, q["id"])
            self.assertTrue(pub["goal"]["text"])
            self.assertEqual([i["id"] for i in pub["inputs"]], [i["param"] for i in q["inputs"]])


class TestGrading(unittest.TestCase):
    def test_every_reference_answer_is_correct(self):
        for q in quiz.QUESTIONS:
            for s in q["solutions"]:
                g = graded(q, s)
                self.assertTrue(g["correct"], (q["id"], s, g["message"]))
                self.assertIn("Spot on", g["message"])

    def test_every_common_mistake_is_wrong_with_a_hint(self):
        for q in quiz.QUESTIONS:
            for w in q["wrong"]:
                g = graded(q, w)
                self.assertFalse(g["correct"], (q["id"], w, g["message"]))
                self.assertTrue(len(g["message"]) > 20, q["id"])

    def test_the_starting_value_is_not_already_an_answer(self):
        for q in quiz.QUESTIONS:
            start = {i["param"]: i["start"] for i in q["inputs"]}
            self.assertFalse(graded(q, start)["correct"], q["id"])

    def test_the_grade_comes_from_the_simulation_run(self):
        q = quiz.BY_ID["motion-easy"]
        g = graded(q, {"v0": 14.0})
        self.assertAlmostEqual(g["value"], g["result"]["frames"][-1]["x"], places=9)
        self.assertEqual(g["result"]["params"]["angle"], 45.0)        # fixed set-up applied
        # both angles of the Moon question are accepted
        q = quiz.BY_ID["motion-medium"]
        self.assertTrue(graded(q, {"angle": 27.0})["correct"])
        self.assertTrue(graded(q, {"angle": 63.0})["correct"])

    def test_failed_preconditions_explain_themselves(self):
        g = graded(quiz.BY_ID["pressure-easy"], {"force": 50.0})
        self.assertFalse(g["correct"])
        self.assertIsNone(g["value"])
        self.assertIn("didn't move", g["message"])
        g = graded(quiz.BY_ID["buoyancy-hard"], {"material": "iron", "size": 10.0})
        self.assertIn("sank", g["message"])

    def test_feedback_points_the_right_way(self):
        q = quiz.BY_ID["motion-easy"]
        self.assertIn("too far", graded(q, {"v0": 20.0})["message"])
        self.assertIn("fell short", graded(q, {"v0": 10.0})["message"])


class TestInputValidation(unittest.TestCase):
    q = quiz.BY_ID["motion-hard"]

    def test_only_the_allowed_parameters(self):
        self.assertIn("can't change", quiz.check_inputs(self.q, {"v0": 20, "angle": 40, "g": 1.6})[1])
        self.assertIn("missing", quiz.check_inputs(self.q, {"v0": 20})[1])
        self.assertIsNotNone(quiz.check_inputs(self.q, [20, 40])[1])

    def test_numbers_in_range_and_finite(self):
        self.assertIn("between", quiz.check_inputs(self.q, {"v0": 999, "angle": 40})[1])
        self.assertIn("between", quiz.check_inputs(self.q, {"v0": float("nan"), "angle": 40})[1])
        self.assertIn("number", quiz.check_inputs(self.q, {"v0": "fast", "angle": 40})[1])
        vals, err = quiz.check_inputs(self.q, {"v0": "20.123456", "angle": 40})
        self.assertIsNone(err)
        self.assertEqual(vals["v0"], 20.1235)

    def test_choices(self):
        q = quiz.BY_ID["buoyancy-easy"]
        self.assertIsNone(quiz.check_inputs(q, {"fluid": "mercury"})[1])
        self.assertIn("choices", quiz.check_inputs(q, {"fluid": "lava"})[1])


class TestScoring(unittest.TestCase):
    def test_points_rules(self):
        easy, hard = quiz.BY_ID["motion-easy"], quiz.BY_ID["motion-hard"]
        self.assertEqual(quiz.points_for(easy, 0, False, False), 10)
        self.assertEqual(quiz.points_for(easy, 1, False, False), 8)         # 7.5 rounds up
        self.assertEqual(quiz.points_for(hard, 1, False, False), 23)        # 22.5 rounds up
        self.assertEqual(quiz.points_for(hard, 2, False, False), 15)
        self.assertEqual(quiz.points_for(hard, 9, False, False), 15)        # never below half
        self.assertEqual(quiz.points_for(hard, 0, True, False), 0)          # already solved
        self.assertEqual(quiz.points_for(hard, 0, False, True), 0)          # answer was revealed

    def test_goal_text(self):
        self.assertEqual(quiz.goal_text(quiz.BY_ID["motion-easy"]),
                         "The landing point should be between 19.5 and 20.5 m.")
        self.assertEqual(quiz.goal_text(quiz.BY_ID["buoyancy-easy"]), "The iron block must float.")


if __name__ == "__main__":
    unittest.main()
