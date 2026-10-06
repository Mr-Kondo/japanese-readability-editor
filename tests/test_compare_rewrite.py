"""scripts/compare_rewrite.py のテスト。

SudachiPy を使う経路のテストは、SudachiPy と辞書が入っている環境だけで実行する。
"""

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

from helpers import SCRIPTS_DIR, copy_real_skill, dedent, load_module, run_script, temporary_directory

compare = load_module("compare_rewrite", SCRIPTS_DIR / "compare_rewrite.py")
SCRIPT = SCRIPTS_DIR / "compare_rewrite.py"
REGEX = compare.RegexAnalyzer()
try:
    SUDACHI = compare.SudachiAnalyzer()
except ImportError:
    SUDACHI = None


def run(before: str, after: str, analyzer=REGEX) -> dict:
    return compare.compare_documents(compare.parse_document(dedent(before), "before.md", True, analyzer),
                                     compare.parse_document(dedent(after), "after.md", True, analyzer),
                                     analyzer.name)


def texts(items) -> list:
    return [item.text for item in items]


def changed_markers(result: dict) -> dict:
    return {kind: (data["before"], data["after"]) for kind, data in result["markers"].items()
            if data["before"] != data["after"]}


class ItemsTest(unittest.TestCase):
    def test_identical_text_has_no_pointers(self):
        text = """
            # 設定

            タイムアウトは30秒である。詳細は https://example.com/docs を見る。

            `config.yaml` の GitHub Actions を使う。

            ```
            run: make test
            ```
        """
        result = run(text, text)
        for kind in compare.ITEM_KINDS:
            self.assertEqual(result[kind], {"missing": [], "added": []}, kind)
        self.assertEqual(result["unmatched"], {"after": [], "before": []})
        self.assertEqual(changed_markers(result), {})
        self.assertFalse(result["style"]["changed"])

    def test_changed_number_is_reported_on_both_sides(self):
        result = run("タイムアウトは30秒である。\n", "タイムアウトは3秒である。\n")
        self.assertEqual(texts(result["numbers"]["missing"]), ["30秒"])
        self.assertEqual(texts(result["numbers"]["added"]), ["3秒"])

    def test_full_width_digits_match_half_width(self):
        result = run("タイムアウトは３０秒である。\n", "タイムアウトは30秒である。\n")
        self.assertEqual(result["numbers"], {"missing": [], "added": []})

    def test_list_markers_are_not_numbers(self):
        result = run("1. 設定を開く。\n2. 保存する。\n", "- 設定を開く。\n- 保存する。\n")
        self.assertEqual(result["numbers"], {"missing": [], "added": []})

    def test_urls_and_code_are_compared(self):
        before = """
            手順は https://example.com/a にある。`config.yaml` を編集する。

            ```
            run: make test
            ```
        """
        after = """
            手順は別のページにある。`config.yml` を編集する。

            ```
            run: make check
            ```
        """
        result = run(before, after)
        self.assertEqual(texts(result["urls"]["missing"]), ["https://example.com/a"])
        self.assertEqual(texts(result["code"]["missing"]), ["`config.yaml`", "run: make test"])
        self.assertEqual(texts(result["code"]["added"]), ["`config.yml`", "run: make check"])

    def test_link_targets_are_compared(self):
        result = run("詳細は[手順](https://example.com/a)と[規則](references/rules.md)を見る。\n", "詳細は手順と規則を見る。\n")
        self.assertEqual(texts(result["urls"]["missing"]), ["https://example.com/a"])
        self.assertEqual(texts(result["terms"]["missing"]), ["references/rules.md"])

    def test_renamed_terms_are_reported(self):
        result = run("GitHub Actions で実行する。\n", "ギットハブのアクションで実行する。\n")
        self.assertEqual(texts(result["terms"]["missing"]), ["GitHub", "Actions"])
        self.assertEqual(texts(result["terms"]["added"]), ["ギットハブ", "アクション"])

    def test_repeated_items_are_counted_and_the_later_one_is_reported(self):
        result = run("APIを呼ぶ。\nAPIを閉じる。\n", "APIを呼んで閉じる。\n")
        self.assertEqual([(i.line, i.text) for i in result["terms"]["missing"]], [(2, "API")])


class UnmatchedTest(unittest.TestCase):
    def test_a_closing_replaced_with_a_new_action_has_no_source(self):
        before = "設定ファイルは、すべてこのリポジトリにまとめてあります。今日から、チームの開発環境を一緒に育てていきましょう。\n"
        after = "設定ファイルは、すべてこのリポジトリにまとめてあります。まずは、自分の端末に設定ファイルを一つ取り込んでみてください。\n"
        result = run(before, after)
        self.assertEqual(texts(result["unmatched"]["after"]), ["まずは、自分の端末に設定ファイルを一つ取り込んでみてください。"])
        self.assertEqual(texts(result["unmatched"]["before"]), ["今日から、チームの開発環境を一緒に育てていきましょう。"])

    def test_a_split_sentence_is_not_reported(self):
        result = run("入力を検証し、問題がなければデータベースに保存し、問題があればエラーを返す。\n",
                     "入力を検証する。問題がなければデータベースに保存する。問題があればエラーを返す。\n")
        self.assertEqual(result["unmatched"], {"after": [], "before": []})

    def test_reordered_clauses_are_matched(self):
        result = run("エラーがあれば、処理をすぐに止める。\n", "処理をすぐに止めるのは、エラーがあるときだ。\n")
        self.assertEqual(result["unmatched"], {"after": [], "before": []})


class MarkersTest(unittest.TestCase):
    def test_a_folded_double_negative_is_reported_at_the_original_line(self):
        result = run("この設定を外すと、負荷が増えないとは言えない。\n", "この設定を外すと、負荷が増える。\n")
        self.assertEqual(changed_markers(result), {"negation": (2, 0)})
        self.assertEqual([i.line for i in result["markers"]["negation"]["removed"]], [1])

    def test_dropped_conjecture_is_reported(self):
        result = run("キャッシュを無効にすると、応答が遅くなる可能性がある。\n", "キャッシュを無効にすると、応答が遅くなる。\n")
        self.assertEqual(changed_markers(result), {"conjecture": (1, 0)})

    def test_added_ability_is_reported_at_the_rewritten_line(self):
        result = run("このオプションで、ログの出力先を指定する。\n", "このオプションで、ログの出力先を指定できる。\n")
        self.assertEqual(changed_markers(result), {"ability": (0, 1)})
        self.assertEqual([i.line for i in result["markers"]["ability"]["added"]], [1])

    def test_dropped_formal_ability_is_reported(self):
        result = run("運用担当者は、ログからエラーの内容を確認することが可能である。\n",
                     "運用担当者は、ログからエラーの内容を確認する。\n")
        self.assertEqual(changed_markers(result), {"ability": (1, 0)})

    def test_ability_counts_each_form_but_not_kanousei(self):
        for text, expected in (("確認が可能でした。", 1), ("確認が可能であり、記録も残る。", 1), ("確認が可能。", 1),
                               ("確認できれば十分だ。", 1), ("確認できず、終了した。", 1), ("失敗する可能性がある。", 0)):
            with self.subTest(text=text):
                self.assertEqual(compare.count_markers(text, REGEX)["ability"], expected)

    def test_a_rewritten_residual_condition_is_reported(self):
        result = run("削除に失敗したファイルがある場合は、終了コード2を返す。それ以外の場合は、0を返す。\n",
                     "削除に失敗したファイルがある場合は、終了コード2を返す。すべて削除できた場合は、0を返す。\n")
        self.assertEqual(changed_markers(result)["residual"], (1, 0))

    def test_an_invitation_turned_into_a_request_is_reported(self):
        result = run("設定を見直す作業を、今日から始めましょう。\n", "設定を見直す作業を、今日から始めてください。\n")
        self.assertEqual(changed_markers(result), {"request": (0, 1), "invitation": (1, 0)})

    def test_regex_negation_skips_words_that_only_look_negative(self):
        for text in ("少ない手順で済む。", "危ない操作は避ける。", "まず、設定を確認する。", "必ず、保存してから閉じる。"):
            with self.subTest(text=text):
                self.assertEqual(REGEX.negations(text), 0)


class StyleTest(unittest.TestCase):
    def test_a_change_from_polite_to_plain_is_reported(self):
        self.assertTrue(run("設定を開きます。値を確認します。\n", "設定を開く。値を確認する。\n")["style"]["changed"])

    def test_the_same_style_is_not_reported(self):
        self.assertFalse(run("設定を開きます。\n", "設定画面を開きます。\n")["style"]["changed"])


@unittest.skipUnless(SUDACHI, "SudachiPy と辞書が入っていない")
class SudachiTest(unittest.TestCase):
    def test_negation_is_counted_by_part_of_speech(self):
        for text, expected in (("エラーがなくなりました。", 0), ("情けない結果だった。", 0), ("迷わず選べる。", 1),
                               ("ログを残さず削除する。", 1), ("知らぬ間に変わっていた。", 1), ("せざるを得ない。", 2)):
            with self.subTest(text=text):
                self.assertEqual(SUDACHI.negations(text), expected)

    def test_katakana_spelling_variants_are_the_same_term(self):
        before, after = "サーバに接続する。\n", "サーバーに接続する。\n"
        self.assertEqual(run(before, after, SUDACHI)["terms"], {"missing": [], "added": []})
        self.assertEqual(texts(run(before, after, REGEX)["terms"]["missing"]), ["サーバ"])

    def test_ascii_terms_are_not_replaced_by_their_katakana_reading(self):
        self.assertEqual(SUDACHI.term_key("Skill"), "Skill")
        result = run("Skill を使う。\n", "スキルを使う。\n", SUDACHI)
        self.assertEqual(texts(result["terms"]["missing"]), ["Skill"])

    def test_auto_prefers_sudachi(self):
        self.assertTrue(compare.load_analyzer("auto").name.startswith("sudachi"))


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)
        self.before = self.tmp / "before.md"
        self.after = self.tmp / "after.md"
        self.before.write_text("この設定を外すと、負荷が増えないとは言えない。タイムアウトは30秒である。\n", encoding="utf-8")
        self.after.write_text("この設定を外すと、負荷が増える。タイムアウトは3秒である。\n", encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def test_text_output_lists_pointers(self):
        code, out, _ = run_script(SCRIPT, "--tokenizer", "regex", str(self.before), str(self.after))
        self.assertEqual(code, 0)
        self.assertIn("tokenizer: regex", out)
        self.assertIn("pointers (info only, not verdicts):", out)
        self.assertIn(f"{self.before}:1  missing  30秒", out)
        self.assertIn("negation: 2 -> 0", out)

    def test_json_output(self):
        code, out, _ = run_script(SCRIPT, "--json", "--tokenizer", "regex", str(self.before), str(self.after))
        data = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(data["tokenizer"], "regex")
        self.assertEqual(data["numbers"]["missing"], [{"line": 1, "text": "30秒"}])
        self.assertEqual(set(data["markers"]), set(compare.MARKER_KINDS))

    def test_unreadable_file_is_an_error(self):
        code, _, err = run_script(SCRIPT, str(self.before), str(self.tmp / "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read", err)

    @unittest.skipIf(SUDACHI, "SudachiPy が入っている")
    def test_requesting_sudachi_without_it_explains_how_to_install(self):
        code, _, err = run_script(SCRIPT, "--tokenizer", "sudachi", str(self.before), str(self.after))
        self.assertEqual(code, 2)
        self.assertIn("pip install sudachipy sudachidict-core", err)

    def test_running_the_script_writes_no_files_into_the_skill(self):
        skill = copy_real_skill(self.tmp / "installed")
        env = {key: value for key, value in os.environ.items() if key != "PYTHONDONTWRITEBYTECODE"}
        env.update(PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
        completed = subprocess.run(
            [sys.executable, str(skill / "scripts" / "compare_rewrite.py"), "--tokenizer", "regex",
             str(self.before), str(self.after)],
            capture_output=True, text=True, encoding="utf-8", env=env, timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertFalse((skill / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
