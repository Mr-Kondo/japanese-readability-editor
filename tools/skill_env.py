"""OpenCode と Hermes Agent の配置先の解決、同名 Skill の探索、配置内容の比較。

install.py、uninstall.py、verify_install.py、package.py が共有する。標準ライブラリだけを使う。

環境変数は、Host の env で受け取る。プロセスの環境は暗黙には読まない。実際の環境変数を使うかどうかは、
呼び出し側(install.py)が決める。

配置先の根拠(確認日・参照 URL・版)は docs/opencode-hermes-checks.md にある。
  OpenCode  https://opencode.ai/docs/skills/ と sst/opencode のソース(packages/opencode/src/skill/index.ts)
  Hermes    https://hermes-agent.nousresearch.com/docs/user-guide/features/skills と
            NousResearch/hermes-agent のソース(hermes_constants.py、agent/skill_utils.py、hermes_cli/main.py)
Hermes のホームとプロファイルの解決は、公式文書の記述に加えて、上のソースの挙動に合わせている。
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from validate_skill import EXPECTED_NAME, SKILL_FILE, iter_skill_files  # noqa: E402

# Hermes のプロファイル名(hermes_constants.PROFILE_ID_RE)。
HERMES_PROFILE_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
# これらのファイルのどれかがあるディレクトリだけを、Hermes はプロファイルとして扱う(プロファイルの公式文書)。
HERMES_PROFILE_MARKERS = ("config.yaml", ".env", "SOUL.md", "profile.yaml", "auth.json", "state.db")
# 探索のとき降りないディレクトリ(Hermes の EXCLUDED_SKILL_DIRS に合わせ、依存物と履歴を除く)。
SCAN_EXCLUDED_DIRS = frozenset((
    ".git", ".github", ".hub", ".archive", ".curator_backups", ".locks", ".venv", "venv",
    "node_modules", "site-packages", "__pycache__",
))
SCAN_MAX_DEPTH = 3
TRUTHY = {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Host:
    """配置先を解決し、同名の Skill を探す前提になる、実行している環境。"""

    workspace: Path
    home: Path
    env: Mapping[str, str] = field(default_factory=dict)
    platform: str = sys.platform

    def setting(self, key: str) -> str:
        return self.env.get(key, "").strip()

    def flag(self, key: str) -> bool:
        return self.setting(key).lower() in TRUTHY

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


@dataclass(frozen=True)
class Copy:
    """探索で見つけた、同名の Skill。"""

    path: Path
    where: str
    relation: str  # identical, differs, unknown


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


def git_root(start: Path) -> Optional[Path]:
    """start から親へたどって、最初に `.git`(ディレクトリまたは worktree のファイル)がある場所。なければ None。"""
    current = start.resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


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


def opencode_config_skill_dirs(host: Host) -> List[Tuple[str, Path]]:
    """OpenCode が `{skill,skills}/**/SKILL.md` として探す設定ディレクトリ配下の候補。"""
    xdg = host.expand(host.setting("XDG_CONFIG_HOME")) if host.setting("XDG_CONFIG_HOME") else host.home / ".config"
    configs = [("OpenCode config", xdg / "opencode")]
    if host.setting("OPENCODE_CONFIG_DIR"):
        configs.append(("$OPENCODE_CONFIG_DIR", host.expand(host.setting("OPENCODE_CONFIG_DIR"))))
    configs.append(("~/.opencode", host.home / ".opencode"))
    return [(label, base / sub) for label, base in configs for sub in ("skills", "skill")]


def _opencode_external_dirs(base: Path, host: Host, label: str) -> List[Tuple[str, Path]]:
    """base 直下の `.claude/skills` と `.agents/skills`(OpenCode の互換探索)。無効化の環境変数を守る。"""
    if host.flag("OPENCODE_DISABLE_EXTERNAL_SKILLS"):
        return []
    claude_off = host.flag("OPENCODE_DISABLE_CLAUDE_CODE") or host.flag("OPENCODE_DISABLE_CLAUDE_CODE_SKILLS")
    found: List[Tuple[str, Path]] = []
    if not claude_off:
        found.append((f"{label}.claude/skills (read by OpenCode per its docs)", base / ".claude" / "skills"))
    found.append((f"{label}.agents/skills (read by OpenCode per its docs)", base / ".agents" / "skills"))
    return found


def opencode_roots(host: Host) -> List[Tuple[str, Path]]:
    """OpenCode が同名の Skill を見つけうる場所(公式文書とソースによる)。"""
    roots = _opencode_external_dirs(host.home, host, "~/")
    roots.extend(opencode_config_skill_dirs(host))
    workspace = host.workspace.resolve()
    top = git_root(workspace)
    directories = [workspace] if top is None else [d for d in (workspace, *workspace.parents) if d == top or top in d.parents]
    for directory in directories:
        roots.extend((f"{directory}/.opencode/{sub}", directory / ".opencode" / sub) for sub in ("skills", "skill"))
        roots.extend(_opencode_external_dirs(directory, host, f"{directory}/"))
    return roots


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


def _skills_block(config_text: str) -> List[str]:
    """config.yaml の最上位の `skills:` の下にある行を、コメントと空行を除いて返す。"""
    block: List[str] = []
    inside = False
    for line in config_text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line.startswith((" ", "\t")):
            inside = bool(re.match(r"^skills:\s*(#.*)?$", line))
            continue
        if inside:
            block.append(line)
    return block


def _scalar(value: str) -> str:
    value = re.sub(r"\s+#.*$", "", value).strip()
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'" else value


def _skills_entries(block: List[str]) -> Dict[str, Tuple[str, List[str]]]:
    """`skills:` の直下のキーごとに、(同じ行の値, 続く `- ` の項目) を返す。キーは、最も浅いインデントのものだけ。"""
    if not block:
        return {}
    base = min(len(line) - len(line.lstrip(" ")) for line in block)
    entries: Dict[str, Tuple[str, List[str]]] = {}
    current: Optional[List[str]] = None
    for line in block:
        stripped = line.strip()
        key = None if stripped.startswith("- ") else re.match(r"^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$", stripped)
        if key and len(line) - len(line.lstrip(" ")) == base:
            current = []
            entries[key.group(1)] = (_scalar(key.group(2)), current)
        elif current is not None and stripped.startswith("- "):
            current.append(_scalar(stripped[2:]))
    return entries


def _parse_skills_block(block: List[str]) -> Tuple[List[str], Optional[str]]:
    """`external_dirs`(ブロック形式か `[a, b]` の1行形式、または1つの値)と `create_dir` を取り出す。"""
    entries = _skills_entries(block)
    inline, items = entries.get("external_dirs", ("", []))
    if inline.startswith("[") and inline.endswith("]"):
        items = [_scalar(part) for part in inline[1:-1].split(",")]
    elif inline:
        items = [inline]
    create = entries.get("create_dir", ("", []))[0]
    return [item for item in items if item], create or None


def read_hermes_skills_config(config_path: Path, host: Host, hermes_home: Path) -> Tuple[List[Path], Optional[Path]]:
    """config.yaml の skills.external_dirs と skills.create_dir を、最小限の読み取りで取り出す。

    PyYAML に依存しないため、`skills:` の直下の `external_dirs:` と `create_dir:` だけを扱う。
    読めない書き方は、見つからなかったものとして扱う(探索の補助であり、検証の根拠ではない)。
    相対パスは Hermes のホームからの相対として扱う(Hermes 本体と同じ)。
    """
    try:
        text = config_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return [], None
    externals, create = _parse_skills_block(_skills_block(text))

    def absolute(entry: str) -> Path:
        path = host.expand(entry)
        return path if path.is_absolute() else hermes_home / path

    return [absolute(entry) for entry in externals], absolute(create) if create else None


def hermes_roots(host: Host, hermes_home: Path) -> List[Tuple[str, Path]]:
    """Hermes が同名の Skill を見つけうる場所(公式文書とソースによる)。"""
    roots: List[Tuple[str, Path]] = [(f"{hermes_home}/skills (profile)", hermes_home / "skills")]
    external, create = read_hermes_skills_config(hermes_home / "config.yaml", host, hermes_home)
    if create is not None:
        roots.append(("skills.create_dir", create))
    roots.extend(("skills.external_dirs entry", path) for path in external)
    top = git_root(host.workspace)
    if top is not None:
        for sub in (".hermes/skills", ".agents/skills"):
            roots.append((f"{top}/{sub} (project; loaded only when the repo is trusted)", top / sub))
    return roots


# --- 同名 Skill の探索 ------------------------------------------------------


def _declared_name(skill_md: Path) -> Optional[str]:
    """SKILL.md の frontmatter の name。読めなければ None。YAML の解釈はしない。"""
    try:
        with open(skill_md, "r", encoding="utf-8-sig") as handle:
            head = [handle.readline() for _ in range(40)]
    except (OSError, UnicodeDecodeError):
        return None
    if not head or head[0].rstrip() != "---":
        return None
    for line in head[1:]:
        if line.rstrip() == "---":
            break
        match = re.match(r"^name:\s*(.*?)\s*$", line)
        if match:
            return match.group(1).strip("\"'")
    return None


def _real(path: Path) -> Path:
    try:
        return path.resolve()
    except OSError:
        return path


def _subdirectories(directory: Path) -> List[Path]:
    try:
        return sorted(p for p in directory.iterdir() if p.is_dir() and p.name not in SCAN_EXCLUDED_DIRS)
    except OSError:
        return []


def scan_for_skill(root: Path, name: str = EXPECTED_NAME, max_depth: int = SCAN_MAX_DEPTH) -> List[Path]:
    """root の下で、frontmatter の name が一致する Skill のディレクトリを返す。シンボリックリンクはたどる。"""
    found: List[Path] = []
    visited: set = set()

    def walk(directory: Path, depth: int) -> None:
        real = _real(directory)
        if real in visited:
            return
        visited.add(real)
        if (directory / SKILL_FILE).is_file():
            if _declared_name(directory / SKILL_FILE) == name:
                found.append(directory)
            return
        if depth < max_depth:
            for child in _subdirectories(directory):
                walk(child, depth + 1)

    if root.is_dir():
        walk(root, 0)
    return found


def find_other_copies(roots: Iterable[Tuple[str, Path]], *, destination: Optional[Path],
                      source: Optional[Path]) -> List[Copy]:
    """roots のどれかで見つかる同名の Skill(destination 自身を除く)。重複する場所は1つにまとめる。"""
    seen = {_real(destination)} if destination is not None else set()
    copies: List[Copy] = []
    for label, root in roots:
        for path in scan_for_skill(root):
            if _real(path) in seen:
                continue
            seen.add(_real(path))
            if source is None:
                relation = "unknown"
            else:
                relation = "identical" if diff_trees(source, path).identical else "differs"
            copies.append(Copy(path, label, relation))
    return copies


def duplicate_roots(target: str, scope: str, host: Host, skills_dir: Path) -> List[Tuple[str, Path]]:
    """target が opencode か hermes のとき、その製品が同名の Skill を見つけうる場所。それ以外は空。"""
    if target == "opencode":
        return opencode_roots(host)
    if target == "hermes":
        installed_home = skills_dir.parent if scope == "user" else resolve_hermes("user", host).skills_dir.parent
        return hermes_roots(host, installed_home)
    return []


def describe_copy(copy: Copy, target: str) -> str:
    consequence = {
        "opencode": "OpenCode keeps only one of them (its docs ask for unique names; the other is logged as a duplicate or overridden, "
                    "so do not rely on which one wins)",
        "hermes": "Hermes uses the higher-precedence copy (project, then profile, then skills.create_dir, then external_dirs) "
                  "and hides the other; two different copies in the same tier are refused as ambiguous",
    }.get(target, "the same skill is discoverable twice")
    state = {"identical": "identical to the source", "differs": "DIFFERENT from the source",
             "unknown": "not compared"}[copy.relation]
    return f"also discoverable at {copy.path} [{copy.where}] ({state}); {consequence}. Nothing was removed; keep one yourself."
