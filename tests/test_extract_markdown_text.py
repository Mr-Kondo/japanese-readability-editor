"""Markdown ブロック抽出。入力はテスト内で組み立てる人工の最小 Markdown。"""
import tempfile
import unittest
from pathlib import Path

from helpers import TOOLS_DIR, load_module, run_script

extract = load_module("extract_markdown_text", TOOLS_DIR / "extract_markdown_text.py")
SAMPLE = """---
title: 見出し付き
---

# 題名
本文の一行目。
二行目。

- 項目1
- 項目2
  - 入れ子

```bash
echo 1

echo 2
```

| 列1 | 列2 |
|---|---|
| a | b |

> 引用

<!-- コメント -->

1. 手順
"""


class ExtractMarkdownTextTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name, "sample.md")
        self.path.write_text(SAMPLE, encoding="utf-8")

    def test_blocks_kinds_and_text_keep_markdown_notation(self):
        rows = extract.elements(self.path)
        self.assertEqual([r[0] for r in rows], [f"P{i}" for i in range(1, 9)])
        self.assertEqual([r[1] for r in rows], ["heading", "paragraph", "list", "fence", "table", "quote", "comment", "list"])
        self.assertEqual(rows[0][2], "# 題名")
        self.assertEqual(rows[1][2], "本文の一行目。\n二行目。")  # 見出しの直後でも別ブロック
        self.assertEqual(rows[2][2], "- 項目1\n- 項目2\n  - 入れ子")

    def test_front_matter_is_dropped_and_code_fence_keeps_blank_lines(self):
        rows = extract.elements(self.path)
        self.assertNotIn("title:", "".join(r[2] for r in rows))
        self.assertEqual(rows[3][2], "```bash\necho 1\n\necho 2\n```")

    def test_cli_escapes_newlines_one_line_per_block(self):
        code, out, err = run_script(TOOLS_DIR / "extract_markdown_text.py", str(self.path))
        self.assertEqual(code, 0, err)
        self.assertEqual(len(out.splitlines()), 8)
        self.assertIn("P2\tparagraph\t本文の一行目。\\n二行目。", out)

    def test_unreadable_input_exits_two(self):
        code, _, err = run_script(TOOLS_DIR / "extract_markdown_text.py", str(Path(self.folder.name, "missing.md")))
        self.assertEqual(code, 2)
        self.assertIn("extract failed", err)


if __name__ == "__main__":
    unittest.main()
