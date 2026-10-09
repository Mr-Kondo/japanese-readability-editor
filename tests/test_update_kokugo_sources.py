"""tools/update_kokugo_sources.py のテスト。ネットワークは使わない(取得は差し替える)。

日常の検査(scripts/check_kokugo.py)がネットワークを使わないこと、規則を更新するときだけこのツールが通信することを分けて確かめる。
"""

import contextlib
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from helpers import TOOLS_DIR, load_module, temporary_directory

update = load_module("update_kokugo_sources", TOOLS_DIR / "update_kokugo_sources.py")


def quiet_main(argv):
    """コマンドの終了コードだけを返し、標準出力と標準エラーは捨てる(テストの出力を静かにする)。"""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return update.main(argv)

JOYO_PAGE = (
    "本　表\nア－イ\n漢　字\t音　訓\t例\t備　考\n"
    "亜\t（亞）\t\t\t\t\tア\t亜流，亜麻\n"
    "哀\t\t\t\t\t\tアイ\t哀愁，哀願\n"
    "\t\t\tあわれ\t哀れ\n"
    "\t\t\tあわれむ\t哀れむ\n"
    "仮\t（假）\t\t\t\t\tカ\t仮面\n"
    "\t\t\t　ケ\t仮病\n"
    "\t\t\tかり\t仮の住まい\n"
    "03初_改定常用漢字表_本表NN.indd   11 2010/11/12   13:10:18\n"
)
IJIDOKUN_PAGE = (
    "本 表\n"
    "あう ００１\n【会う】主に人と人が顔を合わせる。\n客と会う時刻。\n【合う】一致する。\n【遭う】思わぬことに出くわす。\n"
    "あからむ ００２\n【赤らむ】赤くなる。\n【明らむ】明るくなる。\n"
    "ある ００３\n【有る*】備わる。\n【在る*】存在する。\n"
    "余計な見出し ０１５\n"
)


class ParsingTest(unittest.TestCase):
    def test_joyo_rows_become_characters_with_their_readings(self):
        chars, readings = update.parse_joyo_pages([(11, JOYO_PAGE)])
        self.assertEqual(chars, ["亜", "哀", "仮"])
        self.assertEqual(readings, {"亜": ["ア"], "哀": ["アイ", "あわれ", "あわれむ"], "仮": ["カ", "ケ", "かり"]})

    def test_pages_without_the_table_marker_are_ignored(self):
        chars, _ = update.parse_joyo_pages([(3, "亜\tア\n"), (11, JOYO_PAGE)])
        self.assertEqual(chars, ["亜", "哀", "仮"])

    def test_a_repeated_character_is_an_error(self):
        with self.assertRaises(update.ExtractionError):
            update.parse_joyo_pages([(11, JOYO_PAGE), (12, JOYO_PAGE)])

    def test_ijidokun_entries_keep_their_numbers_and_forms(self):
        entries = update.parse_ijidokun_pages([(8, IJIDOKUN_PAGE)])
        self.assertEqual([e["id"] for e in entries], [1, 2, 3])
        self.assertEqual(entries[0]["reading"], "あう")
        self.assertEqual([v["forms"] for v in entries[0]["variants"]], [["会う"], ["合う"], ["遭う"]])
        self.assertEqual(entries[0]["variants"][0]["gloss"], "主に人と人が顔を合わせる。")
        self.assertEqual([v["forms"] for v in entries[2]["variants"]], [["有る"], ["在る"]])  # 注記の印(*)は取り除く
        self.assertEqual(entries[0]["page"], 8)

    def test_an_out_of_sequence_heading_is_not_an_entry(self):
        entries = update.parse_ijidokun_pages([(8, IJIDOKUN_PAGE)])
        self.assertNotIn("余計な見出し", [e["reading"] for e in entries])

    def test_extraction_refuses_unexpected_counts(self):
        source = {"retrieved_files": [{"url": "x"}]}
        with self.assertRaises(update.ExtractionError):
            update.build_joyo_text([(11, JOYO_PAGE)], b"", source)
        with self.assertRaises(update.ExtractionError):
            update.build_ijidokun_text([(8, IJIDOKUN_PAGE)], b"", source)

    def test_rendered_files_are_valid_json_and_carry_the_source_hash(self):
        chars, readings = update.parse_joyo_pages([(11, JOYO_PAGE)])
        source = {"retrieved_files": [{"url": "https://www.bunka.go.jp/x.pdf"}]}
        text = update.render_joyo(chars, readings, source, b"pdf-bytes")
        data = json.loads(text)
        self.assertEqual(data["chars"], "亜哀仮")
        self.assertEqual(data["derived_from"]["sha256"], hashlib.sha256(b"pdf-bytes").hexdigest())
        self.assertEqual(data["readings"]["哀"], ["アイ", "あわれ", "あわれむ"])
        entries = update.parse_ijidokun_pages([(8, IJIDOKUN_PAGE)])
        data = json.loads(update.render_ijidokun(entries, source, b"pdf-bytes"))
        self.assertEqual(data["count"], 3)
        self.assertEqual(data["entries"][0]["variants"][1]["forms"], ["合う"])


class VerificationTest(unittest.TestCase):
    BODY_A, BODY_B = b"a" * 10, b"b" * 20

    def registry(self):
        return {"sources": [
            {"id": "S-1", "retrieved_files": [{"url": "https://www.bunka.go.jp/a", "sha256": hashlib.sha256(self.BODY_A).hexdigest(), "size": 10}]},
            {"id": "S-2", "retrieved_files": [{"url": "https://www.bunka.go.jp/b", "sha256": hashlib.sha256(self.BODY_B).hexdigest(), "size": 20}]},
        ]}

    def test_matching_files_pass(self):
        bodies = {"https://www.bunka.go.jp/a": self.BODY_A, "https://www.bunka.go.jp/b": self.BODY_B}
        results = update.verify_sources(self.registry(), lambda url: (200, bodies[url]))
        self.assertEqual([r["ok"] for r in results], [True, True])

    def test_a_changed_file_is_reported(self):
        bodies = {"https://www.bunka.go.jp/a": self.BODY_A, "https://www.bunka.go.jp/b": b"changed"}
        results = update.verify_sources(self.registry(), lambda url: (200, bodies[url]))
        self.assertEqual([r["ok"] for r in results], [True, False])
        self.assertIn("changed", results[1]["note"])

    def test_http_errors_and_exceptions_are_failures_not_crashes(self):
        def fetch(url):
            if url.endswith("/a"):
                return 404, b"missing"
            raise OSError("network down")

        results = update.verify_sources(self.registry(), fetch)
        self.assertEqual([r["ok"] for r in results], [False, False])
        self.assertIn("HTTP 404", results[0]["note"])
        self.assertIn("network down", results[1]["note"])

    def test_the_verify_command_returns_the_exit_code(self):
        with temporary_directory() as tmp:
            path = Path(tmp) / "sources.json"
            path.write_text(json.dumps(self.registry()), encoding="utf-8")
            bodies = {"https://www.bunka.go.jp/a": self.BODY_A, "https://www.bunka.go.jp/b": self.BODY_B}
            with mock.patch.object(update, "fetch_bytes", lambda url, timeout=60.0: (200, bodies[url])):
                self.assertEqual(quiet_main(["--sources", str(path), "verify"]), 0)
            with mock.patch.object(update, "fetch_bytes", lambda url, timeout=60.0: (200, b"changed")):
                self.assertEqual(quiet_main(["--sources", str(path), "verify"]), 1)


class ExtractionCommandTest(unittest.TestCase):
    def test_extraction_without_pypdf_explains_how_to_install_it_in_a_venv(self):
        with temporary_directory() as tmp:
            pdf = Path(tmp) / "x.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            with mock.patch.dict(sys.modules, {"pypdf": None}):
                with self.assertRaises(update.ExtractionError) as caught:
                    update.extract_pdf_pages(pdf)
            self.assertIn("virtual environment", str(caught.exception))
            self.assertIn("not the system Python", str(caught.exception))

    def test_the_command_returns_2_on_an_extraction_error(self):
        with temporary_directory() as tmp:
            pdf = Path(tmp) / "x.pdf"
            pdf.write_bytes(b"%PDF-1.4")
            with mock.patch.dict(sys.modules, {"pypdf": None}):
                self.assertEqual(quiet_main(["extract-joyo", str(pdf), "--out", str(Path(tmp) / "out.json")]), 2)
            self.assertFalse((Path(tmp) / "out.json").exists(), "失敗したときは、データを書き出さない")

    def test_a_missing_registry_is_an_error(self):
        self.assertEqual(quiet_main(["--sources", "/nonexistent/sources.json", "verify"]), 2)


class RegistryTest(unittest.TestCase):
    def test_the_recorded_registry_is_loadable_and_has_the_files_the_tool_needs(self):
        registry = update.load_registry()
        joyo = update.find_source(registry, update.JOYO_SOURCE_ID)
        self.assertEqual(joyo["retrieved_files"][0]["format"], "pdf")
        iji = update.find_source(registry, update.IJIDOKUN_SOURCE_ID)
        self.assertEqual(iji["retrieved_files"][0]["format"], "pdf")
        with self.assertRaises(update.ExtractionError):
            update.find_source(registry, "NOPE")

    def test_the_tool_is_outside_the_skill_so_it_is_not_distributed(self):
        skill = TOOLS_DIR.parent / "skill" / "japanese-readability-editor"
        self.assertFalse([p for p in skill.rglob("update_kokugo_sources.py")])


if __name__ == "__main__":
    unittest.main()
