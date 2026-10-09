#!/usr/bin/env python3
"""国語の表記・用法の規則で文章を検査する。読み取り専用。ネットワークを使わない。

    check_kokugo.py document.md --profile general-tech
    check_kokugo.py document.md --profile official --json
    check_kokugo.py document.md --glossary glossary.txt

規則と根拠は data/ にある(文化庁の公式資料。出典・節・ページは kokugo-rules.json と
references/kokugo-sources.md)。入力のファイルは変更しない。

適用設定(--profile)。モード A/B/C とは独立している。
  general-tech         技術・業務文書(既定)。明確な誤りを確認し、専門用語・組織の表記・許容形を尊重する。
  public-explanation   一般向けの解説・案内・広報。読み手に応じた表記を検討する。
  official             公用文基準が明示された文書。公用文固有の表記・用語の運用も確認する。
文体が堅いという理由だけで official を選ばない。

指摘の区分(category)。
  error             適用条件と修正根拠が明確な誤り
  recommendation    選択した基準では推奨されるが、一般的な誤りとは限らない
  accepted_variant  許容される表記
  needs_context     意味・品詞・文脈の確認が必要
  excluded          保護対象(コード、URL、引用、frontmatter、除外指定、用語集の語)など、適用しない箇所
許容形や適用範囲外の表記を、誤り(error)として報告しない。文脈に依存する候補を、確定した誤りとして報告しない。

終了コード。
  0  検査を終え、--fail-on で指定した水準(既定は error)以上の指摘がない
  1  検査を終え、--fail-on で指定した水準以上の指摘がある
  2  引数・入力ファイル・用語集・規則データの不備で、検査を完了できなかった

保護するもの(Markdown): YAML frontmatter、fenced code block、インラインコード、URL とリンク先、
ブロッククォート、HTML コメントとタグ、<!-- kokugo-ignore-start --> から <!-- kokugo-ignore-end --> まで。
固有名詞・専門用語は自動では識別しない。--glossary に書いた語(protect:)と、kokugo-ignore で除外する。

--glossary の形式(UTF-8、1行に1語。# から始まる行はコメント)。
    protect: Kubernetes      この語に重なる箇所には規則を適用しない(固有名詞・専門用語)
    use: サーバ              組織が指定する表記。適用設定の推奨と食い違うときは、黙って片方を適用せず要確認にする
    Kubernetes               接頭辞がない行は protect: として扱う

このスクリプトは、意味の保存や日本語の正しさ全体を保証しない。検査していない項目は、出力の coverage に示す。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import measure  # noqa: E402  (入力の展開と Markdown 判定を共有する)
import kokugo_engine as engine  # noqa: E402

EXIT_OK, EXIT_FINDINGS, EXIT_INCOMPLETE = 0, 1, 2
FAIL_LEVELS: Dict[str, Tuple[str, ...]] = {
    "error": ("error",),
    "recommendation": ("error", "recommendation"),
    "needs_context": engine.FLAG_CATEGORIES,
    "never": (),
}
HIDDEN_BY_DEFAULT = ("accepted_variant", "excluded")


def read_input(path: str) -> Tuple[bytes, str]:
    if path == "-":
        data = sys.stdin.buffer.read()
    else:
        with open(path, "rb") as handle:
            data = handle.read()
    return data, data.decode("utf-8-sig")


def analyze_file(path: str, profile: str, ruleset: engine.RuleSet, glossary: Optional[engine.Glossary], fmt: str) -> dict:
    data, text = read_input(path)
    markdown = measure.is_markdown_path(path, fmt)
    findings = engine.check_text(text, profile, ruleset, markdown=markdown, glossary=glossary)
    return {
        "file": "<stdin>" if path == "-" else path,
        "sha256": engine.sha256_hex(data),
        "markdown": markdown,
        "findings": findings,
        "counts": engine.count_categories(findings),
    }


def build_report(files: List[dict], profile: str, ruleset: engine.RuleSet, glossary: Optional[engine.Glossary],
                 fail_on: str) -> dict:
    summary = {category: 0 for category in engine.CATEGORIES}
    for result in files:
        for category, count in result["counts"].items():
            summary[category] += count
    failing = sum(summary[category] for category in FAIL_LEVELS[fail_on])
    return {
        "schema_version": engine.SCHEMA_VERSION,
        "tool": "check_kokugo.py",
        "profile": profile,
        "rules_version": ruleset.version,
        "fail_on": fail_on,
        "exit_code": EXIT_FINDINGS if failing else EXIT_OK,
        "files": files,
        "summary": summary,
        "coverage": engine.coverage(ruleset, profile, glossary),
    }


def format_candidates(finding: dict) -> str:
    return f" → {' / '.join(finding['candidates'])}" if finding["candidates"] else ""


def format_text(report: dict, show_all: bool) -> str:
    lines: List[str] = []
    for result in report["files"]:
        shown = [f for f in result["findings"] if show_all or f["category"] not in HIDDEN_BY_DEFAULT]
        lines.append(f"{result['file']}  (profile: {report['profile']}, rules: {report['rules_version']})")
        if not shown:
            lines.append("  no findings to show")
        for finding in shown:
            lines.append(f"  {finding['line']}:{finding['column']}  [{finding['category']}]  {finding['rule_id']}  "
                         f"{finding['text']}{format_candidates(finding)}")
            count = finding["detail"].get("count")
            suffix = f"  ({count} 件)" if count and count > 1 else ""
            lines.append(f"      {finding['reason']}{suffix}")
            lines.append(f"      出典: {', '.join(finding['source_ids'])}  [{finding['provenance']}]")
    summary = report["summary"]
    lines.append("")
    lines.append("summary: " + " / ".join(f"{category} {summary[category]}" for category in engine.CATEGORIES))
    hidden = sum(summary[c] for c in HIDDEN_BY_DEFAULT)
    if hidden and not show_all:
        lines.append(f"({hidden} 件の accepted_variant / excluded は --all で表示)")
    coverage = report["coverage"]
    lines.append(f"coverage: {len(coverage['rules_checked'])} rules checked, "
                 f"{len(coverage['rules_reference_only'])} reference-only (not checked), tokenizer: {coverage['tokenizer']}")
    lines.append("not checked: " + "; ".join(coverage["not_checked"]))
    lines.append("limits: " + " / ".join(coverage["limits"]))
    lines.append(coverage["disclaimer"])
    return "\n".join(lines)


def format_rule_list(ruleset: engine.RuleSet) -> str:
    lines = ["id  automation  provenance  general-tech / public-explanation / official  title"]
    for rule in ruleset.rules:
        data = rule.data
        if data["automation"] == "detect":
            cats = " / ".join(data["profiles"][p]["category"] for p in engine.PROFILES)
        else:
            cats = "(reference only)"
        lines.append(f"{data['id']}  {data['automation']}  {data['provenance']}  {cats}  {data['title']}")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="check_kokugo.py",
        description="国語の表記・用法の規則で文章を検査する(読み取り専用、ネットワークなし)。判定の全体は保証しない。",
        epilog="終了コード: 0=指摘なし(--fail-on 未満のみ), 1=--fail-on 以上の指摘あり, 2=検査を完了できなかった。",
    )
    parser.add_argument("paths", nargs="*", metavar="PATH", help="ファイル、ディレクトリ(.md/.markdown/.txt を再帰的に探す)、ワイルドカード、標準入力の -")
    parser.add_argument("--profile", choices=engine.PROFILES, default=engine.DEFAULT_PROFILE,
                        help=f"適用設定。既定 {engine.DEFAULT_PROFILE}(モード A/B/C とは独立)")
    parser.add_argument("--json", action="store_true", help="JSON で出力する(形式は schema_version で固定。accepted_variant と excluded も全件)")
    parser.add_argument("--glossary", action="append", default=[], metavar="FILE", help="組織の用語集(protect: / use:)。複数指定できる")
    parser.add_argument("--fail-on", choices=tuple(FAIL_LEVELS), default="error",
                        help="終了コード 1 にする水準。既定 error。recommendation は error を含み、needs_context はすべての確認対象を含む。never は常に 0")
    parser.add_argument("--all", action="store_true", help="テキスト出力でも accepted_variant と excluded を表示する")
    parser.add_argument("--format", choices=("auto", "markdown", "plain"), default="auto",
                        help="Markdown として解析するか。auto は拡張子で判断する。既定 auto")
    parser.add_argument("--data-dir", type=Path, default=None, metavar="DIR", help="規則データのディレクトリ(既定は skill の data/)")
    parser.add_argument("--list-rules", action="store_true", help="規則の一覧(ID、自動判定の有無、設定ごとの区分)を表示して終了する")
    return parser


def load_glossary(names: Sequence[str]) -> Optional[engine.Glossary]:
    """用語集を読む。読めなければ OSError / UnicodeDecodeError(呼び出し側が終了コード 2 にする)。"""
    if not names:
        return None
    return engine.merge_glossaries([engine.parse_glossary(Path(name).read_text(encoding="utf-8")) for name in names])


def analyze_inputs(args: argparse.Namespace, ruleset: engine.RuleSet, glossary: Optional[engine.Glossary]) -> Tuple[List[dict], List[str]]:
    """入力を検査し、(ファイルごとの結果, エラーの一覧) を返す。読めないファイルがあっても、残りは検査する。"""
    paths, errors = measure.expand_inputs(args.paths)
    files: List[dict] = []
    for path in paths:
        try:
            files.append(analyze_file(path, args.profile, ruleset, glossary, args.format))
        except (OSError, UnicodeDecodeError) as exc:
            errors.append(f"cannot read {path}: {exc}")
    if not files and not errors:
        errors.append("no input files")
    return files, errors


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        ruleset = engine.load_rules(args.data_dir)
    except engine.RulesError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INCOMPLETE
    if args.list_rules:
        print(format_rule_list(ruleset))
        return EXIT_OK
    if not args.paths:
        print("error: no input paths (give files, directories or - for stdin)", file=sys.stderr)
        return EXIT_INCOMPLETE
    try:
        glossary = load_glossary(args.glossary)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"error: cannot read glossary: {exc}", file=sys.stderr)
        return EXIT_INCOMPLETE

    files, errors = analyze_inputs(args, ruleset, glossary)
    for message in errors:
        print(f"error: {message}", file=sys.stderr)
    report = build_report(files, args.profile, ruleset, glossary, args.fail_on)
    if errors:
        report["exit_code"] = EXIT_INCOMPLETE
    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_text(report, args.all))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
