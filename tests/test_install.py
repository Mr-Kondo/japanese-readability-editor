"""tools/install.py のテスト。"""

import unittest
from datetime import datetime
from pathlib import Path

from helpers import (SKILL_DIR, SKILL_NAME, TOOLS_DIR, load_module, run_script, symlinks_supported,
                     temporary_directory, write_skill)

install = load_module("install", TOOLS_DIR / "install.py")
SCRIPT = TOOLS_DIR / "install.py"


def tree(root: Path):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


class InstallCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name).resolve()
        self.workspace = self.tmp / "workspace"
        self.home = self.tmp / "home"
        self.workspace.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def run_install(self, *args: str):
        return run_script(SCRIPT, "--workspace", str(self.workspace), "--home", str(self.home), *args)

    def dirs(self, scope: str, targets):
        base = self.workspace if scope == "workspace" else self.home
        destinations = install.resolve_destinations(scope, targets, self.workspace, self.home)
        return [d.skills_dir.relative_to(base).as_posix() for d in destinations]


class TargetPathTest(InstallCase):
    def test_workspace_common_uses_agents_skills(self):
        self.assertEqual(self.dirs("workspace", ["common"]), [".agents/skills"])

    def test_workspace_targets_that_read_agents_skills_share_one_location(self):
        for target in ("codex", "copilot", "gemini-cli", "antigravity", "antigravity-ide", "antigravity-cli"):
            with self.subTest(target=target):
                self.assertEqual(self.dirs("workspace", [target]), [".agents/skills"])

    def test_workspace_claude_code_uses_claude_skills(self):
        self.assertEqual(self.dirs("workspace", ["claude-code"]), [".claude/skills"])

    def test_workspace_all_installs_one_copy_per_location(self):
        self.assertEqual(self.dirs("workspace", ["all"]), [".agents/skills", ".claude/skills"])

    def test_the_same_location_is_listed_once_but_keeps_every_target(self):
        destinations = install.resolve_destinations("workspace", ["common", "codex", "copilot"], self.workspace, self.home)
        self.assertEqual(len(destinations), 1)
        self.assertEqual(destinations[0].targets, ["common", "codex", "copilot"])

    def test_user_paths(self):
        expected = {
            "common": ".agents/skills",
            "codex": ".agents/skills",
            "copilot": ".agents/skills",
            "gemini-cli": ".agents/skills",
            "claude-code": ".claude/skills",
            "antigravity-ide": ".gemini/config/skills",
            "antigravity-cli": ".gemini/antigravity-cli/skills",
        }
        for target, path in expected.items():
            with self.subTest(target=target):
                self.assertEqual(self.dirs("user", [target]), [path])

    def test_codex_user_scope_does_not_use_the_deprecated_codex_home(self):
        self.assertNotIn(".codex", " ".join(self.dirs("user", ["all"])))

    def test_antigravity_ide_and_cli_are_kept_apart_at_user_scope(self):
        self.assertEqual(self.dirs("user", ["antigravity"]), [".gemini/config/skills", ".gemini/antigravity-cli/skills"])

    def test_user_all(self):
        self.assertEqual(self.dirs("user", ["all"]), [
            ".agents/skills", ".claude/skills", ".gemini/config/skills", ".gemini/antigravity-cli/skills"])

    def test_unknown_target(self):
        with self.assertRaises(ValueError):
            install.resolve_destinations("user", ["vscode"], self.workspace, self.home)

    def test_target_list_parsing(self):
        self.assertEqual(install.parse_targets(["codex,claude-code", "copilot"]), ["codex", "claude-code", "copilot"])
        self.assertEqual(install.parse_targets(None), ["common"])


class DryRunTest(InstallCase):
    def test_dry_run_writes_nothing(self):
        code, out, _ = self.run_install("--scope", "workspace", "--target", "all", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertIn(".agents/skills", out)
        self.assertIn(".claude/skills", out)
        self.assertEqual(tree(self.workspace), [])
        self.assertEqual(tree(self.home), [])

    def test_dry_run_for_user_scope_writes_nothing(self):
        code, out, _ = self.run_install("--scope", "user", "--target", "all", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("[dry-run] install"), 4)
        self.assertEqual(tree(self.home), [])

    def test_dry_run_reports_an_existing_destination_without_touching_it(self):
        existing = self.workspace / ".agents" / "skills" / SKILL_NAME
        existing.mkdir(parents=True)
        (existing / "marker.txt").write_text("既存\n", encoding="utf-8")
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common", "--dry-run",
                                        "--on-conflict", "backup")
        self.assertEqual(code, 0)
        self.assertIn("existing moves to", out)
        self.assertEqual(tree(existing), ["marker.txt"])
        self.assertFalse((self.workspace / ".agents" / "skills.bak").exists())


class CopyTest(InstallCase):
    def test_copy_installs_every_file(self):
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0, out)
        installed = self.workspace / ".agents" / "skills" / SKILL_NAME
        self.assertTrue((installed / "SKILL.md").is_file())
        self.assertTrue((installed / "references" / "readability-rules.md").is_file())
        self.assertTrue((installed / "scripts" / "measure.py").is_file())
        self.assertTrue((installed / "assets" / "examples.md").is_file())
        self.assertFalse(installed.is_symlink())

    def test_copy_excludes_bytecode_caches(self):
        source = self.tmp / "src" / SKILL_NAME
        write_skill(self.tmp / "src")
        (source / "__pycache__").mkdir()
        (source / "__pycache__" / "x.cpython-314.pyc").write_bytes(b"\x00")
        code, _, _ = self.run_install("--scope", "workspace", "--target", "common", "--source", str(source))
        self.assertEqual(code, 0)
        installed = self.workspace / ".agents" / "skills" / SKILL_NAME
        self.assertEqual(tree(installed), ["SKILL.md"])

    def test_no_staging_directory_is_left_behind(self):
        self.run_install("--scope", "workspace", "--target", "common")
        leftovers = [p for p in (self.workspace / ".agents" / "skills").iterdir() if p.name != SKILL_NAME]
        self.assertEqual(leftovers, [])

    def test_workspace_all_creates_both_locations(self):
        code, _, _ = self.run_install("--scope", "workspace", "--target", "all")
        self.assertEqual(code, 0)
        self.assertTrue((self.workspace / ".agents" / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertTrue((self.workspace / ".claude" / "skills" / SKILL_NAME / "SKILL.md").is_file())

    def test_user_scope_writes_under_home_only(self):
        code, _, _ = self.run_install("--scope", "user", "--target", "claude-code")
        self.assertEqual(code, 0)
        self.assertTrue((self.home / ".claude" / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertEqual(tree(self.workspace), [])

    def test_invalid_source_installs_nothing(self):
        broken = write_skill(self.tmp / "broken", frontmatter="---\nname: japanese-readability-editor\n---\n")
        code, _, err = self.run_install("--scope", "workspace", "--target", "common", "--source", str(broken))
        self.assertEqual(code, 1)
        self.assertIn("nothing was installed", err)
        self.assertEqual(tree(self.workspace), [])


class ConflictTest(InstallCase):
    def make_existing(self) -> Path:
        existing = self.workspace / ".agents" / "skills" / SKILL_NAME
        existing.mkdir(parents=True)
        (existing / "SKILL.md").write_text("ユーザーの既存ファイル\n", encoding="utf-8")
        (existing / "marker.txt").write_text("既存\n", encoding="utf-8")
        return existing

    def test_existing_installation_is_not_overwritten_by_default(self):
        existing = self.make_existing()
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("skip", out)
        self.assertEqual((existing / "SKILL.md").read_text(encoding="utf-8"), "ユーザーの既存ファイル\n")
        self.assertTrue((existing / "marker.txt").exists())

    def test_backup_moves_the_existing_copy_aside(self):
        existing = self.make_existing()
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "backup")
        self.assertEqual(code, 0, out)
        backups = list((self.workspace / ".agents" / "skills.bak").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "marker.txt").read_text(encoding="utf-8"), "既存\n")
        self.assertFalse((existing / "marker.txt").exists())
        self.assertIn("Japanese Readability Editor", (existing / "SKILL.md").read_text(encoding="utf-8"))

    def test_backup_lives_outside_the_scanned_skills_directory(self):
        self.make_existing()
        self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "backup")
        names = [p.name for p in (self.workspace / ".agents" / "skills").iterdir()]
        self.assertEqual(names, [SKILL_NAME])

    def test_overwrite_replaces_the_existing_copy(self):
        existing = self.make_existing()
        code, _, _ = self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "overwrite")
        self.assertEqual(code, 0)
        self.assertFalse((existing / "marker.txt").exists())
        self.assertTrue((existing / "scripts" / "measure.py").is_file())
        self.assertFalse((self.workspace / ".agents" / "skills.bak").exists())

    def test_overwrite_refuses_a_directory_that_is_not_a_skill(self):
        existing = self.workspace / ".agents" / "skills" / SKILL_NAME
        existing.mkdir(parents=True)
        (existing / "precious.txt").write_text("大事なデータ\n", encoding="utf-8")
        code, _, err = self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "overwrite")
        self.assertEqual(code, 1)
        self.assertIn("not a skill directory", err)
        self.assertEqual((existing / "precious.txt").read_text(encoding="utf-8"), "大事なデータ\n")

    def test_installing_twice_is_safe(self):
        self.run_install("--scope", "workspace", "--target", "common")
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("skip", out)

    def test_backup_uses_a_timestamped_name(self):
        existing = self.make_existing()
        destination = install.Destination(existing.parent, ["common"])
        fixed = datetime(2026, 9, 29, 12, 34, 56)
        outcome = install.install_one(SKILL_DIR, destination, link=False, on_conflict="backup",
                                      dry_run=False, now=lambda: fixed)
        self.assertEqual(outcome.status, "installed")
        self.assertTrue((existing.parent.parent / "skills.bak" / f"{SKILL_NAME}-20260929-123456").is_dir())


@unittest.skipUnless(symlinks_supported(), "symlinks are not available on this system")
class LinkTest(InstallCase):
    def test_link_creates_a_symlink_to_the_source(self):
        code, out, err = self.run_install("--scope", "workspace", "--target", "common", "--link")
        self.assertEqual(code, 0, out + err)
        installed = self.workspace / ".agents" / "skills" / SKILL_NAME
        self.assertTrue(installed.is_symlink())
        self.assertEqual(installed.resolve(), SKILL_DIR.resolve())

    def test_link_is_skipped_when_it_already_points_at_the_source(self):
        self.run_install("--scope", "workspace", "--target", "common", "--link")
        code, out, _ = self.run_install("--scope", "workspace", "--target", "common", "--link")
        self.assertEqual(code, 0)
        self.assertIn("already points at the source", out)

    def test_overwrite_can_replace_a_symlink_without_touching_its_target(self):
        self.run_install("--scope", "workspace", "--target", "common", "--link")
        code, _, _ = self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "overwrite")
        installed = self.workspace / ".agents" / "skills" / SKILL_NAME
        self.assertEqual(code, 0)
        self.assertFalse(installed.is_symlink())
        self.assertTrue((SKILL_DIR / "SKILL.md").is_file())


if __name__ == "__main__":
    unittest.main()
