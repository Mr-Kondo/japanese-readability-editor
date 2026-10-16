#!/usr/bin/env python3
"""公開文書の評価データ台帳（manifest）を検証する。通信・書き込みなし。

    python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json
    python3 tools/validate_public_corpus.py --manifest M --cases cases.json --split tuning

台帳は出典・利用条件・原本ハッシュ・変換履歴・保持要件・理解問題・調整用/最終評価用の分割を持つ。
このツールは台帳の形式と整合性だけを検査する。保持要件や理解問題の意味的な正しさ、利用条件の解釈、
抜粋と原本の一致は人が確認する。件数は報告するが、統計的な十分性の根拠にはしない。

終了コード: 0=検査に合格、1=台帳または cases に不備あり、2=入力を読めない。
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import comprehension_readability as comprehension

SHA256 = re.compile(r"[0-9a-f]{64}")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SPLITS = ("tuning", "final")
EXCERPT_STATUSES = ("candidate", "adopted", "excluded")
ROLES = ("change_target", "no_change_control")
PRESERVE_KINDS = ("claim", "condition", "exception", "actor", "number", "deadline", "deliverable", "strength", "function")
STRENGTHS = ("normative", "informative")
REDISTRIBUTION = ("allowed", "restricted", "unknown")
COLLECTED_SOURCE_FIELDS = ("title", "provider", "url", "version", "format")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def present(entry, name: str) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get(name), str) and bool(entry[name].strip())


def valid_date(value) -> bool:
    if not isinstance(value, str) or not ISO_DATE.fullmatch(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def check_license(label: str, license_entry, errors: list, *, body: bool) -> None:
    if not isinstance(license_entry, dict):
        errors.append(f"{label}: 利用条件がない")
        return
    for name in ("name", "url"):
        if not present(license_entry, name):
            errors.append(f"{label}: {name} がない")
    if not valid_date(license_entry.get("checked_on")):
        errors.append(f"{label}: checked_on は YYYY-MM-DD で記録する")
    if license_entry.get("redistribution") not in REDISTRIBUTION:
        errors.append(f"{label}: redistribution は {'/'.join(REDISTRIBUTION)} のいずれか")
    if body:
        for name in ("attribution", "modification_notice"):
            if not present(license_entry, name):
                errors.append(f"{label}: {name}（帰属・加工表示）がない")


def check_source(source, errors: list) -> None:
    label = f"source {source.get('id')!r}"
    if source.get("status") == "planned":
        return
    if source.get("status") != "collected":
        errors.append(f"{label}: status は planned/collected")
        return
    for name in COLLECTED_SOURCE_FIELDS:
        if not present(source, name):
            errors.append(f"{label}: {name} がない")
    if not valid_date(source.get("retrieved_on")):
        errors.append(f"{label}: retrieved_on は YYYY-MM-DD で記録する")
    if not isinstance(source.get("raw_sha256"), str) or not SHA256.fullmatch(source["raw_sha256"]):
        errors.append(f"{label}: raw_sha256 は小文字64桁の16進数")
    licenses = source.get("license")
    licenses = licenses if isinstance(licenses, dict) else {}
    check_license(f"{label} 本文の利用条件", licenses.get("body"), errors, body=True)
    check_license(f"{label} 書誌情報の利用条件", licenses.get("bibliographic"), errors, body=False)


def check_history(label: str, excerpt: dict, source: dict, errors: list) -> None:
    history = excerpt.get("transform_history")
    if not isinstance(history, list) or not history:
        errors.append(f"{label}: transform_history（抽出・処理の履歴）がない")
        return
    steps_ok = all(isinstance(step, dict) and present(step, "step") and present(step, "tool")
                   and all(isinstance(step.get(k), str) and SHA256.fullmatch(step[k]) for k in ("input_sha256", "output_sha256"))
                   for step in history)
    if not steps_ok:
        errors.append(f"{label}: 履歴の各段階に step/tool と64桁の input_sha256/output_sha256 が必要")
        return
    if history[0]["input_sha256"] != source.get("raw_sha256"):
        errors.append(f"{label}: 履歴の最初の入力が原本の raw_sha256 と一致しない")
    for before, after in zip(history, history[1:]):
        if before["output_sha256"] != after["input_sha256"]:
            errors.append(f"{label}: 履歴が連続していない（{after['step']} の入力が直前の出力と異なる）")
    if history[-1]["output_sha256"] != excerpt.get("text_sha256"):
        errors.append(f"{label}: 履歴の最後の出力が text_sha256 と一致しない")


def check_preserve(label: str, excerpt: dict, errors: list) -> None:
    items = excerpt.get("preserve")
    if not isinstance(items, list) or not items:
        errors.append(f"{label}: 保持要件（preserve）が空")
        return
    for index, item in enumerate(items, 1):
        where = f"{label} preserve[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{where}: オブジェクトではない")
            continue
        if item.get("kind") not in PRESERVE_KINDS:
            errors.append(f"{where}: kind は {'/'.join(PRESERVE_KINDS)} のいずれか")
        if item.get("strength") is not None and item["strength"] not in STRENGTHS:
            errors.append(f"{where}: strength は {'/'.join(STRENGTHS)} または省略")
        if not present(item, "quote") or item["quote"] not in excerpt["text"]:
            errors.append(f"{where}: quote が抜粋に含まれない")
        for name in ("confirmed_by", "reason"):
            if not present(item, name):
                errors.append(f"{where}: {name} がない（人の確認を記録する）")
        allowed = item.get("allowed_changes")
        if not isinstance(allowed, list) or any(not isinstance(s, str) or not s.strip() for s in allowed):
            errors.append(f"{where}: allowed_changes は空でない文字列の配列（変更なしなら空配列）")


def check_questions(label: str, excerpt: dict, errors: list) -> None:
    questions = excerpt.get("questions", [])
    if not isinstance(questions, list):
        errors.append(f"{label}: questions は配列")
        return
    ids = []
    for index, question in enumerate(questions, 1):
        try:
            comprehension.checked_question(question, excerpt["text"])
            ids.append(question["id"])
        except ValueError as error:
            errors.append(f"{label} questions[{index}]: {error}")
    if len(set(ids)) != len(ids):
        errors.append(f"{label}: 理解問題の id が重複している")


def check_excerpt(excerpt, sources: dict, errors: list) -> None:
    label = f"excerpt {excerpt.get('id')!r}"
    status = excerpt.get("status")
    if status not in EXCERPT_STATUSES:
        errors.append(f"{label}: status は {'/'.join(EXCERPT_STATUSES)} のいずれか")
        return
    source = sources.get(excerpt.get("source_id"))
    if source is None:
        errors.append(f"{label}: source_id が台帳にない")
        return
    if source.get("status") != "collected":
        errors.append(f"{label}: 出典 {source['id']!r} が collected でない（未収集の出典から抜粋を作らない）")
        return
    if status == "excluded" and "text" not in excerpt:
        # 除外した抜粋は、理由と所在（locator）だけを残してよい。本文を再配布しない。
        if not present(excerpt, "exclusion_reason") or not present(excerpt, "locator"):
            errors.append(f"{label}: 除外には exclusion_reason と locator が必要")
        return
    if not present(excerpt, "text") or excerpt.get("text_sha256") != sha256_text(excerpt["text"]):
        errors.append(f"{label}: text が空、または text_sha256 と一致しない")
        return
    body = (source.get("license") or {}).get("body") or {}
    if body.get("redistribution") != "allowed":
        errors.append(f"{label}: 本文の再配布が allowed でない出典の本文を台帳へ入れない")
    check_history(label, excerpt, source, errors)
    if status == "excluded":
        if not present(excerpt, "exclusion_reason"):
            errors.append(f"{label}: 除外理由（exclusion_reason）がない")
        return
    if status == "candidate":
        return
    if excerpt.get("split") not in SPLITS:
        errors.append(f"{label}: split は {'/'.join(SPLITS)} のいずれか")
    if excerpt.get("role") not in ROLES:
        errors.append(f"{label}: role は {'/'.join(ROLES)} のいずれか")
    elif excerpt["role"] == "no_change_control" and not present(excerpt, "no_change_reason"):
        errors.append(f"{label}: 変更不要の対照例には no_change_reason が必要")
    if excerpt.get("third_party_content") != "none":
        errors.append(f"{label}: third_party_content が none でない（第三者の引用・図表を含む抜粋は採用しない）")
    if not present(excerpt, "locator"):
        errors.append(f"{label}: 抜粋範囲（locator）がない")
    correspondence = excerpt.get("correspondence")
    if not (present(correspondence, "checked_by") and isinstance(correspondence, dict) and valid_date(correspondence.get("checked_on"))):
        errors.append(f"{label}: 原本との対応の確認者（checked_by）と確認日（checked_on）がない")
    check_preserve(label, excerpt, errors)
    check_questions(label, excerpt, errors)


def check_splits(excerpts: list, sources: dict, errors: list) -> None:
    lineages, hashes = {}, {}
    for excerpt in excerpts:
        source = sources.get(excerpt.get("source_id"), {})
        lineage = source.get("lineage_id") or source.get("id")
        lineages.setdefault(lineage, set()).add(excerpt.get("split"))
        hashes.setdefault(excerpt.get("text_sha256"), set()).add(excerpt.get("split"))
    for lineage, splits in sorted(lineages.items()):
        if len(splits) > 1:
            errors.append(f"分割漏れ: 系列 {lineage!r} の抜粋が調整用と最終評価用の両方にある")
    for digest, splits in hashes.items():
        if len(splits) > 1:
            errors.append(f"分割漏れ: 同一本文（{str(digest)[:12]}…）が調整用と最終評価用の両方にある")


def check_manifest(manifest) -> tuple:
    errors = []
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        return ["schema_version が 1 の台帳ではない"], {}
    groups, sources, excerpts = manifest.get("groups"), manifest.get("sources"), manifest.get("excerpts")
    if not isinstance(groups, dict) or not isinstance(sources, list) or not isinstance(excerpts, list):
        return ["groups（オブジェクト）、sources、excerpts（配列）が必要"], {}
    by_id = {}
    for source in sources:
        if not (isinstance(source, dict) and present(source, "id") and present(source, "title") and present(source, "url")):
            errors.append("source には id/title/url が必要")
            continue
        if source["id"] in by_id:
            errors.append(f"source id が重複: {source['id']!r}")
        if source.get("group") not in groups:
            errors.append(f"source {source['id']!r}: group が groups にない")
        by_id[source["id"]] = source
        check_source(source, errors)
    seen = set()
    for excerpt in excerpts:
        if not isinstance(excerpt, dict) or not present(excerpt, "id"):
            errors.append("excerpt には id が必要")
            continue
        if excerpt["id"] in seen:
            errors.append(f"excerpt id が重複: {excerpt['id']!r}")
        seen.add(excerpt["id"])
        check_excerpt(excerpt, by_id, errors)
    adopted = [e for e in excerpts if isinstance(e, dict) and e.get("status") == "adopted"]
    check_splits(adopted, by_id, errors)
    return errors, report_for(groups, by_id, excerpts, adopted)


def report_for(groups: dict, sources: dict, excerpts: list, adopted: list) -> dict:
    report = {"descriptive_only": "件数は運用上の出発点であり、統計的十分性や効果の根拠ではない", "groups": {}}
    for name, config in groups.items():
        mine = [e for e in excerpts if isinstance(e, dict) and sources.get(e.get("source_id"), {}).get("group") == name]
        group_adopted = [e for e in mine if e in adopted]
        report["groups"][name] = {
            "target_excerpts": (config or {}).get("target_excerpts"),
            "sources": {s: sum(1 for x in sources.values() if x.get("group") == name and x.get("status") == s)
                        for s in ("planned", "collected")},
            "candidate": sum(e.get("status") == "candidate" for e in mine),
            "adopted": len(group_adopted),
            "excluded": [{"id": e["id"], "reason": e.get("exclusion_reason")} for e in mine if e.get("status") == "excluded"],
            "adopted_by_split": {s: sum(e.get("split") == s for e in group_adopted) for s in SPLITS},
            "adopted_by_source": {i: sum(e.get("source_id") == i for e in group_adopted)
                                  for i in sorted({e.get("source_id") for e in group_adopted})},
            "adopted_by_role": {r: sum(e.get("role") == r for e in group_adopted) for r in ROLES},
            "adopted_without_questions": [e["id"] for e in group_adopted if not e.get("questions")],
        }
    return report


def check_cases(manifest: dict, cases_document, split: str, document_id_by: str) -> tuple:
    """cases JSON の各 original が、指定した分割の採用済み抜粋と一致するか検査する。"""
    errors = []
    cases = cases_document.get("cases") if isinstance(cases_document, dict) else None
    if not isinstance(cases, list) or not cases:
        return ["cases が空、または配列でない"], {}
    adopted = {e["text_sha256"]: e for e in manifest["excerpts"] if e.get("status") == "adopted"}
    sources = {s["id"]: s for s in manifest["sources"]}
    sources_used, missing_generation = {}, 0
    for case in cases:
        label = f"case {case.get('id') if isinstance(case, dict) else case!r}"
        if not isinstance(case, dict):
            errors.append(f"{label}: オブジェクトではない")
            continue
        excerpt = adopted.get(sha256_text(case["original"])) if isinstance(case.get("original"), str) else None
        if excerpt is None:
            errors.append(f"{label}: original が台帳の採用済み抜粋と一致しない（原文を直さず台帳の text を使う）")
            continue
        if excerpt["split"] != split:
            errors.append(f"{label}: 抜粋 {excerpt['id']!r} は {excerpt['split']} 用で、{split} の入力に混ぜられない")
        expected = excerpt["source_id"] if document_id_by == "source" else excerpt["id"]
        if case.get("document_id") != expected:
            errors.append(f"{label}: document_id は {expected!r} にする（--document-id-by {document_id_by}）")
        for name in ("request", "audience"):
            if not present(case, name):
                errors.append(f"{label}: {name} を記録する")
        provenance = case.get("provenance")
        if not (present(provenance, "model") and present(provenance, "skill_version")):
            missing_generation += 1
        sources_used.setdefault(excerpt["source_id"], []).append(excerpt["id"])
    if document_id_by == "excerpt":
        for source_id, ids in sorted(sources_used.items()):
            if len(set(ids)) > 1:
                errors.append(f"理解問題の入力は1出典につき1抜粋まで: {source_id!r} に {sorted(set(ids))}（独立文書として数えない）")
    ids = [c.get("id") for c in cases if isinstance(c, dict)]
    if len(set(ids)) != len(ids):
        errors.append("case id が重複している")
    return errors, {"cases": len(cases), "sources": len(sources_used), "split": split,
                    "cases_without_model_or_skill_version": missing_generation,
                    "source_titles": {i: sources[i]["title"] for i in sources_used}}


def adoption_blockers(manifest: dict) -> dict:
    """candidate を adopted とみなして検査し、採用までに残る不備（主に人の確認）を抜粋ごとに返す。"""
    sources = {s["id"]: s for s in manifest["sources"] if isinstance(s, dict) and "id" in s}
    blockers = {}
    for excerpt in manifest["excerpts"]:
        if isinstance(excerpt, dict) and excerpt.get("status") == "candidate":
            errors = []
            check_excerpt({**excerpt, "status": "adopted"}, sources, errors)
            blockers[excerpt["id"]] = [e.split(": ", 1)[1] for e in errors]
    return blockers


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True, help="公開文書の台帳 JSON")
    parser.add_argument("--cases", type=Path, help="既存CLIへ渡す cases JSON。台帳との一致と分割を検査する")
    parser.add_argument("--split", choices=SPLITS, help="--cases に混ぜてよい分割（--cases では必須）")
    parser.add_argument("--readiness", action="store_true", help="candidate を採用するまでに残る不備（人の確認）を一覧する。終了コードには影響しない")
    parser.add_argument("--document-id-by", choices=("source", "excerpt"), default="source",
                        help="document_id の単位。比較・統計は source、理解問題は excerpt（既定 source）")
    args = parser.parse_args(argv)
    if bool(args.cases) != bool(args.split):
        parser.error("--cases と --split は一緒に指定する")
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        cases = json.loads(args.cases.read_text(encoding="utf-8")) if args.cases else None
    except (OSError, ValueError) as error:
        print(f"corpus check failed: {error}", file=sys.stderr)
        return 2
    errors, report = check_manifest(manifest)
    if args.readiness and not errors:
        report["adoption_blockers"] = adoption_blockers(manifest)
    if args.cases and not errors:
        case_errors, case_report = check_cases(manifest, cases, args.split, args.document_id_by)
        errors += case_errors
        report["cases"] = case_report
    for error in errors:
        print(f"NG: {error}", file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
