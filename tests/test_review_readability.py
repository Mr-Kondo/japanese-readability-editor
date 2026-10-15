"""人手とモデルの結果を混同せず、欠測・保存失敗・意味未判定を保持する。"""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from helpers import REPO_ROOT, TOOLS_DIR, load_module, temporary_directory

review = load_module("review_readability", TOOLS_DIR / "review_readability.py")
EXAMPLE = REPO_ROOT / "evals" / "human-review-example.json"


def answers(tasks, method="human", reviewer="reader-1"):
    return {"schema_version": 1, "rubric_version": review.RUBRIC, "task_sha256": tasks["task_sha256"],
            "method": method, "reviewer": reviewer, "reviews": [
                {"id": tasks["cases"][0]["id"], "contract": "fail", "preference": "uncertain",
                 "scores": {"readability": 4, "naturalness": None, "style": 2},
                 "reason": "「30分」が「3分」に変わり、承認条件がなくなった。", "suggestion": "承認条件と30分を戻す。"}]}


class ReviewReadabilityTest(unittest.TestCase):
    def test_offline_reports_number_change_without_claiming_semantic_pass(self):
        with temporary_directory() as tmp:
            folder = Path(tmp) / "auto"
            self.assertEqual(review.main(["auto", "--input", str(EXAMPLE), "--out-dir", str(folder)]), 0)
            report = review.read_json(folder / "automatic.json")
            first, second = report["results"]
            self.assertEqual(first["contract"], "uncertain")
            self.assertEqual(first["comparison"]["numbers"]["missing"][0]["text"], "30分")
            self.assertEqual(first["comparison"]["numbers"]["added"][0]["text"], "3分")
            self.assertTrue(any(f["category"] == "numbers" for f in first["findings"]))
            self.assertGreater(first["metrics"]["original"]["metrics"]["chars"], first["metrics"]["candidate"]["metrics"]["chars"])
            self.assertEqual(second["contract"], "pass")
            self.assertIn("原文", (folder / "automatic.md").read_text(encoding="utf-8"))

    def test_c_rejects_removed_whitespace_bom_crlf_and_linebreaks(self):
        cases = [("a\nb", "a\n\nb", True), ("a b", "a\nb", False),
                 ("a\r\nb", "a\nb", False), ("\ufeffa", "a", False), ("a\nb", "ab", False),
                 ("a\nb", "a\nb", True), ("a", "a\n", True)]
        for original, candidate, expected in cases:
            with self.subTest(original=original, candidate=candidate):
                task = {"id": "c", "mode": "C", "original": original, "candidate": candidate}
                self.assertEqual(review.automatic(task)["contract"], "pass" if expected else "fail")

    def test_existing_run_import_retains_a_b_modes_and_repeated_document_ids(self):
        tasks = review.read_tasks(REPO_ROOT / "evals/readability-generalization-run/run.json")
        self.assertEqual(len(tasks["cases"]), 48)
        self.assertEqual(sum(t["mode"] == "A" for t in tasks["cases"]), 3)
        self.assertEqual(len({t["document_id"] for t in tasks["cases"]}), 16)
        self.assertTrue(tasks["cases"][0]["provenance"]["run_sha256"])

    def test_partial_answers_keep_missing_and_llm_separate_from_human(self):
        tasks = review.read_tasks(EXAMPLE)
        result = review.aggregate(tasks, [answers(tasks), answers(tasks, "llm", "model")])
        self.assertEqual(len(result["groups"]), 4)
        human_b = next(g for g in result["groups"] if g["method"] == "human" and g["mode"] == "B")
        human_c = next(g for g in result["groups"] if g["method"] == "human" and g["mode"] == "C")
        self.assertEqual(human_b["contract_counts"], {"fail": 1})
        self.assertEqual(human_b["preference_among_pass"], {})
        self.assertEqual(human_b["scores"]["naturalness"], {"n": 0, "missing": 1, "distribution": {}, "mean": None})
        self.assertEqual(human_c["missing_reviews"], 1)
        self.assertEqual(human_c["completed_reviews"], 0)

    def test_malformed_duplicate_and_mismatched_answers_rejected(self):
        tasks = review.read_tasks(EXAMPLE)
        for fault in ("hash", "rubric", "duplicate", "id", "score", "bool", "reason", "preference", "unknown", "array"):
            with self.subTest(fault=fault):
                doc = answers(tasks)
                entry = doc["reviews"][0]
                if fault == "hash": doc["task_sha256"] = "other"
                elif fault == "rubric": doc["rubric_version"] = "other"
                elif fault == "duplicate": doc["reviews"] *= 2
                elif fault == "id": entry["id"] = []
                elif fault == "score": entry["scores"]["readability"] = 6
                elif fault == "bool": entry["scores"]["readability"] = True
                elif fault == "reason": entry["reason"] = " "
                elif fault == "preference": entry["preference"] = "candidate"
                elif fault == "unknown": entry["id"] = "unknown"
                elif fault == "array": doc["reviews"] = {}
                with self.assertRaises(ValueError): review.aggregate(tasks, [doc])
        with self.assertRaises(ValueError): review.aggregate(tasks, [answers(tasks), answers(tasks)])

    def test_invalid_input_and_existing_destination_never_overwritten(self):
        with temporary_directory() as tmp:
            folder = Path(tmp) / "manual"
            argv = ["prepare", "--input", str(EXAMPLE), "--out-dir", str(folder)]
            self.assertEqual(review.main(argv), 0)
            before = (folder / "tasks.json").read_bytes()
            self.assertEqual(review.main(argv), 2)
            self.assertEqual((folder / "tasks.json").read_bytes(), before)
            for payload in ({"schema_version": 1, "cases": []},
                            {"schema_version": 1, "outputs": {}, "suite": []},
                            {"schema_version": 1, "cases": [{"mode": "D"}]}):
                path = Path(tmp) / "invalid.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                out = Path(tmp) / "invalid-out"
                self.assertEqual(review.main(["prepare", "--input", str(path), "--out-dir", str(out)]), 2)
                self.assertFalse(out.exists())

    def test_html_escapes_hostile_text_and_summary_roundtrip_keeps_hash(self):
        with temporary_directory() as tmp:
            folder = Path(tmp)
            payload = review.read_json(EXAMPLE)
            hostile = '</script><img src=x onerror="alert(1)">'
            payload["cases"][0]["candidate"] = hostile
            path = folder / "hostile.json"
            review.evaluation.save_json(path, payload)
            tasks = review.read_tasks(path)
            html = review.render_manual(tasks)
            self.assertNotIn(hostile, html)
            self.assertIn("\\u003c/script>", html)
            review.evaluation.save_json(folder / "tasks.json", tasks)
            self.assertEqual(review.read_tasks(folder / "tasks.json")["task_sha256"], tasks["task_sha256"])
            review.evaluation.save_json(folder / "answers.json", answers(tasks))
            self.assertEqual(review.main(["summarize", "--input", str(folder / "tasks.json"), "--answers", str(folder / "answers.json"), "--out-dir", str(folder / "summary")]), 0)
            summary = review.read_json(folder / "summary" / "summary.json")
            self.assertIn("30分", summary["groups"][0]["qualitative"][0]["reason"])

    def test_model_failure_preserves_raw_error_and_partial_reviews(self):
        tasks = review.read_tasks(EXAMPLE)
        first_review = answers(tasks, "llm")["reviews"][0]
        response = json.dumps({"result": json.dumps(first_review, ensure_ascii=False), "modelUsage": {"test-model": {}}, "is_error": False})
        calls = [subprocess.CompletedProcess([], 0, response, ""), subprocess.TimeoutExpired("claude", 180)]
        with temporary_directory() as tmp, patch.object(review.evaluation.subprocess, "run", side_effect=calls):
            folder = Path(tmp)
            with self.assertRaises(RuntimeError): review.run_auto(tasks, folder, True)
            self.assertEqual(review.read_json(folder / "automatic.json")["status"], "failed")
            saved = review.read_json(folder / "llm-answers.json")
            self.assertEqual(len(saved["reviews"]), 1)
            self.assertEqual(saved["calls"][0]["model_ids"], ["test-model"])
            self.assertIn("error", review.read_json(folder / "judge-002.json"))
            self.assertFalse((folder / "summary.json").exists())

    def test_model_cannot_override_deterministic_c_failure(self):
        tasks = review.read_tasks(EXAMPLE)
        tasks["cases"] = [tasks["cases"][1]]
        tasks["cases"][0]["candidate"] = "改変しました。"
        judgment = {"contract": "pass", "scores": dict.fromkeys(review.DIMENSIONS, 5), "preference": "candidate", "reason": "問題なし", "suggestion": ""}
        response = json.dumps({"result": json.dumps(judgment), "modelUsage": {"test-model": {}}, "is_error": False})
        with temporary_directory() as tmp, patch.object(review.evaluation.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, response, "")):
            folder = Path(tmp)
            self.assertEqual(review.run_auto(tasks, folder, True), 1)
            saved = review.read_json(folder / "llm-answers.json")["reviews"][0]
            self.assertEqual(saved["contract"], "fail")
            self.assertEqual(saved["preference"], "uncertain")


if __name__ == "__main__":
    unittest.main()
