#!/usr/bin/env python3
"""2つのファイルで、空白以外の文字列が同一であることを確認する。読み取り専用。

段落だけを分けた(改行と空行だけを挿入した)場合の検証に使う。

    verify_preservation.py before.md after.md

保証すること:
    空白(半角・全角スペース、タブ、改行など)を除いた文字列が、2つのファイルで
    完全に一致する。一致すれば終了コード 0、しなければ 1、読み込みなどの失敗は 2。

保証しないこと:
    意味の保存。空白の位置が意味を変える場合(英単語の間の空白など)や、コード
    ブロックの中の空白の変化は検出できない。これは「空白以外の文字が変更されて
    いないこと」だけを確かめる、機械的な検査である。

--strict を付けると、より厳しく確かめる(段落だけを分ける Paragraph-only モード向け)。
    改行以外のすべての文字(半角・全角スペース、タブ、不可分スペースを含む)が同一で、
    しかも改行が減っていない(挿入しかしていない)ときだけ、終了コード 0 を返す。
    既定の検査は空白全般を無視するため、空白やタブの置換・削除や、既存の改行の削除を
    見逃す。「改行と空行の挿入のみ」を確かめるときは、--strict を使う。
    改行コードの違い(CRLF と LF)は、改行の種類を変えただけなので区別しない。
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional, Tuple

CONTEXT_LENGTH = 20


def normalize(text: str) -> Tuple[str, List[int]]:
    """空白を除いた文字列と、各文字の元の行番号(1始まり)を返す。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    kept: List[str] = []
    lines: List[int] = []
    line = 1
    for ch in text:
        if ch == "\n":
            line += 1
        if not ch.isspace():
            kept.append(ch)
            lines.append(line)
    return "".join(kept), lines


def compare(before: str, after: str) -> dict:
    """比較結果を辞書で返す。identical が True なら空白以外の文字は同一。"""
    left, left_lines = normalize(before)
    right, right_lines = normalize(after)
    result = {
        "identical": left == right,
        "before_chars": len(left),
        "after_chars": len(right),
        "before_paragraphs": count_paragraphs(before),
        "after_paragraphs": count_paragraphs(after),
    }
    if left == right:
        return result

    limit = min(len(left), len(right))
    index = 0
    while index < limit and left[index] == right[index]:
        index += 1
    result["first_difference"] = {
        "position": index + 1,
        "before_line": left_lines[index] if index < len(left_lines) else None,
        "after_line": right_lines[index] if index < len(right_lines) else None,
        "before_context": left[max(0, index - CONTEXT_LENGTH): index + CONTEXT_LENGTH],
        "after_context": right[max(0, index - CONTEXT_LENGTH): index + CONTEXT_LENGTH],
    }
    return result


def split_newlines(text: str) -> Tuple[str, List[int], List[int]]:
    """改行を除いた文字列と、各位置の直前にあった改行の数(長さは文字数+1)、各文字の元の行番号を返す。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    kept: List[str] = []
    gaps: List[int] = [0]
    lines: List[int] = []
    line = 1
    for ch in text:
        if ch == "\n":
            gaps[-1] += 1
            line += 1
        else:
            kept.append(ch)
            lines.append(line)
            gaps.append(0)
    return "".join(kept), gaps, lines


def compare_strict(before: str, after: str) -> dict:
    """after が before に改行を挿入しただけかを調べる。

    改行以外の文字(空白とタブを含む)が同一で、どの位置でも改行の数が減っていないこと。
    """
    left, left_gaps, left_lines = split_newlines(before)
    right, right_gaps, right_lines = split_newlines(after)
    result = {
        "only_newlines_inserted": False,
        "non_newline_identical": left == right,
        "newlines_removed": False,
        "inserted_newlines": sum(right_gaps) - sum(left_gaps),
    }
    if left != right:
        limit = min(len(left), len(right))
        index = 0
        while index < limit and left[index] == right[index]:
            index += 1
        result["first_difference"] = {
            "position": index + 1,
            "before_line": left_lines[index] if index < len(left_lines) else None,
            "after_line": right_lines[index] if index < len(right_lines) else None,
            "before_context": repr(left[max(0, index - CONTEXT_LENGTH): index + CONTEXT_LENGTH]),
            "after_context": repr(right[max(0, index - CONTEXT_LENGTH): index + CONTEXT_LENGTH]),
        }
        return result
    for index, (old, new) in enumerate(zip(left_gaps, right_gaps)):
        if new < old:
            result["newlines_removed"] = True
            result["first_difference"] = {
                "position": index + 1,
                "before_line": left_lines[index] if index < len(left_lines) else None,
                "after_line": right_lines[index] if index < len(right_lines) else None,
                "before_context": repr(left[max(0, index - CONTEXT_LENGTH): index + CONTEXT_LENGTH]),
                "after_context": f"{old} line break(s) before this position became {new}",
            }
            return result
    result["only_newlines_inserted"] = True
    return result


def count_paragraphs(text: str) -> int:
    """空行で区切られた、空白以外を含む塊の数。"""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    count = 0
    in_paragraph = False
    for line in text.split("\n"):
        if line.strip():
            if not in_paragraph:
                count += 1
                in_paragraph = True
        else:
            in_paragraph = False
    return count


def read_file(path: str) -> str:
    if path == "-":
        return sys.stdin.buffer.read().decode("utf-8-sig")
    with open(path, "rb") as handle:
        return handle.read().decode("utf-8-sig")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="verify_preservation.py",
        description=(
            "2つのファイルの、空白を除いた文字列が一致するか確認する(読み取り専用)。"
            "段落だけを分けた場合の検証に使う。"
        ),
        epilog=(
            "終了コード: 0=一致, 1=不一致, 2=読み込みの失敗。--strict は、改行以外が同一で改行が減っていないときだけ 0。"
            "注意: このスクリプトが保証するのは「空白以外の文字列が変更されていないこと」だけである。"
            "意味の保存は保証しない。"
        ),
    )
    parser.add_argument("before", help="編集前のファイル。- で標準入力")
    parser.add_argument("after", help="編集後のファイル。- で標準入力")
    parser.add_argument("--json", action="store_true", help="結果を JSON で出力する")
    parser.add_argument("--strict", action="store_true",
                        help="改行以外のすべての文字(空白とタブを含む)が同一で、改行が減っていないことまで確かめる。"
                             "「改行と空行の挿入のみ」を確かめるときに使う")
    parser.add_argument("-q", "--quiet", action="store_true", help="出力せず、終了コードだけで結果を返す")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if args.before == "-" and args.after == "-":
        print("error: only one of the two files can be read from stdin", file=sys.stderr)
        return 2
    try:
        before = read_file(args.before)
        after = read_file(args.after)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = compare(before, after)
    if args.strict:
        result["strict"] = compare_strict(before, after)
    if args.strict and not args.quiet and not args.json:
        strict = result["strict"]
        if strict["only_newlines_inserted"]:
            print(f"OK (strict): only line breaks were inserted ({strict['inserted_newlines']} added); "
                  "every other character, including spaces and tabs, is identical")
        else:
            diff = strict["first_difference"]
            kind = "an existing line break was removed" if strict["newlines_removed"] else "a character other than a line break changed"
            print(f"FAIL (strict): {kind}")
            print(f"  at non-newline char #{diff['position']} (before line {diff['before_line']}, after line {diff['after_line']})")
            print(f"  before: {diff['before_context']}")
            print(f"  after : {diff['after_context']}")
        return 0 if strict["only_newlines_inserted"] else 1
    if not args.quiet:
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif result["identical"]:
            print(
                f"OK: non-whitespace characters are identical ({result['before_chars']} chars). "
                f"paragraphs: {result['before_paragraphs']} -> {result['after_paragraphs']}"
            )
        else:
            diff = result["first_difference"]
            print(
                f"FAIL: non-whitespace characters differ "
                f"(before {result['before_chars']} chars, after {result['after_chars']} chars)"
            )
            print(f"  first difference at non-whitespace char #{diff['position']} "
                  f"(before line {diff['before_line']}, after line {diff['after_line']})")
            print(f"  before: ...{diff['before_context']}...")
            print(f"  after : ...{diff['after_context']}...")
    if args.strict:
        return 0 if result["strict"]["only_newlines_inserted"] else 1
    return 0 if result["identical"] else 1


if __name__ == "__main__":
    sys.exit(main())
