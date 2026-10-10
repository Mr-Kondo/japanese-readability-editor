#!/usr/bin/env python3
"""配置した Skill を検証する(何も変更せず、何もインストールしない)。

    python3 tools/verify_install.py "/path/to/skills/japanese-readability-editor" --target hermes
    python3 tools/verify_install.py --scope user --target opencode
    python3 tools/verify_install.py --scope user --target hermes --profile coder
    python3 tools/verify_install.py --dest "/path with spaces/skills" --no-run

配置先の決め方は install.py と同じ(--scope、--target、--workspace、--home、--dest、--hermes-home、--profile、
--opencode-config-dir)。位置引数で Skill のディレクトリを直接渡すこともできる。

検証する内容:
  - 構造: SKILL.md の名前、frontmatter、ディレクトリ名、SKILL.md が参照するファイル、scripts/ の安全性(validate_skill.py)
  - メタデータ: 対象の環境(opencode、hermes)の公式仕様の制約(名前の形式と長さ、description の長さ、ディレクトリ名との一致)
  - 内容: 正本(--source。既定はこのリポジトリの skill/)との差(欠けたファイル、余分なファイル、内容の違い)
  - 実行: カレントディレクトリが Skill でもリポジトリでもない、空白と日本語を含む一時ディレクトリから、同梱のスクリプトを
          すべて実行する(--no-run で省く)。実行する Python は、この検証を動かしている Python である
  - 依存: Python 3.10 以上か。SudachiPy は任意。入っていなくても動き、どちらで動いたかを tokenizer で示す。インストールはしない
  - 重複: 同じ Skill が、その製品の別の探索先でも見つかるか(--scope か --dest を指定したときだけ)。何も削除しない

終了コード: 0=問題なし(警告はありうる)、1=誤りがある、2=引数が不正。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skill_env  # noqa: E402
from install import (ENVIRONMENT_TARGETS, add_location_arguments, destination_target,  # noqa: E402
                     destinations_from_args, location_host)
from validate_skill import (MAX_DESCRIPTION_LENGTH, MAX_NAME_LENGTH, SKILL_FILE, default_skill_dir,  # noqa: E402
                            parse_frontmatter, validate_skill)

MIN_PYTHON = (3, 10)
SCRIPT_TIMEOUT_SECONDS = 60
REQUIRED_SCRIPTS = ("measure.py", "verify_preservation.py", "compare_rewrite.py", "check_kokugo.py", "validate_kokugo_rules.py")


@dataclass(frozen=True)
class NameRule:
    """対象の環境が Skill の名前に課す制約と、その根拠。"""

    pattern: "re.Pattern[str]"
    basis: str


# OpenCode は文書にある制約。Hermes は、探索側の制約が文書になく、Agent が作る Skill に課す制約(skill_manager_tool.py)を使う。
NAME_RULES = {
    "opencode": NameRule(re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$"), "OpenCode docs"),
    "hermes": NameRule(re.compile(r"^[a-z0-9][a-z0-9._-]*$"), "the limits Hermes applies to skills it creates; discovery itself documents none"),
}

SAMPLE_BEFORE = (
    "# 確認用\n\n"
    "このシステムは、ユーザーから入力されたデータを受け取り、それを検証したうえで、問題がなければ100件までデータベースに保存し、"
    "問題があればエラーとして呼び出し元に返す。\n"
)
SAMPLE_AFTER = (
    "# 確認用\n\n"
    "このシステムは、ユーザーから入力されたデータを受け取り、それを検証したうえで、\n"
    "問題がなければ100件までデータベースに保存し、\n"
    "問題があればエラーとして呼び出し元に返す。\n"
)


@dataclass
class Finding:
    level: str  # ok, info, warn, error
    code: str
    message: str


@dataclass
class VerifyReport:
    path: Path
    findings: List[Finding] = field(default_factory=list)
    tokenizer: Optional[str] = None
    drift: Optional[skill_env.TreeDiff] = None

    def add(self, level: str, code: str, message: str) -> None:
        self.findings.append(Finding(level, code, message))

    def require_source_match(self) -> None:
        """正本との差を、警告から誤りに引き上げる(配置の直後や、配布物の生成のように、差があってはならないとき)。"""
        for finding in self.findings:
            if finding.code == "source" and finding.level == "warn":
                finding.level = "error"

    def add_duplicates(self, copies: List[skill_env.Copy], target: Optional[str]) -> None:
        for copy in copies:
            self.add("warn", "duplicate", skill_env.describe_copy(copy, target or ""))

    @property
    def errors(self) -> List[Finding]:
        return [f for f in self.findings if f.level == "error"]

    @property
    def warnings(self) -> List[Finding]:
        return [f for f in self.findings if f.level == "warn"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_json(self) -> dict:
        return {
            "path": str(self.path),
            "ok": self.ok,
            "tokenizer": self.tokenizer,
            "findings": [{"level": f.level, "code": f.code, "message": f.message} for f in self.findings],
        }


# --- 個別の検査 -------------------------------------------------------------


def metadata_problems(path: Path, rule: NameRule) -> Optional[List[str]]:
    """対象の環境の仕様が求めるメタデータの制約(名前の形式と長さ、description の長さ、ディレクトリ名との一致)の違反。
    frontmatter を読めないときは None(構造の検査が報告する)。"""
    try:
        fields, _, _ = parse_frontmatter((path / SKILL_FILE).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None
    if not fields:
        return None
    name, description = fields.get("name", ""), fields.get("description", "")
    problems: List[str] = []
    if not rule.pattern.match(name) or len(name) > MAX_NAME_LENGTH:
        problems.append(f"name '{name}' must match {rule.pattern.pattern} and be at most {MAX_NAME_LENGTH} characters ({rule.basis})")
    if path.resolve().name != name:
        problems.append(f"name '{name}' must equal the directory name '{path.resolve().name}' (this Skill requires it)")
    if not description or len(description) > MAX_DESCRIPTION_LENGTH:
        problems.append(f"description must be 1-{MAX_DESCRIPTION_LENGTH} characters (now {len(description)})")
    return problems


def check_target_metadata(path: Path, target: Optional[str], report: VerifyReport) -> None:
    rule = NAME_RULES.get(target or "")
    problems = metadata_problems(path, rule) if rule else None
    if problems is None:
        return
    for problem in problems:
        report.add("error", f"{target}-metadata", problem)
    if not problems:
        report.add("ok", f"{target}-metadata", f"{target}: name, description and directory name meet the limits ({rule.basis})")


def _script_environment() -> dict:
    return dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")


def _run_script(report: VerifyReport, scripts: Path, work: Path, label: str, args: List[str],
                accepted: Tuple[int, ...] = (0,)) -> Optional[subprocess.CompletedProcess]:
    """scripts/<args[0]> を work から実行する。許す終了コード以外や実行できないときは、誤りを報告して None。"""
    command = [sys.executable, str(scripts / args[0]), *args[1:]]
    try:
        done = subprocess.run(command, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env=_script_environment(), timeout=SCRIPT_TIMEOUT_SECONDS)
    except (OSError, subprocess.TimeoutExpired) as exc:
        report.add("error", "script-run", f"{label}: could not run: {exc}")
        return None
    if done.returncode not in accepted:
        tail = (done.stderr or done.stdout).strip().splitlines()[-3:]
        report.add("error", "script-run", f"{label}: exit {done.returncode} (expected {'/'.join(map(str, accepted))}): "
                                          + " | ".join(tail))
        return None
    report.add("ok", "script-run", f"{label}: exit {done.returncode}, run from {work.parent.name}/{work.name}")
    return done


def _json_field(report: VerifyReport, done: Optional[subprocess.CompletedProcess], script: str, field_name: str) -> Optional[str]:
    """done の標準出力を JSON として読み、field_name の値を返す。読めなければ誤りを報告して None。"""
    if done is None:
        return None
    try:
        return str(json.loads(done.stdout)[field_name])
    except (ValueError, KeyError, TypeError):
        report.add("error", "script-output", f"{script} did not print JSON with a '{field_name}' field")
        return None


def execute_scripts(path: Path, report: VerifyReport) -> None:
    """同梱のスクリプトを、Skill でもリポジトリでもない、空白と日本語を含むディレクトリから実行する。"""
    scripts = path / "scripts"
    missing = [name for name in REQUIRED_SCRIPTS if not (scripts / name).is_file()]
    if missing:
        report.add("error", "scripts-missing", "scripts/ is missing: " + ", ".join(missing))
        return

    with tempfile.TemporaryDirectory(prefix="jre verify ") as raw:
        work = Path(raw) / "確認 用"
        work.mkdir()
        for name, text in (("before.md", SAMPLE_BEFORE), ("after.md", SAMPLE_AFTER), ("sample.md", SAMPLE_BEFORE)):
            (work / name).write_text(text, encoding="utf-8")

        def run(label: str, args: List[str], accepted: Tuple[int, ...] = (0,)):
            return _run_script(report, scripts, work, label, args, accepted)

        run("measure.py --locate", ["measure.py", "--locate", "sample.md"])
        run("verify_preservation.py", ["verify_preservation.py", "before.md", "after.md"])
        run("verify_preservation.py --strict", ["verify_preservation.py", "--strict", "before.md", "after.md"])
        compared = run("compare_rewrite.py --json", ["compare_rewrite.py", "--json", "before.md", "after.md"])
        report.tokenizer = _json_field(report, compared, "compare_rewrite.py --json", "tokenizer")
        checked = run("check_kokugo.py --json", ["check_kokugo.py", "sample.md", "--profile", "general-tech", "--json"], (0, 1))
        _json_field(report, checked, "check_kokugo.py --json", "schema_version")
        run("validate_kokugo_rules.py", ["validate_kokugo_rules.py"])


def report_dependencies(report: VerifyReport) -> None:
    if sys.version_info < MIN_PYTHON:
        report.add("error", "python-version", f"Python {'.'.join(map(str, MIN_PYTHON))} or later is required; "
                                              f"this is {sys.version.split()[0]}")
    else:
        report.add("ok", "python-version", f"Python {sys.version.split()[0]} ({sys.executable}) meets the minimum "
                                           f"{'.'.join(map(str, MIN_PYTHON))}")
    if report.tokenizer is None:
        return
    if report.tokenizer.startswith("sudachi"):
        report.add("info", "sudachipy", f"SudachiPy is available: compare_rewrite.py used tokenizer '{report.tokenizer}'")
    else:
        report.add("info", "sudachipy", f"SudachiPy is not installed: compare_rewrite.py used tokenizer '{report.tokenizer}' "
                                        "(standard library only). Optional. This tool never installs it; to add it, use an "
                                        "isolated environment: python3 -m venv DIR && DIR/bin/pip install sudachipy sudachidict-small, "
                                        "and run the agent's scripts with that Python")


def verify_installation(path: Path, *, target: Optional[str] = None, source: Optional[Path] = None,
                        run_scripts: bool = True) -> VerifyReport:
    """path の Skill を検証する。target は opencode か hermes。source を渡すと、内容を正本と比べる。

    正本との差は警告にする。差を誤りとして扱うときは、report.require_source_match() を呼ぶ。
    run_scripts は --no-run に対応し、同梱のスクリプトを実行するかどうかを選ぶ。
    """
    path = Path(path).absolute()  # 作業ディレクトリを移してスクリプトを実行するので、相対パスのままにしない(リンクは解決しない)
    report = VerifyReport(path)
    if not path.is_dir():
        report.add("error", "missing", f"{path} is not a directory")
        return report
    check_symlink(path, target, report)

    structure = validate_skill(path)
    for message in structure.errors:
        report.add("error", "structure", message)
    for message in structure.warnings:
        report.add("warn", "structure", message)
    if structure.ok:
        report.add("ok", "structure", f"{SKILL_FILE}, name, description, referenced files and script safety are valid")
    check_target_metadata(path, target, report)
    if source is not None:
        check_against_source(path, source, report)

    if run_scripts and structure.ok:
        execute_scripts(path, report)
    elif run_scripts:
        report.add("info", "script-run", "scripts were not run because the structure check failed")
    report_dependencies(report)
    return report


def check_symlink(path: Path, target: Optional[str], report: VerifyReport) -> None:
    if not path.is_symlink():
        return
    report.add("info", "symlink", f"{path} is a symlink to {path.resolve()}")
    if target == "hermes":
        report.add("warn", "symlink-remote", "Hermes does not copy symlinked skills into Docker, SSH, Modal or Daytona "
                                             "sandboxes (it skips symlinks); use a copy when the terminal backend is not local")


def check_against_source(path: Path, source: Path, report: VerifyReport) -> None:
    diff = skill_env.diff_trees(source, path)
    report.drift = diff
    if diff.identical:
        report.add("ok", "source", f"identical to the source {source} ({len(skill_env.file_digests(path))} files)")
    else:
        report.add("warn", "source", f"differs from the source {source}: {diff.summary()} "
                                     "(an older version? update with install.py --on-conflict backup)")


# --- CLI --------------------------------------------------------------------


def print_report(report: VerifyReport) -> None:
    print(f"verify   {report.path}")
    for finding in report.findings:
        print(f"  {finding.level:<5}  [{finding.code}] {finding.message}")
    print(f"result: {'OK' if report.ok else 'FAILED'} ({len(report.errors)} error(s), {len(report.warnings)} warning(s))")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="配置した Skill を検証する(何も変更せず、何もインストールしない)。",
                                     epilog=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", type=Path, default=None,
                        help="検証する Skill のディレクトリ(japanese-readability-editor/)。--scope か --dest を使うときは省く")
    add_location_arguments(parser)
    parser.add_argument("--source", type=Path, default=None, help="比べる正本。既定はこのリポジトリの skill/japanese-readability-editor(あれば)")
    parser.add_argument("--no-source", action="store_true", help="正本との比較を省く(リポジトリがない環境で、配置済みの Skill だけを検証する)")
    parser.add_argument("--strict-source", action="store_true", help="正本との差を、警告ではなく誤りとして扱う")
    parser.add_argument("--no-run", action="store_true", help="スクリプトを実行しない(構造・メタデータ・内容・重複だけを検証する)")
    parser.add_argument("--json", action="store_true", help="結果を JSON で出力する")
    return parser


@dataclass
class Job:
    path: Path
    target: Optional[str]
    duplicates: List[skill_env.Copy] = field(default_factory=list)


def resolve_source(args: argparse.Namespace) -> Optional[Path]:
    """比べる正本。--source の指定が誤りなら ValueError。既定の正本がなければ None(リポジトリのない環境)。"""
    if args.no_source:
        if args.source is not None:
            raise ValueError("--no-source and --source cannot be combined")
        return None
    source = (args.source or default_skill_dir()).resolve()
    if source.is_dir():
        return source
    if args.source is not None:
        raise ValueError(f"--source {source} is not a directory")
    return None


def collect_jobs(args: argparse.Namespace, source: Optional[Path]) -> List[Job]:
    """検証する Skill のディレクトリを決める。位置引数なら1つ、--scope か --dest なら install.py と同じ配置先。"""
    if args.path is not None:
        if args.scope is not None or args.dest is not None:
            raise ValueError("pass either a path or --scope/--dest, not both")
        targets = [name for value in (args.target or []) for name in value.split(",")]
        return [Job(args.path, next((t for t in targets if t in ENVIRONMENT_TARGETS), None))]
    host = location_host(args)
    jobs: List[Job] = []
    for destination in destinations_from_args(args):
        target = destination_target(destination)
        copies: List[skill_env.Copy] = []
        if target:
            roots = skill_env.duplicate_roots(target, args.scope or "user", host, destination.skills_dir)
            copies = skill_env.find_other_copies(roots, destination=destination.path, source=source)
        jobs.append(Job(destination.path, target, copies))
    return jobs


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = resolve_source(args)
        jobs = collect_jobs(args, source)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    reports = []
    for job in jobs:
        report = verify_installation(job.path, target=job.target, source=source, run_scripts=not args.no_run)
        report.add_duplicates(job.duplicates, job.target)
        if args.strict_source:
            report.require_source_match()
        reports.append(report)
    if args.json:
        print(json.dumps([r.to_json() for r in reports], ensure_ascii=False, indent=2))
    else:
        for report in reports:
            print_report(report)
    return 0 if all(r.ok for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
