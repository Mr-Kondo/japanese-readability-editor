"""compare_rewrite.best_match の高速化が、すべての窓を順に調べる素朴な実装と同じ答えを返すことを確かめる。

素朴な実装(高速化の前の実装)をここに残し、無作為な入力で突き合わせる。結果が同じでなければ、候補の漏れや余計な候補が出る。
"""
import random
import time
import unittest
from collections import Counter
from unittest import mock

from helpers import SCRIPTS_DIR, load_module

compare = load_module("compare_rewrite_match", SCRIPTS_DIR / "compare_rewrite.py")
REGEX = compare.RegexAnalyzer()


def naive_best_match(sentence, others, index=None):
    """高速化の前の best_match。すべての開始位置と窓の長さを調べる。"""
    if not sentence.units or not others:
        return None
    best = None
    for start in range(len(others)):
        window = frozenset()
        for end in range(start + 1, min(start + compare.MAX_WINDOW, len(others)) + 1):
            window = window | others[end - 1].units
            coverage = len(sentence.units & window) / len(sentence.units)
            if best is None or coverage > best.coverage + 1e-9:
                best = compare.Match(coverage, start, end)
    return best


def sentence(units, line=1):
    return compare.Sentence(line, "", frozenset(units), Counter(), True)


class BestMatchEqualsTheNaiveSearchTest(unittest.TestCase):
    def random_sentences(self, rng, count, vocabulary, longest):
        return [sentence(rng.sample(vocabulary, rng.randint(0, min(longest, len(vocabulary)))), i + 1) for i in range(count)]

    def assert_same(self, wanted, others, index=None):
        expected, actual = naive_best_match(wanted, others), compare.best_match(wanted, others, index)
        self.assertEqual(actual, expected, f"wanted={sorted(wanted.units)}")

    def test_random_small_inputs_including_ties_empty_sets_and_no_overlap(self):
        rng = random.Random(20261018)
        for trial in range(3000):
            vocabulary = [f"u{i}" for i in range(rng.choice((3, 6, 12, 40)))]
            others = self.random_sentences(rng, rng.randint(0, 9), vocabulary, 6)
            wanted = sentence(rng.sample(vocabulary, rng.randint(0, min(7, len(vocabulary)))))
            with self.subTest(trial=trial):
                self.assert_same(wanted, others)

    def test_random_larger_inputs_with_a_prebuilt_index(self):
        rng = random.Random(7)
        for trial in range(40):
            vocabulary = [f"u{i}" for i in range(rng.choice((15, 60, 300)))]
            others = self.random_sentences(rng, 150, vocabulary, 10)
            index = compare.unit_index(others)
            for _ in range(60):
                wanted = sentence(rng.sample(vocabulary, rng.randint(1, min(12, len(vocabulary)))))
                self.assert_same(wanted, others, index)

    def test_identical_repeated_sentences_pick_the_first_window(self):
        same = ["a", "b", "c", "d"]
        others = [sentence(same) for _ in range(30)]
        self.assertEqual(compare.best_match(sentence(same), others), compare.Match(1.0, 0, 1))
        self.assertEqual(naive_best_match(sentence(same), others), compare.Match(1.0, 0, 1))

    def test_a_split_sentence_matches_the_pair_of_sentences(self):
        others = [sentence(["x"]), sentence(["a", "b"]), sentence(["c", "d"]), sentence(["y"])]
        self.assertEqual(compare.best_match(sentence(["a", "b", "c", "d"]), others), compare.Match(1.0, 1, 3))

    def test_no_overlap_returns_the_first_window_with_zero_coverage(self):
        others = [sentence(["a"]), sentence(["b"])]
        self.assertEqual(compare.best_match(sentence(["z"]), others), compare.Match(0.0, 0, 1))

    def test_empty_inputs_return_none(self):
        self.assertIsNone(compare.best_match(sentence([]), [sentence(["a"])]))
        self.assertIsNone(compare.best_match(sentence(["a"]), []))

    def test_units_missing_from_the_other_side_lower_the_ceiling_but_the_answer_is_the_same(self):
        others = [sentence(["a", "b"]), sentence(["a", "b", "q"]), sentence(["a"])]
        wanted = sentence(["a", "b", "never-there"])
        self.assertEqual(compare.best_match(wanted, others), naive_best_match(wanted, others))


class WholeDocumentEqualsTheNaiveSearchTest(unittest.TestCase):
    WORDS = ["管理者", "承認", "サーバー", "ログ", "設定", "更新", "停止", "確認", "期限", "障害", "運用", "監査", "API", "キャッシュ"]
    PARTICLES = ["が", "を", "は", "に", "で", "と"]
    ENDINGS = ["します", "する", "しました", "できます", "です"]

    def make_sentence(self, rng):
        words = [rng.choice(self.WORDS) + rng.choice(self.PARTICLES) for _ in range(rng.randint(1, 4))]
        return "".join(words) + rng.choice(self.ENDINGS) + "。"

    def rewrite(self, rng, sentences):
        out = []
        for text in sentences:
            roll = rng.random()
            if roll < 0.15:
                continue  # 削除
            if roll < 0.30 and "。" in text and len(text) > 8:
                cut = len(text) // 2
                out.extend([text[:cut] + "。", text[cut:]])  # 分割
            elif roll < 0.45:
                out.append(text.replace("が", "は").replace("します", "する"))  # 言い換え
            elif roll < 0.55:
                out.append(self.make_sentence(rng))  # 新しい文
            else:
                out.append(text)
        if rng.random() < 0.3:
            rng.shuffle(out)  # 順序の入れ替え
        return out

    def test_the_json_result_is_identical_for_random_documents(self):
        rng = random.Random(1018)
        for trial in range(60):
            before_sentences = [self.make_sentence(rng) for _ in range(rng.randint(1, 60))]
            after_sentences = self.rewrite(rng, before_sentences)
            before = compare.parse_document("".join(before_sentences), "before.md", True, REGEX)
            after = compare.parse_document("".join(after_sentences), "after.md", True, REGEX)
            fast = compare.compare_documents(before, after, REGEX.name)
            with mock.patch.object(compare, "best_match", naive_best_match):
                slow = compare.compare_documents(before, after, REGEX.name)
            with self.subTest(trial=trial):
                self.assertEqual(fast, slow)


class LongDocumentTest(unittest.TestCase):
    def test_a_long_rewritten_document_finishes_quickly(self):
        # 2乗に比例する実装では、この大きさで数十秒かかった(合成文書。実測は docs/scripts.md)。時間の上限は緩くしてある。
        rng = random.Random(3)
        subjects, verbs, conditions = ["管理者", "運用担当", "開発チーム", "利用者", "監査部門"], ["承認", "確認", "更新", "停止", "記録"], \
            ["月末までに", "障害の発生時に", "週次の会議で", "リリースの前に", "申請があったときに"]
        paragraphs = ["".join(f"{rng.choice(conditions)}{rng.choice(subjects)}が{rng.choice(verbs)}します。" for _ in range(8))
                      for _ in range(800)]
        before = "\n\n".join(paragraphs)
        after = "\n\n".join(p.replace("が", "は").replace("します", "する") for p in paragraphs)
        started = time.monotonic()
        result = compare.compare_documents(compare.parse_document(before, "b.md", True, REGEX),
                                           compare.parse_document(after, "a.md", True, REGEX), REGEX.name)
        elapsed = time.monotonic() - started
        self.assertIn("markers", result)
        self.assertLess(elapsed, 30, f"{elapsed:.1f} 秒かかった")


if __name__ == "__main__":
    unittest.main()
