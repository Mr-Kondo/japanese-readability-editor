"""規則データ(data/*.json)、validate_kokugo_rules.py、規則の文書(references/kokugo-*.md)のテスト。

期待値は、公式資料の原文から決めた(tests/kokugo_sources_data.py と、各テストの docstring)。
"""

import json
import re
import shutil
import unittest
from pathlib import Path

import kokugo_sources_data as src
from helpers import SCRIPTS_DIR, SKILL_DIR, load_module, run_script, temporary_directory

engine = load_module("kokugo_engine", SCRIPTS_DIR / "kokugo_engine.py")
validator = load_module("validate_kokugo_rules", SCRIPTS_DIR / "validate_kokugo_rules.py")
SCRIPT = SCRIPTS_DIR / "validate_kokugo_rules.py"
DATA = SKILL_DIR / "data"
REFERENCES = SKILL_DIR / "references"


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


RULES = load("kokugo-rules.json")
SOURCES = load("kokugo-sources.json")


def rule(rule_id):
    return next(r for r in RULES["rules"] if r["id"] == rule_id)


def source(source_id):
    return next(s for s in SOURCES["sources"] if s["id"] == source_id)


class RealDataIsValidTest(unittest.TestCase):
    def test_the_validator_passes_on_the_shipped_data(self):
        code, out, err = run_script(SCRIPT)
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("OK", out)

    def test_json_output(self):
        code, out, _ = run_script(SCRIPT, "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": True, "errors": [], "warnings": []})

    def test_the_exit_codes_are_documented(self):
        code, out, _ = run_script(SCRIPT, "--help")
        self.assertEqual(code, 0)
        for fragment in ("0=", "1=", "2="):
            self.assertIn(fragment, out)


class InvalidDataIsDetectedTest(unittest.TestCase):
    """要件10: 不正な規則データを検証スクリプトが検出する。"""

    def validate(self, mutate, file="kokugo-rules.json"):
        with temporary_directory() as tmp:
            target = Path(tmp) / "data"
            shutil.copytree(DATA, target)
            path = target / file
            doc = json.loads(path.read_text(encoding="utf-8"))
            mutate(doc)
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            code, out, err = run_script(SCRIPT, "--data-dir", str(target))
            return code, out + err

    def assert_invalid(self, mutate, fragment, file="kokugo-rules.json"):
        code, text = self.validate(mutate, file)
        self.assertEqual(code, 1, text)
        self.assertIn(fragment, text)
        self.assertNotIn("Traceback", text, "検証は、不備を例外ではなく報告として返す")

    @staticmethod
    def r(doc, rule_id):
        return next(x for x in doc["rules"] if x["id"] == rule_id)

    def test_duplicate_rule_ids(self):
        self.assert_invalid(lambda d: d["rules"][1].__setitem__("id", d["rules"][0]["id"]), "duplicate rule id")

    def test_malformed_rule_id(self):
        self.assert_invalid(lambda d: d["rules"][0].__setitem__("id", "RULE-1"), "id must look like")

    def test_a_rule_without_a_source(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("sources", []), "must cite at least one source")

    def test_a_dangling_source_reference(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["sources"][0].__setitem__("source_id", "NOPE-1"), "dangling reference")

    def test_a_missing_locator(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["sources"][0].__setitem__("locator", ""), "missing locator")

    def test_a_pdf_source_without_pages(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["sources"][1].pop("pages"), "record the pages")

    def test_pages_in_a_wrong_form_or_outside_the_pdf(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["sources"][1].__setitem__("pages", "p.4"), "is not in the form")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["sources"][1].__setitem__("pages", "PDF p.99"), "outside the PDF")

    def test_a_missing_required_field(self):
        for key in ("title", "summary", "machine_detectable", "needs_context_scope"):
            with self.subTest(key=key):
                self.assert_invalid(lambda d, key=key: self.r(d, "KOKUGO-KANJI-001").pop(key), f"missing '{key}'")

    def test_missing_skill_decisions(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").pop("skill_decisions"), "skill_decisions")

    def test_missing_conditions_exceptions_or_examples(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("conditions", []), "conditions")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("exceptions", []), "exceptions")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["examples"].__setitem__("keep", []), "fix examples and keep examples")

    def test_an_invalid_profile_set(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["profiles"].pop("official"), "profiles must define exactly")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["profiles"].__setitem__("strict", {"category": "error"}), "profiles must define exactly")

    def test_an_invalid_category_or_basis(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["profiles"]["official"].__setitem__("category", "fatal"), "category must be one of")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["profiles"]["official"].__setitem__("category", "excluded"), "category must be one of")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001")["profiles"]["official"].__setitem__("basis", "guess"), "basis must be one of")

    def test_invalid_family_provenance_automation(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("family", "other"), "family must be one of")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("provenance", "rumor"), "provenance must be one of")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("automation", "magic"), "automation must be one of")

    def test_an_invalid_protected_kind(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANJI-001").__setitem__("protected", ["code", "emoji"]), "protected must be a list")

    def test_a_broken_regular_expression(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANA-001")["detection"]["entries"][0].__setitem__("pattern", "(?P<x"), "invalid regular expression")

    def test_a_pattern_that_matches_the_empty_string(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-KANA-001")["detection"]["entries"][0].__setitem__("pattern", "a*"), "empty string")

    def test_a_candidate_template_that_names_a_missing_group(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-OKURI-001")["detection"]["entries"][0].__setitem__("candidates", ["\\g<nope>"]),
                            "refers to group 'nope'")

    def test_an_ambiguous_entry_without_a_reason(self):
        def mutate(d):
            entry = next(e for e in self.r(d, "KOKUGO-KANJI-005")["detection"]["entries"] if e.get("ambiguous"))
            entry["ambiguity"] = ""

        self.assert_invalid(mutate, "must say why")

    def test_an_error_needs_a_cabinet_notice_or_directive(self):
        def mutate(d):
            self.r(d, "KOKUGO-EXPR-001")["profiles"]["official"].update({"category": "error", "basis": "source"})

        self.assert_invalid(mutate, "'error' needs a cabinet notice or cabinet directive")

    def test_a_skill_policy_rule_cannot_produce_an_error(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-CONSIST-001")["profiles"]["official"].__setitem__("category", "error"), "cannot produce 'error'")

    def test_an_error_must_be_based_on_the_source_text(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-OKURI-003")["profiles"]["official"].__setitem__("basis", "skill-policy"), "basis: source")

    def test_a_skill_policy_rule_must_mark_every_profile_as_skill_policy(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-CONSIST-001")["profiles"]["official"].__setitem__("basis", "source"), "must mark every profile basis")

    def test_the_omitted_form_must_be_a_subsequence_of_the_full_form(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-OKURI-003")["detection"]["entries"][0].__setitem__("candidates", ["別の語"]), "with only hiragana removed")

    def test_a_joyo_check_that_contradicts_the_table(self):
        def mutate(d):
            entry = next(e for e in self.r(d, "KOKUGO-KANJI-002")["detection"]["entries"] if e.get("joyo_check"))
            entry["joyo_check"] = [{"char": "経", "kun_prefix": "へ"}]  # 経は訓『へる』が表にある

        self.assert_invalid(mutate, "so 'へ")

    def test_a_reference_only_rule_must_not_look_like_an_automatic_check(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-REF-001").__setitem__("detection", {"kind": "patterns", "entries": []}), "must not define 'detection'")
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-REF-001").pop("not_checked"), "needs 'not_checked'")

    def test_a_keep_example_that_the_rule_flags(self):
        def mutate(d):
            self.r(d, "KOKUGO-KANA-001")["examples"]["keep"].append({"text": "こんにちわ、田中です。", "profiles": ["official"], "reason": "x"})

        self.assert_invalid(mutate, "must not be flagged")

    def test_a_fix_example_that_the_rule_does_not_detect(self):
        def mutate(d):
            self.r(d, "KOKUGO-KANA-001")["examples"]["fix"].append({"before": "問題なし。", "after": "問題なし。", "profile": "official"})

        self.assert_invalid(mutate, "is not detected by this rule")

    def test_a_fix_example_whose_after_text_is_still_flagged(self):
        def mutate(d):
            self.r(d, "KOKUGO-KANA-001")["examples"]["fix"].append({"before": "こんにちわ。", "after": "こんにちわ。", "profile": "official"})

        self.assert_invalid(mutate, "still gets a")

    def test_an_unused_source(self):
        def mutate(d):
            for r in d["rules"]:
                r["sources"] = [s for s in r.get("sources", []) if s["source_id"] != "NAIKAKU-NOTICE-2022"]

        self.assert_invalid(mutate, "not cited by any rule")

    def test_source_records(self):
        def sources_mutation(mutate):
            return lambda d: mutate(next(s for s in d["sources"] if s["id"] == "NAIKAKU-KUNREI-2010"))

        self.assert_invalid(sources_mutation(lambda s: s.__setitem__("url", "https://example.com/x")), "official URL", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.__setitem__("issued_on", "2010/11/30")), "'issued_on' must be a date", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.__setitem__("verified_on", "")), "'verified_on' must be a date", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.__setitem__("kind", "噂")), "kind must be one of", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.__setitem__("retrieved_files", [])), "retrieved_files must record", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s["retrieved_files"][0].__setitem__("sha256", "abc")), "64 lowercase hex", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s["retrieved_files"][0].pop("pages")), "page count", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.pop("issuer")), "missing 'issuer'", "kokugo-sources.json")
        self.assert_invalid(sources_mutation(lambda s: s.pop("scope")), "missing 'scope'", "kokugo-sources.json")

    def test_a_duplicate_source_id(self):
        self.assert_invalid(lambda d: d["sources"][1].__setitem__("id", d["sources"][0]["id"]), "duplicate source id", "kokugo-sources.json")

    def test_missing_usage_terms(self):
        self.assert_invalid(lambda d: d.pop("usage_terms"), "usage_terms", "kokugo-sources.json")

    def test_the_joyo_table_must_have_the_official_count(self):
        self.assert_invalid(lambda d: d.__setitem__("chars", d["chars"][:-1]), "exactly 2136", "joyo-kanji.json")

    def test_a_joyo_character_without_a_reading(self):
        self.assert_invalid(lambda d: d["readings"].__setitem__("亜", []), "without any reading", "joyo-kanji.json")

    def test_derived_data_must_be_tied_to_the_recorded_file(self):
        self.assert_invalid(lambda d: d["derived_from"].__setitem__("sha256", "0" * 64), "does not match the recorded official file", "joyo-kanji.json")
        self.assert_invalid(lambda d: d["derived_from"].__setitem__("sha256", "0" * 64), "does not match the recorded official file", "ijidokun.json")

    def test_ijidokun_entries_must_run_without_gaps(self):
        self.assert_invalid(lambda d: d["entries"].pop(5), "exactly 133", "ijidokun.json")

    def test_a_consistency_group_needs_two_forms(self):
        self.assert_invalid(lambda d: self.r(d, "KOKUGO-CONSIST-001")["detection"]["groups"][0].__setitem__("forms", d["rules"][0].get("x", [])[:1]), "at least two forms")

    def test_unreadable_data_is_exit_code_2(self):
        with temporary_directory() as tmp:
            target = Path(tmp) / "data"
            shutil.copytree(DATA, target)
            (target / "kokugo-rules.json").write_text("{ not json", encoding="utf-8")
            code, out, err = run_script(SCRIPT, "--data-dir", str(target))
            self.assertEqual(code, 2)
            self.assertIn("invalid JSON", err)
            (target / "kokugo-rules.json").unlink()
            code, out, err = run_script(SCRIPT, "--data-dir", str(target))
            self.assertEqual(code, 2)
            self.assertIn("cannot read", err)

    def test_the_checker_refuses_unusable_rule_data(self):
        with temporary_directory() as tmp:
            target = Path(tmp) / "data"
            shutil.copytree(DATA, target)
            doc = load("kokugo-rules.json")
            doc["rules"][0]["detection"] = {"kind": "patterns", "entries": [{"pattern": "(?P<x"}]}
            (target / "kokugo-rules.json").write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            code, _, err = run_script(SCRIPTS_DIR / "check_kokugo.py", str(SKILL_DIR / "SKILL.md"), "--data-dir", str(target))
            self.assertEqual(code, 2)
            self.assertIn("invalid regular expression", err)


class RuleDataMatchesThePrimarySourcesTest(unittest.TestCase):
    """規則データが、公式資料に書かれた事実と食い違っていないこと。期待値は資料の原文から写した。"""

    def test_the_186_words_are_exactly_the_words_of_the_cabinet_directive(self):
        entries = rule("KOKUGO-OKURI-003")["detection"]["entries"]
        omitted = [e["candidates"][0] for e in entries]
        self.assertEqual(sorted(omitted), sorted(src.KUNREI_186))
        self.assertEqual(len(omitted), 186)  # 考え方 解説 Ⅰ-2イ: 186語

    def test_every_full_form_adds_only_hiragana_to_the_directive_word(self):
        for entry in rule("KOKUGO-OKURI-003")["detection"]["entries"]:
            full, omitted = re.sub(r"\\(.)", r"\1", entry["pattern"]), entry["candidates"][0]
            self.assertNotEqual(full, omitted)
            self.assertTrue(validator.is_subsequence_with_hiragana(omitted, full), (omitted, full))

    def test_an_error_is_only_possible_where_a_cabinet_notice_or_directive_is_cited(self):
        kinds = {s["id"]: s["kind"] for s in SOURCES["sources"]}
        error_rules = [r for r in RULES["rules"] if any(m["category"] == "error" for m in r.get("profiles", {}).values())]
        self.assertTrue(error_rules)
        for r in error_rules:
            self.assertTrue(any(kinds[s["source_id"]] in ("内閣告示", "内閣訓令") for s in r["sources"]), r["id"])
            self.assertNotEqual(r["provenance"], "skill-policy", r["id"])
            for p, m in r["profiles"].items():
                if m["category"] == "error":
                    self.assertEqual(m["basis"], "source", (r["id"], p))

    def test_which_rules_can_be_an_error(self):
        """error になりうる規則は、現代仮名遣いの明確な誤りと、内閣訓令の186語に限る。建議・報告・答申だけの規則は、error にならない。"""
        error_capable = sorted(r["id"] for r in RULES["rules"] if any(m["category"] == "error" for m in r.get("profiles", {}).values()))
        self.assertEqual(error_capable, ["KOKUGO-KANA-001", "KOKUGO-KANA-002", "KOKUGO-KANA-003", "KOKUGO-OKURI-003"])

    def test_rules_resting_only_on_a_proposal_report_or_answer_never_produce_an_error(self):
        weak = {"建議", "報告", "答申", "通知"}
        kinds = {s["id"]: s["kind"] for s in SOURCES["sources"]}
        for r in RULES["rules"]:
            if r["automation"] != "detect":
                continue
            if all(kinds[s["source_id"]] in weak for s in r["sources"]):
                self.assertNotIn("error", {m["category"] for m in r["profiles"].values()}, r["id"])

    def test_the_ijidokun_rule_never_goes_beyond_a_reference(self):
        """異字同訓 前書き3: 一つの参考。error・recommendation を出さない。"""
        categories = {m["category"] for m in rule("KOKUGO-IJIDOKUN-001")["profiles"].values()}
        self.assertEqual(categories, {"accepted_variant", "needs_context"})
        self.assertEqual(len(rule("KOKUGO-IJIDOKUN-001")["detection"]["entry_ids"]), 16)

    def test_kana_rules_for_permitted_forms_are_accepted_in_every_profile(self):
        self.assertEqual({m["category"] for m in rule("KOKUGO-KANA-004")["profiles"].values()}, {"accepted_variant"})

    def test_the_okurigana_permitted_forms_are_never_an_error(self):
        for rid in ("KOKUGO-OKURI-001", "KOKUGO-OKURI-002"):
            self.assertNotIn("error", {m["category"] for m in rule(rid)["profiles"].values()})

    def test_the_length_numbers_are_not_attributed_to_the_agency(self):
        text = " ".join(rule("KOKUGO-REF-005")["skill_decisions"])
        self.assertIn("文化庁の基準ではない", text)
        self.assertIn("50〜60字", text)  # 考え方 解説 Ⅲ-3ア(PDF p.44)が述べるのは、この留意だけ

    def test_every_detect_rule_has_provenance_and_a_separate_list_of_skill_decisions(self):
        for r in RULES["rules"]:
            self.assertIn(r["provenance"], ("primary-source", "primary-source-derived", "skill-policy"))
            self.assertTrue(r["skill_decisions"], r["id"])
        self.assertTrue(any(r["provenance"] == "skill-policy" for r in RULES["rules"]))

    def test_reference_only_sources_are_not_the_basis_of_automatic_rules(self):
        reference_only = {s["id"] for s in SOURCES["sources"] if s["role"] == "reference-only"}
        self.assertEqual(reference_only, {"NAIKAKU-ROMAJI-2025", "NAIKAKU-NOTICE-2022", "BUNKA-KEIGO-2007"})
        for r in RULES["rules"]:
            if r["automation"] == "detect":
                self.assertFalse({s["source_id"] for s in r["sources"]} <= reference_only, r["id"])
        for rid, sid in (("KOKUGO-REF-001", "BUNKA-KEIGO-2007"), ("KOKUGO-REF-002", "NAIKAKU-ROMAJI-2025")):
            self.assertIn(sid, {s["source_id"] for s in rule(rid)["sources"]})
            self.assertEqual(rule(rid)["automation"], "reference-only")


class SourceRecordsTest(unittest.TestCase):
    """出典の記録が、公式資料の原文にある事実と一致すること(正式名称、発出主体、種別、日付、URL、確認日)。"""

    EXPECTED = {
        "NAIKAKU-JOYO-2010": ("常用漢字表", "平成22年内閣告示第2号", "内閣告示", "2010-11-30"),
        "NAIKAKU-KUNREI-2010": ("公用文における漢字使用等について", "平成22年内閣訓令第1号(別紙)", "内閣訓令", "2010-11-30"),
        "NAIKAKU-GENDAIKANA-1986": ("現代仮名遣い", "昭和61年内閣告示第1号", "内閣告示", "1986-07-01"),
        "NAIKAKU-OKURIGANA-1973": ("送り仮名の付け方", "昭和48年内閣告示第2号", "内閣告示", "1973-06-18"),
        "NAIKAKU-GAIRAI-1991": ("外来語の表記", "平成3年内閣告示第2号", "内閣告示", "1991-06-28"),
        "NAIKAKU-ROMAJI-2025": ("ローマ字のつづり方", "令和7年内閣告示第4号", "内閣告示", "2025-12-22"),
        "BUNKA-GUIDE-2022": ("公用文作成の考え方(建議)", "令和4年1月7日 文化審議会建議(付: 解説)", "建議", "2022-01-07"),
        "NAIKAKU-NOTICE-2022": ("「公用文作成の考え方」の周知について", "令和4年1月11日内閣文第1号", "通知", "2022-01-11"),
        "BUNKA-IJIDOKUN-2014": ("「異字同訓」の漢字の使い分け例(報告)", "平成26年2月21日 文化審議会国語分科会報告", "報告", "2014-02-21"),
        "BUNKA-KEIGO-2007": ("敬語の指針(答申)", "平成19年2月2日 文化審議会答申", "答申", "2007-02-02"),
    }

    def test_the_registry_has_exactly_the_documented_sources(self):
        self.assertEqual({s["id"] for s in SOURCES["sources"]}, set(self.EXPECTED))

    def test_names_designations_kinds_and_dates(self):
        for sid, (title, designation, kind, issued) in self.EXPECTED.items():
            s = source(sid)
            with self.subTest(source=sid):
                self.assertEqual((s["title"], s["designation"], s["kind"], s["issued_on"]), (title, designation, kind, issued))

    def test_issuers(self):
        for sid in ("NAIKAKU-JOYO-2010", "NAIKAKU-KUNREI-2010", "NAIKAKU-GENDAIKANA-1986", "NAIKAKU-OKURIGANA-1973", "NAIKAKU-GAIRAI-1991", "NAIKAKU-ROMAJI-2025"):
            self.assertEqual(source(sid)["issuer"], "内閣総理大臣", sid)
        self.assertEqual(source("NAIKAKU-NOTICE-2022")["issuer"], "内閣官房長官")
        self.assertEqual(source("BUNKA-GUIDE-2022")["issuer"], "文化審議会")
        self.assertEqual(source("BUNKA-IJIDOKUN-2014")["issuer"], "文化審議会国語分科会")

    def test_every_source_was_read_from_its_bytes_after_it_was_issued(self):
        """確認日は再確認のたびに変わるので、値ではなく関係を確かめる: 原本を取得して読み、確認日は発出日より後で、一覧の確認日が最新。"""
        for s in SOURCES["sources"]:
            self.assertEqual(s["verification"], "bytes-fetched-and-read", s["id"])
            self.assertGreaterEqual(s["verified_on"], s["issued_on"], s["id"])
        self.assertEqual(SOURCES["verified_on"], max(s["verified_on"] for s in SOURCES["sources"]))

    def test_urls_are_official_and_files_have_a_hash(self):
        for s in SOURCES["sources"]:
            self.assertTrue(s["url"].startswith("https://www.bunka.go.jp/"), s["id"])
            for f in s["retrieved_files"]:
                self.assertTrue(f["url"].startswith("https://www.bunka.go.jp/"), f["url"])
                self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(f["size"], 0)

    def test_the_entry_urls_given_by_the_user_are_recorded(self):
        urls = {f["url"] for s in SOURCES["sources"] for f in s["retrieved_files"]} | {s["url"] for s in SOURCES["sources"]}
        for url in (
            "https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/93651301_01.pdf",
            "https://www.bunka.go.jp/seisaku/bunkashingikai/kokugo/hokoku/pdf/ijidokun_140221.pdf",
            "https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/naikaku/roma/index2.html",
            "https://www.bunka.go.jp/kokugo_nihongo/sisaku/joho/joho/kijun/sanko/koyobun/index.html",
        ):
            self.assertIn(url, urls)

    def test_the_pdf_page_counts_recorded_for_the_main_documents(self):
        pages = {sid: next(f["pages"] for f in source(sid)["retrieved_files"] if f["format"] == "pdf")
                 for sid in ("NAIKAKU-JOYO-2010", "NAIKAKU-KUNREI-2010", "BUNKA-GUIDE-2022", "BUNKA-IJIDOKUN-2014", "NAIKAKU-ROMAJI-2025", "BUNKA-KEIGO-2007")}
        self.assertEqual(pages, {"NAIKAKU-JOYO-2010": 164, "NAIKAKU-KUNREI-2010": 5, "BUNKA-GUIDE-2022": 63,
                                 "BUNKA-IJIDOKUN-2014": 53, "NAIKAKU-ROMAJI-2025": 7, "BUNKA-KEIGO-2007": 82})

    def test_derived_data_is_tied_to_the_recorded_files(self):
        joyo, ijidokun = load("joyo-kanji.json"), load("ijidokun.json")
        joyo_pdf = next(f for f in source("NAIKAKU-JOYO-2010")["retrieved_files"] if f["format"] == "pdf")
        iji_pdf = next(f for f in source("BUNKA-IJIDOKUN-2014")["retrieved_files"] if f["format"] == "pdf")
        self.assertEqual(joyo["derived_from"]["sha256"], joyo_pdf["sha256"])
        self.assertEqual(ijidokun["derived_from"]["sha256"], iji_pdf["sha256"])
        self.assertEqual((joyo["count"], len(joyo["chars"])), (2136, 2136))
        self.assertEqual((ijidokun["count"], len(ijidokun["entries"])), (133, 133))

    def test_usage_terms_are_recorded(self):
        terms = SOURCES["usage_terms"]
        self.assertIn("mext.go.jp", terms["url"])
        self.assertIn("加工", terms["note"])


class DocumentsStayConsistentTest(unittest.TestCase):
    """references/kokugo-*.md と SKILL.md が、規則データと食い違わないこと。"""

    @staticmethod
    def read(path):
        return (path).read_text(encoding="utf-8")

    def test_the_sources_document_lists_every_source_with_its_record(self):
        text = self.read(REFERENCES / "kokugo-sources.md")
        for s in SOURCES["sources"]:
            for value in (s["id"], s["title"], s["designation"], s["issuer"], s["kind"], s["issued_on"], s["url"], s["verified_on"]):
                self.assertIn(value, text, (s["id"], value))
            for f in s["retrieved_files"]:
                self.assertIn(f["sha256"], text, f["url"])
                self.assertIn(f["url"], text)

    def test_the_sources_document_separates_the_agencys_rules_from_the_skills_judgment(self):
        text = self.read(REFERENCES / "kokugo-sources.md")
        self.assertIn("この skill の運用判断", text)
        self.assertIn("文化庁の基準ではない", text)
        self.assertIn("python3 tools/update_kokugo_sources.py verify", text)
        self.assertIn("加工", text)
        self.assertIn("取得できなかった資料", text)

    def test_the_notation_document_lists_every_rule(self):
        text = self.read(REFERENCES / "kokugo-notation.md")
        for r in RULES["rules"]:
            self.assertIn(f"`{r['id']}`", text, r["id"])

    def test_the_notation_document_shows_the_profile_categories(self):
        text = self.read(REFERENCES / "kokugo-notation.md")
        row = next(line for line in text.splitlines() if line.startswith("| `KOKUGO-OKURI-003`"))
        self.assertIn("accepted_variant | accepted_variant | **error**", row)
        row = next(line for line in text.splitlines() if line.startswith("| `KOKUGO-GAIRAI-001`"))
        self.assertIn("accepted_variant | recommendation | recommendation", row)

    def test_the_policy_document_states_the_required_principles(self):
        text = self.read(REFERENCES / "kokugo-policy.md")
        for fragment in ("`general-tech`(既定)", "`public-explanation`", "`official`", "文体が堅いという理由だけで `official` にしない",
                         "`error`", "`recommendation`", "`accepted_variant`", "`needs_context`", "`excluded`",
                         "許容形や適用範囲外の表記を、誤りとして報告しない", "音訓まで確認済みとしない", "世論調査の多数派・少数派だけで、正誤を決めない",
                         "黙って片方を適用せず", "多数派であることを理由に、明確な誤りを広げない", "国語の規則を理由に、文言・句読点・語順を変更しない",
                         "文化庁の基準ではない", "50〜60字", "用語集", "内閣告示", "内閣訓令", "建議"):
            self.assertIn(fragment, text)

    def test_the_official_document_matches_the_rules(self):
        text = self.read(REFERENCES / "kokugo-official.md")
        for rid in ("KOKUGO-OKURI-003", "KOKUGO-KANJI-005", "KOKUGO-KANJI-003", "KOKUGO-GAIRAI-001", "KOKUGO-NUM-001"):
            self.assertIn(rid, text)
        self.assertIn("文体が堅いという理由だけでは `official` にしない", text)
        self.assertIn("固有名詞", text)

    def test_the_old_majority_rule_was_replaced(self):
        text = self.read(REFERENCES / "readability-rules.md")
        self.assertNotIn("文書の中で多数派の表記に合わせる。引用", text)
        self.assertIn("多数派であることを理由に、明確な誤りを広げない", text)
        self.assertIn("明示された表記基準と、組織の用語集があれば、それを確認する", text)
        self.assertIn("複数の表記が許容される場合にだけ、文書内の統一を判断材料にする", text)

    def test_skill_md_carries_the_procedure_and_the_references(self):
        text = self.read(SKILL_DIR / "SKILL.md")
        for fragment in ("`general-tech`（既定）", "`public-explanation`", "`official`", "文体が堅いという理由だけで `official` にしない",
                         "check_kokugo.py", "--profile general-tech", "compare_rewrite.py", "verify_preservation.py --strict",
                         "国語の規則を理由に文言・句読点・語順を変更しない", "検査を実行したとは報告しない", "保証しない",
                         "多数派という理由で、明確な誤りを広げない", "許容形と適用範囲外の表記は、誤りとして直さない", "文化庁の基準ではない"):
            self.assertIn(fragment, text)
        for name in ("kokugo-policy.md", "kokugo-notation.md", "kokugo-official.md", "kokugo-sources.md", "kokugo-cases.md"):
            self.assertIn(name, text)

    def test_skill_md_does_not_carry_the_rule_text(self):
        """規則の全文を SKILL.md に詰め込まない: 個々の規則の語や ID を持ち込まない。"""
        text = self.read(SKILL_DIR / "SKILL.md")
        self.assertNotIn("KOKUGO-", text)
        for word in ("申込み", "取扱い", "いなづま", "ヶ所"):
            self.assertNotIn(word, text)
