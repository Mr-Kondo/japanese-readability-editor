#!/usr/bin/env python3
"""Skill を入れた隔離プロジェクトで `claude -p` を流し、トークンとツール呼び出しを記録する。

  run     入力ごと・回ごとに記録(JSON)と生のトランスクリプト(JSONL)を保存する。
  summary 保存した記録から、条件ごとの最小・中央値・最大を Markdown の表で出す。

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
# skill 本文のトークン数を、他の作業を混ぜずに測る入力。
PROBE_PROMPT = f"{SKILL} スキルを起動し、ほかには何もせず「了」とだけ返してください。"
PROMPT = f"{SKILL} スキルを使って、doc.md をモード B で読みやすく直してください。doc.md を直接書き換えてください。"
VARIANTS = {
    "default": "",
    "no-scripts": " 同梱のスクリプトは実行せず、references の規則と目視だけで確認してください。",
    "mode-c": "",  # モード C で処理させ、改行の挿入だけかを自動で確かめる
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
    return parse_transcript(completed.stdout.splitlines()) | preservation(text, after)


def command_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for spec in args.input:
        name, _, path = spec.partition("=")
        text = Path(path).read_text(encoding="utf-8") if path else ""
        mode = "C" if args.variant == "mode-c" else "B"
        prompt = PROBE_PROMPT if name == "probe" else PROMPT.replace("モード B", f"モード {mode}") + VARIANTS[args.variant]
        for n in range(args.first, args.first + args.repeats):
            stem = f"{args.label}.{args.variant}.{args.model}.{name}.{n}"
            record = run_one(Path(args.skill_dir), text, prompt, args.model, out / f"{stem}.jsonl")
            record |= {"label": args.label, "variant": args.variant, "model_alias": args.model, "input": name, "run": n,
                       "input_chars": len(text)}
            if record["is_error"]:  # 認証切れなどで失敗した回は、記録を残さず止める(集計に混ぜない)
                print(f"{stem}: error; see {out / (stem + '.jsonl')}", file=sys.stderr)
                return 1
            (out / f"{stem}.json").write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            print(stem, record["input_side_tokens"], record["output_tokens"], record["cost_usd"], record["scripts_run"] and
                  [s["script"] for s in record["scripts_run"]], len(record["source_reads"]), flush=True)
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
    print("| 入力 | 条件 | モデル | 版 | 回数 | 入力側合計 | 入力(新規) | キャッシュ書込み | キャッシュ読込み | 出力 | 費用(USD) | ターン数 | スクリプト実行(回/出力字数) | ソースを読んだ回 | 参照を読んだ回 | 改行のみ(C) |")
    print("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for (name, variant, model, label), rs in sorted(groups.items()):
        runs = sum(len(r["scripts_run"]) for r in rs)
        chars = [s["output_chars"] for r in rs for s in r["scripts_run"] if s["output_chars"] is not None]
        print(f"| {name} | {variant} | {model} | {label} | {len(rs)} | {spread([r['input_side_tokens'] for r in rs])} | "
              f"{spread([r['input_tokens'] for r in rs])} | {spread([r['cache_creation_input_tokens'] for r in rs])} | "
              f"{spread([r['cache_read_input_tokens'] for r in rs])} | {spread([r['output_tokens'] for r in rs])} | "
              f"{spread([round(r['cost_usd'], 3) for r in rs])} | {spread([r['num_turns'] for r in rs])} | "
              f"{runs} / {spread(chars)} | {sum(1 for r in rs if r['source_reads'])}/{len(rs)} | "
              f"{sum(1 for r in rs if r.get('references_read'))}/{len(rs)} | "
              f"{sum(1 for r in rs if r.get('strict_same'))}/{len(rs)} |")
    probes = [r for r in records if r["input"] == "probe"]
    for label in sorted({r["label"] for r in probes}):
        deltas = [r["turn_input_totals"][-1] - r["turn_input_totals"][0] for r in probes if r["label"] == label]
        print(f"\nSKILL.md 読み込みによる入力の増分(probe, {label}): {spread(deltas)} トークン(最小 / 中央値 / 最大)")
    return 0


def main(argv: list) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--skill-dir", required=True)
    run.add_argument("--label", required=True, help="版の名前(before / after)")
    run.add_argument("--input", action="append", required=True, help="名前=ファイル。名前 probe はファイル不要(例: probe)")
    run.add_argument("--repeats", type=int, default=5)
    run.add_argument("--first", type=int, default=1, help="最初の回の番号(続きから足すとき)")
    run.add_argument("--model", default="sonnet")
    run.add_argument("--variant", choices=sorted(VARIANTS), default="default")
    run.add_argument("--out", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    return command_run(args) if args.command == "run" else command_summary(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
