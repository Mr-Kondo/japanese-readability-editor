"""Claude Code プラグインの定義ファイル(.claude-plugin/)の整合性テスト。

`claude plugin validate` の代わりではない。CLI がない環境でも、壊れていないことだけを確かめる。
"""

import json
import unittest

from helpers import REPO_ROOT, SKILL_DIR, SKILL_NAME

PLUGIN_DIR = REPO_ROOT / ".claude-plugin"


def load(name: str) -> dict:
    return json.loads((PLUGIN_DIR / name).read_text(encoding="utf-8"))


class PluginManifestTest(unittest.TestCase):
    def test_files_are_valid_json(self):
        for name in ("plugin.json", "marketplace.json"):
            with self.subTest(name=name):
                self.assertIsInstance(load(name), dict)

    def test_plugin_name_is_the_skill_name(self):
        self.assertEqual(load("plugin.json")["name"], SKILL_NAME)

    def test_skills_path_points_at_the_canonical_skill(self):
        paths = load("plugin.json")["skills"]
        self.assertEqual(paths, ["./skill/"])
        for path in paths:
            self.assertTrue(path.startswith("./"), "component paths must start with ./")
            self.assertTrue((REPO_ROOT / path / SKILL_NAME / "SKILL.md").is_file())

    def test_the_manifest_does_not_copy_the_skill(self):
        # 正本は skill/ の1か所だけ。プラグイン用に SKILL.md を複製していない。
        ignored = {".git", "dist", ".agents", ".claude"}  # 生成物と、install.py でこの repo に配置したコピー
        found = [p for p in REPO_ROOT.rglob("SKILL.md") if not ignored & set(p.relative_to(REPO_ROOT).parts)]
        self.assertEqual([p.resolve() for p in found], [(SKILL_DIR / "SKILL.md").resolve()])

    def test_marketplace_lists_the_plugin_from_the_repository_root(self):
        marketplace = load("marketplace.json")
        entries = marketplace["plugins"]
        self.assertEqual([e["name"] for e in entries], [SKILL_NAME])
        self.assertEqual(entries[0]["source"], "./")
        self.assertTrue(marketplace["owner"]["name"])

    def test_version_is_left_unset_so_that_updates_follow_commits(self):
        self.assertNotIn("version", load("plugin.json"))
        self.assertNotIn("version", load("marketplace.json")["plugins"][0])


if __name__ == "__main__":
    unittest.main()
