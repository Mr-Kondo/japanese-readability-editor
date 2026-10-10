"""check_fiction.py の読み取り専用 CLI と補助検査の回帰テスト。"""
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest import mock
from helpers import SCRIPTS_DIR, load_module, run_script, temporary_directory

SCRIPT = SCRIPTS_DIR / "check_fiction.py"
fiction = load_module("check_fiction", SCRIPT)


def analyze(text, settings=None):
    return fiction.analyze_text(text, "sample.txt", settings)


class CountsTest(unittest.TestCase):
    def test_empty_input_has_zero_counts_and_no_candidates(self):
        result = analyze("")
        self.assertEqual(result["counts"], {"codepoints": 0, "whitespace_codepoints": 0,
                                          "non_whitespace_codepoints": 0, "newline_sequences": 0})
        self.assertEqual(result["candidates"], [])

    def test_whitespace_and_crlf_are_counted_without_normalization(self):
        self.assertEqual(analyze("夜 \u3000\t\r\n朝\r雨\n")["counts"],
                         {"codepoints": 10, "whitespace_codepoints": 7,
                          "non_whitespace_codepoints": 3, "newline_sequences": 3})

    def test_combining_characters_and_emoji_are_codepoints_not_graphemes(self):
        result = analyze("か\u3099👩\u200d💻")
        self.assertEqual(result["counts"]["codepoints"], 5)
        self.assertEqual(result["counts"]["non_whitespace_codepoints"], 5)
        self.assertIn("一致しない", fiction.DEFINITIONS["visual_character_limit"])

    def test_bom_is_included_in_count(self):
        self.assertEqual(analyze("\ufeff雨。")["counts"]["codepoints"], 3)

    def test_length_is_not_a_quality_warning(self):
        self.assertEqual(analyze("夜が肺に溜まる。" * 100)["candidates"], [])


class BracketsTest(unittest.TestCase):
    def test_nested_multiline_pairs_are_balanced(self):
        self.assertEqual(analyze("「雨。\n　『待つ（まだ）』\r\n」")["candidates"], [])

    def test_all_documented_pair_types(self):
        self.assertEqual(analyze("([{}])（）［］｛｝「『【〈《〔〖雨〗〕》〉】』」")["candidates"], [])

    def test_unexpected_close_reports_file_line_column_and_id(self):
        finding, = analyze("雨。\r\n\u3000」")["candidates"]
        self.assertEqual((finding["file"], finding["line"], finding["column"], finding["check_id"]),
                         ("sample.txt", 2, 2, "FICTION-BRACKET-UNEXPECTED"))
        self.assertEqual(finding["details"]["expected_open"], "「")

    def test_unclosed_opener_keeps_its_original_location(self):
        finding, = analyze("雨。\n「まだ\n待つ")["candidates"]
        self.assertEqual((finding["line"], finding["column"], finding["check_id"]),
                         (2, 1, "FICTION-BRACKET-UNCLOSED"))
        self.assertEqual(finding["details"]["expected_close"], "」")

    def test_crossed_brackets_report_order_without_cascading_missing_pairs(self):
        finding, = analyze("（「雨）」")["candidates"]
        self.assertEqual(finding["check_id"], "FICTION-BRACKET-ORDER")
        self.assertEqual(finding["details"]["expected_close"], "」")
        self.assertEqual(finding["details"]["opening"], {"text": "「", "line": 1, "column": 2})

    def test_order_error_and_still_unclosed_inner_bracket_are_both_candidates(self):
        self.assertEqual({i["check_id"] for i in analyze("（「雨）")["candidates"]},
                         {"FICTION-BRACKET-ORDER", "FICTION-BRACKET-UNCLOSED"})

    def test_wrong_closing_type_does_not_discard_other_open_brackets(self):
        self.assertEqual([i["check_id"] for i in analyze("（雨】）")["candidates"]],
                         ["FICTION-BRACKET-UNEXPECTED"])

    def test_straight_quotes_apostrophes_and_ascii_angles_are_not_paired(self):
        self.assertEqual(analyze("彼は\"don't <turn> と書いた。")["candidates"], [])

    def test_unicode_columns_are_codepoint_positions(self):
        finding, = analyze("か\u3099」")["candidates"]
        self.assertEqual(finding["column"], 3)


class SettingsTest(unittest.TestCase):
    def test_absent_settings_do_not_require_any_string(self):
        self.assertEqual(analyze("雨。")["candidates"], [])

    def test_forbidden_uses_overlapping_exact_substring_matches(self):
        findings = analyze("あああ", {"forbidden": ["ああ"]})["candidates"]
        self.assertEqual([i["column"] for i in findings], [1, 2])
        self.assertTrue(all(i["check_id"] == "FICTION-STRING-FORBIDDEN" for i in findings))

    def test_literals_can_span_lines(self):
        finding, = analyze("雨。\n駅\n夜", {"forbidden": ["駅\n夜"]})["candidates"]
        self.assertEqual((finding["line"], finding["column"], finding["text"]), (2, 1, "駅\n夜"))

    def test_missing_required_string_has_no_invented_location(self):
        finding, = analyze("雨。", {"required": ["青い傘"]})["candidates"]
        self.assertEqual(finding["check_id"], "FICTION-STRING-REQUIRED")
        self.assertIsNone(finding["line"])
        self.assertIsNone(finding["column"])
        self.assertEqual(finding["details"]["occurrences"], 0)

    def test_required_is_substring_matching_not_person_identity(self):
        self.assertEqual(analyze("アオイーが来た。", {"required": ["アオイ"]})["candidates"], [])

    def test_matching_does_not_normalize_case_width_or_combining_forms(self):
        self.assertEqual(analyze("Ａaoe\u0301", {"forbidden": ["A", "AO", "é"]})["candidates"], [])

    def test_invalid_settings_are_rejected(self):
        values = [[], None, {"unknown": []}, {"forbidden": "雨"}, {"required": [""]},
                  {"required": [1]}, {"forbidden": ["雨", "雨"]}]
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    fiction.validate_settings(value)

    def test_lone_surrogates_are_invalid_settings(self):
        for key in ("forbidden", "required"):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    fiction.validate_settings({key: [chr(0xd800)]})


class CommandLineTest(unittest.TestCase):
    def setUp(self):
        self._temporary = temporary_directory()
        self.addCleanup(self._temporary.cleanup)
        self.tmp = Path(self._temporary.name)
        self.path = self.tmp / "原稿.txt"
        self.path.write_bytes("夜が肺に溜まる。\n".encode("utf-8"))

    def run_json(self, *args, stdin=None):
        code, out, err = run_script(SCRIPT, *args, "--json", stdin=stdin)
        self.assertEqual(err, "")
        return code, json.loads(out)

    def settings(self, value):
        path = self.tmp / "work.json"
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        return path

    def test_escaped_surrogate_settings_return_structured_failure(self):
        settings = self.tmp / "escaped.json"
        for value in ({"required": [chr(0xd800)]}, {chr(0xd800): []}):
            with self.subTest(value=repr(value)):
                settings.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
                code, result = self.run_json(str(self.path), "--settings", str(settings))
                self.assertEqual((code, result["status"]), (2, "execution_failed"))
                self.assertEqual(result["errors"][0]["check_id"], "FICTION-SETTINGS")

    def test_normal_output_prints_definitions_count_and_status(self):
        code, out, err = run_script(SCRIPT, str(self.path))
        self.assertEqual((code, err), (0, ""))
        self.assertIn(f"{self.path}:-:- [FICTION-COUNT]", out)
        self.assertIn("BOM・空白・CR・LF", out)
        self.assertIn("見た目の1文字", out)
        self.assertIn("no_candidates", out)
        self.assertIn("保証しない", out)

    def test_json_schema_and_no_candidates_exit_zero(self):
        code, result = self.run_json(str(self.path))
        self.assertEqual(code, 0)
        self.assertEqual(result["schema_version"], 1)
        self.assertEqual(result["tool"], "check_fiction.py")
        self.assertEqual(result["status"], "no_candidates")
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result["summary"], {"files_checked": 1, "candidates": 0, "errors": 0})
        self.assertEqual(result["settings"], {"file": None, "forbidden": [], "required": []})
        self.assertEqual(result["files"][0]["counts"]["codepoints"], 9)
        self.assertEqual(result["errors"], [])

    def test_candidates_exit_one_and_text_location(self):
        self.path.write_text("雨。\n「待つ", encoding="utf-8")
        code, out, err = run_script(SCRIPT, str(self.path))
        self.assertEqual((code, err), (1, ""))
        self.assertIn(f"{self.path}:2:1 [FICTION-BRACKET-UNCLOSED]", out)
        code, result = self.run_json(str(self.path))
        self.assertEqual(code, 1)
        self.assertEqual(result["status"], "candidates")
        self.assertEqual(result["exit_code"], 1)

    def test_empty_file_is_success(self):
        self.path.write_bytes(b"")
        code, result = self.run_json(str(self.path))
        self.assertEqual(code, 0)
        self.assertEqual(result["files"][0]["counts"]["codepoints"], 0)

    def test_stdin_is_utf8_and_reports_its_filename(self):
        code, result = self.run_json("-", stdin="『雨』")
        self.assertEqual(code, 0)
        self.assertEqual(result["files"][0]["file"], "<stdin>")
        self.assertEqual(result["files"][0]["counts"]["codepoints"], 3)

    def test_optional_settings_add_only_requested_literal_checks(self):
        path = self.settings({"forbidden": ["肺"], "required": ["夜", "朝"]})
        code, result = self.run_json(str(self.path), "--settings", str(path))
        self.assertEqual(code, 1)
        self.assertEqual({i["check_id"] for i in result["files"][0]["candidates"]},
                         {"FICTION-STRING-FORBIDDEN", "FICTION-STRING-REQUIRED"})
        self.assertEqual(result["settings"]["file"], str(path))

    def test_required_is_checked_per_file(self):
        second = self.tmp / "chapter2.txt"
        second.write_text("朝。", encoding="utf-8")
        settings = self.settings({"required": ["夜"]})
        code, result = self.run_json(str(self.path), str(second), "--settings", str(settings))
        self.assertEqual(code, 1)
        self.assertEqual(result["files"][0]["candidates"], [])
        self.assertEqual(result["files"][1]["candidates"][0]["file"], str(second))

    def test_input_and_settings_bytes_do_not_change(self):
        original = "\ufeff「雨」 \u3000\t\r\nか\u3099👩\u200d💻\r".encode("utf-8")
        self.path.write_bytes(original)
        settings = self.settings({"required": ["雨"]})
        settings_bytes = settings.read_bytes()
        for args in ((), ("--json",)):
            code, _, _ = run_script(SCRIPT, str(self.path), "--settings", str(settings), *args)
            self.assertEqual(code, 0)
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(settings.read_bytes(), settings_bytes)
        code, result = self.run_json(str(self.path))
        self.assertEqual(code, 0)
        self.assertEqual(result["files"][0]["counts"]["codepoints"], len(original.decode("utf-8")))
        self.assertEqual(result["files"][0]["counts"]["newline_sequences"], 2)

    def test_missing_file_exits_two_as_json(self):
        missing = self.tmp / "missing.txt"
        code, result = self.run_json(str(missing))
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "execution_failed")
        self.assertEqual(result["errors"][0]["file"], str(missing))
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-INPUT-READ")

    def test_directory_is_a_read_failure(self):
        code, result = self.run_json(str(self.tmp))
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-INPUT-READ")

    def test_invalid_utf8_exits_two(self):
        self.path.write_bytes(b"\xff")
        code, result = self.run_json(str(self.path))
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-INPUT-READ")

    def test_permission_error_is_reported_without_platform_permission_assumptions(self):
        # chmod は実行ユーザーによって読めるため PermissionError を模擬する。
        output = io.StringIO()
        with mock.patch.object(fiction, "read_input", side_effect=PermissionError("read denied")):
            with contextlib.redirect_stdout(output):
                code = fiction.main([str(self.path), "--json"])
        result = json.loads(output.getvalue())
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-INPUT-READ")
        self.assertIn("read denied", result["errors"][0]["message"])

    def test_partial_failure_takes_precedence_over_candidates(self):
        self.path.write_text("「雨", encoding="utf-8")
        code, result = self.run_json(str(self.path), str(self.tmp / "missing.txt"))
        self.assertEqual(code, 2)
        self.assertEqual(result["summary"], {"files_checked": 1, "candidates": 1, "errors": 1})
        self.assertEqual(result["status"], "execution_failed")

    def test_settings_syntax_error_has_json_location(self):
        settings = self.tmp / "bad.json"
        settings.write_text('{\n"required": [}', encoding="utf-8")
        code, result = self.run_json(str(self.path), "--settings", str(settings))
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-SETTINGS-JSON")
        self.assertEqual(result["errors"][0]["line"], 2)
        self.assertGreater(result["errors"][0]["column"], 0)
        self.assertEqual(result["files"], [])

    def test_invalid_settings_schema_exits_two(self):
        settings = self.settings({"unexpected": []})
        code, result = self.run_json(str(self.path), "--settings", str(settings))
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-SETTINGS")

    def test_missing_settings_exits_two(self):
        code, result = self.run_json(str(self.path), "--settings", str(self.tmp / "missing.json"))
        self.assertEqual(code, 2)
        self.assertEqual(result["errors"][0]["check_id"], "FICTION-SETTINGS")

    def test_invalid_cli_has_json_error(self):
        for args in ((), (str(self.path), "--bad-option"), ("-", "-"), (str(self.path), "--settings")):
            with self.subTest(args=args):
                code, result = self.run_json(*args)
                self.assertEqual(code, 2)
                self.assertEqual(result["errors"][0]["check_id"], "FICTION-CLI")
                self.assertEqual(result["status"], "execution_failed")

    def test_normal_cli_error_goes_to_stderr(self):
        code, out, err = run_script(SCRIPT)
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("FICTION-CLI", err)

    def test_help_documents_exit_codes(self):
        code, out, err = run_script(SCRIPT, "--help")
        self.assertEqual((code, err), (0, ""))
        for fragment in ("0=", "1=", "2=", "--settings", "--json"):
            self.assertIn(fragment, out)


if __name__ == "__main__":
    unittest.main()
