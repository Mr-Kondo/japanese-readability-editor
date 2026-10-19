#!/usr/bin/env python3
"""sentence-kind-residue-cases.json の生成結果を、決まった文字列の有無で調べる(LLM の採点を使わない)。

    sentence-kind-residue-check.py LABEL=RUN_DIR [LABEL=RUN_DIR ...]

RUN_DIR は tools/evaluate_readability.py の出力フォルダ(run.json を持つ)。同じ LABEL の結果は合算する。
必須の表現(保つべきもの)が欠けた出力と、禁止の表現(足してはいけないもの、文体の変化)が出た出力を数える。
r01 の「削った」は、規則の動き(挨拶の定型だけを削り、申し出と方針の宣言は残す)を数えるもので、それだけでは失敗ではない。
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PLAIN = r"(?:です|ます|ました|でした)。"
CHECKS = {
    "k01": {"must": ["とされ", "聞い", "仮に", "決まっていない|決まっておらず|未定"], "never": [PLAIN]},
    "k02": {"must": ["まるで", "安全になるのか", "そうではない|ではない", "かえって"], "never": [PLAIN]},
    "k03": {"must": ["三時間|3時間", "次回", "有意義"], "never": ["無駄", PLAIN]},
    "r01": {"must": ["料金プランの比較は扱いません", "半日", "〇〇", "ました"], "never": ["終わった。", "送る。", "月末", r"〇〇(?!宛)"]},
    "r02": {"must": ["暗号化の方式は扱わず", "ご質問ありがとうございます。お使いの端末の型番を教えてください。", "標準的"], "never": []},
    "p01": {"must": ["30分", "承認", "登録し直す"], "never": ["必ず", "常に", "すべて"]},
}
RESIDUE = {"r01": [("挨拶の定型を削った", r"ご質問ありがとうございます"), ("申し出を削った", r"必要なら次に"), ("方針の宣言を削った", r"やさしいトーン|一般論ではなく")]}


def main(argv):
    groups = defaultdict(list)
    for argument in argv:
        label, _, folder = argument.partition("=")
        record = json.loads((Path(folder) / "run.json").read_text(encoding="utf-8"))
        groups[label].extend(record["outputs"])
    for label, outputs in sorted(groups.items()):
        print(f"== {label}（出力 {len(outputs)} 件）")
        by_case = defaultdict(list)
        for output in outputs:
            by_case[output["case_id"]].append(output["text"])
        for case, texts in sorted(by_case.items()):
            rules = CHECKS[case]
            missing = sum(any(not re.search(p, t) for p in rules["must"]) for t in texts)
            forbidden = sum(any(re.search(p, t) for p in rules["never"]) for t in texts)
            extra = "".join(f"、{name} {sum(bool(not re.search(p, t)) for t in texts)}" for name, p in RESIDUE.get(case, []))
            print(f"  {case}: {len(texts)} 回のうち、保つべきものが欠けた {missing}、禁止の表現が出た {forbidden}{extra}")


if __name__ == "__main__":
    main(sys.argv[1:])
