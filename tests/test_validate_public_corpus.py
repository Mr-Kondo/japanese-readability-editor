"""公開文書の台帳検証。本文はすべて人工の検査用で、実在の公開文書ではない。"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from helpers import REPO_ROOT, TOOLS_DIR, load_module, run_script

corpus = load_module("validate_public_corpus", TOOLS_DIR / "validate_public_corpus.py")
TOOL = TOOLS_DIR / "validate_public_corpus.py"
RAW = "a" * 64
TEXT = "担当者は、申請を受けた日から5営業日以内に、審査結果を申請者へ通知しなければならない。ただし、休日を除く。"
OTHER = "管理者は、承認後に設定を変更することができる。"


def license_entry(**extra):
    return {"name": "人工の検査用条件", "url": "https://example.invalid/license", "checked_on": "2026-10-16",
            "redistribution": "allowed", **extra}


def source(source_id="s1", **extra):
    entry = {"id": source_id, "group": "g", "status": "collected", "title": "人工文書", "provider": "検査用",
             "url": "https://example.invalid/doc", "version": "v1", "format": "html", "retrieved_on": "2026-10-16",
             "raw_sha256": RAW,
             "license": {"body": license_entry(attribution="出典: 検査用", modification_notice="検査用に抜粋・加工"),
                         "bibliographic": license_entry()}}
    entry.update(extra)
    return entry


def excerpt(excerpt_id="e1", source_id="s1", text=TEXT, **extra):
    digest = corpus.sha256_text(text)
    entry = {"id": excerpt_id, "source_id": source_id, "status": "adopted", "role": "change_target", "split": "tuning",
             "locator": "第1段落", "correspondence": {"checked_by": "reviewer-a", "checked_on": "2026-10-16"},
             "third_party_content": "none", "text": text, "text_sha256": digest,
             "transform_history": [{"step": "extract", "tool": "manual", "input_sha256": RAW, "output_sha256": digest}],
             "preserve": [{"kind": "deadline", "quote": "5営業日以内" if "5営業日以内" in text else text[:6], "strength": "normative", "confirmed_by": "reviewer-a",
                           "reason": "期限は義務の条件", "allowed_changes": []}],
             "questions": []}
    entry.update(extra)
    return entry


def manifest(*excerpts, sources=None):
    return {"schema_version": 1, "groups": {"g": {"target_excerpts": 10}},
            "sources": sources if sources is not None else [source()], "excerpts": list(excerpts)}


class ManifestTest(unittest.TestCase):
    def errors(self, document):
        return corpus.check_manifest(document)[0]

    def assertError(self, document, fragment):
        errors = self.errors(document)
        self.assertTrue(any(fragment in e for e in errors), f"{fragment!r} not in {errors}")

    def test_committed_skeleton_is_valid_and_has_no_text(self):
        document = json.loads((REPO_ROOT / "evals/public-documents/manifest.json").read_text(encoding="utf-8"))
        errors, report = corpus.check_manifest(document)
        self.assertEqual(errors, [])
        self.assertEqual(document["excerpts"], [])
        self.assertEqual(report["groups"]["digital-agency"]["adopted"], 0)
        self.assertEqual(report["groups"]["digital-agency"]["sources"], {"planned": 5, "collected": 0})

    def test_complete_excerpt_passes_and_is_reported(self):
        errors, report = corpus.check_manifest(manifest(excerpt()))
        self.assertEqual(errors, [])
        group = report["groups"]["g"]
        self.assertEqual((group["adopted"], group["adopted_by_split"]), (1, {"tuning": 1, "final": 0}))
        self.assertEqual(group["adopted_without_questions"], ["e1"])

    def test_planned_source_cannot_supply_an_excerpt(self):
        self.assertError(manifest(excerpt(), sources=[source(status="planned")]), "collected でない")

    def test_source_requires_hash_dates_and_separate_licenses(self):
        broken = source(raw_sha256="xyz", retrieved_on="2026/10/16")
        del broken["license"]["bibliographic"]
        errors = self.errors(manifest(sources=[broken]))
        for fragment in ("raw_sha256", "retrieved_on", "書誌情報の利用条件"):
            self.assertTrue(any(fragment in e for e in errors), fragment)

    def test_body_license_needs_attribution_and_redistribution(self):
        no_notice = source()
        del no_notice["license"]["body"]["modification_notice"]
        self.assertError(manifest(sources=[no_notice]), "modification_notice")
        restricted = source()
        restricted["license"]["body"]["redistribution"] = "unknown"
        self.assertError(manifest(excerpt(), sources=[restricted]), "再配布が allowed でない")

    def test_text_hash_and_history_chain_are_checked(self):
        self.assertError(manifest(excerpt(text_sha256=RAW)), "text_sha256 と一致しない")
        history = [{"step": "extract", "tool": "t", "input_sha256": "b" * 64, "output_sha256": "c" * 64}]
        self.assertError(manifest(excerpt(transform_history=history)), "raw_sha256 と一致しない")
        broken = excerpt()
        broken["transform_history"] = [
            {"step": "extract", "tool": "t", "input_sha256": RAW, "output_sha256": "c" * 64},
            {"step": "select", "tool": "t", "input_sha256": "d" * 64, "output_sha256": broken["text_sha256"]}]
        self.assertError(manifest(broken), "連続していない")
        self.assertError(manifest(excerpt(transform_history=[])), "transform_history")

    def test_adopted_requires_human_confirmed_preserve_with_quote_in_text(self):
        for field in ("confirmed_by", "reason"):
            item = copy.deepcopy(excerpt()["preserve"][0])
            item[field] = ""
            self.assertError(manifest(excerpt(preserve=[item])), field)
        self.assertError(manifest(excerpt(preserve=[{**excerpt()["preserve"][0], "quote": "存在しない引用"}])), "quote")
        self.assertError(manifest(excerpt(preserve=[])), "preserve")
        self.assertError(manifest(excerpt(preserve=[{**excerpt()["preserve"][0], "strength": "optional"}])), "strength")

    def test_adopted_requires_provenance_of_selection(self):
        self.assertError(manifest(excerpt(third_party_content="unchecked")), "third_party_content")
        self.assertError(manifest(excerpt(locator="")), "locator")
        self.assertError(manifest(excerpt(correspondence={"checked_by": "x"})), "対応の確認者")
        self.assertError(manifest(excerpt(split="dev")), "split")
        self.assertError(manifest(excerpt(role="no_change_control")), "no_change_reason")

    def test_excluded_needs_reason_but_not_review_fields(self):
        stub = {k: v for k, v in excerpt().items() if k in ("id", "source_id", "text", "text_sha256", "transform_history")}
        self.assertError(manifest({**stub, "status": "excluded"}), "除外理由")
        self.assertEqual(self.errors(manifest({**stub, "status": "excluded", "exclusion_reason": "文脈が欠ける"})), [])

    def test_questions_reuse_comprehension_rules(self):
        question = {"id": "q1", "prompt": "何日以内か", "options": ["3営業日", "5営業日"], "answer_index": 1,
                    "evidence": "5営業日以内", "verified_by": "reviewer-a", "verification_reason": "原文と照合"}
        self.assertEqual(self.errors(manifest(excerpt(questions=[question]))), [])
        self.assertError(manifest(excerpt(questions=[{**question, "evidence": "原文にない"}])), "evidence")
        self.assertError(manifest(excerpt(questions=[{**question, "verified_by": ""}])), "verified_by")
        self.assertError(manifest(excerpt(questions=[question, question])), "重複")

    def test_same_source_or_lineage_cannot_straddle_splits(self):
        second = excerpt("e2", text=OTHER, split="final")
        self.assertError(manifest(excerpt(), second), "分割漏れ")
        sources = [source("s1"), source("s2", lineage_id="s1")]
        self.assertError(manifest(excerpt(), excerpt("e2", "s2", OTHER, split="final"), sources=sources), "分割漏れ")
        sources = [source("s1"), source("s2")]
        self.assertEqual(self.errors(manifest(excerpt(), excerpt("e2", "s2", OTHER, split="final"), sources=sources)), [])

    def test_identical_text_in_two_sources_cannot_straddle_splits(self):
        sources = [source("s1"), source("s2")]
        document = manifest(excerpt(), excerpt("e2", "s2", TEXT, split="final"), sources=sources)
        self.assertError(document, "同一本文")

    def test_duplicate_ids_and_unknown_group_are_rejected(self):
        self.assertError(manifest(excerpt(), excerpt()), "excerpt id が重複")
        self.assertError(manifest(sources=[source(), source()]), "source id が重複")
        self.assertError(manifest(sources=[source(group="other")]), "group")
        self.assertError({"schema_version": 2}, "schema_version")


class CasesTest(unittest.TestCase):
    def case(self, case_id="c1", text=TEXT, document_id="s1", **extra):
        return {"id": case_id, "document_id": document_id, "mode": "B", "request": "意味を保って推敲する",
                "audience": "申請担当者", "original": text, "candidate": text,
                "provenance": {"model": "m", "skill_version": "v"}, **extra}

    def check(self, cases, split="tuning", by="source", document=None):
        return corpus.check_cases(document or manifest(excerpt(), excerpt("e2", text=OTHER)), {"cases": cases}, split, by)[0]

    def test_matching_cases_pass(self):
        self.assertEqual(self.check([self.case()]), [])

    def test_original_must_be_the_adopted_text(self):
        errors = self.check([self.case(text=TEXT + "。")])
        self.assertTrue(any("一致しない" in e for e in errors))

    def test_final_excerpt_cannot_enter_tuning_run(self):
        document = manifest(excerpt(split="final"))
        errors = self.check([self.case()], document=document)
        self.assertTrue(any("final" in e and "tuning" in e for e in errors))

    def test_document_id_unit_is_checked(self):
        self.assertTrue(any("document_id" in e for e in self.check([self.case(document_id="other")])))
        self.assertEqual(self.check([self.case(document_id="e1")], by="excerpt"), [])

    def test_comprehension_runs_take_one_excerpt_per_source(self):
        errors = self.check([self.case(document_id="e1"), self.case("c2", OTHER, "e2")], by="excerpt")
        self.assertTrue(any("1出典につき1抜粋" in e for e in errors))

    def test_missing_generation_record_is_reported_not_failed(self):
        report = corpus.check_cases(manifest(excerpt()), {"cases": [self.case(provenance={})]}, "tuning", "source")[1]
        self.assertEqual(report["cases_without_model_or_skill_version"], 1)


class CliTest(unittest.TestCase):
    def run_cli(self, *args):
        return run_script(TOOL, *args)

    def test_skeleton_exits_zero(self):
        code, out, err = self.run_cli("--manifest", str(REPO_ROOT / "evals/public-documents/manifest.json"))
        self.assertEqual(code, 0, err)
        self.assertEqual(json.loads(out)["groups"]["digital-agency"]["adopted"], 0)

    def test_invalid_manifest_exits_one_and_unreadable_exits_two(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder, "bad.json")
            bad.write_text(json.dumps(manifest(excerpt(preserve=[]))), encoding="utf-8")
            code, _, err = self.run_cli("--manifest", str(bad))
            self.assertEqual(code, 1)
            self.assertIn("NG:", err)
            self.assertEqual(self.run_cli("--manifest", str(Path(folder, "missing.json")))[0], 2)

    def test_cases_require_split(self):
        code, _, _ = self.run_cli("--manifest", str(REPO_ROOT / "evals/public-documents/manifest.json"), "--cases", "x.json")
        self.assertEqual(code, 2)  # argparse の使用法エラー


if __name__ == "__main__":
    unittest.main()
