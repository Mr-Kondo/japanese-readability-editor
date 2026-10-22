"""フィードバック用 JSON の保存。入力文書と既存の記録は上書きしない。"""

import json
import os
import tempfile
from pathlib import Path


def save_report(report: dict, out_dir=None) -> Path:
    folder = (Path(out_dir).expanduser() if out_dir is not None else
              Path.home() / ".agents" / "feedback" / "japanese-readability-editor")
    folder = folder.resolve()
    folder.mkdir(mode=0o700, parents=True, exist_ok=True)
    contents = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    descriptor, filename = tempfile.mkstemp(prefix=report["kind"] + "-", suffix=".json", dir=folder)
    saved = Path(filename)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(contents)
    except OSError:
        saved.unlink()
        raise
    return saved
