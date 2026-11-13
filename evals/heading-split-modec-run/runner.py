"""#174 の2回目: モード C(h08)だけを測り直す。計画は evals/heading-split-modec.md。

  runner.py            準備（モデル呼び出しなし）。入力と両版の全文は、1回目の run.json から取る
  runner.py --generate 6出力を生成する
  runner.py --count    数える（モデル呼び出しなし）
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import evaluate_readability as evaluation

FOLDER = Path(__file__).resolve().parent
RECORD = FOLDER / "run.json"
SOURCE = ROOT / "evals/heading-split-run/run.json"
PLAN = ROOT / "evals/heading-split-modec.md"
VERSIONS = ("base", "cand")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.M)
LAST_SENTENCE = "交換は、2年に1回の目安である。"
COST_CAP = 1.5
REPEATS = 3


def compact(text):
    return re.sub(r"\s+", "", text)


def prepare():
    if RECORD.exists():
        raise FileExistsError("existing record must not be overwritten")
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    cases = [c for c in source["cases"] if c["id"] == "h08"]
    if len(cases) != 1 or LAST_SENTENCE not in cases[0]["text"]:
        raise ValueError("h08 not found")
    evaluation.save_json(RECORD, {
        "status": "prepared", "prepared_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": evaluation.digest(SOURCE.read_text(encoding="utf-8")),
        "cases": cases, "skill_files": source["skill_files"], "skill_sha256": source["skill_sha256"],
        "flags": evaluation.FLAGS, "system_prompt": evaluation.SYSTEM, "skill_instruction": evaluation.GENERATION,
        "plan_sha256": evaluation.digest(PLAN.read_text(encoding="utf-8")),
        "runner_sha256": evaluation.digest(Path(__file__).read_text(encoding="utf-8")),
        "helper_sha256": evaluation.digest(Path(evaluation.__file__).read_text(encoding="utf-8")),
        "outputs": [],
    })


def check_frozen(record):
    source = SOURCE.read_text(encoding="utf-8")
    for key, text in (("source_sha256", source), ("runner_sha256", Path(__file__).read_text(encoding="utf-8")),
                      ("helper_sha256", Path(evaluation.__file__).read_text(encoding="utf-8")),
                      ("plan_sha256", PLAN.read_text(encoding="utf-8"))):
        if record[key] != evaluation.digest(text):
            raise ValueError(f"{key} changed after preparation")


def task(args):
    record, case, version, repeat, key = args
    request = {k: case[k] for k in ("request", "context", "text")}
    prompt = record["skill_instruction"] + "SKILL_FILES:\n" + json.dumps(record["skill_files"][version], ensure_ascii=False)
    response = evaluation.invoke(prompt + "\nREQUEST:\n" + json.dumps(request, ensure_ascii=False), FOLDER / (key + ".json"))
    return {"id": key, "case_id": case["id"], "version": version, "repeat": repeat, **response}


def generate(record):
    check_frozen(record)
    if record["outputs"]:
        raise ValueError("already generated; use a new record")
    record["status"] = "running"
    record["cli_version"] = subprocess.check_output(["claude", "--version"], text=True).strip()
    jobs = [(record, c, v, r, f"m{i + 1:03}") for i, (c, v, r) in
            enumerate((c, v, r) for r in range(1, REPEATS + 1) for c in record["cases"] for v in VERSIONS)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for output in pool.map(task, jobs):
            record["outputs"].append(output)
            evaluation.save_json(RECORD, record)
            print("generated", output["id"], flush=True)
            if sum(o.get("cost_usd") or 0 for o in record["outputs"]) > COST_CAP:
                raise RuntimeError("cost cap exceeded")
    record["status"] = "generated"
    evaluation.save_json(RECORD, record)


def count(record):
    case = record["cases"][0]
    before = case["text"]
    rows = []
    for output in record["outputs"]:
        after = output["text"].strip()
        tail_at = after.rfind(LAST_SENTENCE)
        rows.append({
            "id": output["id"], "version": output["version"], "repeat": output["repeat"],
            "headings_unchanged": HEADING.findall(after) == HEADING.findall(before),
            "starts_with_input": compact(after).startswith(compact(before)),
            "tail": after[tail_at + len(LAST_SENTENCE):].strip() if tail_at >= 0 else None, "after": after})
    summary = {"models": sorted({m for o in record["outputs"] for m in o.get("model_ids", [])}),
               "cost_usd": round(sum(o.get("cost_usd") or 0 for o in record["outputs"]), 3), "outputs": len(rows)}
    for version in VERSIONS:
        mine = [r for r in rows if r["version"] == version]
        summary[version] = {"outputs": len(mine), "headings_unchanged": sum(r["headings_unchanged"] for r in mine),
                            "starts_with_input": sum(r["starts_with_input"] for r in mine),
                            "with_tail": sum(bool(r["tail"]) for r in mine)}
    record["count"] = {"summary": summary, "rows": rows}
    record["status"] = "counted"
    evaluation.save_json(RECORD, record)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print("---", r["id"], r["version"], r["repeat"], "headings_unchanged=", r["headings_unchanged"],
              "starts_with_input=", r["starts_with_input"])
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
