#!/usr/bin/env python3
"""Agent Skill の構造と互換性を検証する。

    python3 tools/validate_skill.py [SKILL_DIR]

SKILL_DIR の既定は skill/japanese-readability-editor。エラーがあれば終了コード 1。

検証する内容:
  - SKILL.md が存在し、大文字小文字まで正確に SKILL.md である
  - YAML frontmatter が先頭にあり、name と description がある
  - name が japanese-readability-editor で、ディレクトリ名と一致する
  - 製品固有の frontmatter を含まない(既定では name と description だけを許す)
  - SKILL.md が参照する references/ scripts/ assets/ data/ のファイルが存在する
  - Markdown のリンクや参照に、skill の外へ出るパス(../ や絶対パス)がない
  - scripts/ の Python が、通信・外部コマンド・ファイル削除や書き込みをしない
  - ZIP にできる

frontmatter は、どのエージェントの解析器でも読める保守的な YAML の部分集合に限る。
`key: value` の1行形式だけを認め、複数行の値、値の中の ': ' や ' #' は誤りとして報告する。
"""

from __future__ import annotations

import argparse
import ast
import io
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

EXPECTED_NAME = "japanese-readability-editor"
SKILL_FILE = "SKILL.md"

# 共通 SKILL.md の frontmatter に置くことを認めるキー。
ALLOWED_KEYS = {"name", "description"}
# Agent Skills 仕様上は任意だが、この skill では原則として置かないキー。
STANDARD_OPTIONAL_KEYS = {"license", "compatibility", "metadata", "allowed-tools"}
# 製品固有として知られているキー(Claude Code など)。報告時に理由を添える。
PRODUCT_SPECIFIC_KEYS = {
    "when_to_use", "argument-hint", "arguments", "disable-model-invocation", "user-invocable",
    "model", "effort", "context", "agent", "hooks", "paths", "shell", "tools", "version",
}

MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
# Claude のヘルプ記事が claude.ai の登録画面について挙げている上限。仕様の上限とは別に警告する。
CLAUDE_AI_DESCRIPTION_LENGTH = 200
RESERVED_WORDS = ("anthropic", "claude")
RECOMMENDED_MAX_BODY_LINES = 500

IGNORED_NAMES = {"__pycache__", ".DS_Store", "Thumbs.db", ".gitkeep"}
IGNORED_SUFFIXES = (".pyc", ".pyo")

FORBIDDEN_MODULES = {
    "socket", "ssl", "urllib", "http", "ftplib", "smtplib", "imaplib", "poplib", "telnetlib",
    "xmlrpc", "requests", "httpx", "aiohttp", "subprocess", "shutil", "ctypes", "webbrowser", "pty",
}
FORBIDDEN_BUILTINS = {"eval", "exec", "__import__"}
FORBIDDEN_OS_CALLS = {"system", "popen", "remove", "unlink", "rmdir", "removedirs", "rename",
                      "kill", "chmod", "chown", "symlink", "link", "truncate"}
FORBIDDEN_PATH_METHODS = {"write_text", "write_bytes", "unlink", "rmdir", "touch", "mkdir",
                          "symlink_to", "hardlink_to"}

# 日本語の助詞などを巻き込まないよう、パスに使う文字は ASCII に限る。
PATH_MENTION_RE = re.compile(r"(?<![A-Za-z0-9_./-])((?:references|scripts|assets|data)/[A-Za-z0-9_./-]*[A-Za-z0-9_-])")
DRIVE_RE = re.compile(r"^[A-Za-z]:[\\/]")
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


@dataclass
class Report:
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


# --- ファイルの列挙 ---------------------------------------------------------


def iter_skill_files(skill_dir: Path) -> Iterator[Path]:
    """skill に含めるファイルの、skill_dir からの相対パスを辞書順に返す。"""
    skill_dir = Path(skill_dir)
    collected: List[Path] = []
    for current, directories, files in os.walk(skill_dir, followlinks=False):
        directories[:] = sorted(d for d in directories if d not in IGNORED_NAMES)
        for name in files:
            if name in IGNORED_NAMES or name.endswith(IGNORED_SUFFIXES):
                continue
            collected.append((Path(current) / name).relative_to(skill_dir))
    yield from sorted(collected, key=lambda p: p.as_posix())


# --- frontmatter ------------------------------------------------------------

KEY_VALUE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ ]+(.*))?$")
YAML_INDICATORS = "[]{}&*!|>%@`"


def parse_frontmatter(text: str) -> Tuple[Optional[Dict[str, str]], str, List[str]]:
    """(frontmatter の辞書, 本文, エラー) を返す。frontmatter がなければ辞書は None。"""
    errors: List[str] = []
    if text.startswith("﻿"):
        errors.append("SKILL.md starts with a BOM; frontmatter must be at the very start of the file")
        text = text.lstrip("﻿")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0].rstrip() != "---":
        errors.append("YAML frontmatter must start on the first line with '---'")
        return None, text, errors
    closing = next((i for i in range(1, len(lines)) if lines[i].rstrip() == "---"), None)
    if closing is None:
        errors.append("YAML frontmatter is not closed with '---'")
        return None, text, errors

    values: Dict[str, str] = {}
    for offset, raw in enumerate(lines[1:closing], start=2):
        if not raw.strip() or raw.lstrip().startswith("#") and not raw.startswith((" ", "\t")):
            continue
        if raw[0] in " \t":
            errors.append(f"line {offset}: indented or multi-line YAML values are not supported; "
                          "write each value on one line")
            continue
        match = KEY_VALUE_RE.match(raw.rstrip())
        if not match:
            errors.append(f"line {offset}: malformed YAML, expected 'key: value'")
            continue
        key, value = match.group(1), (match.group(2) or "").strip()
        if key in values:
            errors.append(f"line {offset}: duplicate key '{key}'")
            continue
        parsed, problem = parse_scalar(value)
        if problem:
            errors.append(f"line {offset}: {key}: {problem}")
            continue
        values[key] = parsed
    body = "\n".join(lines[closing + 1:])
    return values, body, errors


def parse_scalar(value: str) -> Tuple[str, Optional[str]]:
    """1行の YAML スカラーを解釈する。(値, 問題の説明) を返す。"""
    if not value:
        return "", None
    if value[0] in "\"'":
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            return "", f"unterminated {quote} quote"
        inner = value[1:-1]
        if quote == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        elif "'" in inner.replace("''", ""):
            return "", "unescaped ' inside a single-quoted value"
        else:
            inner = inner.replace("''", "'")
        return inner, None
    if value[0] in YAML_INDICATORS:
        return "", f"value starts with the YAML indicator '{value[0]}'; quote the value"
    if value[0] in "-?:" and (len(value) == 1 or value[1] == " "):
        return "", f"value starts with the YAML indicator '{value[0]} '; quote the value"
    if ": " in value or value.endswith(":"):
        return "", "plain value contains ': ' which YAML parsers reject; quote the value or reword it"
    if " #" in value:
        return "", "plain value contains ' #' which YAML parsers read as a comment; quote the value"
    return value, None


# --- 個別の検査 -------------------------------------------------------------


def check_skill_file(skill_dir: Path, report: Report) -> Optional[str]:
    """SKILL.md の存在と大文字小文字を確認し、内容を返す。"""
    names = os.listdir(skill_dir)
    if SKILL_FILE not in names:
        similar = [n for n in names if n.lower() == SKILL_FILE.lower()]
        if similar:
            report.error(f"found '{similar[0]}' but the file must be named exactly {SKILL_FILE}")
        else:
            report.error(f"{SKILL_FILE} not found in {skill_dir}")
        return None
    try:
        return (skill_dir / SKILL_FILE).read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        report.error(f"{SKILL_FILE} is not valid UTF-8: {exc}")
        return None


def check_frontmatter_fields(fields: Dict[str, str], skill_dir: Path, expected_name: str,
                             allow_standard_optional: bool, report: Report) -> None:
    for key in fields:
        if key in ALLOWED_KEYS:
            continue
        if key in STANDARD_OPTIONAL_KEYS and allow_standard_optional:
            continue
        if key in PRODUCT_SPECIFIC_KEYS:
            report.error(f"frontmatter key '{key}' is product-specific; keep only name and description")
        elif key in STANDARD_OPTIONAL_KEYS:
            report.error(f"frontmatter key '{key}' is optional in the Agent Skills spec but not used here "
                         "(pass --allow-standard-optional to permit it)")
        else:
            report.error(f"unexpected frontmatter key '{key}'; keep only name and description")

    name = fields.get("name")
    if not name:
        report.error("frontmatter 'name' is missing or empty")
    else:
        if name != expected_name:
            report.error(f"name is '{name}' but must be '{expected_name}'")
        if len(name) > MAX_NAME_LENGTH:
            report.error(f"name is {len(name)} chars; the maximum is {MAX_NAME_LENGTH}")
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
            report.error("name may contain only lowercase letters, digits and single hyphens, "
                         "and must not start or end with a hyphen")
        for word in RESERVED_WORDS:
            if word in name:
                report.error(f"name must not contain the reserved word '{word}'")
        if skill_dir.resolve().name != name:
            report.error(f"name '{name}' must match the directory name '{skill_dir.resolve().name}'")

    description = fields.get("description")
    if not description:
        report.error("frontmatter 'description' is missing or empty")
    else:
        if len(description) > MAX_DESCRIPTION_LENGTH:
            report.error(f"description is {len(description)} chars; the maximum is {MAX_DESCRIPTION_LENGTH}")
        elif len(description) > CLAUDE_AI_DESCRIPTION_LENGTH:
            report.warn(f"description is {len(description)} chars; the Claude Help Center documents a "
                        f"{CLAUDE_AI_DESCRIPTION_LENGTH}-char limit for claude.ai uploads "
                        "(the Agent Skills spec allows 1024)")
        if re.search(r"[<>]", description):
            report.error("description must not contain '<' or '>' (XML tags are rejected by some products)")


def strip_fences(text: str) -> str:
    """fenced code block の中身を空行に置き換える(行番号は保つ)。"""
    kept: List[str] = []
    closing: Optional[re.Pattern] = None
    for line in text.split("\n"):
        if closing is not None:
            if closing.match(line):
                closing = None
            kept.append("")
            continue
        fence = FENCE_RE.match(line)
        if fence:
            marker = fence.group(1)
            closing = re.compile(r"^\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
            kept.append("")
            continue
        kept.append(line)
    return "\n".join(kept)


def check_path(target: str, base: Path, skill_dir: Path, label: str, report: Report) -> None:
    """skill 内を指す相対パスとして妥当かを確認する。不正なら報告し、存在しなくても報告する。"""
    target = target.split("#", 1)[0].split("?", 1)[0]
    if not target:
        return
    if not DRIVE_RE.match(target) and SCHEME_RE.match(target):
        return  # http: や mailto: などの外部リンク
    if target.startswith(("/", "~", "\\")) or DRIVE_RE.match(target):
        report.error(f"{label}: unsafe path '{target}' (absolute path)")
        return
    resolved = (base / target).resolve()
    if not resolved.is_relative_to(skill_dir.resolve()):
        report.error(f"{label}: unsafe path '{target}' (resolves outside the skill directory)")
    elif not resolved.exists():
        report.error(f"{label}: referenced file does not exist: {target}")


def check_references(skill_dir: Path, body: str, report: Report) -> None:
    for mention in sorted(set(PATH_MENTION_RE.findall(body))):
        check_path(mention, skill_dir, skill_dir, SKILL_FILE, report)
    for target in LINK_RE.findall(strip_fences(body)):
        check_path(target, skill_dir, skill_dir, SKILL_FILE, report)
    for relative in iter_skill_files(skill_dir):
        path = skill_dir / relative
        if relative.suffix.lower() != ".md" or relative.as_posix() == SKILL_FILE:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            report.error(f"{relative.as_posix()}: cannot read as UTF-8: {exc}")
            continue
        for target in LINK_RE.findall(strip_fences(text)):
            check_path(target, path.parent, skill_dir, relative.as_posix(), report)


def check_symlinks(skill_dir: Path, report: Report) -> None:
    root = skill_dir.resolve()
    for current, directories, files in os.walk(skill_dir, followlinks=False):
        for name in directories + files:
            path = Path(current) / name
            if path.is_symlink() and not path.resolve().is_relative_to(root):
                report.error(f"{path.relative_to(skill_dir).as_posix()}: symlink points outside the skill directory")


def _dotted_name(node: ast.AST) -> Optional[str]:
    parts: List[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def check_script_safety(path: Path, label: str, report: Report) -> None:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=label)
    except (SyntaxError, UnicodeDecodeError, OSError) as exc:
        report.error(f"{label}: cannot parse: {exc}")
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_MODULES:
                    report.error(f"{label}:{node.lineno}: forbidden import '{alias.name}' (no network or external commands)")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] in FORBIDDEN_MODULES:
                report.error(f"{label}:{node.lineno}: forbidden import '{node.module}' (no network or external commands)")
        elif isinstance(node, ast.Call):
            dotted = _dotted_name(node.func)
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_BUILTINS:
                report.error(f"{label}:{node.lineno}: forbidden call '{node.func.id}()'")
            elif dotted and dotted.startswith("os.") and (
                dotted.split(".")[1] in FORBIDDEN_OS_CALLS
                or dotted.split(".")[1].startswith(("exec", "spawn"))
            ):
                report.error(f"{label}:{node.lineno}: forbidden call '{dotted}()'")
            elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_PATH_METHODS:
                report.error(f"{label}:{node.lineno}: forbidden file operation '.{node.func.attr}()' (scripts are read-only)")
            elif isinstance(node.func, ast.Name) and node.func.id == "open" and _opens_for_writing(node):
                report.error(f"{label}:{node.lineno}: open() for writing is forbidden (scripts are read-only)")


def _opens_for_writing(call: ast.Call) -> bool:
    mode: Optional[ast.AST] = call.args[1] if len(call.args) > 1 else None
    for keyword in call.keywords:
        if keyword.arg == "mode":
            mode = keyword.value
    return isinstance(mode, ast.Constant) and isinstance(mode.value, str) and any(c in mode.value for c in "wax+")


def check_scripts(skill_dir: Path, report: Report) -> None:
    scripts = skill_dir / "scripts"
    if not scripts.is_dir():
        return
    for relative in iter_skill_files(skill_dir):
        if relative.parts[0] == "scripts" and relative.suffix == ".py":
            check_script_safety(skill_dir / relative, relative.as_posix(), report)


def check_zip(skill_dir: Path, report: Report) -> None:
    buffer = io.BytesIO()
    try:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for relative in iter_skill_files(skill_dir):
                archive.write(skill_dir / relative, f"{skill_dir.resolve().name}/{relative.as_posix()}")
    except (OSError, ValueError, zipfile.LargeZipFile) as exc:
        report.error(f"cannot build a ZIP from the skill directory: {exc}")


# --- 入口 -------------------------------------------------------------------


def validate_skill(skill_dir: Path, expected_name: str = EXPECTED_NAME,
                   allow_standard_optional: bool = False) -> Report:
    skill_dir = Path(skill_dir)
    report = Report()
    if not skill_dir.is_dir():
        report.error(f"skill directory not found: {skill_dir}")
        return report

    text = check_skill_file(skill_dir, report)
    if text is not None:
        fields, body, problems = parse_frontmatter(text)
        for problem in problems:
            report.error(problem)
        if fields is not None:
            check_frontmatter_fields(fields, skill_dir, expected_name, allow_standard_optional, report)
        if len(body.split("\n")) > RECOMMENDED_MAX_BODY_LINES:
            report.warn(f"{SKILL_FILE} body has more than {RECOMMENDED_MAX_BODY_LINES} lines; "
                        "move detail into references/")
        check_references(skill_dir, body, report)
    check_symlinks(skill_dir, report)
    check_scripts(skill_dir, report)
    check_zip(skill_dir, report)
    return report


def default_skill_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "skill" / EXPECTED_NAME


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Agent Skill の構造と互換性を検証する。")
    parser.add_argument("skill_dir", nargs="?", type=Path, default=None,
                        help="検証する skill のディレクトリ。既定 skill/japanese-readability-editor")
    parser.add_argument("--expected-name", default=EXPECTED_NAME, help=f"期待する name。既定 {EXPECTED_NAME}")
    parser.add_argument("--allow-standard-optional", action="store_true",
                        help="Agent Skills 仕様の任意項目(license, compatibility, metadata, allowed-tools)を許す")
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir or default_skill_dir()
    report = validate_skill(skill_dir, args.expected_name, args.allow_standard_optional)
    for message in report.errors:
        print(f"ERROR: {message}")
    for message in report.warnings:
        print(f"WARN: {message}")
    if report.ok:
        print(f"OK: {skill_dir} ({len(report.warnings)} warning(s))")
        return 0
    print(f"FAILED: {len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
