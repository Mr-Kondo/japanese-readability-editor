"""評価の欠落・採点誤りを合格扱いしない。モデル品質のテストではなく、通信は実行しない。"""
import copy
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from helpers import TOOLS_DIR, load_module, temporary_directory

evaluation = load_module("evaluate_readability", TOOLS_DIR / "evaluate_readability.py")
CASE = {"id": "one", "domain": "test", "covers": ["条件"], "request": "推敲して。", "context": "",
        "text": "承認後に実行する。", "preserve": ["承認後"], "forbid": ["承認前に実行"]}
CONTROL = {"id": "control", "text": "明日行う予定です。", "context": "", "candidate": "実施しました。", "expected": "fail"}
SUITE = {"schema_version": 1, "cases": [CASE], "controls": [CONTROL]}


def complete_record():
    record = {"suite": copy.deepcopy(SUITE), "outputs": [
        {"id": f"g{i}", "case_id": "one", "text": CASE["text"], "model_ids": ["test-model"]} for i in range(3)]}
    record["grading_items"] = evaluation.grading_items(record)
    judgments = [{"id": e["id"], "status": "fail" if e["kind"] == "control" else "pass", "reason": "根拠"}
                 for e in record["grading_items"]]
    record["grading_calls"] = [{"model_ids": ["test-model"], "judgments": judgments}]
    return record


class ReadabilityEvaluationTest(unittest.TestCase):
    def test_missing_grades_control_errors_uncertainty_and_model_drift_hold(self):
        self.assertEqual(evaluation.summary(complete_record())["decision"], "PASS_ON_TEST_SET")
        for fault in ("missing", "control", "uncertain", "model"):
            with self.subTest(fault=fault):
                record = complete_record()
                judgments = record["grading_calls"][0]["judgments"]
                if fault == "missing":
                    judgments.pop()
                elif fault == "model":
                    record["grading_calls"][0]["model_ids"] = ["other-model"]
                else:
                    kind = "control" if fault == "control" else "generated"
                    target = next(e["id"] for e in record["grading_items"] if e["kind"] == kind)
                    next(j for j in judgments if j["id"] == target)["status"] = "pass" if fault == "control" else "uncertain"
                self.assertEqual(evaluation.summary(record)["decision"], "HOLD")

    def test_malformed_or_duplicate_grading_never_silently_passes(self):
        good = {"id": "j1", "status": "pass", "reason": "保持"}
        payloads = [[], [good, good], [{**good, "status": "ok"}], [{**good, "id": []}], [{**good, "reason": ""}]]
        for payload in payloads:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                evaluation.parse_judgments(json.dumps({"judgments": payload}), {"j1"})

    def test_skill_dir_generates_through_the_installed_skill_with_tools_and_grading_stays_isolated(self):
        calls = []

        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            body = json.dumps({"result": "出力", "modelUsage": {"test-model": {}}, "is_error": False})
            return subprocess.CompletedProcess(command, 0, stdout=body, stderr="")

        with temporary_directory() as tmp, patch.object(evaluation.subprocess, "run", side_effect=fake_run):
            skill = Path(tmp) / "skill"
            skill.mkdir()
            (skill / "SKILL.md").write_text("x", encoding="utf-8")
            record = {"skill_dir": str(skill), "suite": copy.deepcopy(SUITE), "outputs": []}
            with patch.object(evaluation, "REPEATS", 1):
                evaluation.generate(record, Path(tmp))
            generation = calls[0][0]
            self.assertNotIn("--safe-mode", generation)
            self.assertNotIn("--tools", generation)
            self.assertIn("project", generation)
            self.assertNotIn("SKILL_FILES", calls[0][1]["input"])
            self.assertEqual(record["outputs"][0]["text"], "出力")
            evaluation.invoke("採点", Path(tmp) / "judge.json")  # 採点は従来どおり、ツールなしの隔離
            self.assertIn("--safe-mode", calls[1][0])

    def test_case_ids_and_repeats_narrow_the_run_and_unknown_ids_are_refused(self):
        other = {**CASE, "id": "two"}
        with temporary_directory() as tmp, patch.object(evaluation.subprocess, "run", side_effect=AssertionError("network forbidden")):
            suite = Path(tmp) / "suite.json"
            suite.write_text(json.dumps({**SUITE, "cases": [CASE, other]}), encoding="utf-8")
            self.assertEqual(evaluation.main(["--suite", str(suite), "--out-dir", str(Path(tmp) / "a"), "--case-ids", "two", "--repeats", "5"]), 0)
            record = json.loads((Path(tmp) / "a" / "run.json").read_text(encoding="utf-8"))
            self.assertEqual([c["id"] for c in record["suite"]["cases"]], ["two"])
            self.assertEqual(record["repeats"], 5)
            self.assertEqual(evaluation.main(["--suite", str(suite), "--out-dir", str(Path(tmp) / "b"), "--case-ids", "nope"]), 2)
        evaluation.REPEATS = 3  # main() が変えたモジュール変数を戻す

    def test_prepare_makes_no_model_calls_and_refuses_to_overwrite(self):
        with temporary_directory() as tmp, patch.object(evaluation.subprocess, "run", side_effect=AssertionError("network forbidden")):
            suite = Path(tmp) / "suite.json"
            suite.write_text(json.dumps(SUITE), encoding="utf-8")
            out = Path(tmp) / "run"
            args = ["--suite", str(suite), "--out-dir", str(out)]
            self.assertEqual(evaluation.main(args), 0)
            before = (out / "run.json").read_bytes()
            self.assertEqual(evaluation.main(args), 2)
            self.assertEqual((out / "run.json").read_bytes(), before)

    def test_failed_model_call_preserves_partial_outputs_and_error_evidence(self):
        raw = json.dumps({"result": CASE["text"], "modelUsage": {"test-model": {}}, "is_error": False})
        responses = [subprocess.CompletedProcess([], 0, raw, ""), subprocess.TimeoutExpired("claude", 180)]
        with temporary_directory() as tmp:
            folder = Path(tmp)
            record = {"suite": copy.deepcopy(SUITE), "skill_files": {}, "outputs": [], "grading_calls": []}
            with patch.object(evaluation.subprocess, "check_output", return_value="test-cli"), \
                 patch.object(evaluation.subprocess, "run", side_effect=responses), self.assertRaises(RuntimeError):
                evaluation.execute(record, folder)
            saved = json.loads((folder / "run.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "execution_failed")
            self.assertEqual(len(saved["outputs"]), 1)
            self.assertNotIn("summary", saved)
            self.assertIn("error", json.loads((folder / "g002.json").read_text(encoding="utf-8")))

    def test_invalid_model_responses_leave_raw_evidence_and_raise(self):
        valid = {"result": "本文", "modelUsage": {"test-model": {}}, "is_error": False}
        responses = ["not JSON", json.dumps([]), json.dumps({**valid, "is_error": True}),
                     json.dumps({**valid, "result": ""}), json.dumps({**valid, "modelUsage": []})]
        for response in responses:
            with self.subTest(response=response), temporary_directory() as tmp:
                path = Path(tmp) / "call.json"
                completed = subprocess.CompletedProcess([], 0, response, "")
                with patch.object(evaluation.subprocess, "run", return_value=completed), self.assertRaises((ValueError, RuntimeError)):
                    evaluation.invoke("入力", path)
                self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["stdout"], response)

    def test_invalid_suite_is_rejected_before_output_is_created(self):
        for field in ("cases", "controls"):
            with self.subTest(field=field), temporary_directory() as tmp:
                suite = copy.deepcopy(SUITE)
                suite[field] *= 2
                path = Path(tmp) / "suite.json"
                path.write_text(json.dumps(suite), encoding="utf-8")
                out = Path(tmp) / "run"
                self.assertEqual(evaluation.main(["--suite", str(path), "--out-dir", str(out)]), 2)
                self.assertFalse(out.exists())

    def test_model_option_changes_only_the_installed_generation_flags(self):
        with patch.object(evaluation, "MODEL", "haiku"):
            flags = evaluation.installed_flags()
        self.assertEqual(flags[flags.index("--model") + 1], "haiku")
        self.assertEqual(evaluation.INSTALLED_FLAGS[evaluation.INSTALLED_FLAGS.index("--model") + 1], "sonnet")
        self.assertEqual(evaluation.FLAGS[evaluation.FLAGS.index("--model") + 1], "sonnet")


if __name__ == "__main__":
    unittest.main()
