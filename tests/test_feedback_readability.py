"""確認記録の境界検証と、既存評価形式への回帰出力を確かめる。"""
import copy
from pathlib import Path
import unittest

from helpers import REPO_ROOT, TOOLS_DIR, load_module, temporary_directory

feedback = load_module("feedback_readability", TOOLS_DIR / "feedback_readability.py")
comparison = feedback.comparison


def confirmed_document(assignments):
    document = feedback.decision_template(assignments)
    entry = document["decisions"][0]
    entry.update(status="confirmed_problem", confirmer="checker", reason="原文と数値・条件を照合した。",
                 quote=entry["input"]["candidate"], origin="artificial", preserve=["原文の数値と条件"],
                 forbid=["条件の削除"], rule_ids=["meaning-preservation"])
    return document


class FeedbackReadabilityTest(unittest.TestCase):
    def setUp(self):
        pairs = comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json")
        self.assignments = [comparison.assignment(pairs, name) for name in ("r1", "r2")]

    def test_export_only_confirmed_problems_and_keeps_pass_control_and_provenance(self):
        document = confirmed_document(self.assignments)
        second = document["decisions"][1]
        second.update(status="no_problem", confirmer="checker", reason="原文との関係を確認した。", quote=second["input"]["candidate"])
        suite = feedback.regression_suite(feedback.checked_decisions(document, self.assignments))
        self.assertEqual(len(suite["cases"]), 1)
        self.assertEqual([c["expected"] for c in suite["controls"]], ["fail", "pass"])
        self.assertEqual(suite["cases"][0]["provenance"]["origin"], "artificial")
        with temporary_directory() as tmp:
            path = Path(tmp) / "suite.json"
            comparison.review.evaluation.save_json(path, suite)
            self.assertEqual(comparison.review.evaluation.read_suite(path), suite)

    def test_unresolved_entries_cannot_be_exported_as_confirmed_failures(self):
        document = feedback.decision_template(self.assignments)
        checked = feedback.checked_decisions(document, self.assignments)
        with self.assertRaisesRegex(ValueError, "no confirmed"):
            feedback.regression_suite(checked)

    def test_corrupt_or_incomplete_decisions_are_rejected_before_writing(self):
        for fault in ("hash", "input", "missing", "duplicate", "status", "confirmer", "quote", "preserve", "origin", "id"):
            with self.subTest(fault=fault):
                document = confirmed_document(self.assignments)
                entry = document["decisions"][0]
                if fault == "hash": document["organizer_sha256"] = "wrong"
                elif fault == "input": entry["input"]["original"] = "changed"
                elif fault == "missing": document["decisions"].pop()
                elif fault == "duplicate": document["decisions"].append(copy.deepcopy(entry))
                elif fault == "status": entry["status"] = "pass"
                elif fault == "confirmer": entry["confirmer"] = " "
                elif fault == "quote": entry["quote"] = "存在しない引用"
                elif fault == "preserve": entry["preserve"] = []
                elif fault == "origin": entry["origin"] = []
                elif fault == "id": entry["source_id"] = []
                with self.assertRaises(ValueError):
                    feedback.checked_decisions(document, self.assignments)

    def test_different_content_under_same_source_id_is_never_combined(self):
        self.assignments[1]["public"]["cases"][0]["context"] = "別資料"
        with self.assertRaisesRegex(ValueError, "different source content"):
            feedback.candidate_index(self.assignments)

    def test_calibration_keeps_false_pass_uncertain_missing_and_unresolved_separate(self):
        document = confirmed_document(self.assignments)
        entries = document["decisions"]
        entries[1].update(status="no_problem", confirmer="checker", reason="保持を確認。", quote=entries[1]["input"]["candidate"])
        entries[2].update(**{k: entries[0][k] for k in ("status", "confirmer", "reason", "preserve", "forbid", "rule_ids")}, quote=entries[2]["input"]["candidate"])
        tasks = comparison.automatic_tasks(comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json"))
        judgments = []
        statuses = {(e["source_id"], e["variant"]): s for e, s in zip(entries, ("pass", "uncertain", "uncertain"))}
        for task in tasks["cases"]:
            status = statuses.get((task["provenance"]["source_id"], task["provenance"]["variant"]))
            if status is None:
                continue
            judgments.append({"id": task["id"], "contract": status,
                "scores": {d: None for d in comparison.review.DIMENSIONS}, "reason": "照合した。", "suggestion": "",
                "preference": "uncertain"})
        answers = {**{k: tasks[k] for k in ("schema_version", "rubric_version", "task_sha256")},
                   "method": "llm", "reviewer": "test-judge", "reviews": judgments}
        decisions = feedback.checked_decisions(document, self.assignments)
        report = feedback.calibration(self.assignments, decisions, tasks, answers)
        self.assertEqual(report["false_pass_among_resolved_llm_pass"], {"numerator": 1, "denominator": 1, "rate": 1})
        self.assertEqual(report["fail_detection_all_confirmed"]["denominator"], 2)
        self.assertEqual(report["confusion_matrix"]["fail"], {"pass": 1, "uncertain": 1})
        self.assertEqual(report["human_unresolved"], 3)
        self.assertEqual(report["llm_uncertain"], 2)
        self.assertEqual(report["llm_missing"], 3)
        answers["reviews"] = []
        self.assertIsNone(feedback.calibration(self.assignments, decisions, tasks, answers)["fail_detection_judged"]["rate"])

    def test_calibration_rejects_changed_content_even_with_matching_ids(self):
        document = confirmed_document(self.assignments)
        decisions = feedback.checked_decisions(document, self.assignments)
        tasks = comparison.automatic_tasks(comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json"))
        for fault in ("content", "provenance", "missing", "mode"):
            with self.subTest(fault=fault):
                changed = copy.deepcopy(tasks)
                if fault == "content": changed["cases"][0]["context"] = "別資料"
                elif fault == "provenance": changed["cases"][0]["provenance"]["variant"] = "other"
                elif fault == "missing": changed["cases"].pop()
                else: changed["cases"][0]["mode"] = "A"
                with self.assertRaises(ValueError):
                    feedback.matched_automatic_tasks(changed, self.assignments)
        answers = {"schema_version": 1, "rubric_version": comparison.review.RUBRIC, "task_sha256": "wrong",
                   "method": "llm", "reviewer": "test-judge", "reviews": []}
        with self.assertRaises(ValueError):
            feedback.calibration(self.assignments, decisions, tasks, answers)

    def test_cli_calibration_uses_saved_tasks_and_preserves_partial_llm_coverage(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            comparison.review.evaluation.save_json(root / "organizer.json", {"schema_version": 1, "rubric_version": comparison.RUBRIC, "assignments": self.assignments})
            comparison.review.evaluation.save_json(root / "decisions.json", confirmed_document(self.assignments))
            tasks = comparison.automatic_tasks(comparison.read_pairs(REPO_ROOT / "evals/blind-comparison-example.json"))
            comparison.review.evaluation.save_json(root / "tasks.json", tasks)
            answers = {**{k: tasks[k] for k in ("schema_version", "rubric_version", "task_sha256")},
                       "method": "llm", "reviewer": "test-judge", "reviews": []}
            comparison.review.evaluation.save_json(root / "answers.json", answers)
            args = ["calibrate", "--organizer", str(root / "organizer.json"), "--decisions", str(root / "decisions.json"),
                    "--tasks", str(root / "tasks.json"), "--llm-answers", str(root / "answers.json"), "--out-dir", str(root / "calibration")]
            self.assertEqual(feedback.main(args), 0)
            self.assertEqual(comparison.review.read_json(root / "calibration/calibration.json")["llm_missing"], 6)
            self.assertTrue((root / "calibration/calibration.md").exists())
            self.assertEqual(feedback.main(args), 2)

    def test_cli_does_not_overwrite_decisions_or_source_answers(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            organizer = root / "organizer.json"
            comparison.review.evaluation.save_json(organizer, {"schema_version": 1, "rubric_version": comparison.RUBRIC, "assignments": self.assignments})
            original = organizer.read_bytes()
            args = ["prepare", "--organizer", str(organizer), "--out-dir", str(root / "confirmation")]
            self.assertEqual(feedback.main(args), 0)
            path = root / "confirmation/decisions.json"
            comparison.review.evaluation.save_json(path, confirmed_document(self.assignments))
            before = path.read_bytes()
            self.assertEqual(feedback.main(args), 2)
            self.assertEqual(path.read_bytes(), before)
            export = ["export", "--organizer", str(organizer), "--decisions", str(path), "--out-dir", str(root / "regression")]
            self.assertEqual(feedback.main(export), 0)
            self.assertEqual(organizer.read_bytes(), original)
            self.assertTrue((root / "regression/regression-cases.json").exists())


if __name__ == "__main__":
    unittest.main()
