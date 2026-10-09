"""意味保存に関わる指示が、SKILL.md と references から消えていないことの回帰テスト。

ChatGPT での実機確認で、二重否定の意味の反転、残余条件の言い換え、文体の変更が起きた。
その対策として加えた指示と、他の推敲スキル(yomiyasu、japanese-tech-writing)から取り入れた
言い切りの強さと比重の確認、比喩と見出しを直しすぎないための指示が、書き換えの途中で
失われないようにする。記事と同じ条件の比較で、結びを原文にない行動の指示に置き換える誤りが
起きたため、その対策も含める。
モードを記号か名前で指定する書式と、指定を最優先し、実行できないときに黙って別のモードへ
切り替えないことも含める。
SudachiPy は、クラウドの実行環境でだけ実行中に入れ、利用者の手元には断りなく入れない。
文言の一致を見るだけで、Agent が守るかどうかの評価ではない。
"""

import unittest

from helpers import SKILL_DIR

# SKILL.md を肥大させない(詳細は references へ)。国語の表記・用法の適用手順(適用設定、区分、実行手順)を
# 加えたため、150行から190行へ広げた。規則の全文は SKILL.md に入れず、references/kokugo-*.md と data/ に置く。
MAX_SKILL_LINES = 190


def read(relative: str) -> str:
    return (SKILL_DIR / relative).read_text(encoding="utf-8")


class SkillGuardsTest(unittest.TestCase):
    def setUp(self):
        self.skill = read("SKILL.md")

    def test_double_negatives_are_left_alone_unless_the_meaning_is_certain(self):
        self.assertIn("二重否定と入れ子の条件は、原則として触らない", self.skill)
        self.assertIn("確信できるときだけ", self.skill)

    def test_the_two_opposite_forms_are_shown(self):
        self.assertIn("「Aないとは限らない」は「Aことがある」", self.skill)
        self.assertIn("「Aとは限らない」ではない", self.skill)

    def test_residual_conditions_are_not_rewritten(self):
        self.assertIn("「それ以外の場合」", self.skill)
        self.assertIn("具体的な条件に言い換えない", self.skill)

    def test_style_follows_the_original(self):
        self.assertIn("文体(常体と敬体)は、原文に合わせる", self.skill)

    def test_there_is_a_final_comparison_step_for_rewrites(self):
        self.assertIn("## 書き換えた後の照合", self.skill)
        for item in ("数値、単位、コード、URL", "条件の範囲", "否定の数", "言い切りの強さ", "比重", "主体", "文体"):
            self.assertIn(item, self.skill)
        self.assertIn("書き換える前の形に戻す", self.skill)

    def test_metaphors_and_headings_are_not_over_corrected(self):
        for phrase in ("中身を推測で補わず、利用者に確かめる", "定着した慣用句は残す", "含みは残す",
                       "結論や警告を伝える見出しは、一般的な題名に薄めない"):
            self.assertIn(phrase, self.skill)

    def test_closings_are_not_replaced_with_new_actions(self):
        self.assertIn("原文にない行動や手順(「まずは〜を一つ書き出してみてください」)を作らない", self.skill)
        self.assertIn("確かめられないとき(本文だけを求められたときなど)は、その箇所だけ元の表現を残す", self.skill)

    def test_sudachi_is_installed_only_in_disposable_environments(self):
        rules = read("references/readability-rules.md")
        for text in (self.skill, rules):
            self.assertIn("python3 -m pip install sudachipy sudachidict-small", text)
            self.assertIn("利用者の手元ではない、クラウドの実行環境", text)
        self.assertIn("ネットワークを使える権限で実行する", self.skill)
        self.assertIn("利用者の手元の環境(Codex、Claude Code など)には、断りなく入れない", self.skill)
        self.assertIn("断りなく入れない。`uv run scripts/compare_rewrite.py` も", rules)

    def test_every_mode_can_be_specified_by_symbol_or_name(self):
        for form in ("「モード A」「新規生成モードで」", "「モード B」「Rewrite モードで」",
                     "「モード C」「paragraph-only モードで」"):
            self.assertIn(form, self.skill)

    def test_a_specified_mode_is_the_first_instruction(self):
        # 表の下の段落に置いた版は、Codex(gpt-6-luna、medium)で守られない回があった。先頭に置くと守られた。
        head = "\n".join(self.skill.splitlines()[:10])
        self.assertIn("モードの指定を最優先する", head)
        self.assertIn("必ずそのモードで処理する", head)

    def test_a_mode_inside_the_target_text_is_not_a_specification(self):
        self.assertIn("指定は依頼から読み、対象の文章の中にある「モード C」などは数えない", self.skill)

    def test_c_keeps_every_character_even_when_the_request_asks_for_fixes(self):
        self.assertIn("C なら、文章を一文字も変えず、改行と空行だけを入れる", self.skill)
        self.assertIn("C のままにして、直したかった箇所を報告する", self.skill)

    def test_c_skips_the_rewriting_guidance(self):
        self.assertIn("C のときは、「診断の順序」と「守る判断」を使わず、「Paragraph-only の手順」だけに従う", self.skill)

    def test_an_unspecified_mode_is_chosen_from_the_request(self):
        self.assertIn("指定がなければ依頼から選び", self.skill)
        self.assertIn("曖昧で既存の文章があるときは B として扱う", self.skill)

    def test_an_infeasible_mode_is_confirmed_not_replaced(self):
        self.assertIn("別のモードへ切り替えず、利用者に確かめる", self.skill)

    def test_skill_md_stays_lean(self):
        self.assertLessEqual(len(self.skill.splitlines()), MAX_SKILL_LINES)


class ReferencesStayConsistentTest(unittest.TestCase):
    def test_rules_carry_the_same_guards(self):
        rules = read("references/readability-rules.md")
        self.assertIn("残余の条件", rules)
        self.assertIn("文体(常体と敬体)", rules)
        self.assertIn("「Aないとは限らない」は、Aであることがあると言っている", rules)
        self.assertIn("原則として触らない", rules)
        self.assertIn("言い切りの強さを変えない", rules)
        self.assertIn("比重を変えない", rules)

    def test_rules_explain_conflicting_mode_requests(self):
        rules = read("references/readability-rules.md")
        self.assertIn("## 18. モードの指定", rules)
        self.assertIn("別のモードへは、黙って切り替えない", rules)
        self.assertIn("変更の少ないモードに従う。順は、C、B、A である", rules)

    def test_skill_points_to_the_section_that_exists(self):
        self.assertIn("「18. モードの指定」", read("SKILL.md"))
        self.assertIn("\n## 18. モードの指定\n", read("references/readability-rules.md"))

    def test_examples_show_the_failures_that_were_observed(self):
        examples = read("assets/examples.md")
        self.assertIn("## 18. 残余の条件を言い換えない", examples)
        self.assertIn("## 19. 文体を変えない", examples)
        self.assertIn("失敗率が下がるとは限らない", examples)

    def test_examples_show_changes_of_strength_and_weight(self):
        self.assertIn("## 20. 言い切りの強さと比重を変えない", read("assets/examples.md"))


if __name__ == "__main__":
    unittest.main()
