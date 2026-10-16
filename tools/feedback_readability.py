#!/usr/bin/env python3
"""匿名比較の確認記録を検証し、回帰ケースへ出力する。通信・自動改訂なし。"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_readability as comparison

review = comparison.review
CONTENT_FIELDS = ("request", "context", "audience", "original", "candidate")
DECISIONS = ("confirmed_problem", "no_problem", "unresolved")


def candidate_index(assignments: list) -> dict:
    indexed = []
    for assigned in assignments:
        candidates = {}
        for case in assigned["public"]["cases"]:
            mapping = assigned["mapping"][case["id"]]
            for side in comparison.SIDES:
                candidate = {k: review.text_field(case, k) for k in CONTENT_FIELDS if k != "candidate"}
                candidate.update(candidate=case[side], document_id=case["document_id"])
                key = (mapping["source_id"], mapping[side])
                if key in candidates:
                    raise ValueError("duplicate source candidate in organizer")
                candidates[key] = candidate
        indexed.append(candidates)
    if any(index != indexed[0] for index in indexed[1:]):
        raise ValueError("reviewers were assigned different source content")
    return indexed[0]


def decision_template(assignments: list) -> dict:
    entries = [{"source_id": source_id, "variant": variant, "input": candidate,
                "candidate_sha256": comparison.fingerprint(candidate), "status": "unresolved",
                "confirmer": "", "reason": "", "quote": "", "origin": "unknown",
                "preserve": [], "forbid": [], "rule_ids": []}
               for (source_id, variant), candidate in candidate_index(assignments).items()]
    return {"schema_version": 1, "organizer_sha256": comparison.fingerprint(assignments), "decisions": entries}


def text_list(entry: dict, name: str) -> list:
    values = entry.get(name)
    if not isinstance(values, list) or any(not isinstance(s, str) or not s.strip() for s in values):
        raise ValueError(f"{name} must be an array of non-empty strings")
    return values


def validate_decision(entry, candidate: dict) -> dict:
    if not {"confirmer", "reason", "quote"} <= entry.keys():
        raise ValueError("decision requires confirmer/reason/quote fields")
    if entry.get("input") != candidate or entry.get("candidate_sha256") != comparison.fingerprint(candidate):
        raise ValueError("decision content/hash does not match organizer")
    status = entry.get("status")
    if status not in DECISIONS or entry.get("origin") not in ("artificial", "model_output", "unknown"):
        raise ValueError("invalid decision status/origin")
    for name in ("preserve", "forbid", "rule_ids"):
        values = text_list(entry, name)
        if status == "confirmed_problem" and not values:
            raise ValueError("confirmed problem requires preserve/forbid/rule_ids")
    for name in ("confirmer", "reason", "quote"):
        review.text_field(entry, name, status != "unresolved")
    if entry["quote"] and entry["quote"] not in candidate["candidate"]:
        raise ValueError("decision quote must occur in candidate")
    return entry


def checked_decisions(document, assignments: list) -> dict:
    if not isinstance(document, dict) or document.get("schema_version") != 1 or document.get("organizer_sha256") != comparison.fingerprint(assignments):
        raise ValueError("decisions do not match organizer/schema")
    entries = document.get("decisions")
    if not isinstance(entries, list):
        raise ValueError("decisions must be an array")
    candidates, checked = candidate_index(assignments), {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid decision")
        key = (review.text_field(entry, "source_id", True), review.text_field(entry, "variant", True))
        if key not in candidates or key in checked:
            raise ValueError("unknown/duplicate decision candidate")
        checked[key] = validate_decision(entry, candidates[key])
    if checked.keys() != candidates.keys():
        raise ValueError("missing decisions; leave unresolved entries in place")
    return checked


def regression_suite(decisions: dict) -> dict:
    confirmed = [entry for entry in decisions.values() if entry["status"] != "unresolved"]
    cases, controls = [], []
    for index, entry in enumerate(confirmed, 1):
        candidate = entry["input"]
        metadata = {k: entry[k] for k in ("source_id", "variant", "candidate_sha256", "confirmer", "reason", "origin", "rule_ids", "quote")}
        controls.append({"id": f"feedback-control-{index:03}", "context": candidate["context"],
                         "text": candidate["original"], "candidate": candidate["candidate"],
                         "expected": "fail" if entry["status"] == "confirmed_problem" else "pass", "provenance": metadata})
        if entry["status"] == "confirmed_problem":
            cases.append({"id": f"feedback-{index:03}", "request": candidate["request"], "context": candidate["context"],
                          "text": candidate["original"], "domain": "確認済みフィードバック", "covers": entry["rule_ids"],
                          "preserve": entry["preserve"], "forbid": entry["forbid"], "expression": entry["reason"], "provenance": metadata})
    if not cases:
        raise ValueError("no confirmed problems to export; unresolved is not a failure")
    return {"schema_version": 1, "purpose": "開発用の確認済み回帰ケース。意味判定の自動化・未知文書の効果実証ではない。",
            "cases": cases, "controls": controls}


def save_output(folder: Path, filename: str, document: dict) -> None:
    folder.mkdir(parents=True, exist_ok=False)
    review.evaluation.save_json(folder / filename, document)


def matched_automatic_tasks(tasks: dict, assignments: list) -> dict:
    candidates, matched = candidate_index(assignments), {}
    for task in tasks["cases"]:
        provenance = task.get("provenance")
        if not isinstance(provenance, dict):
            raise ValueError("automatic task requires source_id/variant provenance")
        key = (review.text_field(provenance, "source_id", True), review.text_field(provenance, "variant", True))
        if task["mode"] != "B" or key not in candidates or key in matched:
            raise ValueError("unknown/duplicate automatic source candidate")
        if any(task[k] != candidates[key][k] for k in CONTENT_FIELDS):
            raise ValueError("automatic source content does not match human assignment")
        matched[key] = task
    if matched.keys() != candidates.keys():
        raise ValueError("automatic tasks must cover the same candidates")
    return matched


def calibration(assignments: list, decisions: dict, tasks: dict, answers: dict) -> dict:
    matched = matched_automatic_tasks(tasks, assignments)
    method, _ = review.validate_answer_header(answers, tasks)
    if method != "llm":
        raise ValueError("calibration requires LLM answers")
    judgments = {r["id"]: r for r in review.read_reviews(answers, {t["id"]: t for t in tasks["cases"]})}
    statuses = {"confirmed_problem": "fail", "no_problem": "pass", "unresolved": "uncertain"}
    rows = [{"source_id": key[0], "variant": key[1], "human": statuses[decisions[key]["status"]],
             "llm": judgments[task["id"]]["contract"] if task["id"] in judgments else "missing",
             "human_reason": decisions[key]["reason"], "llm_reason": judgments.get(task["id"], {}).get("reason", ""),
             "origin": decisions[key]["origin"]}
            for key, task in matched.items()]
    return calibration_summary(rows)


def calibration_summary(rows: list) -> dict:
    matrix = {human: dict(Counter(r["llm"] for r in rows if r["human"] == human)) for human in review.STATUSES}
    failures = [r for r in rows if r["human"] == "fail"]
    judged_failures = [r for r in failures if r["llm"] != "missing"]
    resolved_passes = [r for r in rows if r["llm"] == "pass" and r["human"] != "uncertain"]
    detected = sum(r["llm"] == "fail" for r in failures)
    false_passes = sum(r["human"] == "fail" for r in resolved_passes)
    return {"schema_version": 1, "confusion_matrix": matrix, "reference_failures": len(failures),
            "fail_detection_all_confirmed": fraction(detected, len(failures)),
            "fail_detection_judged": fraction(detected, len(judged_failures)),
            "false_pass_among_resolved_llm_pass": fraction(false_passes, len(resolved_passes)),
            "human_unresolved": sum(r["human"] == "uncertain" for r in rows),
            "llm_uncertain": sum(r["llm"] == "uncertain" for r in rows),
            "llm_missing": sum(r["llm"] == "missing" for r in rows), "candidates": len(rows), "qualitative": rows,
            "limits": "確認済み人手判定を参照。未解決は正解扱いしない。人工例の成績は運用時の誤り頻度ではない。選好・因果効果は比較しない。"}


def fraction(numerator: int, denominator: int) -> dict:
    return {"numerator": numerator, "denominator": denominator, "rate": numerator / denominator if denominator else None}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "export", "calibrate"))
    parser.add_argument("--organizer", type=Path, required=True)
    parser.add_argument("--decisions", type=Path)
    parser.add_argument("--tasks", type=Path)
    parser.add_argument("--llm-answers", type=Path)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    if bool(args.decisions) != (args.command != "prepare"):
        parser.error("--decisions is required for export/calibrate only")
    if any(bool(path) != (args.command == "calibrate") for path in (args.tasks, args.llm_answers)):
        parser.error("--tasks and --llm-answers are required for calibrate only")
    try:
        assignments = comparison.read_assignments(args.organizer)
        if args.command == "prepare":
            save_output(args.out_dir, "decisions.json", decision_template(assignments))
        else:
            decisions = checked_decisions(review.read_json(args.decisions), assignments)
            if args.command == "export":
                save_output(args.out_dir, "regression-cases.json", regression_suite(decisions))
            else:
                report = calibration(assignments, decisions, review.read_tasks(args.tasks), review.read_json(args.llm_answers))
                save_output(args.out_dir, "calibration.json", report)
                (args.out_dir / "calibration.md").write_text("# 人手とLLMの意味保持判定\n\n" + report["limits"] + "\n\n"
                    + json.dumps({k: v for k, v in report.items() if k != "qualitative"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"feedback failed: {error}", file=sys.stderr)
        return 2
    print(str(args.out_dir.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
