"""scripts/measure.py のテスト。"""

import json
import unittest
from pathlib import Path

from helpers import FIXTURES, SCRIPTS_DIR, load_module, run_script, temporary_directory

measure = load_module("measure", SCRIPTS_DIR / "measure.py")
SCRIPT = SCRIPTS_DIR / "measure.py"


def analyze(text: str, **kwargs):
    return measure.analyze_text(text, "test.md", **kwargs)


class OrdinaryTextTest(unittest.TestCase):
    def test_counts_for_plain_sentences(self):
        text = (FIXTURES / "sample_ja.md").read_text(encoding="utf-8")
        metrics = analyze(text).metrics
        self.assertEqual(metrics.paragraphs, 2)
        self.assertEqual(metrics.sentences, 4)
        self.assertEqual(metrics.chars, 38)  # 見出しは数えない
        self.assertEqual(metrics.long_paragraphs, 0)
        self.assertEqual(metrics.long_sentences, 0)
        self.assertEqual(metrics.commas, 0)

    def test_character_ratios(self):
        metrics = analyze("漢字ひらがな。").metrics
        data = metrics.to_dict()
        self.assertEqual(metrics.chars, 7)
        self.assertEqual(metrics.kanji, 2)
        self.assertEqual(metrics.hiragana, 4)
        self.assertAlmostEqual(data["kanji_ratio"], 2 / 7, places=3)
        self.assertAlmostEqual(data["hiragana_ratio"], 4 / 7, places=3)

    def test_commas_per_sentence(self):
        data = analyze("りんご、みかん、ぶどうを買った。次に帰った。").metrics.to_dict()
        self.assertEqual(data["sentences"], 2)
        self.assertEqual(data["commas_per_sentence"], 1.0)

    def test_average_lengths(self):
        data = analyze("あいう。\n\nえおかきく。").metrics.to_dict()
        self.assertEqual(data["paragraphs"], 2)
        self.assertEqual(data["avg_paragraph_length"], 5.0)
        self.assertEqual(data["avg_sentence_length"], 5.0)

    def test_empty_text_does_not_divide_by_zero(self):
        data = analyze("").metrics.to_dict()
        self.assertEqual(data["chars"], 0)
        self.assertEqual(data["avg_sentence_length"], 0.0)


class LongSentenceTest(unittest.TestCase):
    def test_sentence_threshold_is_inclusive_at_80(self):
        self.assertEqual(analyze("あ" * 79 + "。").metrics.long_sentences, 1)  # 句点を含めて80字
        self.assertEqual(analyze("あ" * 78 + "。").metrics.long_sentences, 0)

    def test_thresholds_are_configurable(self):
        metrics = analyze("あ" * 20 + "。", sentence_threshold=10).metrics
        self.assertEqual(metrics.long_sentences, 1)

    def test_quoted_period_does_not_split_a_sentence(self):
        sentences = measure.split_sentences("「今日は晴れ。」と言った。次の文。")
        self.assertEqual([s for _, s in sentences], ["「今日は晴れ。」と言った。", "次の文。"])

    def test_parenthetical_sentence_ends_at_the_closing_bracket(self):
        sentences = measure.split_sentences("（詳細は後述する。）次へ進む。")
        self.assertEqual([s for _, s in sentences], ["（詳細は後述する。）", "次へ進む。"])

    def test_text_without_a_terminator_is_one_sentence(self):
        self.assertEqual(analyze("句点のない箇条書き").metrics.sentences, 1)


class LongParagraphTest(unittest.TestCase):
    def test_paragraph_threshold_is_inclusive_at_200(self):
        exactly_200 = ("あ" * 49 + "。") * 4
        self.assertEqual(analyze(exactly_200).metrics.long_paragraphs, 1)
        self.assertEqual(analyze(exactly_200[:-1]).metrics.long_paragraphs, 0)

    def test_short_sentences_can_still_make_a_long_paragraph(self):
        metrics = analyze(("あ" * 49 + "。") * 4).metrics
        self.assertEqual(metrics.long_paragraphs, 1)
        self.assertEqual(metrics.long_sentences, 0)

    def test_blank_line_ends_a_paragraph(self):
        text = ("あ" * 49 + "。") * 2 + "\n\n" + ("あ" * 49 + "。") * 2
        self.assertEqual(analyze(text).metrics.long_paragraphs, 0)

    def test_wrapped_lines_are_one_paragraph_and_report_the_first_line(self):
        lines = ["あ" * 49 + "。"] * 4
        result = analyze("# 見出し\n\n" + "\n".join(lines))
        self.assertEqual(result.metrics.paragraphs, 1)
        self.assertEqual(result.long_paragraphs[0].line, 3)


class MarkdownHandlingTest(unittest.TestCase):
    def test_link_keeps_display_text_and_drops_the_url(self):
        blocks = measure.extract_blocks("[説明の文字](https://example.com/a/b?x=1)を読む。")
        self.assertEqual(blocks[0].text, "説明の文字を読む。")

    def test_link_with_parentheses_in_url(self):
        blocks = measure.extract_blocks("[記事](https://example.com/wiki/Foo_(bar))を読む。")
        self.assertEqual(blocks[0].text, "記事を読む。")

    def test_bare_url_is_excluded(self):
        blocks = measure.extract_blocks("詳細は https://example.com/path?q=1 を見る。")
        self.assertNotIn("example", blocks[0].text)
        self.assertNotIn("https", blocks[0].text)

    def test_url_length_does_not_make_a_sentence_long(self):
        url = "https://example.com/" + "a" * 300
        self.assertEqual(analyze(f"詳細は {url} にある。").metrics.long_sentences, 0)

    def test_fenced_code_block_is_excluded(self):
        text = "前の文。\n\n```python\n" + "コード内の日本語。" * 30 + "\n```\n\n後の文。\n"
        metrics = analyze(text).metrics
        self.assertEqual(metrics.paragraphs, 2)
        self.assertEqual(metrics.chars, len("前の文。後の文。"))

    def test_tilde_fence_and_longer_closing_fence(self):
        text = "前。\n\n~~~~\n中の日本語。\n~~~~~\n\n後。\n"
        self.assertEqual(analyze(text).metrics.paragraphs, 2)

    def test_yaml_frontmatter_is_excluded_and_line_numbers_are_kept(self):
        text = "---\ntitle: 数えない\n---\n\n" + ("あ" * 49 + "。") * 4 + "\n"
        result = analyze(text)
        self.assertEqual(result.metrics.paragraphs, 1)
        self.assertEqual(result.long_paragraphs[0].line, 5)

    def test_unclosed_frontmatter_marker_is_treated_as_text(self):
        self.assertEqual(analyze("---\n本文である。\n").metrics.paragraphs, 1)

    def test_headings_tables_and_rules_are_not_paragraphs(self):
        text = "# 見出し\n\n| 列 | 列 |\n|---|---|\n| あ | い |\n\n---\n\n本文。\n"
        self.assertEqual(analyze(text).metrics.paragraphs, 1)

    def test_list_items_are_separate_paragraphs(self):
        metrics = analyze("- 一つ目。\n- 二つ目。\n1. 三つ目。\n").metrics
        self.assertEqual(metrics.paragraphs, 3)

    def test_html_comment_is_excluded(self):
        text = "<!--\n隠れた日本語。\n-->\n\n本文。\n"
        self.assertEqual(analyze(text).metrics.chars, len("本文。"))

    def test_fixture_with_many_markdown_features(self):
        text = (FIXTURES / "markdown_features.md").read_text(encoding="utf-8")
        blocks = measure.extract_blocks(text)
        joined = "".join(b.text for b in blocks)
        self.assertIn("リンクの表示テキスト", joined)
        self.assertIn("箇条書きの項目", joined)
        self.assertIn("引用の中身は数える", joined)
        self.assertNotIn("フロントマター", joined)
        self.assertNotIn("コードブロック", joined)
        self.assertNotIn("example.com", joined)
        self.assertEqual([b.first_line for b in blocks], [8, 14, 15, 21, 25])

    def test_plain_format_does_not_interpret_markdown(self):
        text = "# 見出しのように見える行\n"
        self.assertEqual(analyze(text, markdown=True).metrics.paragraphs, 0)
        self.assertEqual(analyze(text, markdown=False).metrics.paragraphs, 1)

    def test_crlf_and_bom_are_handled(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "crlf.md"
            path.write_bytes("﻿一つ目。\r\n\r\n二つ目。\r\n".encode("utf-8"))
            code, out, _ = run_script(SCRIPT, "--json", str(path))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["files"][0]["paragraphs"], 2)


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)
        long_paragraph = ("い" * 49 + "。") * 4      # 200字。文は50字ずつ
        long_sentence = "あ" * 89 + "。"            # 90字の1文
        longer_sentence = "う" * 94 + "。"          # 95字の1文
        (self.tmp / "a.md").write_text(
            f"# 題\n\n短い文である。\n\n{long_paragraph}\n\n{long_sentence}\n\n{longer_sentence}\n",
            encoding="utf-8")
        (self.tmp / "b.md").write_text("別のファイルの文である。\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_single_file_summary(self):
        code, out, _ = run_script(SCRIPT, str(self.tmp / "a.md"))
        self.assertEqual(code, 0)
        self.assertIn("chars:", out)
        self.assertIn("paragraphs: 4", out)
        self.assertIn("sentences: 7", out)

    def test_locate_reports_file_line_length_and_preview(self):
        code, out, _ = run_script(SCRIPT, "--locate", str(self.tmp / "a.md"))
        self.assertEqual(code, 0)
        self.assertIn(f"{self.tmp / 'a.md'}:5  paragraph  200  ", out)
        self.assertIn(f"{self.tmp / 'a.md'}:7  sentence  90  ", out)
        self.assertIn(f"{self.tmp / 'a.md'}:9  sentence  95  ", out)
        self.assertIn("long paragraphs (>=200 chars): 1", out)
        self.assertIn("long sentences (>=80 chars): 2", out)

    def test_locate_limits_the_output(self):
        code, out, _ = run_script(SCRIPT, "--locate", "--max-locate", "1", str(self.tmp / "a.md"))
        self.assertEqual(code, 0)
        self.assertIn("1 more not shown", out)
        self.assertIn(":9  sentence  95", out)  # 上限を超えた場合は長い順に残す
        self.assertNotIn(":7  sentence  90", out)

    def test_json_output(self):
        code, out, _ = run_script(SCRIPT, "--json", str(self.tmp / "a.md"))
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["thresholds"], {"paragraph": 200, "sentence": 80})
        self.assertEqual(data["files"][0]["long_paragraphs"], 1)
        self.assertEqual(data["files"][0]["long_sentences"], 2)
        self.assertNotIn("long_paragraph_candidates", data["files"][0])

    def test_json_with_locate_includes_candidates(self):
        code, out, _ = run_script(SCRIPT, "--json", "--locate", str(self.tmp / "a.md"))
        entry = json.loads(out)["files"][0]
        self.assertEqual(code, 0)
        self.assertEqual([c["line"] for c in entry["long_paragraph_candidates"]], [5])
        self.assertEqual([c["length"] for c in entry["long_sentence_candidates"]], [90, 95])

    def test_multiple_files_show_a_table_with_totals(self):
        code, out, _ = run_script(SCRIPT, str(self.tmp / "a.md"), str(self.tmp / "b.md"))
        self.assertEqual(code, 0)
        self.assertIn("TOTAL", out)
        self.assertEqual(out.count(".md"), 2)

    def test_multiple_files_json_totals_are_sums(self):
        code, out, _ = run_script(SCRIPT, "--json", str(self.tmp / "a.md"), str(self.tmp / "b.md"))
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["total"]["chars"], sum(f["chars"] for f in data["files"]))
        self.assertEqual(data["total"]["paragraphs"], sum(f["paragraphs"] for f in data["files"]))

    def test_wildcard_is_expanded_by_the_script(self):
        code, out, _ = run_script(SCRIPT, "--json", str(self.tmp / "*.md"))
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)["files"]), 2)

    def test_directory_is_searched_recursively(self):
        nested = self.tmp / "sub"
        nested.mkdir()
        (nested / "c.md").write_text("入れ子のファイル。\n", encoding="utf-8")
        code, out, _ = run_script(SCRIPT, "--json", str(self.tmp))
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out)["files"]), 3)

    def test_missing_file_is_an_error(self):
        code, out, err = run_script(SCRIPT, str(self.tmp / "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_missing_file_does_not_hide_other_results(self):
        code, out, err = run_script(SCRIPT, str(self.tmp / "b.md"), str(self.tmp / "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("paragraphs: 1", out)

    def test_stdin(self):
        code, out, _ = run_script(SCRIPT, "--json", "-", stdin="標準入力の文章である。\n")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["files"][0]["file"], "<stdin>")

    def test_invalid_utf8_is_reported_without_a_traceback(self):
        bad = self.tmp / "bad.md"
        bad.write_bytes(b"\xff\xfe\x00")
        code, _, err = run_script(SCRIPT, str(bad))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)
        self.assertNotIn("Traceback", err)

    def test_input_files_are_not_modified(self):
        path = self.tmp / "a.md"
        before = path.read_bytes()
        run_script(SCRIPT, "--locate", str(path))
        self.assertEqual(path.read_bytes(), before)


class ExtrasTest(unittest.TestCase):
    def pointers(self, text: str):
        result = analyze(text, extras=True)
        return {kind: [(c.line, c.length) for c in items] for kind, items in result.extras.items()}

    def test_kanji_run_threshold_is_seven(self):
        self.assertEqual(self.pointers("初回課金転換率を見る。")["kanji-run"], [(1, 7)])
        self.assertEqual(self.pointers("課金転換率を見る。")["kanji-run"], [])  # 6字

    def test_kanji_run_stops_at_kana_and_punctuation(self):
        self.assertEqual(self.pointers("初回課金、転換率の改善を見る。")["kanji-run"], [])

    def test_kanji_run_also_catches_proper_nouns_which_is_a_known_limit(self):
        self.assertEqual(self.pointers("東京地方裁判所で争う。")["kanji-run"], [(1, 7)])

    def test_no_chain_needs_three_no_between_nouns(self):
        self.assertEqual(len(self.pointers("運用コストの削減の実現の効果を測る。")["no-chain"]), 1)
        self.assertEqual(self.pointers("運用コストの削減の実現を測る。")["no-chain"], [])  # 2連

    def test_no_chain_is_not_triggered_by_hiragana_words(self):
        self.assertEqual(self.pointers("私のこのものの話をする。")["no-chain"], [])

    def test_no_chain_accepts_katakana_nouns(self):
        self.assertEqual(len(self.pointers("サーバーのログのエラーの原因を調べる。")["no-chain"]), 1)

    def test_no_chain_accepts_alphanumeric_nouns(self):
        for text in ("APIの仕様の変更の影響を調べる。", "v2の設定の値の上限を変える。", "ＡＰＩの仕様の変更の影響を調べる。"):
            with self.subTest(text=text):
                self.assertEqual(len(self.pointers(text)["no-chain"]), 1)

    def test_double_negative_forms(self):
        for text in ("できないわけではない。", "負荷が増えないとは言えません。", "使えなくはない。",
                     "失敗しないとも限らない。", "失敗率が下がらないとは限らない。", "下がらないとは限りません。",
                     "知らないでもない。", "行かないことはありません。", "使えないわけではなかった。",
                     "使えなくはなかった。", "起きないとは言い切れない。", "気持ちは分からないではない。",
                     "障害の可能性は否定できない。", "影響があることは否めない。", "移行は不可能ではない。",
                     "追加の設定は不要ではない。", "改善の余地はなきにしもあらずだ。"):
            with self.subTest(text=text):
                self.assertEqual(len(self.pointers(text)["double-negative"]), 1)

    def test_conditional_and_obligation_forms_are_not_double_negatives(self):
        for text in ("設定しないと動かない。", "確認しなければならない。", "断らないわけにはいかない。",
                     "行かざるを得ない。", "彼は来ないし、私も行かない。", "成功するとは限らない。",
                     "確認しないではいられない。", "無料ではない。"):
            with self.subTest(text=text):
                self.assertEqual(self.pointers(text)["double-negative"], [])

    def test_pointers_report_the_line_of_the_match(self):
        result = self.pointers("一行目である。\n初回課金転換率を見る。\n")
        self.assertEqual(result["kanji-run"], [(2, 7)])

    def test_pointers_are_not_collected_inside_code_blocks(self):
        text = "```\n初回課金転換率\n```\n\n本文である。\n"
        self.assertEqual(self.pointers(text)["kanji-run"], [])

    def test_extras_are_off_by_default(self):
        self.assertEqual(analyze("初回課金転換率を見る。").extras["kanji-run"], [])

    def test_snippet_marks_truncation(self):
        snippet = measure.make_snippet("あ" * 30 + "初回課金転換率" + "い" * 30, 30, 37)
        self.assertTrue(snippet.startswith("…") and snippet.endswith("…"))
        self.assertIn("初回課金転換率", snippet)


class UnrenderedBoldTest(unittest.TestCase):
    """太字が表示されるかどうかは、GitHub の Markdown API と pandoc(gfm) で確かめた。"""

    def lines(self, text: str, **kwargs):
        return [c.line for c in analyze(text, extras=True, **kwargs).extras["unrendered-bold"]]

    def test_symbol_inside_and_letter_outside_is_reported(self):
        for text in ("次に**「文書の立場」**を決めます。", "これは**必須です。**詳しくは下に書きます。",
                     "**`config`**を設定する。", "**注意:**この操作は戻せない。"):
            with self.subTest(text=text):
                self.assertEqual(self.lines(text), [1])

    def test_bold_that_renders_is_not_reported(self):
        for text in ("次に「**文書の立場**」を決めます。", "これは**必須です**。詳しくは下に書きます。",
                     "立場は **「勧め」か「決まり」** で決めます。", "（**重要**）を見る。"):
            with self.subTest(text=text):
                self.assertEqual(self.lines(text), [])

    def test_symbols_count_as_punctuation_for_commonmark_0_31(self):
        # GitHub では表示されるが、CommonMark 0.31 に従う実装では表示されない。
        self.assertEqual(self.lines("これは**★重要**です。"), [1])

    def test_bold_across_lines_reports_the_line_of_the_opening_delimiter(self):
        self.assertEqual(self.lines("一行目である。\nこれは**必須\nです。**詳しくは下に。\n"), [2])

    def test_delimiters_do_not_pair_across_list_items(self):
        self.assertEqual(self.lines("- 項目の**「一つ目\n- 二つ目」**を見る。\n"), [])

    def test_headings_and_table_rows_are_checked(self):
        self.assertEqual(self.lines("## 次に**「立場」**を決める\n\n| **「列」**の値 |\n"), [1, 3])

    def test_code_and_escaped_asterisks_are_not_reported(self):
        text = "`**「a」**を` の書き方。\n\n\\*\\*「b」\\*\\*を見る。\n\n```\n**「c」**を\n```\n"
        self.assertEqual(self.lines(text), [])

    def test_plain_text_is_not_checked(self):
        self.assertEqual(self.lines("次に**「文書の立場」**を決めます。", markdown=False), [])

    def test_bold_is_not_checked_without_extras(self):
        self.assertEqual(analyze("次に**「文書の立場」**を決めます。").extras["unrendered-bold"], [])


class ExtrasCommandLineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.path = Path(self._tmp.name) / "a.md"
        self.path.write_text("初回課金転換率を見る。\n\nできないわけではない。\n\n次に**「立場」**を決める。\n",
                             encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_extras_are_listed_as_information_only(self):
        code, out, _ = run_script(SCRIPT, "--extras", str(self.path))
        self.assertEqual(code, 0)
        self.assertIn("pointers (info only, not verdicts)", out)
        self.assertIn("kanji-run (>=7 kanji in a row): 1", out)
        self.assertIn(f"{self.path}:1  kanji-run  7  ", out)
        self.assertIn("double-negative: 1", out)
        self.assertIn(f"{self.path}:3  double-negative  ", out)
        self.assertIn("unrendered-bold (** shown as-is): 1", out)
        self.assertIn(f"{self.path}:5  unrendered-bold  ", out)

    def test_default_output_has_no_pointers(self):
        code, out, _ = run_script(SCRIPT, "--locate", str(self.path))
        self.assertEqual(code, 0)
        self.assertNotIn("pointers", out)

    def test_json_includes_pointers_only_when_requested(self):
        _, plain, _ = run_script(SCRIPT, "--json", str(self.path))
        self.assertNotIn("pointers", json.loads(plain)["files"][0])
        code, out, _ = run_script(SCRIPT, "--json", "--extras", str(self.path))
        entry = json.loads(out)["files"][0]
        self.assertEqual(code, 0)
        self.assertEqual(entry["pointers"]["kanji-run"][0]["line"], 1)
        self.assertEqual(entry["pointers"]["no-chain"], [])
        self.assertEqual(entry["pointers"]["unrendered-bold"][0]["line"], 5)

    def test_extras_can_be_combined_with_locate(self):
        code, out, _ = run_script(SCRIPT, "--locate", "--extras", str(self.path))
        self.assertEqual(code, 0)
        self.assertIn("long paragraphs", out)
        self.assertIn("pointers", out)


if __name__ == "__main__":
    unittest.main()
