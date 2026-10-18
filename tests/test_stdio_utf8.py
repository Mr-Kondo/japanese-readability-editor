"""配布 CLI の標準出力が、cp932 の Windows のような環境でも UTF-8 になり、異常終了しないことを確かめる。

macOS や Linux で、`PYTHONUTF8=0` と `PYTHONIOENCODING=cp932` を渡して、Windows の日本語環境に近づけた再現である。
実機の Windows では確かめていない。
"""
import contextlib
import io
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import SCRIPTS_DIR, load_module, temporary_directory

CLIS = ("check_fiction", "check_kokugo", "compare_rewrite", "make_feedback", "measure", "validate_kokugo_rules",
        "verify_preservation")
CP932_ENV = {"PYTHONUTF8": "0", "PYTHONIOENCODING": "cp932", "PYTHONDONTWRITEBYTECODE": "1"}


def run_cp932(script: str, *args: str):
    """cp932 の標準出力を持つ環境で CLI を動かし、(終了コード, stdout の UTF-8 の復号, stderr の UTF-8 の復号) を返す。"""
    environment = {k: v for k, v in os.environ.items() if k not in ("PYTHONUTF8", "PYTHONIOENCODING")}
    environment.update(CP932_ENV)
    done = subprocess.run([sys.executable, str(SCRIPTS_DIR / f"{script}.py"), *args], capture_output=True, env=environment, timeout=60)
    return done.returncode, done.stdout.decode("utf-8"), done.stderr.decode("utf-8")


class Cp932OutputTest(unittest.TestCase):
    def setUp(self):
        self.folder = temporary_directory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)

    def write(self, name: str, text: str) -> str:
        path = self.root / name
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_compare_rewrite_quotes_sentences_with_emoji(self):
        before, after = self.write("a.md", "全く別の内容🙂です。\n"), self.write("b.md", "新しい情報🚀を追加しました。\n")
        code, out, _ = run_cp932("compare_rewrite", before, after, "--tokenizer", "regex")
        self.assertEqual(code, 0)
        self.assertIn("新しい情報🚀を追加しました。", out)

    def test_verify_preservation_reports_a_difference_that_contains_emoji(self):
        before, after = self.write("a.md", "全く別の内容🙂です。\n"), self.write("b.md", "新しい情報🚀を追加しました。\n")
        code, out, err = run_cp932("verify_preservation", before, after)
        self.assertEqual(code, 1)
        self.assertNotIn("Traceback", err)

    def test_check_fiction_prints_findings_with_japanese_brackets(self):
        code, out, err = run_cp932("check_fiction", self.write("n.md", "私は🙂ひとつ、ふたつの設定をして、その結果、3件の例外が出た。\n"))
        self.assertNotIn("Traceback", err)
        self.assertIn(code, (0, 1))

    def test_measure_prints_a_japanese_file_name(self):
        code, out, _ = run_cp932("measure", self.write("測定🙂.md", "短い文です。\n"))
        self.assertEqual(code, 0)
        self.assertIn("測定🙂.md", out)

    def test_check_kokugo_prints_japanese(self):
        code, out, _ = run_cp932("check_kokugo", self.write("国語.md", "データの更新は月末までに行う。\n"))
        self.assertEqual(code, 0)
        self.assertIn("国語.md", out)
        self.assertIn("形態素解析", out)

    def test_make_feedback_prints_json_with_emoji_and_a_japanese_notice(self):
        before, after = self.write("a.md", "全く別の内容🙂です。\n"), self.write("b.md", "新しい情報🚀を追加しました。\n")
        code, out, err = run_cp932("make_feedback", "--original", before, "--result", after, "--type", "other", "--quote", "🚀",
                                   "--consent-storage")
        self.assertEqual(code, 0, err)
        self.assertIn("🚀", out)
        self.assertIn("確認", err)

    def test_validate_kokugo_rules_runs(self):
        code, out, _ = run_cp932("validate_kokugo_rules")
        self.assertEqual(code, 0)
        self.assertIn("OK", out)


class Utf8OutputSetupTest(unittest.TestCase):
    """標準出力を切り替えられない環境(IDLE、閉じた標準出力、pythonw)で、何もせずに戻る。"""

    class Plain:  # reconfigure を持たない
        def write(self, text):
            return len(text)

    class Closed:
        def reconfigure(self, **kwargs):
            raise ValueError("I/O operation on closed file")

    class Broken:
        def reconfigure(self, **kwargs):
            raise OSError("broken")

    def test_every_cli_ignores_streams_it_cannot_reconfigure(self):
        for name in CLIS:
            module = load_module(f"stdio_{name}", SCRIPTS_DIR / f"{name}.py")
            for stream in (self.Plain(), self.Closed(), self.Broken(), None, io.StringIO()):
                with self.subTest(cli=name, stream=type(stream).__name__):
                    original = sys.stdout, sys.stderr
                    sys.stdout = sys.stderr = stream
                    try:
                        module.use_utf8_output()
                    finally:
                        sys.stdout, sys.stderr = original

    def test_a_text_stream_is_switched_to_utf8_and_never_raises_on_odd_characters(self):
        module = load_module("stdio_measure_utf8", SCRIPTS_DIR / "measure.py")
        raw = io.BytesIO()
        stream = io.TextIOWrapper(raw, encoding="cp932")
        original = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = stream
        try:
            module.use_utf8_output()
            print("日本語🙂\ud800", end="", file=stream)
            stream.flush()
        finally:
            sys.stdout, sys.stderr = original
        self.assertEqual(raw.getvalue().decode("utf-8"), "日本語🙂\\ud800")


if __name__ == "__main__":
    unittest.main()
