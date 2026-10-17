#!/usr/bin/env python3
"""Markdown を、空行で区切ったブロックの順に取り出す。標準ライブラリのみ、通信・書き込みなし。

    python3 tools/extract_markdown_text.py FILE.md

公開文書の抜粋を台帳に載せる際の変換段階として使う。出力は1行1ブロックで、行頭の識別子が抜粋範囲（locator）になる。
  P<連番>\\t<種別>\\t<本文>   ブロックの連番は1から。本文は Markdown の記法をそのまま残す。

種別: heading（# で始まる1行）、fence（```／~~~ で囲んだコード）、list（- * + 数字. で始まる行を含む塊）、
table（| で始まる行の塊）、quote（> の塊）、comment（<!-- -->）、paragraph。

規則:
  - 先頭の YAML front matter（--- で囲む部分）は含めない。
  - コードブロックの中の空行ではブロックを分けない。見出し行は、直前に空行がなくても独立したブロックにする。
  - 記法は解釈しない。リンク先、強調、HTML、ショートコードは本文として残る。
制約: 参照式リンクの定義や脚注の対応は追わない。文書の見た目の再現ではなく、本文の取り出しが目的。
"""
from __future__ import annotations

import re
import sys

sys.dont_write_bytecode = True
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
LIST = re.compile(r"^\s*([-*+]|\d+[.)])\s+")


def kind_of(lines: list) -> str:
    first = lines[0]
    if FENCE.match(first):
        return "fence"
    if first.startswith("#"):
        return "heading"
    if first.lstrip().startswith("<!--"):
        return "comment"
    if first.lstrip().startswith(">"):
        return "quote"
    if first.lstrip().startswith("|"):
        return "table"
    return "list" if any(LIST.match(line) for line in lines) else "paragraph"


def blocks(text: str) -> list:
    """(識別子, 種別, 本文) の一覧。"""
    lines = text.replace("\r\n", "\n").split("\n")
    if lines and lines[0].strip() == "---":
        end = next((i for i, line in enumerate(lines[1:], 1) if line.strip() == "---"), None)
        lines = lines[end + 1:] if end else lines
    rows, current, fence = [], [], None

    def flush():
        if current:
            rows.append((f"P{len(rows) + 1}", kind_of(current), "\n".join(current).rstrip()))
            current.clear()

    for line in lines:
        marker = FENCE.match(line)
        if fence:
            current.append(line)
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence) and not line.strip().strip(fence[0]):
                fence = None
                flush()
        elif marker:
            flush()
            fence = marker.group(1)
            current.append(line)
        elif not line.strip():
            flush()
        elif line.startswith("#") and not line.startswith("#!"):
            flush()
            current.append(line)
            flush()
        else:
            current.append(line)
    flush()
    return rows


def elements(path) -> list:
    with open(path, "rb") as handle:
        return blocks(handle.read().decode("utf-8-sig"))


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")


def render(rows: list) -> str:
    return "".join(f"{i}\t{kind}\t{escape(text)}\n" for i, kind, text in rows)


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        print("usage: extract_markdown_text.py FILE.md", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(render(elements(arguments[0])))
    except (OSError, UnicodeDecodeError) as error:
        print(f"extract failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
