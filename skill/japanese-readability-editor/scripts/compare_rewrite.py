#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "sudachipy>=0.6.8",
#     "sudachidict-core>=20240409",
# ]
# ///
"""書き換えの前後を比べ、意味が変わったかもしれない箇所を挙げる。読み取り専用。

    compare_rewrite.py before.md after.md [--json] [--tokenizer auto|sudachi|regex]

SKILL.md の「書き換えた後の照合」を、機械で補助する。挙げる候補は次のとおり。

  numbers    数値(単位を含む)が消えた、または増えた
  urls       URL が消えた、または増えた
  code       インラインコードと fenced code block が消えた、または増えた
  terms      英数字の語とカタカナ語(固有名詞・技術用語の候補)が消えた、または増えた
  unmatched  書き換え後の文に、対応する元の文がない(原文にない情報の候補)。
             元の文に、対応する書き換え後の文がない(削除の候補)
  markers    否定、推量、可能、義務、依頼、勧誘、強調、限定、残余の条件の表現が、
             対応する文のあいだで増えた、または減った
  style      敬体と常体のどちらが多いかが変わった

これらは判定ではない。正しい言い換えも拾う。1つずつ元の文と見比べて決める。

SudachiPy と辞書(sudachidict-core など)が入っていれば、形態素解析を使う(--tokenizer auto)。
否定を品詞で数え、文の対応を内容語の重なりで推定し、カタカナ語の表記ゆれ(サーバ/サーバー)を
同じ語とみなす。入っていなければ、標準ライブラリだけで動く。否定は正規表現で数え、文の対応は
漢字・カタカナ・英数字を含む2文字の組の重なりで推定する。どちらも、語順の入れ替えと、
文の分割・統合(2文まで)には対応する。否定以外の表現の検出は、正規表現による近似である。

ネットワーク通信、ファイルの書き込み、外部コマンドの実行は行わない。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True  # measure を読み込むときに、skill の中へ __pycache__ を作らない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure  # noqa: E402

UNMATCHED_THRESHOLD = 0.5  # 対応先との重なりがこれ未満なら、対応する文がないとみなす
MAX_WINDOW = 2  # 分割・統合として、連続する何文までを1つの対応先とみなすか
DEFAULT_MAX_SHOWN = 20

# --- 抜き出す語 -------------------------------------------------------------

NUMBER_RE = re.compile(
    r"\d+(?:[.,]\d+)*"
    r"(?:\s?(?:%|[A-Za-z]+|[秒分時日週月年件回倍個字行円人台本度点枚つ割歳]))?"
)
ASCII_TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.+#/-]*[A-Za-z0-9+#]|[A-Za-z]{2,}")
KATAKANA_TERM_RE = re.compile(r"[ァ-ヴ][ァ-ヴー]{2,}")
FENCED_BLOCK_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})[^\n]*\n(.*?)^ {0,3}\1[`~]*[ \t]*$", re.M | re.S)
HEADING_MARK_RE = re.compile(r"^\s{0,3}#{1,6}\s+")

# --- 表現の種類 -------------------------------------------------------------
# 否定は、解析器ごとに数える(RegexAnalyzer、SudachiAnalyzer)。ほかの表現は正規表現で数える。
# 正規表現の否定は、「少ない」「危ない」「まず」「必ず」のように、否定ではない語を除く。
NEGATION_RE = re.compile(r"(?<![少危切])な(?:い|く|かっ|けれ)|ません|(?<![ま必わ])ず(?=[にとも、。])")
REGEX_MARKERS: Dict[str, re.Pattern] = {
    "conjecture": re.compile(
        r"でしょう|だろう|かもしれ|と思(?:う|われ|います)|と考えられ|ようだ|ようです|らしい|"
        r"可能性が|はずだ|はずです|おそれ|恐れが"
    ),
    "ability": re.compile(r"でき(?:る|ます|ない|ません|た|て)|可能(?:だ|です|な|に)"),
    "obligation": re.compile(r"なければ(?:ならな|なりませ|いけな)|必要があ|必要です|べき|必須"),
    "request": re.compile(r"[てで](?:ください|下さい)"),
    "invitation": re.compile(r"ましょう|しよう(?=[。！!])"),
    "emphasis": re.compile(r"必ず|絶対|確実に|常に|決して|まったく|全く"),
    "limit": re.compile(r"のみ|だけ|しか|に限り|に限って"),
    "residual": re.compile(r"それ以外|上記以外|以外の場合|その他の場合"),
}
MARKER_KINDS = ("negation",) + tuple(REGEX_MARKERS)
POLITE_END_RE = re.compile(r"(?:です|ます|ません|でした|ました|でしょう|ください|ましょう)[。！？!?」』）)]*$")
PLAIN_END_RE = re.compile(r"[。！？!?]$")


def normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def is_content_char(ch: str) -> bool:
    return ch.isalnum() and not ("ぁ" <= ch <= "ゟ")  # ひらがな以外の文字・数字


# --- 解析器 -----------------------------------------------------------------


class RegexAnalyzer:
    """標準ライブラリだけで動く解析器。"""

    name = "regex"
    min_units = 4  # 2文字の組がこれより少ない文は、対応の有無を判断しない

    def units(self, text: str) -> FrozenSet[str]:
        """文の対応を推定するための単位。漢字・カタカナ・英数字を含む2文字の組。"""
        chars = [ch for ch in normalize(text) if not ch.isspace()]
        return frozenset(a + b for a, b in zip(chars, chars[1:]) if is_content_char(a) or is_content_char(b))

    def negations(self, text: str) -> int:
        return len(NEGATION_RE.findall(text))

    def term_key(self, term: str) -> str:
        return term


class SudachiAnalyzer:
    """SudachiPy による解析器。辞書は core、full、small の順に探す。"""

    min_units = 2  # 内容語がこれより少ない文は、対応の有無を判断しない
    CONTENT_POS = {"名詞", "動詞", "形容詞", "副詞", "形状詞"}
    LIGHT_WORDS = {"する", "ある", "いる", "なる", "こと", "もの"}
    NEGATIVE_AUXILIARIES = {"ない", "ぬ", "ず", "ん"}

    def __init__(self) -> None:
        from sudachipy import Dictionary, SplitMode  # 入っていなければ ImportError

        dictionary = None
        for dict_name in ("core", "full", "small"):
            try:
                dictionary = Dictionary(dict=dict_name)
                break
            except ImportError:  # その辞書のパッケージ(sudachidict_*)が入っていない
                continue
        if dictionary is None:
            raise ImportError("no Sudachi dictionary package (sudachidict_core, _full or _small) is installed")
        create = getattr(dictionary, "tokenizer", None) or dictionary.create  # 0.6 系は create だけ
        self._tokenizer = create()
        self._mode = SplitMode.C
        self.name = f"sudachi (sudachidict_{dict_name})"

    def _morphemes(self, text: str):
        return self._tokenizer.tokenize(normalize(text), self._mode)

    def units(self, text: str) -> FrozenSet[str]:
        """文の対応を推定するための単位。内容語の正規化形。"""
        words = set()
        for morpheme in self._morphemes(text):
            pos = morpheme.part_of_speech()
            form = morpheme.normalized_form()
            if pos[0] in self.CONTENT_POS and pos[1] not in ("非自立可能", "数詞") and form not in self.LIGHT_WORDS:
                words.add(form)
        return frozenset(words)

    def negations(self, text: str) -> int:
        count = 0
        for morpheme in self._morphemes(text):
            pos = morpheme.part_of_speech()
            form = morpheme.normalized_form()
            if (pos[0] == "助動詞" and form in self.NEGATIVE_AUXILIARIES) or (pos[0] == "形容詞" and form == "無い"):
                count += 1
        return count

    def term_key(self, term: str) -> str:
        """カタカナ語は表記ゆれをそろえる。英数字の語は、カタカナに読み替えずにそのまま比べる。"""
        if not KATAKANA_TERM_RE.fullmatch(term):
            return term
        return "".join(m.normalized_form() for m in self._morphemes(term))


def load_analyzer(choice: str):
    """--tokenizer の指定に合う解析器を返す。sudachi を指定して使えないときは ImportError。"""
    if choice == "regex":
        return RegexAnalyzer()
    try:
        return SudachiAnalyzer()
    except ImportError:
        if choice == "sudachi":
            raise
        return RegexAnalyzer()


# --- 文書の解析 -------------------------------------------------------------


@dataclass
class Item:
    line: int
    text: str
    key: str = ""  # 比べるときの値。空なら text で比べる

    def __post_init__(self) -> None:
        self.key = self.key or self.text

    def to_dict(self) -> dict:
        return {"line": self.line, "text": self.text}


@dataclass
class Sentence:
    line: int
    text: str
    units: FrozenSet[str]
    markers: Counter
    judgeable: bool  # 対応の有無を判断できる長さか


@dataclass
class Document:
    path: str
    numbers: List[Item] = field(default_factory=list)
    urls: List[Item] = field(default_factory=list)
    code: List[Item] = field(default_factory=list)
    terms: List[Item] = field(default_factory=list)
    sentences: List[Sentence] = field(default_factory=list)


def count_markers(text: str, analyzer) -> Counter:
    counts = Counter({kind: len(pattern.findall(text)) for kind, pattern in REGEX_MARKERS.items()})
    counts["negation"] = analyzer.negations(text)
    return counts


def line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def collect_code_blocks(text: str, doc: Document) -> None:
    for match in FENCED_BLOCK_RE.finditer(text):
        doc.code.append(Item(line_of(text, match.start()), match.group(2).rstrip("\n")))


def split_link(match: re.Match) -> str:
    """Markdown のリンクを、表示テキストとリンク先に分ける。リンク先の URL も比べるため。"""
    text = match.group(1)
    target = match.group(0)[len(text) + 3:-1]  # "[" + text + "](" の後ろから ")" の手前まで
    return f"{text} {target} "


def collect_line_items(number: int, line: str, doc: Document, markdown: bool, analyzer) -> None:
    """1行から、インラインコード、URL、数値、語を抜き出す。"""
    if markdown:
        for match in measure.CODE_SPAN_RE.finditer(line):
            doc.code.append(Item(number, match.group(0)))
        line = measure.CODE_SPAN_RE.sub(" ", line)
        line = measure.IMAGE_RE.sub(" ", line)
        line = measure.LINK_RE.sub(split_link, line)
        line = measure.HTML_TAG_RE.sub(" ", line)
    for match in measure.URL_RE.finditer(line):
        doc.urls.append(Item(number, match.group(0).rstrip(".,)")))
    line = measure.URL_RE.sub(" ", line)
    if markdown:
        line = measure.QUOTE_RE.sub("", line)
        line = HEADING_MARK_RE.sub("", line)
        line = measure.LIST_ITEM_RE.sub("", line)
    line = normalize(line)
    doc.numbers += [Item(number, m.group(0).replace(" ", "")) for m in NUMBER_RE.finditer(line)]
    for pattern in (ASCII_TERM_RE, KATAKANA_TERM_RE):
        doc.terms += [Item(number, m.group(0), analyzer.term_key(m.group(0))) for m in pattern.finditer(line)]


def collect_sentences(text: str, doc: Document, markdown: bool, analyzer) -> None:
    for block in measure.extract_blocks(text, markdown=markdown):
        for offset, sentence in measure.split_sentences(block.text):
            units = analyzer.units(sentence)
            doc.sentences.append(Sentence(block.line_at(offset), sentence, units,
                                          count_markers(sentence, analyzer), len(units) >= analyzer.min_units))


def parse_document(text: str, path: str, markdown: bool = True, analyzer=None) -> Document:
    analyzer = analyzer or RegexAnalyzer()
    doc = Document(path)
    lines = measure.split_lines(text)
    if markdown:
        collect_code_blocks("\n".join(lines), doc)
        source_lines = ((n, raw) for n, raw in measure.markdown_lines(lines) if raw is not None)
    else:
        source_lines = enumerate(lines, start=1)
    for number, raw in source_lines:
        collect_line_items(number, raw, doc, markdown, analyzer)
    doc.code.sort(key=lambda item: item.line)  # fenced code block を先に集めたので、行の順に並べ直す
    collect_sentences(text, doc, markdown, analyzer)
    return doc


# --- 比較 -------------------------------------------------------------------


@dataclass
class Match:
    coverage: float
    start: int  # 対応先の最初の文の位置
    end: int  # 対応先の最後の文の次の位置


def best_match(sentence: Sentence, others: Sequence[Sentence]) -> Optional[Match]:
    """sentence の単位が、others の連続する1〜MAX_WINDOW 文に最も多く含まれる位置を返す。"""
    if not sentence.units or not others:
        return None
    best: Optional[Match] = None
    for start in range(len(others)):
        window: FrozenSet[str] = frozenset()
        for end in range(start + 1, min(start + MAX_WINDOW, len(others)) + 1):
            window = window | others[end - 1].units
            coverage = len(sentence.units & window) / len(sentence.units)
            if best is None or coverage > best.coverage + 1e-9:
                best = Match(coverage, start, end)
    return best


def take_surplus(items: List[Item], surplus: Counter) -> List[Item]:
    """surplus の回数だけ、items を後ろから選ぶ(増えた・消えたのは、後に出たほうとみなす)。"""
    chosen: List[Item] = []
    remaining = Counter(surplus)
    for item in reversed(items):
        if remaining[item.key] > 0:
            remaining[item.key] -= 1
            chosen.append(item)
    return list(reversed(chosen))


def compare_items(before: List[Item], after: List[Item]) -> Dict[str, List[Item]]:
    """出現回数の差で、消えたものと増えたものを返す。"""
    before_counts = Counter(item.key for item in before)
    after_counts = Counter(item.key for item in after)
    return {"missing": take_surplus(before, before_counts - after_counts),
            "added": take_surplus(after, after_counts - before_counts)}


def compare_sentences(before: Document, after: Document) -> Tuple[Dict[str, List[Item]], Dict[str, dict]]:
    unmatched: Dict[str, List[Item]] = {"after": [], "before": []}
    markers = {kind: {"before": sum(s.markers[kind] for s in before.sentences),
                      "after": sum(s.markers[kind] for s in after.sentences),
                      "removed": [], "added": []}
               for kind in MARKER_KINDS}
    for side, own, others in (("after", after.sentences, before.sentences), ("before", before.sentences, after.sentences)):
        direction = "added" if side == "after" else "removed"
        for sentence in own:
            match = best_match(sentence, others)
            if sentence.judgeable and (match is None or match.coverage < UNMATCHED_THRESHOLD):
                unmatched[side].append(Item(sentence.line, sentence.text))
                continue  # 対応先が分からない文では、表現の増減を比べない
            counterpart: Counter = Counter()
            if match is not None:
                for other in others[match.start:match.end]:
                    counterpart.update(other.markers)
            for kind in MARKER_KINDS:
                if sentence.markers[kind] > counterpart[kind]:
                    markers[kind][direction].append(Item(sentence.line, sentence.text))
    return unmatched, markers


def style_counts(doc: Document) -> Dict[str, int]:
    polite = sum(1 for s in doc.sentences if POLITE_END_RE.search(s.text))
    plain = sum(1 for s in doc.sentences if PLAIN_END_RE.search(s.text) and not POLITE_END_RE.search(s.text))
    return {"polite": polite, "plain": plain}


def majority_style(counts: Dict[str, int]) -> Optional[str]:
    if counts["polite"] + counts["plain"] == 0:
        return None
    return "polite" if counts["polite"] > counts["plain"] else "plain"


def compare_documents(before: Document, after: Document, tokenizer: str = RegexAnalyzer.name) -> dict:
    unmatched, markers = compare_sentences(before, after)
    style_before, style_after = style_counts(before), style_counts(after)
    majorities = (majority_style(style_before), majority_style(style_after))
    return {
        "tokenizer": tokenizer,
        "numbers": compare_items(before.numbers, after.numbers),
        "urls": compare_items(before.urls, after.urls),
        "code": compare_items(before.code, after.code),
        "terms": compare_items(before.terms, after.terms),
        "unmatched": unmatched,
        "markers": markers,
        "style": {"before": style_before, "after": style_after,
                  "changed": None not in majorities and majorities[0] != majorities[1]},
    }


# --- 出力 -------------------------------------------------------------------

ITEM_KINDS = ("numbers", "urls", "code", "terms")


def format_list(lines: List[str], items: List[Item], path: str, label: str, limit: int) -> None:
    visible = items if limit <= 0 else items[:limit]
    for item in visible:
        lines.append(f"  {path}:{item.line}  {label}  {measure.make_preview(item.text)}")
    if len(items) > len(visible):
        lines.append(f"  ... {len(items) - len(visible)} more not shown (use --max 0 for all)")


def format_text(result: dict, before_path: str, after_path: str, limit: int) -> str:
    lines = [f"before: {before_path}", f"after:  {after_path}", f"tokenizer: {result['tokenizer']}",
             "pointers (info only, not verdicts):"]
    for kind in ITEM_KINDS:
        pair = result[kind]
        lines.append(f"{kind}: {len(pair['missing'])} missing, {len(pair['added'])} added")
        format_list(lines, pair["missing"], before_path, "missing", limit)
        format_list(lines, pair["added"], after_path, "added  ", limit)
    unmatched = result["unmatched"]
    lines.append(f"unmatched sentences: {len(unmatched['after'])} in after, {len(unmatched['before'])} in before")
    format_list(lines, unmatched["after"], after_path, "no source ", limit)
    format_list(lines, unmatched["before"], before_path, "no rewrite", limit)
    lines.append("markers (before -> after):")
    for kind, data in result["markers"].items():
        if data["removed"] or data["added"] or data["before"] != data["after"]:
            lines.append(f"  {kind}: {data['before']} -> {data['after']}")
            format_list(lines, data["removed"], before_path, "removed", limit)
            format_list(lines, data["added"], after_path, "added  ", limit)
    style = result["style"]
    lines.append(
        f"style: polite {style['before']['polite']} / plain {style['before']['plain']} -> "
        f"polite {style['after']['polite']} / plain {style['after']['plain']}"
        + ("  (majority changed)" if style["changed"] else "")
    )
    return "\n".join(lines)


def to_json(result: dict, before_path: str, after_path: str) -> dict:
    def items(values: List[Item]) -> List[dict]:
        return [item.to_dict() for item in values]

    payload: dict = {"before": before_path, "after": after_path, "tokenizer": result["tokenizer"]}
    for kind in ITEM_KINDS:
        payload[kind] = {key: items(values) for key, values in result[kind].items()}
    payload["unmatched"] = {key: items(values) for key, values in result["unmatched"].items()}
    payload["markers"] = {
        kind: {"before": data["before"], "after": data["after"],
               "removed": items(data["removed"]), "added": items(data["added"])}
        for kind, data in result["markers"].items()
    }
    payload["style"] = result["style"]
    return payload


# --- CLI --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="compare_rewrite.py",
        description="書き換えの前後を比べ、意味が変わったかもしれない箇所を挙げる(読み取り専用)。判定ではない。",
    )
    parser.add_argument("before", help="書き換える前のファイル")
    parser.add_argument("after", help="書き換えた後のファイル")
    parser.add_argument("--json", action="store_true", help="JSON で出力する(候補は全件)")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX_SHOWN, metavar="N",
                        help=f"種類ごとに表示する件数の上限。0 で無制限。既定 {DEFAULT_MAX_SHOWN}")
    parser.add_argument("--format", choices=("auto", "markdown", "plain"), default="auto",
                        help="Markdown として解析するか。auto は before の拡張子で判断する。既定 auto")
    parser.add_argument("--tokenizer", choices=("auto", "sudachi", "regex"), default="auto",
                        help="auto は SudachiPy が入っていれば使い、なければ regex。既定 auto")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        before_text = measure.read_text(args.before)
        after_text = measure.read_text(args.after)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read: {exc}", file=sys.stderr)
        return 2
    try:
        analyzer = load_analyzer(args.tokenizer)
    except ImportError as exc:
        print(f"error: SudachiPy is not available ({exc}). "
              "Install it with: pip install sudachipy sudachidict-core", file=sys.stderr)
        return 2
    markdown = measure.is_markdown_path(args.before, args.format)
    result = compare_documents(parse_document(before_text, args.before, markdown, analyzer),
                               parse_document(after_text, args.after, markdown, analyzer), analyzer.name)
    if args.json:
        print(json.dumps(to_json(result, args.before, args.after), ensure_ascii=False, indent=2))
    else:
        print(format_text(result, args.before, args.after, args.max))
    return 0


if __name__ == "__main__":
    sys.exit(main())
