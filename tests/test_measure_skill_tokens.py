"""tools/measure_skill_tokens.py の解析部分のテスト。`claude` は呼ばず、合成したトランスクリプトを読ませる。"""

import json
import unittest

from helpers import TOOLS_DIR, load_module

measure = load_module("measure_skill_tokens", TOOLS_DIR / "measure_skill_tokens.py")

USAGE = {"input_tokens": 2, "cache_creation_input_tokens": 10, "cache_read_input_tokens": 100, "output_tokens": 5}


def assistant(message_id: str, block: dict) -> dict:
    return {"type": "assistant", "message": {"id": message_id, "content": [block], "usage": USAGE}}


def tool_use(use_id: str, name: str, **args) -> dict:
    return {"type": "tool_use", "id": use_id, "name": name, "input": args}


def tool_result(use_id: str, text: str) -> dict:
    return {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": use_id, "content": text}]}}


def transcript(*events) -> list:
    return [json.dumps(e) for e in events]


class ParseTranscriptTest(unittest.TestCase):
    def test_blocks_of_one_message_are_merged_and_scripts_are_counted(self):
        lines = transcript(
            assistant("m1", tool_use("a", "Skill", skill="japanese-readability-editor")),
            assistant("m1", tool_use("b", "Bash", command="python3 /x/scripts/compare_rewrite.py before.md after.md")),
            tool_result("b", "x" * 40),
            {"type": "result", "usage": USAGE, "total_cost_usd": 0.1, "num_turns": 2, "modelUsage": {"m": {}}})
        record = measure.parse_transcript(lines)
        self.assertEqual(record["tools"], ["Skill", "Bash"])
        self.assertTrue(record["skill_called"])
        self.assertEqual(record["scripts_run"], [{"script": "compare_rewrite.py", "output_chars": 40}])
        self.assertEqual(record["source_reads"], [])
        self.assertEqual(record["input_side_tokens"], 112)

    def test_reading_a_script_source_is_not_counted_as_running_it(self):
        lines = transcript(
            assistant("m1", tool_use("a", "Read", file_path="/x/scripts/check_kokugo.py")),
            assistant("m2", tool_use("b", "Bash", command="cat scripts/measure.py | head -50")),
            assistant("m3", tool_use("c", "Read", file_path="/x/references/scripts.md")),
            {"type": "result", "usage": USAGE})
        record = measure.parse_transcript(lines)
        self.assertEqual(len(record["source_reads"]), 2)
        self.assertEqual(record["scripts_run"], [])
        self.assertEqual(record["references_read"], ["scripts.md"])


class PreservationTest(unittest.TestCase):
    def test_only_inserted_newlines_pass_strict(self):
        self.assertTrue(measure.preservation("a b\nc", "a b\n\nc")["strict_same"])
        self.assertFalse(measure.preservation("a b\nc", "a  b\nc")["strict_same"])
        self.assertTrue(measure.preservation("a b\nc", "a  b\nc")["nonspace_same"])
        self.assertFalse(measure.preservation("ab\n\nc", "ab\nc")["strict_same"])


if __name__ == "__main__":
    unittest.main()
