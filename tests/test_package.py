"""tools/package.py のテスト。"""

import hashlib
import unittest
import zipfile
from pathlib import Path

from helpers import (SKILL_DIR, SKILL_NAME, TOOLS_DIR, copy_real_skill, hermes_default_home, load_module, run_script,
                     temporary_directory, write_skill)

package = load_module("package", TOOLS_DIR / "package.py")
validate = load_module("validate_skill_for_package", TOOLS_DIR / "validate_skill.py")
SCRIPT = TOOLS_DIR / "package.py"


class PackageCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)
        self.out = self.tmp / "dist"

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, skill: Path = SKILL_DIR) -> Path:
        zip_path = self.out / f"{SKILL_NAME}.zip"
        package.build_zip(skill, zip_path)
        return zip_path


class ZipStructureTest(PackageCase):
    def test_zip_has_exactly_one_top_level_folder(self):
        with zipfile.ZipFile(self.build()) as archive:
            top_levels = {name.split("/", 1)[0] for name in archive.namelist()}
        self.assertEqual(top_levels, {SKILL_NAME})

    def test_skill_md_is_directly_under_the_folder_and_not_at_the_zip_root(self):
        with zipfile.ZipFile(self.build()) as archive:
            names = archive.namelist()
        self.assertIn(f"{SKILL_NAME}/SKILL.md", names)
        self.assertNotIn("SKILL.md", names)

    def test_references_scripts_and_assets_are_included(self):
        with zipfile.ZipFile(self.build()) as archive:
            names = set(archive.namelist())
        for expected in ("references/readability-rules.md", "scripts/measure.py",
                         "scripts/verify_preservation.py", "scripts/compare_rewrite.py", "assets/examples.md"):
            self.assertIn(f"{SKILL_NAME}/{expected}", names)

    def test_zip_matches_the_source_files_byte_for_byte(self):
        with zipfile.ZipFile(self.build()) as archive:
            for relative in validate.iter_skill_files(SKILL_DIR):
                self.assertEqual(archive.read(f"{SKILL_NAME}/{relative.as_posix()}"),
                                 (SKILL_DIR / relative).read_bytes(), relative)

    def test_bytecode_caches_and_os_files_are_excluded(self):
        skill = copy_real_skill(self.tmp / "copy")
        (skill / "scripts" / "__pycache__").mkdir()
        (skill / "scripts" / "__pycache__" / "measure.cpython-314.pyc").write_bytes(b"\x00")
        (skill / ".DS_Store").write_bytes(b"\x00")
        with zipfile.ZipFile(self.build(skill)) as archive:
            names = archive.namelist()
        self.assertFalse([n for n in names if "__pycache__" in n or n.endswith((".pyc", ".DS_Store"))])

    def test_zip_is_reproducible(self):
        first = self.build().read_bytes()
        (self.out / f"{SKILL_NAME}.zip").unlink()
        self.assertEqual(self.build().read_bytes(), first)

    def test_scripts_are_executable_when_extracted(self):
        with zipfile.ZipFile(self.build()) as archive:
            mode = archive.getinfo(f"{SKILL_NAME}/scripts/measure.py").external_attr >> 16
            skill_mode = archive.getinfo(f"{SKILL_NAME}/SKILL.md").external_attr >> 16
        self.assertEqual(mode & 0o777, 0o755)
        self.assertEqual(skill_mode & 0o777, 0o644)

    def test_extracted_zip_is_a_valid_skill(self):
        extract = self.tmp / "extract"
        with zipfile.ZipFile(self.build()) as archive:
            archive.extractall(extract)
        self.assertTrue(validate.validate_skill(extract / SKILL_NAME).ok)

    def test_verify_zip_accepts_the_generated_zip(self):
        self.assertEqual(package.verify_zip(self.build()), [])

    def test_verify_zip_rejects_skill_md_at_the_zip_root(self):
        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr("SKILL.md", "---\n---\n")
        problems = package.verify_zip(bad)
        self.assertTrue(any("top-level folder" in p for p in problems))
        self.assertTrue(any("does not contain" in p for p in problems))

    def test_verify_zip_rejects_several_top_level_folders(self):
        bad = self.tmp / "bad.zip"
        with zipfile.ZipFile(bad, "w") as archive:
            archive.writestr(f"{SKILL_NAME}/SKILL.md", "x")
            archive.writestr("other/SKILL.md", "x")
        self.assertTrue(any("top-level folder" in p for p in package.verify_zip(bad)))


class ChecksumTest(PackageCase):
    def test_sha256_file_uses_sha256sum_format(self):
        zip_path = self.build()
        sha_path = self.out / f"{SKILL_NAME}.sha256"
        digest = package.write_sha256(zip_path, sha_path)
        self.assertEqual(digest, hashlib.sha256(zip_path.read_bytes()).hexdigest())
        self.assertEqual(sha_path.read_text(encoding="utf-8"), f"{digest}  {SKILL_NAME}.zip\n")


class GeminiAppsAdapterTest(PackageCase):
    def setUp(self):
        super().setUp()
        self.text = package.render_gemini_apps_instructions(SKILL_DIR)

    def test_frontmatter_is_removed(self):
        self.assertNotIn("name: japanese-readability-editor", self.text)
        self.assertFalse(self.text.startswith("---"))

    def test_contains_the_skill_body_and_the_detailed_rules(self):
        self.assertIn("変更してはならないもの", self.text)      # SKILL.md の本文
        self.assertIn("未解決の疑問", self.text)                 # references の本文
        self.assertIn("Part 1", self.text)
        self.assertIn("Part 2", self.text)

    def test_relative_file_links_are_flattened(self):
        self.assertNotIn("](references/", self.text)
        self.assertNotIn("](assets/", self.text)

    def test_marked_as_generated(self):
        self.assertIn("Generated by tools/package.py", self.text)

    def test_notes_that_scripts_cannot_run(self):
        self.assertIn("scripts/ は実行できない", self.text)

    def test_headings_are_demoted_below_the_document_title(self):
        headings = [line for line in self.text.splitlines() if line.startswith("# ")]
        self.assertEqual(len(headings), 1)

    def test_code_fence_contents_are_not_treated_as_headings(self):
        demoted = package.demote_headings("# 題\n\n```text\n# コメント\n```\n", 2)
        self.assertIn("### 題", demoted)
        self.assertIn("\n# コメント\n", demoted)

    def test_folder_export_omits_scripts(self):
        copied = package.export_gemini_apps_folder(SKILL_DIR, self.out / "gemini-apps")
        self.assertIn("SKILL.md", copied)
        self.assertIn("references/readability-rules.md", copied)
        self.assertFalse([c for c in copied if c.startswith("scripts/")])
        self.assertFalse((self.out / "gemini-apps" / SKILL_NAME / "scripts").exists())


class AgentBundleTest(PackageCase):
    """OpenCode と Hermes Agent 向けの配布物。正本の完全な複製と、生成した INSTALL.md。"""

    def export(self, target: str):
        root = self.out / target
        copied = package.export_agent_bundle(SKILL_DIR, root, target)
        return root, copied

    def test_the_skill_folder_is_a_byte_for_byte_copy_of_the_source(self):
        for target in package.AGENT_BUNDLE_TARGETS:
            with self.subTest(target=target):
                root, copied = self.export(target)
                self.assertEqual(copied, [p.as_posix() for p in validate.iter_skill_files(SKILL_DIR)])
                for relative in copied:
                    self.assertEqual((root / SKILL_NAME / relative).read_bytes(), (SKILL_DIR / relative).read_bytes(), relative)

    def test_install_notes_sit_beside_the_skill_folder_not_inside_it(self):
        root, copied = self.export("opencode")
        self.assertTrue((root / "INSTALL.md").is_file())
        self.assertNotIn("INSTALL.md", copied)
        self.assertEqual(sorted(p.name for p in root.iterdir()), ["INSTALL.md", SKILL_NAME])

    def test_install_notes_state_the_locations_the_installer_uses(self):
        install = load_module("install_for_package_test", TOOLS_DIR / "install.py")
        for target in package.AGENT_BUNDLE_TARGETS:
            with self.subTest(target=target):
                root, _ = self.export(target)
                text = (root / "INSTALL.md").read_text(encoding="utf-8")
                self.assertIn(install.WORKSPACE_DIRS[target], text)
                self.assertIn(install.USER_DIRS[target], text)
                self.assertIn(f"--target {target}", text)
                self.assertIn("Generated by tools/package.py", text)

    def test_hermes_notes_warn_about_trust_hub_install_and_remote_backends(self):
        root, _ = self.export("hermes")
        text = (root / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn("hermes skills trust", text)
        self.assertIn("hermes skills install", text)
        self.assertIn("data/", text)
        self.assertIn("Docker", text)

    def test_opencode_notes_warn_about_duplicates_and_stray_markdown(self):
        root, _ = self.export("opencode")
        text = (root / "INSTALL.md").read_text(encoding="utf-8")
        self.assertIn(".claude/skills/", text)
        self.assertIn("`INSTALL.md` は skills ディレクトリに置かない", text)

    def test_re_exporting_replaces_the_previous_bundle(self):
        root, _ = self.export("opencode")
        (root / SKILL_NAME / "stale.txt").write_text("古い\n", encoding="utf-8")
        self.export("opencode")
        self.assertFalse((root / SKILL_NAME / "stale.txt").exists())


class CommandLineTest(PackageCase):
    def test_generates_the_opencode_and_hermes_bundles_by_default(self):
        code, out, err = run_script(SCRIPT, "--out-dir", str(self.out))
        self.assertEqual(code, 0, err)
        for target in ("opencode", "hermes"):
            self.assertTrue((self.out / target / SKILL_NAME / "SKILL.md").is_file())
            self.assertTrue((self.out / target / "INSTALL.md").is_file())
            self.assertIn(f"[{target}] verify: OK", out)

    def test_bundle_option_selects_targets(self):
        code, _, err = run_script(SCRIPT, "--out-dir", str(self.out), "--bundle", "hermes")
        self.assertEqual(code, 0, err)
        self.assertTrue((self.out / "hermes").is_dir())
        self.assertFalse((self.out / "opencode").exists())

    def test_no_agent_bundles_flag(self):
        code, _, _ = run_script(SCRIPT, "--out-dir", str(self.out), "--no-agent-bundles")
        self.assertEqual(code, 0)
        self.assertFalse((self.out / "opencode").exists())
        self.assertFalse((self.out / "hermes").exists())
        self.assertTrue((self.out / f"{SKILL_NAME}.zip").is_file())

    def test_existing_artifacts_are_not_changed_by_the_new_bundles(self):
        run_script(SCRIPT, "--out-dir", str(self.out), "--no-agent-bundles")
        before = (self.out / f"{SKILL_NAME}.sha256").read_text(encoding="utf-8")
        run_script(SCRIPT, "--out-dir", str(self.out))
        self.assertEqual((self.out / f"{SKILL_NAME}.sha256").read_text(encoding="utf-8"), before)
        self.assertTrue((self.out / "gemini-apps" / SKILL_NAME / "SKILL.md").is_file())

    def test_a_bundle_installed_from_dist_works_without_the_repository_skill(self):
        run_script(SCRIPT, "--out-dir", str(self.out))
        home = self.tmp / "ホーム 空白"
        home.mkdir()
        bundle = self.out / "hermes" / SKILL_NAME
        code, out, err = run_script(TOOLS_DIR / "install.py", "--source", str(bundle), "--scope", "user",
                                    "--target", "hermes", "--home", str(home))
        self.assertEqual(code, 0, out + err)
        installed = hermes_default_home(home) / "skills" / SKILL_NAME
        code, out, err = run_script(installed / "scripts" / "verify_preservation.py", "--strict",
                                    str(SKILL_DIR.parent.parent / "tests" / "fixtures" / "before.md"),
                                    str(SKILL_DIR.parent.parent / "tests" / "fixtures" / "after_split.md"), cwd=home)
        self.assertEqual(code, 0, out + err)

    def test_generates_all_artifacts(self):
        code, out, err = run_script(SCRIPT, "--out-dir", str(self.out))
        self.assertEqual(code, 0, err)
        self.assertTrue((self.out / f"{SKILL_NAME}.zip").is_file())
        self.assertTrue((self.out / f"{SKILL_NAME}.sha256").is_file())
        self.assertTrue((self.out / "gemini-apps-instructions.md").is_file())
        self.assertTrue((self.out / "gemini-apps" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn("zip", out)

    def test_recorded_checksum_matches_the_zip(self):
        run_script(SCRIPT, "--out-dir", str(self.out))
        recorded = (self.out / f"{SKILL_NAME}.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(recorded, hashlib.sha256((self.out / f"{SKILL_NAME}.zip").read_bytes()).hexdigest())

    def test_no_gemini_apps_flag(self):
        code, _, _ = run_script(SCRIPT, "--out-dir", str(self.out), "--no-gemini-apps")
        self.assertEqual(code, 0)
        self.assertTrue((self.out / f"{SKILL_NAME}.zip").is_file())
        self.assertFalse((self.out / "gemini-apps-instructions.md").exists())
        self.assertFalse((self.out / "gemini-apps").exists())

    def test_running_twice_gives_identical_zip_and_checksum(self):
        run_script(SCRIPT, "--out-dir", str(self.out))
        first = (self.out / f"{SKILL_NAME}.sha256").read_text(encoding="utf-8")
        run_script(SCRIPT, "--out-dir", str(self.out))
        self.assertEqual((self.out / f"{SKILL_NAME}.sha256").read_text(encoding="utf-8"), first)

    def test_invalid_skill_is_not_packaged(self):
        broken = write_skill(self.tmp / "broken", frontmatter="---\nname: japanese-readability-editor\n---\n")
        code, _, err = run_script(SCRIPT, "--skill-dir", str(broken), "--out-dir", str(self.out))
        self.assertEqual(code, 1)
        self.assertIn("validation errors", err)
        self.assertFalse(self.out.exists())


if __name__ == "__main__":
    unittest.main()
