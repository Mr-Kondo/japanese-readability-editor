#!/usr/bin/env python3
"""匿名比較を文書ごとにまとめ、版間差と対応のある文書単位の区間を出す。"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import statistics
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import compare_readability as comparison

RESAMPLES = 9999
SEED = 0


def document_outcomes(rows: list, variants: list) -> dict:
    first, second = variants
    determined = [r for r in rows if all(r["variants"][v]["contract"] in ("pass", "fail") for v in variants)]
    preferences = [r for r in rows if all(r["variants"][v]["contract"] == "pass" for v in variants)
                   and r["selected"] in (first, second, "tie")]
    differences = [(r["variants"][second]["contract"] == "fail") - (r["variants"][first]["contract"] == "fail") for r in determined]
    preference_values = [{first: -1, second: 1, "tie": 0}[r["selected"]] for r in preferences]
    return {"completed_reviews": len(rows), "determined_pairs": len(determined), "preference_votes": len(preferences),
            "fail_rate_difference": statistics.mean(differences) if differences else None,
            "preference_balance": statistics.mean(preference_values) if preference_values else None}


def percentile(sorted_samples: list, probability: float) -> float:
    position = (len(sorted_samples) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(sorted_samples) - 1)
    return sorted_samples[lower] + (position - lower) * (sorted_samples[upper] - sorted_samples[lower])


def estimate(values: list) -> dict:
    count = len(values)
    outcome = {"documents": count, "mean": statistics.mean(values) if values else None, "interval_95": None}
    if count < 2:
        return {**outcome, "interval_status": "insufficient_documents"}
    if len(set(values)) == 1:
        return {**outcome, "interval_status": "degenerate_document_values"}
    generator = random.Random(SEED)
    samples = sorted(statistics.mean(generator.choices(values, k=count)) for _ in range(RESAMPLES))
    return {**outcome, "interval_95": [percentile(samples, 0.025), percentile(samples, 0.975)], "interval_status": "estimated"}


def summarize(assignments: list, documents: list) -> dict:
    summary = comparison.aggregate(assignments, documents)
    variants = comparison.variant_names(assignments[0])
    doc_ids = sorted({c["document_id"] for a in assignments for c in a["public"]["cases"]})
    by_document = [{"document_id": doc, **document_outcomes([r for r in summary["qualitative"] if r["document_id"] == doc], variants)} for doc in doc_ids]
    estimates = {metric: estimate([doc[metric] for doc in by_document if doc[metric] is not None])
                 for metric in ("fail_rate_difference", "preference_balance")}
    return {"schema_version": 1, "variants_in_order": variants,
            "definition": "不合格割合の差=第2版-第1版（低い方が良い）。選好収支=第2版+1/第1版-1/同等0。文書内平均後に文書を等重み。",
            "coverage": {k: summary[k] for k in ("assigned_documents", "expected_reviews", "completed_reviews", "missing_reviews", "both_pass")},
            "bootstrap": {"unit": "document", "method": "paired percentile", "resamples": RESAMPLES, "seed": SEED, "confidence_level": 0.95},
            "estimates": estimates, "documents": by_document,
            "limits": "両版が判定済みの回答だけで不合格割合の差を算出。選好は両版合格かつ選好判定済みに限定。"
                      "文書の抽出と固定した評価者に条件付けた近似区間で、欠測の偏りや評価者集団への一般化を扱わない。"
                      "少数文書の区間は不安定。同等性・因果効果・全体の品質改善の証明ではない。"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--organizer", type=Path, required=True)
    parser.add_argument("--answers", type=Path, nargs="+", required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        assignments = comparison.read_assignments(args.organizer)
        report = summarize(assignments, [comparison.review.read_json(p) for p in args.answers])
        args.out_dir.mkdir(parents=True, exist_ok=False)
        comparison.review.evaluation.save_json(args.out_dir / "statistics.json", report)
        (args.out_dir / "statistics.md").write_text("# 文書単位の版間差\n\n" + report["definition"] + "\n\n" + report["limits"]
            + "\n\n" + json.dumps(report, ensure_ascii=False, indent=2).replace("<", "&lt;") + "\n", encoding="utf-8")
    except (OSError, ValueError, RuntimeError) as error:
        print(f"statistics failed: {error}", file=sys.stderr)
        return 2
    print(str(args.out_dir.resolve()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
