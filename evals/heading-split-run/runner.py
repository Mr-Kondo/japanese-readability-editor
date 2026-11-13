"""#174: 独立した話題を並べた見出しを、本文が別々なら分ける規則を、旧版と新版で比べる。計画は evals/heading-split.md。

  runner.py            準備（モデル呼び出しなし）。旧版は BASE のコミット、新版は作業ツリー（コミット済み）のスキル3ファイル
  runner.py --generate 54出力を生成する
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
PLAN = ROOT / "evals/heading-split.md"
BASE = "82d81ad2fb1c9ea853c7890fba2d803f9c8691fe"
VERSIONS = ("base", "cand")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.M)
NUMBER = re.compile(r"^(\d+)\.\s")
COST_CAP = 5.0
REPEATS = 3


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True)


def prepare():
    if RECORD.exists():
        raise FileExistsError("existing record must not be overwritten")
    paths = ["skills/japanese-readability-editor/" + name for name in evaluation.FILES]
    if git("status", "--porcelain", "--", *paths).strip():
        raise ValueError("skill files have uncommitted changes")
    cases = json.loads((FOLDER / "cases.json").read_text(encoding="utf-8"))["cases"]
    files = {
        "base": {name: git("show", f"{BASE}:skills/japanese-readability-editor/{name}") for name in evaluation.FILES},
        "cand": {name: (evaluation.SKILL / name).read_text(encoding="utf-8") for name in evaluation.FILES},
    }
    if files["base"] == files["cand"]:
        raise ValueError("candidate equals base")
    evaluation.save_json(RECORD, {
        "status": "prepared", "prepared_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": BASE, "commit": git("rev-parse", "HEAD").strip(),
        "cases": cases, "skill_files": files,
        "skill_sha256": {v: {k: evaluation.digest(t) for k, t in files[v].items()} for v in VERSIONS},
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
    record, case, version, repeat, key = args
    request = {k: case[k] for k in ("request", "context", "text")}
    prompt = record["skill_instruction"] + "SKILL_FILES:\n" + json.dumps(record["skill_files"][version], ensure_ascii=False)
    response = evaluation.invoke(prompt + "\nREQUEST:\n" + json.dumps(request, ensure_ascii=False), FOLDER / (key + ".json"))
    return {"id": key, "case_id": case["id"], "group": case["group"], "version": version, "repeat": repeat, **response}


def generate(record):
    check_frozen(record)
    if record["outputs"]:
        raise ValueError("already generated; use a new record")
    record["status"] = "running"
    record["cli_version"] = subprocess.check_output(["claude", "--version"], text=True).strip()
    combos = [(c, v, r) for r in range(1, REPEATS + 1) for c in record["cases"] for v in VERSIONS]
    jobs = [(record, c, v, r, f"e{i + 1:03}") for i, (c, v, r) in enumerate(combos)]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for output in pool.map(task, jobs):
            record["outputs"].append(output)
            evaluation.save_json(RECORD, record)
            print("generated", output["id"], flush=True)
            if sum(o.get("cost_usd") or 0 for o in record["outputs"]) > COST_CAP:
                raise RuntimeError("cost cap exceeded")
    record["status"] = "generated"
    evaluation.save_json(RECORD, record)


def headings(text):
    return HEADING.findall(text)


def heading_state(found, topics):
    """分けた: 2つの話題がそれぞれ別の見出しにあり、両方を含む見出しがない。残した: 両方を含む見出しがあり、別々の見出しがない。"""
    a, b = topics
    both = any(a in h and b in h for h in found)
    apart = any(a in h and b not in h for h in found) and any(b in h and a not in h for h in found)
    return "split" if apart and not both else "kept" if both and not apart else "other"


def numbering_ok(found):
    numbers = [int(m.group(1)) for h in found if (m := NUMBER.match(h))]
    return numbers == list(range(1, len(numbers) + 1)) if numbers else None


def count(record):
    cases = {c["id"]: c for c in record["cases"]}
    rows = []
    for output in record["outputs"]:
        case = cases[output["case_id"]]
        before, after = case["text"], output["text"].strip()
        found = headings(after)
        compact = lambda s: re.sub(r"\s+", "", s)
        rows.append({
            "id": output["id"], "case_id": case["id"], "group": case["group"], "version": output["version"],
            "repeat": output["repeat"], "headings": found, "state": heading_state(found, case["topics"]),
            "headings_unchanged": found == headings(before), "numbering_ok": numbering_ok(found),
            "keep_missing": [t for t in case["keep"] if t not in after],
            "chars_unchanged": compact(before) == compact(after), "after": after})
    summary = {"models": sorted({m for o in record["outputs"] for m in o.get("model_ids", [])}),
               "cost_usd": round(sum(o.get("cost_usd") or 0 for o in record["outputs"]), 3), "outputs": len(rows)}
    for version in VERSIONS:
        mine = [r for r in rows if r["version"] == version]
        by = lambda group: [r for r in mine if r["group"] == group]
        summary[version] = {
            "split_group_split": sum(r["state"] == "split" for r in by("split")), "split_group_outputs": len(by("split")),
            "split_group_numbering_ok": sum(r["numbering_ok"] is True for r in by("split") if r["case_id"] == "h02"),
            "keep_body_split": sum(r["state"] == "split" for r in by("keep_body")), "keep_body_outputs": len(by("keep_body")),
            "request_headings_unchanged": sum(r["headings_unchanged"] for r in by("request")), "request_outputs": len(by("request")),
            "modec_chars_unchanged": sum(r["chars_unchanged"] for r in mine if r["case_id"] == "h08"),
            "vague_split": sum(r["state"] == "split" for r in by("vague")), "vague_outputs": len(by("vague")),
            "outputs_with_keep_missing": sum(bool(r["keep_missing"]) for r in mine)}
    record["count"] = {"summary": summary, "rows": rows}
    record["status"] = "counted"
    evaluation.save_json(RECORD, record)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    for r in rows:
        print("---", r["id"], r["case_id"], r["version"], r["state"], "keep_missing=", r["keep_missing"],
              "headings=", r["headings"])
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
