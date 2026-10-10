"""テストの共通ヘルパー。標準ライブラリだけを使う。"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path
from types import ModuleType
from typing import List, Optional

sys.dont_write_bytecode = True  # skill 本体のディレクトリに __pycache__ を残さない

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_NAME = "japanese-readability-editor"
SKILL_DIR = REPO_ROOT / "skill" / SKILL_NAME
SCRIPTS_DIR = SKILL_DIR / "scripts"
TOOLS_DIR = REPO_ROOT / "tools"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_module(name: str, path: Path) -> ModuleType:
    """ファイルのパスからモジュールを読み込む(scripts/ と tools/ はパッケージではないため)。"""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# 利用者の環境の設定が、テストの配置先の解決に混ざらないよう、子プロセスから外す変数。
ISOLATED_ENV_VARS = ("HERMES_HOME", "HERMES_DATA_DIR_SUFFIX", "XDG_CONFIG_HOME", "OPENCODE_CONFIG_DIR",
                     "OPENCODE_DISABLE_EXTERNAL_SKILLS", "OPENCODE_DISABLE_CLAUDE_CODE", "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS")


def run_script(path: Path, *args: str, stdin: Optional[str] = None, cwd: Optional[Path] = None,
               env: Optional[dict] = None):
    """スクリプトを別プロセスで実行する。(終了コード, stdout, stderr) を返す。

    env を渡すと、その変数を足す(利用者の HERMES_HOME などは、渡さない限り子プロセスに引き継がない)。
    """
    base = {k: v for k, v in os.environ.items() if k not in ISOLATED_ENV_VARS}
    base.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    base.update(env or {})
    completed = subprocess.run(
        [sys.executable, str(path), *args],
        input=stdin, capture_output=True, text=True, encoding="utf-8", cwd=cwd, env=base, timeout=60,
    )
    return completed.returncode, completed.stdout, completed.stderr


VALID_DESCRIPTION = "日本語の文章を読みやすくするテスト用の skill。"


def write_skill(root: Path, *, name: str = SKILL_NAME, frontmatter: Optional[str] = None,
                body: str = "# テスト\n\n本文。\n", directory: Optional[str] = None) -> Path:
    """テスト用の skill を root/<directory or name>/ に作る。skill のパスを返す。"""
    skill = root / (directory or name)
    skill.mkdir(parents=True, exist_ok=True)
    if frontmatter is None:
        frontmatter = f"---\nname: {name}\ndescription: {VALID_DESCRIPTION}\n---\n"
    (skill / "SKILL.md").write_text(frontmatter + body, encoding="utf-8")
    return skill


def copy_real_skill(destination_root: Path) -> Path:
    """本物の skill を一時ディレクトリへ複製する。"""
    import shutil

    target = destination_root / SKILL_NAME
    shutil.copytree(SKILL_DIR, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return target


def hermes_default_home(home: Path) -> Path:
    """--home を指定したときの、Hermes の既定のホーム。Windows は %LOCALAPPDATA% の下(hermes_constants に合わせる)。"""
    return home / "AppData" / "Local" / "hermes" if sys.platform == "win32" else home / ".hermes"


def symlinks_supported() -> bool:
    """シンボリックリンクを作れる環境か。Windows では権限が要ることがある。"""
    with tempfile.TemporaryDirectory(prefix="jre-symlink-") as tmp:
        try:
            os.symlink(Path(tmp), Path(tmp) / "link", target_is_directory=True)
        except (OSError, NotImplementedError):
            return False
    return True


def temporary_directory() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="jre-test-")


def dedent(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


__all__: List[str] = [
    "ISOLATED_ENV_VARS", "REPO_ROOT", "SKILL_NAME", "SKILL_DIR", "SCRIPTS_DIR", "TOOLS_DIR", "FIXTURES", "VALID_DESCRIPTION",
    "load_module", "run_script", "write_skill", "copy_real_skill", "hermes_default_home", "symlinks_supported",
    "temporary_directory",
    "dedent",
]
