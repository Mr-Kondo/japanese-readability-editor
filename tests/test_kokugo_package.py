"""国語の表記・用法の追加物が、配布物(ZIP、Gemini Apps 向け、インストール)に正しく入ることのテスト。"""

import json
import unittest
import zipfile
from pathlib import Path

from helpers import SKILL_DIR, SKILL_NAME, TOOLS_DIR, load_module, run_script, temporary_directory

package = load_module("package", TOOLS_DIR / "package.py")
validate = load_module("validate_skill_for_kokugo_package", TOOLS_DIR / "validate_skill.py")

NEW_FILES = [
    "scripts/check_kokugo.py", "scripts/kokugo_engine.py", "scripts/validate_kokugo_rules.py",
    "data/kokugo-rules.json", "data/kokugo-sources.json", "data/joyo-kanji.json", "data/ijidokun.json",
    "references/kokugo-policy.md", "references/kokugo-notation.md", "references/kokugo-official.md", "references/kokugo-sources.md",
    "assets/kokugo-cases.md",
]


class PackageTest(unittest.TestCase):
    def setUp(self):
        self._tmp = temporary_directory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_the_zip_contains_the_new_files(self):
        zip_path = self.tmp / "out.zip"
        package.build_zip(SKILL_DIR, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            for relative in NEW_FILES:
                self.assertIn(f"{SKILL_NAME}/{relative}", names, relative)
            for relative in ("scripts/check_kokugo.py", "scripts/validate_kokugo_rules.py"):
                self.assertEqual(archive.getinfo(f"{SKILL_NAME}/{relative}").external_attr >> 16 & 0o777, 0o755)
            self.assertEqual(archive.getinfo(f"{SKILL_NAME}/data/kokugo-rules.json").external_attr >> 16 & 0o777, 0o644)

    def test_the_extracted_skill_checks_a_document_offline(self):
        zip_path = self.tmp / "out.zip"
        package.build_zip(SKILL_DIR, zip_path)
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(self.tmp / "x")
        installed = self.tmp / "x" / SKILL_NAME
        doc = self.tmp / "doc.md"
        doc.write_text("こんにちわ。\n", encoding="utf-8")
        code, out, _ = run_script(installed / "scripts" / "check_kokugo.py", str(doc), "--json")
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["files"][0]["findings"][0]["rule_id"], "KOKUGO-KANA-001")
        code, out, _ = run_script(installed / "scripts" / "validate_kokugo_rules.py")
        self.assertEqual(code, 0, out)

    def test_the_gemini_folder_leaves_out_scripts_and_data_but_keeps_the_documents(self):
        copied = package.export_gemini_apps_folder(SKILL_DIR, self.tmp / "gemini-apps")
        self.assertFalse([c for c in copied if c.startswith(("scripts/", "data/"))])
        for relative in ("references/kokugo-policy.md", "references/kokugo-notation.md", "references/kokugo-sources.md", "assets/kokugo-cases.md"):
            self.assertIn(relative, copied)

    def test_data_holds_only_json_files(self):
        names = {p.as_posix() for p in validate.iter_skill_files(SKILL_DIR)}
        self.assertFalse([n for n in names if n.startswith("data/") and not n.endswith(".json")])


if __name__ == "__main__":
    unittest.main()
