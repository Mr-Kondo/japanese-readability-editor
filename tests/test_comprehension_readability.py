"""単一版の配布、正解非公開、割付に結び付いた採点を確認する。"""
import copy
from pathlib import Path
import unittest

from helpers import REPO_ROOT, TOOLS_DIR, load_module, temporary_directory

comprehension = load_module("comprehension_readability", TOOLS_DIR / "comprehension_readability.py")
review = comprehension.review
EXAMPLE = REPO_ROOT / "evals/comprehension-example.json"


def answer_file(assigned):
    public = assigned["public"]
    return {**{k: public[k] for k in ("schema_version", "rubric_version", "task_sha256", "reviewer")},
            "method": "human", "responses": []}


class ComprehensionReadabilityTest(unittest.TestCase):
    def test_single_candidate_assignments_balance_both_readers_and_documents_without_keys(self):
        with temporary_directory() as tmp:
            root = Path(tmp) / "manual"
            self.assertEqual(comprehension.main(["prepare", "--input", str(EXAMPLE), "--readers", "r1", "r2", "r3", "--out-dir", str(root)]), 0)
            assignments = comprehension.read_assignments(root / "organizer.json")
            for assigned in assignments:
                self.assertEqual(len({c["document_id"] for c in assigned["public"]["cases"]}), 2)
                self.assertEqual(len({m["variant"] for m in assigned["mapping"].values()}), 2)
            for case_id in ("pair-001", "pair-002"):
                counts = [a["mapping"][case_id]["variant"] for a in assignments]
                self.assertEqual(sorted(counts.count(v) for v in set(counts)), [1, 2])
            for folder in root.glob("reader-*"):
                html = (folder / "review.html").read_text(encoding="utf-8")
                for private in ("baseline", "revision", "answer_index", "verified_by", "evidence", '"original"'):
                    self.assertNotIn(private, html)

    def test_grading_distinguishes_wrong_unknown_missing_and_preserves_document_results(self):
        pairs = comprehension.read_source(EXAMPLE)
        base = comprehension.comparison.assignment(pairs, "organizer")
        assigned = comprehension.reader_assignment(pairs, base, "r1", "left")
        absent = comprehension.reader_assignment(pairs, base, "r2", "right")
        answers = answer_file(assigned)
        answers["responses"] = [
            {"id": "pair-001", "question_id": "approval", "choice": 0, "note": "承認条件を確認した。"},
            {"id": "pair-001", "question_id": "minutes", "choice": "unknown", "note": ""},
            {"id": "pair-002", "question_id": "contact", "choice": 2, "note": ""}]
        report = comprehension.summarize([assigned, absent], [answers])
        self.assertEqual((report["assigned_questions"], report["correct"], report["unknown"], report["missing"]), (6, 1, 1, 3))
        self.assertEqual(report["accuracy_completed"], 1 / 3)
        self.assertEqual(report["correct_rate_all_assigned"], 1 / 6)
        self.assertEqual(len(report["documents"]), 4)
        answers["responses"] = []
        self.assertIsNone(comprehension.summarize([assigned], [answers])["accuracy_completed"])

    def test_bad_answers_never_create_output_or_mix_readers(self):
        pairs = comprehension.read_source(EXAMPLE)
        assigned = comprehension.reader_assignment(pairs, comprehension.comparison.assignment(pairs, "organizer"), "r1", "left")
        valid = {"id": "pair-001", "question_id": "approval", "choice": 0, "note": ""}
        for fault in ("reader", "hash", "duplicate", "unknown_id", "bool", "choice", "null", "note"):
            with self.subTest(fault=fault):
                answers = answer_file(assigned)
                answers["responses"] = [copy.deepcopy(valid)]
                response = answers["responses"][0]
                if fault == "reader": answers["reviewer"] = "other"
                elif fault == "hash": answers["task_sha256"] = "wrong"
                elif fault == "duplicate": answers["responses"] *= 2
                elif fault == "unknown_id": response["question_id"] = "missing"
                elif fault == "bool": response["choice"] = True
                elif fault == "choice": response["choice"] = 50
                elif fault == "null": answers["responses"] = [None]
                elif fault == "note": response["note"] = []
                with self.assertRaises(ValueError): comprehension.summarize([assigned], [answers])

    def test_unverified_questions_and_repeated_sources_are_rejected_and_markup_is_escaped(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "input.json"
            for fault in ("answer", "evidence", "verification", "repeat", "options"):
                with self.subTest(fault=fault):
                    source = review.read_json(EXAMPLE)
                    question = source["cases"][0]["questions"][0]
                    if fault == "answer": question["answer_index"] = True
                    elif fault == "evidence": question["evidence"] = "原文にない根拠"
                    elif fault == "verification": question["verified_by"] = ""
                    elif fault == "repeat": source["cases"][1]["document_id"] = source["cases"][0]["document_id"]
                    elif fault == "options": question["options"] = ["same", "same"]
                    review.evaluation.save_json(path, source)
                    with self.assertRaises(ValueError): comprehension.read_source(path)
            source = review.read_json(EXAMPLE)
            hostile = '</script><img src=x onerror="alert(1)">'
            source["cases"][0]["questions"][0]["prompt"] = hostile
            review.evaluation.save_json(path, source)
            folder = Path(tmp) / "safe"
            comprehension.prepare(comprehension.read_source(path), ["r1"], folder)
            html = (folder / "reader-001/review.html").read_text(encoding="utf-8")
            self.assertNotIn(hostile, html)
            self.assertIn("\\u003c/script>", html)
            with self.assertRaises(FileExistsError): comprehension.prepare(comprehension.read_source(path), ["r1"], folder)


if __name__ == "__main__":
    unittest.main()
