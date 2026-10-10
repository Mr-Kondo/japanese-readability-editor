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
  opencode         workspace は .opencode/skills。user は OPENCODE_CONFIG_DIR、$XDG_CONFIG_HOME/opencode、
                   ~/.config/opencode のうち、実際に使われるもの(skills/ の下)。all には含めない
  hermes           workspace は .hermes/skills(使うには hermes skills trust が要る)。user は実際の Hermes ホーム
                   (HERMES_HOME、プロファイル、~/.hermes)の skills/。all には含めない
  all              上のすべて(同じ場所は1回だけ配置する)。opencode と hermes は含まない

OpenCode は .agents/skills と .claude/skills も読み、Hermes は trust 済みのプロジェクトの .agents/skills も読む。
そのため common や claude-code で入れた Skill は、OpenCode と Hermes からも見える。同名の Skill が複数の場所で
見つかるときは、警告として示す(何も削除しない)。

配置先の明示指定: --dest DIR(skills ディレクトリを直接指定)、--hermes-home PATH、--profile NAME、--opencode-config-dir PATH。
--home を指定したときは、HERMES_HOME などの環境変数を使わない(別のホームを丸ごと指定したものとして扱う)。

既存のファイルは無断で上書きしない。内容が同じなら何もしない。違うときは、--on-conflict で
skip(既定)、backup(退避してから配置)、overwrite(削除して配置)を選ぶ。
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import skill_env  # noqa: E402
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
    "opencode": ".opencode/skills",
    "hermes": ".hermes/skills",
}
USER_DIRS: Dict[str, str] = {
    "common": ".agents/skills",
    "codex": ".agents/skills",
    "copilot": ".agents/skills",
    "gemini-cli": ".agents/skills",
    "claude-code": ".claude/skills",
    "antigravity-ide": ".gemini/config/skills",
    "antigravity-cli": ".gemini/antigravity-cli/skills",
    "opencode": ".config/opencode/skills",  # 実際の場所は skill_env.resolve_opencode が決める
    "hermes": ".hermes/skills",             # 実際の場所は skill_env.resolve_hermes が決める
}
ENVIRONMENT_TARGETS = ("opencode", "hermes")  # 配置先が環境変数・プロファイルで変わる target
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
    origin: str = ""  # 配置先をどう決めたか(例 "$HERMES_HOME")。環境で変わる target のときだけ入る
    notes: List[str] = field(default_factory=list)

    @property
    def path(self) -> Path:
        return self.skills_dir / EXPECTED_NAME


@dataclass
class Outcome:
    destination: Path
    status: str  # installed, unchanged, removed, skipped, dry-run, error, note
    message: str


@dataclass
class LocationOptions:
    """配置先の解決に使う、環境変数と明示指定。env が None なら、環境変数がないものとして扱う。"""

    env: Optional[Mapping[str, str]] = None
    hermes_home: Optional[Path] = None
    profile: Optional[str] = None
    opencode_config_dir: Optional[Path] = None
    platform: Optional[str] = None

    def requested(self) -> List[str]:
        names = {"hermes_home": "--hermes-home", "profile": "--profile", "opencode_config_dir": "--opencode-config-dir"}
        return [flag for attr, flag in names.items() if getattr(self, attr) is not None]


def parse_targets(values: Optional[List[str]]) -> List[str]:
    targets: List[str] = []
    for value in values or ["common"]:
        for item in value.split(","):
            item = item.strip()
            if item:
                targets.append(item)
    return targets


def _check_options(scope: str, expanded: List[str], options: LocationOptions) -> None:
    """明示指定が、対象外の target や scope で黙って無視されないようにする。"""
    if options.hermes_home is not None and options.profile is not None:
        raise ValueError("--hermes-home and --profile cannot be combined")
    for flag, attr, target in (("--hermes-home", "hermes_home", "hermes"), ("--profile", "profile", "hermes"),
                               ("--opencode-config-dir", "opencode_config_dir", "opencode")):
        if getattr(options, attr) is None:
            continue
        if target not in expanded:
            raise ValueError(f"{flag} applies to --target {target}, which is not selected")
        if scope != "user":
            raise ValueError(f"{flag} applies to --scope user; the workspace location is fixed inside the project")


def _expand_targets(scope: str, targets: List[str]) -> List[str]:
    expanded: List[str] = []
    for target in targets:
        if target not in TARGET_CHOICES:
            raise ValueError(f"unknown target '{target}'; choose from {', '.join(TARGET_CHOICES)}")
        expanded.extend(EXPANSIONS[scope].get(target, [target]))
    return expanded


def _resolve_target(target: str, scope: str, host: skill_env.Host, options: LocationOptions) -> skill_env.Resolution:
    """target の skills ディレクトリと、その決め方。OpenCode と Hermes は環境で変わり、ほかは表から引く。"""
    if target == "opencode":
        return skill_env.resolve_opencode(scope, host, options.opencode_config_dir)
    if target == "hermes":
        return skill_env.resolve_hermes(scope, host, options.hermes_home, options.profile)
    table = WORKSPACE_DIRS if scope == "workspace" else USER_DIRS
    base = host.workspace if scope == "workspace" else host.home
    return skill_env.Resolution(base / table[target], "")


def resolve_destinations(scope: str, targets: List[str], workspace: Path, home: Path,
                         options: Optional[LocationOptions] = None) -> List[Destination]:
    """target を配置先のディレクトリへ解決する。同じ場所は1つにまとめる。"""
    options = options or LocationOptions()
    host = skill_env.Host(workspace, home, options.env or {}, options.platform or sys.platform)
    expanded = _expand_targets(scope, targets)
    _check_options(scope, expanded, options)

    destinations: Dict[Path, Destination] = {}
    for target in expanded:
        resolution = _resolve_target(target, scope, host, options)
        entry = destinations.setdefault(
            resolution.skills_dir, Destination(resolution.skills_dir, [], resolution.origin, list(resolution.notes)))
        if target not in entry.targets:
            entry.targets.append(target)
    return list(destinations.values())


def backup_root(skills_dir: Path) -> Path:
    """--on-conflict backup の退避先。Skill の探索先(skills/)の外に置く。"""
    return skills_dir.parent / f"{skills_dir.name}.bak"


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


def _existing_outcome(source: Path, destination: Destination, *, link: bool, on_conflict: str,
                      prefix: str) -> Optional[Outcome]:
    """配置先に既にあるものを、そのまま残す(または拒否する)理由があれば、その結果を返す。置き直してよければ None。"""
    target = destination.path
    same_as_source = target.resolve() == source.resolve()
    if same_as_source and not target.is_symlink():
        return Outcome(target, "skipped", f"{prefix}skip     {target} is the source directory itself")
    if same_as_source and (link or on_conflict == "skip"):
        return Outcome(target, "skipped", f"{prefix}skip     {target} (already points at the source)")
    diff = skill_env.diff_trees(source, target) if target.is_dir() and not target.is_symlink() else None
    if diff is not None and diff.identical and not link:
        return Outcome(target, "unchanged", f"{prefix}skip     {target} is already up to date (identical to the source)")
    differs = f" and differs from the source ({diff.summary()})" if diff is not None and not diff.identical else ""
    if on_conflict == "skip":
        return Outcome(target, "skipped",
                       f"{prefix}skip     {target} exists{differs}; kept as is "
                       "(use --on-conflict backup to replace it and keep the old copy, or overwrite)")
    if on_conflict == "overwrite" and not is_safe_to_remove(target):
        return Outcome(target, "error", f"refuse   {target} exists but is not a skill directory; remove it yourself")
    return None


def _move_aside_or_remove(target: Path, backup: Optional[Path]) -> None:
    if backup:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))
    elif target.is_symlink() or target.is_file():
        target.unlink()
    else:
        shutil.rmtree(target)


def _planned_replacement(exists: bool, backup: Optional[Path]) -> str:
    if backup:
        return f" (existing moves to {backup})"
    return " (existing is removed: --on-conflict overwrite)" if exists else ""


def _backup_destination(destination: Destination, now: Callable[[], datetime]) -> Path:
    return backup_root(destination.skills_dir) / f"{EXPECTED_NAME}-{now().strftime('%Y%m%d-%H%M%S')}"


def install_one(source: Path, destination: Destination, *, link: bool, on_conflict: str, dry_run: bool,
                now: Callable[[], datetime] = datetime.now) -> Outcome:
    target = destination.path
    prefix = "[dry-run] " if dry_run else ""
    mode = "link" if link else "copy"
    exists = target.exists() or target.is_symlink()
    backup: Optional[Path] = None

    if exists:
        settled = _existing_outcome(source, destination, link=link, on_conflict=on_conflict, prefix=prefix)
        if settled:
            return settled
        if on_conflict == "backup":
            backup = _backup_destination(destination, now)

    if dry_run:
        detail = f"{mode} -> {target}" + _planned_replacement(exists, backup)
        return Outcome(target, "dry-run", f"{prefix}install  {detail}  [{', '.join(destination.targets)}]")

    try:
        destination.skills_dir.mkdir(parents=True, exist_ok=True)
        if exists:
            _move_aside_or_remove(target, backup)
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


# --- 配置先の指定(install.py と uninstall.py と verify_install.py で共有する) -------------------------


def add_location_arguments(parser: argparse.ArgumentParser) -> None:
    """配置先を決める引数。uninstall.py と verify_install.py と共有する。"""
    parser.add_argument("--scope", choices=("workspace", "user"), default=None,
                        help="対象にする配置先。workspace はプロジェクト内、user はホームディレクトリ内。--dest を使わないときは必須")
    parser.add_argument("--target", action="append", metavar="TARGET",
                        help=f"配置先の環境。繰り返し指定、またはカンマ区切りで複数指定できる。既定 common。選択肢: {', '.join(TARGET_CHOICES)}")
    parser.add_argument("--workspace", type=Path, default=None, help="--scope workspace の基準ディレクトリ。既定はカレントディレクトリ")
    parser.add_argument("--home", type=Path, default=None,
                        help="--scope user の基準ディレクトリ。既定はホームディレクトリ。指定すると HERMES_HOME などの環境変数は使わない")
    parser.add_argument("--dest", type=Path, default=None, metavar="DIR",
                        help="skills ディレクトリを直接指定する(DIR/japanese-readability-editor/ に配置する)。--scope の代わりに使う。"
                             "--target は、opencode か hermes のときだけ、検証と重複の確認の基準になる")
    parser.add_argument("--hermes-home", type=Path, default=None, metavar="PATH",
                        help="--target hermes --scope user の Hermes ホーム(PATH/skills/ に配置する)。HERMES_HOME とプロファイルより優先する")
    parser.add_argument("--profile", default=None, metavar="NAME",
                        help="--target hermes --scope user のプロファイル名(<根>/profiles/NAME/skills/ に配置する。default は根)")
    parser.add_argument("--opencode-config-dir", type=Path, default=None, metavar="PATH",
                        help="--target opencode --scope user の設定ディレクトリ(PATH/skills/ に配置する)。OPENCODE_CONFIG_DIR より優先する")


def location_host(args: argparse.Namespace) -> skill_env.Host:
    """作業ディレクトリ、ホーム、環境変数。--home を指定したときは、環境変数を使わない。"""
    workspace = (args.workspace or Path.cwd()).resolve()
    home = (args.home or Path.home()).resolve()
    return skill_env.Host(workspace, home, {} if args.home else dict(os.environ))


def options_from_args(args: argparse.Namespace, host: skill_env.Host) -> LocationOptions:
    return LocationOptions(
        env=host.env,
        hermes_home=args.hermes_home.expanduser().resolve() if args.hermes_home else None,
        profile=args.profile,
        opencode_config_dir=args.opencode_config_dir.expanduser().resolve() if args.opencode_config_dir else None,
    )


def destinations_from_args(args: argparse.Namespace) -> List[Destination]:
    """引数から配置先を解決する。不正な組み合わせは ValueError。"""
    host = location_host(args)
    options = options_from_args(args, host)
    if args.dest is not None:
        if args.scope is not None:
            raise ValueError("--dest replaces --scope; do not pass both")
        if options.requested():
            raise ValueError(f"{', '.join(options.requested())} cannot be combined with --dest; pass the skills directory itself")
        targets = parse_targets(args.target) if args.target else []
        for target in targets:
            if target not in TARGET_CHOICES:
                raise ValueError(f"unknown target '{target}'; choose from {', '.join(TARGET_CHOICES)}")
        return [Destination(args.dest.expanduser().resolve(), targets or ["custom"], "--dest")]
    if args.scope is None:
        raise ValueError("one of --scope or --dest is required")
    return resolve_destinations(args.scope, parse_targets(args.target), host.workspace, host.home, options)


def destination_target(destination: Destination) -> Optional[str]:
    """opencode か hermes を含む配置先なら、その名前。重複の確認と検証の基準にする。"""
    for name in ENVIRONMENT_TARGETS:
        if name in destination.targets:
            return name
    return None


def destination_notes(destination: Destination, scope: Optional[str], host: skill_env.Host,
                      source: Optional[Path]) -> List[str]:
    """配置先の決め方、注意、同名 Skill の重複を、表示用の行にする。何も変更しない。"""
    lines: List[str] = []
    if destination.origin:
        lines.append(f"note     {', '.join(destination.targets)}: skills directory {destination.skills_dir} "
                     f"(decided by: {destination.origin})")
    lines.extend(f"note     {text}" for text in destination.notes)
    target = destination_target(destination)
    if target:
        roots = skill_env.duplicate_roots(target, scope or "user", host, destination.skills_dir)
        copies = skill_env.find_other_copies(roots, destination=destination.path, source=source)
        lines.extend(f"warn     {skill_env.describe_copy(copy, target)}" for copy in copies)
    return lines


def link_note(destination: Destination) -> Optional[str]:
    """Hermes は、シンボリックリンクの Skill をリモートの backend へ送らない。"""
    if destination_target(destination) != "hermes":
        return None
    return ("note     --link: Hermes does not copy symlinked skills into Docker, SSH, Modal or Daytona sandboxes "
            "(it skips symlinks); use the default copy when the terminal backend is not local")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="共通 Skill を、各エージェントが読む場所へ配置する。",
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_location_arguments(parser)
    parser.add_argument("--dry-run", action="store_true", help="何も書かずに、実行する内容だけを表示する")
    parser.add_argument("--link", action="store_true",
                        help="複製ではなくシンボリックリンクを作る(正本の更新がすぐ反映される。Windows では権限が要る場合がある)")
    parser.add_argument("--on-conflict", choices=("skip", "backup", "overwrite"), default="skip",
                        help="配置先に、内容の違うものが既にある場合の動作。skip=何もしない(既定), backup=退避してから配置, overwrite=削除して配置。"
                             "内容が同じなら、どれを指定しても何もしない")
    parser.add_argument("--source", type=Path, default=None, help="skill のディレクトリ。既定 skill/japanese-readability-editor")
    return parser


def post_install_check(source: Path, path: Path, target: Optional[str]) -> Outcome:
    """配置した直後に、構造・メタデータ・参照先・正本との一致を確かめる(スクリプトは実行しない)。"""
    import verify_install  # install.py と循環しないよう、ここで読み込む

    report = verify_install.verify_installation(path, target=target, source=source, run_scripts=False)
    report.require_source_match()
    if report.ok:
        return Outcome(path, "note", "verify   OK: structure, metadata, references, identical to the source "
                                     "(run tools/verify_install.py to also run the scripts)")
    return Outcome(path, "error", "verify   FAILED: " + "; ".join(f.message for f in report.errors))


def _install_and_report(source: Path, destination: Destination, args: argparse.Namespace,
                        host: skill_env.Host) -> List[Outcome]:
    """1つの配置先に配置して、結果、注意、配置後の検証を表示する。"""
    outcomes = [install_one(source, destination, link=args.link, on_conflict=args.on_conflict, dry_run=args.dry_run)]
    notes = destination_notes(destination, args.scope, host, source)
    if args.link:
        notes.extend(filter(None, [link_note(destination)]))
    if outcomes[0].status in ("installed", "unchanged") and not args.link:
        outcomes.append(post_install_check(source, destination.path, destination_target(destination)))
    for outcome in outcomes[:1] + [Outcome(destination.path, "note", line) for line in notes] + outcomes[1:]:
        print(outcome.message, file=sys.stderr if outcome.status == "error" else sys.stdout)
    return outcomes


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    source = (args.source or default_skill_dir()).resolve()

    report = validate_skill(source)
    if not report.ok:
        for message in report.errors:
            print(f"ERROR: {message}", file=sys.stderr)
        print("FAILED: the source skill is invalid; nothing was installed", file=sys.stderr)
        return 1

    host = location_host(args)
    try:
        destinations = destinations_from_args(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    outcomes = [outcome for destination in destinations for outcome in _install_and_report(source, destination, args, host)]
    counts = {status: sum(1 for o in outcomes if o.status == status)
              for status in ("installed", "unchanged", "dry-run", "skipped", "error")}
    print("summary: " + ", ".join(f"{n} {status}" for status, n in counts.items() if n))
    return 1 if counts["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
