#!/usr/bin/env python3
"""install.py で配置した Skill を、配置先から削除する。

    python3 tools/uninstall.py --scope user --target all --dry-run
    python3 tools/uninstall.py --scope workspace --target common
    python3 tools/uninstall.py --scope user --target claude-code --include-backups

配置先の決め方は install.py と同じ(--scope、--target、--workspace、--home)。

削除するのは、各配置先の japanese-readability-editor/ だけ。
  - --link で入れたものは、リンクだけを削除する。リンク先の正本は残る。
  - SKILL.md を持たないディレクトリと、このリポジトリの正本そのものは、削除を断る。
  - 配置先がなければ、何もしない。
  - skills/ ディレクトリは、ほかの Skill が入っていることがあるので、空になっても残す。

--on-conflict backup が退避した skills.bak/ は、既定では残す。--include-backups を付けると、
japanese-readability-editor-<日時>/ を削除し、skills.bak/ が空になれば、それも削除する。

Claude Code のプラグインは `claude plugin uninstall`、ChatGPT Work、Claude Cowork、Gemini Apps は
各製品の画面から削除する。このスクリプトでは削除できない。
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from install import (Destination, Outcome, add_location_arguments, backup_root, is_safe_to_remove,  # noqa: E402
                     parse_targets, resolve_destinations)
from validate_skill import EXPECTED_NAME, default_skill_dir  # noqa: E402

BACKUP_NAME = re.compile(rf"^{re.escape(EXPECTED_NAME)}-\d{{8}}-\d{{6}}$")


def refusal(path: Path, source: Path) -> Optional[str]:
    """削除を断る理由を返す。削除してよければ None。"""
    if not path.is_symlink() and path.resolve() == source.resolve():
        return f"refuse   {path} is the source directory itself"
    if not is_safe_to_remove(path):
        return f"refuse   {path} is not a skill directory; remove it yourself"
    return None


def remove_entry(path: Path, source: Path, *, dry_run: bool, suffix: str = "") -> Outcome:
    reason = refusal(path, source)
    if reason:
        return Outcome(path, "error", reason)
    prefix = "[dry-run] " if dry_run else ""
    is_link = path.is_symlink()
    detail = " (symlink only; what it points at is kept)" if is_link else ""
    if dry_run:
        return Outcome(path, "dry-run", f"{prefix}remove   {path}{detail}{suffix}")
    try:
        if is_link:
            path.unlink()
        else:
            shutil.rmtree(path)
    except OSError as exc:
        return Outcome(path, "error", f"error    {path}: {exc}")
    return Outcome(path, "removed", f"remove   {path}{detail}{suffix}")


def find_backups(skills_dir: Path) -> List[Path]:
    root = backup_root(skills_dir)
    if not root.is_dir():
        return []
    return sorted(entry for entry in root.iterdir() if BACKUP_NAME.match(entry.name))


def remove_backups(skills_dir: Path, source: Path, *, include_backups: bool, dry_run: bool) -> List[Outcome]:
    backups = find_backups(skills_dir)
    if not backups:
        return []
    root = backup_root(skills_dir)
    if not include_backups:
        message = f"note     {len(backups)} backup(s) remain in {root} (use --include-backups to remove them)"
        return [Outcome(root, "note", message)]
    outcomes = [remove_entry(backup, source, dry_run=dry_run, suffix="  (backup)") for backup in backups]
    if not dry_run and not any(root.iterdir()):
        root.rmdir()
    return outcomes


def uninstall_one(destination: Destination, source: Path, *, include_backups: bool, dry_run: bool) -> List[Outcome]:
    target = destination.path
    if target.exists() or target.is_symlink():
        suffix = f"  [{', '.join(destination.targets)}]"
        outcomes = [remove_entry(target, source, dry_run=dry_run, suffix=suffix)]
    else:
        prefix = "[dry-run] " if dry_run else ""
        outcomes = [Outcome(target, "skipped", f"{prefix}skip     {target} does not exist")]
    outcomes.extend(remove_backups(destination.skills_dir, source, include_backups=include_backups, dry_run=dry_run))
    return outcomes


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="install.py で配置した Skill を、配置先から削除する。",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_location_arguments(parser)
    parser.add_argument("--dry-run", action="store_true", help="何も削除せずに、実行する内容だけを表示する")
    parser.add_argument("--include-backups", action="store_true",
                        help="--on-conflict backup が退避した skills.bak/ の中の Skill も削除する")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = (args.workspace or Path.cwd()).resolve()
    home = (args.home or Path.home()).resolve()
    try:
        destinations = resolve_destinations(args.scope, parse_targets(args.target), workspace, home)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    source = default_skill_dir().resolve()
    outcomes = [
        outcome
        for destination in destinations
        for outcome in uninstall_one(destination, source, include_backups=args.include_backups, dry_run=args.dry_run)
    ]
    for outcome in outcomes:
        print(outcome.message, file=sys.stderr if outcome.status == "error" else sys.stdout)

    counts = {status: sum(1 for o in outcomes if o.status == status)
              for status in ("removed", "dry-run", "skipped", "error")}
    print("summary: " + ", ".join(f"{n} {status}" for status, n in counts.items() if n))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
