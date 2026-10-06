#!/usr/bin/env python3
"""日本語文章の長さに関する指標を測り、修正候補の位置を示す。読み取り専用。

段落は200字以上、文は80字以上を「修正候補」として数える。この数値は合否の基準では
なく、候補を見つけるための目安である。技術仕様や引用など、長いほうが正確な文章も
ある。数値を満たすためだけの機械的な分割はしない。

解析から可能な範囲で除くもの: fenced code block、YAML frontmatter、URL、Markdown の記号。
Markdown のリンクは表示テキストだけを残す。見出し・表・水平線も文章ではないので除く。
Markdown として扱うのは既定で拡張子が .md .markdown .mdx .mkd のファイルと標準入力である。

文の区切りは、句点・感嘆符・疑問符と括弧の対応から推定する。ASCII のピリオドでは区切らない。

--extras を付けると、長さとは別に、読み流すと見落としやすい4種類の箇所を「指摘」として挙げる。
  kanji-run        漢字が7字以上続く箇所(造語の圧縮漢語など。固有名詞・法令用語も拾う)
  no-chain         名詞と「の」が3回以上つながる箇所
  double-negative  「ないわけではない」のような二重否定
  unrendered-bold  太字にならず `**` がそのまま表示される箇所(Markdown のみ)
これらは判定ではない。読んで引っかからなければ直さない。

ネットワーク通信、ファイルの書き込み、外部コマンドの実行は行わない。
"""

from __future__ import annotations

import argparse
import bisect
import glob
import itertools
import json
import os
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

PARAGRAPH_THRESHOLD = 200
SENTENCE_THRESHOLD = 80
DEFAULT_MAX_LOCATE = 20
PREVIEW_LENGTH = 30
KANJI_RUN_THRESHOLD = 7
NO_CHAIN_COUNT = 3
SNIPPET_MARGIN = 10

MARKDOWN_SUFFIXES = (".md", ".markdown", ".mdx", ".mkd")
DIRECTORY_SUFFIXES = MARKDOWN_SUFFIXES + (".txt",)
SKIPPED_DIRECTORIES = {".git", "node_modules", "__pycache__", ".venv", "venv"}

# --- 文字種 ---------------------------------------------------------------


def is_kanji(ch: str) -> bool:
    o = ord(ch)
    return (
        0x4E00 <= o <= 0x9FFF
        or 0x3400 <= o <= 0x4DBF
        or 0xF900 <= o <= 0xFAFF
        or 0x20000 <= o <= 0x2FA1F
        or o == 0x3005  # 々
    )


def is_hiragana(ch: str) -> bool:
    o = ord(ch)
    return 0x3041 <= o <= 0x3096 or 0x309D <= o <= 0x309F


def is_cjk(ch: str) -> bool:
    return ord(ch) >= 0x2E80


def visible_length(text: str) -> int:
    """空白(改行・全角空白を含む)を除いた文字数。"""
    return sum(1 for ch in text if not ch.isspace())


# --- --extras の指摘 --------------------------------------------------------

_KANJI_CLASS = "\u4e00-\u9fff\u3400-\u4dbf\u3005"
# 漢字、カタカナ、英数字(全角を含む)。「APIの仕様」「v2の設定」の英数字も名詞として数える。
_NOUN_CLASS = _KANJI_CLASS + "\u30a1-\u30f6\u30fc" + "A-Za-z0-9\uff10-\uff19\uff21-\uff3a\uff41-\uff5a"

KANJI_RUN_RE = re.compile("[" + _KANJI_CLASS + "]{" + str(KANJI_RUN_THRESHOLD) + ",}")
NO_CHAIN_RE = re.compile("(?:[" + _NOUN_CLASS + "]+の){" + str(NO_CHAIN_COUNT) + "}[" + _NOUN_CLASS + "]+")
# 「〜ないと動かない」「〜なければならない」「〜ざるを得ない」「〜ないわけにはいかない」は、
# 必要条件や義務の定型で、符号の反転を計算させないので拾わない。
# 「否定できない」「不可能ではない」のように、漢語の否定に「ない」が重なるものは拾う。過去形も拾う。
_NEGATIVE_END = "(?:な(?:い|かっ)|ありません)"
DOUBLE_NEGATIVE_RE = re.compile(
    "|".join(
        (
            "ない(?:わけ|こと)(?:では|でも|は|も)" + _NEGATIVE_END,
            "な(?:く|いで)(?:は|も)" + _NEGATIVE_END,
            "ないとは(?:言え|いえ|言い切れ|いいきれ)(?:な(?:い|かっ)|ません)",
            "ないと(?:は|も)限(?:らな(?:い|かっ)|りません)",
            "(?:不可能|不要|不必要|無関係|無理)(?:では|でも)" + _NEGATIVE_END,
            "否定(?:でき|し(?:え|得))(?:な(?:い|かっ)|ません)",
            "否め(?:な(?:い|かっ)|ません)",
            "なきにしもあらず",
        )
    )
)
EXTRA_PATTERNS = (
    ("kanji-run", KANJI_RUN_RE),
    ("no-chain", NO_CHAIN_RE),
    ("double-negative", DOUBLE_NEGATIVE_RE),
)
UNRENDERED_BOLD = "unrendered-bold"
EXTRA_KINDS = tuple(kind for kind, _ in EXTRA_PATTERNS) + (UNRENDERED_BOLD,)
EXTRA_LABELS = {
    "kanji-run": f"kanji-run (>={KANJI_RUN_THRESHOLD} kanji in a row)",
    "no-chain": f"no-chain (noun + の x{NO_CHAIN_COUNT}+)",
    "double-negative": "double-negative",
    UNRENDERED_BOLD: "unrendered-bold (** shown as-is)",
}


def make_snippet(text: str, start: int, end: int) -> str:
    """指摘した箇所とその前後を、短く切り出す。"""
    left = max(0, start - SNIPPET_MARGIN)
    right = min(len(text), end + SNIPPET_MARGIN)
    return ("…" if left > 0 else "") + text[left:right] + ("…" if right < len(text) else "")


# --- Markdown の前処理 ------------------------------------------------------

FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
RULE_RE = re.compile(r"^\s{0,3}([-*_])(\s*\1){2,}\s*$")
SETEXT_RE = re.compile(r"^\s{0,3}(=+|-+)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|")
COMMENT_LINE_RE = re.compile(r"^\s*<!--.*-->\s*$")
LINK_DEFINITION_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*\S+")
LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]|\d{1,9}[.)])\s+")
TASK_BOX_RE = re.compile(r"^\[[ xX]\]\s+")
QUOTE_RE = re.compile(r"^\s{0,3}(?:>\s?)+")

IMAGE_RE = re.compile(r"!\[[^\]]*\]\((?:[^()]|\([^()]*\))*\)")
LINK_RE = re.compile(r"\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")
REFERENCE_LINK_RE = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
AUTOLINK_RE = re.compile(r"<(?:https?|ftp|mailto):[^>\s]+>")
URL_RE = re.compile(r"(?:https?|ftp)://[A-Za-z0-9\-._~:/?#\[\]@!$&'*+,;=%]+")
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>]*>")
EMPHASIS_RE = re.compile(r"\*+|__|~~")


def clean_inline(line: str) -> str:
    """1行分のインライン Markdown 記法と URL を取り除く。"""
    line = IMAGE_RE.sub("", line)
    line = LINK_RE.sub(r"\1", line)
    line = REFERENCE_LINK_RE.sub(r"\1", line)
    line = AUTOLINK_RE.sub("", line)
    line = URL_RE.sub("", line)
    line = HTML_TAG_RE.sub("", line)
    line = EMPHASIS_RE.sub("", line)
    line = line.replace("`", "")
    return line.strip()


@dataclass
class Block:
    """段落として数える連続した文章。"""

    text: str
    line_starts: List[Tuple[int, int]]  # (text 内の開始位置, 元ファイルの行番号)

    @property
    def first_line(self) -> int:
        return self.line_starts[0][1]

    def line_at(self, offset: int) -> int:
        offsets = [o for o, _ in self.line_starts]
        index = max(bisect.bisect_right(offsets, offset) - 1, 0)
        return self.line_starts[index][1]


class _BlockBuilder:
    def __init__(self) -> None:
        self.blocks: List[Block] = []
        self._text = ""
        self._starts: List[Tuple[int, int]] = []

    def add(self, line_number: int, part: str) -> None:
        if not part:
            return
        separator = ""
        if self._text and not (is_cjk(self._text[-1]) or is_cjk(part[0])):
            separator = " "
        self._starts.append((len(self._text) + len(separator), line_number))
        self._text += separator + part

    def flush(self) -> None:
        if self._text and visible_length(self._text) > 0:
            self.blocks.append(Block(self._text, self._starts))
        self._text = ""
        self._starts = []


def _skip_frontmatter(lines: List[str]) -> int:
    """YAML frontmatter の直後の行番号(0始まり)を返す。なければ 0。"""
    if not lines or lines[0].strip() != "---":
        return 0
    for index in range(1, len(lines)):
        if lines[index].strip() in ("---", "..."):
            return index + 1
    return 0


def split_lines(text: str) -> List[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def markdown_lines(lines: List[str]) -> Iterator[Tuple[int, Optional[str]]]:
    """YAML frontmatter より後の行を (行番号, 行) で返す。

    fenced code block と複数行の HTML コメントの中身は返さない。その始まりの位置を、
    段落の切れ目として (行番号, None) で返す。
    """
    fence_close: Optional[re.Pattern] = None
    in_comment = False

    for index in range(_skip_frontmatter(lines), len(lines)):
        raw = lines[index]
        number = index + 1

        if fence_close is not None:
            if fence_close.match(raw):
                fence_close = None
            continue
        if in_comment:
            if "-->" in raw:
                in_comment = False
            continue

        fence = FENCE_RE.match(raw)
        if fence:
            marker = fence.group(1)
            fence_close = re.compile(
                r"^\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$"
            )
            yield number, None
            continue
        if "<!--" in raw and "-->" not in raw.split("<!--", 1)[1]:
            in_comment = True
            yield number, None
            continue
        yield number, raw


def is_boundary_line(line: str) -> bool:
    """空行・水平線・コメント・リンク定義のように、文章を含まず段落を区切る行か。"""
    return bool(
        not line.strip()
        or RULE_RE.match(line)
        or SETEXT_RE.match(line)
        or COMMENT_LINE_RE.match(line)
        or LINK_DEFINITION_RE.match(line)
    )


def extract_blocks(text: str, markdown: bool = True) -> List[Block]:
    lines = split_lines(text)
    builder = _BlockBuilder()

    if not markdown:
        for index in range(_skip_frontmatter(lines), len(lines)):
            raw = lines[index]
            if not raw.strip():
                builder.flush()
            else:
                builder.add(index + 1, URL_RE.sub("", raw).strip())
        builder.flush()
        return builder.blocks

    for number, raw in markdown_lines(lines):
        if raw is None:
            builder.flush()
            continue

        line = QUOTE_RE.sub("", raw)
        if is_boundary_line(line) or HEADING_RE.match(line) or TABLE_ROW_RE.match(line):
            builder.flush()
            continue

        item = LIST_ITEM_RE.match(line)
        if item:
            builder.flush()
            line = TASK_BOX_RE.sub("", line[item.end():])
        builder.add(number, clean_inline(line))

    builder.flush()
    return builder.blocks


# --- 表示されない太字 -------------------------------------------------------
#
# CommonMark では、`**` のすぐ内側が記号で、すぐ外側が文字だと、`**` は太字の区切りに
# ならず、そのまま表示される。日本語では「**「用語」**を」「**必須です。**次に」で起きやすい。
# 何を記号とみなすかは実装で違う。GitHub(cmark-gfm)は Unicode の P(句読点)だけを、
# CommonMark 0.31 に従う実装(pandoc など)は S(★ などの記号)も記号とみなす。
# どちらか一方でも表示されないものを拾う。

_ASCII_PUNCTUATION = frozenset("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
_PUNCTUATION_CATEGORIES = ("P", "PS")  # 記号とみなす Unicode の大分類。GitHub、CommonMark 0.31 の順
CODE_SPAN_RE = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)", re.S)
STRONG_DELIMITER_RE = re.compile(r"(?<!\*)\*\*(?!\*)")


def _is_space(ch: str) -> bool:
    return ch in "\t\n\f\r" or unicodedata.category(ch) == "Zs"


def _is_punctuation(ch: str, categories: str) -> bool:
    return ch in _ASCII_PUNCTUATION or unicodedata.category(ch)[0] in categories


def _can_open(before: str, after: str, categories: str) -> bool:
    """CommonMark の left-flanking。"""
    if _is_space(after):
        return False
    return (not _is_punctuation(after, categories)
            or _is_space(before) or _is_punctuation(before, categories))


def _can_close(before: str, after: str, categories: str) -> bool:
    """CommonMark の right-flanking。"""
    if _is_space(before):
        return False
    return (not _is_punctuation(before, categories)
            or _is_space(after) or _is_punctuation(after, categories))


def _strong_renders(text: str, opener: int, closer: int) -> bool:
    def char(index: int) -> str:
        return text[index] if 0 <= index < len(text) else " "  # 行の端は空白とみなす

    return all(
        _can_open(char(opener - 1), char(opener + 2), categories)
        and _can_close(char(closer - 1), char(closer + 2), categories)
        for categories in _PUNCTUATION_CATEGORIES
    )


def _inline_units(lines: List[str]) -> Iterator[List[Tuple[int, str]]]:
    """太字が続きうる範囲(段落、リストの1項目、見出し、表の1行)ごとに、(行番号, 行) の一覧を返す。"""
    unit: List[Tuple[int, str]] = []
    for number, raw in markdown_lines(lines):
        line = None if raw is None else QUOTE_RE.sub("", raw)
        if line is None or is_boundary_line(line):
            if unit:
                yield unit
            unit = []
            continue
        single_line = bool(HEADING_RE.match(line) or TABLE_ROW_RE.match(line))
        if single_line or LIST_ITEM_RE.match(line):
            if unit:
                yield unit
            unit = []
        if single_line:
            yield [(number, line)]
        else:
            unit.append((number, line))
    if unit:
        yield unit


def find_unrendered_bold(text: str) -> List[Tuple[int, int, str]]:
    """太字にならず `**` がそのまま表示される箇所を、(行番号, 長さ, 切り出し) の一覧で返す。

    `**` を出現順に2つずつ対にして調べる。対にならない最後の `**` と、`*` の個数が2でない
    区切り(`*` や `***`)は調べない。インラインコードの中は除く。
    """
    found: List[Tuple[int, int, str]] = []
    for unit in _inline_units(split_lines(text)):
        text_of_unit = "\n".join(line for _, line in unit)
        line_offsets = list(itertools.accumulate(len(line) + 1 for _, line in unit))
        # 長さを変えずに、コードの中身とエスケープした `*` を区切りの判定から外す。
        masked = CODE_SPAN_RE.sub(lambda m: m.group(1) + "0" * len(m.group(2)) + m.group(1), text_of_unit)
        masked = masked.replace("\\*", "\\\\")
        delimiters = [m.start() for m in STRONG_DELIMITER_RE.finditer(masked)]
        for opener, closer in zip(delimiters[0::2], delimiters[1::2]):
            if _strong_renders(masked, opener, closer):
                continue
            line = unit[bisect.bisect_right(line_offsets, opener)][0]
            snippet = make_snippet(text_of_unit.replace("\n", " "), opener, closer + 2)
            found.append((line, closer + 2 - opener, snippet))
    return found


# --- 文の分割 ---------------------------------------------------------------

_OPENERS = "「『（(【〈《［["
_CLOSERS = "」』）)】〉》］]"
_TERMINATORS = "。！？．"
_ASCII_TERMINATORS = "!?"


def split_sentences(text: str) -> List[Tuple[int, str]]:
    """(開始位置, 文) の一覧を返す。括弧や引用の内側の句点では区切らない。"""
    sentences: List[Tuple[int, str]] = []
    length = len(text)
    start = 0
    depth = 0
    i = 0

    def emit(end: int) -> None:
        chunk = text[start:end]
        stripped = chunk.strip()
        if visible_length(stripped) > 0:
            sentences.append((start + (len(chunk) - len(chunk.lstrip())), stripped))

    while i < length:
        ch = text[i]
        ends_sentence = False
        if ch in _OPENERS:
            depth += 1
        elif ch in _CLOSERS:
            depth = max(0, depth - 1)
            # 「（…する。）」のように括弧の中で文が終わっている場合は、括弧の直後で区切る。
            if depth == 0 and ch in "）)" and i > start and text[i - 1] in _TERMINATORS:
                ends_sentence = True
        elif depth == 0:
            if ch in _TERMINATORS:
                ends_sentence = True
            elif ch in _ASCII_TERMINATORS and (i + 1 == length or text[i + 1].isspace()):
                ends_sentence = True
            elif ch == "." and i + 1 == length:
                ends_sentence = True
        if ends_sentence:
            j = i + 1
            while j < length and (text[j] in _TERMINATORS + _ASCII_TERMINATORS or text[j] in _CLOSERS):
                j += 1
            emit(j)
            start = j
            i = j
            depth = 0
            continue
        i += 1
    emit(length)
    return sentences


# --- 集計 -------------------------------------------------------------------


@dataclass
class Candidate:
    path: str
    line: int
    length: int
    preview: str

    def to_dict(self) -> dict:
        return {"file": self.path, "line": self.line, "length": self.length, "preview": self.preview}


@dataclass
class Metrics:
    chars: int = 0
    kanji: int = 0
    hiragana: int = 0
    paragraphs: int = 0
    long_paragraphs: int = 0
    sentences: int = 0
    sentence_chars: int = 0
    long_sentences: int = 0
    commas: int = 0

    def add(self, other: "Metrics") -> None:
        for name in self.__dataclass_fields__:
            setattr(self, name, getattr(self, name) + getattr(other, name))

    def to_dict(self) -> dict:
        def ratio(numerator: float, denominator: float, digits: int) -> float:
            return round(numerator / denominator, digits) if denominator else 0.0

        return {
            "chars": self.chars,
            "kanji_ratio": ratio(self.kanji, self.chars, 4),
            "hiragana_ratio": ratio(self.hiragana, self.chars, 4),
            "paragraphs": self.paragraphs,
            "avg_paragraph_length": ratio(self.chars, self.paragraphs, 1),
            "long_paragraphs": self.long_paragraphs,
            "sentences": self.sentences,
            "avg_sentence_length": ratio(self.sentence_chars, self.sentences, 1),
            "long_sentences": self.long_sentences,
            "commas_per_sentence": ratio(self.commas, self.sentences, 2),
        }


@dataclass
class FileResult:
    path: str
    metrics: Metrics = field(default_factory=Metrics)
    long_paragraphs: List[Candidate] = field(default_factory=list)
    long_sentences: List[Candidate] = field(default_factory=list)
    extras: Dict[str, List[Candidate]] = field(
        default_factory=lambda: {kind: [] for kind in EXTRA_KINDS}
    )


def make_preview(text: str) -> str:
    collapsed = " ".join(text.split())
    if len(collapsed) > PREVIEW_LENGTH:
        return collapsed[:PREVIEW_LENGTH] + "…"
    return collapsed


def analyze_text(
    text: str,
    path: str = "<text>",
    markdown: bool = True,
    paragraph_threshold: int = PARAGRAPH_THRESHOLD,
    sentence_threshold: int = SENTENCE_THRESHOLD,
    extras: bool = False,
) -> FileResult:
    result = FileResult(path=path)
    metrics = result.metrics
    for block in extract_blocks(text, markdown=markdown):
        length = visible_length(block.text)
        metrics.paragraphs += 1
        metrics.chars += length
        metrics.kanji += sum(1 for ch in block.text if is_kanji(ch))
        metrics.hiragana += sum(1 for ch in block.text if is_hiragana(ch))
        if length >= paragraph_threshold:
            metrics.long_paragraphs += 1
            result.long_paragraphs.append(
                Candidate(path, block.first_line, length, make_preview(block.text))
            )
        for offset, sentence in split_sentences(block.text):
            sentence_length = visible_length(sentence)
            metrics.sentences += 1
            metrics.sentence_chars += sentence_length
            metrics.commas += sentence.count("、") + sentence.count("，")
            if sentence_length >= sentence_threshold:
                metrics.long_sentences += 1
                result.long_sentences.append(
                    Candidate(path, block.line_at(offset), sentence_length, make_preview(sentence))
                )
            if extras:
                for kind, pattern in EXTRA_PATTERNS:
                    for match in pattern.finditer(sentence):
                        result.extras[kind].append(
                            Candidate(path, block.line_at(offset + match.start()), len(match.group()),
                                      make_snippet(sentence, match.start(), match.end()))
                        )
    if extras and markdown:
        result.extras[UNRENDERED_BOLD] = [
            Candidate(path, line, length, snippet) for line, length, snippet in find_unrendered_bold(text)
        ]
    return result


# --- 入力 -------------------------------------------------------------------


def expand_inputs(arguments: Iterable[str]) -> Tuple[List[str], List[str]]:
    """引数を、ファイルの一覧とエラーの一覧へ展開する。"""
    paths: List[str] = []
    errors: List[str] = []
    seen = set()

    def add(path: str) -> None:
        if path not in seen:
            seen.add(path)
            paths.append(path)

    for argument in arguments:
        if argument == "-":
            add(argument)
        elif os.path.isdir(argument):
            for found in _walk_directory(argument):
                add(found)
        elif os.path.exists(argument):
            add(argument)
        elif any(char in argument for char in "*?["):
            matches = sorted(glob.glob(argument, recursive=True))
            files = [m for m in matches if os.path.isfile(m)]
            if not files:
                errors.append(f"no files match: {argument}")
            for match in files:
                add(match)
        else:
            errors.append(f"not found: {argument}")
    return paths, errors


def _walk_directory(root: str) -> Iterator[str]:
    for current, directories, files in os.walk(root):
        directories[:] = sorted(d for d in directories if d not in SKIPPED_DIRECTORIES)
        for name in sorted(files):
            if name.lower().endswith(DIRECTORY_SUFFIXES):
                yield os.path.join(current, name)


def read_text(path: str) -> str:
    if path == "-":
        return sys.stdin.buffer.read().decode("utf-8-sig")
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8-sig")


def is_markdown_path(path: str, mode: str) -> bool:
    if mode == "markdown":
        return True
    if mode == "plain":
        return False
    return path == "-" or path.lower().endswith(MARKDOWN_SUFFIXES)


# --- 出力 -------------------------------------------------------------------


def format_percent(value: float) -> str:
    return f"{value * 100:.1f}"


def format_single(result: FileResult, thresholds: Tuple[int, int]) -> str:
    m = result.metrics.to_dict()
    return "\n".join(
        [
            result.path,
            f"  chars: {m['chars']}  kanji: {format_percent(m['kanji_ratio'])}%  "
            f"hiragana: {format_percent(m['hiragana_ratio'])}%",
            f"  paragraphs: {m['paragraphs']}  avg-length: {m['avg_paragraph_length']}  "
            f">={thresholds[0]}: {m['long_paragraphs']}",
            f"  sentences: {m['sentences']}  avg-length: {m['avg_sentence_length']}  "
            f">={thresholds[1]}: {m['long_sentences']}  "
            f"commas/sentence: {m['commas_per_sentence']}",
        ]
    )


def format_table(results: List[FileResult], total: FileResult, thresholds: Tuple[int, int]) -> str:
    header = ["file", "chars", "kanji%", "hira%", "para", "avgP", f"P>={thresholds[0]}",
              "sent", "avgS", f"S>={thresholds[1]}", "comma/s"]
    rows = [header]
    for result in results + [total]:
        m = result.metrics.to_dict()
        rows.append(
            [
                result.path,
                str(m["chars"]),
                format_percent(m["kanji_ratio"]),
                format_percent(m["hiragana_ratio"]),
                str(m["paragraphs"]),
                str(m["avg_paragraph_length"]),
                str(m["long_paragraphs"]),
                str(m["sentences"]),
                str(m["avg_sentence_length"]),
                str(m["long_sentences"]),
                str(m["commas_per_sentence"]),
            ]
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    lines = []
    for row in rows:
        cells = [row[0].ljust(widths[0])] + [row[i].rjust(widths[i]) for i in range(1, len(row))]
        lines.append("  ".join(cells))
    return "\n".join(lines)


def select_candidates(candidates: List[Candidate], limit: int) -> Tuple[List[Candidate], int]:
    """長い順に limit 件を選び、ファイル・行の順に並べ直す。省いた件数も返す。"""
    if limit <= 0 or len(candidates) <= limit:
        return sorted(candidates, key=lambda c: (c.path, c.line)), 0
    longest = sorted(candidates, key=lambda c: -c.length)[:limit]
    return sorted(longest, key=lambda c: (c.path, c.line)), len(candidates) - limit


def format_locate(results: List[FileResult], limit: int, thresholds: Tuple[int, int]) -> str:
    lines: List[str] = []
    for label, kind, threshold in (
        ("long paragraphs", "paragraph", thresholds[0]),
        ("long sentences", "sentence", thresholds[1]),
    ):
        candidates = [
            c
            for r in results
            for c in (r.long_paragraphs if kind == "paragraph" else r.long_sentences)
        ]
        shown, omitted = select_candidates(candidates, limit)
        lines.append(f"{label} (>={threshold} chars): {len(candidates)}")
        for c in shown:
            lines.append(f"  {c.path}:{c.line}  {kind}  {c.length}  {c.preview}")
        if omitted:
            lines.append(f"  ... {omitted} more not shown (use --max-locate 0 for all)")
    return "\n".join(lines)


def format_extras(results: List[FileResult], limit: int) -> str:
    lines = ["pointers (info only, not verdicts):"]
    for kind in EXTRA_KINDS:
        candidates = [c for r in results for c in r.extras[kind]]
        shown, omitted = select_candidates(candidates, limit)
        lines.append(f"{EXTRA_LABELS[kind]}: {len(candidates)}")
        for c in shown:
            lines.append(f"  {c.path}:{c.line}  {kind}  {c.length}  {c.preview}")
        if omitted:
            lines.append(f"  ... {omitted} more not shown (use --max-locate 0 for all)")
    return "\n".join(lines)


def build_json(results: List[FileResult], total: FileResult, locate: bool,
               paragraph_threshold: int, sentence_threshold: int, extras: bool = False) -> dict:
    files = []
    for result in results:
        entry = {"file": result.path, **result.metrics.to_dict()}
        if locate:
            entry["long_paragraph_candidates"] = [c.to_dict() for c in result.long_paragraphs]
            entry["long_sentence_candidates"] = [c.to_dict() for c in result.long_sentences]
        if extras:
            entry["pointers"] = {kind: [c.to_dict() for c in items] for kind, items in result.extras.items()}
        files.append(entry)
    return {
        "thresholds": {"paragraph": paragraph_threshold, "sentence": sentence_threshold},
        "files": files,
        "total": total.metrics.to_dict(),
    }


# --- CLI --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="measure.py",
        description=(
            "日本語文章の長さの指標を測り、長い段落と長い文の位置を示す(読み取り専用)。"
            f"{PARAGRAPH_THRESHOLD}字以上の段落と{SENTENCE_THRESHOLD}字以上の文は、"
            "合否の基準ではなく修正候補の目安である。"
        ),
        epilog="例: measure.py --locate docs/*.md / measure.py --json README.md / cat a.md | measure.py -",
    )
    parser.add_argument("paths", nargs="+", metavar="PATH",
                        help="ファイル、ディレクトリ(.md/.markdown/.txt を再帰的に探す)、ワイルドカード、標準入力の -")
    parser.add_argument("--locate", action="store_true",
                        help="長い段落と長い文の位置(ファイル名・行番号・長さ・冒頭)を示す")
    parser.add_argument("--extras", action="store_true",
                        help=f"連続漢字({KANJI_RUN_THRESHOLD}字以上)、名詞+「の」の{NO_CHAIN_COUNT}連、二重否定、"
                             "表示されない太字を指摘として挙げる。判定ではない")
    parser.add_argument("--json", action="store_true", help="JSON で出力する(--locate と --extras の候補は全件)")
    parser.add_argument("--max-locate", type=int, default=DEFAULT_MAX_LOCATE, metavar="N",
                        help=f"--locate で表示する件数の上限(段落・文それぞれ)。0 で無制限。既定 {DEFAULT_MAX_LOCATE}")
    parser.add_argument("--para-threshold", type=int, default=PARAGRAPH_THRESHOLD, metavar="N",
                        help=f"長い段落の閾値(字)。既定 {PARAGRAPH_THRESHOLD}")
    parser.add_argument("--sent-threshold", type=int, default=SENTENCE_THRESHOLD, metavar="N",
                        help=f"長い文の閾値(字)。既定 {SENTENCE_THRESHOLD}")
    parser.add_argument("--format", choices=("auto", "markdown", "plain"), default="auto",
                        help="Markdown として解析するか。auto は拡張子で判断する。既定 auto")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    thresholds = (args.para_threshold, args.sent_threshold)

    paths, errors = expand_inputs(args.paths)
    results: List[FileResult] = []
    for path in paths:
        try:
            text = read_text(path)
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
            continue
        display = "<stdin>" if path == "-" else path
        results.append(
            analyze_text(text, display, is_markdown_path(path, args.format),
                         args.para_threshold, args.sent_threshold, extras=args.extras)
        )

    for message in errors:
        print(f"error: {message}", file=sys.stderr)

    total = FileResult(path="TOTAL")
    for result in results:
        total.metrics.add(result.metrics)

    if results:
        if args.json:
            payload = build_json(results, total, args.locate, args.para_threshold, args.sent_threshold,
                                 extras=args.extras)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            if len(results) == 1:
                print(format_single(results[0], thresholds))
            else:
                print(format_table(results, total, thresholds))
            if args.locate:
                print(format_locate(results, args.max_locate, thresholds))
            if args.extras:
                print(format_extras(results, args.max_locate))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
