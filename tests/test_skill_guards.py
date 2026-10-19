"""SKILL.md の分量と、参照先の節が残っていることの回帰テスト。文言の一致は見ない(推敲の質は evals で測る)。"""

import unittest

from helpers import SKILL_DIR

# SKILL.md を肥大させない(詳細は references へ)。国語の表記・用法の適用手順(適用設定、区分、実行手順)を
# 加えたため190行、D の入口を追加したため205行を上限とする。詳細は references と assets に分離する。
MAX_SKILL_LINES = 205


def read(relative: str) -> str:
    return (SKILL_DIR / relative).read_text(encoding="utf-8")


class SkillGuardsTest(unittest.TestCase):
    def setUp(self):
        self.skill = read("SKILL.md")

    def test_skill_md_stays_lean(self):
        self.assertLessEqual(len(self.skill.splitlines()), MAX_SKILL_LINES)


class ReferencesStayConsistentTest(unittest.TestCase):
    def test_skill_points_to_the_section_that_exists(self):
        self.assertIn("「18. モードの指定」", read("SKILL.md"))
        self.assertIn("\n## 18. モードの指定\n", read("references/readability-rules.md"))


if __name__ == "__main__":
    unittest.main()
