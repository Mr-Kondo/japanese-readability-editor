#!/usr/bin/env python3
"""小説原稿の字数・括弧・任意の指定文字列を調べる読み取り専用の補助検査。

入力は UTF-8 のまま読む。BOM、空白、CR、LF も各1コードポイントに数える。
見た目の1文字(書記素クラスタ)は複数コードポイントになり得るため算出しない。
位置は1始まりの行・コードポイント列。CRLF は1改行、単独 CR/LF も1改行。
任意設定は {"forbidden": ["避ける表記"], "required": ["必要な文字列"]}。
大文字小文字を区別する正規化なしの部分文字列一致で、重なる出現も数える。
required は入力ファイルごとに1回以上の出現を要求し、不在の位置は null。
入力と設定を変更せず、API・LLM・ネットワークは使わない。
意味保存・文体・伏線・視点・全編整合性・文学的品質は保証しない。
終了コード: 0=候補なし、1=候補あり、2=引数・読み込み・設定の失敗。
JSON スキーマ version 1: tool, status, exit_code, definitions, settings, files, summary, errors。
"""

from __future__ import annotations

import argparse
from bisect import bisect_right
import json
from pathlib import Path
import re
import sys
from typing import List, Optional, Sequence

SCHEMA_VERSION = 1
EXIT_OK, EXIT_CANDIDATES, EXIT_FAILED = 0, 1, 2
BRACKET_PAIRS = {
    "(": ")", "[": "]", "{": "}", "（": "）", "［": "］", "｛": "｝",
    "「": "」", "『": "』", "【": "】", "〈": "〉", "《": "》", "〔": "〕", "〖": "〗",
}
CLOSE_TO_OPEN = {closing: opening for opening, closing in BRACKET_PAIRS.items()}
NEWLINES = re.compile(r"\r\n|\r|\n")
DEFINITIONS = {
    "character_count": "Unicodeコードポイント数。UTF-8で読んだBOM・空白・CR・LFを含む。CRLFは2コードポイント。",
    "visual_character_limit": "結合文字・絵文字列など、見た目の1文字とコードポイント数は一致しない。書記素クラスタ数は算出しない。",
    "whitespace_count": "Python str.isspace() が真となるコードポイント数。改行を含む。",
    "locations": "行・列は1始まり。列はコードポイント数。CRLFは1改行、単独CR/LFも1改行。他のUnicode区切り文字は改行に数えない。",
    "literal_match": "大文字小文字を区別する正規化なしの完全な部分文字列一致。重なる出現も数える。requiredは各ファイルで1回以上。",
    "brackets": "認識する括弧: " + " ".join(a + b for a, b in BRACKET_PAIRS.items()) + "。複数行と入れ子を検査。引用やコードも対象。",
    "limits": "候補は自動修正しない。文学上の意図や独自記法を考慮して人が確認する。意味保存・人物の同一性・文体・伏線・視点・全編の整合性・小説の品質は保証しない。",
}


class UsageError(ValueError):
    """argparse の失敗を JSON にも出力するための例外。"""


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise UsageError(message)


def read_input(path: str) -> str:
    """改行と BOM を除去・正規化せず UTF-8 として読み込む。"""
    data = sys.stdin.buffer.read() if path == "-" else Path(path).read_bytes()
    return data.decode("utf-8")


def validate_settings(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("設定は JSON オブジェクトで指定してください")
    unknown = set(value) - {"forbidden", "required"}
    if unknown:
        raise ValueError("未対応の設定キー: " + ", ".join(repr(key) for key in sorted(unknown, key=repr)))
    result = {"forbidden": [], "required": []}
    for key in result:
        items = value.get(key, [])
        if not isinstance(items, list) or any(not isinstance(item, str) or not item for item in items):
            raise ValueError(f"{key} は空でない文字列の配列で指定してください")
        try:
            for item in items:
                item.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{key} は UTF-8 で表せる Unicode 文字列にしてください") from exc
        if len(set(items)) != len(items):
            raise ValueError(f"{key} に重複した文字列があります")
        result[key] = items
    return result


def read_settings(path: str) -> dict:
    value = json.loads(Path(path).read_bytes().decode("utf-8-sig"))
    return validate_settings(value)


def line_starts(text: str) -> List[int]:
    return [0] + [match.end() for match in NEWLINES.finditer(text)]


def location(index: int, starts: List[int]) -> dict:
    line = bisect_right(starts, index)
    return {"line": line, "column": index - starts[line - 1] + 1}


def candidate(file: str, check_id: str, index: Optional[int], starts: List[int],
              text: str, message: str, **details) -> dict:
    position = location(index, starts) if index is not None else {"line": None, "column": None}
    return {"file": file, **position, "check_id": check_id, "text": text,
            "message": message, "details": details}


def bracket_candidates(text: str, file: str, starts: List[int]) -> List[dict]:
    findings: List[dict] = []
    stack = []
    for index, char in enumerate(text):
        if char in BRACKET_PAIRS:
            stack.append((char, index))
        elif char in CLOSE_TO_OPEN:
            matching = next((i for i in range(len(stack) - 1, -1, -1)
                             if stack[i][0] == CLOSE_TO_OPEN[char]), None)
            if matching is None:
                findings.append(candidate(file, "FICTION-BRACKET-UNEXPECTED", index, starts, char,
                                          "対応する開き括弧が見つかりません", expected_open=CLOSE_TO_OPEN[char]))
            else:
                if matching != len(stack) - 1:
                    top, top_index = stack[-1]
                    findings.append(candidate(file, "FICTION-BRACKET-ORDER", index, starts, char,
                                              "入れ子の括弧が閉じる順序を確認してください", expected_close=BRACKET_PAIRS[top],
                                              opening={"text": top, **location(top_index, starts)}))
                # 交差は対応する開始だけを消費し、後続を検査する。
                del stack[matching]
    for char, index in stack:
        findings.append(candidate(file, "FICTION-BRACKET-UNCLOSED", index, starts, char,
                                  "対応する閉じ括弧が見つかりません", expected_close=BRACKET_PAIRS[char]))
    return findings


def literal_positions(text: str, needle: str):
    offset = 0
    while True:
        index = text.find(needle, offset)
        if index < 0:
            return
        yield index
        offset = index + 1


def analyze_text(text: str, file: str, settings: Optional[dict] = None) -> dict:
    settings = validate_settings({} if settings is None else settings)
    starts = line_starts(text)
    findings = bracket_candidates(text, file, starts)
    for needle in settings["forbidden"]:
        for index in literal_positions(text, needle):
            findings.append(candidate(file, "FICTION-STRING-FORBIDDEN", index, starts, needle,
                                      "作品設定で避けるよう指定された文字列が見つかりました", match="exact_unicode_substring"))
    for needle in settings["required"]:
        if needle not in text:
            findings.append(candidate(file, "FICTION-STRING-REQUIRED", None, starts, needle,
                                      "作品設定で必要と指定された文字列が、このファイルにありません",
                                      match="exact_unicode_substring", occurrences=0))
    findings.sort(key=lambda item: (item["line"] if item["line"] is not None else sys.maxsize,
                                    item["column"] if item["column"] is not None else sys.maxsize,
                                    item["check_id"], item["text"]))
    whitespace = sum(char.isspace() for char in text)
    return {"file": file, "counts": {"codepoints": len(text), "whitespace_codepoints": whitespace,
                                    "non_whitespace_codepoints": len(text) - whitespace,
                                    "newline_sequences": len(starts) - 1}, "candidates": findings}


def error(file: Optional[str], check_id: str, message: str, line: Optional[int] = None,
          column: Optional[int] = None) -> dict:
    return {"file": file, "line": line, "column": column, "check_id": check_id, "message": message}


def report(files: List[dict], errors: List[dict], settings: dict, settings_file: Optional[str]) -> dict:
    count = sum(len(item["candidates"]) for item in files)
    code = EXIT_FAILED if errors else EXIT_CANDIDATES if count else EXIT_OK
    return {"schema_version": SCHEMA_VERSION, "tool": "check_fiction.py",
            "status": "execution_failed" if errors else "candidates" if count else "no_candidates", "exit_code": code,
            "definitions": DEFINITIONS, "settings": {"file": settings_file, **settings}, "files": files,
            "summary": {"files_checked": len(files), "candidates": count, "errors": len(errors)}, "errors": errors}


def format_text(result: dict) -> str:
    lines = [f"字数の定義: {DEFINITIONS['character_count']}", DEFINITIONS["visual_character_limit"],
             "空白の定義: " + DEFINITIONS["whitespace_count"], "位置の定義: " + DEFINITIONS["locations"],
             "文字列照合: " + DEFINITIONS["literal_match"], DEFINITIONS["brackets"]]
    for item in result["files"]:
        counts = item["counts"]
        lines.append(f"{item['file']}:-:- [FICTION-COUNT] codepoints={counts['codepoints']}, "
                     f"whitespace_codepoints={counts['whitespace_codepoints']}, "
                     f"non_whitespace_codepoints={counts['non_whitespace_codepoints']}, "
                     f"newline_sequences={counts['newline_sequences']}")
        for finding in item["candidates"]:
            row = finding["line"] if finding["line"] is not None else "-"
            col = finding["column"] if finding["column"] is not None else "-"
            lines.append(f"{finding['file']}:{row}:{col} [{finding['check_id']}] {finding['text']!r}: {finding['message']}")
    for item in result["errors"]:
        lines.append(f"{item['file'] or '<arguments>'}:{item['line'] or '-'}:{item['column'] or '-'} "
                     f"[{item['check_id']}] {item['message']}")
    lines.append(f"status: {result['status']}, exit {result['exit_code']}, "
                 f"candidates={result['summary']['candidates']}, errors={result['summary']['errors']}")
    lines.append(DEFINITIONS["limits"])
    return "\n".join(lines)


def emit(result: dict, as_json: bool) -> int:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_text(result), file=sys.stderr if result["errors"] else sys.stdout)
    return result["exit_code"]


def build_parser() -> argparse.ArgumentParser:
    parser = Parser(prog="check_fiction.py", allow_abbrev=False,
                    description="小説原稿の字数・括弧・指定文字列を調べる(読み取り専用、標準ライブラリのみ)。",
                    epilog="終了コード: 0=候補なし、1=候補あり、2=引数・入力・設定の失敗。候補なしでも小説の品質は保証しない。")
    parser.add_argument("paths", nargs="+", metavar="PATH", help="UTF-8の原稿ファイル。- で標準入力。ディレクトリは不可")
    parser.add_argument("--settings", metavar="FILE", help="任意の作品設定JSON。forbidden/required の文字列配列")
    parser.add_argument("--json", action="store_true", help="JSONスキーマ version 1 で出力する。失敗時もJSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    actual = list(sys.argv[1:] if argv is None else argv)
    empty = {"forbidden": [], "required": []}
    try:
        args = build_parser().parse_args(actual)
        if args.paths.count("-") > 1:
            raise UsageError("標準入力(-)は1回だけ指定できます")
    except UsageError as exc:
        return emit(report([], [error(None, "FICTION-CLI", str(exc))], empty, None), "--json" in actual)
    settings = empty
    if args.settings is not None:
        try:
            settings = read_settings(args.settings)
        except json.JSONDecodeError as exc:
            return emit(report([], [error(args.settings, "FICTION-SETTINGS-JSON", str(exc), exc.lineno, exc.colno)],
                               empty, args.settings), args.json)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            return emit(report([], [error(args.settings, "FICTION-SETTINGS", str(exc))], empty, args.settings), args.json)
    files: List[dict] = []
    errors: List[dict] = []
    for path in args.paths:
        filename = "<stdin>" if path == "-" else path
        try:
            files.append(analyze_text(read_input(path), filename, settings))
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(error(filename, "FICTION-INPUT-READ", str(exc)))
    return emit(report(files, errors, settings, args.settings), args.json)


if __name__ == "__main__":
    sys.exit(main())
