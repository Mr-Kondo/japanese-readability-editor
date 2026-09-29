"""tools/validate_skill.py のテスト。"""

import os
import unittest
from pathlib import Path

from helpers import (SKILL_DIR, SKILL_NAME, TOOLS_DIR, VALID_DESCRIPTION, copy_real_skill, load_module,
                     run_script, temporary_directory, write_skill)

validate = load_module("validate_skill", TOOLS_DIR / "validate_skill.py")
SCRIPT = TOOLS_DIR / "validate_skill.py"


class ValidationCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def check(self, skill: Path, **kwargs):
        return validate.validate_skill(skill, **kwargs)

    def assertError(self, report, fragment: str):
        self.assertTrue(any(fragment in e for e in report.errors),
                        f"no error containing {fragment!r}; errors were {report.errors}")


class RealSkillTest(ValidationCase):
    def test_the_real_skill_is_valid_and_has_no_warnings(self):
        report = self.check(SKILL_DIR)
        self.assertEqual(report.errors, [])
        self.assertEqual(report.warnings, [])

    def test_the_real_skill_has_only_name_and_description(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        fields, _, problems = validate.parse_frontmatter(text)
        self.assertEqual(problems, [])
        self.assertEqual(sorted(fields), ["description", "name"])

    def test_the_real_skill_description_fits_every_documented_limit(self):
        text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
        fields, _, _ = validate.parse_frontmatter(text)
        self.assertLessEqual(len(fields["description"]), 200)

    def test_the_real_skill_is_an_open_standard_skill_without_local_files(self):
        names = {p.as_posix() for p in validate.iter_skill_files(SKILL_DIR)}
        self.assertIn("SKILL.md", names)
        self.assertIn("references/readability-rules.md", names)
        self.assertIn("scripts/measure.py", names)
        self.assertIn("scripts/verify_preservation.py", names)
        self.assertIn("assets/examples.md", names)
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith(".pyc")])


class SkillFileTest(ValidationCase):
    def test_valid_minimal_skill(self):
        self.assertTrue(self.check(write_skill(self.tmp)).ok)

    def test_missing_directory(self):
        self.assertError(self.check(self.tmp / "nope"), "not found")

    def test_missing_skill_md(self):
        skill = self.tmp / SKILL_NAME
        skill.mkdir()
        self.assertError(self.check(skill), "SKILL.md not found")

    def test_lowercase_file_name_is_rejected(self):
        skill = write_skill(self.tmp)
        (skill / "SKILL.md").rename(skill / "skill.md")
        report = self.check(skill)
        self.assertError(report, "exactly SKILL.md")

    def test_mixed_case_file_name_is_rejected(self):
        skill = write_skill(self.tmp)
        (skill / "SKILL.md").rename(skill / "Skill.md")
        self.assertError(self.check(skill), "exactly SKILL.md")

    def test_file_that_is_not_utf8(self):
        skill = write_skill(self.tmp)
        (skill / "SKILL.md").write_bytes(b"\xff\xfe---")
        self.assertError(self.check(skill), "UTF-8")


class FrontmatterTest(ValidationCase):
    def skill(self, frontmatter: str, **kwargs) -> Path:
        return write_skill(self.tmp, frontmatter=frontmatter, **kwargs)

    def test_no_frontmatter(self):
        skill = write_skill(self.tmp, frontmatter="")
        self.assertError(self.check(skill), "frontmatter must start")

    def test_frontmatter_not_at_the_top(self):
        skill = self.skill(f"\n---\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\n---\n")
        self.assertError(self.check(skill), "frontmatter must start")

    def test_unclosed_frontmatter(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\n")
        self.assertError(self.check(skill), "not closed")

    def test_missing_name(self):
        skill = self.skill(f"---\ndescription: {VALID_DESCRIPTION}\n---\n")
        self.assertError(self.check(skill), "'name' is missing")

    def test_empty_name(self):
        skill = self.skill(f"---\nname:\ndescription: {VALID_DESCRIPTION}\n---\n")
        self.assertError(self.check(skill), "'name' is missing")

    def test_missing_description(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\n---\n")
        self.assertError(self.check(skill), "'description' is missing")

    def test_malformed_line_without_a_colon(self):
        skill = self.skill(f"---\nname {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\n---\n")
        self.assertError(self.check(skill), "malformed YAML")

    def test_plain_value_containing_colon_space(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\ndescription: 使い方: 校正する\n---\n")
        self.assertError(self.check(skill), "': '")

    def test_plain_value_containing_a_comment_marker(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\ndescription: 校正する #課題\n---\n")
        self.assertError(self.check(skill), "' #'")

    def test_unterminated_quote(self):
        skill = self.skill(f'---\nname: {SKILL_NAME}\ndescription: "閉じていない\n---\n')
        self.assertError(self.check(skill), "unterminated")

    def test_quoted_value_with_colon_is_accepted(self):
        skill = self.skill(f'---\nname: {SKILL_NAME}\ndescription: "使い方: 校正する"\n---\n')
        self.assertTrue(self.check(skill).ok)

    def test_multiline_block_scalar_is_rejected(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\ndescription: >\n  折りたたむ\n  説明\n---\n")
        report = self.check(skill)
        self.assertFalse(report.ok)
        self.assertError(report, "YAML indicator")

    def test_indented_continuation_line_is_rejected(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\ndescription: 一行目\n  二行目\n---\n")
        self.assertError(self.check(skill), "multi-line")

    def test_duplicate_key(self):
        skill = self.skill(f"---\nname: {SKILL_NAME}\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\n---\n")
        self.assertError(self.check(skill), "duplicate key")

    def test_bom_is_rejected(self):
        skill = write_skill(self.tmp)
        path = skill / "SKILL.md"
        path.write_bytes(b"\xef\xbb\xbf" + path.read_bytes())
        self.assertError(self.check(skill), "BOM")


class NameAndDescriptionTest(ValidationCase):
    def test_wrong_name(self):
        skill = write_skill(self.tmp, name="other-skill", directory=SKILL_NAME)
        self.assertError(self.check(skill), "must be 'japanese-readability-editor'")

    def test_name_must_match_the_directory(self):
        skill = write_skill(self.tmp, directory="some-other-directory")
        self.assertError(self.check(skill), "must match the directory name")

    def test_uppercase_name(self):
        skill = write_skill(self.tmp, name="Japanese-Readability-Editor", directory="Japanese-Readability-Editor")
        report = self.check(skill, expected_name="Japanese-Readability-Editor")
        self.assertError(report, "lowercase")

    def test_reserved_word_in_name(self):
        skill = write_skill(self.tmp, name="claude-helper", directory="claude-helper")
        self.assertError(self.check(skill, expected_name="claude-helper"), "reserved word")

    def test_name_too_long(self):
        name = "a" * 65
        skill = write_skill(self.tmp, name=name)
        self.assertError(self.check(skill, expected_name=name), "maximum is 64")

    def test_description_over_1024_chars_is_an_error(self):
        skill = write_skill(self.tmp, frontmatter=f"---\nname: {SKILL_NAME}\ndescription: {'あ' * 1025}\n---\n")
        self.assertError(self.check(skill), "maximum is 1024")

    def test_description_over_200_chars_is_only_a_warning(self):
        skill = write_skill(self.tmp, frontmatter=f"---\nname: {SKILL_NAME}\ndescription: {'あ' * 300}\n---\n")
        report = self.check(skill)
        self.assertTrue(report.ok)
        self.assertTrue(any("200" in w for w in report.warnings))

    def test_description_with_angle_brackets(self):
        skill = write_skill(self.tmp, frontmatter=f"---\nname: {SKILL_NAME}\ndescription: <b>太字</b>で書く\n---\n")
        self.assertError(self.check(skill), "'<' or '>'")


class ProductSpecificFrontmatterTest(ValidationCase):
    def test_product_specific_keys_are_rejected(self):
        for key, value in (("disable-model-invocation", "true"), ("when_to_use", "校正のとき"),
                           ("user-invocable", "false"), ("model", "opus"), ("paths", '"**/*.md"')):
            with self.subTest(key=key):
                frontmatter = (f"---\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\n{key}: {value}\n---\n")
                report = self.check(write_skill(self.tmp / key, frontmatter=frontmatter))
                self.assertError(report, f"'{key}' is product-specific")

    def test_unknown_keys_are_rejected(self):
        frontmatter = f"---\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\nsurprise: 1\n---\n"
        self.assertError(self.check(write_skill(self.tmp, frontmatter=frontmatter)), "unexpected frontmatter key")

    def test_standard_optional_keys_need_an_explicit_flag(self):
        frontmatter = f"---\nname: {SKILL_NAME}\ndescription: {VALID_DESCRIPTION}\nlicense: MIT\n---\n"
        skill = write_skill(self.tmp, frontmatter=frontmatter)
        self.assertError(self.check(skill), "optional in the Agent Skills spec")
        self.assertTrue(self.check(skill, allow_standard_optional=True).ok)


class ReferenceTest(ValidationCase):
    def test_existing_references_pass(self):
        skill = write_skill(self.tmp, body="詳細は references/rules.md と scripts/run.py と assets/a.md を見る。\n")
        for relative in ("references/rules.md", "scripts/run.py", "assets/a.md"):
            (skill / relative).parent.mkdir(exist_ok=True)
            (skill / relative).write_text("x = 1\n" if relative.endswith(".py") else "内容\n", encoding="utf-8")
        self.assertTrue(self.check(skill).ok)

    def test_missing_reference_file(self):
        skill = write_skill(self.tmp, body="[規則](references/missing.md) を読む。\n")
        self.assertError(self.check(skill), "references/missing.md")

    def test_missing_script_mentioned_in_a_code_block(self):
        skill = write_skill(self.tmp, body="```bash\npython3 scripts/missing.py file.md\n```\n")
        self.assertError(self.check(skill), "scripts/missing.py")

    def test_missing_asset(self):
        skill = write_skill(self.tmp, body="例は assets/missing.md にある。\n")
        self.assertError(self.check(skill), "assets/missing.md")

    def test_trailing_punctuation_is_not_part_of_the_path(self):
        skill = write_skill(self.tmp, body="規則は references/rules.md。\n")
        (skill / "references").mkdir()
        (skill / "references" / "rules.md").write_text("内容\n", encoding="utf-8")
        self.assertTrue(self.check(skill).ok)

    def test_japanese_particles_after_a_path_are_not_part_of_it(self):
        skill = write_skill(self.tmp, body="規則はreferences/rules.mdを読む。\n")
        (skill / "references").mkdir()
        (skill / "references" / "rules.md").write_text("内容\n", encoding="utf-8")
        self.assertTrue(self.check(skill).ok)

    def test_links_that_stay_inside_the_skill_may_use_parent_directories(self):
        skill = write_skill(self.tmp, body="規則は references/rules.md を読む。\n")
        (skill / "references").mkdir()
        (skill / "assets").mkdir()
        (skill / "assets" / "a.md").write_text("例\n", encoding="utf-8")
        (skill / "references" / "rules.md").write_text("[例](../assets/a.md)\n", encoding="utf-8")
        self.assertTrue(self.check(skill).ok)

    def test_directory_mentions_without_a_file_name_are_ignored(self):
        skill = write_skill(self.tmp, body="scripts/ と references/ と assets/ の説明。scripts/*.py も含む。\n")
        self.assertTrue(self.check(skill).ok)

    def test_relative_link_in_a_reference_file_must_exist(self):
        skill = write_skill(self.tmp, body="規則は references/rules.md を読む。\n")
        (skill / "references").mkdir()
        (skill / "references" / "rules.md").write_text("[別の規則](other.md)\n", encoding="utf-8")
        self.assertError(self.check(skill), "other.md")

    def test_external_links_and_anchors_are_ignored(self):
        skill = write_skill(self.tmp, body="[公式](https://example.com/x) と [節](#section) と [メール](mailto:a@b.c)。\n")
        self.assertTrue(self.check(skill).ok)

    def test_links_inside_code_blocks_are_ignored(self):
        skill = write_skill(self.tmp, body="```markdown\n[例](missing/file.md)\n```\n")
        self.assertTrue(self.check(skill).ok)


class TraversalTest(ValidationCase):
    def test_parent_directory_link(self):
        skill = write_skill(self.tmp, body="[外](../secret.md) を読む。\n")
        (self.tmp / "secret.md").write_text("秘密\n", encoding="utf-8")
        self.assertError(self.check(skill), "unsafe path")

    def test_deep_traversal(self):
        skill = write_skill(self.tmp, body="[外](references/../../../etc/passwd) を読む。\n")
        self.assertError(self.check(skill), "unsafe path")

    def test_absolute_path_link(self):
        skill = write_skill(self.tmp, body="[外](/etc/passwd) を読む。\n")
        self.assertError(self.check(skill), "unsafe path")

    def test_home_directory_link(self):
        skill = write_skill(self.tmp, body="[外](~/notes.md) を読む。\n")
        self.assertError(self.check(skill), "unsafe path")

    def test_windows_absolute_path_link(self):
        skill = write_skill(self.tmp, body="[外](C:\\Users\\a\\notes.md) を読む。\n")
        self.assertError(self.check(skill), "unsafe path")

    def test_traversal_in_a_reference_file_link(self):
        skill = write_skill(self.tmp, body="規則は references/rules.md を読む。\n")
        (skill / "references").mkdir()
        (skill / "references" / "rules.md").write_text("[外](../../outside.md)\n", encoding="utf-8")
        self.assertError(self.check(skill), "unsafe path")

    def test_symlink_pointing_outside(self):
        skill = write_skill(self.tmp)
        outside = self.tmp / "outside.txt"
        outside.write_text("外\n", encoding="utf-8")
        try:
            os.symlink(outside, skill / "leak.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available")
        self.assertError(self.check(skill), "symlink points outside")


class ScriptSafetyTest(ValidationCase):
    _cases = 0

    def script_report(self, code: str):
        type(self)._cases += 1
        skill = write_skill(self.tmp / f"case{self._cases}")  # 1つのテストで何度も呼べるよう、毎回別の場所に作る
        (skill / "scripts").mkdir()
        (skill / "scripts" / "tool.py").write_text(code, encoding="utf-8")
        return self.check(skill)

    def test_clean_script_passes(self):
        report = self.script_report("import re, sys, json, os\nprint(re.compile('a').pattern)\n")
        self.assertTrue(report.ok, report.errors)

    def test_network_modules_are_forbidden(self):
        for code in ("import socket", "import urllib.request", "from http import client", "import requests"):
            with self.subTest(code=code):
                self.assertError(self.script_report(code + "\n"), "forbidden import")

    def test_subprocess_and_shutil_are_forbidden(self):
        self.assertError(self.script_report("import subprocess\n"), "forbidden import")
        self.assertError(self.script_report("from shutil import rmtree\n"), "forbidden import")

    def test_dynamic_execution_is_forbidden(self):
        self.assertError(self.script_report("eval('1')\n"), "forbidden call 'eval()'")
        self.assertError(self.script_report("exec('x=1')\n"), "forbidden call 'exec()'")

    def test_os_system_and_deletion_are_forbidden(self):
        self.assertError(self.script_report("import os\nos.system('ls')\n"), "os.system")
        self.assertError(self.script_report("import os\nos.remove('a')\n"), "os.remove")
        self.assertError(self.script_report("import os\nos.execvp('a', [])\n"), "os.execvp")

    def test_writing_files_is_forbidden(self):
        self.assertError(self.script_report("open('a.txt', 'w')\n"), "open() for writing")
        self.assertError(self.script_report("open('a.txt', mode='a')\n"), "open() for writing")
        self.assertError(self.script_report("from pathlib import Path\nPath('a').write_text('x')\n"), "write_text")
        self.assertError(self.script_report("from pathlib import Path\nPath('a').unlink()\n"), "unlink")

    def test_reading_files_is_allowed(self):
        self.assertTrue(self.script_report("open('a.txt')\nopen('a.txt', 'rb')\n").ok)

    def test_syntax_error_is_reported(self):
        self.assertError(self.script_report("def broken(:\n"), "cannot parse")

    def test_real_scripts_are_read_only(self):
        report = validate.Report()
        for name in ("measure.py", "verify_preservation.py"):
            validate.check_script_safety(SKILL_DIR / "scripts" / name, name, report)
        self.assertEqual(report.errors, [])


class ZipabilityTest(ValidationCase):
    def test_zip_is_checked_for_a_valid_skill(self):
        self.assertTrue(self.check(copy_real_skill(self.tmp)).ok)

    def test_broken_symlink_makes_zip_fail_or_is_reported(self):
        skill = write_skill(self.tmp)
        try:
            os.symlink(self.tmp / "does-not-exist", skill / "broken.txt")
        except (OSError, NotImplementedError):
            self.skipTest("symlinks are not available")
        self.assertFalse(self.check(skill).ok)


class CommandLineTest(ValidationCase):
    def test_default_target_is_valid(self):
        code, out, _ = run_script(SCRIPT)
        self.assertEqual(code, 0)
        self.assertIn("OK", out)

    def test_invalid_skill_exits_with_one(self):
        skill = write_skill(self.tmp, frontmatter="---\nname: japanese-readability-editor\n---\n")
        code, out, _ = run_script(SCRIPT, str(skill))
        self.assertEqual(code, 1)
        self.assertIn("ERROR:", out)
        self.assertIn("FAILED", out)

    def test_output_is_concise(self):
        skill = write_skill(self.tmp, frontmatter="")
        _, out, _ = run_script(SCRIPT, str(skill))
        self.assertLess(len(out.splitlines()), 10)


if __name__ == "__main__":
    unittest.main()
