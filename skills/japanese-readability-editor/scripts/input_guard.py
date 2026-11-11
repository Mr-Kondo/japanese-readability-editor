"""入力ファイルを読む前の検査。直接実行しない。

推敲する文書に紛れ込んだ指示で、スクリプトが鍵や認証のファイルを読み、中身を出力に載せる経路を塞ぐ。
呼び出し側は、標準入力(-)を先に分けてから呼ぶ(「-」という名前のファイルも検査する)。
読んでよいのは、標準入力と、作業フォルダまたは一時フォルダの下にあり、
その下の部分に「.」で始まる名前(.env、.git など)を含まないファイル。
シンボリックリンクは、リンク先で判定する。読まないときは PermissionError を送出する。
呼び出し側は OSError として扱い、終了コード 2 にする。

限界: 文書内の指示に従うエージェントの動きは防げない。読む範囲を狭めるだけである。
一時フォルダ全体を許すため、そこに「.」なしの名前で置かれた他のファイルは読める(書き換え前の文章の退避先に使うため)。
大文字小文字を区別しないファイルシステムで、作業フォルダと大文字小文字だけが違うパスは、読まない側に倒れる。
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import List


def _roots() -> List[Path]:
    roots = [Path.cwd().resolve(), Path(tempfile.gettempdir()).resolve()]
    if os.path.isdir("/tmp"):  # scripts.md の退避先に /tmp を使う環境がある
        roots.append(Path("/tmp").resolve())
    return roots


def check_readable(path: str) -> None:
    real = Path(os.path.realpath(path))
    for root in _roots():
        try:
            relative = real.relative_to(root)
        except ValueError:
            continue
        if not any(part.startswith(".") for part in relative.parts):
            return
    raise PermissionError(
        f"{path}: 読まない。作業フォルダ・一時フォルダの外にあるか、名前が「.」で始まる場所にある。"
        "読ませたい文書は、作業フォルダの「.」で始まらない名前へ写すか、標準入力(-)で渡す"
    )
