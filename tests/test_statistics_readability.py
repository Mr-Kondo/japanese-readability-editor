"""票・反復生成を独立文書とせず、対応を保った版間差を計算する。"""
import copy
import unittest

from helpers import REPO_ROOT, TOOLS_DIR, load_module
from test_compare_readability import answer_file

inference = load_module("statistics_readability", TOOLS_DIR / "statistics_readability.py")
comparison = inference.comparison


class StatisticsReadabilityTest(unittest.TestCase):
    def test_repeated_generation_does_not_outweigh_other_document(self):
        pairs = comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json")[:2]
        pairs.extend([{**pairs[0], "id": f"repeat-{i}"} for i in range(3)])
        assigned = comparison.assignment(pairs, "r1")
        answers = answer_file(assigned)
        prototype = answers["reviews"][0]
        answers["reviews"] = []
        for case in assigned["public"]["cases"]:
            answer = {**copy.deepcopy(prototype), "id": case["id"], "preference": "uncertain"}
            failing = "baseline" if case["document_id"] == "doc-001" else "revision"
            side = next(s for s in comparison.SIDES if assigned["mapping"][case["id"]][s] == failing)
            answer[side]["contract"] = "fail"
            answers["reviews"].append(answer)
        report = inference.summarize([assigned], [answers])
        estimate = report["estimates"]["fail_rate_difference"]
        self.assertEqual(estimate["documents"], 2)
        self.assertEqual(estimate["mean"], 0)
        self.assertEqual(estimate["interval_95"], [-1, 1])
        self.assertEqual(report["estimates"]["preference_balance"]["documents"], 0)

    def test_tie_uncertain_and_missing_never_become_votes_or_failures(self):
        assigned = comparison.assignment(comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json"), "r1")
        answers = answer_file(assigned)
        answers["reviews"][0]["preference"] = "tie"
        report = inference.summarize([assigned], [answers])
        self.assertEqual(report["estimates"]["preference_balance"]["mean"], 0)
        self.assertEqual(report["coverage"]["missing_reviews"], 2)
        self.assertEqual(report["estimates"]["preference_balance"]["interval_status"], "insufficient_documents")
        answers["reviews"][0]["left"]["contract"] = "uncertain"
        answers["reviews"][0]["preference"] = "uncertain"
        report = inference.summarize([assigned], [answers])
        self.assertIsNone(report["estimates"]["fail_rate_difference"]["mean"])
        self.assertEqual(report["coverage"]["completed_reviews"], 1)

    def test_bootstrap_is_reproducible_and_degenerate_values_have_no_interval(self):
        self.assertEqual(inference.estimate([-1, 0, 0.5, 1]), inference.estimate([-1, 0, 0.5, 1]))
        for values, reason in (([], "insufficient_documents"), ([1], "insufficient_documents"), ([0, 0, 0], "degenerate_document_values")):
            with self.subTest(values=values):
                estimate = inference.estimate(values)
                self.assertEqual(estimate["interval_status"], reason)
                self.assertIsNone(estimate["interval_95"])


if __name__ == "__main__":
    unittest.main()
