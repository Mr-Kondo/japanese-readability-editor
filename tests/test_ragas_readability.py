"""Ragas 採点CLI。Ragas が無い環境では結合試験をスキップする。LLM 呼出しは偽の invoke で置き換え、通信しない。"""
import copy
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


if __name__ == "__main__":
    unittest.main()
