"""assets/kokugo-cases.md の例が、実際の検査結果と一致していることのテスト。

文書の『前』『後』『直さない』の文字列が、文書に載っていること、そして設定ごとに期待どおりの区分になることを確かめる。
"""

import unittest

from helpers import SCRIPTS_DIR, SKILL_DIR, load_module

engine = load_module("kokugo_engine", SCRIPTS_DIR / "kokugo_engine.py")
RULESET = engine.load_rules()
DOC = (SKILL_DIR / "assets" / "kokugo-cases.md").read_text(encoding="utf-8")
GT, PE, OF = engine.PROFILES
FLAG = engine.FLAG_CATEGORIES


def check(text, profile=OF, **kwargs):
    return engine.check_text(text, profile, RULESET, **kwargs)


def flagged(text, profile=OF, rule_id=None):
    return [f for f in check(text, profile) if f["category"] in FLAG and (rule_id is None or f["rule_id"] == rule_id)]


def cats(text, rule_id, profile):
    return [f["category"] for f in check(text, profile) if f["rule_id"] == rule_id]


class CasesDocumentTest(unittest.TestCase):
    def assertInDoc(self, *texts):
        for text in texts:
            self.assertIn(text, DOC, text)

    def test_case_1_okurigana_of_the_directive(self):
        before, after = "申し込みを受け付ける。取り扱いの方法を示す。", "申込みを受け付ける。取扱いの方法を示す。"
        self.assertInDoc(before, after)
        self.assertEqual(cats(before, "KOKUGO-OKURI-003", OF), ["error", "error"])
        self.assertEqual(flagged(after), [])
        for profile in (GT, PE):
            self.assertEqual(flagged(before, profile), [])
        self.assertEqual(flagged("入り口で申し込む。"), [])
        self.assertEqual(cats("先に申し込み、支払う。", "KOKUGO-OKURI-003", OF), ["needs_context"])

    def test_case_2_permitted_forms(self):
        self.assertInDoc("処理を行なう。結果を表わす。処理が終る。いなづまが光る。", "処理を行う。結果を表す。")
        self.assertEqual(flagged("処理を行なう。結果を表わす。処理が終る。いなづまが光る。", GT), [])
        self.assertEqual(cats("処理を行なう。結果を表わす。", "KOKUGO-OKURI-001", OF), ["recommendation", "recommendation"])
        self.assertEqual(flagged("処理を行う。結果を表す。"), [])

    def test_case_3_long_vowel_mark(self):
        self.assertInDoc("サーバを再起動する。", "`use: サーバ`")
        self.assertEqual([cats("サーバを再起動する。", "KOKUGO-GAIRAI-001", p)[0] for p in (GT, PE, OF)],
                         ["accepted_variant", "recommendation", "recommendation"])
        conflict = engine.check_text("サーバを再起動する。", OF, RULESET, glossary=engine.parse_glossary("use: サーバ\n"))
        self.assertEqual([f["category"] for f in conflict if f["rule_id"] == "KOKUGO-GAIRAI-001"], ["needs_context"])

    def test_case_4_adverbs_and_conjunctions(self):
        before = "すべての設定とログを確認し、AおよびBを記録する。且つ、安定させる。"
        after = "全ての設定とログを確認し、A及びBを記録する。かつ、安定させる。"
        self.assertInDoc(before, after)
        self.assertEqual(len(flagged(before)), 3)
        self.assertEqual(flagged(after), [])
        self.assertEqual(flagged(before, PE, "KOKUGO-KANJI-005") + flagged(before, PE, "KOKUGO-KANJI-004"), [])
        self.assertInDoc("『かなり』『ふと』『やはり』『よほど』")  # 仮名で書く語。直さない
        self.assertEqual(flagged("かなり重要な点を述べる。"), [])
        for ambiguous in ("きわめて重要な点を述べる。", "はじめて実行する。", "さらに確認する。", "もっとも重要である。"):
            self.assertEqual({f["category"] for f in check(ambiguous) if f["rule_id"] == "KOKUGO-KANJI-005"}, {"needs_context"}, ambiguous)

    def test_case_5_historical_kana_errors(self):
        before, after = "こんにちわ、田中です。そうゆう場合は再実行する。", "こんにちは、田中です。そういう場合は再実行する。"
        self.assertInDoc(before, after)
        for profile in engine.PROFILES:
            self.assertEqual([f["category"] for f in check(before, profile) if f["category"] != "excluded"], ["error", "error"])
        self.assertEqual(flagged(after), [])
        self.assertEqual(flagged("> こんにちわ、と書いてあった。"), [])
        self.assertEqual(flagged("```\nそうゆう\n```\n"), [])

    def test_case_6_du(self):
        self.assertInDoc("少しづつ進める。")
        self.assertEqual(cats("少しづつ進める。", "KOKUGO-KANA-005", OF), ["needs_context"])
        self.assertEqual(cats("ひとりづつ並ぶ。", "KOKUGO-KANA-004", OF), ["accepted_variant"])
        self.assertEqual(flagged("ひとりづつ並ぶ。"), [])

    def test_case_7_outside_kanji(self):
        before, after = "地域の絆を深める。", "地域のきずなを深める。"
        self.assertInDoc(before, after, "髙橋")
        for profile in (PE, OF):
            self.assertEqual(cats(before, "KOKUGO-KANJI-001", profile), ["needs_context"])
        self.assertEqual(flagged(before, GT), [])
        self.assertEqual(flagged(after), [])
        protected = check("髙橋さんが担当する。", OF, glossary=engine.parse_glossary("protect: 髙橋\n"))
        self.assertEqual([f["category"] for f in protected if f["rule_id"] == "KOKUGO-KANJI-001"], ["excluded"])

    def test_case_8_ijidokun(self):
        self.assertInDoc("時間を計る。")
        for profile in (PE, OF):
            found = [f for f in check("時間を計る。", profile) if f["rule_id"] == "KOKUGO-IJIDOKUN-001"]
            self.assertEqual([(f["category"], f["candidates"]) for f in found], [("needs_context", [])])

    def test_case_9_redundant_expressions(self):
        before, after = "約20名くらいが参加した。", "約20名が参加した。"
        self.assertInDoc(before, after)
        self.assertEqual(len(flagged(before, PE, "KOKUGO-EXPR-002")), 1)
        self.assertEqual(flagged(after), [])
        for kept in ("まず最初に", "従来から", "返事を返す", "排気ガス", "被害を被る"):
            self.assertInDoc(kept)
            self.assertEqual(flagged(f"{kept}の方法を確認する。", OF, "KOKUGO-EXPR-002"), [], kept)

    def test_case_10_kasho(self):
        before, after = "3ヶ所を直す。7カ月かかる。", "3か所を直す。7か月かかる。"
        self.assertInDoc(before, after)
        for profile in (PE, OF):
            self.assertEqual(len(flagged(before, profile, "KOKUGO-NUM-001")), 2)
        self.assertEqual(flagged(before, GT), [])
        self.assertEqual(flagged(after), [])
        self.assertInDoc("『数箇所』『何箇月』")
        self.assertEqual(flagged("数箇所を直す。何箇月かかる。"), [])

    def test_case_11_protected_text(self):
        text = ("---\ntitle: 申し込み\n---\n\n`申し込みを`\n\nhttps://example.com/申し込みを\n\n> 申し込みを\n\n```\n申し込みを\n```\n\n"
                "<!-- kokugo-ignore-start -->\n申し込みを\n<!-- kokugo-ignore-end -->\n")
        self.assertEqual(flagged(text), [])
        self.assertEqual({f["reason_code"] for f in check(text) if f["category"] == "excluded"},
                         {"protected:frontmatter", "protected:inline_code", "protected:url", "protected:quote", "protected:fenced_code",
                          "protected:ignore_region"} | {f["reason_code"] for f in check(text) if f["reason_code"] == "protected:html_comment"})

    def test_case_12_meaning_preservation(self):
        compare = load_module("compare_rewrite", SCRIPTS_DIR / "compare_rewrite.py")
        original = "申し込みは3か所に限る。ただし、例外は認めない。\n"
        correct = "申込みは3か所に限る。ただし、例外は認めない。\n"
        wrong = "申込みは3か所に限らない。ただし、例外を認める。\n"
        self.assertInDoc("申し込みは3か所に限る。ただし、例外は認めない。", "申込みは3か所に限る。ただし、例外は認めない。", "申込みは3か所に限らない。ただし、例外を認める。")
        analyzer = compare.RegexAnalyzer()

        def run(before, after):
            return compare.compare_documents(compare.parse_document(before, "b.md", True, analyzer), compare.parse_document(after, "a.md", True, analyzer), "regex")

        good = run(original, correct)
        self.assertEqual((good["numbers"], good["unmatched"]), ({"missing": [], "added": []}, {"after": [], "before": []}))
        self.assertTrue(all(not d["added"] and not d["removed"] for d in good["markers"].values()))
        self.assertTrue(run(original, wrong)["markers"]["negation"]["added"])

    def test_case_13_mode_c(self):
        verify = load_module("verify_preservation", SCRIPTS_DIR / "verify_preservation.py")
        before = "申し込みを受け付ける。サーバを再起動する。\n"
        after = "申し込みを受け付ける。\n\nサーバを再起動する。\n"
        self.assertInDoc("申し込みを受け付ける。サーバを再起動する。", "--strict")
        self.assertTrue(verify.compare_strict(before, after)["only_newlines_inserted"])
        self.assertFalse(verify.compare_strict(before, after.replace("申し込み", "申込み"))["only_newlines_inserted"])
        spaced_before = "一つ目。 二つ目。\n"
        self.assertTrue(verify.compare(spaced_before, "一つ目。\n\n二つ目。\n")["identical"])  # 既定の検証は合格にしてしまう
        self.assertFalse(verify.compare_strict(spaced_before, "一つ目。\n\n二つ目。\n")["only_newlines_inserted"])


if __name__ == "__main__":
    unittest.main()
