"""匿名配布、左右復元、意味保持の入口条件と欠測を検証する。"""
import copy
import json
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from helpers import REPO_ROOT, TOOLS_DIR, load_module, temporary_directory

comparison = load_module("compare_readability", TOOLS_DIR / "compare_readability.py")
EXAMPLE = REPO_ROOT / "evals/blind-comparison-example.json"


def answer_file(assigned):
    public = assigned["public"]
    candidate = {"contract": "pass", "scores": {d: 4 for d in comparison.review.DIMENSIONS},
                 "reason": "数値・条件・主体が保持されている。", "suggestion": "", "issues": []}
    return {**{k: public[k] for k in ("schema_version", "rubric_version", "task_sha256", "reviewer")},
            "method": "human", "reviews": [{"id": public["cases"][0]["id"], "left": copy.deepcopy(candidate),
                                             "right": copy.deepcopy(candidate), "preference": "left", "reason": "読み戻りが少ない。"}]}


class CompareReadabilityTest(unittest.TestCase):
    def test_same_pair_input_runs_offline_checks_without_losing_variant_or_document(self):
        with temporary_directory() as tmp:
            folder = Path(tmp) / "auto"
            self.assertEqual(comparison.main(["auto", "--input", str(EXAMPLE), "--out-dir", str(folder)]), 0)
            tasks = comparison.review.read_tasks(folder / "tasks.json")
            report = comparison.review.read_json(folder / "automatic.json")
            self.assertEqual(len(report["results"]), 6)
            self.assertEqual(len({c["document_id"] for c in tasks["cases"]}), 3)
            failed_example = next(c for c in tasks["cases"] if c["provenance"]["variant"] == "revision")
            inspected = next(r for r in report["results"] if r["id"] == failed_example["id"])
            self.assertEqual(inspected["contract"], "uncertain")
            self.assertTrue(any(f["category"] == "numbers" for f in inspected["findings"]))

    def test_distribution_hides_variant_names_and_preserves_assignment_on_reload(self):
        with temporary_directory() as tmp:
            folder = Path(tmp) / "comparison"
            self.assertEqual(comparison.main(["prepare", "--input", str(EXAMPLE), "--reviewers", "r1", "r2", "--out-dir", str(folder)]), 0)
            assignments = comparison.read_assignments(folder / "organizer.json")
            for index, assigned in enumerate(assignments, 1):
                public_path = folder / f"reader-{index:03}" / "tasks.json"
                self.assertEqual(json.loads(public_path.read_text(encoding="utf-8")), assigned["public"])
                for filename in ("tasks.json", "review.html"):
                    public_text = (public_path.parent / filename).read_text(encoding="utf-8")
                    for private_label in ("baseline", "revision", "condition-practice", "source_id", "provenance"):
                        self.assertNotIn(private_label, public_text)
            before = public_path.read_bytes()
            self.assertEqual(comparison.main(["prepare", "--input", str(EXAMPLE), "--reviewers", "r1", "--out-dir", str(folder)]), 2)
            self.assertEqual(public_path.read_bytes(), before)

    def test_repeated_document_keeps_orientation_and_balances_unique_documents(self):
        pairs = comparison.read_pairs(EXAMPLE)
        pairs.append({**pairs[0], "id": "repeat"})
        assigned = comparison.assignment(pairs, "r1")
        mapped = assigned["mapping"]
        self.assertEqual(mapped["pair-001"]["left"], mapped["pair-004"]["left"])
        self.assertEqual(assigned["public"]["cases"][0]["document_id"], assigned["public"]["cases"][3]["document_id"])
        self.assertEqual(len({mapped[f"pair-{i:03}"]["left"] for i in range(1, 4)}), 2)

    def test_single_document_can_be_assigned_either_orientation(self):
        pairs = comparison.read_pairs(EXAMPLE)[:1]
        left_variants = set()
        for seed in range(4):
            with patch.object(comparison.random, "SystemRandom", return_value=random.Random(seed)):
                left_variants.add(comparison.assignment(pairs, "r1")["mapping"]["pair-001"]["left"])
        self.assertEqual(left_variants, {"baseline", "revision"})

    def test_selection_restores_variant_and_includes_absent_reviewer_and_partial_answers(self):
        pairs = comparison.read_pairs(EXAMPLE)
        assignments = [comparison.assignment(pairs, name) for name in ("r1", "r2")]
        answers = answer_file(assignments[0])
        summary = comparison.aggregate(assignments, [answers])
        winner = assignments[0]["mapping"]["pair-001"]["left"]
        self.assertEqual(summary["expected_reviews"], 6)
        self.assertEqual(summary["missing_reviews"], 5)
        self.assertEqual(summary["assigned_documents"], 3)
        self.assertEqual(summary["preference_among_both_pass"], {winner: 1})
        self.assertEqual(summary["variants"][winner]["scores"]["style"]["mean"], 4)

    def test_failed_candidate_never_contributes_preference_but_retains_issues(self):
        assigned = comparison.assignment(comparison.read_pairs(EXAMPLE), "r1")
        answers = answer_file(assigned)
        entry = answers["reviews"][0]
        entry["left"].update(contract="fail", issues=[{"category": "condition", "severity": "critical",
                                                     "quote": assigned["public"]["cases"][0]["left"], "reason": "条件を照合する。"}])
        with self.assertRaises(ValueError):
            comparison.aggregate([assigned], [answers])
        entry["preference"] = "uncertain"
        summary = comparison.aggregate([assigned], [answers])
        variant = assigned["mapping"]["pair-001"]["left"]
        self.assertEqual(summary["both_pass"], 0)
        self.assertEqual(summary["preference_among_both_pass"], {})
        self.assertEqual(summary["variants"][variant]["fail_rate_all_assignments"], 1 / 3)
        self.assertEqual(summary["variants"][variant]["issues_by_category"], {"condition": 1})

    def test_disagreements_keep_candidate_identity_and_do_not_count_votes_as_documents(self):
        pairs = comparison.read_pairs(EXAMPLE)[:1]
        pairs.append({**pairs[0], "id": "repeat"})
        assignments = [comparison.assignment(pairs, name) for name in ("r1", "r2", "absent")]
        documents = [answer_file(a) for a in assignments[:2]]
        variant = assignments[0]["mapping"]["pair-001"]["left"]
        for index, (assigned, document) in enumerate(zip(assignments, documents)):
            side = next(s for s in comparison.SIDES if assigned["mapping"]["pair-001"][s] == variant)
            answer = document["reviews"][0]
            answer[side]["issues"] = [{"category": "condition", "severity": "critical",
                "quote": assigned["public"]["cases"][0][side], "reason": "条件を確認する。"}]
            if index == 0:
                answer[side]["contract"] = "fail"
                answer["preference"] = "uncertain"
            document["reviews"].append({**copy.deepcopy(answer), "id": "pair-002"})
        summary = comparison.aggregate(assignments, documents)
        stats = summary["variants"][variant]
        self.assertEqual(stats["fail_rate_all_assignments"], 2 / 6)
        self.assertEqual(stats["fail_rate_completed"], 2 / 4)
        self.assertEqual(stats["missing_reviews"], 2)
        self.assertEqual(stats["issues_by_severity"], {"critical": 4})
        self.assertEqual(stats["documents_with_major_or_critical_issues"], 1)
        self.assertEqual(summary["both_pass_documents"], 1)
        self.assertEqual(summary["both_pass_rate_all_assignments"], 2 / 6)
        self.assertEqual(len(summary["disagreements"]), 2)
        self.assertEqual(summary["disagreements"][0]["contract_counts"], {"fail": 1, "pass": 1})
        self.assertEqual(summary["disagreements"][0]["votes"][0]["issues"][0]["severity"], "critical")

    def test_unanswered_and_single_reviewer_never_invent_agreement_or_rates(self):
        assigned = comparison.assignment(comparison.read_pairs(EXAMPLE), "r1")
        summary = comparison.aggregate([assigned], [])
        self.assertEqual(summary["disagreements"], [])
        self.assertTrue(all(s["fail_rate_completed"] is None for s in summary["variants"].values()))
        self.assertEqual(summary["both_pass_documents"], 0)
        self.assertEqual(comparison.aggregate([assigned], [answer_file(assigned)])["disagreements"], [])

    def test_malformed_answers_cannot_mix_assignments_or_invent_quotes(self):
        assigned = comparison.assignment(comparison.read_pairs(EXAMPLE), "r1")
        for fault in ("reviewer", "hash", "method", "id", "duplicate", "bool", "quote", "category", "reason", "array", "null"):
            with self.subTest(fault=fault):
                answers = answer_file(assigned)
                entry = answers["reviews"][0]
                if fault == "reviewer": answers["reviewer"] = "r2"
                elif fault == "hash": answers["task_sha256"] = "other"
                elif fault == "method": answers["method"] = "llm"
                elif fault == "id": entry["id"] = []
                elif fault == "duplicate": answers["reviews"] *= 2
                elif fault == "bool": entry["left"]["scores"]["style"] = True
                elif fault in ("quote", "category"):
                    entry["left"]["issues"] = [{"quote": "原文にない引用", "category": "condition" if fault == "quote" else "invalid", "severity": "major", "reason": "条件"}]
                elif fault == "reason": entry["reason"] = " "
                elif fault == "array": answers["reviews"] = {}
                elif fault == "null": entry["left"] = None
                with self.assertRaises(ValueError): comparison.aggregate([assigned], [answers])
        with self.assertRaises(ValueError): comparison.aggregate([assigned], [answer_file(assigned)] * 2)

    def test_broken_organizer_never_silently_attributes_results_to_wrong_variants(self):
        assigned = comparison.assignment(comparison.read_pairs(EXAMPLE), "r1")
        with temporary_directory() as tmp:
            path = Path(tmp) / "organizer.json"
            for fault in ("hash", "mapping", "case", "duplicate_reviewer", "variant"):
                with self.subTest(fault=fault):
                    changed = copy.deepcopy(assigned)
                    assignments = [changed]
                    if fault == "hash": changed["public"]["cases"][0]["left"] = "changed"
                    elif fault == "mapping": del changed["mapping"]["pair-001"]
                    elif fault == "case":
                        changed["public"]["cases"][0] = None
                        changed["public"]["task_sha256"] = comparison.fingerprint({k: v for k, v in changed["public"].items() if k != "task_sha256"})
                    elif fault == "duplicate_reviewer": assignments *= 2
                    elif fault == "variant": changed["mapping"]["pair-002"]["left"] = "other-version"
                    comparison.review.evaluation.save_json(path, {"schema_version": 1, "rubric_version": comparison.RUBRIC, "assignments": assignments})
                    with self.assertRaises(ValueError): comparison.read_assignments(path)

    def test_invalid_input_leaves_no_output_and_html_injection_is_escaped(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "input.json"
            for fault in ("mode", "variants", "empty", "reserved"):
                payload = comparison.review.read_json(EXAMPLE)
                if fault == "mode": payload["cases"][0]["mode"] = "A"
                elif fault == "variants": payload["cases"][0]["candidates"] = {"one": "text"}
                elif fault == "empty": payload["cases"] = []
                elif fault == "reserved": payload["cases"][0]["candidates"] = {"tie": "a", "uncertain": "b"}
                comparison.review.evaluation.save_json(path, payload)
                folder = Path(tmp) / "output"
                self.assertEqual(comparison.main(["prepare", "--input", str(path), "--reviewers", "r1", "--out-dir", str(folder)]), 2)
                self.assertFalse(folder.exists())
            payload = comparison.review.read_json(EXAMPLE)
            hostile = '</script><img src=x onerror="alert(1)">'
            payload["cases"][0]["candidates"]["baseline"] = hostile
            comparison.review.evaluation.save_json(path, payload)
            folder = Path(tmp) / "safe"
            self.assertEqual(comparison.main(["prepare", "--input", str(path), "--reviewers", "r1", "--out-dir", str(folder)]), 0)
            html = (folder / "reader-001/review.html").read_text(encoding="utf-8")
            self.assertNotIn(hostile, html)
            self.assertIn("\\u003c/script>", html)
            assigned = comparison.read_assignments(folder / "organizer.json")[0]
            comparison.review.evaluation.save_json(Path(tmp) / "answers.json", answer_file(assigned))
            self.assertEqual(comparison.main(["summarize", "--organizer", str(folder / "organizer.json"), "--answers", str(Path(tmp) / "answers.json"), "--out-dir", str(Path(tmp) / "summary")]), 0)
            self.assertTrue((Path(tmp) / "summary/summary.md").exists())


if __name__ == "__main__":
    unittest.main()
