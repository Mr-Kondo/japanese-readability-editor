#!/usr/bin/env python3
"""規則データの検証、Skill の検証、テストを、まとめて実行する。

    python3 tools/check_all.py [--skip-tests] [--verbose]

実行する内容(上から順に。1つでも失敗すれば、終了コードは 1)。
  1. tools/validate_skill.py                    Skill の構造と互換性
  2. scripts/validate_kokugo_rules.py           国語表記の規則データ(出典、必須項目、例の再検査)
  3. tools/render_kokugo_docs.py --check        規則データから生成する2つの文書が、最新であること
  4. python3 -m unittest discover -s tests      単体テスト、CLI の統合テスト、既存の回帰テスト

ネットワークは使わない。公式資料の更新を確かめる tools/update_kokugo_sources.py verify は、通信するので含めない。
CI(.github/workflows/ci.yml)は、同じ内容を段階に分けて実行する。

終了コード: 0=すべて成功, 1=失敗あり。テストの件数(実行、失敗、エラー、スキップ)を最後に表示する。
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO_ROOT / "skill" / "japanese-readability-editor"
RAN_RE = re.compile(r"^Ran (\d+) tests? in ([0-9.]+)s", re.M)
RESULT_RE = re.compile(r"^(OK|FAILED)(?: \((.*)\))?$", re.M)


def run(command: List[str]) -> Tuple[int, str, float]:
    started = time.monotonic()
    completed = subprocess.run(command, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace",
                               env=_env())
    return completed.returncode, completed.stdout + completed.stderr, time.monotonic() - started


def _env() -> dict:
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")


def summarize_tests(output: str) -> str:
    ran = RAN_RE.search(output)
    result = RESULT_RE.search(output)
    if not ran or not result:
        return "no test summary found"
    counts = {"failures": 0, "errors": 0, "skipped": 0}
    for part in (result.group(2) or "").split(", "):
        if "=" in part:
            key, value = part.split("=", 1)
            counts[key] = int(value)
    passed = int(ran.group(1)) - counts["failures"] - counts["errors"] - counts["skipped"]
    return (f"{ran.group(1)} run, {passed} passed, {counts['failures']} failed, {counts['errors']} errors, "
            f"{counts['skipped']} skipped ({ran.group(2)}s)")


def steps(args: argparse.Namespace) -> List[Tuple[str, List[str], bool]]:
    python = sys.executable
    plan = [
        ("validate the skill", [python, str(REPO_ROOT / "tools" / "validate_skill.py")] + ([str(args.skill_dir)] if args.skill_dir else []), False),
        ("validate the kokugo rules", [python, str(SKILL_DIR / "scripts" / "validate_kokugo_rules.py")]
         + (["--data-dir", str(args.data_dir)] if args.data_dir else []), False),
    ]
    plan.append(("check the generated kokugo documents", [python, str(REPO_ROOT / "tools" / "render_kokugo_docs.py"), "--check"], False))
    if not args.skip_tests:
        plan.append(("run the tests", [python, "-m", "unittest", "discover", "-s", "tests"], True))
    return plan


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="規則データの検証、Skill の検証、テストをまとめて実行する(ネットワークなし)。")
    parser.add_argument("--skip-tests", action="store_true", help="テストを実行しない(検証だけ)")
    parser.add_argument("--verbose", action="store_true", help="各段階の出力をすべて表示する")
    parser.add_argument("--skill-dir", type=Path, default=None, help="検証する Skill のディレクトリ(既定は skill/japanese-readability-editor)")
    parser.add_argument("--data-dir", type=Path, default=None, help="検証する規則データのディレクトリ(既定は Skill の data/)")
    args = parser.parse_args(argv)

    failed = False
    for name, command, is_tests in steps(args):
        code, output, seconds = run(command)
        status = "ok" if code == 0 else "FAILED"
        detail = summarize_tests(output) if is_tests else (output.strip().splitlines() or [""])[-1]
        print(f"[{status}] {name}: exit {code}, {detail}")
        if code != 0 or args.verbose:
            print(output.rstrip())
        failed = failed or code != 0
    print("all checks passed" if not failed else "some checks FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
