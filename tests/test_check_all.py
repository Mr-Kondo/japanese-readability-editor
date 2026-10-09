"""tools/check_all.py(検証とテストをまとめて実行するコマンド)のテスト。テスト自身を再帰的に実行しない。"""

import shutil
import unittest
from pathlib import Path

from helpers import REPO_ROOT, SKILL_DIR, TOOLS_DIR, load_module, run_script, temporary_directory

SCRIPT = TOOLS_DIR / "check_all.py"
check_all = load_module("check_all", SCRIPT)


class CheckAllTest(unittest.TestCase):
    def test_validation_only_passes_on_the_repository(self):
        code, out, err = run_script(SCRIPT, "--skip-tests")
        self.assertEqual(code, 0, out + err)
        self.assertIn("[ok] validate the skill", out)
        self.assertIn("[ok] validate the kokugo rules", out)
        self.assertIn("[ok] check the generated kokugo documents", out)
        self.assertNotIn("run the tests", out)
        self.assertIn("all checks passed", out)

    def test_broken_rule_data_makes_it_fail(self):
        with temporary_directory() as tmp:
            data = Path(tmp) / "data"
            shutil.copytree(SKILL_DIR / "data", data)
            (data / "kokugo-rules.json").write_text((data / "kokugo-rules.json").read_text(encoding="utf-8").replace("KOKUGO-KANA-001", "KOKUGO-KANA-002", 1),
                                                    encoding="utf-8")
            code, out, _ = run_script(SCRIPT, "--skip-tests", "--data-dir", str(data))
            self.assertEqual(code, 1)
            self.assertIn("[FAILED] validate the kokugo rules", out)
            self.assertIn("some checks FAILED", out)

    def test_a_broken_skill_makes_it_fail(self):
        with temporary_directory() as tmp:
            code, out, _ = run_script(SCRIPT, "--skip-tests", "--skill-dir", str(Path(tmp) / "japanese-readability-editor"))
            self.assertEqual(code, 1)
            self.assertIn("[FAILED] validate the skill", out)

    def test_the_test_summary_reports_counts(self):
        ok = "....\n----------------------------------------------------------------------\nRan 562 tests in 16.8s\n\nOK (skipped=1)\n"
        self.assertEqual(check_all.summarize_tests(ok), "562 run, 561 passed, 0 failed, 0 errors, 1 skipped (16.8s)")
        bad = "Ran 10 tests in 0.5s\n\nFAILED (failures=2, errors=1, skipped=3)\n"
        self.assertEqual(check_all.summarize_tests(bad), "10 run, 4 passed, 2 failed, 1 errors, 3 skipped (0.5s)")
        self.assertEqual(check_all.summarize_tests("OK\n"), "no test summary found")

    def test_it_does_not_use_the_network(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for module in ("urllib", "socket", "http.client"):
            self.assertNotIn(f"import {module}", text)

    def test_ci_runs_the_kokugo_validation(self):
        ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("validate_kokugo_rules.py", ci)


if __name__ == "__main__":
    unittest.main()
