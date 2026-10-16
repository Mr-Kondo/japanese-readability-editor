#!/usr/bin/env python3
"""docx の本文を段落・表の順に取り出す。標準ライブラリのみ、通信・書き込みなし。

    python3 tools/extract_docx_text.py FILE.docx

公開文書の抜粋を台帳に載せる際の変換段階として使う。出力は1行1要素で、行頭の識別子が抜粋範囲（locator）になる。
  P<連番>\\t<段落スタイル>\\t<自動番号 numId:ilvl>\\t<本文>   段落（空段落も連番を進める）
  T<表>.<行>.<列>\\t<本文>                                  表のセル（セル内の段落は " / " で連結）
  N<id>\\t<本文>                                            脚注

制約: 自動番号の文字列（(1)、ア等）は復元しない。図・テキストボックス・数式・変更履歴の削除分（w:delText）は
含めない。脚注参照は [^id] として本文に残す。文書の見た目の再現ではなく、本文の取り出しが目的。
"""
from __future__ import annotations

import sys
import zipfile
from xml.etree import ElementTree as ET

sys.dont_write_bytecode = True
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def run_text(element) -> str:
    out = []
    for node in element.iter():
        if node.tag == W + "t":
            out.append(node.text or "")
        elif node.tag == W + "tab":
            out.append("\t")
        elif node.tag in (W + "br", W + "cr"):
            out.append("\n")
        elif node.tag == W + "footnoteReference":
            out.append(f"[^{node.get(W + 'id')}]")
    return "".join(out)


def style_names(archive: zipfile.ZipFile) -> dict:
    if "word/styles.xml" not in archive.namelist():
        return {}
    names = {}
    for style in ET.fromstring(archive.read("word/styles.xml")).iter(W + "style"):
        name = style.find(W + "name")
        names[style.get(W + "styleId")] = name.get(W + "val") if name is not None else ""
    return names


def paragraph_info(paragraph, names: dict) -> tuple:
    style, level = "", ""
    properties = paragraph.find(W + "pPr")
    if properties is not None:
        found = properties.find(W + "pStyle")
        if found is not None:
            style = names.get(found.get(W + "val"), found.get(W + "val"))
        numbering = properties.find(W + "numPr")
        if numbering is not None:
            ilvl, num = numbering.find(W + "ilvl"), numbering.find(W + "numId")
            level = f"{num.get(W + 'val') if num is not None else ''}:{ilvl.get(W + 'val') if ilvl is not None else ''}"
    return style, level


def elements(path) -> list:
    """(識別子, 本文) の一覧。段落は (識別子, スタイル, 番号, 本文) の4要素。"""
    archive = zipfile.ZipFile(path)
    names = style_names(archive)
    body = ET.fromstring(archive.read("word/document.xml")).find(W + "body")
    rows, paragraphs, tables = [], 0, 0
    for child in body:
        if child.tag == W + "p":
            paragraphs += 1
            style, level = paragraph_info(child, names)
            rows.append((f"P{paragraphs}", style, level, run_text(child)))
        elif child.tag == W + "tbl":
            tables += 1
            for r, row in enumerate(child.iter(W + "tr"), 1):
                for c, cell in enumerate(row.findall(W + "tc"), 1):
                    texts = [run_text(p).strip() for p in cell.iter(W + "p")]
                    rows.append((f"T{tables}.{r}.{c}", "", "", " / ".join(t for t in texts if t)))
    if "word/footnotes.xml" in archive.namelist():
        for note in ET.fromstring(archive.read("word/footnotes.xml")).iter(W + "footnote"):
            text = "".join(run_text(p) for p in note.iter(W + "p")).strip()
            if text:
                rows.append((f"N{note.get(W + 'id')}", "", "", text))
    return rows


def render(rows: list) -> str:
    lines = []
    for identifier, style, level, text in rows:
        text = text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")
        lines.append(f"{identifier}\t{style}\t{level}\t{text}" if identifier.startswith("P") else f"{identifier}\t{text}")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: extract_docx_text.py FILE.docx", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(render(elements(arguments[0])))
    except (OSError, KeyError, ET.ParseError, zipfile.BadZipFile) as error:
        print(f"extract failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
