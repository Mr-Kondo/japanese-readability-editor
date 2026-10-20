"""変化の記録(本文を含まない選択式の JSON)を出す配布スクリプト。入力はテスト内で組み立てる人工の文章。"""
import json
import re
import unittest
import uuid
from pathlib import Path

from helpers import SCRIPTS_DIR, run_script, temporary_directory

SCRIPT = SCRIPTS_DIR / "make_change_report.py"
ORIGINAL = "管理者の承認後、30分以内に実行できます。\nなお詳細はhttps://canary.example/path を参照してください。\n"
RESULT = "管理者が承認すれば、必ず30分以内に実行されます。\n"
STATUSES = {"no_candidate", "candidate", "ok", "problem"}
METHODS = {"deterministic", "human", "model_self_report"}


class MakeChangeReportTest(unittest.TestCase):
    def setUp(self):
        self.folder = temporary_directory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.original = self.write("before.md", ORIGINAL)
        self.result = self.write("after.md", RESULT)

    def write(self, name, text):
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def run_report(self, *extra, original=None, result=None):
        return run_script(SCRIPT, "--original", original or self.original, "--result", result or self.result, *extra)

    def report(self, *extra, **files):
        code, out, err = self.run_report(*extra, **files)
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_every_check_has_a_fixed_status_and_method_and_the_changes_show_up(self):
        report = self.report("--mode", "B", "--model", "claude-sonnet-5-5")
        self.assertEqual((report["kind"], report["evidence_status"]), ("jre-change-report", "reported_not_independently_verified"))
        self.assertEqual(report["context"]["mode"], "B")
        self.assertEqual(set(report["checks"]), {"numbers", "urls", "code", "terms", "added_content", "omitted_content",
                                                 "negation", "modality", "style"})
        for check in report["checks"].values():
            self.assertIn(check["status"], STATUSES)
            self.assertIn(check["method"], METHODS)
        self.assertEqual(report["checks"]["urls"], {"status": "candidate", "method": "deterministic", "direction": ["removed"]})
        self.assertEqual(report["checks"]["omitted_content"]["direction"], ["removed"])
        self.assertEqual(report["checks"]["modality"]["status"], "candidate")
        self.assertEqual(report["checks"]["numbers"], {"status": "no_candidate", "method": "deterministic", "direction": []})
        self.assertEqual(report["readability"]["chars"], "decreased")

    def test_the_report_has_no_text_path_or_count_from_the_inputs(self):
        folder = self.root / "CANARYDIR"
        folder.mkdir()
        original = folder / "CANARYFILE-before.md"
        original.write_text(ORIGINAL + "カナリア固有の文です。\n", encoding="utf-8")
        _, out, _ = self.run_report(original=str(original))
        for canary in ("CANARY", "カナリア", "承認", "canary.example", "30", "before", self.folder.name):
            self.assertNotIn(canary, out)
        self.assertEqual(set(json.loads(out)), {"schema_version", "kind", "case_id", "evidence_status", "context", "checks", "readability"})

    def test_unchanged_text_has_no_candidates_and_same_readability(self):
        report = self.report(result=self.original)
        self.assertEqual({check["status"] for check in report["checks"].values()}, {"no_candidate"})
        self.assertEqual(set(report["readability"].values()), {"same"})

    def test_case_id_is_a_fresh_random_uuid(self):
        first, second = self.report()["case_id"], self.report()["case_id"]
        self.assertNotEqual(first, second)
        self.assertEqual(uuid.UUID(first).version, 4)

    def test_review_sets_the_method_by_who_reviewed(self):
        human = self.report("--review", "urls=ok", "--review", "modality=problem", "--reviewed-by", "human")
        self.assertEqual((human["checks"]["urls"]["status"], human["checks"]["urls"]["method"]), ("ok", "human"))
        self.assertEqual(human["checks"]["modality"]["status"], "problem")
        model = self.report("--review", "urls=ok", "--reviewed-by", "model")
        self.assertEqual(model["checks"]["urls"]["method"], "model_self_report")

    def test_invalid_reviews_are_refused_without_output(self):
        for extra in (("--review", "urls=ok"),  # 主体がない
                      ("--review", "numbers=ok", "--reviewed-by", "human"),  # 候補が挙がっていない検査
                      ("--review", "urls=fine", "--reviewed-by", "human"),
                      ("--review", "nothing=ok", "--reviewed-by", "human"),
                      ("--review", "urls=ok", "--review", "urls=problem", "--reviewed-by", "human")):
            code, out, err = self.run_report(*extra)
            self.assertEqual((code, out), (2, ""), extra)
            self.assertIn("make_change_report failed", err)

    def test_free_text_model_and_empty_or_missing_inputs_are_refused(self):
        self.assertEqual(self.run_report("--model", "my secret project")[0], 2)
        self.assertEqual(self.run_report(original=self.write("empty.md", "\n"))[0], 2)
        self.assertEqual(self.run_report(result=str(self.root / "missing.md"))[0], 2)

    def test_model_defaults_to_unknown_and_the_date_is_a_day(self):
        context = self.report()["context"]
        self.assertEqual(context["model"], "unknown")
        self.assertRegex(context["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(re.match(r"^\d+\.\d+\.\d+$", context["skill_version"]))


class ExampleTest(unittest.TestCase):
    def test_the_documented_example_matches_the_scripts_checks(self):
        from helpers import REPO_ROOT, load_module
        script = load_module("make_change_report", SCRIPT)
        example = json.loads((REPO_ROOT / "docs" / "change-report-example.json").read_text(encoding="utf-8"))
        self.assertEqual(example["context"]["origin"], "artificial")
        self.assertEqual(list(example["checks"]), list(script.CHECKS))
        self.assertEqual(list(example["readability"]), list(script.METRICS))
        self.assertEqual(example["context"]["skill_version"], (REPO_ROOT / "skills" / "japanese-readability-editor" / "VERSION").read_text().strip())
