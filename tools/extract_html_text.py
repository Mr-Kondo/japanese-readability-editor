#!/usr/bin/env python3
"""HTML の本文を段落の順に取り出す。標準ライブラリのみ、通信・書き込みなし。

    python3 tools/extract_html_text.py FILE.html [--root SELECTOR]

公開文書の抜粋を台帳に載せる際の変換段階として使う。出力は1行1要素で、行頭の識別子が抜粋範囲（locator）になる。
  P<連番>\\t<要素>\\t<本文>   空でない段落・見出し・箇条書き・表のセル・コードブロック等（連番は空でないものだけ）

--root は本文の範囲（例: div[role=main]、main、div.main_text、#content）。省略時は文書全体。
指定すると、その要素の内側だけを対象にする。

規則:
  - script/style/nav/svg/button、Sphinx の見出しリンク（a.headerlink）は含めない。
  - pre の中は空白と改行をそのまま残す。それ以外は連続する空白を1つにまとめる。
    ただし改行を含む空白が全角文字どうしの間にあるときは、ブラウザの表示に合わせて消す。
  - br、ブロック要素（p/li/h1-h6/pre/td/th/dt/dd/blockquote/caption/figcaption/div/tr）の境界で段落を分ける。
  - ルビ（ruby）は 親字《ルビ》 の形で残し、rp は含めない。画像は alt を本文として残す（青空文庫の外字）。
  - 傍点（class に sesame_dot）と傍線（underline_solid）は ［＃傍点］…［＃傍点終わり］ の形で残す。
制約: 表の行・列の位置、画像、CSS による表示の変更、JavaScript で追加される内容は再現しない。
    文書の見た目の再現ではなく、本文の取り出しが目的。
"""
from __future__ import annotations

import re
import sys
from html.parser import HTMLParser

sys.dont_write_bytecode = True

BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "td", "th", "dt", "dd", "blockquote",
          "caption", "figcaption", "div", "tr"}
SKIPPED = {"script", "style", "nav", "svg", "button", "noscript", "template"}
VOID = {"br", "img", "hr", "meta", "link", "input", "wbr", "col", "area", "base", "source", "track", "embed"}
EMPHASIS = {"sesame_dot": "傍点", "underline_solid": "傍線"}
WIDE = re.compile(r"[぀-ヿ㐀-鿿＀-￯　-〿]")  # かな・漢字・全角記号


def parse_selector(selector: str) -> dict:
    """tag#id.class[attr=value] の形だけを扱う。"""
    match = re.fullmatch(r"([a-zA-Z0-9]*)(#[\w-]+)?((?:\.[\w-]+)*)((?:\[[\w-]+=[^\]]+\])*)", selector)
    if not match:
        raise ValueError(f"unsupported selector: {selector}")
    attributes = dict(a.strip("[]").split("=", 1) for a in re.findall(r"\[[^\]]+\]", match.group(4)))
    return {"tag": match.group(1) or None, "id": (match.group(2) or "")[1:] or None,
            "classes": [c for c in match.group(3).split(".") if c], "attributes": attributes}


def matches(selector: dict, tag: str, attributes: dict) -> bool:
    classes = (attributes.get("class") or "").split()
    return ((selector["tag"] in (None, tag)) and (selector["id"] in (None, attributes.get("id")))
            and all(c in classes for c in selector["classes"])
            and all(attributes.get(k) == v.strip("\"'") for k, v in selector["attributes"].items()))


def join_text(parts: list) -> str:
    """空白をまとめる。改行を含む空白が全角文字の間にあれば消す。"""
    text = re.sub(r"[ \t\r\f\v]*\n[ \t\r\f\v\n]*", "\n", "".join(parts))
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    out = []
    for index, char in enumerate(text):
        if char != "\n":
            out.append(char)
        elif not (index and WIDE.match(text[index - 1]) and index + 1 < len(text) and WIDE.match(text[index + 1])):
            out.append(" ")
    return re.sub(r" {2,}", " ", "".join(out)).strip()


# 終了タグを省略できる要素が、次の開始タグで暗黙に閉じられる規則（最小限）
IMPLIED_CLOSE = {
    "p": {"p", "ul", "ol", "dl", "pre", "table", "blockquote", "div", "h1", "h2", "h3", "h4", "h5", "h6"},
    "li": {"li"}, "dt": {"dt", "dd"}, "dd": {"dt", "dd"},
    "td": {"td", "th", "tr"}, "th": {"td", "th", "tr"}, "tr": {"tr"},
}


class Extractor(HTMLParser):
    def __init__(self, root: dict | None):
        super().__init__(convert_charrefs=True)
        self.root, self.inside, self.done = root, root is None, False
        self.stack = []  # (タグ, 効果の種類): "skip"=本文に含めない、"inert"=skip の内側、""=通常
        self.skip, self.pre = 0, 0
        self.parts, self.blocks, self.emphasis, self.rows = [], [], [], []

    def flush(self) -> None:
        text = "".join(self.parts).strip("\n") if self.pre else join_text(self.parts)
        if text.strip():
            self.rows.append((f"P{len(self.rows) + 1}", self.blocks[-1] if self.blocks else "text", text))
        self.parts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if not self.inside:
            if self.done or not (self.root and matches(self.root, tag, attributes)):
                return
            self.inside = True
        while self.stack and tag in IMPLIED_CLOSE.get(self.stack[-1][0], ()):
            self.close_top()
        classes = (attributes.get("class") or "").split()
        if tag in VOID:
            if not self.skip:
                if tag == "br":
                    self.flush()
                elif tag == "img" and attributes.get("alt"):
                    self.parts.append(attributes["alt"])
            return
        if self.skip:
            self.stack.append((tag, "inert"))
        elif tag in SKIPPED or tag == "rp" or "headerlink" in classes:
            self.stack.append((tag, "skip"))
            self.skip += 1
        else:
            self.stack.append((tag, ""))
            if tag in BLOCKS:
                self.flush()
                self.blocks.append(tag)
                self.pre += tag == "pre"
            elif tag == "rt":
                self.parts.append("《")
            marks = [EMPHASIS[c] for c in classes if c in EMPHASIS]
            if marks:
                self.parts.append("".join(f"［＃{m}］" for m in marks))
                self.emphasis.append((len(self.stack), marks))

    def close_top(self) -> None:
        tag, kind = self.stack.pop()
        if kind == "skip":
            self.skip -= 1
        elif kind == "":
            if self.emphasis and self.emphasis[-1][0] == len(self.stack) + 1:
                self.parts.append("".join(f"［＃{m}終わり］" for m in self.emphasis.pop()[1]))
            if tag == "rt":
                self.parts.append("》")
            elif tag in BLOCKS:
                self.flush()
                self.pre -= tag == "pre"
                self.blocks.pop()

    def handle_endtag(self, tag):
        if not self.inside or tag in VOID or tag not in [t for t, _ in self.stack]:
            return
        while self.stack:
            closed = self.stack[-1][0]
            self.close_top()
            if closed == tag:
                break
        if not self.stack:
            self.flush()
            self.inside, self.done = self.root is None, self.root is not None

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.inside and not self.skip:
            self.parts.append(data)


def decode(raw: bytes) -> str:
    if raw.startswith(b"\xef\xbb\xbf"):
        text = raw[3:].decode("utf-8")
    else:
        found = re.search(rb"charset=[\"']?([\w-]+)", raw[:2048], re.I)
        name = found.group(1).decode("ascii").lower() if found else "utf-8"
        text = raw.decode({"shift_jis": "cp932", "shift-jis": "cp932", "x-sjis": "cp932"}.get(name, name))
    return text.replace("\r\n", "\n").replace("\r", "\n")  # HTML 仕様と同じ改行の正規化


def elements(path, root: str | None = None) -> list:
    """(識別子, 要素, 本文) の一覧。"""
    with open(path, "rb") as handle:
        html = decode(handle.read())
    extractor = Extractor(parse_selector(root) if root else None)
    extractor.feed(html)
    extractor.close()
    extractor.flush()
    return extractor.rows


def escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t")


def render(rows: list) -> str:
    return "".join(f"{i}\t{label}\t{escape(text)}\n" for i, label, text in rows)


def main(argv=None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    root = None
    if "--root" in arguments:
        position = arguments.index("--root")
        root = arguments[position + 1] if position + 1 < len(arguments) else None
        arguments = arguments[:position] + arguments[position + 2:]
    if len(arguments) != 1 or ("--root" in sys.argv[1:] and root is None):
        print("usage: extract_html_text.py FILE.html [--root SELECTOR]", file=sys.stderr)
        return 2
    try:
        sys.stdout.write(render(elements(arguments[0], root)))
    except (OSError, ValueError, UnicodeDecodeError) as error:
        print(f"extract failed: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
