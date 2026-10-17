"""フィードバック票を出す配布スクリプト。入力はテスト内で組み立てる人工の文章。"""
import json
import tempfile
import unittest
from pathlib import Path

from helpers import SCRIPTS_DIR, run_script

SCRIPT = SCRIPTS_DIR / "make_feedback.py"
ORIGINAL = "管理者の承認後、30分以内に実行できます。"
RESULT = "管理者が承認すれば、必ず30分以内に実行されます。"


class MakeFeedbackTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.original = Path(self.folder.name, "before.md")
        self.result = Path(self.folder.name, "after.md")
        self.original.write_text(ORIGINAL, encoding="utf-8")
        self.result.write_text(RESULT, encoding="utf-8")

    def run_form(self, *extra, quote="必ず"):
        return run_script(SCRIPT, "--original", str(self.original), "--result", str(self.result),
                          "--type", "strength_changed", "--quote", quote, *extra)

    def test_outputs_a_ticket_with_consent_and_quote_location(self):
        code, out, _ = self.run_form("--consent-storage", "--mode", "B")
        self.assertEqual(code, 0)
        ticket = json.loads(out)
        self.assertEqual(ticket["kind"], "jre-feedback")
        self.assertEqual(ticket["consent"], {"version": 1, "storage": True, "ai_processing": False, "publish": False})
        self.assertEqual(ticket["case"]["quote_in"], "result")
        self.assertEqual(ticket["case"]["original"], ORIGINAL)

    def test_a_lost_item_is_quoted_from_the_original(self):
        code, out, _ = self.run_form("--consent-storage", quote="30分以内")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["case"]["quote_in"], "result")
        code, out, _ = run_script(SCRIPT, "--original", str(self.original), "--result", str(self.result),
                                  "--type", "meaning_lost", "--quote", "承認後", "--consent-storage")
        self.assertEqual(json.loads(out)["case"]["quote_in"], "original")

    def test_without_storage_consent_nothing_is_output(self):
        code, out, err = self.run_form()
        self.assertEqual((code, out), (2, ""))
        self.assertIn("--consent-storage", err)

    def test_a_quote_that_is_in_neither_text_is_refused(self):
        code, out, err = self.run_form("--consent-storage", quote="どこにもない文")
        self.assertEqual((code, out), (2, ""))
        self.assertIn("--quote", err)

    def test_an_unknown_problem_type_is_refused(self):
        code, _, _ = run_script(SCRIPT, "--original", str(self.original), "--result", str(self.result),
                                "--type", "made_up", "--quote", "必ず", "--consent-storage")
        self.assertEqual(code, 2)

    def test_email_url_and_phone_like_strings_are_warned_but_not_blocked(self):
        self.result.write_text(RESULT + "連絡は taro@example.com か https://example.com/x、03-1234-5678 へ。", encoding="utf-8")
        code, out, err = self.run_form("--consent-storage")
        self.assertEqual(code, 0)
        for name in ("メールアドレス", "URL", "電話番号"):
            self.assertIn(name, err)
        self.assertEqual(json.loads(out)["kind"], "jre-feedback")

    def test_missing_or_empty_input_exits_two(self):
        self.result.write_text("  \n", encoding="utf-8")
        code, _, err = self.run_form("--consent-storage")
        self.assertEqual(code, 2)
        self.assertIn("結果", err)


if __name__ == "__main__":
    unittest.main()
