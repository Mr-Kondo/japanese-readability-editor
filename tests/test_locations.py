"""tools/skill_env.py の配置先の表と解決(resolve_destinations、destinations_from_args)のテスト。"""

import argparse
import tempfile
import unittest
from pathlib import Path

from helpers import TOOLS_DIR, load_module

env = load_module("skill_env_locations", TOOLS_DIR / "skill_env.py")


class LocationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.ws, self.home = self.root / "ws", self.root / "home"

    def dirs(self, scope, *targets):
        return [d.skills_dir for d in env.resolve_destinations(scope, list(targets), self.ws, self.home)]

    def test_workspace_targets_that_read_agents_skills_share_one_location(self):
        self.assertEqual(self.dirs("workspace", "common", "codex", "copilot", "gemini-cli"), [self.ws / ".agents/skills"])

    def test_workspace_all_is_agents_and_claude(self):
        self.assertEqual(self.dirs("workspace", "all"), [self.ws / ".agents/skills", self.ws / ".claude/skills"])

    def test_user_paths(self):
        expected = {"common": ".agents/skills", "claude-code": ".claude/skills", "antigravity-ide": ".gemini/config/skills",
                    "antigravity-cli": ".gemini/antigravity-cli/skills", "opencode": ".config/opencode/skills",
                    "hermes": ".hermes/skills"}
        for target, path in expected.items():
            with self.subTest(target=target):
                self.assertEqual(self.dirs("user", target), [self.home / path])

    def test_user_all_excludes_opencode_and_hermes(self):
        self.assertEqual(len(self.dirs("user", "all")), 4)
        self.assertNotIn(self.home / ".hermes/skills", self.dirs("user", "all"))

    def test_unknown_target_is_an_error(self):
        with self.assertRaises(ValueError):
            self.dirs("user", "nope")

    def test_target_list_parsing(self):
        self.assertEqual(env.parse_targets(["common, claude-code", "hermes"]), ["common", "claude-code", "hermes"])
        self.assertEqual(env.parse_targets(None), ["common"])

    def test_options_are_refused_where_they_would_be_ignored(self):
        options = env.LocationOptions(profile="coder")
        with self.assertRaises(ValueError):
            env.resolve_destinations("user", ["common"], self.ws, self.home, options)

    def args(self, **kw):
        base = dict(scope=None, target=None, workspace=self.ws, home=self.home, dest=None, hermes_home=None,
                    profile=None, opencode_config_dir=None)
        return argparse.Namespace(**{**base, **kw})

    def test_dest_takes_the_skills_directory_as_given(self):
        dest = self.root / "空白 あり" / "skills"
        [destination] = env.destinations_from_args(self.args(dest=dest))
        self.assertEqual(destination.skills_dir, dest.resolve())

    def test_dest_and_scope_are_mutually_exclusive_and_one_is_required(self):
        for kw in (dict(dest=self.root, scope="user"), dict()):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                env.destinations_from_args(self.args(**kw))


if __name__ == "__main__":
    unittest.main()
