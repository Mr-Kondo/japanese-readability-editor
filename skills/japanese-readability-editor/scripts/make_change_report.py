#!/usr/bin/env python3
"""Skill で書き換えた前後の変化を、本文を含まない選択式の記録(JSON)として標準出力に出す。読み取り専用。

    make_change_report.py --original before.md --result after.md --mode B --model NAME > change-report.json
    make_change_report.py ... --review numbers=ok --review style=problem --reviewed-by human

compare_rewrite.py と measure.py の結果を、決まった選択肢だけに直して出す。原文・結果・引用・行番号・
ファイル名・パス・件数は出さない(official-prompt-tailor の private_feedback.py の方式)。
ファイルの書き込みも通信もしない。出した JSON を、利用者が内容を確かめて自分で保存する。

各検査の状態(status)と方法(method):
    no_candidate   deterministic   スクリプトが照合の候補を挙げなかった
    candidate      deterministic   候補が挙がった。正しい言い換えも拾うので、問題とは限らない
    ok / problem   human           人が元の文と見比べて、問題なし / 問題ありと確かめた
    ok / problem   model_self_report   生成したモデル自身の申告。改善の証拠にしない

保証しないこと: 候補がないことは、意味が保たれたことの証明ではない。記録は申告であり、
メンテナーの確認前は確認済みの変化ではない。総合点や改善率は出さない。

終了コード: 0=出した、2=入力の誤りで出さなかった。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

sys.dont_write_bytecode = True  # 読み込むスクリプトのために、skill の中へ __pycache__ を作らない
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_rewrite  # noqa: E402
import measure  # noqa: E402
import skill_info  # noqa: E402

SCHEMA_VERSION = 1
KIND = "jre-change-report"
MODES = ("A", "B", "C", "D", "unknown")
ORIGINS = ("model_output", "artificial", "unknown")
MODALITY_MARKERS = ("conjecture", "ability", "obligation", "request", "invitation", "emphasis", "limit", "residual")
# 検査の名前。メンテナー側の集計も、この表を正本として読む。
CHECKS: Dict[str, str] = {
    "numbers": "数値・単位が消えた、または増えた",
    "urls": "URL が消えた、または増えた",
    "code": "コードが消えた、または増えた",
    "terms": "英数字・カタカナの語が消えた、または新しく出た",
    "added_content": "書き換え後に、対応する元の文がない文がある(原文にない情報の候補)",
    "omitted_content": "元の文に、対応する書き換え後の文がない(脱落の候補)",
    "negation": "否定の表現が増えた、または減った",
    "modality": "推量・可能・義務・依頼・勧誘・強調・限定・残余の条件の表現が増えた、または減った",
    "style": "敬体と常体の多い方が変わった",
}
DIRECTIONS = ("removed", "added", "changed")
METRICS = {"chars": "文字数", "long_paragraphs": "長い段落", "long_sentences": "長い文", "short_runs": "短い文の連続"}
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9._:/-]{1,64}$")  # 自由記述を通さない


def candidate_directions(result: dict) -> Dict[str, List[str]]:
    """compare_documents の結果を、検査ごとの方向(removed / added / changed)に直す。件数と本文は持たない。"""
    def pair(missing: list, added: list) -> List[str]:
        return [name for name, items in (("removed", missing), ("added", added)) if items]

    def marker_change(kinds) -> List[str]:
        found = set()
        for kind in kinds:
            data = result["markers"][kind]
            found.update(pair(data["removed"], data["added"]))
            found.update(("removed",) if data["after"] < data["before"] else ())
            found.update(("added",) if data["after"] > data["before"] else ())
        return [name for name in DIRECTIONS if name in found]

    found = {kind: pair(result[kind]["missing"], result[kind]["added"]) for kind in ("numbers", "urls", "code", "terms")}
    found["added_content"] = ["added"] if result["unmatched"]["after"] else []
    found["omitted_content"] = ["removed"] if result["unmatched"]["before"] else []
    found["negation"] = marker_change(("negation",))
    found["modality"] = marker_change(MODALITY_MARKERS)
    found["style"] = ["changed"] if result["style"]["changed"] else []
    return found


def direction_of(before: int, after: int) -> str:
    return "decreased" if after < before else "increased" if after > before else "same"


def parse_reviews(values: List[str], reviewed_by: str, found: Dict[str, List[str]]) -> Dict[str, str]:
    reviews: Dict[str, str] = {}
    if values and not reviewed_by:
        raise ValueError("--review には --reviewed-by(human か model)が必要")
    for value in values:
        check, _, verdict = value.partition("=")
        if check not in CHECKS or verdict not in ("ok", "problem"):
            raise ValueError("--review は 検査名=ok または 検査名=problem の形(検査名は --help の一覧)")
        if not found[check]:
            raise ValueError(f"--review {check}: 候補が挙がっていない検査には付けられない")
        if check in reviews:
            raise ValueError(f"--review {check}: 同じ検査を2回指定した")
        reviews[check] = verdict
    return reviews


def build(args: argparse.Namespace) -> dict:
    model = args.model.strip() or "unknown"
    if not MODEL_PATTERN.match(model):
        raise ValueError("--model は英数字と . _ : / - だけの64字まで(自由記述は通さない)")
    before_text, after_text = measure.read_text(args.original), measure.read_text(args.result)
    if not before_text.strip() or not after_text.strip():
        raise ValueError("原文か結果が空")
    markdown = measure.is_markdown_path(args.original, "auto")
    analyzer = compare_rewrite.load_analyzer("auto")
    result = compare_rewrite.compare_documents(
        compare_rewrite.parse_document(before_text, args.original, markdown, analyzer),
        compare_rewrite.parse_document(after_text, args.result, markdown, analyzer), analyzer.name)
    found = candidate_directions(result)
    reviews = parse_reviews(args.review, args.reviewed_by, found)
    method = {"human": "human", "model": "model_self_report"}.get(args.reviewed_by, "")
    checks = {}
    for check in CHECKS:
        if check in reviews:
            checks[check] = {"status": reviews[check], "method": method, "direction": found[check]}
        else:
            checks[check] = {"status": "candidate" if found[check] else "no_candidate", "method": "deterministic",
                             "direction": found[check]}
    before, after = (measure.analyze_text(text, markdown=markdown).metrics for text in (before_text, after_text))
    record = skill_info.build_record({}, model)  # 環境変数を渡さない: アプリ名や版は記録しない
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND, "case_id": str(uuid.uuid4()),
        "evidence_status": "reported_not_independently_verified",
        "context": {"mode": args.mode, "origin": args.origin, "skill_version": record["skill_version"], "model": model,
                    "os": record["os"]["system"], "tokenizer": analyzer.name, "date": record["date"]},
        "checks": checks,
        "readability": {name: direction_of(getattr(before, name), getattr(after, name)) for name in METRICS},
    }


def use_utf8_output() -> None:
    """標準出力と標準エラーを UTF-8 にする(cp932 の Windows で、日本語の通知が文字化け・異常終了しないように)。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)  # IDLE や閉じた標準出力には無い、または失敗する。そのときは何もしない
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="backslashreplace")
            except (ValueError, OSError):
                pass


def main(argv: Optional[List[str]] = None) -> int:
    use_utf8_output()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--original", required=True, help="スキルに渡す前の文章のファイル")
    parser.add_argument("--result", required=True, help="スキルが返した文章のファイル")
    parser.add_argument("--mode", choices=MODES, default="unknown")
    parser.add_argument("--origin", choices=ORIGINS, default="model_output", help="実際のモデル出力か、人工例か")
    parser.add_argument("--model", default="", help="実行しているモデル名(環境から分からないので、実行する側が渡す)")
    parser.add_argument("--review", action="append", default=[], metavar="CHECK=ok|problem",
                        help="候補が挙がった検査を、元の文と見比べた結果。検査名: " + " / ".join(f"{k}={v}" for k, v in CHECKS.items()))
    parser.add_argument("--reviewed-by", choices=("human", "model"), help="--review を付けた主体。モデルの申告は改善の証拠にならない")
    args = parser.parse_args(argv)
    try:
        report = build(args)
    except (ValueError, OSError, UnicodeDecodeError) as error:
        print(f"make_change_report failed: {error}", file=sys.stderr)
        return 2
    print("確認: 標準出力の JSON をファイルに保存し、内容を確かめてから送る。本文は含まれない。", file=sys.stderr)
    sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
