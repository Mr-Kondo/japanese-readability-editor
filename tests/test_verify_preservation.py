"""scripts/verify_preservation.py のテスト。"""

import json
import unittest
from pathlib import Path

from helpers import FIXTURES, SCRIPTS_DIR, load_module, run_script, temporary_directory

verify = load_module("verify_preservation", SCRIPTS_DIR / "verify_preservation.py")
SCRIPT = SCRIPTS_DIR / "verify_preservation.py"


def fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


class CompareTest(unittest.TestCase):
    def test_inserting_line_breaks_and_blank_lines_only_passes(self):
        result = verify.compare(fixture("before.md"), fixture("after_split.md"))
        self.assertTrue(result["identical"])
        self.assertEqual(result["before_paragraphs"], 1)
        self.assertEqual(result["after_paragraphs"], 4)

    def test_changing_a_character_fails(self):
        result = verify.compare(fixture("before.md"), fixture("after_changed_char.md"))
        self.assertFalse(result["identical"])
        diff = result["first_difference"]
        self.assertIn("である", diff["before_context"])
        self.assertIn("だ", diff["after_context"])

    def test_changing_punctuation_fails(self):
        self.assertFalse(verify.compare("原因は、Aである。", "原因は、Aである.")["identical"])
        self.assertFalse(verify.compare("ただし、費用が増える。", "ただし費用が増える。")["identical"])

    def test_deleting_text_fails(self):
        result = verify.compare(fixture("before.md"), fixture("after_deleted.md"))
        self.assertFalse(result["identical"])
        self.assertGreater(result["before_chars"], result["after_chars"])

    def test_adding_text_fails(self):
        self.assertFalse(verify.compare("あいう。", "あいう。えお。")["identical"])

    def test_reordering_fails(self):
        self.assertFalse(verify.compare("あ。い。", "い。あ。")["identical"])

    def test_all_kinds_of_whitespace_are_ignored(self):
        before = "一つ目。二つ目。\n"
        after = "一つ目。\r\n\r\n\t二つ目。　 \n\n"
        self.assertTrue(verify.compare(before, after)["identical"])

    def test_first_difference_reports_position_and_lines(self):
        result = verify.compare("あいう\n\nえお", "あいう\n\nえか")
        diff = result["first_difference"]
        self.assertEqual(diff["position"], 5)
        self.assertEqual(diff["before_line"], 3)
        self.assertEqual(diff["after_line"], 3)

    def test_difference_at_the_end_when_one_side_is_a_prefix(self):
        diff = verify.compare("あいう", "あい")["first_difference"]
        self.assertEqual(diff["position"], 3)
        self.assertIsNone(diff["after_line"])

    def test_whitespace_inside_english_is_a_known_blind_spot(self):
        # 保証するのは「空白以外の文字が同じ」ことだけ。意味の保存は保証しない。
        self.assertTrue(verify.compare("API key", "APIkey")["identical"])


class CommandLineTest(unittest.TestCase):
    def test_exit_code_zero_when_identical(self):
        code, out, _ = run_script(SCRIPT, str(FIXTURES / "before.md"), str(FIXTURES / "after_split.md"))
        self.assertEqual(code, 0)
        self.assertIn("OK", out)
        self.assertIn("paragraphs: 1 -> 4", out)

    def test_exit_code_one_when_different(self):
        for name in ("after_changed_char.md", "after_changed_punct.md", "after_deleted.md"):
            with self.subTest(name=name):
                code, out, _ = run_script(SCRIPT, str(FIXTURES / "before.md"), str(FIXTURES / name))
                self.assertEqual(code, 1)
                self.assertIn("FAIL", out)
                self.assertIn("first difference", out)

    def test_exit_code_two_when_a_file_is_missing(self):
        code, _, err = run_script(SCRIPT, str(FIXTURES / "before.md"), str(FIXTURES / "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("error", err)
        self.assertNotIn("Traceback", err)

    def test_json_output(self):
        code, out, _ = run_script(SCRIPT, "--json", str(FIXTURES / "before.md"), str(FIXTURES / "after_deleted.md"))
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(data["identical"])
        self.assertIn("first_difference", data)

    def test_quiet_prints_nothing(self):
        code, out, err = run_script(SCRIPT, "-q", str(FIXTURES / "before.md"), str(FIXTURES / "after_split.md"))
        self.assertEqual((code, out, err), (0, "", ""))

    def test_stdin_can_replace_one_side(self):
        code, _, _ = run_script(SCRIPT, "-q", str(FIXTURES / "before.md"), "-", stdin=fixture("after_split.md"))
        self.assertEqual(code, 0)

    def test_both_sides_from_stdin_is_rejected(self):
        code, _, err = run_script(SCRIPT, "-", "-", stdin="あ")
        self.assertEqual(code, 2)
        self.assertIn("stdin", err)

    def test_help_states_what_is_and_is_not_guaranteed(self):
        code, out, _ = run_script(SCRIPT, "--help")
        self.assertEqual(code, 0)
        self.assertIn("空白以外の文字列が変更されていないこと", out)
        self.assertIn("意味の保存は保証しない", out)

    def test_module_docstring_states_the_limit(self):
        self.assertIn("意味の保存", verify.__doc__)
        self.assertIn("保証しないこと", verify.__doc__)

    def test_files_are_not_modified(self):
        with temporary_directory() as tmp:
            before = Path(tmp) / "before.md"
            after = Path(tmp) / "after.md"
            before.write_text("あ。い。\n", encoding="utf-8")
            after.write_text("あ。\n\nい。\n", encoding="utf-8")
            snapshot = (before.read_bytes(), after.read_bytes())
            run_script(SCRIPT, str(before), str(after))
            self.assertEqual((before.read_bytes(), after.read_bytes()), snapshot)


if __name__ == "__main__":
    unittest.main()
