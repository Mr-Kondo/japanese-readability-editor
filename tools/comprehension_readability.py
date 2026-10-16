#!/usr/bin/env python3
"""一つの版だけを読む理解問題の配布・採点。正解は主催者側に保持する。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_readability as comparison

review = comparison.review
RUBRIC = "readability-comprehension-v1"


def checked_question(question, original: str) -> dict:
    if not isinstance(question, dict):
        raise ValueError("invalid question")
    for name in ("id", "prompt", "evidence", "verified_by", "verification_reason"):
        review.text_field(question, name, True)
    options = question.get("options")
    if not isinstance(options, list) or len(options) < 2 or any(not isinstance(s, str) or not s.strip() for s in options):
        raise ValueError("question requires at least two non-empty options")
    if len(set(options)) != len(options):
        raise ValueError("duplicate question options")
    answer = question.get("answer_index")
    if type(answer) is not int or not 0 <= answer < len(options) or question["evidence"] not in original:
        raise ValueError("invalid answer index or evidence absent from original")
    return question


def read_source(path: Path) -> list:
    pairs = comparison.read_pairs(path)
    raw = review.read_json(path)
    for pair, entry in zip(pairs, raw["cases"]):
        pair["questions"] = checked_questions(entry.get("questions"), pair["original"])
    if len({p["document_id"] for p in pairs}) != len(pairs):
        raise ValueError("comprehension requires one generation per source document")
    return pairs


def checked_questions(questions, original: str) -> list:
    if not isinstance(questions, list) or not questions:
        raise ValueError("each document requires verified questions")
    checked = [checked_question(q, original) for q in questions]
    if len({q["id"] for q in checked}) != len(checked):
        raise ValueError("duplicate question id")
    return checked


def reader_assignment(pairs: list, base: dict, reader: str, side: str) -> dict:
    cases, mapping = [], {}
    for pair, assigned in zip(pairs, base["public"]["cases"]):
        variant = base["mapping"][assigned["id"]][side]
        questions = [{k: q[k] for k in ("id", "prompt", "options")} for q in pair["questions"]]
        cases.append({"id": assigned["id"], "document_id": assigned["document_id"],
                      "candidate": pair["candidates"][variant], "audience": pair["audience"], "questions": questions})
        mapping[assigned["id"]] = {"source_id": pair["id"], "variant": variant,
                                  "original": pair["original"], "candidate": pair["candidates"][variant], "questions": pair["questions"]}
    public = {"schema_version": 1, "rubric_version": RUBRIC, "reviewer": reader, "cases": cases}
    public["task_sha256"] = comparison.fingerprint(public)
    return {"public": public, "mapping": mapping}


def prepare(pairs: list, readers: list, folder: Path) -> None:
    if any(not reader.strip() for reader in readers) or len(set(readers)) != len(readers):
        raise ValueError("readers must be distinct non-empty pseudonyms")
    shuffled = readers[:]
    random.SystemRandom().shuffle(shuffled)
    base = comparison.assignment(pairs, "organizer")
    assignments = [reader_assignment(pairs, base, reader, comparison.SIDES[index % 2]) for index, reader in enumerate(shuffled)]
    organizer = {"schema_version": 1, "rubric_version": RUBRIC, "source_sha256": comparison.fingerprint(pairs), "assignments": assignments}
    folder.mkdir(parents=True, exist_ok=False)
    review.evaluation.save_json(folder / "organizer.json", organizer)
    template = Path(__file__).with_suffix(".html").read_text(encoding="utf-8")
    for index, assigned in enumerate(assignments, 1):
        destination = folder / f"reader-{index:03}"
        destination.mkdir()
        payload = json.dumps(assigned["public"], ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
        (destination / "review.html").write_text(template.replace("__TASK_DATA__", payload), encoding="utf-8")
        review.evaluation.save_json(destination / "tasks.json", assigned["public"])


def validate_header(document) -> None:
    if not isinstance(document, dict) or document.get("schema_version") != 1 or document.get("rubric_version") != RUBRIC:
        raise ValueError("invalid comprehension schema/rubric")


def checked_assignment(assigned) -> dict:
    if not isinstance(assigned, dict) or not isinstance(assigned.get("mapping"), dict):
        raise ValueError("invalid comprehension assignment")
    public = assigned.get("public")
    validate_header(public)
    review.text_field(public, "reviewer", True)
    if public.get("task_sha256") != comparison.fingerprint({k: v for k, v in public.items() if k != "task_sha256"}):
        raise ValueError("comprehension assignment hash mismatch")
    cases = public.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("missing comprehension cases")
    ids = [checked_assigned_case(case, assigned["mapping"]) for case in cases]
    if len(set(ids)) != len(ids) or set(ids) != set(assigned["mapping"]):
        raise ValueError("duplicate/missing comprehension case")
    if len({c["document_id"] for c in cases}) != len(cases):
        raise ValueError("reader must see each document only once")
    return assigned


def checked_assigned_case(case, mapping: dict) -> str:
    if not isinstance(case, dict):
        raise ValueError("invalid comprehension case")
    for name in ("id", "document_id", "candidate"):
        review.text_field(case, name, True)
    private = mapping.get(case["id"])
    if not isinstance(private, dict):
        raise ValueError("missing comprehension key")
    for name in ("source_id", "variant", "original"):
        review.text_field(private, name, True)
    if case["candidate"] != private.get("candidate"):
        raise ValueError("candidate does not match private assignment")
    checked = checked_questions(private.get("questions"), private["original"])
    if case.get("questions") != [{k: q[k] for k in ("id", "prompt", "options")} for q in checked]:
        raise ValueError("public questions do not match answer key")
    return case["id"]


def read_assignments(path: Path) -> list:
    organizer = review.read_json(path)
    validate_header(organizer)
    entries = organizer.get("assignments")
    if not isinstance(entries, list) or not entries:
        raise ValueError("missing reader assignments")
    assignments = [checked_assignment(a) for a in entries]
    if len({a["public"]["reviewer"] for a in assignments}) != len(assignments):
        raise ValueError("duplicate reader")
    validate_shared_references(assignments)
    return assignments


def validate_shared_references(assignments: list) -> None:
    references, candidates = [], {}
    for assigned in assignments:
        sources = {}
        for case in assigned["public"]["cases"]:
            private = assigned["mapping"][case["id"]]
            source = private["source_id"]
            if source in sources:
                raise ValueError("duplicate comprehension source")
            sources[source] = {k: private[k] for k in ("original", "questions")} | {"document_id": case["document_id"]}
            key = (source, private["variant"])
            if key in candidates and candidates[key] != case["candidate"]:
                raise ValueError("inconsistent comprehension candidate")
            candidates[key] = case["candidate"]
        references.append(sources)
    if any(reference != references[0] for reference in references[1:]) or len({v for _, v in candidates}) > 2:
        raise ValueError("inconsistent comprehension references/variants")


def checked_responses(document, assigned: dict) -> dict:
    public = assigned["public"]
    validate_header(document)
    if any(document.get(k) != public[k] for k in ("reviewer", "task_sha256")) or document.get("method") != "human":
        raise ValueError("answers do not match reader/tasks")
    entries = document.get("responses")
    if not isinstance(entries, list):
        raise ValueError("responses must be an array")
    cases = {c["id"]: c for c in public["cases"]}
    responses = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("invalid response")
        key = (review.text_field(entry, "id", True), review.text_field(entry, "question_id", True))
        case = cases.get(key[0])
        if case is None or key in responses:
            raise ValueError("unknown/duplicate response")
        responses[key] = checked_response(entry, case)
    return responses


def checked_response(entry: dict, case: dict) -> dict:
    question = next((q for q in case["questions"] if q["id"] == entry["question_id"]), None)
    choice = entry.get("choice")
    valid_choice = choice == "unknown" or type(choice) is int and question is not None and 0 <= choice < len(question["options"])
    if question is None or not valid_choice:
        raise ValueError("invalid question/choice")
    return {**entry, "note": review.text_field(entry, "note")}


def scored_rows(assigned: dict, responses: dict) -> list:
    rows = []
    for case in assigned["public"]["cases"]:
        private = assigned["mapping"][case["id"]]
        for question in private["questions"]:
            response = responses.get((case["id"], question["id"]))
            rows.append({"reviewer": assigned["public"]["reviewer"], "document_id": case["document_id"],
                         "source_id": private["source_id"], "variant": private["variant"], "question_id": question["id"],
                         "choice": response["choice"] if response else None, "correct": response is not None and response["choice"] == question["answer_index"],
                         "note": response["note"] if response else ""})
    return rows


def score_summary(rows: list) -> dict:
    completed = [r for r in rows if r["choice"] is not None]
    correct = sum(r["correct"] for r in completed)
    return {"assigned_questions": len(rows), "completed": len(completed), "missing": len(rows) - len(completed),
            "unknown": sum(r["choice"] == "unknown" for r in completed), "correct": correct,
            "accuracy_completed": correct / len(completed) if completed else None,
            "correct_rate_all_assigned": correct / len(rows) if rows else None}


def summarize(assignments: list, documents: list) -> dict:
    by_reader = {a["public"]["reviewer"]: a for a in assignments}
    submitted = {}
    for document in documents:
        reader = review.text_field(document, "reviewer", True) if isinstance(document, dict) else ""
        if reader not in by_reader or reader in submitted:
            raise ValueError("unknown/duplicate reader submission")
        submitted[reader] = checked_responses(document, by_reader[reader])
    rows = [r for reader, assigned in by_reader.items() for r in scored_rows(assigned, submitted.get(reader, {}))]
    return {"schema_version": 1, "rubric_version": RUBRIC, **score_summary(rows),
            **group_scores(rows),
            "qualitative": rows, "limits": "文章を参照して解く情報読取課題。未知分野の理解・記憶・因果効果を保証せず、未回答を誤答と混同しない。"}


def group_scores(rows: list) -> dict:
    variants, documents = {}, {}
    for row in rows:
        variants.setdefault(row["variant"], []).append(row)
        documents.setdefault((row["document_id"], row["variant"]), []).append(row)
    return {"variants": {v: score_summary(entries) for v, entries in sorted(variants.items())},
            "documents": [{"document_id": doc, "variant": v, **score_summary(entries)} for (doc, v), entries in sorted(documents.items())]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    creation = subparsers.add_parser("prepare")
    creation.add_argument("--input", type=Path, required=True)
    creation.add_argument("--readers", nargs="+", required=True)
    summary = subparsers.add_parser("summarize")
    summary.add_argument("--organizer", type=Path, required=True)
    summary.add_argument("--answers", type=Path, nargs="+", required=True)
    for command in (creation, summary):
        command.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare":
            prepare(read_source(args.input), args.readers, args.out_dir)
        else:
            report = summarize(read_assignments(args.organizer), [review.read_json(p) for p in args.answers])
            args.out_dir.mkdir(parents=True, exist_ok=False)
            review.evaluation.save_json(args.out_dir / "summary.json", report)
            (args.out_dir / "summary.md").write_text("# 理解問題の結果\n\n" + report["limits"] + "\n\n"
                + json.dumps({k: v for k, v in report.items() if k != "qualitative"}, ensure_ascii=False, indent=2).replace("<", "&lt;") + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"comprehension failed: {error}", file=sys.stderr)
        return 2
    print(str(args.out_dir.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
