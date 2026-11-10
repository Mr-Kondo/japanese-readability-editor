"""tools/skill_env.py のテスト。OpenCode と Hermes の配置先の解決、同名 Skill の探索、内容の比較。"""

import os
import unittest
from pathlib import Path
from unittest import mock

from helpers import SKILL_DIR, SKILL_NAME, TOOLS_DIR, copy_real_skill, load_module, symlinks_supported, \
    temporary_directory, write_skill

skill_env = load_module("skill_env", TOOLS_DIR / "skill_env.py")


class EnvCase(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name).resolve()
        self.home = self.tmp / "ホーム dir"
        self.workspace = self.tmp / "ワークスペース dir"
        self.home.mkdir()
        self.workspace.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def host(self, env=None, platform: str = "linux"):
        return skill_env.Host(self.workspace, self.home, env or {}, platform)

    def make_profile(self, root: Path, name: str) -> Path:
        directory = root / "profiles" / name
        directory.mkdir(parents=True)
        (directory / "config.yaml").write_text("{}\n", encoding="utf-8")
        return directory


class OpenCodeResolveTest(EnvCase):
    def resolve(self, scope="user", config_dir=None, env=None):
        return skill_env.resolve_opencode(scope, self.host(env), config_dir)

    def test_workspace_is_the_project_opencode_directory(self):
        resolution = self.resolve("workspace")
        self.assertEqual(resolution.skills_dir, self.workspace / ".opencode" / "skills")

    def test_user_default_is_dot_config_opencode(self):
        resolution = self.resolve()
        self.assertEqual(resolution.skills_dir, self.home / ".config" / "opencode" / "skills")
        self.assertIn("default", resolution.origin)

    def test_xdg_config_home_is_followed(self):
        resolution = self.resolve(env={"XDG_CONFIG_HOME": str(self.tmp / "xdg")})
        self.assertEqual(resolution.skills_dir, self.tmp / "xdg" / "opencode" / "skills")
        self.assertEqual(resolution.origin, "$XDG_CONFIG_HOME/opencode")

    def test_opencode_config_dir_beats_xdg(self):
        resolution = self.resolve(env={"XDG_CONFIG_HOME": str(self.tmp / "xdg"),
                                       "OPENCODE_CONFIG_DIR": str(self.tmp / "oc config")})
        self.assertEqual(resolution.skills_dir, self.tmp / "oc config" / "skills")
        self.assertEqual(resolution.origin, "$OPENCODE_CONFIG_DIR")

    def test_explicit_config_dir_beats_the_environment(self):
        resolution = self.resolve(config_dir=self.tmp / "explicit", env={"OPENCODE_CONFIG_DIR": str(self.tmp / "env")})
        self.assertEqual(resolution.skills_dir, self.tmp / "explicit" / "skills")

    def test_the_process_environment_is_not_read_implicitly(self):
        with mock.patch.dict(os.environ, {"XDG_CONFIG_HOME": str(self.tmp / "leak")}):
            self.assertEqual(self.resolve().skills_dir, self.home / ".config" / "opencode" / "skills")

    def test_tilde_in_the_environment_is_expanded_against_the_given_home(self):
        resolution = self.resolve(env={"OPENCODE_CONFIG_DIR": "~/my-opencode"})
        self.assertEqual(resolution.skills_dir, self.home / "my-opencode" / "skills")


class HermesResolveTest(EnvCase):
    def resolve(self, scope="user", hermes_home=None, profile=None, env=None):
        return skill_env.resolve_hermes(scope, self.host(env), hermes_home, profile)

    def test_default_is_dot_hermes(self):
        resolution = self.resolve(env={})
        self.assertEqual(resolution.skills_dir, self.home / ".hermes" / "skills")
        self.assertEqual(resolution.origin, "default")

    def test_hermes_home_environment_variable(self):
        resolution = self.resolve(env={"HERMES_HOME": str(self.tmp / "custom home")})
        self.assertEqual(resolution.skills_dir, self.tmp / "custom home" / "skills")
        self.assertEqual(resolution.origin, "$HERMES_HOME")

    def test_explicit_hermes_home_beats_the_environment(self):
        resolution = self.resolve(hermes_home=self.tmp / "explicit", env={"HERMES_HOME": str(self.tmp / "env")})
        self.assertEqual(resolution.skills_dir, self.tmp / "explicit" / "skills")
        self.assertEqual(resolution.origin, "--hermes-home")

    def test_named_profile_lives_under_profiles(self):
        self.make_profile(self.home / ".hermes", "coder")
        resolution = self.resolve(profile="coder", env={})
        self.assertEqual(resolution.skills_dir, self.home / ".hermes" / "profiles" / "coder" / "skills")

    def test_default_profile_is_the_root(self):
        self.assertEqual(self.resolve(profile="default", env={}).skills_dir, self.home / ".hermes" / "skills")

    def test_a_profile_that_does_not_exist_is_an_error(self):
        with self.assertRaisesRegex(ValueError, "not found"):
            self.resolve(profile="ghost", env={})

    def test_a_directory_without_identity_files_is_not_a_profile(self):
        (self.home / ".hermes" / "profiles" / "empty").mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "not found"):
            self.resolve(profile="empty", env={})

    def test_invalid_profile_names_are_rejected(self):
        for name in ("../escape", "Coder", "a b", "", "-x", "x" * 65):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, "invalid Hermes profile name"):
                    self.resolve(profile=name, env={})

    def test_hermes_home_pointing_at_a_profile_directory_is_used_as_is(self):
        profile = self.make_profile(self.home / ".hermes", "coder")
        resolution = self.resolve(env={"HERMES_HOME": str(profile)})
        self.assertEqual(resolution.skills_dir, profile / "skills")
        self.assertIn("profile directory", resolution.origin)

    def test_the_sticky_active_profile_is_followed(self):
        root = self.home / ".hermes"
        profile = self.make_profile(root, "coder")
        (root / "active_profile").write_text("coder\n", encoding="utf-8")
        resolution = self.resolve(env={})
        self.assertEqual(resolution.skills_dir, profile / "skills")
        self.assertIn("active profile 'coder'", resolution.origin)

    def test_a_sticky_profile_named_default_is_ignored(self):
        root = self.home / ".hermes"
        root.mkdir()
        (root / "active_profile").write_text("default\n", encoding="utf-8")
        self.assertEqual(self.resolve(env={}).skills_dir, root / "skills")

    def test_a_sticky_profile_that_is_gone_falls_back_to_the_root_with_a_note(self):
        root = self.home / ".hermes"
        root.mkdir()
        (root / "active_profile").write_text("gone\n", encoding="utf-8")
        resolution = self.resolve(env={})
        self.assertEqual(resolution.skills_dir, root / "skills")
        self.assertTrue(any("gone" in note for note in resolution.notes))

    def test_an_explicit_profile_beats_the_sticky_profile(self):
        root = self.home / ".hermes"
        self.make_profile(root, "coder")
        other = self.make_profile(root, "writer")
        (root / "active_profile").write_text("coder\n", encoding="utf-8")
        self.assertEqual(self.resolve(profile="writer", env={}).skills_dir, other / "skills")

    def test_a_custom_root_holds_its_own_profiles(self):
        custom = self.tmp / "opt data"
        custom.mkdir()
        profile = self.make_profile(custom, "coder")
        resolution = self.resolve(profile="coder", env={"HERMES_HOME": str(custom)})
        self.assertEqual(resolution.skills_dir, profile / "skills")

    def test_a_profile_is_found_when_hermes_home_already_points_at_another_profile(self):
        root = self.home / ".hermes"
        current = self.make_profile(root, "coder")
        other = self.make_profile(root, "writer")
        resolution = self.resolve(profile="writer", env={"HERMES_HOME": str(current)})
        self.assertEqual(resolution.skills_dir, other / "skills")

    def test_windows_default_is_under_localappdata(self):
        local = self.tmp / "Local"
        resolution = skill_env.resolve_hermes("user", self.host({"LOCALAPPDATA": str(local)}, "win32"))
        self.assertEqual(resolution.skills_dir, local / "hermes" / "skills")

    def test_data_dir_suffix_is_appended(self):
        resolution = self.resolve(env={"HERMES_DATA_DIR_SUFFIX": "-dev"})
        self.assertEqual(resolution.skills_dir, self.home / ".hermes-dev" / "skills")

    def test_workspace_scope_is_the_project_directory_and_says_trust_is_needed(self):
        resolution = self.resolve("workspace")
        self.assertEqual(resolution.skills_dir, self.workspace / ".hermes" / "skills")
        self.assertTrue(any("hermes skills trust" in note for note in resolution.notes))


class DiffTreesTest(EnvCase):
    def test_identical_copies(self):
        copy = copy_real_skill(self.tmp)
        self.assertTrue(skill_env.diff_trees(SKILL_DIR, copy).identical)

    def test_missing_extra_and_changed_files_are_told_apart(self):
        copy = copy_real_skill(self.tmp)
        (copy / "assets" / "examples.md").unlink()
        (copy / "extra.txt").write_text("x\n", encoding="utf-8")
        (copy / "SKILL.md").write_text("changed\n", encoding="utf-8")
        diff = skill_env.diff_trees(SKILL_DIR, copy)
        self.assertEqual((diff.missing, diff.extra, diff.changed), (["assets/examples.md"], ["extra.txt"], ["SKILL.md"]))
        self.assertFalse(diff.identical)
        self.assertIn("missing: assets/examples.md", diff.summary())

    def test_bytecode_caches_do_not_count_as_a_difference(self):
        copy = copy_real_skill(self.tmp)
        (copy / "scripts" / "__pycache__").mkdir()
        (copy / "scripts" / "__pycache__" / "measure.cpython-314.pyc").write_bytes(b"\x00")
        self.assertTrue(skill_env.diff_trees(SKILL_DIR, copy).identical)

    def test_a_path_that_is_not_a_directory_is_all_missing(self):
        diff = skill_env.diff_trees(SKILL_DIR, self.tmp / "nothing")
        self.assertTrue(diff.missing and not diff.extra and not diff.changed)


if __name__ == "__main__":
    unittest.main()
