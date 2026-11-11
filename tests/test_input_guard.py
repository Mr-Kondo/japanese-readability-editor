"""scripts/input_guard.py と、入力を読む各スクリプトの読み先の制限のテスト。"""

import os
import unittest
from pathlib import Path

from helpers import SCRIPTS_DIR, load_module, run_script, symlinks_supported, temporary_directory

guard = load_module("input_guard", SCRIPTS_DIR / "input_guard.py")

SECRET = "sk-secret-1234567890"


def blocked(path) -> bool:
    try:
        guard.check_readable(str(path))
    except PermissionError:
        return True
    return False


class CheckReadableTest(unittest.TestCase):
    def setUp(self):
        self.tmp = temporary_directory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.cwd = Path.cwd()
        self.addCleanup(os.chdir, self.cwd)
        self.work = self.root / "work"
        self.work.mkdir()
        os.chdir(self.work)

    @unittest.skipUnless(symlinks_supported(), "symlink を作れない環境")
    def test_a_file_named_hyphen_is_checked_like_any_other(self):
        # 標準入力の「-」は呼び出し側が先に分ける。ここへ来た「-」は、ファイル名として検査する
        os.symlink(Path.home() / "Documents" / "secret.txt", self.work / "-")
        self.assertTrue(blocked("-"))

    def test_working_folder_alone_is_enough_when_it_is_not_under_the_temporary_folder(self):
        os.chdir(Path(__file__).resolve().parent.parent)  # リポジトリ。一時フォルダの外
        self.assertFalse(blocked("README.md"))
        self.assertTrue(blocked(Path.home() / "Documents" / "a.md"))

    def test_file_in_working_folder_is_allowed(self):
        (self.work / "a.md").write_text("本文", encoding="utf-8")
        self.assertFalse(blocked("a.md"))
        self.assertFalse(blocked(self.work / "sub" / "b.md"))

    def test_temporary_folder_is_allowed_for_the_saved_original(self):
        # scripts.md の手順: 書き換え前の文章は、対象と別の一時フォルダへ保存する
        other = self.root / "elsewhere"
        other.mkdir()
        os.chdir(other)
        self.assertFalse(blocked(self.work / "a.md"))  # 一時フォルダ(self.root)の下

    def test_outside_working_and_temporary_folders_is_blocked(self):
        home_like = Path.home() / "Documents" / "a.md"
        self.assertTrue(blocked(home_like))
        self.assertTrue(blocked("/etc/hosts"))
        self.assertTrue(blocked("../" * 12 + "etc/hosts"))  # 根まで上がる

    def test_dot_prefixed_part_is_blocked(self):
        for name in (".env", ".git/config", ".ssh/id_rsa", "sub/.aws/credentials", ".hidden.md"):
            self.assertTrue(blocked(self.work / name), name)
            self.assertTrue(blocked(name), name)

    def test_dot_in_the_middle_of_a_name_is_allowed(self):
        self.assertFalse(blocked("a.b.md"))
        self.assertFalse(blocked("dir.d/file.md"))

    def test_working_folder_itself_under_a_dot_folder_is_allowed(self):
        hidden = self.root / ".claude" / "project"
        hidden.mkdir(parents=True)
        os.chdir(hidden)
        self.assertFalse(blocked("a.md"))
        self.assertTrue(blocked(".env"))

    @unittest.skipUnless(symlinks_supported(), "symlink を作れない環境")
    def test_symlink_to_outside_is_blocked_by_its_target(self):
        target = Path.home() / "Documents" / "secret.txt"
        link = self.work / "innocent.md"
        os.symlink(target, link)
        self.assertTrue(blocked("innocent.md"))

    @unittest.skipUnless(symlinks_supported(), "symlink を作れない環境")
    def test_symlink_to_dot_file_is_blocked(self):
        (self.work / ".env").write_text(SECRET, encoding="utf-8")
        os.symlink(self.work / ".env", self.work / "innocent.md")
        self.assertTrue(blocked("innocent.md"))

    def test_message_tells_how_to_proceed(self):
        with self.assertRaises(PermissionError) as raised:
            guard.check_readable(".env")
        self.assertIn("標準入力", str(raised.exception))


class CliTest(unittest.TestCase):
    """入力を読む各スクリプトが、止めて終了コード 2 を返し、中身を出さない。"""

    def setUp(self):
        self.tmp = temporary_directory()
        self.addCleanup(self.tmp.cleanup)
        self.work = Path(self.tmp.name) / "work"
        self.work.mkdir()
        (self.work / ".env").write_text(f"API_KEY={SECRET}\n", encoding="utf-8")
        (self.work / "ok.md").write_text("これは本文である。\n", encoding="utf-8")
        (self.work / "settings.json").write_text('{"forbidden": []}', encoding="utf-8")
        (self.work / ".settings.json").write_text('{"forbidden": []}', encoding="utf-8")
        (self.work / "terms.txt").write_text("protect: 本文\n", encoding="utf-8")
        (self.work / ".terms.txt").write_text(f"protect: {SECRET}\n", encoding="utf-8")

    def run_cli(self, script, *args):
        return run_script(SCRIPTS_DIR / script, *args, cwd=self.work)

    def assert_stopped(self, script, *args):
        code, out, err = self.run_cli(script, *args)
        self.assertEqual(code, 2, (script, out, err))
        self.assertIn("読まない", out + err, script)  # 別の理由(引数の誤り)で止まったのではない
        self.assertNotIn(SECRET, out + err, script)

    def test_each_reader_stops_on_a_dot_file(self):
        self.assert_stopped("measure.py", ".env")
        self.assert_stopped("check_kokugo.py", ".env")
        self.assert_stopped("check_kokugo.py", "ok.md", "--glossary", ".terms.txt")
        self.assert_stopped("check_fiction.py", ".env")
        self.assert_stopped("check_fiction.py", "ok.md", "--settings", ".settings.json")
        self.assert_stopped("verify_preservation.py", ".env", "ok.md")
        self.assert_stopped("verify_preservation.py", "ok.md", ".env")
        self.assert_stopped("compare_rewrite.py", ".env", "ok.md")
        self.assert_stopped("compare_rewrite.py", "ok.md", ".env")

    def test_each_reader_stops_outside_the_allowed_folders(self):
        outside = str(Path(__file__).resolve())  # 実在する、作業フォルダと一時フォルダの外のファイル
        self.assert_stopped("measure.py", outside)
        self.assert_stopped("check_kokugo.py", outside)
        self.assert_stopped("check_fiction.py", outside)
        self.assert_stopped("verify_preservation.py", outside, "ok.md")
        self.assert_stopped("compare_rewrite.py", "ok.md", outside)

    def test_make_feedback_and_change_report_stop(self):
        self.assert_stopped("make_feedback.py", "--original", ".env", "--result", "ok.md",
                            "--quote", "x", "--consent-storage", "--type", "other")
        self.assert_stopped("make_change_report.py", "--original", ".env", "--result", "ok.md")

    def test_stdin_and_normal_files_still_work(self):
        self.assertEqual(self.run_cli("measure.py", "ok.md")[0], 0)
        code, _, _ = run_script(SCRIPTS_DIR / "measure.py", "-", stdin="これは本文である。\n", cwd=self.work)
        self.assertEqual(code, 0)
        self.assertEqual(self.run_cli("verify_preservation.py", "ok.md", "ok.md")[0], 0)
        self.assertEqual(self.run_cli("check_fiction.py", "ok.md", "--settings", "settings.json")[0], 0)
        self.assertEqual(self.run_cli("check_kokugo.py", "ok.md", "--glossary", "terms.txt")[0], 0)

    def test_a_directory_argument_outside_is_stopped_before_walking(self):
        outside = str(Path(__file__).resolve().parent)  # 実在するフォルダ(tests/)。.md を含む
        code, out, err = self.run_cli("measure.py", outside)
        self.assertEqual(code, 2, (out, err))
        self.assertIn("読まない", err)
        self.assertNotIn("test_", out + err)  # 中のファイル名を出さない
        self.assertEqual(self.run_cli("measure.py", ".hidden_missing")[0], 2)

    def test_directory_walk_skips_dot_entries_silently(self):
        (self.work / ".hidden").mkdir()
        (self.work / ".hidden" / "x.md").write_text(f"{SECRET}\n", encoding="utf-8")
        (self.work / ".note.md").write_text(f"{SECRET}\n", encoding="utf-8")
        code, out, err = self.run_cli("measure.py", ".")
        self.assertEqual(code, 0, err)
        self.assertNotIn(SECRET, out + err)
        self.assertNotIn(".hidden", out + err)
        self.assertIn("ok.md", out)


if __name__ == "__main__":
    unittest.main()
