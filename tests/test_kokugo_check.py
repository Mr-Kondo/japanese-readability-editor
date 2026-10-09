"""国語の表記・用法の検査エンジン(scripts/kokugo_engine.py)のテスト。

期待値は、実装の出力から作らない。文化庁の公式資料の例示・許容・適用範囲(tests/kokugo_sources_data.py、
references/kokugo-sources.md)と、保存要件(誤修正を防ぐこと)から決めている。
各テストの docstring に、期待の根拠を書いた。
"""

import unittest

import kokugo_sources_data as src
from helpers import SCRIPTS_DIR, load_module

engine = load_module("kokugo_engine", SCRIPTS_DIR / "kokugo_engine.py")
RULESET = engine.load_rules()
GT, PE, OF = engine.PROFILES
FLAG = engine.FLAG_CATEGORIES


def check(text, profile=GT, **kwargs):
    return engine.check_text(text, profile, RULESET, **kwargs)


def by_rule(findings, rule_id):
    return [f for f in findings if f["rule_id"] == rule_id]


def flagged(findings, rule_id=None):
    return [f for f in findings if f["category"] in FLAG and (rule_id is None or f["rule_id"] == rule_id)]


def categories(text, rule_id, profile):
    return sorted({f["category"] for f in by_rule(check(text, profile), rule_id)})


class DetectsPrimarySourceTargetsTest(unittest.TestCase):
    """要件1: 一次資料に基づく検出対象を検出できる。"""

    def assert_detected(self, text, profile, rule_id, category, matched, candidate=None):
        found = [f for f in by_rule(check(text, profile), rule_id) if f["text"] == matched]
        self.assertEqual(len(found), 1, (text, profile, rule_id, [(f["text"], f["category"]) for f in check(text, profile)]))
        self.assertEqual(found[0]["category"], category, (text, profile))
        if candidate is not None:
            self.assertIn(candidate, found[0]["candidates"], (text, profile))
        return found[0]

    def test_the_omitted_okurigana_nouns_of_the_cabinet_directive(self):
        """内閣訓令 別紙2(1)ただし書: 申込み・取扱い など186語は、送り仮名を省くものとする。名詞なら official で error。"""
        for text, matched, candidate in [
            ("申し込みを受け付ける。", "申し込み", "申込み"),
            ("取り扱いの方法を示す。", "取り扱い", "取扱い"),
            ("打ち合わせの結果を共有する。", "打ち合わせ", "打合せ"),
            ("問い合わせを受け付ける。", "問い合わせ", "問合せ"),
            ("引き渡しの日を決める。", "引き渡し", "引渡し"),
            ("売り上げが増えた。", "売り上げ", "売上げ"),
            ("組み合わせを試す。", "組み合わせ", "組合せ"),
            ("引き継ぎを行う。", "引き継ぎ", "引継ぎ"),
        ]:
            with self.subTest(text=text):
                found = self.assert_detected(text, OF, "KOKUGO-OKURI-003", "error", matched, candidate)
                self.assertIn("NAIKAKU-KUNREI-2010", found["source_ids"])

    def test_the_historical_kana_errors_are_errors_in_every_profile(self):
        """現代仮名遣い 第2 2(助詞の『は』は『は』と書く)と第2 4(動詞の『いう』は『いう』と書く)。"""
        for wrong, right in src.GENDAI_HA_ERRORS:
            for profile in engine.PROFILES:
                with self.subTest(wrong=wrong, profile=profile):
                    self.assert_detected(f"{wrong}、確認する。", profile, "KOKUGO-KANA-001", "error", wrong, right)
        for wrong, right in src.GENDAI_IU_ERRORS:
            with self.subTest(wrong=wrong):
                self.assert_detected(f"{wrong}場合は再実行する。", GT, "KOKUGO-KANA-002", "error", wrong, right)

    def test_words_with_outside_readings_that_the_guideline_lists(self):
        """考え方 解説 Ⅰ-1(2)ア(ア): 敢えて・予め・未だ・概ね・自ずから・宜しく・以て・為す は仮名で書く。"""
        for word, kana in src.GUIDE_KUN_OUTSIDE:
            with self.subTest(word=word):
                found = self.assert_detected(f"これは{word}確認する。", OF, "KOKUGO-KANJI-002", "recommendation", word)
                self.assertTrue(any(c.startswith(kana) or kana.startswith(c) for c in found["candidates"]), found["candidates"])

    def test_conjunctions_and_adverbs_of_the_cabinet_directive(self):
        """内閣訓令 別紙1(2): 接続詞『ただし』『かつ』は仮名、4語の接続詞は漢字、副詞『全て』『特に』は漢字。"""
        self.assert_detected("但し、例外がある。", OF, "KOKUGO-KANJI-003", "recommendation", "但し", "ただし")
        self.assert_detected("速い。且つ、安定する。", OF, "KOKUGO-KANJI-003", "recommendation", "且つ", "かつ")
        for kana, kanji in [("および", "及び"), ("ならびに", "並びに"), ("または", "又は"), ("もしくは", "若しくは")]:
            self.assert_detected(f"AとB{kana}Cを指定する。", OF, "KOKUGO-KANJI-004", "recommendation", kana, kanji)
        for kana, kanji in [("すべて", "全て"), ("とくに", "特に"), ("すでに", "既に"), ("かならず", "必ず"), ("つねに", "常に"),
                            ("ただちに", "直ちに"), ("たとえば", "例えば"), ("ふたたび", "再び")]:
            self.assert_detected(f"{kana}確認する。", OF, "KOKUGO-KANJI-005", "recommendation", kana, kanji)

    def test_the_okurigana_permitted_forms_are_recommended_against_in_official(self):
        """内閣訓令 別紙2(2): 許容を適用してよいのは通則2・4・6だけ。通則1の許容形は、official では本則への推奨が出る。"""
        for permitted, rule in src.OKURI_TSUSOKU1_PERMITTED:
            with self.subTest(permitted=permitted):
                self.assertEqual(categories(f"それを{permitted}。", "KOKUGO-OKURI-001", OF), ["recommendation"])

    def test_notation_rules_of_the_guideline(self):
        """考え方 解説 Ⅰ-3エ(長音)、Ⅰ-3ウ(ヴ)、Ⅰ-4ケ(か所)、Ⅰ-5(1)ア(ピリオド)、Ⅲ-1オ(するべき)。"""
        self.assert_detected("サーバを再起動する。", OF, "KOKUGO-GAIRAI-001", "recommendation", "サーバ", "サーバー")
        self.assert_detected("カテゴリを分ける。", OF, "KOKUGO-GAIRAI-001", "recommendation", "カテゴリ", "カテゴリー")
        self.assert_detected("ヴァイオリンを弾く。", OF, "KOKUGO-GAIRAI-002", "recommendation", "ヴァ", "バ")
        self.assert_detected("3ヶ所を直す。", OF, "KOKUGO-NUM-001", "recommendation", "3ヶ所", "3か所")
        self.assert_detected("7カ月かかる。", OF, "KOKUGO-NUM-001", "recommendation", "7カ月", "7か月")
        self.assert_detected("設定を確認する．", OF, "KOKUGO-PUNCT-001", "recommendation", "．", "。")
        self.assert_detected("検討するべきだ。", OF, "KOKUGO-EXPR-001", "recommendation", "するべき", "すべき")

    def test_redundant_expressions_that_the_guideline_lists(self):
        """考え方 解説 Ⅱ-5ウ(ア): 諸先生方・各都道府県ごとに・第1日目・約20名くらい・違和感を感じる はむやみに用いない。"""
        for text, matched in [("諸先生方に伝える。", "諸先生方"), ("各都道府県ごとに集計する。", "各都道府県ごとに"), ("第1日目に実施する。", "第1日目"),
                              ("約20名くらいが参加した。", "約20名くらい"), ("違和感を感じる。", "違和感を感じ")]:
            with self.subTest(text=text):
                self.assert_detected(text, OF, "KOKUGO-EXPR-002", "recommendation", matched)

    def test_an_outside_kanji_is_found_by_its_character_only(self):
        """考え方 解説 Ⅰ-1(1)ア: 絆は表にない漢字。固有名詞か専門用語かは機械では決まらないので、要確認にとどめる。"""
        found = self.assert_detected("地域の絆を深める。", OF, "KOKUGO-KANJI-001", "needs_context", "絆")
        self.assertEqual(found["candidates"], [])

    def test_a_finding_in_a_later_line_reports_its_position_and_reason(self):
        """規則 ID、位置、該当表記、区分、理由、出典 ID(キーの形式は CLI のテストで固定する)。"""
        finding = check("一行目。\n申し込みを受け付ける。", OF)[0]
        self.assertEqual((finding["line"], finding["column"]), (2, 1))
        self.assertEqual(finding["text"], "申し込み")
        self.assertEqual(finding["length"], 4)
        self.assertTrue(finding["reason"])
        self.assertTrue(finding["source_ids"])


class AcceptedVariantsTest(unittest.TestCase):
    """要件2: 許容形を誤りと判定しない。"""

    def test_tsusoku1_permitted_forms_are_accepted_in_general_tech(self):
        """送り仮名の付け方 通則1 許容: 表わす・著わす・現われる・行なう・断わる・賜わる。"""
        for permitted, regular in src.OKURI_TSUSOKU1_PERMITTED:
            with self.subTest(permitted=permitted):
                found = check(f"それを{permitted}。", GT)
                self.assertEqual(flagged(found), [], found)
                self.assertIn("accepted_variant", {f["category"] for f in found})

    def test_tsusoku2_permitted_forms_are_accepted_in_general_tech(self):
        """送り仮名の付け方 通則2 許容: 浮ぶ・生れる・押える・捕える・晴やか・積る・聞える・起る・落す・暮す・当る・終る・変る。"""
        samples = {"浮ぶ": "雲が浮ぶ。", "生れる": "子が生れる。", "押える": "手で押える。", "捕える": "犯人を捕える。", "晴やかだ": "晴やかな日だ。",
                   "積る": "雪が積る。", "聞える": "声が聞える。", "起る": "問題が起る。", "落す": "物を落す。", "暮す": "日々を暮す。",
                   "当る": "球に当る。", "終る": "仕事が終る。", "変る": "状況が変る。"}
        self.assertEqual({p for p, _ in src.OKURI_TSUSOKU2_PERMITTED}, set(samples))
        for permitted, text in samples.items():
            with self.subTest(permitted=permitted):
                found = check(text, GT)
                self.assertEqual(flagged(found), [], found)
                self.assertEqual([f["category"] for f in by_rule(found, "KOKUGO-OKURI-002")], ["accepted_variant"])

    def test_tsusoku2_permitted_forms_are_never_errors_in_any_profile(self):
        """内閣訓令 別紙2(2): 必要と認める場合は通則2の許容を適用して差し支えない。official でも誤りではない。"""
        for permitted, text in [("終る", "仕事が終る。"), ("変る", "状況が変る。"), ("起る", "問題が起る。")]:
            for profile in engine.PROFILES:
                with self.subTest(permitted=permitted, profile=profile):
                    self.assertNotIn("error", {f["category"] for f in check(text, profile)})

    def test_du_permitted_forms_are_accepted_in_every_profile(self):
        """現代仮名遣い 第2 5(2): 『じ』『ず』を本則とし、『ぢ』『づ』で書くこともできる。誤りではない。"""
        for permitted, regular in src.GENDAI_DU_PERMITTED:
            for profile in engine.PROFILES:
                with self.subTest(permitted=permitted, profile=profile):
                    found = check(f"{permitted}。", profile)
                    self.assertEqual(flagged(found), [], found)
                    self.assertEqual([f["category"] for f in by_rule(found, "KOKUGO-KANA-004")], ["accepted_variant"])
                    self.assertEqual(by_rule(found, "KOKUGO-KANA-004")[0]["candidates"], [regular])

    def test_omitting_the_long_vowel_mark_is_accepted_in_general_tech(self):
        """外来語の表記 留意事項その2 Ⅲ 3 注3: 慣用に応じて『ー』を省くことができる(コンピュータ、エレベータ)。"""
        for word in ("コンピュータ", "エレベータ", "サーバ", "ユーザ"):
            with self.subTest(word=word):
                found = check(f"{word}を使う。", GT)
                self.assertEqual(flagged(found), [], found)

    def test_the_v_kana_is_accepted_in_general_tech(self):
        """外来語の表記 第2表: 『ヴ』は原音や原つづりになるべく近く書き表そうとする場合に用いる仮名。"""
        self.assertEqual(flagged(check("ヴァイオリンを弾く。", GT)), [])

    def test_the_okurigana_full_forms_are_accepted_outside_official(self):
        """送り仮名の付け方 通則6 本則(申し込み)と考え方 解説 Ⅰ-2ウ(解説・広報等では省かずに書ける)。"""
        for profile in (GT, PE):
            with self.subTest(profile=profile):
                self.assertEqual(flagged(check("申し込みを受け付ける。", profile)), [])

    def test_kana_for_adverbs_is_accepted_for_explanations(self):
        """考え方 本文 Ⅰ-1 ただし書: 解説・広報等では、漢字を用いることになっている語も仮名で書いてよい。"""
        for text in ("すべての設定を確認する。", "AおよびBを指定する。", "すでに完了している。"):
            with self.subTest(text=text):
                self.assertEqual(flagged(check(text, PE)), [])

    def test_the_regular_forms_are_not_reported_at_all(self):
        """本則・公用文の形は、どの設定でも指摘の対象にならない。"""
        text = "全ての設定を確認する。A及びBを指定する。行う。表す。3か所を直す。サーバーを再起動する。申込みを受け付ける。"
        for profile in engine.PROFILES:
            with self.subTest(profile=profile):
                self.assertEqual([f for f in check(text, profile) if f["category"] != "excluded"], [])

    def test_the_omitted_okurigana_forms_of_the_directive_are_never_flagged(self):
        """内閣訓令が省くものとする186語そのもの(省いた形)を、どの設定でも指摘しない(変更してはいけない反例)。"""
        self.assertEqual(len(src.KUNREI_186), 186)
        text = "\n\n".join(f"{word}を確認する。" for word in src.KUNREI_186)
        for profile in engine.PROFILES:
            with self.subTest(profile=profile):
                self.assertEqual(flagged(check(text, profile), "KOKUGO-OKURI-003"), [])

    def test_redundant_expressions_that_are_not_clearly_wrong_are_left_alone(self):
        """考え方 解説 Ⅱ-5ウ(ア): 慣用や強調として『一概に誤りとも言えない』例(従来から、まず最初に 等)は検出しない。"""
        for expression in src.GUIDE_NOT_REDUNDANT:
            for profile in engine.PROFILES:
                with self.subTest(expression=expression, profile=profile):
                    self.assertEqual(by_rule(check(f"{expression}の方法を続ける。", profile), "KOKUGO-EXPR-002"), [])

    def test_kanji_that_the_directive_keeps_are_not_flagged(self):
        """内閣訓令 別紙1(2)イ・オ: 『かなり』『やはり』『よほど』は仮名が正しい。『又は』『及び』は漢字が正しい。『従って』(動詞)は漢字。"""
        for text in ("かなり重要である。", "やはり必要だ。", "よほどの理由がある。", "A又はBを指定する。", "命令に従って実行する。"):
            for profile in engine.PROFILES:
                with self.subTest(text=text, profile=profile):
                    self.assertEqual(flagged(check(text, profile), "KOKUGO-KANJI-003"), [])
                    self.assertEqual(flagged(check(text, profile), "KOKUGO-KANJI-004"), [])

    def test_helper_constructions_in_kanji_are_kept_when_they_are_real_actions(self):
        """考え方 解説 Ⅰ-1(3)ア: 実際の動作を表す場合は漢字(賞状を頂く、出来が良い)。"""
        for text in ("賞状を頂く。", "出来が良い。", "声が良い。", "資格が欲しい。"):
            with self.subTest(text=text):
                self.assertEqual(flagged(check(text, OF), "KOKUGO-KANJI-007"), [])

    def test_simple_cases_that_look_similar_but_are_correct(self):
        """似て見えるが正しい表記を、誤りにしない。"""
        for text in ("いちじくを食べる。", "いちじるしい変化がある。", "つづきを読む。", "ちぢむ。", "みかづきが出る。", "こんにちは。", "という。"):
            with self.subTest(text=text):
                self.assertEqual(flagged(check(text, OF)), [])


class ProfileMatrixTest(unittest.TestCase):
    """要件3: 同じ表記でも、適用設定によって期待する判定が変わる。(general-tech, public-explanation, official)"""

    MATRIX = [
        # 外来語の表記 留意事項その2 Ⅲ 3 注3(告示は省略を許容)と考え方 解説 Ⅰ-3エ(長音符号を用いて書くのが原則)
        ("サーバを再起動する。", "KOKUGO-GAIRAI-001", ("accepted_variant", "recommendation", "recommendation")),
        # 送り仮名の付け方 通則1 許容と、内閣訓令 別紙2(2)(許容は通則2・4・6)
        ("処理を行なう。", "KOKUGO-OKURI-001", ("accepted_variant", "recommendation", "recommendation")),
        # 内閣訓令 別紙2(1)ただし書(省くものとする)と、考え方 解説 Ⅰ-2ウ(解説・広報等は省かずに書ける)
        ("申し込みを受け付ける。", "KOKUGO-OKURI-003", ("accepted_variant", "accepted_variant", "error")),
        # 内閣訓令 別紙1(2)イ(副詞は漢字)と、考え方 本文 Ⅰ-1 ただし書(解説・広報等は仮名でよい)
        ("すべての設定を確認する。", "KOKUGO-KANJI-005", ("accepted_variant", "accepted_variant", "recommendation")),
        ("AおよびBを指定する。", "KOKUGO-KANJI-004", ("accepted_variant", "accepted_variant", "recommendation")),
        # 内閣訓令 別紙1(2)オ(接続詞は仮名)と、考え方 解説 Ⅰ-1(3)エ(法令に倣い仮名で書く)
        ("速い。且つ、安定する。", "KOKUGO-KANJI-003", ("accepted_variant", "recommendation", "recommendation")),
        # 考え方 解説 Ⅰ-4ケ
        ("3ヶ所を直す。", "KOKUGO-NUM-001", ("accepted_variant", "recommendation", "recommendation")),
        # 常用漢字表 前書き2(専門分野・個々人の表記に及ばない)と、考え方 解説 Ⅰ-1(1)ア・ウ(固有名詞は対象外)
        ("地域の絆を深める。", "KOKUGO-KANJI-001", ("accepted_variant", "needs_context", "needs_context")),
        # 異字同訓 前書き3(一つの参考)と、考え方 本文 Ⅱ-5ア(イ)
        ("時間を計る。", "KOKUGO-IJIDOKUN-001", ("accepted_variant", "needs_context", "needs_context")),
        # 現代仮名遣い 第2 2(どの設定でも誤り)
        ("こんにちわ、田中です。", "KOKUGO-KANA-001", ("error", "error", "error")),
        # 考え方 解説 Ⅱ-6ウ(解説・広報等の文末)。告示・通知等には触れていない
        ("資料がございます。", "KOKUGO-EXPR-003", ("accepted_variant", "recommendation", "accepted_variant")),
        # 現代仮名遣い 第2 5(2)(許容形。設定によらない)
        ("いなづまが光る。", "KOKUGO-KANA-004", ("accepted_variant", "accepted_variant", "accepted_variant")),
        # 考え方 解説 Ⅰ-1(2)ア(ア)
        ("予め確認する。", "KOKUGO-KANJI-002", ("accepted_variant", "recommendation", "recommendation")),
        # 考え方 解説 Ⅲ-1オ
        ("検討するべきだ。", "KOKUGO-EXPR-001", ("accepted_variant", "recommendation", "recommendation")),
    ]

    def test_the_same_text_gets_different_categories_by_profile(self):
        for text, rule_id, expected in self.MATRIX:
            with self.subTest(text=text):
                actual = tuple(categories(text, rule_id, profile)[0] if categories(text, rule_id, profile) else None for profile in engine.PROFILES)
                self.assertEqual(actual, expected, text)

    def test_the_default_profile_is_general_tech(self):
        self.assertEqual(engine.DEFAULT_PROFILE, "general-tech")
        self.assertEqual(check("サーバを再起動する。"), check("サーバを再起動する。", GT))

    def test_unknown_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            check("あ。", "strict")

    def test_a_formal_tone_alone_does_not_make_the_text_official(self):
        """文体が堅いという理由だけで official にしない。設定は呼び出し側が指定し、文章から推測しない。"""
        formal = "本通知は、次のとおり定める。申し込みは、所定の窓口で受け付ける。"
        self.assertEqual(flagged(check(formal)), [])  # 既定の general-tech では、送り仮名を省かない形を指摘しない
        self.assertTrue(flagged(check(formal, OF), "KOKUGO-OKURI-003"))


class NeedsContextTest(unittest.TestCase):
    """要件4: 文脈が不足する場合は needs_context とする。"""

    def test_a_possible_verb_form_is_not_a_certain_noun(self):
        """申し込み、 は動詞『申し込む』の連用形(中止法)かもしれない。名詞と確定できるのは直後が『が』『を』『の』のとき。"""
        found = by_rule(check("先に申し込み、後で支払う。", OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["needs_context"])
        self.assertEqual(found[0]["reason_code"], "verb-form-possible")

    def test_a_compound_may_be_covered_by_tsusoku7(self):
        """通則7(申込書・取扱所 など)を適用する語は、186語に含まれない。直後が漢字の複合語は、確定した誤りにしない。"""
        found = by_rule(check("申し込み書を提出する。", OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["needs_context"])
        self.assertEqual(found[0]["reason_code"], "compound-word")

    def test_a_word_whose_part_of_speech_is_not_known_is_never_an_error_or_recommendation(self):
        """動詞の連用形+『て』になりうる語(きわめて、はじめて、はたして、もっとも、さらに 等)。"""
        for word in ("きわめて", "はじめて", "はたして", "もっとも", "さらに", "いたって", "つとめて", "たいして"):
            for profile in engine.PROFILES:
                with self.subTest(word=word, profile=profile):
                    found = by_rule(check(f"{word}重要である。", profile), "KOKUGO-KANJI-005")
                    self.assertTrue(found, word)
                    self.assertNotIn(found[0]["category"], ("error", "recommendation"))

    def test_every_ambiguous_entry_in_the_data_stays_below_a_confirmed_finding(self):
        """規則データの ambiguous な語は、どの設定でも error / recommendation にならない。"""
        checked = 0
        for rule in RULESET.rules:
            detection = rule.data.get("detection") or {}
            for entry in detection.get("entries", []):
                if not entry.get("ambiguous"):
                    continue
                literal = engine_literal(entry["pattern"])
                for profile in engine.PROFILES:
                    found = [f for f in check(f"これは{literal}重要である。", profile) if f["rule_id"] == rule.id and f["text"] == literal]
                    self.assertTrue(found, (rule.id, literal, profile))
                    self.assertNotIn(found[0]["category"], ("error", "recommendation"), (rule.id, literal, profile))
                    checked += 1
        self.assertGreater(checked, 20)

    def test_a_dubious_zu_is_not_declared_wrong_or_right(self):
        """現代仮名遣い 第2 5(2)の例示は『ひとりずつ』まで。『少しづつ』への適用は例示から断定しない。"""
        for profile in engine.PROFILES:
            with self.subTest(profile=profile):
                self.assertEqual(categories("少しづつ進める。", "KOKUGO-KANA-005", profile), ["needs_context"])

    def test_historical_kana_characters_may_be_proper_nouns(self):
        """現代仮名遣い 前書き: 固有名詞は対象外。ゐ・ゑ・ヱ は要確認にとどめる。"""
        for text in ("ヱビスを飲む。", "ゐる場所。"):
            with self.subTest(text=text):
                self.assertEqual(categories(text, "KOKUGO-KANA-006", OF), ["needs_context"])

    def test_isidokun_never_gets_a_candidate_nor_a_verdict(self):
        """異字同訓 前書き3: 一つの参考。読みだけでは決まらない。候補を示さず、要確認にとどめる。"""
        for text in ("時間を計る。", "長さを測る。", "目的を図る。", "意見を諮る。", "計画を立てる。"):
            for profile in (PE, OF):
                found = by_rule(check(text, profile), "KOKUGO-IJIDOKUN-001")
                for finding in found:
                    self.assertEqual(finding["category"], "needs_context")
                    self.assertEqual(finding["candidates"], [])

    def test_ijidokun_reports_each_form_once_with_its_count(self):
        found = by_rule(check("時間を計る。次も計る。さらに計る。", OF), "KOKUGO-IJIDOKUN-001")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["detail"]["count"], 3)
        self.assertEqual(found[0]["detail"]["reading"], "はかる")

    def test_the_joyo_check_covers_character_forms_not_readings(self):
        """常用漢字の字種だけを確認して、音訓まで確認済みとしない。予・以・為 は表内の字種。音訓が表外の語は、登録した語だけ検出する。"""
        text = "予め確認する。以て足りる。為す。"
        found = check(text, OF)
        self.assertEqual(by_rule(found, "KOKUGO-KANJI-001"), [])  # 字種はすべて表内
        self.assertEqual(len(flagged(found, "KOKUGO-KANJI-002")), 3)  # 音訓が表外の語は、登録した語だけ
        unregistered = check("拠り所を探す。", OF)  # 『拠』は表内の字種。この語の音訓は登録していないので検出しない(未検査)
        self.assertEqual(by_rule(unregistered, "KOKUGO-KANJI-001"), [])


def engine_literal(pattern: str) -> str:
    import re

    return re.sub(r"\\(.)", r"\1", pattern)


class GlossaryAndExclusionTest(unittest.TestCase):
    """要件5: 固有名詞・専門用語の除外指定が機能する。完全自動で識別できるとは仮定しない。"""

    def test_a_protected_term_is_excluded_while_others_are_still_checked(self):
        glossary = engine.parse_glossary("protect: 髙橋\n")
        found = check("髙橋さんの絆を深める。", OF, glossary=glossary)
        outside = by_rule(found, "KOKUGO-KANJI-001")
        self.assertEqual([(f["text"], f["category"]) for f in outside], [("髙", "excluded"), ("絆", "needs_context")])
        self.assertEqual(outside[0]["reason_code"], "protected:glossary:髙橋")

    def test_without_the_glossary_the_same_name_is_not_assumed_to_be_proper(self):
        """固有名詞を自動では識別しない: 用語集がなければ要確認として示す。"""
        found = by_rule(check("髙橋さんが来た。", OF), "KOKUGO-KANJI-001")
        self.assertEqual([f["category"] for f in found], ["needs_context"])

    def test_a_bare_line_is_a_protected_term(self):
        glossary = engine.parse_glossary("# 組織の用語集\n\nKubernetes\n申し込みフォーム\n")
        self.assertEqual(glossary.protect, ["Kubernetes", "申し込みフォーム"])
        found = check("申し込みフォームで申し込みを受け付ける。", OF, glossary=glossary)
        cats = [(f["text"], f["category"]) for f in by_rule(found, "KOKUGO-OKURI-003")]
        self.assertEqual(cats, [("申し込み", "excluded"), ("申し込み", "error")])

    def test_glossary_parsing(self):
        glossary = engine.parse_glossary("﻿# コメント\nprotect: A社\nuse: サーバ\nprotect: A社\n\n  B製品  \nuse: ユーザ\n")
        self.assertEqual(glossary.protect, ["A社", "B製品"])
        self.assertEqual(glossary.use, ["サーバ", "ユーザ"])
        merged = engine.merge_glossaries([glossary, engine.parse_glossary("protect: C\nprotect: A社\n")])
        self.assertEqual(merged.protect, ["A社", "B製品", "C"])

    def test_the_organization_notation_conflicting_with_the_profile_is_shown_not_silently_applied(self):
        """組織の用語集(use: サーバ)と公用文の推奨(サーバー)が競合するとき、片方を黙って適用せず、競合を示す。"""
        glossary = engine.parse_glossary("use: サーバ\n")
        found = by_rule(check("サーバを再起動する。", OF, glossary=glossary), "KOKUGO-GAIRAI-001")
        self.assertEqual([f["category"] for f in found], ["needs_context"])
        self.assertEqual(found[0]["reason_code"], "glossary:use-conflict")
        self.assertIn("サーバ", found[0]["reason"])
        self.assertIn("黙って片方を適用しない", found[0]["reason"])
        without = by_rule(check("サーバを再起動する。", OF), "KOKUGO-GAIRAI-001")
        self.assertEqual([f["category"] for f in without], ["recommendation"])

    def test_a_use_term_does_not_change_an_accepted_variant(self):
        glossary = engine.parse_glossary("use: サーバ\n")
        found = by_rule(check("サーバを再起動する。", GT, glossary=glossary), "KOKUGO-GAIRAI-001")
        self.assertEqual([f["category"] for f in found], ["accepted_variant"])

    def test_the_ignore_region_excludes_the_enclosed_lines(self):
        text = "申し込みを受け付ける。\n<!-- kokugo-ignore-start -->\n申し込みを受け付ける。\n<!-- kokugo-ignore-end -->\n申し込みを受け付ける。\n"
        found = by_rule(check(text, OF), "KOKUGO-OKURI-003")
        self.assertEqual([(f["line"], f["category"]) for f in found], [(1, "error"), (3, "excluded"), (5, "error")])
        self.assertEqual(found[1]["reason_code"], "protected:ignore_region")

    def test_an_unclosed_ignore_region_runs_to_the_end(self):
        text = "<!-- kokugo-ignore-start -->\n申し込みを受け付ける。\n"
        self.assertEqual([f["category"] for f in by_rule(check(text, OF), "KOKUGO-OKURI-003")], ["excluded"])


class ProtectedZonesTest(unittest.TestCase):
    """要件6: コード、URL、引用、frontmatter を誤検出しない。"""

    DOC = (
        "---\n"
        "title: 申し込みとサーバ 絆 こんにちわ\n"
        "---\n"
        "\n"
        "本文の申し込みを受け付ける。\n"
        "\n"
        "> 引用の申し込みを。こんにちわ。\n"
        "\n"
        "`申し込みを` と [リンク](https://example.com/申し込みを) と https://example.com/申し込みを と <https://example.com/申し込みを> を参照。\n"
        "\n"
        "```text\n"
        "申し込みを こんにちわ 絆\n"
        "```\n"
        "\n"
        "~~~\n"
        "申し込みを\n"
        "~~~\n"
        "\n"
        "<!-- 申し込みを -->\n"
    )

    def test_only_the_prose_is_flagged(self):
        found = check(self.DOC, OF)
        self.assertEqual([(f["rule_id"], f["line"], f["category"]) for f in flagged(found)],
                         [("KOKUGO-OKURI-003", 5, "error")])
        excluded = [f for f in found if f["category"] == "excluded"]
        self.assertGreaterEqual(len(excluded), 9)

    def test_each_kind_of_protection_is_named(self):
        kinds = {f["reason_code"] for f in check(self.DOC, OF) if f["category"] == "excluded"}
        for expected in ("protected:frontmatter", "protected:quote", "protected:inline_code", "protected:url", "protected:fenced_code",
                         "protected:html_comment"):
            self.assertIn(expected, kinds)

    def test_a_japanese_path_inside_a_url_is_part_of_the_url(self):
        found = by_rule(check("参照: https://ja.wikipedia.org/wiki/申し込みを 以上。", OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["excluded"])

    def test_prose_between_two_code_spans_is_not_swallowed(self):
        found = by_rule(check("`a` 申し込みを `b` 申し込みを", OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["error", "error"])

    def test_an_unclosed_fence_protects_to_the_end(self):
        found = by_rule(check("本文。\n```\n申し込みを\n", OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["excluded"])

    def test_a_longer_fence_is_closed_only_by_an_equally_long_fence(self):
        text = "````\n```\n申し込みを\n```\n````\n申し込みを\n"
        found = by_rule(check(text, OF), "KOKUGO-OKURI-003")
        self.assertEqual([(f["line"], f["category"]) for f in found], [(3, "excluded"), (6, "error")])

    def test_inline_html_tags_are_protected_but_their_text_is_prose(self):
        found = by_rule(check('<a href="/申し込みを">申し込みを</a>', OF), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["excluded", "error"])

    def test_plain_text_protects_only_urls(self):
        found = by_rule(check("> 申し込みを\nhttps://example.com/申し込みを\n", OF, markdown=False), "KOKUGO-OKURI-003")
        self.assertEqual([f["category"] for f in found], ["error", "excluded"])

    def test_a_quote_is_not_a_target_of_consistency_either(self):
        text = "> サーバを止める。\n\nサーバーを再起動する。\n"
        self.assertEqual(by_rule(check(text, GT), "KOKUGO-CONSIST-001"), [])

class PositionsAndDeterminismTest(unittest.TestCase):
    TEXT = ("# 手引\r\n\r\n申し込みを受け付ける。サーバを再起動する。\r\n処理を行なう。予め確認する。\r\n"
            "3ヶ所を直す。地域の絆を深める。時間を計る。こんにちわ。\r\n")

    def test_offsets_point_at_the_reported_text(self):
        normalized = engine.normalize_newlines(self.TEXT)
        for profile in engine.PROFILES:
            for finding in check(self.TEXT, profile):
                with self.subTest(profile=profile, finding=finding["rule_id"]):
                    self.assertEqual(normalized[finding["offset"]: finding["offset"] + finding["length"]], finding["text"])
                    line = normalized.split("\n")[finding["line"] - 1]
                    self.assertEqual(line[finding["column"] - 1: finding["column"] - 1 + finding["length"]], finding["text"])

    def test_crlf_and_lf_give_the_same_findings(self):
        self.assertEqual(check(self.TEXT, OF), check(self.TEXT.replace("\r\n", "\n"), OF))

    def test_the_same_input_gives_the_same_output(self):
        first = check(self.TEXT, OF)
        for _ in range(3):
            self.assertEqual(check(self.TEXT, OF), first)

    def test_findings_are_ordered_by_position(self):
        found = check(self.TEXT, OF)
        keys = [(f["offset"], f["rule_id"], f["length"]) for f in found]
        self.assertEqual(keys, sorted(keys))

    def test_reordering_the_rules_does_not_change_the_output(self):
        reordered = engine.RuleSet(RULESET.doc, RULESET.joyo, RULESET.ijidokun, list(reversed(RULESET.rules)))
        self.assertEqual(engine.check_text(self.TEXT, OF, reordered), check(self.TEXT, OF))


class JoyoKanjiTest(unittest.TestCase):
    """常用漢字表(平成22年内閣告示第2号)の字種。本表の抜き取りで、抽出が正しいことを確かめる。"""

    def test_the_table_has_the_official_count(self):
        """常用漢字表 前書き: 本表には字種 2136 字を掲げる。"""
        self.assertEqual(RULESET.joyo.count, 2136)
        self.assertEqual(len(RULESET.joyo.chars), 2136)

    def test_spot_checks_against_the_main_table(self):
        """本表を読んで写した抜き取り。2010年の改定で加わった字(鬱・彙・茨・媛・岡 など)と『𠮟』を含む。"""
        for ch in "亜鬱彙茨媛岡埼栃熊阪奈山𠮟":
            self.assertIn(ch, RULESET.joyo.chars, ch)
        for ch in "絆叱髙﨑":
            self.assertNotIn(ch, RULESET.joyo.chars, ch)

    def test_readings_spot_checks(self):
        """本表の音訓欄の抜き取り(予・以・為 は音だけ、経は訓『へる』だけ、止は『とまる・とめる』)。"""
        readings = RULESET.joyo.readings
        self.assertEqual(readings["予"], ["ヨ"])
        self.assertEqual(readings["以"], ["イ"])
        self.assertEqual(readings["為"], ["イ"])
        self.assertEqual(readings["経"], ["ケイ", "キョウ", "へる"])
        self.assertEqual(readings["止"], ["シ", "とまる", "とめる"])
        self.assertEqual(readings["留"], ["リュウ", "ル", "とめる", "とまる"])
        self.assertEqual(readings["哀"], ["アイ", "あわれ", "あわれむ"])

    def test_characters_of_the_table_are_not_reported_as_outside(self):
        found = check("鬱を茨と媛と岡と𠮟る。", OF)
        self.assertEqual(by_rule(found, "KOKUGO-KANJI-001"), [])

    def test_a_character_outside_the_table_is_reported_once_per_run_with_a_count(self):
        found = by_rule(check("絆。絆。絆。髙橋。", OF), "KOKUGO-KANJI-001")
        self.assertEqual([(f["text"], f["detail"]["count"]) for f in found], [("絆", 3), ("髙", 1)])

    def test_iteration_marks_and_katakana_are_not_kanji_of_the_table(self):
        """々・〆・〇・ヶ は字種として数えない。"""
        self.assertEqual(by_rule(check("人々。〆切。〇印。3ヶ月。", GT), "KOKUGO-KANJI-001"), [])

    def test_in_general_tech_the_outside_kanji_is_not_flagged(self):
        """常用漢字表 前書き2: 専門分野や個々人の表記には及ばない。"""
        self.assertEqual(flagged(check("絆を深める。", GT)), [])


class ConsistencyTest(unittest.TestCase):
    """複数の表記が許容されるときだけ、文書内の統一を判断材料にする。多数派で明確な誤りを広げない。"""

    def test_mixed_allowed_forms_are_pointed_out_at_the_minority_form(self):
        text = "サーバーを止める。サーバーを再起動する。サーバーを確認する。サーバを停止する。"
        found = by_rule(check(text, GT), "KOKUGO-CONSIST-001")
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["text"], found[0]["category"], found[0]["candidates"]), ("サーバ", "recommendation", ["サーバー"]))
        self.assertEqual(found[0]["detail"]["counts"], {"サーバー": 3, "サーバ": 1})
        self.assertEqual(found[0]["provenance"], "skill-policy")
        self.assertIn("判断材料の一つにとどめ", found[0]["reason"])

    def test_when_the_longer_spelling_is_the_minority_the_more_frequent_spelling_is_the_hint(self):
        """多数派は、許容される表記のあいだで選ぶときの判断材料。『サーバ』が3件、『サーバー』が1件なら、少数の『サーバー』を指摘し、候補に『サーバ』を示す。"""
        text = "サーバを止める。サーバを再起動する。サーバを確認する。サーバーを停止する。"
        found = by_rule(check(text, GT), "KOKUGO-CONSIST-001")
        self.assertEqual([(f["text"], f["candidates"], f["category"]) for f in found], [("サーバー", ["サーバ"], "recommendation")])
        self.assertEqual(found[0]["detail"]["counts"], {"サーバ": 3, "サーバー": 1})

    def test_the_majority_does_not_spread_a_clear_error(self):
        """多数派という理由で、明確な誤りを広げない: 『こんにちわ』が3件、『こんにちは』が1件でも、誤りは誤りのまま。"""
        found = check("こんにちわ。こんにちわ。こんにちわ。こんにちは。", GT)
        self.assertEqual([f["category"] for f in by_rule(found, "KOKUGO-KANA-001")], ["error"] * 3)
        self.assertFalse(any("こんにちわ" in f.get("candidates", []) for f in found))

    def test_the_majority_does_not_spread_a_form_the_profile_recommends_against(self):
        """official では『サーバ』が3件、『サーバー』が1件でも、『サーバ』を候補にして多数派へそろえない。"""
        found = check("サーバを止める。サーバを再起動する。サーバを確認する。サーバーを停止する。", OF)
        self.assertEqual(by_rule(found, "KOKUGO-CONSIST-001"), [])
        self.assertEqual(len(flagged(found, "KOKUGO-GAIRAI-001")), 3)

    def test_a_glossary_notation_wins_over_the_majority(self):
        glossary = engine.parse_glossary("use: サーバ\n")
        text = "サーバーを止める。サーバーを再起動する。サーバを停止する。"
        found = by_rule(check(text, GT, glossary=glossary), "KOKUGO-CONSIST-001")
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0]["text"], found[0]["candidates"], found[0]["reason_code"]), ("サーバー", ["サーバ"], "glossary:use"))

    def test_digits_and_commas(self):
        found = by_rule(check("3つと４つを数える。AはB，Cは、D。", GT), "KOKUGO-CONSIST-001")
        self.assertEqual(sorted(f["text"] for f in found), sorted(["４", "，"]))  # 全角数字と全角コンマが、少数の側として指摘される

    def test_consistent_text_is_quiet(self):
        text = "サーバーを止める。サーバーを再起動する。3つ。4つ。A、B、C。"
        self.assertEqual(by_rule(check(text, GT), "KOKUGO-CONSIST-001"), [])

    def test_a_single_form_is_never_a_mixture(self):
        self.assertEqual(by_rule(check("サーバを止める。サーバを再起動する。", GT), "KOKUGO-CONSIST-001"), [])


if __name__ == "__main__":
    unittest.main()
