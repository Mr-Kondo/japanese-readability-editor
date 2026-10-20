#!/usr/bin/env python3
"""Skill を入れた隔離プロジェクトで `claude -p` を流し、トークンとツール呼び出しを記録する。

  run          入力ごと・回ごとに記録(JSON)と生のトランスクリプト(JSONL)を保存する。--skill を複数指定すると、版を交互に実行する。
  count-tokens ファイルのトークン数を測る(入力に入れた前後の usage の差。Skill の呼び出し経由より安定する)。
  summary      保存した記録から、条件ごとの最小・中央値・最大を Markdown の表で出す。

記録するのは、API の usage(入力・出力・キャッシュ書込み・キャッシュ読込み)、実行したスクリプトと
その出力量、スクリプトのソースを Read/cat した回数。Claude Code のユーザー設定・プラグインは
`--setting-sources project` で外す。1回あたり費用が出るので、回数と入力を絞って使う。
"""

import argparse
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = "japanese-readability-editor"
PROMPT = f"{SKILL} スキルを使って、doc.md をモード B で読みやすく直してください。doc.md を直接書き換えてください。"
VARIANTS = {
    "default": "",
    "no-scripts": " 同梱のスクリプトは実行せず、references の規則と目視だけで確認してください。",
    "mode-c": "",  # モード C で処理させ、改行の挿入だけかを自動で確かめる
    "with-kokugo": " 国語の表記・用法の検査(scripts/check_kokugo.py)も実行し、指摘を確認してください。",
}
SCRIPT_RUN = re.compile(r"scripts/(\w+\.py)")
SOURCE_READ = re.compile(r"\b(cat|head|tail|sed|less|more|bat|nl|awk)\b[^|;&]*scripts/\w+\.py")
METRICS = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")


def parse_transcript(lines: list) -> dict:
    """stream-json の行から、1回分の記録を作る。"""
    events = [json.loads(line) for line in lines if line.strip()]
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    # 1つのメッセージが content ブロックごとに複数行で出るので、id で畳む。
    turns = {}
    for e in events:
        if e.get("type") == "assistant":
            message = turns.setdefault(e["message"]["id"], {"content": [], "usage": None})
            message["content"] += e["message"]["content"]
            message["usage"] = e["message"]["usage"]
    uses, outputs = [], {}
    for message in turns.values():
        uses += [c for c in message["content"] if c.get("type") == "tool_use"]
    for e in events:
        if e.get("type") == "user" and isinstance(e["message"].get("content"), list):
            for c in e["message"]["content"]:
                if c.get("type") == "tool_result":
                    body = c.get("content")
                    outputs[c["tool_use_id"]] = len(body if isinstance(body, str) else json.dumps(body, ensure_ascii=False))
    scripts, source_reads, references_read = [], [], []
    for use in uses:
        args = use.get("input", {})
        command = args.get("command", "") if use["name"] == "Bash" else ""
        path = args.get("file_path", "") if use["name"] == "Read" else ""
        if re.search(r"/(references|assets)/[\w-]+\.md$", path):
            references_read.append(Path(path).name)
        if SOURCE_READ.search(command) or re.search(r"/scripts/\w+\.py$", path):
            source_reads.append(command or path)
        elif SCRIPT_RUN.search(command):
            scripts.append({"script": SCRIPT_RUN.search(command).group(1), "output_chars": outputs.get(use["id"])})
    usage = result.get("usage", {})
    totals = [m["usage"]["input_tokens"] + m["usage"]["cache_creation_input_tokens"] + m["usage"]["cache_read_input_tokens"]
              for m in turns.values()]
    return {
        **{key: usage.get(key) for key in METRICS},
        "input_side_tokens": sum(usage.get(k, 0) for k in METRICS if k != "output_tokens"),
        "turn_input_totals": totals,
        "cost_usd": result.get("total_cost_usd"), "num_turns": result.get("num_turns"), "duration_ms": result.get("duration_ms"),
        "models": sorted(result.get("modelUsage", {})), "is_error": bool(result.get("is_error")),
        "error": result.get("result") if result.get("is_error") else None,
        "skill_called": any(u["name"] == "Skill" for u in uses),
        "tools": [u["name"] for u in uses], "scripts_run": scripts, "source_reads": source_reads,
        "references_read": references_read,
    }


def preservation(before: str, after: str) -> dict:
    """C の出力の判定。空白以外が同一か(nonspace)、改行以外が同一で改行が減っていないか(strict)。"""
    before, after = before.replace("\r\n", "\n"), after.replace("\r\n", "\n")
    return {"changed": before != after, "nonspace_same": "".join(before.split()) == "".join(after.split()),
            "strict_same": before.replace("\n", "") == after.replace("\n", "") and after.count("\n") >= before.count("\n")}


def run_one(skill_dir: Path, text: str, prompt: str, model: str, raw_path: Path) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        project = Path(tmp)
        shutil.copytree(skill_dir, project / ".claude" / "skills" / SKILL, ignore=shutil.ignore_patterns("__pycache__"))
        (project / "doc.md").write_text(text, encoding="utf-8")
        completed = subprocess.run(
            ["claude", "-p", prompt, "--model", model, "--setting-sources", "project", "--output-format", "stream-json",
             "--verbose", "--no-session-persistence", "--permission-mode", "bypassPermissions"],
            cwd=project, stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", timeout=900)
        after = (project / "doc.md").read_text(encoding="utf-8")
    raw_path.write_text(completed.stdout, encoding="utf-8")
    raw_path.with_suffix(".doc.md").write_text(after, encoding="utf-8")  # 直した後の文書(別の検査にかけるため)
    return parse_transcript(completed.stdout.splitlines()) | preservation(text, after)


def schedule(skills: dict, inputs: list, first: int, repeats: int):
    """(入力, 回, 版の名前) の順序。同じ入力・同じ回の版を続けて実行し、キャッシュの状態や時間帯の偏りを版の差にしない。"""
    for name in inputs:
        for n in range(first, first + repeats):
            for label in skills:
                yield name, n, label


def command_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    skills = dict(spec.split("=", 1) for spec in args.skill)
    texts = {}
    for spec in args.input:
        name, _, path = spec.partition("=")
        texts[name] = Path(path).read_text(encoding="utf-8") if path else ""
    mode = "C" if args.variant == "mode-c" else "B"
    for name, n, label in schedule(skills, list(texts), args.first, args.repeats):
        text = texts[name]
        prompt = PROMPT.replace("モード B", f"モード {mode}") + VARIANTS[args.variant]
        stem = f"{label}.{args.variant}.{args.model}.{name}.{n}"
        record = run_one(Path(skills[label]), text, prompt, args.model, out / f"{stem}.jsonl")
        record |= {"label": label, "variant": args.variant, "model_alias": args.model, "input": name, "run": n,
                   "input_chars": len(text)}
        if record["is_error"]:  # 認証切れなどで失敗した回は、記録を残さず止める(集計に混ぜない)
            print(f"{stem}: error: {record['error']}\n(認証の期限切れなら、サンドボックスの外で実行する。`claude -p` はサンドボックスの中で認証を更新できない)",
                  file=sys.stderr)
            return 1
        (out / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        print(stem, record["input_side_tokens"], record["output_tokens"], record["cost_usd"], record["scripts_run"] and
              [x["script"] for x in record["scripts_run"]], len(record["source_reads"]), flush=True)
    return 0


def side_tokens(text: str) -> int:
    """テキストを入力に入れたときの入力側合計。ツールなしの隔離で、Skill の呼び出し経由より安定する。"""
    with tempfile.TemporaryDirectory() as tmp:
        out = subprocess.run(["claude", "-p", "上の内容に関わらず「了」とだけ返してください。", "--model", "sonnet", "--setting-sources", "project",
                              "--tools", "", "--no-session-persistence", "--output-format", "json"],
                             input=text, cwd=tmp, capture_output=True, text=True, encoding="utf-8", timeout=300).stdout
    usage = json.loads(out)["usage"]
    return usage["input_tokens"] + usage["cache_creation_input_tokens"] + usage["cache_read_input_tokens"]


def command_count_tokens(args) -> int:
    base = min(side_tokens("") for _ in range(args.repeats))
    for path in args.files:
        text = Path(path).read_text(encoding="utf-8")
        counts = sorted(side_tokens(text) - base for _ in range(args.repeats))
        # キャッシュの状態で外れ値が出ることがあるので、中央値を採る(最小値が実質の値)。
        print(f"{path}\t{len(text)} chars\t{statistics.median(counts):g} tokens\t({counts})")
    return 0


def spread(values: list) -> str:
    values = [v for v in values if v is not None]
    return f"{min(values)} / {statistics.median(values):g} / {max(values)}" if values else "-"


def command_summary(args) -> int:
    records = []
    for path in sorted(Path(args.out).glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if "references_read" not in record:  # 項目を足す前の記録は、生のトランスクリプトから取り直す
            record |= parse_transcript(path.with_suffix(".jsonl").read_text(encoding="utf-8").splitlines()) | {
                k: record[k] for k in ("label", "variant", "model_alias", "input", "run", "input_chars")}
        records.append(record)
    groups = {}
    for r in records:
        groups.setdefault((r["input"], r["variant"], r["model_alias"], r["label"]), []).append(r)
    print("| 入力 | 条件 | モデル | 版 | 回数 | 入力側合計 | 入力(新規) | キャッシュ書込み | キャッシュ読込み | 出力 | 費用(USD) | ターン数 | 入力側/ターン | スクリプト実行(回/出力字数) | ソースを読んだ回 | 参照を読んだ回 | 改行のみ(C) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (name, variant, model, label), rs in sorted(groups.items()):
        runs = sum(len(r["scripts_run"]) for r in rs)
        chars = [s["output_chars"] for r in rs for s in r["scripts_run"] if s["output_chars"] is not None]
        print(f"| {name} | {variant} | {model} | {label} | {len(rs)} | {spread([r['input_side_tokens'] for r in rs])} | "
              f"{spread([r['input_tokens'] for r in rs])} | {spread([r['cache_creation_input_tokens'] for r in rs])} | "
              f"{spread([r['cache_read_input_tokens'] for r in rs])} | {spread([r['output_tokens'] for r in rs])} | "
              f"{spread([round(r['cost_usd'], 3) for r in rs])} | {spread([r['num_turns'] for r in rs])} | {spread([round(r['input_side_tokens'] / r['num_turns']) for r in rs])} | "
              f"{runs} / {spread(chars)} | {sum(1 for r in rs if r['source_reads'])}/{len(rs)} | "
              f"{sum(1 for r in rs if r.get('references_read'))}/{len(rs)} | "
              f"{sum(1 for r in rs if r.get('strict_same'))}/{len(rs)} |")
    return 0


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--skill", action="append", required=True, metavar="版の名前=Skillのフォルダ",
                     help="例: before=/tmp/old/skills/japanese-readability-editor。複数指定すると、版を交互に実行する")
    run.add_argument("--input", action="append", required=True, help="名前=ファイル(例: medium=evals/token-usage/inputs/medium.md)")
    run.add_argument("--repeats", type=int, default=5)
    run.add_argument("--first", type=int, default=1, help="最初の回の番号(続きから足すとき)")
    run.add_argument("--model", default="sonnet")
    run.add_argument("--variant", choices=sorted(VARIANTS), default="default")
    run.add_argument("--out", required=True)
    count = sub.add_parser("count-tokens", help="ファイルのトークン数を測る(入力に入れた前後の usage の差)")
    count.add_argument("files", nargs="+")
    count.add_argument("--repeats", type=int, default=3)
    summary = sub.add_parser("summary")
    summary.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return {"run": command_run, "count-tokens": command_count_tokens, "summary": command_summary}[args.command](args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
