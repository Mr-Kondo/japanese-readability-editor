"""意味保存に関わる指示が、SKILL.md と references から消えていないことの回帰テスト。

ChatGPT での実機確認で、二重否定の意味の反転、残余条件の言い換え、文体の変更が起きた。
その対策として加えた指示と、他の推敲スキル(yomiyasu、japanese-tech-writing)から取り入れた
言い切りの強さと比重の確認、比喩と見出しを直しすぎないための指示が、書き換えの途中で
失われないようにする。
文言の一致を見るだけで、Agent が守るかどうかの評価ではない。
"""

import unittest

from helpers import SKILL_DIR

MAX_SKILL_LINES = 150  # SKILL.md を肥大させない(詳細は references へ)


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

    def test_examples_show_the_failures_that_were_observed(self):
        examples = read("assets/examples.md")
        self.assertIn("## 18. 残余の条件を言い換えない", examples)
        self.assertIn("## 19. 文体を変えない", examples)
        self.assertIn("失敗率が下がるとは限らない", examples)

    def test_examples_show_changes_of_strength_and_weight(self):
        self.assertIn("## 20. 言い切りの強さと比重を変えない", read("assets/examples.md"))


if __name__ == "__main__":
    unittest.main()
