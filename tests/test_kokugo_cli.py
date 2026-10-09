"""scripts/check_kokugo.py(コマンドライン)の統合テスト。

出力の形式(JSON のキー)、終了コード、再現性、入力が変わらないこと、ネットワークなしで動くこと。
"""

import contextlib
import hashlib
import io
import json
import os
import socket
import unittest
from pathlib import Path

from helpers import FIXTURES, SCRIPTS_DIR, load_module, run_script, temporary_directory

SCRIPT = SCRIPTS_DIR / "check_kokugo.py"
KOKUGO = FIXTURES / "kokugo"
engine = load_module("kokugo_engine", SCRIPTS_DIR / "kokugo_engine.py")
cli = load_module("check_kokugo", SCRIPTS_DIR / "check_kokugo.py")

# 出力の形式。ここを変えるときは schema_version を上げる。
TOP_KEYS = ["schema_version", "tool", "profile", "rules_version", "fail_on", "exit_code", "files", "summary", "coverage"]
FILE_KEYS = ["file", "sha256", "markdown", "findings", "counts"]
FINDING_KEYS = ["rule_id", "category", "line", "column", "end_line", "end_column", "offset", "length", "text", "candidates", "title",
                "reason", "reason_code", "source_ids", "provenance", "detail"]
COVERAGE_KEYS = ["profile", "tokenizer", "rules_checked", "rules_reference_only", "not_checked", "limits", "glossary", "disclaimer"]
CATEGORY_KEYS = ["error", "recommendation", "needs_context", "accepted_variant", "excluded"]


def run_json(*args, **kwargs):
    code, out, err = run_script(SCRIPT, *args, "--json", **kwargs)
    return code, json.loads(out) if out.strip() else None, err


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class JsonFormatTest(unittest.TestCase):
    def setUp(self):
        code, self.report, _ = run_json(str(KOKUGO / "official_sample.md"), "--profile", "official")
        self.assertEqual(code, 1)

    def test_top_level_keys_and_order_are_fixed(self):
        self.assertEqual(list(self.report), TOP_KEYS)
        self.assertEqual(self.report["schema_version"], 1)
        self.assertEqual(self.report["tool"], "check_kokugo.py")
        self.assertEqual(self.report["profile"], "official")
        self.assertEqual(self.report["fail_on"], "error")

    def test_file_entry_keys_are_fixed(self):
        entry = self.report["files"][0]
        self.assertEqual(list(entry), FILE_KEYS)
        self.assertEqual(entry["sha256"], sha256(KOKUGO / "official_sample.md"))
        self.assertTrue(entry["markdown"])
        self.assertEqual(list(entry["counts"]), CATEGORY_KEYS)

    def test_every_finding_has_exactly_the_fixed_keys(self):
        findings = self.report["files"][0]["findings"]
        self.assertTrue(findings)
        for finding in findings:
            self.assertEqual(list(finding), FINDING_KEYS)
            self.assertIn(finding["category"], CATEGORY_KEYS)
            self.assertIn(finding["provenance"], ("primary-source", "primary-source-derived", "skill-policy"))
            self.assertIsInstance(finding["candidates"], list)
            self.assertIsInstance(finding["source_ids"], list)
            self.assertTrue(finding["source_ids"])

    def test_summary_is_the_sum_of_the_file_counts(self):
        self.assertEqual(list(self.report["summary"]), CATEGORY_KEYS)
        for category in CATEGORY_KEYS:
            self.assertEqual(self.report["summary"][category], sum(f["counts"][category] for f in self.report["files"]))
        entry = self.report["files"][0]
        for category in CATEGORY_KEYS:
            self.assertEqual(entry["counts"][category], sum(1 for f in entry["findings"] if f["category"] == category))

    def test_a_known_finding_has_the_expected_values(self):
        """official では、見出しの『申し込みの』(5行目、直後が『の』)と本文の『申し込みを』(7行目)が error。位置・区分・候補・出典。"""
        found = [f for f in self.report["files"][0]["findings"] if f["rule_id"] == "KOKUGO-OKURI-003" and f["category"] == "error"]
        self.assertEqual([(f["line"], f["column"], f["text"], f["candidates"]) for f in found],
                         [(5, 3, "申し込み", ["申込み"]), (7, 1, "申し込み", ["申込み"])])
        self.assertIn("NAIKAKU-KUNREI-2010", found[1]["source_ids"])

    def test_exit_code_in_the_report_matches_the_process(self):
        self.assertEqual(self.report["exit_code"], 1)
        code, report, _ = run_json(str(KOKUGO / "clean.md"))
        self.assertEqual((code, report["exit_code"]), (0, 0))

    def test_coverage_names_what_was_and_was_not_checked(self):
        coverage = self.report["coverage"]
        self.assertEqual(list(coverage), COVERAGE_KEYS)
        self.assertEqual(coverage["tokenizer"], "none")
        checked = {r["id"] for r in coverage["rules_checked"]}
        reference = {r["id"] for r in coverage["rules_reference_only"]}
        self.assertFalse(checked & reference, "参照のみの規則を、検査済みとして示してはならない")
        self.assertTrue({"KOKUGO-REF-001", "KOKUGO-REF-002"} <= reference)
        self.assertTrue(all(r["id"].startswith("KOKUGO-") for r in coverage["rules_checked"]))
        for item in coverage["rules_reference_only"]:
            self.assertTrue(item["not_checked"])
        self.assertTrue(any("敬語" in line for line in coverage["not_checked"]))
        self.assertTrue(any("ローマ字" in line for line in coverage["not_checked"]))
        self.assertTrue(any("形態素解析" in line for line in coverage["limits"]))
        self.assertIn("保証しない", coverage["disclaimer"])

    def test_the_json_includes_accepted_variants_and_excluded_findings(self):
        categories = {f["category"] for f in self.report["files"][0]["findings"]}
        self.assertTrue({"error", "recommendation", "needs_context", "excluded"} <= categories)

    def test_output_is_utf8_json_without_escaping_japanese(self):
        code, out, _ = run_script(SCRIPT, str(KOKUGO / "has_error.md"), "--json")
        self.assertIn("こんにちわ", out)
        self.assertEqual(json.loads(out)["files"][0]["findings"][0]["text"], "こんにちわ")


class ExitCodeTest(unittest.TestCase):
    """終了コード: 0=指定水準以上の指摘なし、1=あり、2=検査を完了できなかった。"""

    def code(self, *args):
        return run_script(SCRIPT, *args)[0]

    def test_zero_when_nothing_to_confirm(self):
        for profile in ("general-tech", "public-explanation", "official"):
            self.assertEqual(self.code(str(KOKUGO / "clean.md"), "--profile", profile), 0, profile)

    def test_one_when_there_is_an_error(self):
        for profile in ("general-tech", "public-explanation", "official"):
            self.assertEqual(self.code(str(KOKUGO / "has_error.md"), "--profile", profile), 1, profile)

    def test_recommendations_do_not_fail_by_default(self):
        self.assertEqual(self.code(str(KOKUGO / "only_recommendation.md"), "--profile", "official"), 0)

    def test_fail_on_recommendation_fails_on_a_recommendation_and_on_an_error(self):
        self.assertEqual(self.code(str(KOKUGO / "only_recommendation.md"), "--profile", "official", "--fail-on", "recommendation"), 1)
        self.assertEqual(self.code(str(KOKUGO / "has_error.md"), "--fail-on", "recommendation"), 1)
        self.assertEqual(self.code(str(KOKUGO / "clean.md"), "--profile", "official", "--fail-on", "recommendation"), 0)

    def test_needs_context_does_not_fail_by_default_but_can(self):
        path = str(KOKUGO / "only_needs_context.md")
        self.assertEqual(self.code(path, "--profile", "official"), 0)
        self.assertEqual(self.code(path, "--profile", "official", "--fail-on", "recommendation"), 0)
        self.assertEqual(self.code(path, "--profile", "official", "--fail-on", "needs_context"), 1)

    def test_accepted_variants_never_fail(self):
        path = str(KOKUGO / "only_recommendation.md")
        self.assertEqual(self.code(path, "--profile", "general-tech", "--fail-on", "needs_context"), 0)

    def test_never_always_returns_zero_for_findings(self):
        self.assertEqual(self.code(str(KOKUGO / "has_error.md"), "--fail-on", "never"), 0)

    def test_two_when_a_file_is_missing(self):
        code, out, err = run_script(SCRIPT, str(KOKUGO / "missing.md"))
        self.assertEqual(code, 2)
        self.assertIn("not found", err)

    def test_two_even_when_some_files_were_checked(self):
        code, out, err = run_json(str(KOKUGO / "has_error.md"), str(KOKUGO / "missing.md"))
        self.assertEqual(code, 2)
        self.assertEqual(code, 2)
        self.assertEqual(len(out["files"]), 1)  # 読めたファイルの結果は出す
        self.assertEqual(out["exit_code"], 2)

    def test_two_when_the_file_is_not_utf8(self):
        with temporary_directory() as tmp:
            path = Path(tmp.name if hasattr(tmp, "name") else tmp) / "bad.md"
            path.write_bytes("あ".encode("shift_jis") + b"\n")
            self.assertEqual(self.code(str(path)), 2)

    def test_two_without_input_paths(self):
        code, _, err = run_script(SCRIPT)
        self.assertEqual(code, 2)
        self.assertIn("no input paths", err)

    def test_two_for_an_unknown_profile(self):
        self.assertEqual(self.code(str(KOKUGO / "clean.md"), "--profile", "strict"), 2)

    def test_two_when_the_rule_data_is_missing(self):
        with temporary_directory() as tmp:
            self.assertEqual(self.code(str(KOKUGO / "clean.md"), "--data-dir", tmp.name if hasattr(tmp, "name") else str(tmp)), 2)

    def test_two_when_the_glossary_is_missing(self):
        code, _, err = run_script(SCRIPT, str(KOKUGO / "clean.md"), "--glossary", str(KOKUGO / "nope.txt"))
        self.assertEqual(code, 2)
        self.assertIn("cannot read glossary", err)

    def test_the_exit_codes_are_documented_in_the_help(self):
        code, out, _ = run_script(SCRIPT, "--help")
        self.assertEqual(code, 0)
        for fragment in ("0=", "1=", "2=", "--fail-on", "--profile"):
            self.assertIn(fragment, out)


class InputsTest(unittest.TestCase):
    def test_stdin_and_directories(self):
        code, report, _ = run_json("-", stdin="こんにちわ。\n")
        self.assertEqual(code, 1)
        self.assertEqual(report["files"][0]["file"], "<stdin>")
        code, report, _ = run_json(str(KOKUGO))
        names = [Path(f["file"]).name for f in report["files"]]
        self.assertEqual(names, sorted(names))  # 辞書順で再現できる
        self.assertIn("clean.md", names)
        self.assertNotIn("glossary.txt", [n for n in names if not n.endswith((".md", ".txt"))])

    def test_a_plain_text_file_protects_only_urls(self):
        with temporary_directory() as tmp:
            path = Path(tmp.name if hasattr(tmp, "name") else tmp) / "a.txt"
            path.write_text("> 申し込みを受け付ける。\n", encoding="utf-8")
            _, report, _ = run_json(str(path), "--profile", "official")
            self.assertFalse(report["files"][0]["markdown"])
            self.assertEqual(report["summary"]["error"], 1)
            _, report, _ = run_json(str(path), "--profile", "official", "--format", "markdown")
            self.assertEqual(report["summary"]["error"], 0)  # Markdown の引用として保護される

    def test_a_bom_is_ignored(self):
        with temporary_directory() as tmp:
            path = Path(tmp.name if hasattr(tmp, "name") else tmp) / "bom.md"
            path.write_bytes("﻿こんにちわ。\n".encode("utf-8"))
            _, report, _ = run_json(str(path))
            self.assertEqual((report["files"][0]["findings"][0]["line"], report["files"][0]["findings"][0]["column"]), (1, 1))

    def test_the_glossary_option_works_from_the_command_line(self):
        glossary = str(KOKUGO / "glossary.txt")
        _, report, _ = run_json(str(KOKUGO / "official_sample.md"), "--profile", "official", "--glossary", glossary)
        self.assertEqual(report["coverage"]["glossary"], {"protect": 1, "use": 1})
        gairai = [f for f in report["files"][0]["findings"] if f["rule_id"] == "KOKUGO-GAIRAI-001"]
        self.assertEqual([f["reason_code"] for f in gairai if f["category"] == "needs_context"], ["glossary:use-conflict"])

    def test_list_rules_shows_every_rule(self):
        code, out, _ = run_script(SCRIPT, "--list-rules")
        self.assertEqual(code, 0)
        data = json.loads((SCRIPTS_DIR.parent / "data" / "kokugo-rules.json").read_text(encoding="utf-8"))
        for rule in data["rules"]:
            self.assertIn(rule["id"], out)
        self.assertIn("reference-only", out)


class TextOutputTest(unittest.TestCase):
    def test_default_output_hides_accepted_variants_and_says_so(self):
        _, out, _ = run_script(SCRIPT, str(KOKUGO / "only_recommendation.md"))
        self.assertNotIn("[accepted_variant]", out)
        self.assertIn("--all", out)
        _, out_all, _ = run_script(SCRIPT, str(KOKUGO / "only_recommendation.md"), "--all")
        self.assertIn("[accepted_variant]", out_all)

    def test_the_output_names_the_limits_and_what_was_not_checked(self):
        _, out, _ = run_script(SCRIPT, str(KOKUGO / "clean.md"))
        self.assertIn("not checked:", out)
        self.assertIn("reference-only (not checked)", out)
        self.assertIn("保証しない", out)
        self.assertIn("no findings to show", out)  # 『指摘なし』は『検査済み』の保証ではないので、coverage を必ず添える

    def test_each_reported_line_shows_position_category_rule_and_candidate(self):
        _, out, _ = run_script(SCRIPT, str(KOKUGO / "has_error.md"))
        self.assertIn("3:1  [error]  KOKUGO-KANA-001  こんにちわ → こんにちは", out)
        self.assertIn("NAIKAKU-GENDAIKANA-1986", out)


class DeterminismTest(unittest.TestCase):
    ARGS = (str(KOKUGO / "official_sample.md"), "--profile", "official", "--glossary", str(KOKUGO / "glossary.txt"))

    def test_the_same_input_gives_byte_identical_output(self):
        for extra in ((), ("--json",), ("--all",)):
            first = run_script(SCRIPT, *self.ARGS, *extra)
            second = run_script(SCRIPT, *self.ARGS, *extra)
            self.assertEqual(first, second, extra)

    def test_the_working_directory_does_not_change_the_output(self):
        with temporary_directory() as tmp:
            cwd = Path(tmp.name if hasattr(tmp, "name") else tmp)
            self.assertEqual(run_script(SCRIPT, *self.ARGS, "--json", cwd=cwd), run_script(SCRIPT, *self.ARGS, "--json"))

    def test_the_json_has_no_timestamps_or_environment_dependent_values(self):
        import re

        # 相対パスで渡せば、出力に絶対パス(ホームやリポジトリの場所)は入らない
        _, out, _ = run_script(SCRIPT, "official_sample.md", "--profile", "official", "--glossary", "glossary.txt", "--json", cwd=KOKUGO)
        report = json.loads(out)
        self.assertEqual(set(re.findall(r"\d{4}-\d{2}-\d{2}", out)), {report["rules_version"]})  # 日付は規則データの版だけ
        self.assertIsNone(re.search(r"\d{2}:\d{2}", out))  # 時刻が入らない
        self.assertEqual(report["files"][0]["file"], "official_sample.md")
        self.assertNotIn(str(Path.home()), out)
        self.assertNotIn(str(KOKUGO), out)


class ReadOnlyTest(unittest.TestCase):
    """要件11: 検査後も入力ファイルのバイト列が変わらない。"""

    def snapshot(self, root: Path):
        return {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in sorted(root.iterdir()) if p.is_file()}

    def test_inputs_are_byte_identical_after_every_mode_of_checking(self):
        before = self.snapshot(KOKUGO)
        listing = sorted(p.name for p in KOKUGO.iterdir())
        for profile in ("general-tech", "public-explanation", "official"):
            for extra in ([], ["--json"], ["--all"], ["--fail-on", "never"], ["--glossary", str(KOKUGO / "glossary.txt")]):
                run_script(SCRIPT, str(KOKUGO), "--profile", profile, *extra)
        self.assertEqual(self.snapshot(KOKUGO), before)
        self.assertEqual(sorted(p.name for p in KOKUGO.iterdir()), listing)  # 新しいファイルも作らない

    def test_no_files_are_created_in_the_working_directory_or_the_skill(self):
        skill = SCRIPTS_DIR.parent
        listing = sorted(str(p.relative_to(skill)) for p in skill.rglob("*"))
        with temporary_directory() as tmp:
            cwd = Path(tmp.name if hasattr(tmp, "name") else tmp)
            run_script(SCRIPT, str(KOKUGO / "official_sample.md"), "--profile", "official", "--json", cwd=cwd)
            self.assertEqual(list(cwd.iterdir()), [])
        self.assertEqual(sorted(str(p.relative_to(skill)) for p in skill.rglob("*")), listing)

    def test_a_read_only_file_can_be_checked(self):
        with temporary_directory() as tmp:
            path = Path(tmp.name if hasattr(tmp, "name") else tmp) / "ro.md"
            path.write_text("こんにちわ。\n", encoding="utf-8")
            os.chmod(path, 0o444)
            try:
                self.assertEqual(run_script(SCRIPT, str(path))[0], 1)
                self.assertEqual(path.read_text(encoding="utf-8"), "こんにちわ。\n")
            finally:
                os.chmod(path, 0o644)


class NoNetworkTest(unittest.TestCase):
    """要件12: 通常の検査は、ネットワークなしで実行できる。"""

    def test_checking_works_with_sockets_disabled(self):
        def refuse(*args, **kwargs):
            raise AssertionError("network access attempted")

        original = (socket.socket, socket.create_connection, socket.getaddrinfo)
        socket.socket, socket.create_connection, socket.getaddrinfo = refuse, refuse, refuse
        try:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = cli.main([str(KOKUGO / "official_sample.md"), "--profile", "official", "--json"])
            self.assertEqual(code, 1)
            self.assertTrue(json.loads(out.getvalue())["files"])
        finally:
            socket.socket, socket.create_connection, socket.getaddrinfo = original

    def test_the_scripts_do_not_import_network_or_process_modules(self):
        import ast

        forbidden = {"socket", "ssl", "urllib", "http", "ftplib", "requests", "httpx", "aiohttp", "subprocess", "shutil", "webbrowser"}
        for name in ("check_kokugo.py", "kokugo_engine.py", "validate_kokugo_rules.py"):
            tree = ast.parse((SCRIPTS_DIR / name).read_text(encoding="utf-8"))
            imported = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    imported |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module:
                    imported.add(node.module.split(".")[0])
            self.assertFalse(imported & forbidden, (name, imported & forbidden))

    def test_only_the_update_tool_may_use_the_network(self):
        tools = Path(__file__).resolve().parent.parent / "tools"
        self.assertIn("urllib", (tools / "update_kokugo_sources.py").read_text(encoding="utf-8"))
        for path in SCRIPTS_DIR.glob("*.py"):
            self.assertNotIn("urllib", path.read_text(encoding="utf-8"), path.name)


if __name__ == "__main__":
    unittest.main()
