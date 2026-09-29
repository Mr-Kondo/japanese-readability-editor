#!/usr/bin/env python3
"""日本語文章の長さに関する指標を測り、修正候補の位置を示す。読み取り専用。

段落は200字以上、文は80字以上を「修正候補」として数える。この数値は合否の基準では
なく、候補を見つけるための目安である。技術仕様や引用など、長いほうが正確な文章も
ある。数値を満たすためだけの機械的な分割はしない。

解析から可能な範囲で除くもの: fenced code block、YAML frontmatter、URL、Markdown の記号。
Markdown のリンクは表示テキストだけを残す。見出し・表・水平線も文章ではないので除く。
Markdown として扱うのは既定で拡張子が .md .markdown .mdx .mkd のファイルと標準入力である。

文の区切りは、句点・感嘆符・疑問符と括弧の対応から推定する。ASCII のピリオドでは区切らない。

ネットワーク通信、ファイルの書き込み、外部コマンドの実行は行わない。
"""

from __future__ import annotations

import argparse
import bisect
import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field
from typing import Iterable, Iterator, List, Optional, Tuple

PARAGRAPH_THRESHOLD = 200
SENTENCE_THRESHOLD = 80
DEFAULT_MAX_LOCATE = 20
PREVIEW_LENGTH = 30

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


def extract_blocks(text: str, markdown: bool = True) -> List[Block]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    builder = _BlockBuilder()
    fence_close: Optional[re.Pattern] = None
    in_comment = False

    for index in range(_skip_frontmatter(lines), len(lines)):
        raw = lines[index]
        number = index + 1

        if not markdown:
            if not raw.strip():
                builder.flush()
            else:
                builder.add(number, URL_RE.sub("", raw).strip())
            continue

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
            builder.flush()
            marker = fence.group(1)
            fence_close = re.compile(
                r"^\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$"
            )
            continue
        if "<!--" in raw and "-->" not in raw.split("<!--", 1)[1]:
            builder.flush()
            in_comment = True
            continue

        line = QUOTE_RE.sub("", raw)
        if (
            not line.strip()
            or HEADING_RE.match(line)
            or RULE_RE.match(line)
            or SETEXT_RE.match(line)
            or TABLE_ROW_RE.match(line)
            or COMMENT_LINE_RE.match(line)
            or LINK_DEFINITION_RE.match(line)
        ):
            builder.flush()
            continue

        item = LIST_ITEM_RE.match(line)
        if item:
            builder.flush()
            line = TASK_BOX_RE.sub("", line[item.end():])
        builder.add(number, clean_inline(line))

    builder.flush()
    return builder.blocks


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


def build_json(results: List[FileResult], total: FileResult, locate: bool,
               paragraph_threshold: int, sentence_threshold: int) -> dict:
    files = []
    for result in results:
        entry = {"file": result.path, **result.metrics.to_dict()}
        if locate:
            entry["long_paragraph_candidates"] = [c.to_dict() for c in result.long_paragraphs]
            entry["long_sentence_candidates"] = [c.to_dict() for c in result.long_sentences]
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
    parser.add_argument("--json", action="store_true", help="JSON で出力する(--locate の候補は全件)")
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
                         args.para_threshold, args.sent_threshold)
        )

    for message in errors:
        print(f"error: {message}", file=sys.stderr)

    total = FileResult(path="TOTAL")
    for result in results:
        total.metrics.add(result.metrics)

    if results:
        if args.json:
            payload = build_json(results, total, args.locate, args.para_threshold, args.sent_threshold)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            if len(results) == 1:
                print(format_single(results[0], thresholds))
            else:
                print(format_table(results, total, thresholds))
            if args.locate:
                print(format_locate(results, args.max_locate, thresholds))
    return 2 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
