#!/usr/bin/env python3
"""共通 Skill を、各エージェントが読む場所へ配置する。

    python3 tools/install.py --scope workspace --target common
    python3 tools/install.py --scope workspace --target all --dry-run
    python3 tools/install.py --scope user --target claude-code

配置先の一覧(公式資料で確認した探索先):

  workspace                      .agents/skills/  Codex, GitHub Copilot, Gemini CLI, Antigravity (IDE, CLI)
                                 .claude/skills/  Claude Code
  user                           ~/.agents/skills/                  Codex, GitHub Copilot, Gemini CLI
                                 ~/.claude/skills/                  Claude Code
                                 ~/.gemini/config/skills/           Antigravity IDE
                                 ~/.gemini/antigravity-cli/skills/  Antigravity CLI

target:
  common           .agents/skills(共通配置)。codex, copilot, gemini-cli と同じ場所
  codex            workspace と user の共通配置。$CODEX_HOME/skills は現行仕様で非推奨のため使わない
  copilot          workspace と user の共通配置
  gemini-cli       workspace と user の共通配置
  claude-code      .claude/skills
  antigravity-ide  user は ~/.gemini/config/skills。workspace は共通配置
  antigravity-cli  user は ~/.gemini/antigravity-cli/skills。workspace は共通配置
  antigravity      antigravity-ide と antigravity-cli の両方
  all              上のすべて(同じ場所は1回だけ配置する)

既存のファイルは無断で上書きしない。--on-conflict で skip(既定)、backup、overwrite を選ぶ。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_skill import EXPECTED_NAME, SKILL_FILE, default_skill_dir, iter_skill_files, validate_skill  # noqa: E402

COMMON = ".agents/skills"

WORKSPACE_DIRS: Dict[str, str] = {
    "common": COMMON,
    "codex": COMMON,
    "copilot": COMMON,
    "gemini-cli": COMMON,
    "antigravity-ide": COMMON,
    "antigravity-cli": COMMON,
    "claude-code": ".claude/skills",
}
USER_DIRS: Dict[str, str] = {
    "common": ".agents/skills",
    "codex": ".agents/skills",
    "copilot": ".agents/skills",
    "gemini-cli": ".agents/skills",
    "claude-code": ".claude/skills",
    "antigravity-ide": ".gemini/config/skills",
    "antigravity-cli": ".gemini/antigravity-cli/skills",
}
EXPANSIONS: Dict[str, Dict[str, List[str]]] = {
    "workspace": {
        "antigravity": ["antigravity-ide", "antigravity-cli"],
        "all": ["common", "claude-code"],
    },
    "user": {
        "antigravity": ["antigravity-ide", "antigravity-cli"],
        "all": ["common", "claude-code", "antigravity-ide", "antigravity-cli"],
    },
}
TARGET_CHOICES = sorted(set(WORKSPACE_DIRS) | {"antigravity", "all"})


@dataclass
class Destination:
    skills_dir: Path
    targets: List[str]

    @property
    def path(self) -> Path:
        return self.skills_dir / EXPECTED_NAME


@dataclass
class Outcome:
    destination: Path
    status: str  # installed, skipped, dry-run, error
    message: str


def parse_targets(values: Optional[List[str]]) -> List[str]:
    targets: List[str] = []
    for value in values or ["common"]:
        for item in value.split(","):
            item = item.strip()
            if item:
                targets.append(item)
    return targets


def resolve_destinations(scope: str, targets: List[str], workspace: Path, home: Path) -> List[Destination]:
    """target を配置先のディレクトリへ解決する。同じ場所は1つにまとめる。"""
    table = WORKSPACE_DIRS if scope == "workspace" else USER_DIRS
    base = workspace if scope == "workspace" else home
    expanded: List[str] = []
    for target in targets:
        if target not in TARGET_CHOICES:
            raise ValueError(f"unknown target '{target}'; choose from {', '.join(TARGET_CHOICES)}")
        expanded.extend(EXPANSIONS[scope].get(target, [target]))

    destinations: Dict[Path, Destination] = {}
    for target in expanded:
        skills_dir = base / table[target]
        entry = destinations.setdefault(skills_dir, Destination(skills_dir, []))
        if target not in entry.targets:
            entry.targets.append(target)
    return list(destinations.values())


def is_safe_to_remove(path: Path) -> bool:
    """overwrite で消してよいのは、シンボリックリンクか、SKILL.md を持つディレクトリだけ。"""
    return path.is_symlink() or (path.is_dir() and (path / SKILL_FILE).is_file())


def copy_skill(source: Path, destination: Path) -> None:
    """一時ディレクトリに複製してから配置先へ移す。途中で失敗しても、中途半端なものを残さない。"""
    staging = destination.parent / f".{destination.name}.installing-{os.getpid()}"
    try:
        for relative in iter_skill_files(source):
            target = staging / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / relative, target)
        os.replace(staging, destination)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def install_one(source: Path, destination: Destination, *, link: bool, on_conflict: str, dry_run: bool,
                now: Callable[[], datetime] = datetime.now) -> Outcome:
    target = destination.path
    prefix = "[dry-run] " if dry_run else ""
    mode = "link" if link else "copy"
    exists = target.exists() or target.is_symlink()
    backup: Optional[Path] = None

    if exists:
        same_as_source = target.resolve() == source.resolve()
        if same_as_source and not target.is_symlink():
            return Outcome(target, "skipped", f"{prefix}skip     {target} is the source directory itself")
        if same_as_source and (link or on_conflict == "skip"):
            return Outcome(target, "skipped", f"{prefix}skip     {target} (already points at the source)")
        if on_conflict == "skip":
            return Outcome(target, "skipped",
                           f"{prefix}skip     {target} exists (use --on-conflict backup or overwrite)")
        if on_conflict == "overwrite" and not is_safe_to_remove(target):
            return Outcome(target, "error",
                           f"refuse   {target} exists but is not a skill directory; remove it yourself")
        if on_conflict == "backup":
            stamp = now().strftime("%Y%m%d-%H%M%S")
            backup = destination.skills_dir.parent / f"{destination.skills_dir.name}.bak" / f"{EXPECTED_NAME}-{stamp}"

    if dry_run:
        detail = f"{mode} -> {target}"
        if backup:
            detail += f" (existing moves to {backup})"
        elif exists:
            detail += " (existing is removed: --on-conflict overwrite)"
        return Outcome(target, "dry-run", f"{prefix}install  {detail}  [{', '.join(destination.targets)}]")

    try:
        destination.skills_dir.mkdir(parents=True, exist_ok=True)
        if exists:
            if backup:
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(backup))
            elif target.is_symlink() or target.is_file():
                target.unlink()
            else:
                shutil.rmtree(target)
        if link:
            os.symlink(source.resolve(), target, target_is_directory=True)
        else:
            copy_skill(source, target)
    except OSError as exc:
        hint = " (symlinks may need extra privileges on Windows; retry without --link)" if link else ""
        return Outcome(target, "error", f"error    {target}: {exc}{hint}")

    detail = f"{mode} -> {target}"
    if backup:
        detail += f" (previous copy saved to {backup})"
    return Outcome(target, "installed", f"install  {detail}  [{', '.join(destination.targets)}]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="共通 Skill を、各エージェントが読む場所へ配置する。",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--scope", required=True, choices=("workspace", "user"),
                        help="workspace はプロジェクト内、user はホームディレクトリ内に配置する")
    parser.add_argument("--target", action="append", metavar="TARGET",
                        help=f"配置先の環境。繰り返し指定、またはカンマ区切りで複数指定できる。既定 common。選択肢: {', '.join(TARGET_CHOICES)}")
    parser.add_argument("--dry-run", action="store_true", help="何も書かずに、実行する内容だけを表示する")
    parser.add_argument("--link", action="store_true",
                        help="複製ではなくシンボリックリンクを作る(正本の更新がすぐ反映される。Windows では権限が要る場合がある)")
    parser.add_argument("--on-conflict", choices=("skip", "backup", "overwrite"), default="skip",
                        help="配置先に既にある場合の動作。skip=何もしない(既定), backup=退避してから配置, overwrite=削除して配置")
    parser.add_argument("--source", type=Path, default=None, help="skill のディレクトリ。既定 skill/japanese-readability-editor")
    parser.add_argument("--workspace", type=Path, default=None, help="--scope workspace の基準ディレクトリ。既定はカレントディレクトリ")
    parser.add_argument("--home", type=Path, default=None, help="--scope user の基準ディレクトリ。既定はホームディレクトリ")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    source = (args.source or default_skill_dir()).resolve()

    report = validate_skill(source)
    if not report.ok:
        for message in report.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print("FAILED: the source skill is invalid; nothing was installed", file=sys.stderr)
        return 1

    workspace = (args.workspace or Path.cwd()).resolve()
    home = (args.home or Path.home()).resolve()
    try:
        destinations = resolve_destinations(args.scope, parse_targets(args.target), workspace, home)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    outcomes = [
        install_one(source, destination, link=args.link, on_conflict=args.on_conflict, dry_run=args.dry_run)
        for destination in destinations
    ]
    for outcome in outcomes:
        print(outcome.message, file=sys.stderr if outcome.status == "error" else sys.stdout)

    counts = {status: sum(1 for o in outcomes if o.status == status)
              for status in ("installed", "dry-run", "skipped", "error")}
    print("summary: " + ", ".join(f"{n} {status}" for status, n in counts.items() if n))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
