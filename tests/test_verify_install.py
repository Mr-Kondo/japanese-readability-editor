"""tools/verify_install.py のテスト。配置した Skill の構造・メタデータ・内容・実行・依存・重複を検証する。"""

import json
import unittest
from pathlib import Path

from helpers import (SKILL_DIR, SKILL_NAME, TOOLS_DIR, copy_real_skill, hermes_default_home, load_module, run_script,
                     symlinks_supported, temporary_directory, write_skill)

verify = load_module("verify_install", TOOLS_DIR / "verify_install.py")
skill_env = verify.skill_env
SCRIPT = TOOLS_DIR / "verify_install.py"


def codes(report, level):
    return [f.code for f in report.findings if f.level == level]


class VerifyCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name).resolve()
        self.base = self.tmp / "空白 と 日本語"
        self.base.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def installed(self) -> Path:
        return copy_real_skill(self.base)


class HealthyInstallTest(VerifyCase):
    def test_a_complete_copy_passes_from_a_path_with_spaces_and_japanese(self):
        report = verify.verify_installation(self.installed(), target="hermes", source=SKILL_DIR)
        self.assertTrue(report.ok, [f.message for f in report.errors])
        self.assertEqual(report.errors, [])
        self.assertIn("structure", codes(report, "ok"))
        self.assertIn("hermes-metadata", codes(report, "ok"))
        self.assertIn("source", codes(report, "ok"))

    def test_every_script_is_run_from_outside_the_skill_and_the_repository(self):
        report = verify.verify_installation(self.installed(), target="opencode", source=SKILL_DIR)
        ran = [f.message for f in report.findings if f.code == "script-run" and f.level == "ok"]
        for script in ("measure.py", "verify_preservation.py", "verify_preservation.py --strict", "compare_rewrite.py",
                       "check_kokugo.py", "validate_kokugo_rules.py"):
            self.assertTrue(any(m.startswith(script) for m in ran), (script, ran))
        self.assertTrue(all("jre verify" in m and "確認 用" in m for m in ran), ran)

    def test_the_run_leaves_no_files_in_the_installed_copy(self):
        skill = self.installed()
        verify.verify_installation(skill, source=SKILL_DIR)
        self.assertTrue(skill_env.diff_trees(SKILL_DIR, skill).identical)
        self.assertFalse(list(skill.rglob("__pycache__")))

    def test_the_tokenizer_is_reported_without_installing_anything(self):
        report = verify.verify_installation(self.installed(), source=SKILL_DIR)
        self.assertIsNotNone(report.tokenizer)
        self.assertTrue(report.tokenizer.startswith(("sudachi", "regex")), report.tokenizer)
        info = [f for f in report.findings if f.code == "sudachipy"]
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0].level, "info")
        if report.tokenizer == "regex":
            self.assertIn("never installs", info[0].message)

    def test_python_version_is_reported(self):
        report = verify.verify_installation(self.installed(), source=SKILL_DIR, run_scripts=False)
        self.assertIn("python-version", codes(report, "ok"))

    def test_without_a_source_the_copy_can_still_be_verified(self):
        report = verify.verify_installation(self.installed(), source=None)
        self.assertTrue(report.ok)
        self.assertNotIn("source", [f.code for f in report.findings])


class BrokenInstallTest(VerifyCase):
    def test_a_missing_data_file_is_caught_by_running_the_script_and_by_the_source_comparison(self):
        skill = self.installed()
        (skill / "data" / "kokugo-rules.json").unlink()
        report = verify.verify_installation(skill, source=SKILL_DIR)
        report.require_source_match()
        self.assertFalse(report.ok)
        messages = " | ".join(f.message for f in report.errors)
        self.assertIn("data/kokugo-rules.json", messages)
        self.assertIn("check_kokugo.py", messages)

    def test_a_missing_script_is_named(self):
        skill = self.installed()
        (skill / "scripts" / "check_kokugo.py").unlink()
        report = verify.verify_installation(skill, source=None)
        self.assertFalse(report.ok)
        self.assertTrue(any("check_kokugo.py" in f.message for f in report.errors))

    def test_a_missing_reference_is_a_structure_error(self):
        skill = self.installed()
        (skill / "references" / "readability-rules.md").unlink()
        report = verify.verify_installation(skill, source=None, run_scripts=False)
        self.assertFalse(report.ok)
        self.assertIn("structure", codes(report, "error"))

    def test_drift_from_the_source_is_a_warning_unless_strict(self):
        skill = self.installed()
        (skill / "assets" / "examples.md").write_text("古い版\n", encoding="utf-8")
        relaxed = verify.verify_installation(skill, source=SKILL_DIR, run_scripts=False)
        self.assertTrue(relaxed.ok)
        self.assertIn("source", codes(relaxed, "warn"))
        self.assertEqual(relaxed.drift.changed, ["assets/examples.md"])
        strict = verify.verify_installation(skill, source=SKILL_DIR, run_scripts=False)
        strict.require_source_match()
        self.assertFalse(strict.ok)
        self.assertIn("source", codes(strict, "error"))

    def test_a_script_that_crashes_is_reported_with_its_exit_code(self):
        skill = self.installed()
        (skill / "scripts" / "measure.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        report = verify.verify_installation(skill, source=None)
        self.assertFalse(report.ok)
        self.assertTrue(any("measure.py" in f.message and "exit 7" in f.message for f in report.errors))

    def test_no_run_skips_script_execution(self):
        skill = self.installed()
        (skill / "scripts" / "measure.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        report = verify.verify_installation(skill, source=None, run_scripts=False)
        self.assertTrue(report.ok)
        self.assertNotIn("script-run", [f.code for f in report.findings])

    def test_a_path_that_is_not_a_directory(self):
        report = verify.verify_installation(self.base / "nothing", source=None)
        self.assertFalse(report.ok)
        self.assertEqual(codes(report, "error"), ["missing"])

    def test_scripts_are_not_run_when_the_structure_is_invalid(self):
        skill = self.installed()
        (skill / "SKILL.md").write_text("no frontmatter\n", encoding="utf-8")
        report = verify.verify_installation(skill, source=None)
        self.assertFalse(report.ok)
        self.assertNotIn("ok", [f.level for f in report.findings if f.code == "script-run"])


class TargetMetadataTest(VerifyCase):
    def test_opencode_rejects_a_name_that_does_not_match_the_directory(self):
        skill = write_skill(self.base, name="another-name", directory=SKILL_NAME)
        for target in ("opencode", "hermes"):
            with self.subTest(target=target):
                report = verify.verify_installation(skill, target=target, source=None, run_scripts=False)
                self.assertFalse(report.ok)
                self.assertIn(f"{target}-metadata", codes(report, "error"))

    def test_opencode_rejects_uppercase_and_double_hyphen_names(self):
        for name in ("Japanese-Editor", "japanese--editor", "-japanese", "japanese_editor"):
            with self.subTest(name=name):
                skill = write_skill(self.base / name, name=name)
                report = verify.verify_installation(skill, target="opencode", source=None, run_scripts=False)
                self.assertFalse(report.ok)
                self.assertTrue(any("name" in f.message for f in report.errors))

    def test_an_overlong_description_is_rejected(self):
        frontmatter = f"---\nname: {SKILL_NAME}\ndescription: {'あ' * 1025}\n---\n"
        skill = write_skill(self.base, frontmatter=frontmatter)
        report = verify.verify_installation(skill, target="opencode", source=None, run_scripts=False)
        self.assertFalse(report.ok)
        self.assertIn("opencode-metadata", codes(report, "error"))

    def test_each_environment_applies_its_own_name_rule(self):
        skill = write_skill(self.base, name="my_skill.v2")  # Hermes が許す形。OpenCode の形式にはない
        for target, accepted in (("hermes", True), ("opencode", False)):
            with self.subTest(target=target):
                report = verify.VerifyReport(skill)
                verify.check_target_metadata(skill, target, report)
                self.assertEqual(not report.errors, accepted, [f.message for f in report.findings])
        hermes = verify.VerifyReport(skill)
        verify.check_target_metadata(skill, "hermes", hermes)
        self.assertIn("discovery itself documents none", hermes.findings[0].message)

    def test_without_a_target_no_environment_rules_are_applied(self):
        report = verify.verify_installation(self.installed(), source=None, run_scripts=False)
        self.assertNotIn("opencode-metadata", [f.code for f in report.findings])
        self.assertNotIn("hermes-metadata", [f.code for f in report.findings])

    @unittest.skipUnless(symlinks_supported(), "symlinks are not available on this system")
    def test_hermes_warns_about_a_symlinked_skill_but_opencode_does_not(self):
        link_root = self.base / "links"
        link_root.mkdir()
        (link_root / SKILL_NAME).symlink_to(SKILL_DIR, target_is_directory=True)
        hermes = verify.verify_installation(link_root / SKILL_NAME, target="hermes", source=SKILL_DIR, run_scripts=False)
        opencode = verify.verify_installation(link_root / SKILL_NAME, target="opencode", source=SKILL_DIR, run_scripts=False)
        self.assertIn("symlink-remote", codes(hermes, "warn"))
        self.assertNotIn("symlink-remote", codes(opencode, "warn"))


class DuplicateReportTest(VerifyCase):
    def test_duplicates_are_reported_as_warnings_and_do_not_fail(self):
        copy = skill_env.Copy(self.base / "elsewhere", "~/.agents/skills", "differs")
        report = verify.verify_installation(self.installed(), target="opencode", source=SKILL_DIR, run_scripts=False)
        report.add_duplicates([copy], "opencode")
        self.assertTrue(report.ok)
        self.assertIn("duplicate", codes(report, "warn"))


class CommandLineTest(VerifyCase):
    def test_positional_path_exit_zero_and_text_report(self):
        code, out, err = run_script(SCRIPT, str(self.installed()), "--target", "hermes")
        self.assertEqual(code, 0, out + err)
        self.assertIn("result: OK", out)

    def test_failure_exits_one(self):
        skill = self.installed()
        (skill / "data" / "ijidokun.json").unlink()
        code, out, _ = run_script(SCRIPT, str(skill), "--target", "opencode")
        self.assertEqual(code, 1)
        self.assertIn("result: FAILED", out)

    def test_json_output_is_machine_readable(self):
        code, out, _ = run_script(SCRIPT, str(self.installed()), "--json", "--no-run")
        self.assertEqual(code, 0)
        [report] = json.loads(out)
        self.assertTrue(report["ok"])
        self.assertTrue(all({"level", "code", "message"} <= set(f) for f in report["findings"]))

    def test_scope_target_resolves_the_install_location_like_the_installer(self):
        home = self.tmp / "home"
        install_script = TOOLS_DIR / "install.py"
        code, out, err = run_script(install_script, "--scope", "user", "--target", "hermes", "--home", str(home))
        self.assertEqual(code, 0, out + err)
        code, out, err = run_script(SCRIPT, "--scope", "user", "--target", "hermes", "--home", str(home))
        self.assertEqual(code, 0, out + err)
        self.assertIn(str(hermes_default_home(home) / "skills" / SKILL_NAME), out)

    def test_a_target_with_nothing_installed_fails(self):
        code, out, _ = run_script(SCRIPT, "--scope", "user", "--target", "opencode", "--home", str(self.tmp / "empty"))
        self.assertEqual(code, 1)
        self.assertIn("is not a directory", out)

    def test_scope_dest_reports_duplicates_found_in_the_other_discovery_directories(self):
        home = self.tmp / "home"
        run_script(TOOLS_DIR / "install.py", "--scope", "user", "--target", "opencode", "--home", str(home))
        copy_real_skill(home / ".agents" / "skills")
        code, out, _ = run_script(SCRIPT, "--scope", "user", "--target", "opencode", "--home", str(home), "--no-run")
        self.assertEqual(code, 0)
        self.assertIn("[duplicate]", out)

    def test_bad_arguments_exit_two(self):
        for args in ((), (str(self.base), "--scope", "user"), ("--no-source", "--source", str(SKILL_DIR), str(self.base)),
                     ("--source", str(self.base / "missing"), str(self.base))):
            with self.subTest(args=args):
                code, _, err = run_script(SCRIPT, *args)
                self.assertEqual(code, 2, err)


if __name__ == "__main__":
    unittest.main()
