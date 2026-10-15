#!/usr/bin/env python3
"""モードBの二候補を匿名配布し、候補別の意味保持と選好を集計する。"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import review_readability as review

RUBRIC = "readability-pair-v1"
SIDES = ("left", "right")
CATEGORIES = ("number", "condition", "negation", "actor", "speech_act", "omission", "addition", "style", "readability", "other")
SEVERITIES = ("minor", "major", "critical")


def fingerprint(document: dict) -> str:
    return review.evaluation.digest(json.dumps(document, ensure_ascii=False, sort_keys=True))


def read_pairs(path: Path) -> list:
    document = review.read_json(path)
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("unsupported pair input schema")
    entries = document.get("cases")
    if not isinstance(entries, list) or not entries:
        raise ValueError("cases must be a non-empty array")
    pairs = [validate_pair(entry) for entry in entries]
    if len({p["id"] for p in pairs}) != len(pairs):
        raise ValueError("duplicate pair id")
    if any(set(p["candidates"]) != set(pairs[0]["candidates"]) for p in pairs):
        raise ValueError("all pairs must compare the same two variants")
    return pairs


def validate_pair(entry) -> dict:
    if not isinstance(entry, dict) or entry.get("mode") != "B":
        raise ValueError("pair comparison supports explicit mode B only")
    candidates = entry.get("candidates")
    if not isinstance(candidates, dict) or len(candidates) != 2:
        raise ValueError("exactly two named candidates required")
    if any(not isinstance(name, str) or not name.strip() or name in ("tie", "uncertain") for name in candidates):
        raise ValueError("candidate names must be non-empty and not tie/uncertain")
    for candidate in candidates.values():
        review.validate_task({**entry, "candidate": candidate})
    return {**review.validate_task({**entry, "candidate": next(iter(candidates.values()))}), "candidates": candidates}


def assignment(pairs: list, reviewer_id: str) -> dict:
    # Repeated outputs of one document share orientation; independent documents are balanced.
    documents = list(dict.fromkeys(p["document_id"] for p in pairs))
    generator = random.SystemRandom()
    offset = generator.randrange(2)
    orientations = [(index + offset) % 2 for index in range(len(documents))]
    generator.shuffle(orientations)
    order = dict(zip(documents, orientations))
    public_cases, mapping = [], {}
    for index, pair in enumerate(pairs, 1):
        public_id = f"pair-{index:03}"
        variants = sorted(pair["candidates"])
        if order[pair["document_id"]]:
            variants.reverse()
        public_cases.append({"id": public_id, "document_id": f"doc-{documents.index(pair['document_id']) + 1:03}",
                             **{k: pair[k] for k in ("request", "audience", "context", "original")},
                             **dict(zip(SIDES, (pair["candidates"][name] for name in variants)))})
        mapping[public_id] = {"source_id": pair["id"], **dict(zip(SIDES, variants))}
    public = {"schema_version": 1, "rubric_version": RUBRIC, "reviewer": reviewer_id, "cases": public_cases}
    public["task_sha256"] = fingerprint(public)
    return {"public": public, "mapping": mapping}


def prepare(pairs: list, reviewers: list, folder: Path) -> None:
    if any(not name.strip() for name in reviewers) or len(set(reviewers)) != len(reviewers):
        raise ValueError("reviewers must be distinct, non-empty pseudonyms")
    assignments = [assignment(pairs, name) for name in reviewers]
    folder.mkdir(parents=True, exist_ok=False)
    organizer = {"schema_version": 1, "rubric_version": RUBRIC,
                 "created_at": datetime.now(timezone.utc).isoformat(), "source_sha256": fingerprint(pairs),
                 "assignments": assignments}
    review.evaluation.save_json(folder / "organizer.json", organizer)
    template = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
    for index, assigned in enumerate(assignments, 1):
        distribution = folder / f"reader-{index:03}"
        distribution.mkdir()
        payload = json.dumps(assigned["public"], ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
        (distribution / "review.html").write_text(template.replace("__TASK_DATA__", payload), encoding="utf-8")
        review.evaluation.save_json(distribution / "tasks.json", assigned["public"])


def validate_version(document) -> None:
    if not isinstance(document, dict) or document.get("schema_version") != 1 or document.get("rubric_version") != RUBRIC:
        raise ValueError("unsupported comparison schema/rubric")


def validate_assignment(assigned) -> dict:
    if not isinstance(assigned, dict):
        raise ValueError("invalid organizer assignment")
    public = assigned.get("public")
    validate_version(public)
    body = {k: v for k, v in public.items() if k != "task_sha256"}
    if public.get("task_sha256") != fingerprint(body):
        raise ValueError("assignment hash/rubric mismatch")
    review.text_field(public, "reviewer", True)
    cases = public.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("invalid assigned cases")
    mapping = assigned.get("mapping")
    if not isinstance(mapping, dict):
        raise ValueError("invalid private mapping")
    case_ids = [validate_assigned_case(case, mapping) for case in cases]
    if len(set(case_ids)) != len(cases) or set(mapping) != set(case_ids):
        raise ValueError("duplicate/invalid assigned cases")
    return assigned


def validate_assigned_case(case, mapping: dict) -> str:
    if not isinstance(case, dict):
        raise ValueError("invalid assigned case")
    for key in ("id", "document_id", "request", "original", *SIDES):
        review.text_field(case, key, True)
    pair_map = mapping.get(case["id"])
    if not isinstance(pair_map, dict):
        raise ValueError("missing private variant mapping")
    variants = [review.text_field(pair_map, side, True) for side in SIDES]
    if len(set(variants)) != 2 or any(name in ("tie", "uncertain") for name in variants):
        raise ValueError("invalid private variant names")
    return case["id"]


def read_assignments(path: Path) -> list:
    organizer = review.read_json(path)
    validate_version(organizer)
    assignments = organizer.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise ValueError("missing assignments")
    validated = [validate_assignment(a) for a in assignments]
    if len({a["public"]["reviewer"] for a in validated}) != len(validated):
        raise ValueError("duplicate assigned reviewer")
    variants = set(variant_names(validated[0]))
    for assigned in validated:
        if any(set(names) != variants for names in mapped_variants(assigned)):
            raise ValueError("inconsistent variants in organizer")
    return validated


def mapped_variants(assigned: dict) -> list:
    return [[pair_map[s] for s in SIDES] for pair_map in assigned["mapping"].values()]


def variant_names(assigned: dict) -> list:
    return sorted(mapped_variants(assigned)[0])


def validate_candidate(answer, candidate: str) -> dict:
    checked = review.validate_review({**answer, "preference": "uncertain"}, {"id": "candidate", "mode": "B"}) if isinstance(answer, dict) else None
    if checked is None:
        raise ValueError("invalid candidate review")
    issues = answer.get("issues", [])
    if not isinstance(issues, list):
        raise ValueError("issues must be an array")
    for issue in issues:
        if not isinstance(issue, dict) or issue.get("category") not in CATEGORIES or issue.get("severity") not in SEVERITIES:
            raise ValueError("invalid issue category/severity")
        quote = review.text_field(issue, "quote", True)
        if quote not in candidate:
            raise ValueError("issue quote must occur verbatim in candidate")
        review.text_field(issue, "reason", True)
    return {k: checked[k] for k in ("contract", "scores", "reason", "suggestion")} | {"issues": issues}


def validate_pair_review(answer, case: dict) -> dict:
    if not isinstance(answer, dict):
        raise ValueError("invalid pair review")
    candidates = {side: validate_candidate(answer.get(side), case[side]) for side in SIDES}
    preference = answer.get("preference")
    if preference not in (*SIDES, "tie", "uncertain"):
        raise ValueError("invalid pair preference")
    if any(c["contract"] != "pass" for c in candidates.values()) and preference != "uncertain":
        raise ValueError("preference requires both candidates to pass")
    return {"id": case["id"], **candidates, "preference": preference, "reason": review.text_field(answer, "reason", True)}


def read_answers(document, assigned: dict) -> list:
    public = assigned["public"]
    if not isinstance(document, dict) or any(document.get(k) != public[k] for k in ("schema_version", "rubric_version", "task_sha256", "reviewer")) or document.get("method") != "human":
        raise ValueError("answers do not match assigned reviewer/tasks/rubric")
    entries = document.get("reviews")
    if not isinstance(entries, list):
        raise ValueError("reviews must be an array")
    by_id = {c["id"]: c for c in public["cases"]}
    return checked_pair_reviews(entries, by_id)


def checked_pair_reviews(entries: list, by_id: dict) -> list:
    checked, seen = [], set()
    for entry in entries:
        pair_id = entry.get("id") if isinstance(entry, dict) else None
        if not isinstance(pair_id, str) or pair_id not in by_id or pair_id in seen:
            raise ValueError("unknown/duplicate pair review id")
        seen.add(pair_id)
        checked.append(validate_pair_review(entry, by_id[pair_id]))
    return checked


def aggregate(assignments: list, documents: list) -> dict:
    by_reviewer = {a["public"]["reviewer"]: a for a in assignments}
    completed = {}
    for document in documents:
        reviewer_id = document.get("reviewer") if isinstance(document, dict) else None
        if not isinstance(reviewer_id, str) or reviewer_id not in by_reviewer or reviewer_id in completed:
            raise ValueError("unknown/duplicate reviewer; use one latest answer file per reviewer")
        completed[reviewer_id] = read_answers(document, by_reviewer[reviewer_id])
    rows = [row for reviewer_id, assigned in by_reviewer.items() for row in mapped_reviews(assigned, completed.get(reviewer_id, []))]
    return comparison_summary(assignments, rows, len(completed))


def mapped_reviews(assigned: dict, answers: list) -> list:
    case_documents = {c["id"]: c["document_id"] for c in assigned["public"]["cases"]}
    rows = []
    for answer in answers:
        mapping = assigned["mapping"][answer["id"]]
        rows.append({**answer, "reviewer": assigned["public"]["reviewer"], "document_id": case_documents[answer["id"]],
                     "variants": {mapping[s]: answer[s] for s in SIDES},
                     "selected": mapping.get(answer["preference"], answer["preference"])})
    return rows


def comparison_summary(assignments: list, rows: list, responding_reviewers: int) -> dict:
    expected = sum(len(a["public"]["cases"]) for a in assignments)
    variants = variant_names(assignments[0])
    eligible = [r for r in rows if all(r[s]["contract"] == "pass" for s in SIDES)]
    return {"schema_version": 1, "rubric_version": RUBRIC, "method": "human", "assigned_reviewers": len(assignments),
            "assigned_documents": len({c["document_id"] for a in assignments for c in a["public"]["cases"]}),
            "responding_reviewers": responding_reviewers, "expected_reviews": expected, "completed_reviews": len(rows),
            "missing_reviews": expected - len(rows), "both_pass": len(eligible),
            "preference_among_both_pass": dict(Counter(r["selected"] for r in eligible)),
            "variants": {name: variant_summary(name, rows, expected) for name in variants}, "qualitative": rows,
            "limits": "割付全件を母数に欠測を記録。選好は両候補合格の票だけ。票は独立文書ではなく、理解率・効果量・因果効果は未測定。"}


def variant_summary(name: str, rows: list, expected: int) -> dict:
    reviews = [r["variants"][name] for r in rows]
    counts = Counter(r["contract"] for r in reviews)
    return {"contract_counts": dict(counts), "fail_rate_all_assignments": counts["fail"] / expected,
            "scores": {d: review.score_summary(reviews, d) for d in review.DIMENSIONS},
            "issues_by_category": dict(Counter(i["category"] for r in reviews for i in r["issues"]))}


def automatic_tasks(pairs: list) -> dict:
    cases = []
    for index, pair in enumerate(pairs, 1):
        for variant_index, (name, candidate) in enumerate(pair["candidates"].items(), 1):
            cases.append(review.validate_task({**pair, "id": f"pair-{index:03}-variant-{variant_index}",
                                               "candidate": candidate,
                                               "provenance": {"variant": name, "source_id": pair["id"], "generation": pair["provenance"]}}))
    tasks = {"schema_version": 1, "rubric_version": review.RUBRIC, "cases": cases}
    tasks["task_sha256"] = fingerprint(tasks)
    return tasks


def run_auto(pairs: list, args: argparse.Namespace) -> int:
    tasks = automatic_tasks(pairs)
    args.out_dir.mkdir(parents=True, exist_ok=False)
    review.evaluation.save_json(args.out_dir / "tasks.json", tasks)
    return review.run_auto(tasks, args.out_dir, args.judge)


def write_summary(folder: Path, summary: dict) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    review.evaluation.save_json(folder / "summary.json", summary)
    lines = ["# 匿名二候補の比較結果", "", summary["limits"], "",
             f"回答 {summary['completed_reviews']} / 割付 {summary['expected_reviews']}、欠測 {summary['missing_reviews']}。",
             f"両候補合格 {summary['both_pass']}。その中の選好：{summary['preference_among_both_pass']}。", ""]
    for name, statistics in summary["variants"].items():
        lines.extend(["> " + json.dumps({name: statistics}, ensure_ascii=False).replace("<", "&lt;"), ""])
    lines.extend(["候補別の引用・理由・修正案は summary.json の qualitative に保存しています。", ""])
    (folder / "summary.md").write_text("\n".join(lines), encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    creation = subparsers.add_parser("prepare")
    creation.add_argument("--input", type=Path, required=True)
    creation.add_argument("--reviewers", nargs="+", required=True, help="評価者の仮名ID。各評価者に全件を割当")
    automatic = subparsers.add_parser("auto")
    automatic.add_argument("--input", type=Path, required=True)
    automatic.add_argument("--judge", action="store_true", help="各候補をClaude CLIへ送信して個別採点（外部通信あり）")
    summary = subparsers.add_parser("summarize")
    summary.add_argument("--organizer", type=Path, required=True)
    summary.add_argument("--answers", type=Path, nargs="+", required=True)
    for command in (creation, automatic, summary):
        command.add_argument("--out-dir", type=Path, required=True, help="新規ディレクトリ。上書き禁止")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(read_pairs(args.input), args.reviewers, args.out_dir)
        elif args.command == "auto":
            return run_auto(read_pairs(args.input), args)
        else:
            write_summary(args.out_dir, aggregate(read_assignments(args.organizer), [review.read_json(p) for p in args.answers]))
    except (OSError, ValueError, RuntimeError) as error:
        print(f"comparison failed: {error}", file=sys.stderr)
        return 2
    print(str(args.out_dir.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
