"""Ragas 採点CLI。Ragas が無い環境では結合試験をスキップする。LLM 呼出しは偽の invoke で置き換え、通信しない。"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from helpers import REPO_ROOT, TOOLS_DIR, load_module, run_script

ragas_tool = load_module("ragas_readability", TOOLS_DIR / "ragas_readability.py")
TOOL = TOOLS_DIR / "ragas_readability.py"


def ragas_usable() -> bool:
    if importlib.util.find_spec("ragas") is None:
        return False
    try:
        ragas_tool.load_ragas()
    except RuntimeError:
        return False
    return True


def case(case_id="c1", original="管理者は、承認後に設定を変更することができる。", candidate="管理者は、承認後に設定を変更できる。", **extra):
    return {"id": case_id, "document_id": case_id, "mode": "B", "request": "意味を保って推敲する", "audience": "担当者",
            "context": "", "original": original, "candidate": candidate, **extra}


def write_cases(folder: str, *cases) -> Path:
    path = Path(folder, "cases.json")
    path.write_text(json.dumps({"schema_version": 1, "cases": list(cases)}, ensure_ascii=False), encoding="utf-8")
    return path


def call(kind, parsed=None, error=None):
    return {"kind": kind, "parsed": parsed, "error": error}


def decomposition(*claims):
    return call("ClaimDecompositionOutput", {"claims": list(claims)})


def nli(*verdicts):
    return call("NLIStatementOutput", {"statements": [{"statement": f"s{i}", "reason": f"r{i}", "verdict": v}
                                                      for i, v in enumerate(verdicts)]})


class PureLogicTest(unittest.TestCase):
    def test_cases_must_be_mode_b(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_cases(folder, {**case(), "mode": "A"})
            with self.assertRaisesRegex(ValueError, "モード B"):
                ragas_tool.read_cases(path)

    def test_rubric_templates_are_japanese_and_survive_braces_in_text(self):
        for aspect in ragas_tool.ASPECTS:
            template = ragas_tool.aspect_template(aspect)
            for field in ("request", "audience", "context", "original", "candidate"):
                self.assertIn("{" + field + "}", template)
            self.assertNotIn("{label}", template)
            self.assertNotIn("{criterion}", template)
        text = "設定は {\"key\": \"value\"} と {name} のとおり。"
        filled = ragas_tool.aspect_template("condition_scope").format(**ragas_tool.case_inputs(case(original=text, candidate=text)))
        self.assertIn(text, filled)

    def test_profiles_use_known_aspects_and_default_is_documented(self):
        for names in ragas_tool.PROFILES.values():
            self.assertTrue(set(names) <= set(ragas_tool.ASPECTS))
        self.assertEqual(set(ragas_tool.PROFILES["all"]), set(ragas_tool.ASPECTS))

    def test_planned_calls_is_an_upper_bound_per_metric(self):
        plan = ragas_tool.planned_calls(3, ["factual", "rubric"], ragas_tool.PROFILES["core"])
        self.assertEqual(plan["per_case"], {"factual": 4, "rubric": 6, "readability": 0})
        self.assertEqual(plan["upper_bound"], 30)

    def test_extract_json_accepts_fenced_and_wrapped_output(self):
        self.assertEqual(ragas_tool.extract_json('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(ragas_tool.extract_json('結果です。{"a": {"b": 2}} 以上'), {"a": {"b": 2}})
        with self.assertRaises(ValueError):
            ragas_tool.extract_json("JSONなし")

    def test_cost_comes_from_the_raw_cli_output_and_is_never_invented(self):
        with tempfile.TemporaryDirectory() as folder:
            raw = Path(folder, "c.json")
            raw.write_text(json.dumps({"stdout": json.dumps({"total_cost_usd": 0.0125})}), encoding="utf-8")
            self.assertEqual(ragas_tool.raw_cost(raw), 0.0125)
            raw.write_text(json.dumps({"stdout": "{}"}), encoding="utf-8")
            self.assertIsNone(ragas_tool.raw_cost(raw))
            self.assertIsNone(ragas_tool.raw_cost(Path(folder, "missing.json")))

    def test_precision_counts_and_unsupported_claims(self):
        result = ragas_tool.derive_factual([decomposition("a", "b", "c"), nli(1, 1, 0)], "precision", 0.67, None)
        self.assertEqual(result["status"], "scored")
        self.assertEqual(result["response_claims"], {"total": 3, "supported": 2, "unsupported": 1,
                                                     "unsupported_texts": [{"claim": "s2", "reason": "r2"}]})
        self.assertTrue(result["consistent"])

    def test_recall_uses_ragas_formula_and_reports_reference_coverage_separately(self):
        calls = [decomposition("a", "b"), nli(1, 1), decomposition("x", "y", "z"), nli(1, 0, 0)]
        result = ragas_tool.derive_factual(calls, "recall", 0.5, None)  # tp=2, fn=2 -> 0.5
        self.assertTrue(result["consistent"])
        self.assertEqual(result["reference_claims"]["coverage"], 0.33)  # 原文の主張3件のうち1件が支持
        self.assertEqual([t["claim"] for t in result["reference_claims"]["unsupported_texts"]], ["s1", "s2"])

    def test_zero_claims_is_not_a_zero_score(self):
        result = ragas_tool.derive_factual([decomposition()], "precision", 0.0, None)
        self.assertEqual((result["status"], result["value"], result["ragas_value"]), ("no_claims", None, 0.0))

    def test_errors_and_unexpected_sequences_are_never_scored(self):
        self.assertEqual(ragas_tool.derive_factual([], "precision", None, "RuntimeError: x")["status"], "error")
        self.assertEqual(ragas_tool.derive_factual([decomposition("a"), nli(1)], "recall", 1.0, None)["status"], "error")

    def test_inconsistent_value_and_verdict_mismatch_are_flagged(self):
        result = ragas_tool.derive_factual([decomposition("a", "b"), nli(1, 1)], "precision", 0.5, None)
        self.assertFalse(result["consistent"])
        mismatch = ragas_tool.derive_factual([decomposition("a", "b", "c"), nli(1, 1)], "precision", 1.0, None)
        self.assertTrue(any("verdict_count_mismatch" in w for w in mismatch["warnings"]))


def scored(value, unsupported=()):
    return {"status": "scored", "value": value, "ragas_value": value,
            "response_claims": {"unsupported_texts": [{"claim": c, "reason": ""} for c in unsupported]},
            "reference_claims": {"unsupported_texts": [{"claim": c, "reason": ""} for c in unsupported]}}


def rubric(**values):
    return {a: {"status": "scored", "value": v, "reason": "r"} for a, v in values.items()}


def run_case(case_id, precision=1.0, recall=1.0, **aspects):
    return {"id": case_id, "document_id": "d", "errors": [],
            "factual": {"precision": scored(precision), "recall": scored(recall)}, "rubric": rubric(**aspects)}


def label(expected, aspect=None, perturbation="p"):
    return {"expected_preservation": expected, "perturbation": perturbation, "violated_aspect": aspect, "source_id": "s"}


class CalibrationTest(unittest.TestCase):
    def report(self, cases, labels):
        return ragas_tool.calibrate({"cases": cases, "status": "complete", "models": ["m"], "call_summary": {}},
                                    {"labels": labels, "notice": "n"})

    def test_signals_rates_and_targeted_hits_use_expected_labels(self):
        cases = [run_case("f1", recall=0.67, condition_scope="fail", actor_target="fail", unnecessary_change="fail"),
                 run_case("f2", condition_scope="pass", actor_target="pass", unnecessary_change="pass"),
                 run_case("p1", condition_scope="pass", actor_target="pass", unnecessary_change="fail"),
                 run_case("p2", precision=0.5, condition_scope="fail", actor_target="pass", unnecessary_change="pass")]
        labels = {"f1": label("fail", "condition_scope"), "f2": label("fail", "condition_scope"),
                  "p1": label("pass"), "p2": label("pass")}
        summary = self.report(cases, labels)["summary"]
        self.assertEqual(summary["fail"]["factual_signal"], {"signalled": 1, "available": 2, "unavailable": 0, "rate": 0.5})
        self.assertEqual(summary["fail"]["targeted_aspect_hit"]["signalled"], 1)
        self.assertEqual(summary["fail"]["failed_aspects_per_case"]["values"], [2, 0])  # 観点が弁別していない例
        self.assertEqual(summary["pass"]["factual_signal"]["signalled"], 1)
        self.assertEqual(summary["pass"]["rubric_signal"]["signalled"], 1)
        # unnecessary_change は保持の信号に含めない（p1 は保持の信号なし）
        self.assertEqual(summary["pass"]["unnecessary_change_fail"], {"signalled": 1, "available": 2})

    def test_unscored_cases_are_unavailable_not_negative(self):
        broken = run_case("f1", condition_scope="fail")
        broken["factual"]["precision"] = {"status": "no_claims", "value": None}
        broken["rubric"]["actor_target"] = {"status": "error", "value": None, "error": "x"}
        report = self.report([broken], {"f1": label("fail", "condition_scope")})
        part = report["summary"]["fail"]
        self.assertEqual((part["factual_signal"]["available"], part["factual_signal"]["unavailable"]), (0, 1))
        self.assertEqual((part["rubric_signal"]["available"], part["rubric_signal"]["unavailable"]), (0, 1))
        self.assertIsNone(report["cases"][0]["factual_signal"])

    def test_missing_label_and_unlabelled_file_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "no label"):
            self.report([run_case("x")], {})
        with self.assertRaisesRegex(ValueError, "no labels"):
            ragas_tool.calibrate({"cases": []}, {})

    def test_report_states_that_labels_are_unconfirmed(self):
        report = self.report([run_case("f1", condition_scope="fail")], {"f1": label("fail", "condition_scope")})
        self.assertEqual(report["status"], "constructed_labels_not_human_confirmed")
        self.assertIn("人の確認前", ragas_tool.render_calibration(report))

    def test_committed_labels_cover_every_artificial_case_and_use_only_tuning_sources(self):
        base = REPO_ROOT / "evals/ragas-calibration"
        cases = json.loads((base / "artificial-cases.json").read_text(encoding="utf-8"))["cases"]
        labels = json.loads((base / "artificial-labels.json").read_text(encoding="utf-8"))["labels"]
        self.assertEqual({c["id"] for c in cases}, set(labels))
        manifest = json.loads((REPO_ROOT / "evals/public-documents/manifest.json").read_text(encoding="utf-8"))
        splits = {e["id"]: e["split"] for e in manifest["excerpts"] if e["status"] == "candidate"}
        self.assertTrue(all(splits[v["source_excerpt"]] == "tuning" for v in labels.values()))  # 最終評価用は校正に使わない
        self.assertTrue(all(v["confirmed_by"] == "" for v in labels.values()))  # 人の確認を偽らない
        for c in cases:
            self.assertEqual(labels[c["id"]]["original_sha256"], __import__("hashlib").sha256(c["original"].encode()).hexdigest())

    def test_cli_calibrate_writes_report_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            run, labels = Path(folder, "run.json"), Path(folder, "labels.json")
            run.write_text(json.dumps({"cases": [run_case("f1", condition_scope="fail")], "status": "complete", "config": {}}), encoding="utf-8")
            labels.write_text(json.dumps({"labels": {"f1": label("fail", "condition_scope")}}), encoding="utf-8")
            out = Path(folder, "out")
            code, _, err = run_script(TOOL, "calibrate", "--run", str(run), "--labels", str(labels), "--out-dir", str(out))
            self.assertEqual(code, 0, err)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["ragas-calibration.json", "ragas-calibration.md"])
            self.assertEqual(run_script(TOOL, "calibrate", "--run", str(run), "--labels", str(labels), "--out-dir", str(out))[0], 2)


class MergeRunsTest(unittest.TestCase):
    def run_file(self, *cases, **config):
        base = {"atomicity": "high", "coverage": "high", "rubric_sha256": "r", "aspects": ["a"], "metrics": ["factual"],
                "claude_flags": ["--print"], "packages": {"ragas": "0.4.3"}}
        return {"status": "complete", "config": base | config, "models": ["m"], "cases": list(cases),
                "call_summary": {"calls": 4, "cache_hits": 1, "failures": 0, "seconds": 2.0, "cost_usd_list_price": 0.5, "calls_without_cost": 0}}

    def test_split_runs_merge_with_summed_calls(self):
        merged = ragas_tool.merge_runs([self.run_file(run_case("a")), self.run_file(run_case("b"))])
        self.assertEqual([c["id"] for c in merged["cases"]], ["a", "b"])
        self.assertEqual((merged["call_summary"]["calls"], merged["call_summary"]["cost_usd_list_price"]), (8, 1.0))
        self.assertEqual(merged["status"], "complete")

    def test_different_settings_or_duplicate_cases_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "different config: coverage"):
            ragas_tool.merge_runs([self.run_file(run_case("a")), self.run_file(run_case("b"), coverage="low")])
        with self.assertRaisesRegex(ValueError, "duplicate case id"):
            ragas_tool.merge_runs([self.run_file(run_case("a")), self.run_file(run_case("a"))])

    def test_a_partial_run_keeps_the_merged_status_partial(self):
        partial = self.run_file(run_case("b"))
        partial["status"] = "complete_with_errors"
        self.assertEqual(ragas_tool.merge_runs([self.run_file(run_case("a")), partial])["status"], "partial_or_with_errors")


class CompareLlmTest(unittest.TestCase):
    def eval_run(self, candidate, status="pass"):
        return {"skill_sha256": {"SKILL.md": "x"}, "suite": {"cases": [{"id": "k1", "text": "原文。"}]},
                "outputs": [{"id": "g001", "case_id": "k1", "repeat": 1, "text": candidate, "model_ids": ["gen"]}],
                "grading_items": [{"id": "j001", "source_id": "g001", "kind": "generated"}],
                "grading_calls": [{"model_ids": ["grader"], "judgments": [{"id": "j001", "status": status, "reason": "理由"}]}]}

    def test_pairs_existing_grader_with_ragas_signals_without_judging_correctness(self):
        ragas = {"cases": [run_case("g001", recall=0.5, condition_scope="fail")]}
        report = ragas_tool.compare_llm(ragas, self.eval_run("原文。", "pass"))
        row = report["cases"][0]
        self.assertEqual((row["existing_grader"], row["factual_signal"], row["rubric_signal"]), ("pass", True, True))
        self.assertTrue(row["identical_to_original"])
        self.assertEqual(report["crosstab"], {"grader=pass | factual_signal=True | rubric_signal=True": 1})
        self.assertEqual(report["status"], "no_human_labels")
        self.assertEqual((report["generation_models"], report["grading_models"]), (["gen"], ["grader"]))

    def test_missing_grading_is_missing_not_pass(self):
        run = self.eval_run("別。")
        run["grading_calls"], run["grading_items"] = [], []
        report = ragas_tool.compare_llm({"cases": [run_case("g001")]}, run)
        self.assertEqual(report["cases"][0]["existing_grader"], "missing")

    def test_unknown_output_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "no generated output"):
            ragas_tool.compare_llm({"cases": [run_case("g999")]}, self.eval_run("原文。"))


class CliTest(unittest.TestCase):
    def test_prepare_only_sends_nothing_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_cases(folder, case("c1"), case("c2"))
            out = Path(folder, "out")
            code, stdout, stderr = run_script(TOOL, "score", "--input", str(path), "--out-dir", str(out))
            self.assertEqual(code, 0, stderr)
            plan = json.loads(stdout)
            self.assertFalse(plan["execute"])
            self.assertEqual(plan["sent_to_model"], [])
            self.assertEqual(plan["calls"]["upper_bound"], 20)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["plan.json", "tasks.json"])
            self.assertEqual(run_script(TOOL, "score", "--input", str(path), "--out-dir", str(out))[0], 2)

    def test_execute_plan_lists_what_is_sent(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder, "out")
            # Ragas が無い、または CLI が無い環境でも、送信範囲は準備段階で確認できる（実行は失敗してよい）
            code, _, _ = run_script(TOOL, "score", "--input", str(write_cases(folder, case())), "--out-dir", str(out),
                                    "--execute", "--metrics", "readability", env={"PATH": "/nonexistent"})
            self.assertIn(code, (1, 2))
            plan = json.loads((out / "plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["sent_to_model"], ["request", "audience", "context", "original", "candidate"])

    def test_non_b_input_exits_two_without_creating_output(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder, "out")
            path = write_cases(folder, {**case(), "mode": "C"})
            code, _, stderr = run_script(TOOL, "score", "--input", str(path), "--out-dir", str(out))
            self.assertEqual(code, 2)
            self.assertIn("ragas failed", stderr)
            self.assertFalse(out.exists())

    def test_check_reports_pins_without_network(self):
        code, stdout, _ = run_script(TOOL, "check")
        report = json.loads(stdout)
        self.assertEqual(report["pinned"], {"ragas": "0.4.3", "langchain-community": "0.3.31"})
        self.assertEqual(code, 1 if report["problems"] else 0)

    def test_requirements_file_matches_pins(self):
        text = (TOOLS_DIR / "requirements-ragas.txt").read_text(encoding="utf-8")
        for name, version in ragas_tool.PINNED.items():
            self.assertIn(f"{name}=={version}", text)
        constraints = (TOOLS_DIR / "ragas-constraints.txt").read_text(encoding="utf-8").lower()
        for name, version in ragas_tool.PINNED.items():
            self.assertIn(f"{name}=={version}", constraints)


@unittest.skipUnless(ragas_usable(), "ragas が未導入、または import できない（任意依存）")
class RagasIntegrationTest(unittest.TestCase):
    """実際の Ragas 0.4.3 のメトリクスを、偽の invoke（LLM なし）で動かす。"""

    def make_run(self, folder, script, tasks, metrics=("factual", "rubric"), profile="core"):
        classes = ragas_tool.load_ragas()
        llm = ragas_tool.make_llm_class(classes[0])(Path(folder, "raw"), invoke=self.fake_invoke(script))
        Path(folder, "raw").mkdir(exist_ok=True)
        args = type("Args", (), {"profile": profile, "atomicity": "high", "coverage": "high"})()
        config = {"atomicity": "high", "coverage": "high"}
        import asyncio
        records = [asyncio.run(ragas_tool.score_task(t, llm, list(metrics), ragas_tool.PROFILES[profile], config, classes))
                   for t in tasks["cases"]]
        return llm, records

    @staticmethod
    def fake_invoke(script):
        def invoke(prompt, destination):
            Path(destination).write_text("{}", encoding="utf-8")
            return {"text": json.dumps(script(prompt), ensure_ascii=False), "model_ids": ["fake-model"],
                    "prompt_sha256": "x", "raw_file": Path(destination).name}
        return invoke

    def scripted(self, claims_by_text, unsupported=()):
        state = {"claims": []}

        def script(prompt):
            body = prompt.split("スキーマ:")[0]
            if '"title": "ClaimDecompositionOutput"' in prompt:
                state["claims"] = next((c for marker, c in claims_by_text.items() if marker in body), [])
                return {"claims": state["claims"]}
            if '"title": "NLIStatementOutput"' in prompt:
                return {"statements": [{"statement": c, "reason": "r", "verdict": 0 if c in unsupported else 1} for c in state["claims"]]}
            failing = "FAILMARK" in body
            if "読みやすさの検査者" in body:
                return {"value": "worse" if failing else "better", "reason": "「根拠」"}
            return {"value": "fail" if failing else "pass", "reason": "「根拠」"}
        return script

    def test_scores_are_reconstructed_and_shared_calls_are_reused(self):
        original, candidate = "ORIGINAL文。条件Xがある。", "CANDIDATE文。"
        script = self.scripted({"CANDIDATE": ["候補の主張"], "ORIGINAL": ["原文の主張", "条件Xがある"]}, unsupported=("条件Xがある",))
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case(original=original, candidate=candidate)))
            llm, (record,) = self.make_run(folder, script, tasks, metrics=("factual",))
        precision, recall = record["factual"]["precision"], record["factual"]["recall"]
        self.assertEqual((precision["status"], precision["value"]), ("scored", 1.0))
        self.assertEqual(recall["reference_claims"]["unsupported"], 1)
        self.assertEqual([t["claim"] for t in recall["reference_claims"]["unsupported_texts"]], ["条件Xがある"])
        self.assertTrue(precision["consistent"] and recall["consistent"])
        self.assertGreater(sum(c["cache_hit"] for c in llm.calls), 0)  # precision の呼出しを recall が再利用
        self.assertEqual(record["errors"], [])

    def test_zero_claims_from_the_model_is_reported_not_scored_as_zero(self):
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case()))
            _, (record,) = self.make_run(folder, self.scripted({}), tasks, metrics=("factual",))
        self.assertEqual(record["factual"]["precision"]["status"], "no_claims")
        self.assertIsNone(record["factual"]["precision"]["value"])

    def test_rubric_records_value_and_reason_and_handles_braces(self):
        braces = "設定は {\"a\": 1} のとおり。"
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case(original=braces, candidate="FAILMARK " + braces)))
            _, (record,) = self.make_run(folder, self.scripted({}), tasks, metrics=("rubric", "readability"), profile="tech")
        self.assertEqual(set(record["rubric"]), set(ragas_tool.PROFILES["tech"]))
        self.assertTrue(all(v == {"status": "scored", "value": "fail", "reason": "「根拠」"} for v in record["rubric"].values()))
        self.assertEqual(record["readability"]["readability"]["value"], "worse")

    def test_model_failure_is_recorded_and_never_becomes_a_score(self):
        def failing(prompt):
            raise RuntimeError("model down")
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case()))
            llm, (record,) = self.make_run(folder, failing, tasks)
        self.assertEqual(record["factual"]["precision"]["status"], "error")
        self.assertIsNone(record["factual"]["precision"]["value"])
        self.assertTrue(all(v["status"] == "error" for v in record["rubric"].values()))
        self.assertTrue(record["errors"])
        self.assertTrue(all(c["error"] for c in llm.calls))

    def test_invalid_model_json_is_an_error_not_a_default(self):
        def junk(prompt):
            return {"value": "maybe", "reason": "r"}
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case()))
            _, (record,) = self.make_run(folder, junk, tasks, metrics=("rubric",))
        self.assertTrue(all(v["status"] == "error" for v in record["rubric"].values()))

    def test_every_call_records_prompt_hash_models_and_raw_file(self):
        with tempfile.TemporaryDirectory() as folder:
            tasks = ragas_tool.read_cases(write_cases(folder, case()))
            llm, _ = self.make_run(folder, self.scripted({"candidate": ["a"]}), tasks, metrics=("rubric",))
            for entry in llm.calls:
                self.assertEqual(len(entry["prompt_sha256"]), 64)
                self.assertEqual(entry["model_ids"], ["fake-model"])
                self.assertTrue(Path(folder, "raw", entry["raw_file"]).exists())


class StabilityTest(unittest.TestCase):
    def repeat(self, *cases, **config):
        base = {"atomicity": "high", "coverage": "high", "discriminate": False, "rubric_sha256": "r", "aspects": ["a"],
                "metrics": ["factual"], "claude_flags": [], "packages": {}}
        return {"status": "complete", "config": base | config, "models": ["m"], "cases": list(cases), "call_summary": {}}

    def test_counts_unstable_signals_aspect_flips_and_majority(self):
        runs = [self.repeat(run_case("f1", condition_scope="fail", actor_target="pass"), run_case("p1", condition_scope="pass", actor_target="pass")),
                self.repeat(run_case("f1", condition_scope="fail", actor_target="fail"), run_case("p1", condition_scope="pass", actor_target="pass")),
                self.repeat(run_case("f1", condition_scope="pass", actor_target="pass"), run_case("p1", precision=0.5, condition_scope="pass", actor_target="pass"))]
        labels = {"labels": {"f1": label("fail", "condition_scope"), "p1": label("pass")}}
        report = ragas_tool.stability(runs, labels)
        summary = report["summary"]
        self.assertEqual(summary["repeats"], 3)
        self.assertEqual(summary["rubric_signal_unstable_cases"], 1)  # f1: True, True, False
        self.assertEqual(summary["factual_signal_unstable_cases"], 1)  # p1: False, False, True
        self.assertEqual(summary["failed_aspects_unstable_cases"], 1)
        self.assertEqual(summary["aspect_flips"], {"flipped": 2, "aspect_scores": 4, "rate": 0.5})  # f1 の2観点とも値が変わった
        self.assertEqual(summary["fail"]["rubric_signal"], {"signalled_per_repeat": [1, 1, 0], "signalled_by_majority": 1})
        self.assertEqual(summary["fail"]["targeted_hits_per_repeat"], [1, 1, 0])
        self.assertEqual(summary["pass"]["factual_signal"]["signalled_by_majority"], 0)  # 1/3 は多数決で信号なし
        self.assertEqual(report["status"], "constructed_labels_not_human_confirmed")
        self.assertIn("人の確認前", ragas_tool.render_stability(report))

    def test_needs_two_repeats_the_same_settings_and_the_same_cases(self):
        one = self.repeat(run_case("a", condition_scope="pass"))
        with self.assertRaisesRegex(ValueError, "at least two"):
            ragas_tool.stability([one])
        with self.assertRaisesRegex(ValueError, "different config: coverage"):
            ragas_tool.stability([one, self.repeat(run_case("a", condition_scope="pass"), coverage="low")])
        with self.assertRaisesRegex(ValueError, "different cases"):
            ragas_tool.stability([one, self.repeat(run_case("b", condition_scope="pass"))])

    def test_cli_writes_report_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            files = []
            for index in range(2):
                path = Path(folder, f"r{index}.json")
                path.write_text(json.dumps(self.repeat(run_case("a", condition_scope="pass"))), encoding="utf-8")
                files.append(str(path))
            out = Path(folder, "out")
            args = ["stability", "--repeat", files[0], "--repeat", files[1], "--out-dir", str(out)]
            code, _, err = run_script(TOOL, *args)
            self.assertEqual(code, 0, err)
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["ragas-stability.json", "ragas-stability.md"])
            self.assertEqual(run_script(TOOL, *args)[0], 2)


class DiscriminateAndSubtleLabelsTest(unittest.TestCase):
    def test_discriminate_adds_one_instruction_and_changes_the_rubric_hash(self):
        plain, strict = ragas_tool.aspect_template("numbers_order"), ragas_tool.aspect_template("numbers_order", True)
        self.assertNotIn("他の観点に当たる違い", plain)
        self.assertIn("他の観点に当たる違い", strict)
        self.assertEqual(strict.count("他の観点に当たる違い"), 1)
        self.assertNotEqual(ragas_tool.rubric_sha256(), ragas_tool.rubric_sha256(True))
        self.assertEqual(ragas_tool.aspect_template("numbers_order"), plain)  # 既定は変えない

    def test_committed_subtle_labels_cover_every_case_and_use_only_tuning_candidates(self):
        base = REPO_ROOT / "evals/ragas-calibration"
        cases = json.loads((base / "artificial-cases-subtle.json").read_text(encoding="utf-8"))["cases"]
        labels = json.loads((base / "artificial-labels-subtle.json").read_text(encoding="utf-8"))["labels"]
        self.assertEqual({c["id"] for c in cases}, set(labels))
        manifest = json.loads((REPO_ROOT / "evals/public-documents/manifest.json").read_text(encoding="utf-8"))
        excerpts = {e["id"]: e for e in manifest["excerpts"] if e["status"] == "candidate"}
        for c in cases:
            lab = labels[c["id"]]
            self.assertEqual(excerpts[lab["source_excerpt"]]["split"], "tuning")  # 最終評価用は校正に使わない
            self.assertIn(c["original"], excerpts[lab["source_excerpt"]]["text"])
            self.assertEqual(lab["confirmed_by"], "")  # 人の確認を偽らない
            self.assertEqual(lab["original_sha256"], __import__("hashlib").sha256(c["original"].encode()).hexdigest())
            self.assertEqual(c["candidate"] != c["original"], lab["perturbation"] != "control_unchanged")
            self.assertEqual(lab["expected_preservation"] == "fail", lab["violated_aspect"] is not None)


if __name__ == "__main__":
    unittest.main()
