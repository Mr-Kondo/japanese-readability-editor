"""HTML 本文抽出。入力はテスト内で組み立てる人工の最小 HTML。"""
import tempfile
import unittest
from pathlib import Path

from helpers import TOOLS_DIR, load_module, run_script

extract = load_module("extract_html_text", TOOLS_DIR / "extract_html_text.py")
SPHINX = """<html><head><title>t</title><script>var x = 1;</script></head><body>
<nav><p>ナビ</p></nav>
<div role="main"><h1>見出し<a class="headerlink" href="#x">¶</a></h1>
<p>一文目です。
二文目を続けます。 English
word と続く。</p>
<ul><li>項目 <code>sys.path</code> の説明<ul><li>入れ子</li></ul></li></ul>
<pre><span>&gt;&gt;&gt; x = 1</span>
    indented
</pre>
<p><ruby><rb>漢字</rb><rp>(</rp><rt>かんじ</rt><rp>)</rp></ruby>と<em class="sesame_dot">強調</em>と<img alt="※(外字)" src="g.png"/>。</p>
<table><tr><td>セル1</td><td>セル2</td></tr></table>
</div><div><p>範囲外</p></div></body></html>"""


class ExtractHtmlTextTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name, "page.html")
        self.path.write_text(SPHINX, encoding="utf-8")

    def rows(self, root="div[role=main]"):
        return extract.elements(self.path, root)

    def test_root_limits_scope_and_skips_navigation_script_and_headerlink(self):
        texts = [r[2] for r in self.rows()]
        self.assertEqual(texts[0], "見出し")
        self.assertNotIn("ナビ", texts)
        self.assertNotIn("範囲外", texts)
        self.assertFalse(any("var x" in t or "¶" in t for t in texts))

    def test_whitespace_collapses_but_cjk_line_break_disappears(self):
        text = self.rows()[1][2]
        self.assertEqual(text, "一文目です。二文目を続けます。 English word と続く。")

    def test_nested_list_items_are_separate_paragraphs_in_order(self):
        rows = self.rows()
        self.assertEqual([r[2] for r in rows[2:4]], ["項目 sys.path の説明", "入れ子"])
        self.assertEqual([r[0] for r in rows], [f"P{i}" for i in range(1, len(rows) + 1)])

    def test_pre_keeps_newlines_and_indentation(self):
        code = next(r for r in self.rows() if r[1] == "pre")
        self.assertEqual(code[2], ">>> x = 1\n    indented")

    def test_ruby_emphasis_and_image_alt_are_kept_as_notation(self):
        text = next(r[2] for r in self.rows() if "漢字" in r[2])
        self.assertEqual(text, "漢字《かんじ》と［＃傍点］強調［＃傍点終わり］と※(外字)。")

    def test_table_cells_are_separate_elements(self):
        self.assertEqual([r[2] for r in self.rows()[-2:]], ["セル1", "セル2"])

    def test_without_root_the_whole_document_is_read(self):
        self.assertIn("範囲外", [r[2] for r in self.rows(None)])

    def test_omitted_end_tags_and_unquoted_attributes_still_split_paragraphs(self):
        path = Path(self.folder.name, "minified.html")
        path.write_text("<body><main class=content><h1>題<p>一<p>二<ul><li>甲<li>乙</ul><table><tr><td>a<td>b</table></main><p>外", encoding="utf-8")
        self.assertEqual([r[2] for r in extract.elements(path, "main.content")], ["題", "一", "二", "甲", "乙", "a", "b"])

    def test_shift_jis_declared_by_meta_is_decoded(self):
        path = Path(self.folder.name, "sjis.html")
        path.write_bytes('<html><head><meta charset="Shift_JIS"></head><body><p>日本語</p></body></html>'.encode("cp932"))
        self.assertEqual(extract.elements(path)[0][2], "日本語")

    def test_crlf_input_is_normalized_to_lf(self):
        path = Path(self.folder.name, "crlf.html")
        path.write_bytes("<body><pre>a\r\n  b\rc</pre></body>".encode("utf-8"))
        self.assertEqual(extract.elements(path)[0][2], "a\n  b\nc")

    def test_cli_escapes_control_characters_one_line_per_element(self):
        code, out, err = run_script(TOOLS_DIR / "extract_html_text.py", str(self.path), "--root", "div[role=main]")
        self.assertEqual(code, 0, err)
        self.assertIn("pre\t>>> x = 1\\n    indented", out)

    def test_unreadable_input_or_bad_selector_exits_two(self):
        code, _, err = run_script(TOOLS_DIR / "extract_html_text.py", str(Path(self.folder.name, "missing.html")))
        self.assertEqual(code, 2)
        self.assertIn("extract failed", err)
        code, _, _ = run_script(TOOLS_DIR / "extract_html_text.py", str(self.path), "--root", "a > b")
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
