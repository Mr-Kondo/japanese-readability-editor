"""docx 本文抽出。入力はテスト内で組み立てる人工の最小 docx。"""
import tempfile
import unittest
import zipfile
from pathlib import Path

from helpers import TOOLS_DIR, load_module, run_script

extract = load_module("extract_docx_text", TOOLS_DIR / "extract_docx_text.py")
NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'
STYLES = f'<w:styles {NS}><w:style w:styleId="H1"><w:name w:val="heading 1"/></w:style></w:styles>'
DOCUMENT = f"""<w:document {NS}><w:body>
<w:p><w:pPr><w:pStyle w:val="H1"/></w:pPr><w:r><w:t>見出し</w:t></w:r></w:p>
<w:p><w:r><w:t>一文目。</w:t></w:r><w:r><w:br/></w:r><w:r><w:t>二文目</w:t></w:r><w:r><w:tab/></w:r>
<w:r><w:footnoteReference w:id="2"/></w:r><w:del><w:r><w:delText>削除済み</w:delText></w:r></w:del></w:p>
<w:p><w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="7"/></w:numPr></w:pPr><w:r><w:t>箇条書き</w:t></w:r></w:p>
<w:p/>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>項目</w:t></w:r></w:p><w:p><w:r><w:t>補足</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>値</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
</w:body></w:document>"""
FOOTNOTES = f'<w:footnotes {NS}><w:footnote w:id="2"><w:p><w:r><w:t>脚注本文</w:t></w:r></w:p></w:footnote></w:footnotes>'


def make_docx(folder: Path, **parts) -> Path:
    path = folder / "sample.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", parts.get("document", DOCUMENT))
        archive.writestr("word/styles.xml", STYLES)
        archive.writestr("word/footnotes.xml", FOOTNOTES)
    return path


class ExtractDocxTextTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = make_docx(Path(self.folder.name))

    def test_paragraphs_tables_and_footnotes_keep_order_and_identifiers(self):
        rows = extract.elements(self.path)
        self.assertEqual([r[0] for r in rows], ["P1", "P2", "P3", "P4", "T1.1.1", "T1.1.2", "N2"])
        self.assertEqual(rows[0][1:], ("heading 1", "", "見出し"))
        self.assertEqual(rows[1][3], "一文目。\n二文目\t[^2]")  # 変更履歴の削除分は含めない
        self.assertEqual(rows[2][2], "7:1")
        self.assertEqual(rows[3][3], "")  # 空段落も連番を進める
        self.assertEqual(rows[4][3], "項目 / 補足")
        self.assertEqual(rows[6][3], "脚注本文")

    def test_cli_escapes_control_characters_one_line_per_element(self):
        code, out, err = run_script(TOOLS_DIR / "extract_docx_text.py", str(self.path))
        self.assertEqual(code, 0, err)
        lines = out.splitlines()
        self.assertEqual(len(lines), 7)
        self.assertEqual(lines[1], "P2\t\t\t一文目。\\n二文目\\t[^2]")
        self.assertEqual(lines[4], "T1.1.1\t項目 / 補足")

    def test_unreadable_input_exits_two(self):
        code, _, err = run_script(TOOLS_DIR / "extract_docx_text.py", str(Path(self.folder.name, "missing.docx")))
        self.assertEqual(code, 2)
        self.assertIn("extract failed", err)


if __name__ == "__main__":
    unittest.main()
