"""tools/render_kokugo_docs.py のテスト: 生成する2つの文書が、規則データと一致していること。"""

import copy
import json
import unittest

from helpers import SKILL_DIR, TOOLS_DIR, load_module, run_script

render = load_module("render_kokugo_docs", TOOLS_DIR / "render_kokugo_docs.py")
SCRIPT = TOOLS_DIR / "render_kokugo_docs.py"


class RenderedDocumentsTest(unittest.TestCase):
    def test_the_committed_documents_are_up_to_date(self):
        code, out, err = run_script(SCRIPT, "--check")
        self.assertEqual((code, err), (0, ""), out)
        self.assertIn("up to date", out)

    def test_rendering_is_deterministic(self):
        self.assertEqual(render.render_all(), render.render_all())

    def test_the_files_equal_the_rendering_byte_for_byte(self):
        for path, text in render.render_all().items():
            self.assertEqual(path.read_text(encoding="utf-8"), text, path.name)

    def test_changing_the_data_makes_the_document_stale(self):
        registry = json.loads(render.SOURCES_JSON.read_text(encoding="utf-8"))
        changed = copy.deepcopy(registry)
        changed["sources"][0]["issued_on"] = "1999-01-01"
        self.assertNotEqual(render.render_sources_md(changed), render.SOURCES_MD.read_text(encoding="utf-8"))
        rules = json.loads(render.RULES_JSON.read_text(encoding="utf-8"))["rules"]
        changed_rules = copy.deepcopy(rules)
        changed_rules[0]["profiles"]["official"]["category"] = "accepted_variant"
        self.assertNotEqual(render.render_notation_md(changed_rules), render.NOTATION_MD.read_text(encoding="utf-8"))

    def test_the_documents_mark_themselves_as_generated(self):
        notation = (SKILL_DIR / "references" / "kokugo-notation.md").read_text(encoding="utf-8")
        self.assertIn("規則データから生成した", notation)

    def test_no_note_in_the_data_is_just_a_back_reference(self):
        """CLI の出力にそのまま出る説明が『同上』だけにならない(前の設定の説明を指しても、出力では何を指すか分からない)。"""
        rules = json.loads(render.RULES_JSON.read_text(encoding="utf-8"))["rules"]
        for rule in rules:
            for profile, mapping in rule.get("profiles", {}).items():
                self.assertNotIn("同上", mapping["note"], (rule["id"], profile))


if __name__ == "__main__":
    unittest.main()
