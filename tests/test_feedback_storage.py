"""自動保存の保存先、追記、失敗時の CLI 契約。人工例だけを一時領域へ保存する。"""
import contextlib
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from helpers import SCRIPTS_DIR, load_module, run_script, temporary_directory

storage = load_module("feedback_storage", SCRIPTS_DIR / "feedback_storage.py")


class FeedbackStorageTest(unittest.TestCase):
    def setUp(self):
        self.folder = temporary_directory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.original = self.root / "before.md"
        self.result = self.root / "after.md"
        self.original.write_text("実行できます。", encoding="utf-8")
        self.result.write_text("必ず実行されます。", encoding="utf-8")

    def run_report(self, script, folder):
        options = ("--type", "strength_changed", "--quote", "必ず", "--consent-storage") if script == "make_feedback" else ()
        return run_script(SCRIPTS_DIR / f"{script}.py", "--original", str(self.original),
                          "--result", str(self.result), "--out-dir", str(folder), *options)

    def test_default_location_is_under_home_and_file_is_private_on_posix(self):
        with patch.object(storage.Path, "home", return_value=self.root):
            saved = storage.save_report({"kind": "jre-feedback", "case": "日本語🙂"})
        self.assertEqual(saved.parent, self.root.resolve() / ".agents" / "feedback" / "japanese-readability-editor")
        self.assertEqual(json.loads(saved.read_text(encoding="utf-8"))["case"], "日本語🙂")
        if os.name == "posix":
            self.assertEqual(saved.stat().st_mode & 0o777, 0o600)

    def test_both_clis_save_identical_json_and_preserve_previous_records(self):
        for script, kind in (("make_feedback", "jre-feedback"), ("make_change_report", "jre-change-report")):
            with self.subTest(script=script):
                folder = self.root / script / "記録🙂"
                previous = None
                for _ in range(2):
                    code, stdout, stderr = self.run_report(script, folder)
                    self.assertEqual(code, 0, stderr)
                    saved = Path(next(line.removeprefix("saved_to: ") for line in stderr.splitlines()
                                      if line.startswith("saved_to: ")))
                    self.assertEqual(saved.read_text(encoding="utf-8"), stdout)
                    self.assertEqual(json.loads(stdout)["kind"], kind)
                    self.assertTrue(saved.name.startswith(kind + "-"))
                    if previous:
                        self.assertEqual(previous.read_bytes(), contents)
                    previous, contents = saved, saved.read_bytes()
                self.assertEqual(len(list(folder.glob("*.json"))), 2)

    def test_save_failure_returns_two_without_json_or_input_changes(self):
        blocker = self.root / "not-a-directory"
        blocker.write_text("keep", encoding="utf-8")
        for script in ("make_feedback", "make_change_report"):
            with self.subTest(script=script):
                code, stdout, stderr = self.run_report(script, blocker / "reports")
                self.assertEqual((code, stdout), (2, ""))
                self.assertIn("failed", stderr)
                self.assertNotIn("saved_to:", stderr)
        self.assertEqual(blocker.read_text(encoding="utf-8"), "keep")
        self.assertEqual(self.original.read_text(encoding="utf-8"), "実行できます。")
        self.assertEqual(self.result.read_text(encoding="utf-8"), "必ず実行されます。")

    def test_partial_record_is_removed_when_writing_fails(self):
        fdopen = os.fdopen

        @contextlib.contextmanager
        def failing_stream(*args, **kwargs):
            with fdopen(*args, **kwargs) as stream:
                yield stream
                raise OSError("simulated flush failure")

        folder = self.root / "reports"
        with patch.object(storage.os, "fdopen", side_effect=failing_stream):
            with self.assertRaises(OSError):
                storage.save_report({"kind": "jre-feedback"}, folder)
        self.assertEqual(list(folder.iterdir()), [])
