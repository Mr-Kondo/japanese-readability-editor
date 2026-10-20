"""skill_info.py(版と実行環境の出力)と、VERSION の整合のテスト。"""

import json
import re
import unittest
from pathlib import Path

from helpers import REPO_ROOT, SCRIPTS_DIR, SKILL_DIR, load_module, run_script, temporary_directory

info = load_module("skill_info", SCRIPTS_DIR / "skill_info.py")


class DetectAppTest(unittest.TestCase):
    def test_ai_agent_gives_name_and_version(self):
        self.assertEqual(info.detect_app({"AI_AGENT": "claude-code_2-1-299_agent"}),
                         {"name": "claude-code", "version": "2.1.299", "source": "AI_AGENT"})

    def test_marker_variable_gives_name_only(self):
        self.assertEqual(info.detect_app({"GEMINI_CLI": "1"})["name"], "gemini-cli")

    def test_apps_own_markers_beat_an_inherited_ai_agent(self):
        inherited = {"AI_AGENT": "claude-code_2-1-299_agent", "CLAUDECODE": "1"}  # 子プロセスは親の環境を引き継ぐ
        self.assertEqual(info.detect_app({**inherited, "CODEX_THREAD_ID": "t", "CODEX_VERSION": "0.155.1"}),
                         {"name": "codex", "version": "0.155.1", "source": "CODEX_THREAD_ID"})
        self.assertEqual(info.detect_app({**inherited, "OPENCODE": "1"})["name"], "opencode")
        self.assertEqual(info.detect_app({**inherited, "HERMES_AGENT": "true"})["name"], "hermes")
        self.assertEqual(info.detect_app({"CODEX_THREAD_ID": "t"})["version"], "unknown")

    def test_unknown_when_nothing_matches(self):
        self.assertEqual(info.detect_app({"AI_AGENT": "weird"})["name"], "unknown")

    def test_argument_overrides_detection(self):
        record = info.build_record({"AI_AGENT": "claude-code_2-1-299_agent"}, app="codex", app_version="0.5")
        self.assertEqual(record["app"], {"name": "codex", "version": "0.5", "source": "argument"})


class RecordTest(unittest.TestCase):
    def test_record_has_the_required_fields_and_no_personal_data(self):
        record = info.build_record({}, model=" claude-sonnet-5-5 ")
        self.assertEqual(record["model"], "claude-sonnet-5-5")
        self.assertEqual(set(record), {"schema_version", "kind", "skill", "skill_version", "os", "app", "model", "python",
                                       "date", "recorded_at"})
        self.assertEqual(info.build_record({})["model"], "unknown")
        self.assertRegex(record["recorded_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

    def test_prints_json_and_the_save_location_but_writes_nothing(self):
        with temporary_directory() as name:
            home = Path(name)
            code, out, err = run_script(SCRIPTS_DIR / "skill_info.py", "--model", "m1", env={"HOME": str(home), "USERPROFILE": str(home)})
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["model"], "m1")
            self.assertEqual(err.strip(), f"save_to: {home / '.agents' / 'skill-env' / (SKILL_DIR.name + '.json')}")
            self.assertEqual(list(home.iterdir()), [])  # スクリプトは書き込まない(保存は実行した側)

    def test_version_flag_prints_one_line(self):
        code, out, _ = run_script(SCRIPTS_DIR / "skill_info.py", "--version")
        self.assertEqual((code, out.strip()), (0, f"{SKILL_DIR.name} {info.read_version()}"))


class VersionFileTest(unittest.TestCase):
    def test_version_is_semver_and_has_release_notes(self):
        version = (SKILL_DIR / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")
        self.assertTrue((REPO_ROOT / "docs" / "release-notes" / f"v{version}.md").is_file(), "版を上げる PR には、リリースノートを入れる")


if __name__ == "__main__":
    unittest.main()
