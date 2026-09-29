"""SKILL.md の description が、要件で求められた発火条件を満たし続けることの回帰テスト。

description は、エージェントが Skill を選ぶ唯一の手がかりである。語を削ったり、文字数の上限を
超えたりしていないかを、機械的に確かめる。実際に発火するかどうかの評価ではない。
"""

import unittest

from helpers import SKILL_DIR, TOOLS_DIR, load_module

validate = load_module("validate_skill_for_description", TOOLS_DIR / "validate_skill.py")

# Claude のヘルプ記事が claude.ai の登録画面について挙げる上限。仕様の1024字より厳しい。
LIMIT = 200

# 自動発火させたい依頼。どれか一つを含めばよい語は、タプルで並べる。
MUST_MENTION = [
    ("書く",),
    ("校正",),
    ("推敲",),
    ("読みやすく",),
    ("冗長",),
    ("長すぎる",),
    ("直訳調",),
    ("AIっぽい", "AI"),
    ("技術文書",),
    ("README",),
    ("レポート",),
    ("Issue",),
    ("Pull Request",),
    ("設計書",),
    ("提案書",),
    ("説明資料",),
    ("Markdown",),
    ("generated",),
    ("Japanese readability",),
    ("editing",),
]

# 原則として自動発火させたくない入力。
MUST_EXCLUDE = [("コード",), ("JSON",), ("ログ",), ("数式",), ("短い会話",)]


def description() -> str:
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    fields, _, problems = validate.parse_frontmatter(text)
    assert not problems, problems
    return fields["description"]


class DescriptionTest(unittest.TestCase):
    def setUp(self):
        self.text = description()

    def test_fits_the_strictest_documented_limit(self):
        self.assertLessEqual(len(self.text), LIMIT)

    def test_mentions_every_requested_trigger(self):
        missing = [alternatives[0] for alternatives in MUST_MENTION
                   if not any(word in self.text for word in alternatives)]
        self.assertEqual(missing, [], f"description is missing trigger words: {missing}")

    def test_states_what_it_is_not_for(self):
        missing = [alternatives[0] for alternatives in MUST_EXCLUDE
                   if not any(word in self.text for word in alternatives)]
        self.assertEqual(missing, [], f"description does not exclude: {missing}")

    def test_exclusions_are_phrased_as_exclusions(self):
        self.assertIn("対象外", self.text)

    def test_says_what_is_preserved(self):
        for word in ("意味", "数値", "コード"):
            self.assertIn(word, self.text)

    def test_contains_no_yaml_hazards(self):
        self.assertNotIn(": ", self.text)
        self.assertNotIn(" #", self.text)
        self.assertFalse(any(ch in self.text for ch in "<>"))


if __name__ == "__main__":
    unittest.main()
