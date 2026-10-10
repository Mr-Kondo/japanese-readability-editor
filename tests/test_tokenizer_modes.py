"""compare_rewrite.py の SudachiPy あり/なしの経路と、tokenizer の表示のテスト。

SudachiPy がない経路は、入っている環境でも試せるよう、import を塞いだ別プロセスで実行する。
入っている経路は、SudachiPy と辞書が入っている環境だけで実行する。
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import SCRIPTS_DIR, load_module, run_script, temporary_directory

compare = load_module("compare_rewrite_for_tokenizer", SCRIPTS_DIR / "compare_rewrite.py")
SCRIPT = SCRIPTS_DIR / "compare_rewrite.py"

try:
    SUDACHI = compare.SudachiAnalyzer()
except ImportError:
    SUDACHI = None

# sudachipy を import できない環境を作ってから、スクリプトをそのまま実行する。
NO_SUDACHIPY = (
    "import runpy, sys\n"
    "sys.modules['sudachipy'] = None\n"
    "sys.argv = sys.argv[1:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)
# sudachipy は入っているが、辞書のパッケージ(sudachidict_*)がない環境。
NO_DICTIONARY = (
    "import runpy, sys, types\n"
    "fake = types.ModuleType('sudachipy')\n"
    "def Dictionary(dict=None):\n"
    "    raise ImportError('no dictionary package')\n"
    "fake.Dictionary = Dictionary\n"
    "fake.SplitMode = type('SplitMode', (), {'C': None})\n"
    "sys.modules['sudachipy'] = fake\n"
    "sys.argv = sys.argv[1:]\n"
    "runpy.run_path(sys.argv[0], run_name='__main__')\n"
)

BEFORE = (
    "# 手順\n\n"
    "設定値は100ミリ秒で、例外として管理者は除く。\n"
    "接続先は https://example.com/api/v1 で、`--force` を付けて実行する。\n"
    "この操作は元に戻せないとは限らない。\n"
)
AFTER = (
    "# 手順\n\n"
    "設定値は10秒で、管理者を含む。\n"
    "接続先は https://example.com/api/v2 で、`--yes` を付けて実行する。\n"
    "この操作は元に戻せる。\n"
)


def run_isolated(wrapper: str, *args: str):
    done = subprocess.run([sys.executable, "-c", wrapper, str(SCRIPT), *args], capture_output=True, text=True,
                          encoding="utf-8", timeout=60, env={**os.environ, "PYTHONUTF8": "1", "PYTHONDONTWRITEBYTECODE": "1"})
    return done.returncode, done.stdout, done.stderr


class TokenizerCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)
        self.before = self.tmp / "before.md"
        self.after = self.tmp / "after.md"
        self.before.write_text(BEFORE, encoding="utf-8")
        self.after.write_text(AFTER, encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()


class WithoutSudachiPyTest(TokenizerCase):
    def test_auto_falls_back_to_regex_and_says_so(self):
        for label, wrapper in (("import blocked", NO_SUDACHIPY), ("no dictionary package", NO_DICTIONARY)):
            with self.subTest(case=label):
                code, out, err = run_isolated(wrapper, str(self.before), str(self.after))
                self.assertEqual(code, 0, err)
                self.assertIn("tokenizer: regex", out)

    def test_json_reports_the_regex_tokenizer(self):
        for wrapper in (NO_SUDACHIPY, NO_DICTIONARY):
            code, out, err = run_isolated(wrapper, "--json", str(self.before), str(self.after))
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["tokenizer"], "regex")

    def test_requesting_sudachi_explains_how_to_install_it_and_does_not_install(self):
        for wrapper in (NO_SUDACHIPY, NO_DICTIONARY):
            code, out, err = run_isolated(wrapper, "--tokenizer", "sudachi", str(self.before), str(self.after))
            self.assertNotEqual(code, 0)
            self.assertIn("pip install sudachipy sudachidict-core", err)
            self.assertEqual(out, "")

    def test_the_regex_path_still_reports_the_meaning_changes(self):
        code, out, err = run_isolated(NO_SUDACHIPY, "--json", str(self.before), str(self.after))
        self.assertEqual(code, 0, err)
        data = json.loads(out)
        for kind in ("numbers", "urls", "code"):
            self.assertTrue(data[kind]["missing"] and data[kind]["added"], kind)
        self.assertEqual((data["markers"]["negation"]["before"], data["markers"]["negation"]["after"]), (2, 0))


@unittest.skipUnless(SUDACHI, "SudachiPy と辞書が入っていない")
class WithSudachiPyTest(TokenizerCase):
    def test_auto_uses_sudachi_and_names_the_dictionary(self):
        code, out, err = run_script(SCRIPT, str(self.before), str(self.after))
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"tokenizer: sudachi \(sudachidict_\w+\)")

    def test_json_reports_the_dictionary(self):
        code, out, _ = run_script(SCRIPT, "--json", str(self.before), str(self.after))
        self.assertEqual(code, 0)
        self.assertRegex(json.loads(out)["tokenizer"], r"^sudachi \(sudachidict_\w+\)$")

    def test_regex_can_still_be_forced_when_sudachi_is_installed(self):
        code, out, _ = run_script(SCRIPT, "--tokenizer", "regex", str(self.before), str(self.after))
        self.assertEqual(code, 0)
        self.assertIn("tokenizer: regex", out)


class BothPathsAgreeOnTheMeaningSignalsTest(unittest.TestCase):
    """数値・単位・URL・コード・否定の変化は、どちらの解析器でも挙がる。"""

    ANALYZERS = [("regex", compare.RegexAnalyzer())] + ([("sudachi", SUDACHI)] if SUDACHI else [])

    def result(self, analyzer):
        before = compare.parse_document(BEFORE, "before.md", True, analyzer)
        after = compare.parse_document(AFTER, "after.md", True, analyzer)
        return compare.compare_documents(before, after, analyzer.name)

    def test_a_changed_number_and_unit_are_reported(self):
        for name, analyzer in self.ANALYZERS:
            with self.subTest(tokenizer=name):
                numbers = self.result(analyzer)["numbers"]
                self.assertTrue(any(i.text.startswith("100") for i in numbers["missing"]), numbers)
                self.assertIn("10秒", [i.text for i in numbers["added"]])

    def test_a_changed_url_and_code_are_reported(self):
        for name, analyzer in self.ANALYZERS:
            with self.subTest(tokenizer=name):
                result = self.result(analyzer)
                self.assertIn("https://example.com/api/v1", [i.text for i in result["urls"]["missing"]])
                self.assertIn("https://example.com/api/v2", [i.text for i in result["urls"]["added"]])
                self.assertIn("--force", " ".join(i.text for i in result["code"]["missing"]))
                self.assertIn("--yes", " ".join(i.text for i in result["code"]["added"]))

    def test_a_dropped_double_negative_is_counted_as_two_negations_lost(self):
        for name, analyzer in self.ANALYZERS:
            with self.subTest(tokenizer=name):
                negation = self.result(analyzer)["markers"]["negation"]
                self.assertEqual((negation["before"], negation["after"]), (2, 0))

    def test_identical_text_reports_nothing_with_either_tokenizer(self):
        for name, analyzer in self.ANALYZERS:
            with self.subTest(tokenizer=name):
                before = compare.parse_document(BEFORE, "before.md", True, analyzer)
                same = compare.parse_document(BEFORE, "after.md", True, analyzer)
                result = compare.compare_documents(before, same, analyzer.name)
                for kind in ("numbers", "urls", "code"):
                    self.assertEqual(result[kind], {"missing": [], "added": []}, kind)
                self.assertEqual(result["unmatched"], {"after": [], "before": []})


if __name__ == "__main__":
    unittest.main()
