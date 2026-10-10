"""C の文字保持と新規素材の配布を検証する。モデル挙動の証拠ではない。"""
import json
import re
import unittest
import zipfile
from pathlib import Path
from helpers import FIXTURES, SCRIPTS_DIR, SKILL_DIR, SKILL_NAME, TOOLS_DIR, load_module, run_script, temporary_directory

verify = load_module("verify_fiction_c", SCRIPTS_DIR / "verify_preservation.py")
package = load_module("package_fiction", TOOLS_DIR / "package.py")
MATERIALS = ("references/fiction-writing.md", "references/fiction-checks.md", "assets/fiction-examples.md", "assets/fiction-context-template.md", "scripts/check_fiction.py")


def newline_gaps(raw):
    # バイト列の改行トークンを保持する。CRLF を LF に正規化しない。
    parts = re.split(rb"(\r\n|\r|\n)", raw)
    chars, gaps = bytearray(), [[]]
    for part in parts:
        if part in (b"\r\n", b"\r", b"\n"):
            gaps[-1].append(part)
        else:
            for ch in part:
                chars.append(ch)
                gaps.append([])
    return bytes(chars), gaps


def raw_insertion_only(before, after):
    left, old_gaps = newline_gaps(before)
    right, new_gaps = newline_gaps(after)
    if left != right:
        return False
    for old, new in zip(old_gaps, new_gaps):
        at = 0
        for token in new:
            if at < len(old) and old[at] == token:
                at += 1
        if at != len(old):
            return False
    return True


class FictionCRegressionTest(unittest.TestCase):
    def setUp(self):
        self.cases = json.loads((FIXTURES / "fiction-mode-c.json").read_text(encoding="utf-8"))["cases"]

    def test_owned_fixtures_allow_only_newline_insertions(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertEqual(raw_insertion_only(case["before"].encode(), case["after"].encode()), case["allowed"])

    def test_strict_cli_and_input_immutability(self):
        with temporary_directory() as tmp:
            before, after = Path(tmp) / "before.md", Path(tmp) / "after.md"
            for case in self.cases:
                with self.subTest(case=case["id"]):
                    before.write_bytes(case["before"].encode())
                    after.write_bytes(case["after"].encode())
                    snapshot = before.read_bytes(), after.read_bytes()
                    code, out, err = run_script(SCRIPTS_DIR / "verify_preservation.py", "--strict", "--json", str(before), str(after))
                    # 現行検証器の保証範囲は変更しない。改行コード/BOM は追加比較で検出する。
                    expected = case["allowed"] or case["id"] in ("crlf_replaced", "bom_deleted")
                    self.assertEqual(code, 0 if expected else 1, err)
                    self.assertEqual(json.loads(out)["strict"]["only_newlines_inserted"], expected)
                    self.assertEqual((before.read_bytes(), after.read_bytes()), snapshot)

    def test_default_whitespace_comparison_is_insufficient(self):
        for case in self.cases:
            if case["id"] in ("ascii_space_removed", "fullwidth_space_removed", "space_width_changed", "existing_newline_deleted", "newline_moved", "crlf_replaced", "tab_changed"):
                with self.subTest(case=case["id"]):
                    self.assertTrue(verify.compare(case["before"], case["after"])["identical"])
                    self.assertFalse(raw_insertion_only(case["before"].encode(), case["after"].encode()))


class FictionDistributionTest(unittest.TestCase):
    def test_zip_contains_all_materials_and_checker_runs_after_extraction(self):
        with temporary_directory() as tmp:
            root = Path(tmp)
            archive_path = root / "skill.zip"
            package.build_zip(SKILL_DIR, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                for relative in MATERIALS:
                    self.assertEqual(archive.read(f"{SKILL_NAME}/{relative}"), (SKILL_DIR / relative).read_bytes())
                archive.extractall(root / "extract")
            checker = root / "extract" / SKILL_NAME / "scripts" / "check_fiction.py"
            code, out, err = run_script(checker, "-", "--json", stdin="「夜が肺に溜まる」\n")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["status"], "no_candidates")

    def test_gemini_folder_keeps_prose_materials_and_omits_runtime_scripts(self):
        with temporary_directory() as tmp:
            copied = package.export_gemini_apps_folder(SKILL_DIR, Path(tmp) / "gemini")
            for relative in MATERIALS[:-1]:
                self.assertIn(relative, copied)
            self.assertNotIn(MATERIALS[-1], copied)

    def test_gemini_paste_instructions_embed_fiction_contract(self):
        text = package.render_gemini_apps_instructions(SKILL_DIR)
        fiction = (SKILL_DIR / "references" / "fiction-writing.md").read_text(encoding="utf-8").strip("\n")
        self.assertIn(package.demote_headings(package.strip_relative_links(fiction), 2), text)
        self.assertNotIn("](fiction-", text)
        self.assertNotIn("](../assets/", text)
