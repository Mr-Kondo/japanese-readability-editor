"""環境ごとの配置先の表と解決(OpenCode と Hermes Agent を含む)、配置内容の比較。

verify_install.py と package.py が共有する。標準ライブラリだけを使う。

環境変数は、Host の env で受け取る。プロセスの環境は暗黙には読まない。実際の環境変数を使うかどうかは、
呼び出し側(location_host)が決める。

配置先の根拠(確認日・参照 URL・版)は docs/opencode-hermes-checks.md にある。
  OpenCode  https://opencode.ai/docs/skills/ と sst/opencode のソース(packages/opencode/src/skill/index.ts)
  Hermes    https://hermes-agent.nousresearch.com/docs/user-guide/features/skills と
            NousResearch/hermes-agent のソース(hermes_constants.py、agent/skill_utils.py、hermes_cli/main.py)
Hermes のホームとプロファイルの解決は、公式文書の記述に加えて、上のソースの挙動に合わせている。
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_skill import EXPECTED_NAME, SKILL_FILE, iter_skill_files  # noqa: E402

# Hermes のプロファイル名(hermes_constants.PROFILE_ID_RE)。
HERMES_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
# これらのファイルのどれかがあるディレクトリだけを、Hermes はプロファイルとして扱う(プロファイルの公式文書)。
HERMES_PROFILE_MARKERS = ("config.yaml", ".env", "SOUL.md", "profile.yaml", "auth.json", "state.db")


@dataclass(frozen=True)
class Host:
    """配置先を解決し、同名の Skill を探す前提になる、実行している環境。"""

    workspace: Path
    home: Path
    env: Mapping[str, str] = field(default_factory=dict)
    platform: str = sys.platform

    def setting(self, key: str) -> str:
        return self.env.get(key, "").strip()

    def expand(self, value: str) -> Path:
        """`~` と `${VAR}` を展開する。`~` は home、`${VAR}` は env から取る(os.environ は読まない)。"""
        def substitute(match: "re.Match[str]") -> str:
            return self.env.get(match.group(1), match.group(0))

        text = re.sub(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", substitute, value.strip())
        if text == "~":
            return self.home
        if text.startswith(("~/", "~\\")):
            return self.home / text[2:]
        return Path(text)


@dataclass(frozen=True)
class Resolution:
    """配置先の skills ディレクトリと、その決め方。"""

    skills_dir: Path
    origin: str
    notes: Tuple[str, ...] = ()


@dataclass
class TreeDiff:
    missing: List[str] = field(default_factory=list)  # 正本にあって、比較先にない
    extra: List[str] = field(default_factory=list)    # 比較先にだけある
    changed: List[str] = field(default_factory=list)  # 両方にあって、内容が違う

    @property
    def identical(self) -> bool:
        return not (self.missing or self.extra or self.changed)

    def summary(self, limit: int = 5) -> str:
        parts: List[str] = []
        for label, items in (("missing", self.missing), ("extra", self.extra), ("changed", self.changed)):
            if items:
                shown = ", ".join(items[:limit]) + (f", ... (+{len(items) - limit})" if len(items) > limit else "")
                parts.append(f"{label}: {shown}")
        return "; ".join(parts) or "identical"


# --- 内容の比較 -------------------------------------------------------------


def file_digests(root: Path) -> Dict[str, str]:
    """skill に含めるファイル(iter_skill_files と同じ範囲)の、相対パス → SHA-256。"""
    return {relative.as_posix(): hashlib.sha256((root / relative).read_bytes()).hexdigest()
            for relative in iter_skill_files(root)}


def diff_trees(source: Path, other: Path) -> TreeDiff:
    """source を基準に、other の内容がどう違うかを返す。other がディレクトリでなければ、すべて missing。"""
    expected = file_digests(source)
    if not other.is_dir():
        return TreeDiff(missing=sorted(expected))
    actual = file_digests(other)
    return TreeDiff(
        missing=sorted(set(expected) - set(actual)),
        extra=sorted(set(actual) - set(expected)),
        changed=sorted(p for p in expected.keys() & actual.keys() if expected[p] != actual[p]),
    )


# --- OpenCode ---------------------------------------------------------------


def resolve_opencode(scope: str, host: Host, config_dir: Optional[Path] = None) -> Resolution:
    """OpenCode が読む skills ディレクトリ。

    workspace: <workspace>/.opencode/skills。OpenCode は、作業ディレクトリから git の worktree まで
               親へたどって `.opencode` を探す。
    user:      OPENCODE_CONFIG_DIR(または config_dir)があればその skills。なければ
               $XDG_CONFIG_HOME/opencode/skills。それもなければ ~/.config/opencode/skills。
               OpenCode は XDG の設定ディレクトリと OPENCODE_CONFIG_DIR の両方を探すので、どちらに置いても読まれる。
    """
    if scope == "workspace":
        return Resolution(host.workspace / ".opencode" / "skills", "project (.opencode/skills)")
    if config_dir is not None:
        return Resolution(config_dir / "skills", "--opencode-config-dir")
    if host.setting("OPENCODE_CONFIG_DIR"):
        return Resolution(host.expand(host.setting("OPENCODE_CONFIG_DIR")) / "skills", "$OPENCODE_CONFIG_DIR")
    if host.setting("XDG_CONFIG_HOME"):
        return Resolution(host.expand(host.setting("XDG_CONFIG_HOME")) / "opencode" / "skills", "$XDG_CONFIG_HOME/opencode")
    return Resolution(host.home / ".config" / "opencode" / "skills", "default (~/.config/opencode)")


# --- Hermes Agent -----------------------------------------------------------


def hermes_native_home(host: Host) -> Path:
    """プラットフォームの既定の Hermes ホーム(hermes_constants._get_platform_default_hermes_home)。"""
    suffix = host.setting("HERMES_DATA_DIR_SUFFIX")
    if host.platform == "win32":
        local = host.setting("LOCALAPPDATA")
        return (Path(local) if local else host.home / "AppData" / "Local") / ("hermes" + suffix)
    return host.home / (".hermes" + suffix)


def hermes_root(host: Host) -> Path:
    """プロファイルを含む根(hermes_constants.get_default_hermes_root)。

    HERMES_HOME が既定のホームの下なら、既定のホーム。それ以外(Docker など)は HERMES_HOME 自身。
    ただし HERMES_HOME が `profiles/<名前>` なら、その2つ上を根とする。
    """
    native = hermes_native_home(host)
    if not host.setting("HERMES_HOME"):
        return native
    path = host.expand(host.setting("HERMES_HOME"))
    try:
        path.resolve().relative_to(native.resolve())
        return native
    except ValueError:
        return path.parent.parent if path.parent.name == "profiles" else path


def _read_active_profile(root: Path) -> Optional[str]:
    marker = root / "active_profile"
    try:
        name = marker.read_text(encoding="utf-8-sig").strip() if marker.is_file() else ""
    except (OSError, UnicodeDecodeError):
        return None
    return name or None


def is_hermes_profile_dir(path: Path) -> bool:
    return path.is_dir() and any((path / marker).exists() for marker in HERMES_PROFILE_MARKERS)


def _hermes_named_profile(root: Path, profile: str) -> Resolution:
    if not HERMES_PROFILE_RE.match(profile):
        raise ValueError(f"invalid Hermes profile name '{profile}' (allowed: lowercase letters, digits, '_' and '-', "
                         "starting with a letter or digit, up to 64 characters)")
    if profile == "default":
        return Resolution(root / "skills", "--profile default")
    profile_dir = root / "profiles" / profile
    if not is_hermes_profile_dir(profile_dir):
        raise ValueError(f"Hermes profile '{profile}' was not found at {profile_dir} "
                         "(create it with: hermes profile create NAME; or pass the directory with --hermes-home)")
    return Resolution(profile_dir / "skills", f"--profile {profile}")


def _hermes_implicit_home(host: Host) -> Resolution:
    """明示の指定がないときに、Hermes 本体が選ぶホーム(hermes_cli.main._apply_profile_override)。"""
    root = hermes_root(host)
    value = host.setting("HERMES_HOME")
    env_home = host.expand(value) if value else None
    if env_home is not None and env_home.parent.name == "profiles":
        return Resolution(env_home / "skills", "$HERMES_HOME (a profile directory)")
    notes: List[str] = []
    sticky = _read_active_profile(root)
    if sticky and sticky != "default":
        if HERMES_PROFILE_RE.match(sticky) and is_hermes_profile_dir(root / "profiles" / sticky):
            return Resolution(root / "profiles" / sticky / "skills", f"active profile '{sticky}' ({root / 'active_profile'})",
                              ("to install into another profile, pass --profile NAME or --hermes-home PATH",))
        notes.append(f"{root / 'active_profile'} names profile '{sticky}', which was not found; using the root home instead")
    if env_home is not None:
        return Resolution(env_home / "skills", "$HERMES_HOME", tuple(notes))
    return Resolution(root / "skills", "default", tuple(notes))


def resolve_hermes(scope: str, host: Host, hermes_home: Optional[Path] = None,
                   profile: Optional[str] = None) -> Resolution:
    """Hermes が読む skills ディレクトリ。

    workspace: <workspace>/.hermes/skills(プロジェクトローカル。使うには `hermes skills trust` が要る)。
    user:      実際の Hermes ホーム/skills。ホームは次の順で決める(Hermes 本体と同じ)。
               1. hermes_home  2. profile 名(<根>/profiles/<名>。default は根)
               3. HERMES_HOME が profiles/<名> を指すなら、それ
               4. <根>/active_profile に default 以外の名前があれば、そのプロファイル(`hermes profile use`)
               5. HERMES_HOME  6. 既定のホーム(~/.hermes。Windows は %LOCALAPPDATA%\\hermes)
    """
    if scope == "workspace":
        return Resolution(host.workspace / ".hermes" / "skills", "project (.hermes/skills)", (
            "Hermes loads project skills only after you trust the repo once: hermes skills trust (not run by this tool)",
            "the project root is the nearest ancestor of the working directory that contains .git",
        ))
    if hermes_home is not None:
        return Resolution(hermes_home / "skills", "--hermes-home")
    if profile is not None:
        return _hermes_named_profile(hermes_root(host), profile)
    return _hermes_implicit_home(host)


# --- 配置先の指定(package.py と verify_install.py が使う) -------------------------------------------

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
    "opencode": ".config/opencode/skills",  # 実際の場所は resolve_opencode が決める
    "hermes": ".hermes/skills",             # 実際の場所は resolve_hermes が決める
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


def _resolve_target(target: str, scope: str, host: Host, options: LocationOptions) -> Resolution:
    """target の skills ディレクトリと、その決め方。OpenCode と Hermes は環境で変わり、ほかは表から引く。"""
    if target == "opencode":
        return resolve_opencode(scope, host, options.opencode_config_dir)
    if target == "hermes":
        return resolve_hermes(scope, host, options.hermes_home, options.profile)
    table = WORKSPACE_DIRS if scope == "workspace" else USER_DIRS
    base = host.workspace if scope == "workspace" else host.home
    return Resolution(base / table[target], "")


def resolve_destinations(scope: str, targets: List[str], workspace: Path, home: Path,
                         options: Optional[LocationOptions] = None) -> List[Destination]:
    """target を配置先のディレクトリへ解決する。同じ場所は1つにまとめる。"""
    options = options or LocationOptions()
    host = Host(workspace, home, options.env or {}, options.platform or sys.platform)
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


def location_host(args: argparse.Namespace) -> Host:
    """作業ディレクトリ、ホーム、環境変数。--home を指定したときは、環境変数を使わない。"""
    workspace = (args.workspace or Path.cwd()).resolve()
    home = (args.home or Path.home()).resolve()
    return Host(workspace, home, {} if args.home else dict(os.environ))


def options_from_args(args: argparse.Namespace, host: Host) -> LocationOptions:
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
