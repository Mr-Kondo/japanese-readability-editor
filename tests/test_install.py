"""tools/install.py のテスト。"""

import shutil
import unittest
from datetime import datetime
from pathlib import Path

from helpers import (SKILL_DIR, SKILL_NAME, TOOLS_DIR, copy_real_skill, hermes_default_home, load_module, run_script,
                     symlinks_supported, temporary_directory, write_skill)

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

    def test_all_does_not_include_opencode_or_hermes(self):
        # 利用者のホームに、使っていない製品の設定ディレクトリを作らない。既存の all の挙動も変えない。
        for scope in ("workspace", "user"):
            with self.subTest(scope=scope):
                joined = " ".join(self.dirs(scope, ["all"]))
                self.assertNotIn("opencode", joined)
                self.assertNotIn("hermes", joined)

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
        portable = out.replace("\\", "/")  # Windows ではパスが バックスラッシュ区切りで表示される
        self.assertIn(".agents/skills", portable)
        self.assertIn(".claude/skills", portable)
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


class OpenCodeTargetTest(InstallCase):
    def test_workspace_path(self):
        self.assertEqual(self.dirs("workspace", ["opencode"]), [".opencode/skills"])

    def test_user_default_path(self):
        self.assertEqual(self.dirs("user", ["opencode"]), [".config/opencode/skills"])

    def test_user_path_follows_xdg_config_home_and_opencode_config_dir(self):
        xdg = self.tmp / "xdg conf"
        options = install.LocationOptions(env={"XDG_CONFIG_HOME": str(xdg)})
        [destination] = install.resolve_destinations("user", ["opencode"], self.workspace, self.home, options)
        self.assertEqual(destination.skills_dir, xdg / "opencode" / "skills")
        self.assertEqual(destination.origin, "$XDG_CONFIG_HOME/opencode")
        options = install.LocationOptions(env={"XDG_CONFIG_HOME": str(xdg)}, opencode_config_dir=self.tmp / "oc dir")
        [destination] = install.resolve_destinations("user", ["opencode"], self.workspace, self.home, options)
        self.assertEqual(destination.skills_dir, self.tmp / "oc dir" / "skills")

    def test_install_writes_where_opencode_looks_and_the_skill_is_complete(self):
        code, out, err = self.run_install("--scope", "workspace", "--target", "opencode")
        self.assertEqual(code, 0, out + err)
        installed = self.workspace / ".opencode" / "skills" / SKILL_NAME
        self.assertTrue(install.skill_env.diff_trees(SKILL_DIR, installed).identical)
        self.assertTrue((installed / "data" / "kokugo-rules.json").is_file())
        self.assertIn("verify   OK", out)

    def test_user_scope_with_home_ignores_the_process_environment(self):
        leak = self.tmp / "must-stay-empty"
        code, out, err = run_script(SCRIPT, "--scope", "user", "--target", "opencode", "--home", str(self.home),
                                    env={"XDG_CONFIG_HOME": str(leak), "OPENCODE_CONFIG_DIR": str(leak)})
        self.assertEqual(code, 0, out + err)
        self.assertTrue((self.home / ".config" / "opencode" / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertFalse(leak.exists())

    def test_without_home_the_environment_decides(self):
        xdg = self.tmp / "xdg"
        code, out, err = run_script(SCRIPT, "--scope", "user", "--target", "opencode",
                                    env={"HOME": str(self.home), "USERPROFILE": str(self.home), "XDG_CONFIG_HOME": str(xdg)})
        self.assertEqual(code, 0, out + err)
        self.assertTrue((xdg / "opencode" / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn("decided by: $XDG_CONFIG_HOME/opencode", out)

    def test_a_duplicate_in_agents_skills_is_reported_and_left_alone(self):
        duplicate = copy_real_skill(self.workspace / ".agents" / "skills")
        (duplicate / "references" / "readability-rules.md").write_text("手元の版\n", encoding="utf-8")
        code, out, _ = self.run_install("--scope", "workspace", "--target", "opencode")
        self.assertEqual(code, 0)
        self.assertIn("also discoverable at", out)
        self.assertIn("DIFFERENT from the source", out)
        self.assertEqual((duplicate / "references" / "readability-rules.md").read_text(encoding="utf-8"), "手元の版\n")

    def test_an_identical_duplicate_in_claude_skills_is_reported_as_identical(self):
        copy_real_skill(self.home / ".claude" / "skills")
        code, out, _ = self.run_install("--scope", "user", "--target", "opencode")
        self.assertEqual(code, 0)
        self.assertIn("identical to the source", out)
        self.assertIn(".claude", out)

    def test_dry_run_reports_duplicates_without_writing(self):
        copy_real_skill(self.workspace / ".agents" / "skills")
        before = tree(self.workspace)
        code, out, _ = self.run_install("--scope", "workspace", "--target", "opencode", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("also discoverable at", out)
        self.assertEqual(tree(self.workspace), before)

    def test_no_duplicate_warning_when_there_is_only_one_copy(self):
        _, out, _ = self.run_install("--scope", "workspace", "--target", "opencode")
        self.assertNotIn("also discoverable", out)


class HermesTargetTest(InstallCase):
    def make_profile(self, name: str) -> Path:
        directory = hermes_default_home(self.home) / "profiles" / name
        directory.mkdir(parents=True)
        (directory / "config.yaml").write_text("{}\n", encoding="utf-8")
        return directory

    def test_workspace_path_and_the_trust_note(self):
        code, out, err = self.run_install("--scope", "workspace", "--target", "hermes")
        self.assertEqual(code, 0, out + err)
        self.assertTrue((self.workspace / ".hermes" / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn("hermes skills trust", out)

    def test_user_default_installs_under_the_default_hermes_home_and_prints_it(self):
        code, out, err = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0, out + err)
        self.assertTrue((hermes_default_home(self.home) / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn(str(hermes_default_home(self.home) / "skills"), out)
        self.assertIn("decided by: default", out)

    def test_hermes_home_environment_variable_is_followed_without_home(self):
        target_home = self.tmp / "Hermes ホーム"
        code, out, err = run_script(SCRIPT, "--scope", "user", "--target", "hermes",
                                    env={"HOME": str(self.home), "USERPROFILE": str(self.home), "HERMES_HOME": str(target_home)})
        self.assertEqual(code, 0, out + err)
        self.assertTrue((target_home / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn("decided by: $HERMES_HOME", out)
        self.assertFalse((hermes_default_home(self.home)).exists())

    def test_home_ignores_hermes_home_in_the_environment(self):
        leak = self.tmp / "must-stay-empty"
        code, out, err = run_script(SCRIPT, "--scope", "user", "--target", "hermes", "--home", str(self.home),
                                    env={"HERMES_HOME": str(leak)})
        self.assertEqual(code, 0, out + err)
        self.assertTrue((hermes_default_home(self.home) / "skills" / SKILL_NAME).is_dir())
        self.assertFalse(leak.exists())

    def test_explicit_hermes_home(self):
        explicit = self.tmp / "explicit home"
        code, out, err = self.run_install("--scope", "user", "--target", "hermes", "--hermes-home", str(explicit))
        self.assertEqual(code, 0, out + err)
        self.assertTrue((explicit / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertIn("decided by: --hermes-home", out)

    def test_profile_installs_into_that_profile_only(self):
        profile = self.make_profile("coder")
        code, out, err = self.run_install("--scope", "user", "--target", "hermes", "--profile", "coder")
        self.assertEqual(code, 0, out + err)
        self.assertTrue((profile / "skills" / SKILL_NAME / "SKILL.md").is_file())
        self.assertFalse((hermes_default_home(self.home) / "skills").exists())

    def test_unknown_profile_is_refused_and_nothing_is_written(self):
        code, _, err = self.run_install("--scope", "user", "--target", "hermes", "--profile", "ghost")
        self.assertEqual(code, 2)
        self.assertIn("not found", err)
        self.assertEqual(tree(self.home), [])

    def test_the_sticky_profile_is_followed_and_reported(self):
        profile = self.make_profile("coder")
        (hermes_default_home(self.home) / "active_profile").write_text("coder\n", encoding="utf-8")
        code, out, err = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0, out + err)
        self.assertTrue((profile / "skills" / SKILL_NAME).is_dir())
        self.assertIn("active profile 'coder'", out)

    def test_hermes_home_and_profile_cannot_be_combined(self):
        code, _, err = self.run_install("--scope", "user", "--target", "hermes", "--hermes-home", str(self.tmp), "--profile", "x")
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined", err)

    def test_options_are_refused_where_they_would_be_ignored(self):
        cases = [
            (("--scope", "user", "--target", "common", "--profile", "coder"), "--profile applies to --target hermes"),
            (("--scope", "user", "--target", "hermes", "--opencode-config-dir", str(self.tmp)), "--opencode-config-dir applies"),
            (("--scope", "workspace", "--target", "hermes", "--profile", "coder"), "applies to --scope user"),
            (("--scope", "workspace", "--target", "hermes", "--hermes-home", str(self.tmp)), "applies to --scope user"),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                code, _, err = self.run_install(*args, "--dry-run")
                self.assertEqual(code, 2)
                self.assertIn(message, err)

    def test_duplicates_in_external_dirs_and_agents_skills_are_reported(self):
        (self.workspace / ".git").mkdir()
        copy_real_skill(self.home / ".agents" / "skills")
        hermes_home = hermes_default_home(self.home)
        hermes_home.mkdir(parents=True)
        (hermes_home / "config.yaml").write_text("skills:\n  external_dirs:\n    - ~/.agents/skills\n", encoding="utf-8")
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0)
        self.assertIn("also discoverable at", out)
        self.assertIn("higher-precedence copy", out)

    @unittest.skipUnless(symlinks_supported(), "symlinks are not available on this system")
    def test_link_install_warns_that_remote_backends_do_not_receive_symlinks(self):
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes", "--link")
        self.assertEqual(code, 0)
        self.assertIn("Docker, SSH, Modal or Daytona", out)


class IdempotenceAndProtectionTest(InstallCase):
    def digest(self, root: Path):
        return install.skill_env.file_digests(root)

    def test_second_run_changes_nothing_and_says_so(self):
        self.run_install("--scope", "user", "--target", "hermes")
        installed = hermes_default_home(self.home) / "skills" / SKILL_NAME
        marker_times = {p: p.stat().st_mtime_ns for p in installed.rglob("*") if p.is_file()}
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0)
        self.assertIn("already up to date", out)
        self.assertIn("1 unchanged", out)
        self.assertEqual({p: p.stat().st_mtime_ns for p in installed.rglob("*") if p.is_file()}, marker_times)

    def test_identical_content_is_never_backed_up_or_removed(self):
        self.run_install("--scope", "user", "--target", "opencode")
        for mode in ("skip", "backup", "overwrite"):
            with self.subTest(on_conflict=mode):
                code, out, _ = self.run_install("--scope", "user", "--target", "opencode", "--on-conflict", mode)
                self.assertEqual(code, 0)
                self.assertIn("already up to date", out)
        self.assertFalse((self.home / ".config" / "opencode" / "skills.bak").exists())

    def test_different_content_is_kept_by_default_and_the_difference_is_named(self):
        self.run_install("--scope", "user", "--target", "hermes")
        edited = hermes_default_home(self.home) / "skills" / SKILL_NAME / "references" / "readability-rules.md"
        edited.write_text("利用者が直したもの\n", encoding="utf-8")
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0)
        self.assertIn("differs from the source", out)
        self.assertIn("references/readability-rules.md", out)
        self.assertEqual(edited.read_text(encoding="utf-8"), "利用者が直したもの\n")
        self.assertIn("1 skipped", out)

    def test_an_extra_file_in_the_installed_copy_counts_as_different(self):
        self.run_install("--scope", "user", "--target", "hermes")
        extra = hermes_default_home(self.home) / "skills" / SKILL_NAME / "notes.txt"
        extra.write_text("メモ\n", encoding="utf-8")
        _, out, _ = self.run_install("--scope", "user", "--target", "hermes")
        self.assertIn("differs from the source", out)
        self.assertIn("extra: notes.txt", out)
        self.assertTrue(extra.exists())

    def test_backup_keeps_the_old_copy_so_it_can_be_restored(self):
        self.run_install("--scope", "user", "--target", "hermes")
        edited = hermes_default_home(self.home) / "skills" / SKILL_NAME / "references" / "readability-rules.md"
        edited.write_text("利用者が直したもの\n", encoding="utf-8")
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes", "--on-conflict", "backup")
        self.assertEqual(code, 0, out)
        backups = list((hermes_default_home(self.home) / "skills.bak").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "references" / "readability-rules.md").read_text(encoding="utf-8"), "利用者が直したもの\n")
        self.assertTrue(self.digest(hermes_default_home(self.home) / "skills" / SKILL_NAME) == self.digest(SKILL_DIR))

    def test_moving_the_backup_back_restores_the_previous_copy(self):
        # docs/installation.md の復元手順(置き直したものを消し、退避したものを戻す)が成り立つ。
        self.run_install("--scope", "user", "--target", "hermes")
        installed = hermes_default_home(self.home) / "skills" / SKILL_NAME
        edited = installed / "references" / "readability-rules.md"
        edited.write_text("利用者が直したもの\n", encoding="utf-8")
        before = self.digest(installed)
        self.run_install("--scope", "user", "--target", "hermes", "--on-conflict", "backup")
        self.assertNotEqual(self.digest(installed), before)
        [backup] = list((hermes_default_home(self.home) / "skills.bak").iterdir())
        shutil.rmtree(installed)
        shutil.move(str(backup), str(installed))
        self.assertEqual(self.digest(installed), before)
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes")
        self.assertEqual(code, 0)
        self.assertIn("differs from the source", out)  # 戻したものは、また保護される

    def test_dry_run_with_a_different_existing_copy_changes_nothing(self):
        self.run_install("--scope", "user", "--target", "hermes")
        edited = hermes_default_home(self.home) / "skills" / SKILL_NAME / "SKILL.md"
        edited.write_text("手元の版\n", encoding="utf-8")
        before = tree(self.home)
        code, out, _ = self.run_install("--scope", "user", "--target", "hermes", "--on-conflict", "overwrite", "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertEqual(tree(self.home), before)
        self.assertEqual(edited.read_text(encoding="utf-8"), "手元の版\n")

    def test_dry_run_on_a_clean_target_writes_nothing_for_both_targets(self):
        code, out, _ = self.run_install("--scope", "user", "--target", "opencode,hermes", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(out.count("[dry-run] install"), 2)
        self.assertEqual(tree(self.home), [])
        self.assertEqual(tree(self.workspace), [])


class ExplicitDestinationTest(InstallCase):
    def test_dest_with_spaces_and_japanese(self):
        dest = self.tmp / "私の skills フォルダ"
        code, out, err = self.run_install("--dest", str(dest))
        self.assertEqual(code, 0, out + err)
        self.assertTrue((dest / SKILL_NAME / "scripts" / "measure.py").is_file())
        self.assertEqual(tree(self.home), [])
        self.assertEqual(tree(self.workspace), [])

    def test_dest_with_a_target_verifies_against_that_environment(self):
        dest = self.tmp / "skills"
        code, out, _ = self.run_install("--dest", str(dest), "--target", "hermes")
        self.assertEqual(code, 0)
        self.assertIn("verify   OK", out)

    def test_dest_dry_run_writes_nothing(self):
        dest = self.tmp / "skills"
        code, out, _ = self.run_install("--dest", str(dest), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("[dry-run]", out)
        self.assertFalse(dest.exists())

    def test_dest_and_scope_are_mutually_exclusive(self):
        code, _, err = self.run_install("--dest", str(self.tmp / "s"), "--scope", "user")
        self.assertEqual(code, 2)
        self.assertIn("replaces --scope", err)

    def test_dest_cannot_take_location_options(self):
        code, _, err = self.run_install("--dest", str(self.tmp / "s"), "--profile", "coder")
        self.assertEqual(code, 2)
        self.assertIn("cannot be combined with --dest", err)

    def test_neither_scope_nor_dest_is_an_error(self):
        code, _, err = self.run_install("--target", "hermes")
        self.assertEqual(code, 2)
        self.assertIn("--scope or --dest", err)

    def test_dest_rejects_an_unknown_target(self):
        code, _, err = self.run_install("--dest", str(self.tmp / "s"), "--target", "vscode")
        self.assertEqual(code, 2)
        self.assertIn("unknown target", err)

    def test_rerunning_into_dest_is_idempotent(self):
        dest = self.tmp / "skills"
        self.run_install("--dest", str(dest))
        code, out, _ = self.run_install("--dest", str(dest))
        self.assertEqual(code, 0)
        self.assertIn("already up to date", out)


class InstalledCopyBehavesLikeTheSourceTest(InstallCase):
    """配置した複製が、正本と同じ出力を返す。リポジトリの外、空白と日本語を含むパスから実行する。"""

    def test_every_script_prints_the_same_from_the_installed_copy(self):
        base = self.tmp / "日本語 の 配置先"
        code, out, err = self.run_install("--dest", str(base))
        self.assertEqual(code, 0, out + err)
        installed = base / SKILL_NAME
        fixtures = Path(__file__).resolve().parent / "fixtures"
        work = self.tmp / "作業 dir"
        work.mkdir()
        for name in ("before.md", "after_split.md", "after_changed_char.md"):
            (work / name).write_text((fixtures / name).read_text(encoding="utf-8"), encoding="utf-8")
        commands = [
            ("measure.py", "--locate", "before.md"),
            ("verify_preservation.py", "--strict", "before.md", "after_split.md"),
            ("verify_preservation.py", "before.md", "after_changed_char.md"),
            ("compare_rewrite.py", "--json", "--tokenizer", "regex", "before.md", "after_changed_char.md"),
            ("check_kokugo.py", "before.md", "--profile", "general-tech", "--json"),
        ]
        for command in commands:
            with self.subTest(command=" ".join(command)):
                from_source = run_script(SKILL_DIR / "scripts" / command[0], *command[1:], cwd=work)
                from_copy = run_script(installed / "scripts" / command[0], *command[1:], cwd=work)
                self.assertEqual(from_copy[0], from_source[0])
                self.assertEqual(from_copy[1].replace(str(installed), "<SKILL>"), from_source[1].replace(str(SKILL_DIR), "<SKILL>"))
        self.assertEqual(tree(work), sorted(["before.md", "after_split.md", "after_changed_char.md"]))
        self.assertFalse(list(installed.rglob("__pycache__")))


if __name__ == "__main__":
    unittest.main()
