#!/usr/bin/env python3
"""measure_skill_tokens.py の記録(evals/kokugo-check の入力で流したもの)を、国語の検査で集計する。

直した後の文書(`*.doc.md`)を check_kokugo.py(general-tech)で再検査し、残った error の数と、保護すべき箇所
(05 の引用、06 のコード)が変わっていないかを、版・条件ごとに数える。モデルは使わない。
"""

import json
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = ROOT / "skills" / "japanese-readability-editor" / "scripts" / "check_kokugo.py"
# 保護すべき箇所(入力の番号, その箇所の文字列)。直されたら保持に失敗した扱い。
PROTECTED = {"05": "> こんにちわ、田中です。(原文のまま引用)", "06": 'echo "そうゆう"'}


def remaining_errors(text: str) -> int:
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as stream:
        stream.write(text)
    try:
        out = subprocess.run([sys.executable, str(CHECK), stream.name, "--profile", "general-tech", "--json"],
                             capture_output=True, text=True, encoding="utf-8").stdout
    finally:
        Path(stream.name).unlink()
    return json.loads(out)["summary"]["error"]


def main(argv) -> int:
    runs = Path(argv[0])
    groups = defaultdict(list)
    for path in sorted(runs.glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        doc = path.parent / (path.stem + ".doc.md")
        text = doc.read_text(encoding="utf-8")
        protected = PROTECTED.get(record["input"])
        groups[(record["label"], record["variant"])].append({
            "errors": remaining_errors(text), "protected_kept": protected is None or protected in text,
            "calls": len(record["turn_input_totals"]), "tokens": record["input_side_tokens"],
            "kokugo_run": any(s["script"] == "check_kokugo.py" for s in record["scripts_run"])})
    print("| 版 | 条件 | 回数 | 誤りが残らなかった回 | 残った誤り(平均) | 保護箇所を保った回 | check_kokugo.py を実行した回 | API 呼び出し(中央値) | 入力側(中央値) |")
    print("|---|---|---|---|---|---|---|---|---|")
    for (label, variant), rows in sorted(groups.items()):
        n = len(rows)
        print(f"| {label} | {variant} | {n} | {sum(r['errors'] == 0 for r in rows)}/{n} | {statistics.mean(r['errors'] for r in rows):.2f} | "
              f"{sum(r['protected_kept'] for r in rows)}/{sum(1 for r in rows)} | {sum(r['kokugo_run'] for r in rows)}/{n} | "
              f"{statistics.median(r['calls'] for r in rows):g} | {statistics.median(r['tokens'] for r in rows):,.0f} |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
