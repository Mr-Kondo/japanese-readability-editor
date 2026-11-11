"""#57 E: 太字のラベルを文へ入れる書き換えで、ラベルの語と働きが落ちるかを測る。計画は evals/bold-label.md。

  runner.py            準備（モデル呼び出しなし）
  runner.py --generate 48出力を生成する
  runner.py --count    数える・compare_rewrite で検出を調べる（モデル呼び出しなし）
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import evaluate_readability as evaluation

FOLDER = Path(__file__).resolve().parent
RECORD = FOLDER / "run.json"
PLAN = ROOT / "evals/bold-label.md"
COMPARE = ROOT / "skills/japanese-readability-editor/scripts/compare_rewrite.py"
BOLD = re.compile(r"\*\*([^*\n]+?)\*\*")
COST_CAP = 4.0
REPEATS = 3


def prepare():
    if RECORD.exists():
        raise FileExistsError("existing record must not be overwritten")
    paths = ["skills/japanese-readability-editor/" + name for name in evaluation.FILES]
    if subprocess.check_output(["git", "status", "--porcelain", "--"] + paths, cwd=ROOT, text=True).strip():
        raise ValueError("skill files have uncommitted changes")
    cases = json.loads((FOLDER / "cases.json").read_text(encoding="utf-8"))["cases"]
    snapshot = {name: (evaluation.SKILL / name).read_text(encoding="utf-8") for name in evaluation.FILES}
    evaluation.save_json(RECORD, {
        "status": "prepared", "prepared_at": datetime.now(timezone.utc).isoformat(),
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "cases": cases, "skill_files": snapshot, "skill_sha256": {k: evaluation.digest(v) for k, v in snapshot.items()},
        "flags": evaluation.FLAGS, "system_prompt": evaluation.SYSTEM, "skill_instruction": evaluation.GENERATION,
        "plan_sha256": evaluation.digest(PLAN.read_text(encoding="utf-8")),
        "runner_sha256": evaluation.digest(Path(__file__).read_text(encoding="utf-8")),
        "helper_sha256": evaluation.digest(Path(evaluation.__file__).read_text(encoding="utf-8")),
        "cases_sha256": evaluation.digest((FOLDER / "cases.json").read_text(encoding="utf-8")),
        "outputs": [],
    })


def check_frozen(record):
    for key, path in (("runner_sha256", Path(__file__)), ("helper_sha256", Path(evaluation.__file__)),
                      ("plan_sha256", PLAN), ("cases_sha256", FOLDER / "cases.json")):
        if record[key] != evaluation.digest(path.read_text(encoding="utf-8")):
            raise ValueError(f"{path.name} changed after preparation")


def task(args):
    record, case, repeat, key = args
    request = {k: case[k] for k in ("request", "context", "text")}
    prompt = record["skill_instruction"] + "SKILL_FILES:\n" + json.dumps(record["skill_files"], ensure_ascii=False)
    response = evaluation.invoke(prompt + "\nREQUEST:\n" + json.dumps(request, ensure_ascii=False), FOLDER / (key + ".json"))
    return {"id": key, "case_id": case["id"], "group": case["group"], "repeat": repeat, **response}


def generate(record):
    check_frozen(record)
    if record["outputs"]:
        raise ValueError("already generated; use a new record")
    record["status"] = "running"
    record["cli_version"] = subprocess.check_output(["claude", "--version"], text=True).strip()
    jobs = [(record, case, repeat, f"e{index + 1:03}")
            for index, (repeat, case) in enumerate((r, c) for r in range(1, REPEATS + 1) for c in record["cases"])]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for output in pool.map(task, jobs):
            record["outputs"].append(output)
            evaluation.save_json(RECORD, record)
            print("generated", output["id"], flush=True)
            if sum(o.get("cost_usd") or 0 for o in record["outputs"]) > COST_CAP:
                raise RuntimeError("cost cap exceeded")
    record["status"] = "generated"
    evaluation.save_json(RECORD, record)


def labels(text):
    return [m.strip().rstrip(":：").strip() for m in BOLD.findall(text)]


def detected(before, after, words):
    """compare_rewrite の terms.missing・roles・unmatched.before のいずれかに、ラベルの語を含む項目が現れるか。"""
    with tempfile.TemporaryDirectory(prefix="jre-label-") as tmp:
        (Path(tmp) / "b.md").write_text(before, encoding="utf-8")
        (Path(tmp) / "a.md").write_text(after, encoding="utf-8")
        out = subprocess.run([sys.executable, str(COMPARE), "--json", "b.md", "a.md"], cwd=tmp,
                             capture_output=True, text=True, encoding="utf-8", timeout=60)
    if out.returncode != 0:
        raise RuntimeError(out.stderr)
    data = json.loads(out.stdout)
    shown = json.dumps([data["terms"]["missing"], data["roles"], data["unmatched"]["before"]], ensure_ascii=False)
    return {w: w in shown for w in words}


def count(record):
    cases = {c["id"]: c for c in record["cases"]}
    rows = []
    for output in record["outputs"]:
        case = cases[output["case_id"]]
        before, after = case["text"], output["text"].strip()
        names = labels(before)
        gone = [w for w in names if w not in after]
        row = {"id": output["id"], "case_id": case["id"], "group": case["group"], "repeat": output["repeat"],
               "labels": names, "bold_before": len(BOLD.findall(before)), "bold_after": len(BOLD.findall(after)),
               "folded": len(BOLD.findall(after)) < len(BOLD.findall(before)), "label_words_gone": gone,
               "unchanged": re.sub(r"\s+", "", before) == re.sub(r"\s+", "", after), "after": after}
        if gone:
            row["detected"] = detected(before, after, gone)
        rows.append(row)
    summary = {"models": sorted({m for o in record["outputs"] for m in o.get("model_ids", [])}),
               "cost_usd": round(sum(o.get("cost_usd") or 0 for o in record["outputs"]), 3), "outputs": len(rows)}
    for group in ("target", "redundant"):
        part = [r for r in rows if r["group"] == group]
        summary[group] = {"outputs": len(part), "folded": sum(r["folded"] for r in part),
                          "rewritten": sum(not r["unchanged"] for r in part),
                          "outputs_with_label_word_gone": sum(bool(r["label_words_gone"]) for r in part),
                          "label_words_gone": sum(len(r["label_words_gone"]) for r in part),
                          "gone_and_detected": sum(sum(r["detected"].values()) for r in part if r["label_words_gone"])}
    record["count"] = {"summary": summary, "rows": rows}
    record["status"] = "counted"
    evaluation.save_json(RECORD, record)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print("---", r["id"], r["case_id"], "folded" if r["folded"] else "kept-bold", "gone=", r["label_words_gone"])
        print(r["after"])


def main():
    if "--generate" in sys.argv:
        generate(json.loads(RECORD.read_text(encoding="utf-8")))
    elif "--count" in sys.argv:
        count(json.loads(RECORD.read_text(encoding="utf-8")))
    else:
        prepare()


if __name__ == "__main__":
    main()
