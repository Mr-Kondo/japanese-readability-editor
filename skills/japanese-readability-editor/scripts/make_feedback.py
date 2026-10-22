#!/usr/bin/env python3
"""スキルの結果への問題報告(フィードバック票)を JSON として自動保存し、標準出力にも出す。

    make_feedback.py --original before.md --result after.md --type over_editing \\
        --quote "出力にある該当箇所" --consent-storage

既定では ~/.agents/feedback/japanese-readability-editor/ に新規保存する。
--out-dir で保存先を変えられる。通信はしない。保存した JSON を利用者が確かめて送る。

保証すること:
    引用が結果(または原文)に実在する。問題の種類が決まった値である。非公開の保管への
    同意がある。メールアドレス・URL・電話番号らしい文字列があれば、標準エラー出力に警告する。

保証しないこと:
    機密や個人情報が含まれないこと。警告は目安で、送る前に利用者が内容を確かめる。
    問題が実在すること。票は利用者の報告であり、メンテナーの確認前は確認済みの問題ではない。

終了コード: 0=保存して出力した、2=入力または保存の誤りで出力しなかった。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Dict, List, Optional

sys.dont_write_bytecode = True
from feedback_storage import save_report

SCHEMA_VERSION = 1
KIND = "jre-feedback"
CONSENT_VERSION = 1
MAX_CHARS = 100_000
MODES = ("A", "B", "C", "D", "unknown")
SEVERITIES = ("major", "minor", "unknown")
ORIGINS = ("model_output", "artificial", "unknown")
# 問題の種類。メンテナー側のツールも、この表を正本として読む。
PROBLEM_TYPES: Dict[str, str] = {
    "added_content": "原文にない主体・条件・完了状態・事実を足した",
    "strength_changed": "必須・推奨・断定・推量などの言い切りの強さが変わった",
    "number_or_negation": "数値・単位・範囲・否定の数が変わった",
    "meaning_lost": "情報・条件・例外が抜けた",
    "over_editing": "直さなくてよい箇所まで書き換えた",
    "unneeded_change": "変更が不要な文章を変えた",
    "unnatural": "不自然、または読みにくくなった",
    "other": "上のどれでもない",
}
PATTERNS = (
    ("メールアドレス", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")),
    ("URL", re.compile(r"https?://\S+")),
    ("電話番号らしい数字", re.compile(r"(?<![\d-])0\d{1,4}-\d{1,4}-\d{3,4}(?![\d-])")),
    ("長い数字列(番号・口座など)", re.compile(r"(?<!\d)\d{10,}(?!\d)")),
)


def read_text(path: str, label: str) -> str:
    try:
        with open(path, "rb") as handle:
            raw = handle.read(MAX_CHARS * 4 + 1)
        text = raw.decode("utf-8-sig")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"{label} を読めない: {error}")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ValueError(f"{label} が空")
    if len(text) > MAX_CHARS:
        raise ValueError(f"{label} が長すぎる(最大 {MAX_CHARS} 文字)。問題の箇所を含む範囲に絞る")
    return text


def sensitive_warnings(texts: Dict[str, str]) -> List[str]:
    found = []
    for label, text in texts.items():
        for name, pattern in PATTERNS:
            count = len(pattern.findall(text))
            if count:
                found.append(f"{label} に {name} らしい文字列が {count} 件ある。送る前に伏せるか、メールで送る")
    return found


def build(args: argparse.Namespace) -> dict:
    if not args.consent_storage:
        raise ValueError("--consent-storage が必要(非公開で保管し、スキル改良の検討に使うことへの同意)")
    original = read_text(args.original, "原文")
    result = read_text(args.result, "結果")
    quote = args.quote.strip()
    if not quote:
        raise ValueError("--quote が空")
    if quote in result:
        quote_in = "result"
    elif quote in original:
        quote_in = "original"
    else:
        raise ValueError("--quote が結果にも原文にもない。該当箇所をそのまま写す")
    comment = args.comment.strip()
    request = args.request.strip()
    if len(request) > 2000:
        raise ValueError("--request が長すぎる(最大 2000 文字)")
    if len(comment) > 2000:
        raise ValueError("--comment が長すぎる(最大 2000 文字)")
    return {
        "schema_version": SCHEMA_VERSION, "kind": KIND,
        "consent": {"version": CONSENT_VERSION, "storage": True,
                    "ai_processing": bool(args.consent_ai), "publish": bool(args.consent_publish)},
        "context": {"mode": args.mode, "origin": args.origin, "skill_version": args.skill_version.strip(),
                    "model": args.model.strip()},
        "case": {"original": original, "result": result, "problem_type": args.type, "quote": quote,
                 "quote_in": quote_in, "severity": args.severity, "comment": comment, **({"request": request} if request else {})},
    }


def use_utf8_output() -> None:
    """標準出力と標準エラーを UTF-8 にする。cp932 の Windows で、日本語や絵文字を含む出力が文字化け・異常終了しないようにする。"""
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
    parser.add_argument("--type", required=True, choices=sorted(PROBLEM_TYPES),
                        help="問題の種類: " + " / ".join(f"{k}={v}" for k, v in PROBLEM_TYPES.items()))
    parser.add_argument("--quote", required=True, help="問題の箇所。結果(欠落なら原文)からそのまま写す")
    parser.add_argument("--mode", choices=MODES, default="unknown")
    parser.add_argument("--origin", choices=ORIGINS, default="model_output", help="実際のモデル出力か、人工例か")
    parser.add_argument("--severity", choices=SEVERITIES, default="unknown")
    parser.add_argument("--comment", default="", help="任意。何が問題か、読者への影響")
    parser.add_argument("--request", default="", help="任意。スキルに出した依頼文(あれば回帰ケースの再現に使う)")
    parser.add_argument("--skill-version", default="", help="任意。分かる範囲の版")
    parser.add_argument("--model", default="", help="任意。分かる範囲のモデル名")
    parser.add_argument("--consent-storage", action="store_true",
                        help="必須。非公開で保管し、スキル改良の検討に使うことへの同意")
    parser.add_argument("--consent-ai", action="store_true", help="任意。AIサービスへの送信(改良案の下書き)への同意")
    parser.add_argument("--consent-publish", action="store_true",
                        help="任意。匿名化した上で、公開の回帰ケースなどへ使うことへの同意")
    parser.add_argument("--out-dir", help="保存先フォルダ(既定: ~/.agents/feedback/japanese-readability-editor/)")
    args = parser.parse_args(argv)
    try:
        document = build(args)
        saved = save_report(document, args.out_dir)
    except (ValueError, OSError) as error:
        print(f"make_feedback failed: {error}", file=sys.stderr)
        return 2
    for warning in sensitive_warnings({"原文": document["case"]["original"], "結果": document["case"]["result"],
                                       "コメント": document["case"]["comment"]}):
        print(f"warning: {warning}", file=sys.stderr)
    print("確認: 保存した JSON の内容を確かめてから送る。機密は GitHub Issue に貼らず、メールで送る。", file=sys.stderr)
    print(f"saved_to: {saved}", file=sys.stderr)
    sys.stdout.write(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
