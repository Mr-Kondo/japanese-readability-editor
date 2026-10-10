"""評価ケースの構造検査。モデルの挙動や文学的品質は判定しない。"""
import json
import unittest
from helpers import REPO_ROOT

EVALS = REPO_ROOT / "evals"
DATA = json.loads((EVALS / "fiction-cases.json").read_text(encoding="utf-8"))
CASES = DATA["cases"]

class FictionEvalStructureTest(unittest.TestCase):
    def test_version_and_unique_ids(self):
        self.assertEqual(DATA["schema_version"], 1)
        self.assertEqual(len(CASES), 24)
        self.assertEqual(len(CASES), len({c["id"] for c in CASES}))

    def test_required_content(self):
        fields = {"id", "covers", "input", "expected_mode", "expected_operation",
                  "facts_to_preserve", "forbidden_changes", "evaluation_method"}
        for c in CASES:
            with self.subTest(case=c["id"]):
                self.assertTrue(fields.issubset(c))
                self.assertTrue(c["input"].strip())
                for key in ("facts_to_preserve", "forbidden_changes"):
                    self.assertTrue(c[key])
                    self.assertTrue(all(isinstance(v, str) and v.strip() for v in c[key]))
                self.assertEqual(c["evaluation_method"]["kind"], "human-rubric")
                self.assertTrue(c["evaluation_method"]["criteria"])
                self.assertIsInstance(c["evaluation_method"]["automated_checks"], list)

    def test_eighteen_topics(self):
        expected = set(range(1, 19))
        self.assertEqual({int(k) for k in DATA["coverage_labels"]}, expected)
        self.assertEqual({v for c in CASES for v in c["covers"]}, expected)
        self.assertTrue(all(type(v) is int and v in expected for c in CASES for v in c["covers"]))

    def test_modes_and_operations(self):
        self.assertEqual({c["expected_mode"] for c in CASES}, {"A", "B", "C", "D", "undetermined"})
        self.assertEqual({c["expected_operation"] for c in CASES if c["expected_mode"] == "D"},
                         {"plan", "draft", "continue", "revise", "critique", "clarify"})
        by_id = {c["id"]: c for c in CASES}
        for key in ("r11", "r12", "e20-missing-revise", "e21-missing-critique", "e24-no-material"):
            self.assertEqual(by_id[key]["expected_operation"], "clarify")

    def test_c_case_documents_strict_and_raw_preservation(self):
        c = next(c for c in CASES if c["expected_mode"] == "C")
        self.assertIn(c["target_text"], c["input"])
        checks = "\n".join(c["evaluation_method"]["automated_checks"])
        for phrase in ("--strict", "空白", "CRLF", "BOM", "生バイト", "test_fiction_integration.py"):
            self.assertIn(phrase, checks)

    def test_limited_run_input_links(self):
        self.assertEqual(DATA["suite_execution_status"], "partial")
        record = json.loads((EVALS / DATA["representative_run_record"]).read_text(encoding="utf-8"))
        by_id = {c["id"]: c for c in record["cases"]}
        linked = [c for c in CASES if "execution_evidence" in c]
        self.assertEqual(len(linked), 12)
        for c in linked:
            self.assertEqual(c["input"], by_id[c["execution_evidence"]["record_case_id"]]["input"])
        readme = (EVALS / "README.md").read_text(encoding="utf-8")
        self.assertIn("モデルを呼ばず", readme)
        self.assertIn("完全一致を正解にしない", readme)
