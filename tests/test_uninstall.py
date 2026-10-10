"""tools/uninstall.py のテスト。"""

import os
import unittest
from pathlib import Path

from helpers import (SKILL_NAME, TOOLS_DIR, copy_real_skill, hermes_default_home, load_module, run_script,
                     symlinks_supported, temporary_directory)

install = load_module("install", TOOLS_DIR / "install.py")
uninstall = load_module("uninstall", TOOLS_DIR / "uninstall.py")
INSTALL = TOOLS_DIR / "install.py"
UNINSTALL = TOOLS_DIR / "uninstall.py"


def tree(root: Path):
    return sorted(p.relative_to(root).as_posix() for p in root.rglob("*"))


class UninstallCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name).resolve()
        self.workspace = self.tmp / "workspace"
        self.home = self.tmp / "home"
        self.workspace.mkdir()
        self.home.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def locations(self, *args: str):
        return ("--workspace", str(self.workspace), "--home", str(self.home), *args)

    def run_install(self, *args: str):
        return run_script(INSTALL, *self.locations(*args))

    def run_uninstall(self, *args: str):
        return run_script(UNINSTALL, *self.locations(*args))

    def workspace_copy(self, skills_dir: str = ".agents/skills") -> Path:
        return self.workspace / skills_dir / SKILL_NAME

    def make_non_skill_directory(self) -> Path:
        directory = self.workspace_copy()
        directory.mkdir(parents=True)
        (directory / "precious.txt").write_text("大事なデータ\n", encoding="utf-8")
        return directory


class RemoveTest(UninstallCase):
    def test_removes_what_install_placed(self):
        self.run_install("--scope", "workspace", "--target", "common")
        code, out, err = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0, out + err)
        self.assertIn("summary: 1 removed", out)
        self.assertFalse(self.workspace_copy().exists())

    def test_keeps_the_skills_directory_and_the_other_skills_in_it(self):
        self.run_install("--scope", "workspace", "--target", "common")
        other = self.workspace / ".agents" / "skills" / "other-skill"
        other.mkdir()
        (other / "SKILL.md").write_text("別の Skill\n", encoding="utf-8")
        self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(tree(self.workspace / ".agents" / "skills"), ["other-skill", "other-skill/SKILL.md"])

    def test_workspace_all_removes_both_locations(self):
        self.run_install("--scope", "workspace", "--target", "all")
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "all")
        self.assertEqual(code, 0)
        self.assertIn("summary: 2 removed", out)
        self.assertFalse(self.workspace_copy().exists())
        self.assertFalse(self.workspace_copy(".claude/skills").exists())

    def test_user_scope_touches_home_only(self):
        self.run_install("--scope", "workspace", "--target", "claude-code")
        self.run_install("--scope", "user", "--target", "claude-code")
        code, _, _ = self.run_uninstall("--scope", "user", "--target", "claude-code")
        self.assertEqual(code, 0)
        self.assertFalse((self.home / ".claude" / "skills" / SKILL_NAME).exists())
        self.assertTrue(self.workspace_copy(".claude/skills").is_dir())

    def test_only_the_requested_target_is_removed(self):
        self.run_install("--scope", "workspace", "--target", "all")
        self.run_uninstall("--scope", "workspace", "--target", "claude-code")
        self.assertTrue(self.workspace_copy().is_dir())
        self.assertFalse(self.workspace_copy(".claude/skills").exists())

    def test_nothing_to_remove_is_not_an_error(self):
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("does not exist", out)
        self.assertIn("summary: 1 skipped", out)

    def test_running_twice_is_safe(self):
        self.run_install("--scope", "workspace", "--target", "common")
        self.run_uninstall("--scope", "workspace", "--target", "common")
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("does not exist", out)

    def test_unknown_target(self):
        code, _, err = self.run_uninstall("--scope", "workspace", "--target", "nope")
        self.assertEqual(code, 2)
        self.assertIn("unknown target", err)


class DryRunTest(UninstallCase):
    def test_dry_run_removes_nothing(self):
        self.run_install("--scope", "workspace", "--target", "all")
        before = tree(self.workspace)
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "all", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("[dry-run] remove"), 2)
        self.assertIn("summary: 2 dry-run", out)
        self.assertEqual(tree(self.workspace), before)

    def test_dry_run_for_a_missing_destination_says_so(self):
        code, out, _ = self.run_uninstall("--scope", "user", "--target", "common", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run] skip", out)
        self.assertEqual(tree(self.home), [])


class RefusalTest(UninstallCase):
    def test_refuses_a_directory_that_is_not_a_skill(self):
        directory = self.make_non_skill_directory()
        code, _, err = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 1)
        self.assertIn("not a skill directory", err)
        self.assertEqual((directory / "precious.txt").read_text(encoding="utf-8"), "大事なデータ\n")

    def test_a_refusal_does_not_stop_the_other_locations(self):
        self.run_install("--scope", "workspace", "--target", "claude-code")
        directory = self.make_non_skill_directory()
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "all")
        self.assertEqual(code, 1)
        self.assertIn("summary: 1 removed, 1 error", out)
        self.assertFalse(self.workspace_copy(".claude/skills").exists())
        self.assertTrue((directory / "precious.txt").is_file())

    def test_dry_run_also_reports_a_refusal(self):
        self.make_non_skill_directory()
        code, _, err = self.run_uninstall("--scope", "workspace", "--target", "common", "--dry-run")
        self.assertEqual(code, 1)
        self.assertIn("not a skill directory", err)

    def test_refuses_the_source_directory_itself(self):
        self.run_install("--scope", "workspace", "--target", "common")
        installed = self.workspace_copy()
        destination = install.Destination(installed.parent, ["common"])
        outcomes = uninstall.uninstall_one(destination, installed, include_backups=False, dry_run=False)
        self.assertEqual([o.status for o in outcomes], ["error"])
        self.assertIn("source directory itself", outcomes[0].message)
        self.assertTrue((installed / "SKILL.md").is_file())


@unittest.skipUnless(symlinks_supported(), "symlinks are not available on this system")
class LinkTest(UninstallCase):
    def test_removes_only_the_link_not_the_source(self):
        # リンクの先は、リポジトリの Skill ではなく、一時ディレクトリの複製にする(削除が先へ及んでも、正本を壊さない)
        source = copy_real_skill(self.tmp / "src")
        self.run_install("--scope", "workspace", "--target", "common", "--link", "--source", str(source))
        self.assertTrue(self.workspace_copy().is_symlink())
        code, out, err = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0, out + err)
        self.assertIn("symlink only", out)
        self.assertFalse(self.workspace_copy().is_symlink())
        self.assertFalse(self.workspace_copy().exists())
        self.assertTrue((source / "SKILL.md").is_file())
        self.assertTrue((source / "scripts" / "measure.py").is_file())

    def test_removes_a_link_whose_target_is_gone(self):
        location = self.workspace_copy()
        location.parent.mkdir(parents=True)
        os.symlink(self.tmp / "gone", location, target_is_directory=True)
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("summary: 1 removed", out)
        self.assertFalse(location.is_symlink())


class BackupTest(UninstallCase):
    def install_with_backup(self) -> Path:
        """内容の違う既存のコピーを退避させて、skills.bak/ に1件の退避を作る(内容が同じなら退避しない)。"""
        self.run_install("--scope", "workspace", "--target", "common")
        edited = self.workspace_copy() / "references" / "readability-rules.md"
        edited.write_text("利用者が直したもの\n", encoding="utf-8")
        self.run_install("--scope", "workspace", "--target", "common", "--on-conflict", "backup")
        root = self.workspace / ".agents" / "skills.bak"
        self.assertEqual(len(list(root.iterdir())), 1)
        return root

    def test_backups_are_kept_by_default_and_reported(self):
        root = self.install_with_backup()
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common")
        self.assertEqual(code, 0)
        self.assertIn("1 backup(s) remain", out)
        self.assertIn("--include-backups", out)
        self.assertFalse(self.workspace_copy().exists())
        self.assertEqual(len(list(root.iterdir())), 1)

    def test_include_backups_removes_them_and_the_empty_backup_directory(self):
        root = self.install_with_backup()
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common", "--include-backups")
        self.assertEqual(code, 0)
        self.assertIn("summary: 2 removed", out)
        self.assertFalse(root.exists())
        self.assertFalse(self.workspace_copy().exists())

    def test_include_backups_removes_backups_even_when_the_install_is_gone(self):
        root = self.install_with_backup()
        self.run_uninstall("--scope", "workspace", "--target", "common")
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common", "--include-backups")
        self.assertEqual(code, 0)
        self.assertIn("summary: 1 removed, 1 skipped", out)
        self.assertFalse(root.exists())

    def test_dry_run_with_include_backups_removes_nothing(self):
        root = self.install_with_backup()
        before = tree(self.workspace)
        code, out, _ = self.run_uninstall("--scope", "workspace", "--target", "common", "--include-backups", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("[dry-run] remove"), 2)
        self.assertTrue(root.is_dir())
        self.assertEqual(tree(self.workspace), before)

    def test_other_things_in_the_backup_directory_are_left_alone(self):
        root = self.install_with_backup()
        (root / "my-own-notes").mkdir()
        (root / f"{SKILL_NAME}-not-a-timestamp").mkdir()
        code, _, _ = self.run_uninstall("--scope", "workspace", "--target", "common", "--include-backups")
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in root.iterdir()), [f"{SKILL_NAME}-not-a-timestamp", "my-own-notes"])

    def test_a_backup_that_is_not_a_skill_is_refused(self):
        root = self.install_with_backup()
        for entry in root.iterdir():
            (entry / "SKILL.md").unlink()
            (entry / "precious.txt").write_text("大事なデータ\n", encoding="utf-8")
        code, _, err = self.run_uninstall("--scope", "workspace", "--target", "common", "--include-backups")
        self.assertEqual(code, 1)
        self.assertIn("not a skill directory", err)
        self.assertEqual(len(list(root.iterdir())), 1)


class OpenCodeAndHermesTest(UninstallCase):
    def test_removes_what_install_placed_for_each_new_target(self):
        cases = [("workspace", "opencode", self.workspace / ".opencode" / "skills"),
                 ("workspace", "hermes", self.workspace / ".hermes" / "skills"),
                 ("user", "opencode", self.home / ".config" / "opencode" / "skills"),
                 ("user", "hermes", hermes_default_home(self.home) / "skills")]
        for scope, target, skills_dir in cases:
            with self.subTest(scope=scope, target=target):
                self.run_install("--scope", scope, "--target", target)
                self.assertTrue((skills_dir / SKILL_NAME).is_dir())
                code, out, err = self.run_uninstall("--scope", scope, "--target", target)
                self.assertEqual(code, 0, out + err)
                self.assertFalse((skills_dir / SKILL_NAME).exists())
                self.assertTrue(skills_dir.is_dir())  # skills/ とほかの Skill は残す

    def test_other_skills_beside_ours_are_kept(self):
        self.run_install("--scope", "user", "--target", "hermes")
        other = hermes_default_home(self.home) / "skills" / "writing" / "another-skill"
        other.mkdir(parents=True)
        (other / "SKILL.md").write_text("---\nname: another-skill\ndescription: x\n---\n", encoding="utf-8")
        self.run_uninstall("--scope", "user", "--target", "hermes")
        self.assertTrue((other / "SKILL.md").is_file())

    def test_hermes_profile_and_home_options_are_shared_with_install(self):
        profile = hermes_default_home(self.home) / "profiles" / "coder"
        profile.mkdir(parents=True)
        (profile / "config.yaml").write_text("{}\n", encoding="utf-8")
        self.run_install("--scope", "user", "--target", "hermes", "--profile", "coder")
        self.assertTrue((profile / "skills" / SKILL_NAME).is_dir())
        code, out, err = self.run_uninstall("--scope", "user", "--target", "hermes", "--profile", "coder")
        self.assertEqual(code, 0, out + err)
        self.assertFalse((profile / "skills" / SKILL_NAME).exists())

    def test_dest_is_removed_the_same_way(self):
        dest = self.tmp / "私の skills"
        self.run_install("--dest", str(dest))
        code, out, err = self.run_uninstall("--dest", str(dest))
        self.assertEqual(code, 0, out + err)
        self.assertFalse((dest / SKILL_NAME).exists())
        self.assertTrue(dest.is_dir())

    def test_a_different_installed_copy_is_removed_only_when_it_is_a_skill_directory(self):
        self.run_install("--scope", "user", "--target", "opencode")
        edited = self.home / ".config" / "opencode" / "skills" / SKILL_NAME / "SKILL.md"
        edited.write_text("手元の版\n", encoding="utf-8")
        before = tree(self.home)
        code, out, _ = self.run_uninstall("--scope", "user", "--target", "opencode", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(tree(self.home), before)
        self.assertIn("remove", out)


if __name__ == "__main__":
    unittest.main()
