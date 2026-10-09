"""モード C(改行と空行の挿入のみ)とモード B(意味を保存した書き換え)で、国語の規則が誤修正を起こさないことのテスト。

モード C: 既存の verify_preservation.py は空白全般を無視するため、空白やタブの置換・削除を見逃す。
          --strict がそれを検出すること、国語の規則を理由に本文を変えないことを確かめる。
モード B: 数値、単位、条件、例外、否定、主体、断定の強さを変えた例を、既存の compare_rewrite.py の回帰ケースとして確かめる。
          用意したケースでの確認であり、すべての自然言語入力に対する保証ではない。
"""

import json
import unittest
from collections import Counter
from pathlib import Path

from helpers import FIXTURES, SCRIPTS_DIR, dedent, load_module, run_script, temporary_directory

engine = load_module("kokugo_engine", SCRIPTS_DIR / "kokugo_engine.py")
verify = load_module("verify_preservation", SCRIPTS_DIR / "verify_preservation.py")
compare = load_module("compare_rewrite", SCRIPTS_DIR / "compare_rewrite.py")
RULESET = engine.load_rules()
KOKUGO = FIXTURES / "kokugo"
VERIFY = SCRIPTS_DIR / "verify_preservation.py"
REGEX = compare.RegexAnalyzer()
GT, PE, OF = engine.PROFILES


def strict_ok(before, after):
    return verify.compare_strict(before, after)["only_newlines_inserted"]


def default_ok(before, after):
    return verify.compare(before, after)["identical"]


class StrictVerificationAcceptsOnlyInsertedLineBreaksTest(unittest.TestCase):
    """要件7: モード C の出力は、改行・空行の挿入以外が変わらない。"""

    ACCEPTED = {
        "blank lines between sentences": ("一つ目。二つ目。三つ目。\n", "一つ目。\n\n二つ目。\n\n三つ目。\n"),
        "a single line break": ("一つ目。二つ目。\n", "一つ目。\n二つ目。\n"),
        "a line break at the end": ("一つ目。", "一つ目。\n"),
        "a blank line at the start": ("一つ目。\n", "\n一つ目。\n"),
        "existing breaks and spaces kept": ("一つ目。 二つ目。\n三つ目。\n", "一つ目。 \n\n二つ目。\n三つ目。\n"),
        "tabs kept": ("見出し\n\t項目。二つ目。\n", "見出し\n\t項目。\n\n二つ目。\n"),
        "full-width space kept": ("　一つ目。二つ目。\n", "　一つ目。\n\n二つ目。\n"),
        "no-break space kept": ("一つ目。 二つ目。\n", "一つ目。 \n\n二つ目。\n"),
        "trailing spaces kept": ("一つ目。  \n二つ目。\n", "一つ目。  \n\n二つ目。\n"),
        "identical text": ("一つ目。\n", "一つ目。\n"),
        "CRLF breaks inserted into an LF text": ("一つ目。二つ目。\n", "一つ目。\r\n\r\n二つ目。\n"),
        "an LF text turned into CRLF": ("一つ目。\n二つ目。\n", "一つ目。\r\n\r\n二つ目。\r\n"),
    }

    REJECTED = {
        "the space between sentences was dropped": ("一つ目。 二つ目。\n", "一つ目。\n\n二つ目。\n"),
        "a tab became a space": ("見出し\n\t項目。\n", "見出し\n 項目。\n"),
        "a tab was removed": ("見出し\n\t項目。\n", "見出し\n項目。\n"),
        "a full-width space was removed": ("　一つ目。\n", "一つ目。\n"),
        "a full-width space became a half-width space": ("　一つ目。\n", " 一つ目。\n"),
        "trailing spaces were stripped": ("一つ目。  \n二つ目。\n", "一つ目。\n\n二つ目。\n"),
        "indentation changed": ("    一つ目。\n", "  一つ目。\n"),
        "a no-break space became a space": ("一つ目。 二つ目。\n", "一つ目。 二つ目。\n"),
        "lines were joined": ("一つ目。\n二つ目。\n", "一つ目。二つ目。\n"),
        "a blank line was removed": ("一つ目。\n\n二つ目。\n", "一つ目。\n二つ目。\n"),
        "the final line break was removed": ("一つ目。\n", "一つ目。"),
        "a character changed": ("原因は、Aである。\n", "原因は、Aだ。\n"),
        "punctuation changed": ("原因は、Aである。\n", "原因は，Aである。\n"),
        "a punctuation mark was dropped": ("ただし、費用が増える。\n", "ただし費用が増える。\n"),
        "text was deleted": ("一つ目。二つ目。\n", "一つ目。\n"),
        "text was added": ("一つ目。\n", "一つ目。二つ目。\n"),
        "text was reordered": ("あ。い。\n", "い。\n\nあ。\n"),
        "a conjunction was added": ("原因は A。対策は B。\n", "原因は A。\n\nそのため、対策は B。\n"),
        "a notation fix was applied (申し込み)": ("申し込みを受け付ける。サーバを再起動する。\n", "申込みを受け付ける。\n\nサーバを再起動する。\n"),
        "a notation fix was applied (サーバ)": ("サーバを再起動する。\n", "サーバーを再起動する。\n"),
        "a historical kana fix was applied (こんにちわ)": ("こんにちわ、田中です。\n", "こんにちは、田中です。\n"),
    }

    def test_accepted_transformations(self):
        for name, (before, after) in self.ACCEPTED.items():
            with self.subTest(name):
                self.assertTrue(strict_ok(before, after), name)

    def test_rejected_transformations(self):
        for name, (before, after) in self.REJECTED.items():
            with self.subTest(name):
                self.assertFalse(strict_ok(before, after), name)

    def test_the_default_check_alone_cannot_guarantee_line_breaks_only(self):
        """既存の検証は空白全般を無視するので、空白・タブの置換・削除と、改行の削除を合格にしてしまう。--strict が必要な理由。"""
        for name in ("the space between sentences was dropped", "a tab became a space", "a tab was removed", "a full-width space was removed",
                     "trailing spaces were stripped", "indentation changed", "a no-break space became a space", "lines were joined",
                     "a blank line was removed", "the final line break was removed"):
            before, after = self.REJECTED[name]
            with self.subTest(name):
                self.assertTrue(default_ok(before, after), "既存の検証は、これを見逃す(だから --strict を使う)")
                self.assertFalse(strict_ok(before, after))

    def test_the_default_check_still_catches_changed_characters(self):
        for name in ("a character changed", "punctuation changed", "text was deleted", "text was added", "text was reordered",
                     "a notation fix was applied (申し込み)", "a notation fix was applied (サーバ)"):
            before, after = self.REJECTED[name]
            with self.subTest(name):
                self.assertFalse(default_ok(before, after))

    def test_strict_implies_the_default_check(self):
        for name, (before, after) in self.ACCEPTED.items():
            with self.subTest(name):
                self.assertTrue(default_ok(before, after))

    def test_the_result_names_what_went_wrong(self):
        removed = verify.compare_strict("一つ目。\n二つ目。\n", "一つ目。二つ目。\n")
        self.assertTrue(removed["newlines_removed"])
        self.assertTrue(removed["non_newline_identical"])
        changed = verify.compare_strict("見出し\n\t項目。\n", "見出し\n 項目。\n")
        self.assertFalse(changed["non_newline_identical"])
        self.assertEqual(changed["first_difference"]["position"], 4)
        inserted = verify.compare_strict("一つ目。二つ目。\n", "一つ目。\n\n二つ目。\n")
        self.assertEqual(inserted["inserted_newlines"], 2)


class StrictVerificationCommandLineTest(unittest.TestCase):
    def run_verify(self, before, after, *extra):
        with temporary_directory() as tmp:
            a, b = Path(tmp) / "before.md", Path(tmp) / "after.md"
            a.write_bytes(before.encode("utf-8"))
            b.write_bytes(after.encode("utf-8"))
            return run_script(VERIFY, *extra, str(a), str(b))

    def test_exit_codes(self):
        code, out, _ = self.run_verify("一つ目。二つ目。\n", "一つ目。\n\n二つ目。\n", "--strict")
        self.assertEqual(code, 0)
        self.assertIn("OK (strict)", out)
        code, out, _ = self.run_verify("見出し\n\t項目。\n", "見出し\n 項目。\n", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("FAIL (strict)", out)
        code, out, _ = self.run_verify("一つ目。\n二つ目。\n", "一つ目。二つ目。\n", "--strict")
        self.assertEqual(code, 1)
        self.assertIn("line break was removed", out)

    def test_without_strict_the_behavior_is_unchanged(self):
        code, out, _ = self.run_verify("見出し\n\t項目。\n", "見出し\n 項目。\n")
        self.assertEqual(code, 0)
        self.assertIn("OK: non-whitespace characters are identical", out)
        code, out, _ = self.run_verify("見出し\n\t項目。\n", "見出し\n 項目。\n", "--json")
        self.assertNotIn("strict", json.loads(out))

    def test_json_includes_the_strict_result(self):
        code, out, _ = self.run_verify("一つ目。二つ目。\n", "一つ目。\n\n二つ目。\n", "--strict", "--json")
        self.assertEqual(code, 0)
        self.assertTrue(json.loads(out)["strict"]["only_newlines_inserted"])

    def test_quiet_with_strict(self):
        code, out, _ = self.run_verify("見出し\n\t項目。\n", "見出し\n 項目。\n", "--strict", "-q")
        self.assertEqual((code, out), (1, ""))

class ModeCDoesNotChangeTheTextForNotationReasonsTest(unittest.TestCase):
    def setUp(self):
        self.before = (KOKUGO / "mode_c_before.md").read_text(encoding="utf-8")
        self.after = (KOKUGO / "mode_c_after.md").read_text(encoding="utf-8")

    def test_the_fixture_inserts_only_line_breaks(self):
        self.assertTrue(strict_ok(self.before, self.after))
        self.assertIn("\t", self.after)
        self.assertIn("。 処理", self.after)  # 空白もタブも残っている

    def test_notation_problems_are_still_reported_after_the_split_and_left_unfixed(self):
        """表記上の問題を見つけても、本文は変えない。報告するだけ。"""
        for profile in engine.PROFILES:
            summary = lambda text: Counter((f["rule_id"], f["text"], f["category"]) for f in engine.check_text(text, profile, RULESET))
            self.assertEqual(summary(self.before), summary(self.after), profile)
        found = engine.check_text(self.after, OF, RULESET)
        self.assertTrue([f for f in found if f["category"] == "error"], "こんにちわ は、報告するが直さない")

    def test_applying_the_reported_fixes_would_break_the_mode_c_check(self):
        """検査の候補を本文へ適用すると、モード C の検証が失敗する(だからモード C では適用しない)。"""
        fixed = apply_candidates(self.after, engine.check_text(self.after, OF, RULESET))
        self.assertNotEqual(fixed, self.after)
        self.assertFalse(strict_ok(self.before, fixed))
        self.assertFalse(default_ok(self.before, fixed))

    def test_mode_c_text_passes_the_strict_check_from_the_command_line(self):
        code, out, _ = run_script(VERIFY, "--strict", str(KOKUGO / "mode_c_before.md"), str(KOKUGO / "mode_c_after.md"))
        self.assertEqual(code, 0, out)


def apply_candidates(text, findings):
    """確定した指摘(error / recommendation)のうち、候補が1つのものを、後ろから本文へ適用する(モード B の修正の模擬)。"""
    text = engine.normalize_newlines(text)
    for finding in sorted(findings, key=lambda f: f["offset"], reverse=True):
        if finding["category"] in ("error", "recommendation") and len(finding["candidates"]) == 1:
            text = text[: finding["offset"]] + finding["candidates"][0] + text[finding["offset"] + finding["length"]:]
    return text


def run_compare(before, after, analyzer=REGEX):
    return compare.compare_documents(compare.parse_document(dedent(before), "before.md", True, analyzer),
                                     compare.parse_document(dedent(after), "after.md", True, analyzer), analyzer.name)


def pointers(result):
    found = []
    for kind in compare.ITEM_KINDS:
        if result[kind]["missing"] or result[kind]["added"]:
            found.append(kind)
    if result["unmatched"]["after"] or result["unmatched"]["before"]:
        found.append("unmatched")
    found += [f"markers:{kind}" for kind, data in result["markers"].items() if data["removed"] or data["added"] or data["before"] != data["after"]]
    if result["style"]["changed"]:
        found.append("style")
    return found


class MeaningChangesAreStillFlaggedByTheExistingComparisonTest(unittest.TestCase):
    """要件8: 数値、単位、条件、例外、否定、主体、断定の強さを変えた例を、既存照合の回帰ケースとして確かめる。

    期待値は SKILL.md の『書き換えた後の照合』の観点から決めた。compare_rewrite.py は候補を挙げる補助であり、判定ではない。
    """

    def assert_flagged(self, before, after, expected):
        result = run_compare(before, after)
        self.assertIn(expected, pointers(result), (before, after, pointers(result)))
        return result

    def test_a_changed_number(self):
        self.assert_flagged("タイムアウトは30秒である。\n", "タイムアウトは3秒である。\n", "numbers")

    def test_a_changed_unit(self):
        result = self.assert_flagged("タイムアウトは30秒である。\n", "タイムアウトは30分である。\n", "numbers")
        self.assertEqual([i.text for i in result["numbers"]["missing"]], ["30秒"])
        self.assertEqual([i.text for i in result["numbers"]["added"]], ["30分"])

    def test_a_narrowed_or_widened_condition(self):
        result = self.assert_flagged("管理者の場合に限り、実行できる。\n", "管理者の場合に、実行できる。\n", "markers:limit")
        self.assertEqual((result["markers"]["limit"]["before"], result["markers"]["limit"]["after"]), (1, 0))

    def test_a_residual_condition_rewritten(self):
        result = self.assert_flagged("上記以外の場合は、実行を拒否する。\n", "場合は、実行を拒否する。\n", "markers:residual")
        self.assertEqual((result["markers"]["residual"]["before"], result["markers"]["residual"]["after"]), (1, 0))

    def test_a_dropped_exception(self):
        result = self.assert_flagged("すべての利用者が実行できる。ただし、停止中の利用者は除く。\n", "すべての利用者が実行できる。\n", "unmatched")
        self.assertEqual([i.text for i in result["unmatched"]["before"]], ["ただし、停止中の利用者は除く。"])

    def test_a_negation_removed_or_added(self):
        result = self.assert_flagged("この設定を変更しない。\n", "この設定を変更する。\n", "markers:negation")
        self.assertEqual((result["markers"]["negation"]["before"], result["markers"]["negation"]["after"]), (1, 0))
        self.assert_flagged("この設定を変更する。\n", "この設定を変更しない。\n", "markers:negation")

    def test_a_weakened_or_strengthened_assertion(self):
        self.assert_flagged("失敗する可能性がある。\n", "失敗する。\n", "markers:conjecture")
        self.assert_flagged("遅くなるかもしれない。\n", "遅くなる。\n", "markers:conjecture")
        self.assert_flagged("遅くなる。\n", "遅くなるかもしれない。\n", "markers:conjecture")

    def test_a_changed_subject_that_involves_a_term(self):
        result = self.assert_flagged("ユーザーが申請を承認する。\n", "システムが申請を承認する。\n", "terms")
        self.assertEqual([i.text for i in result["terms"]["missing"]], ["ユーザー"])
        self.assertEqual([i.text for i in result["terms"]["added"]], ["システム"])

    def test_known_limit_a_subject_swap_between_plain_kanji_nouns_is_not_flagged(self):
        """既知の限界: 漢字の名詞だけの主体の入れ替え(利用者→管理者)は、現在の照合では挙がらない。

        SKILL.md の『主体が同じか』は、人が元の文と見比べて確かめる。このテストは、機械が補助できない範囲を明示するためにある。
        機械が拾えるように改良したときは、このテストを意図して更新する。
        """
        self.assertEqual(pointers(run_compare("利用者が申請を承認する。\n", "管理者が申請を承認する。\n")), [])

    def test_known_limit_a_causal_reversal_is_not_flagged(self):
        """既知の限界: 因果関係の入れ替えは、現在の照合では挙がらない。人が確かめる。"""
        self.assertEqual(pointers(run_compare("負荷が高いため、応答が遅れた。\n", "応答が遅れたため、負荷が高くなった。\n")), [])

    def test_a_changed_style_is_flagged(self):
        self.assert_flagged("設定を変更する。値を確認する。\n", "設定を変更します。値を確認します。\n", "style")


class NotationOnlyRewritesDoNotLookLikeMeaningChangesTest(unittest.TestCase):
    """国語の規則による表記の修正(意味を保つ書き換え)は、意味の変化候補を出さない。変更してはいけない反例ではなく、保存の確認。"""

    def test_okurigana_and_permitted_form_fixes_leave_no_pointer(self):
        before = "申し込みを受け付ける。処理を行なう。結果を表わす。\n"
        after = "申込みを受け付ける。処理を行う。結果を表す。\n"
        self.assertEqual(pointers(run_compare(before, after)), [])

    def test_a_long_vowel_fix_may_show_a_term_pointer_only(self):
        """正規表現の解析器は『サーバ』と『サーバー』を別の語と数える。ポインタ(判定ではない)として terms だけが挙がる。"""
        self.assertEqual(pointers(run_compare("サーバを再起動する。\n", "サーバーを再起動する。\n")), ["terms"])

    def test_fixing_the_notation_keeps_numbers_conditions_negation_and_style(self):
        before = ("申し込みの受付は3か所に限る。処理を行なう。結果を表わす。\n"
                  "ただし、上記以外の場合は拒否する。すべての設定を確認する。この設定は変更しない。\n")
        findings = engine.check_text(before, OF, RULESET)
        after = apply_candidates(before, findings)
        self.assertNotEqual(after, before)
        self.assertEqual(after, "申込みの受付は3か所に限る。処理を行う。結果を表す。\nただし、上記以外の場合は拒否する。全ての設定を確認する。この設定は変更しない。\n")
        self.assertEqual(pointers(run_compare(before, after)), [])
        # 修正後に再検査すると、確認対象が残っていない
        self.assertEqual([f for f in engine.check_text(after, OF, RULESET) if f["category"] in engine.FLAG_CATEGORIES], [])

    def test_a_wrongly_applied_fix_that_changes_meaning_is_caught(self):
        """表記の修正に見えて、数値・条件・否定を変えた書き換えは、照合が挙げる。"""
        before = "申し込みは3か所に限る。ただし、例外は認めない。\n"
        wrong = "申込みは3か所に限らない。ただし、例外を認める。\n"
        result = run_compare(before, wrong)
        self.assertEqual([i.text for i in result["markers"]["negation"]["added"]], ["申込みは3か所に限らない。"])
        # 近接する2文を1つの対応先とみなすため、『認めない→認める』の否定の消失は、全体の否定数が同じだと相殺されて挙がらない。
        # 照合は候補を挙げる補助であり、残りは SKILL.md の『書き換えた後の照合』で人が元の文と見比べる。
        self.assertEqual(result["markers"]["negation"]["removed"], [])
        wrong_number = "申込みは5か所に限る。ただし、例外は認めない。\n"
        self.assertIn("numbers", pointers(run_compare(before, wrong_number)))


class ProtectedTextIsNotRewrittenByTheFixSimulationTest(unittest.TestCase):
    def test_applying_candidates_never_touches_protected_text(self):
        text = ("---\ntitle: 申し込みとサーバ\n---\n\n"
                "申し込みを受け付ける。\n\n"
                "> 引用の申し込みを。\n\n"
                "`申し込みを` と https://example.com/申し込みを\n\n"
                "```text\n申し込みを\n```\n")
        fixed = apply_candidates(text, engine.check_text(text, OF, RULESET))
        self.assertEqual(fixed, text.replace("\n申し込みを受け付ける。\n", "\n申込みを受け付ける。\n", 1))  # 直るのは本文の1か所だけ
        for protected in ("title: 申し込みとサーバ", "> 引用の申し込みを。", "`申し込みを`", "https://example.com/申し込みを", "```text\n申し込みを\n```"):
            self.assertIn(protected, fixed)


if __name__ == "__main__":
    unittest.main()
