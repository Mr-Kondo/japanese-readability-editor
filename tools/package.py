#!/usr/bin/env python3
"""共通 Skill から配布用の成果物を生成する。

    python3 tools/package.py [--out-dir dist] [--no-gemini-apps]

生成物(既定では dist/):
  japanese-readability-editor.zip      ChatGPT Work / Claude Cowork などのアップロード用。
                                       ZIP の最上位は japanese-readability-editor/ の1フォルダ。
  japanese-readability-editor.sha256   ZIP の SHA-256(sha256sum 形式)
  gemini-apps-instructions.md          Gemini Apps の Gem / Custom Instructions に貼る指示文
  gemini-apps/japanese-readability-editor/
                                       Gemini Apps の Skills へフォルダごとアップロードする用
                                       (scripts/ を除いたコピー)
  opencode/japanese-readability-editor/ と opencode/INSTALL.md
  hermes/japanese-readability-editor/   と hermes/INSTALL.md
                                       OpenCode と Hermes Agent 向けの配布物。Skill は正本の完全な複製で、
                                       INSTALL.md に配置先、配置コマンド、確認方法を書く。生成後に verify_install.py で検証する

Gemini Apps 向けの2つと、OpenCode・Hermes 向けの配布物は、共通 Skill から機械的に作る出力(adapter)であり、別実装ではない。
内容の正本は skill/japanese-readability-editor/ だけである。
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import zipfile
from pathlib import Path
from typing import Iterable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

import install  # noqa: E402
import verify_install  # noqa: E402
from validate_skill import EXPECTED_NAME, SKILL_FILE, default_skill_dir, iter_skill_files, parse_frontmatter, validate_skill  # noqa: E402

ZIP_TIMESTAMP = (2026, 1, 1, 0, 0, 0)  # 再現可能な ZIP にするため固定する
AGENT_BUNDLE_TARGETS = install.ENVIRONMENT_TARGETS  # 配布物を生成する環境。配置先は install.py の表から取る
REPOSITORY_URL = "https://github.com/Mr-Kondo/japanese-readability-editor"
GEMINI_EXCLUDED_DIRS = ("scripts", "data")  # Gemini Apps では実行できない scripts/ と、その入力にしか使わない data/ は含めない
FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
RELATIVE_LINK_RE = re.compile(r"\[([^\]]+)\]\((?![A-Za-z][A-Za-z0-9+.-]*:|#)[^)\s]+\)")


def default_out_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "dist"


# --- ZIP --------------------------------------------------------------------


def build_zip(skill_dir: Path, zip_path: Path) -> List[str]:
    """skill_dir を <name>/ 以下に収めた ZIP を作る。収めたファイルの相対パスを返す。"""
    skill_dir = Path(skill_dir)
    root = skill_dir.resolve().name
    added: List[str] = []
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for relative in iter_skill_files(skill_dir):
            info = zipfile.ZipInfo(f"{root}/{relative.as_posix()}", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            executable = relative.parts[0] == "scripts" and relative.suffix == ".py"
            info.external_attr = (0o755 if executable else 0o644) << 16
            archive.writestr(info, (skill_dir / relative).read_bytes())
            added.append(relative.as_posix())
    return added


def verify_zip(zip_path: Path, name: str = EXPECTED_NAME) -> List[str]:
    """ZIP の構造の問題を返す。空なら問題なし。"""
    problems: List[str] = []
    with zipfile.ZipFile(zip_path) as archive:
        if archive.testzip() is not None:
            problems.append("ZIP contains a corrupt entry")
        names = archive.namelist()
    top_levels = {n.split("/", 1)[0] for n in names}
    if top_levels != {name}:
        problems.append(f"ZIP must contain exactly one top-level folder '{name}', found {sorted(top_levels)}")
    if f"{name}/{SKILL_FILE}" not in names:
        problems.append(f"ZIP does not contain {name}/{SKILL_FILE}")
    return problems


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256(zip_path: Path, sha_path: Path) -> str:
    digest = sha256_of(zip_path)
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    return digest


# --- Gemini Apps 向けの出力 --------------------------------------------------


def demote_headings(markdown: str, levels: int) -> str:
    """fenced code block の外にある見出しを levels 段下げる。"""
    output: List[str] = []
    closing: Optional[re.Pattern] = None
    for line in markdown.split("\n"):
        if closing is not None:
            if closing.match(line):
                closing = None
        else:
            fence = FENCE_RE.match(line)
            if fence:
                marker = fence.group(1)
                closing = re.compile(r"^\s{0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}\s*$")
            elif re.match(r"^#{1,6}\s", line):
                line = "#" * min(6, len(line) - len(line.lstrip("#")) + levels) + " " + line.lstrip("#").lstrip()
        output.append(line)
    return "\n".join(output)


def strip_relative_links(markdown: str) -> str:
    """相対パスへのリンクを、リンク文字列だけに直す(貼り付け先ではファイルを開けないため)。"""
    return RELATIVE_LINK_RE.sub(r"\1", markdown)


def render_gemini_apps_instructions(skill_dir: Path) -> str:
    skill_dir = Path(skill_dir)
    _, body, _ = parse_frontmatter((skill_dir / SKILL_FILE).read_text(encoding="utf-8"))
    rules_path = skill_dir / "references" / "readability-rules.md"
    rules = rules_path.read_text(encoding="utf-8") if rules_path.is_file() else ""

    parts = [
        f"<!-- Generated by tools/package.py from skill/{skill_dir.name}/. Do not edit this file. -->",
        f"# {skill_dir.name}: Gemini Apps 用の指示",
        "",
        "Gem の「指示」、または Custom Instructions に貼り付けて使う。"
        "Gemini Apps の Skills では、この文書ではなく Skill のフォルダ(SKILL.md)をそのままアップロードできる。",
        "",
        "この文書は、共通の Agent Skill から自動生成した。scripts/ は実行できないので、"
        "計測と検証が必要なときは、長さの見積もりと空白以外の文字の一致を自分で確かめる。",
        "",
        "## Part 1. 指示",
        "",
        demote_headings(strip_relative_links(body.strip("\n")), 2),
    ]
    if rules:
        parts += [
            "",
            "## Part 2. 詳細ルール",
            "",
            "文字数の上限で貼り付けられない場合は、この Part 2 を省いてよい。",
            "",
            demote_headings(strip_relative_links(rules.strip("\n")), 2),
        ]
    return "\n".join(parts) + "\n"


def export_gemini_apps_folder(skill_dir: Path, target_root: Path) -> List[str]:
    """scripts/ と data/ を除いた skill のコピーを target_root/<name>/ に作る。"""
    skill_dir = Path(skill_dir)
    destination = target_root / skill_dir.resolve().name
    if target_root.exists():
        shutil.rmtree(target_root)
    copied: List[str] = []
    for relative in iter_skill_files(skill_dir):
        if relative.parts[0] in GEMINI_EXCLUDED_DIRS:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(skill_dir / relative, target)
        copied.append(relative.as_posix())
    return copied


# --- OpenCode / Hermes Agent 向けの配布物 ------------------------------------

BUNDLE_TEXT = {
    "opencode": {
        "title": "OpenCode",
        "invoke": "OpenCode のエージェントが `skill` ツールで `japanese-readability-editor` を読み込む。依頼文に Skill 名を書くと確実",
        "user_note": "`$XDG_CONFIG_HOME/opencode/skills/` や `$OPENCODE_CONFIG_DIR/skills/` も読まれる",
        "cautions": [
            "OpenCode の公式文書によると、`.claude/skills/` と `.agents/skills/` も読む。そこに同名の Skill があると、片方しか使われない。どちらが使われるかに頼らず、1か所にそろえる。",
            "`INSTALL.md` は skills ディレクトリに置かない。v2 のソースでは、skills ディレクトリの直下の `.md` も Skill として読み込まれる。置くのは `japanese-readability-editor/` のフォルダだけにする。",
        ],
    },
    "hermes": {
        "title": "Hermes Agent",
        "invoke": "`/japanese-readability-editor` のスラッシュコマンド、または Agent が `skill_view` で読み込む",
        "user_note": "`HERMES_HOME` やプロファイルで変わる。`~/.hermes/profiles/<名前>/skills/` など",
        "cautions": [
            "プロジェクトに置いた Skill は、`hermes skills trust` でリポジトリを信頼するまで読み込まれない。",
            "`hermes skills install` は `data/` を取り込まない。この Skill は `data/` がないと国語の検査が動かないので、下のコマンドか手動のコピーで置く。",
            "ターミナルのバックエンドが Docker、SSH、Modal、Daytona のときは、シンボリックリンクではなく複製で置く。",
        ],
    },
}

INSTALL_NOTES_TEMPLATE = """<!-- Generated by tools/package.py from skill/{skill}/. Do not edit this file. -->
# {skill}: {title} 用の配布物

`{skill}/` は、共通の Agent Skill (`skill/{skill}/`) の完全な複製です。{title} 向けに変えたファイルはありません。
`{skill}/` のフォルダごと、{title} の skills ディレクトリへ置きます。`SKILL.md`、`references/`、`scripts/`、`data/`、`assets/` はすべて必要です。

## 配置先

| 範囲 | 配置先 |
|---|---|
| プロジェクト | `<プロジェクト>/{project}/{skill}/` |
| ユーザー共通 | `{user}/{skill}/`({user_note}) |

## 置く

リポジトリを取得している場合は、`install.py` で置きます。内容が同じなら何もせず、違う既存のものは上書きしません。

```bash
python3 tools/install.py --source dist/{target}/{skill} --scope user --target {target} --dry-run
python3 tools/install.py --source dist/{target}/{skill} --scope user --target {target}
```

リポジトリがない場合は、フォルダを手でコピーします。

```bash
cp -R {skill} <skills ディレクトリ>/
```

## 確かめる

リポジトリがあるときは、置いた Skill を検証します。構造、メタデータ、正本との一致、同梱スクリプトの実行を確かめます。

```bash
python3 tools/verify_install.py --scope user --target {target}
```

リポジトリがなくても、置いた Skill のスクリプトは、どのディレクトリからでも実行できます。

```bash
python3 <skills ディレクトリ>/{skill}/scripts/measure.py --locate 文章.md
```

呼び出し方: {invoke}。

## 注意

{cautions}

導入、更新、トラブル対応の詳細は {url}/blob/main/docs/installation.md にあります。
"""


def render_agent_install_notes(skill_name: str, target: str) -> str:
    text = BUNDLE_TEXT[target]
    return INSTALL_NOTES_TEMPLATE.format(
        skill=skill_name, target=target, title=text["title"], invoke=text["invoke"], user_note=text["user_note"],
        project=install.WORKSPACE_DIRS[target], user="~/" + install.USER_DIRS[target], url=REPOSITORY_URL,
        cautions="\n".join(f"- {line}" for line in text["cautions"]),
    )


def export_agent_bundle(skill_dir: Path, bundle_root: Path, target: str) -> List[str]:
    """bundle_root/<name>/ に正本の完全な複製、bundle_root/INSTALL.md を作る。複製したファイルの相対パスを返す。"""
    skill_dir = Path(skill_dir)
    name = skill_dir.resolve().name
    if bundle_root.exists():
        shutil.rmtree(bundle_root)
    copied: List[str] = []
    for relative in iter_skill_files(skill_dir):
        destination = bundle_root / name / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(skill_dir / relative, destination)
        copied.append(relative.as_posix())
    (bundle_root / "INSTALL.md").write_text(render_agent_install_notes(name, target), encoding="utf-8")
    return copied


def build_agent_bundles(skill_dir: Path, out_dir: Path, targets: Iterable[str]) -> bool:
    """対象ごとに配布物を作り、正本と一致して動くかを検証する。すべて通れば True。"""
    name = skill_dir.resolve().name
    all_ok = True
    for target in targets:
        bundle_root = out_dir / target
        copied = export_agent_bundle(skill_dir, bundle_root, target)
        check = verify_install.verify_installation(bundle_root / name, target=target, source=skill_dir.resolve())
        check.require_source_match()
        print(f"bundle  {bundle_root / name} ({len(copied)} files, INSTALL.md) [{target}] verify: {'OK' if check.ok else 'FAILED'}")
        for finding in check.errors:
            print(f"ERROR: {target}: {finding.message}", file=sys.stderr)
        all_ok = all_ok and check.ok
    return all_ok


# --- CLI --------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="共通 Skill から配布用の成果物を生成する。")
    parser.add_argument("--skill-dir", type=Path, default=None, help="skill のディレクトリ。既定 skill/japanese-readability-editor")
    parser.add_argument("--out-dir", type=Path, default=None, help="出力先。既定 dist/")
    parser.add_argument("--no-gemini-apps", action="store_true", help="Gemini Apps 向けの出力を生成しない")
    parser.add_argument("--bundle", action="append", choices=AGENT_BUNDLE_TARGETS, metavar="TARGET",
                        help=f"OpenCode・Hermes 向けの配布物を生成する対象。繰り返し指定できる。既定は両方。選択肢: {', '.join(AGENT_BUNDLE_TARGETS)}")
    parser.add_argument("--no-agent-bundles", action="store_true", help="OpenCode・Hermes 向けの配布物を生成しない")
    args = parser.parse_args(argv)

    skill_dir = args.skill_dir or default_skill_dir()
    out_dir = args.out_dir or default_out_dir()

    report = validate_skill(skill_dir)
    for message in report.errors:
        print(f"ERROR: {message}", file=sys.stderr)
    if not report.ok:
        print("FAILED: fix the validation errors before packaging", file=sys.stderr)
        return 1

    name = skill_dir.resolve().name
    zip_path = out_dir / f"{name}.zip"
    files = build_zip(skill_dir, zip_path)
    problems = verify_zip(zip_path, name)
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        return 1
    digest = write_sha256(zip_path, out_dir / f"{name}.sha256")
    print(f"zip     {zip_path} ({zip_path.stat().st_size} bytes, {len(files)} files)")
    print(f"sha256  {out_dir / (name + '.sha256')} ({digest})")

    if not args.no_gemini_apps:
        instructions = out_dir / "gemini-apps-instructions.md"
        text = render_gemini_apps_instructions(skill_dir)
        instructions.write_text(text, encoding="utf-8")
        print(f"gemini  {instructions} ({len(text)} chars)")
        copied = export_gemini_apps_folder(skill_dir, out_dir / "gemini-apps")
        print(f"gemini  {out_dir / 'gemini-apps' / name} ({len(copied)} files, scripts/ and data/ excluded)")

    if not args.no_agent_bundles and not build_agent_bundles(skill_dir, out_dir, args.bundle or AGENT_BUNDLE_TARGETS):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
