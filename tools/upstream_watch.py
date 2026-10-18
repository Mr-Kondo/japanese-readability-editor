#!/usr/bin/env python3
"""参考にしたリポジトリの更新を確認する開発用ツール。ネットワークを使う(gh api)。配布物(ZIP)には入らない。

    upstream_watch.py check   [--only ID ...] [--json FILE]             各参考先の更新を調べる(読み取りのみ)
    upstream_watch.py notify  --report FILE [--repo OWNER/NAME] [--execute]   更新のあった参考先の追跡 Issue を作る
    upstream_watch.py mark-reviewed ID --ref REF --review FILE           解析を終えた基準を記録する
    upstream_watch.py add ID (--repo OWNER/NAME | --gist GIST_ID) --role ROLE [--paths GLOB ...] [--at ISO | --sha SHA]
                                                                         参考先を登録する(ライセンスと基準を取得して書く)

共通: --sources F (既定 docs/upstream/sources.json)。登録簿の形と運用は docs/upstream-watch.md にある。

守ること:
  - check は読み取りのみ。取得に失敗した参考先を「更新なし」にしない(status=error、終了コード 2)。
  - 更新は、確認済みの基準(sha)以降に、新しいリリース、監視パスの変更、ライセンスの変更があるときだけ数える。
  - 追跡 Issue には構造化した事実(id、タグ、sha、日付、パス、件数、組み立てた URL)だけを書く。上流のコミットメッセージ・
    リリース本文・ファイルの中身は、外部の入力なので転記しない。パスなどの文字列は、制御文字と双方向制御文字を除いて長さを制限する。
  - notify は --execute を付けたときだけ作る。同じ参考先の未完了の追跡 Issue(ラベル upstream)があれば作らない。
  - mark-reviewed は、確認の記録(ファイル)が実在し、その基準に触れているときだけ基準を進める。
終了コード: 0=完了、2=エラー(取得の失敗、基準の消失、登録簿の誤りを含む)。
"""
from __future__ import annotations

import argparse
import datetime
import fnmatch
import json
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCES = ROOT / "docs" / "upstream" / "sources.json"

ROLES = ("rule-source", "fiction-source", "reference", "host-docs")
KINDS = ("repo", "gist")
SCHEMA_VERSION = 1
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,39}")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
GIST_RE = re.compile(r"[0-9a-f]{20,40}")
SHA_RE = re.compile(r"[0-9a-f]{40}")
AT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
CONTROL_RE = re.compile("[\x00-\x1f\x7f-\x9f  ‪-‮⁦-⁩]")
COMPARE_FILE_CAP, COMPARE_COMMIT_CAP = 300, 250  # ページ指定なしの compare が返す上限
ISSUE_FILE_LIMIT = 30
MAX_PATH_QUERIES = 60  # 大きな差の調べ直しで、1つの参考先に使う問い合わせの上限
LABEL = "upstream"
MAX_REVIEW_BYTES = 1_000_000


class RegistryError(ValueError):
    """登録簿の形の誤り。"""


class ApiError(Exception):
    def __init__(self, status, message, rate_limited=False):
        super().__init__(message)
        self.status, self.rate_limited = status, rate_limited


def clean(text, limit: int = 200) -> str:
    """外部由来の文字列を、Issue やログに書ける形にする(制御文字・双方向制御文字・表を壊す記号を除き、長さを制限する)。"""
    text = CONTROL_RE.sub("?", str(text)).replace("`", "'").replace("|", "/")
    return text if len(text) <= limit else text[:limit] + "…"


def utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---- 登録簿 ----------------------------------------------------------------

def checked_source(entry, seen: set) -> dict:
    def need(condition, message):
        if not condition:
            raise RegistryError(f"{entry.get('id', '?') if isinstance(entry, dict) else '?'}: {message}")

    need(isinstance(entry, dict), "登録は対象(オブジェクト)であること")
    need(isinstance(entry.get("id"), str) and ID_RE.fullmatch(entry["id"]), "id は英小文字・数字・ハイフンの40字以内")
    need(entry["id"] not in seen, "id が重複している")
    seen.add(entry["id"])
    need(entry.get("kind") in KINDS, f"kind は {KINDS} のどれか")
    if entry["kind"] == "repo":
        need(isinstance(entry.get("repo"), str) and REPO_RE.fullmatch(entry["repo"]), "repo は OWNER/NAME の形")
    else:
        need(isinstance(entry.get("gist"), str) and GIST_RE.fullmatch(entry["gist"]), "gist は16進の ID")
    need(entry.get("role") in ROLES, f"role は {ROLES} のどれか")
    license_ = entry.get("license")
    need(isinstance(license_, dict) and isinstance(license_.get("spdx"), str) and license_["spdx"],
         "license.spdx が要る(無いときは none)")
    watch = entry.get("watch")
    need(isinstance(watch, dict) and isinstance(watch.get("enabled"), bool), "watch.enabled が要る")
    need(isinstance(watch.get("paths", []), list) and all(isinstance(p, str) for p in watch.get("paths", [])),
         "watch.paths は文字列の一覧")
    need(isinstance(watch.get("releases", True), bool), "watch.releases は真偽値")
    reviewed = entry.get("reviewed")
    if reviewed is not None:
        need(isinstance(reviewed, dict), "reviewed は対象(オブジェクト)")
        need(isinstance(reviewed.get("ref"), str) and 0 < len(reviewed["ref"]) <= 100, "reviewed.ref が要る")
        need(isinstance(reviewed.get("sha"), str) and SHA_RE.fullmatch(reviewed["sha"]), "reviewed.sha は40桁の16進")
        need(isinstance(reviewed.get("at"), str) and AT_RE.fullmatch(reviewed["at"]), "reviewed.at は YYYY-MM-DDTHH:MM:SSZ")
        need(reviewed.get("review") is None or isinstance(reviewed["review"], str), "reviewed.review は文字列か null")
    need(not watch["enabled"] or reviewed is not None, "監視する参考先には reviewed(基準)が要る")
    need(isinstance(entry.get("adopted", []), list), "adopted は一覧")
    need(isinstance(entry.get("not_adopted", []), list), "not_adopted は一覧")
    return entry


def load_registry(path: Path) -> dict:
    try:
        registry = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RegistryError(f"登録簿を読めない: {path}: {exc}") from exc
    if not isinstance(registry, dict) or registry.get("schema_version") != SCHEMA_VERSION:
        raise RegistryError(f"schema_version が {SCHEMA_VERSION} ではない")
    sources = registry.get("sources")
    if not isinstance(sources, list):
        raise RegistryError("sources が一覧ではない")
    seen: set = set()
    for entry in sources:
        checked_source(entry, seen)
    return registry


def save_registry(path: Path, registry: dict) -> None:
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def find_source(registry: dict, source_id: str) -> dict:
    for entry in registry["sources"]:
        if entry["id"] == source_id:
            return entry
    raise RegistryError(f"登録にない id: {source_id}")


# ---- GitHub への問い合わせ ---------------------------------------------------

class GhApi:
    """`gh api` を呼ぶ。5xx と通信の失敗は少し待って再試行し、API の上限と 404 は再試行しない。"""

    def __init__(self, run=subprocess.run, sleep=time.sleep, retries: int = 2):
        self.run, self.sleep, self.retries = run, sleep, retries

    def get(self, path: str):
        command = ["gh", "api", "-H", "Accept: application/vnd.github+json", path]
        for attempt in range(self.retries + 1):
            try:
                done = self.run(command, capture_output=True, text=True, encoding="utf-8", timeout=90)
            except FileNotFoundError as exc:
                raise ApiError(None, "gh が見つからない(GitHub CLI を入れる)") from exc
            except subprocess.TimeoutExpired:
                done = None
            if done is not None and done.returncode == 0:
                try:
                    return json.loads(done.stdout)
                except ValueError as exc:
                    raise ApiError(None, f"JSON ではない応答: {clean(path)}") from exc
            error = done.stderr if done is not None else "timeout"
            match = re.search(r"HTTP (\d{3})", error)
            status = int(match.group(1)) if match else None
            if status in (403, 429) and "rate limit" in error.lower():
                raise ApiError(status, "API の上限に達した", rate_limited=True)
            if status is not None and status < 500:
                raise ApiError(status, f"{clean(path)}: HTTP {status}")
            if attempt < self.retries:
                self.sleep(2 * (attempt + 1))
        raise ApiError(status, f"{clean(path)}: 取得に失敗した")


def quote(text: str) -> str:
    return urllib.parse.quote(text, safe="/")


def relevant(path: str, patterns: list) -> bool:
    return not patterns or any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def touches(entry: dict, patterns: list) -> bool:
    """変更されたファイル(改名なら元の名前も)が、監視パスに当たるか。"""
    return relevant(entry["filename"], patterns) or bool(entry.get("previous_filename")) and relevant(entry["previous_filename"], patterns)


def license_name(meta: dict) -> str:
    return ((meta.get("license") or {}).get("spdx_id") or "none")


# ---- check -----------------------------------------------------------------

def changed_since(repo: str, branch: str, head_sha: str, patterns: list, at: str, api):
    """compare が切れる大きな差で、監視パスに当たるファイルのうち、時刻 at 以降に変更されたものを返す。決められなければ None。

    shortcut: 先頭に残るファイルだけを調べる(基準のあとに消えたファイルは見ない)。パターンが空、ファイルが多すぎる、
    木が切れているときは None を返し、呼び出し側が truncated として報告する。
    """
    if not patterns:
        return None
    tree = api.get(f"repos/{repo}/git/trees/{head_sha}?recursive=1")
    if tree.get("truncated"):
        return None
    paths = [e["path"] for e in tree.get("tree", []) if e.get("type") == "blob" and relevant(e["path"], patterns)]
    if len(paths) > MAX_PATH_QUERIES:
        return None
    changed = []
    for path in paths:
        commits = api.get(f"repos/{repo}/commits?sha={quote(branch)}&path={quote(path)}&since={at}&per_page=1")
        if commits:
            changed.append(path)
    return changed


def inspect_repo(source: dict, api, result: dict) -> None:
    repo, reviewed = source["repo"], source["reviewed"]
    meta = api.get(f"repos/{repo}")
    if str(meta.get("full_name", repo)).lower() != repo.lower():
        result["warnings"].append(f"改名された: {clean(repo)} → {clean(meta['full_name'])}(登録簿の repo を直す)")
    if meta.get("archived"):
        result["warnings"].append("アーカイブされている")
    now_license = license_name(meta)
    result["license"] = {"recorded": source["license"]["spdx"], "now": clean(now_license, 40)}
    if now_license.lower() != source["license"]["spdx"].lower():
        result["reasons"].append("license_changed")
    head = api.get(f"repos/{repo}/commits/{quote(meta['default_branch'])}")
    result["head"] = {"sha": head["sha"], "date": clean(head["commit"]["committer"]["date"], 40)}
    if head["sha"] != reviewed["sha"]:
        try:
            comparison = api.get(f"repos/{repo}/compare/{reviewed['sha']}...{head['sha']}")
        except ApiError as exc:
            if exc.status != 404:
                raise
            result["status"] = "baseline_missing"
            result["error"] = "確認済みの基準のコミットが見つからない(履歴の書き換えか、削除)"
            return
        files = comparison.get("files") or []
        result["ahead_by"] = int(comparison.get("ahead_by", 0))
        patterns = source["watch"].get("paths", [])
        names = [f["filename"] for f in files if touches(f, patterns)]
        if len(files) >= COMPARE_FILE_CAP or result["ahead_by"] > COMPARE_COMMIT_CAP:
            # compare が切れる(大きな差)ときは、監視パスに当たるファイルを1つずつ、基準の時刻以降の変更で調べ直す。
            result["truncated"] = True
            narrowed = changed_since(repo, meta["default_branch"], head["sha"], patterns, reviewed["at"], api)
            if narrowed is None:
                result["reasons"].append("truncated")
            else:
                names = narrowed
        result["relevant_files"] = [clean(name) for name in names]
        result["relevant_count"] = len(names)
        if names:
            result["reasons"].append("relevant_files")
        result["compare_url"] = f"https://github.com/{repo}/compare/{reviewed['sha'][:12]}...{head['sha'][:12]}"
    releases = api.get(f"repos/{repo}/releases?per_page=30")
    listed = [r for r in releases if isinstance(r, dict) and not r.get("draft")]
    stable = [r for r in listed if not r.get("prerelease")]
    if stable:
        result["latest_release"] = {"tag": clean(stable[0]["tag_name"], 80), "published": clean(stable[0]["published_at"], 40)}
    fresh = [r for r in listed if str(r.get("published_at", "")) > reviewed["at"] and not included(repo, reviewed["sha"], r, api)]
    result["new_releases"] = [{"tag": clean(r["tag_name"], 80), "published": clean(r["published_at"], 40)} for r in fresh]
    if fresh and source["watch"].get("releases", True):  # リリースが頻繁な参考先は、監視パスの変更だけで数える
        result["reasons"].append("new_release")


def included(repo: str, base_sha: str, release: dict, api) -> bool:
    """リリースのタグが、基準のコミットに含まれる(基準の時点ですでに出ていた内容)なら True。"""
    try:
        comparison = api.get(f"repos/{repo}/compare/{base_sha}...{quote(str(release['tag_name']))}")
    except ApiError as exc:
        if exc.status == 404:
            return False
        raise
    return int(comparison.get("ahead_by", 1)) == 0


def inspect_gist(source: dict, api, result: dict) -> None:
    reviewed = source["reviewed"]
    gist = api.get(f"gists/{source['gist']}")
    history = gist.get("history") or []
    if not history:
        raise ApiError(None, "Gist に履歴がない")
    head = history[0]
    result["head"] = {"sha": head["version"], "date": clean(head.get("committed_at", ""), 40)}
    owner = clean((gist.get("owner") or {}).get("login", "") or "", 40)
    result["compare_url"] = f"https://gist.github.com/{owner}/{source['gist']}/revisions"
    if head["version"] != reviewed["sha"]:
        names = [name for name in (gist.get("files") or {}) if relevant(name, source["watch"].get("paths", []))]
        result["relevant_files"], result["relevant_count"] = [clean(n) for n in names], len(names)
        result["reasons"].append("gist_updated")


def check_source(source: dict, api) -> dict:
    result = {"id": source["id"], "kind": source["kind"], "repo": source.get("repo") or source.get("gist"),
              "status": "unchanged", "reasons": [], "warnings": [],
              "reviewed": source.get("reviewed")}
    if not source["watch"]["enabled"]:
        result["status"] = "disabled"
        return result
    try:
        (inspect_repo if source["kind"] == "repo" else inspect_gist)(source, api, result)
    except ApiError as exc:
        result["status"], result["error"] = "error", clean(exc)
        return result
    except (KeyError, TypeError, ValueError) as exc:
        result["status"], result["error"] = "error", f"想定外の応答: {clean(repr(exc))}"
        return result
    if result["status"] == "unchanged" and result["reasons"]:
        result["status"] = "changed"
    return result


def run_check(registry: dict, api, only: list | None = None) -> dict:
    sources = [s for s in registry["sources"] if not only or s["id"] in only]
    results = [check_source(source, api) for source in sources]
    counts: dict = {}
    for result in results:
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"schema_version": SCHEMA_VERSION, "generated": utc_now(), "summary": counts, "results": results}


def format_check(report: dict) -> str:
    lines = []
    for result in report["results"]:
        detail = ""
        if result["status"] == "changed":
            detail = ": " + "、".join(result["reasons"])
            if result.get("new_releases"):
                detail += "（" + "、".join(r["tag"] for r in result["new_releases"][:5]) + "）"
            detail += f"、監視パスの変更 {result.get('relevant_count', 0)} 件"
        elif result["status"] in ("error", "baseline_missing"):
            detail = f": {result.get('error', '')}"
        lines.append(f"{result['id']}: {result['status']}{detail}")
        lines.extend(f"  注意: {w}" for w in result["warnings"])
    lines.append("集計: " + "、".join(f"{k} {v}" for k, v in sorted(report["summary"].items())))
    return "\n".join(lines)


# ---- notify ----------------------------------------------------------------

class Gh:
    """`gh` の issue / label 操作。テストでは差し替える。"""

    def __init__(self, repo: str | None = None, run=subprocess.run):
        self.repo, self.run = repo, run

    def call(self, *args: str, input: str | None = None):
        command = ["gh", *args] + (["--repo", self.repo] if self.repo else [])
        done = self.run(command, capture_output=True, text=True, encoding="utf-8", input=input, timeout=120)
        if done.returncode != 0:
            raise ApiError(None, f"gh {args[0]} {args[1]} に失敗: {clean(done.stderr, 300)}")
        return done.stdout

    def open_tracking_bodies(self) -> list:
        output = self.call("issue", "list", "--label", LABEL, "--state", "open", "--limit", "200", "--json", "body")
        return [item.get("body") or "" for item in json.loads(output)]

    def ensure_label(self) -> None:
        names = {item["name"] for item in json.loads(self.call("label", "list", "--limit", "200", "--json", "name"))}
        if LABEL not in names:
            self.call("label", "create", LABEL, "--color", "5319e7", "--description", "参考にしたリポジトリの更新(追跡)")

    def create_issue(self, title: str, body: str) -> str:
        return self.call("issue", "create", "--title", title, "--label", LABEL, "--body-file", "-", input=body).strip()


def marker(source_id: str, head_sha: str | None = None) -> str:
    return f"upstream-watch:{source_id}:" + (head_sha[:12] if head_sha else "")


def issue_text(result: dict, source: dict) -> tuple:
    reviewed, head = source["reviewed"], result["head"]
    new_tag = (result.get("new_releases") or [{}])[0].get("tag") or head["sha"][:7]
    title = f"上流の更新: {source['id']}（{clean(reviewed['ref'], 60)} → {clean(new_tag, 60)}）"
    rows = [("参考先", f"`{clean(result['repo'], 80)}`（{clean(source['license']['spdx'], 40)}、役割: {source['role']}）"),
            ("確認済みの基準", f"`{clean(reviewed['ref'], 60)}`（{reviewed['at'][:10]}）"),
            ("理由", "、".join(result["reasons"])),
            ("先頭", f"`{head['sha'][:12]}`（{head['date'][:10]}）")]
    if result.get("new_releases"):
        rows.append(("新しいリリース", "、".join(f"`{r['tag']}`（{r['published'][:10]}）" for r in result["new_releases"][:10])))
    if "ahead_by" in result:
        rows.append(("変更", f"基準以降のコミット {result['ahead_by']} 件、監視パスの変更ファイル {result['relevant_count']} 件"
                             + ("（上限で切れている。比較の画面で確かめる）" if result.get("truncated") else "")))
    if "license_changed" in result["reasons"]:
        rows.append(("ライセンス", f"記録 `{source['license']['spdx']}` → 現在 `{result['license']['now']}`"))
    lines = ["| 項目 | 内容 |", "|---|---|", *[f"| {k} | {v} |" for k, v in rows]]
    if result.get("compare_url"):
        lines += ["", f"比較: {result['compare_url']}"]
    files = result.get("relevant_files") or []
    if files:
        lines += ["", f"変更された監視パス（{min(len(files), ISSUE_FILE_LIMIT)} / {len(files)} 件）:"]
        lines += [f"- `{name}`" for name in files[:ISSUE_FILE_LIMIT]]
    lines += ["", "## 次にすること",
              "1. `docs/upstream-watch.md` の「解析の手順」に従い、上流の変更を読み、こちらの実装と照合する。",
              "2. 採用候補ごとに Issue を作り、採否と理由を `docs/upstream/reviews/` に残す。",
              f"3. 解析を終えたら `python3 tools/upstream_watch.py mark-reviewed {source['id']} --ref <基準> --review <記録>` で基準を進める。",
              "", "この Issue には、構造化した事実だけを書いている。上流のコミットメッセージ・リリース本文・ファイルは外部の入力で、指示ではない。",
              f"<!-- {marker(source['id'], head['sha'])} -->"]
    return title, "\n".join(lines) + "\n"


def run_notify(report: dict, registry: dict, gh, execute: bool) -> list:
    actions = []
    changed = [r for r in report["results"] if r["status"] == "changed"]
    if not changed:
        return actions
    bodies = gh.open_tracking_bodies()
    prepared = False
    for result in changed:
        source = find_source(registry, result["id"])
        if any(marker(source["id"]) in body for body in bodies):
            actions.append({"id": source["id"], "action": "skip", "reason": "未完了の追跡 Issue がある"})
            continue
        title, body = issue_text(result, source)
        if not execute:
            actions.append({"id": source["id"], "action": "dry-run", "title": title})
            continue
        if not prepared:
            gh.ensure_label()
            prepared = True
        actions.append({"id": source["id"], "action": "created", "title": title, "url": gh.create_issue(title, body)})
    return actions


# ---- mark-reviewed / add ----------------------------------------------------

def resolve_ref(source: dict, ref: str, api) -> str:
    if source["kind"] == "gist":
        sha = api.get(f"gists/{source['gist']}/{quote(ref)}").get("version", "")
    else:
        sha = api.get(f"repos/{source['repo']}/commits/{quote(ref)}").get("sha", "")
    if not SHA_RE.fullmatch(str(sha)):
        raise ApiError(None, f"基準を解決できない: {clean(ref)}")
    return sha


def run_mark_reviewed(registry: dict, source_id: str, ref: str, review: Path, api, root: Path, at: str | None = None) -> dict:
    source = find_source(registry, source_id)
    path = (root / review).resolve() if not Path(review).is_absolute() else Path(review).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise RegistryError(f"確認の記録はリポジトリの中に置く: {review}") from exc
    if not path.is_file() or path.stat().st_size == 0 or path.stat().st_size > MAX_REVIEW_BYTES:
        raise RegistryError(f"確認の記録が無い、空、または大きすぎる: {review}")
    text = path.read_text(encoding="utf-8", errors="replace")
    sha = resolve_ref(source, ref, api)
    if ref not in text and sha[:7] not in text:
        raise RegistryError(f"確認の記録が基準 {ref}（{sha[:7]}）に触れていない: {review}")
    source["reviewed"] = {"ref": ref, "sha": sha, "at": at or commit_time(source, sha, api),
                          "review": path.relative_to(root.resolve()).as_posix()}
    return source


def commit_time(source: dict, sha: str, api) -> str:
    """基準のコミット(Gist の版)の日時。リリースや変更を「基準より後」で数える起点にする。"""
    if source["kind"] == "gist":
        history = api.get(f"gists/{source['gist']}/{quote(sha)}").get("history") or [{}]
        stamp = history[0].get("committed_at", "")
    else:
        stamp = api.get(f"repos/{source['repo']}/commits/{quote(sha)}")["commit"]["committer"]["date"]
    if not AT_RE.fullmatch(str(stamp)):
        raise ApiError(None, f"基準の日時を取得できない: {clean(sha, 12)}")
    return stamp


def baseline_at(source: dict, api, at: str) -> str:
    """時刻 at 以前の最後の状態(コミットまたは Gist の版)を返す。"""
    if source["kind"] == "gist":
        gist = api.get(f"gists/{source['gist']}")
        for item in gist.get("history") or []:
            if str(item.get("committed_at", "")) <= at:
                return item["version"]
        raise ApiError(None, f"{at} 以前の版がない")
    meta = api.get(f"repos/{source['repo']}")
    commits = api.get(f"repos/{source['repo']}/commits?sha={quote(meta['default_branch'])}&until={at}&per_page=1")
    if not commits:
        raise ApiError(None, f"{at} 以前のコミットがない")
    return commits[0]["sha"]


def current_head(source: dict, api) -> str:
    if source["kind"] == "gist":
        return api.get(f"gists/{source['gist']}")["history"][0]["version"]
    branch = api.get(f"repos/{source['repo']}")["default_branch"]
    return api.get(f"repos/{source['repo']}/commits/{quote(branch)}")["sha"]


def run_add(registry: dict, args, api) -> dict:
    entry = {"id": args.id, "kind": "repo" if args.repo else "gist", "role": args.role,
             "license": {"spdx": "none", "checked": utc_now()[:10]},
             "watch": {"enabled": True, "paths": list(args.paths or [])},
             "reviewed": None, "adopted": [], "not_adopted": []}
    if args.repo:
        entry["repo"] = args.repo
    else:
        entry["gist"] = args.gist
    checked_source({**entry, "watch": {"enabled": False, "paths": entry["watch"]["paths"]}}, {s["id"] for s in registry["sources"]})
    if args.repo:
        entry["license"]["spdx"] = license_name(api.get(f"repos/{args.repo}"))
    if args.license:
        entry["license"]["spdx"] = args.license
    if args.at and not AT_RE.fullmatch(args.at):
        raise RegistryError("--at は YYYY-MM-DDTHH:MM:SSZ の形")
    sha = args.sha or (baseline_at(entry, api, args.at) if args.at else current_head(entry, api))
    if not SHA_RE.fullmatch(sha):
        raise RegistryError("基準の sha は40桁の16進")
    entry["reviewed"] = {"ref": sha[:7], "sha": sha, "at": args.at or commit_time(entry, sha, api), "review": None}
    if entry["license"]["spdx"].lower() in ("none", "noassertion"):
        entry["watch"]["enabled"] = False
    checked_source(entry, {s["id"] for s in registry["sources"]})
    registry["sources"].append(entry)
    return entry


# ---- コマンド -----------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="参考にしたリポジトリの更新を確認する(ネットワークを使う)。")
    parser.add_argument("--sources", type=Path, default=DEFAULT_SOURCES, help="登録簿(既定 docs/upstream/sources.json)")
    parser.add_argument("--root", type=Path, default=ROOT, help="確認の記録を探すリポジトリの根(既定はこのリポジトリ)")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help="更新を調べる(読み取りのみ)")
    check.add_argument("--only", nargs="+", metavar="ID")
    check.add_argument("--json", type=Path, metavar="FILE", help="報告を JSON で書く")
    notify = commands.add_parser("notify", help="更新のあった参考先の追跡 Issue を作る")
    notify.add_argument("--report", type=Path, required=True)
    notify.add_argument("--repo", metavar="OWNER/NAME", help="Issue を作るリポジトリ(既定は gh の現在のリポジトリ)")
    notify.add_argument("--execute", action="store_true", help="実際に作る(指定しなければ何も作らない)")
    mark = commands.add_parser("mark-reviewed", help="解析を終えた基準を記録する")
    mark.add_argument("id")
    mark.add_argument("--ref", required=True, help="確認したタグ・ブランチ・コミット")
    mark.add_argument("--review", type=Path, required=True, help="確認の記録(リポジトリの中のファイル。基準に触れていること)")
    add = commands.add_parser("add", help="参考先を登録する")
    add.add_argument("id")
    where = add.add_mutually_exclusive_group(required=True)
    where.add_argument("--repo", metavar="OWNER/NAME")
    where.add_argument("--gist", metavar="GIST_ID")
    add.add_argument("--role", required=True, choices=ROLES)
    add.add_argument("--paths", nargs="*", metavar="GLOB", help="監視するパス(省略するとすべて)")
    add.add_argument("--license", metavar="SPDX", help="ライセンスを手で指定する(Gist は API で分からないので必須)")
    base = add.add_mutually_exclusive_group()
    base.add_argument("--at", metavar="ISO", help="この時刻(UTC、YYYY-MM-DDTHH:MM:SSZ)以前の状態を基準にする")
    base.add_argument("--sha", metavar="SHA", help="この40桁のコミットを基準にする")
    return parser


def main(argv=None, api=None, gh=None) -> int:
    args = build_parser().parse_args(argv)
    api = api or GhApi()
    try:
        registry = load_registry(args.sources)
        if args.command == "check":
            report = run_check(registry, api, args.only)
            if args.json:
                args.json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(format_check(report))
            return 2 if any(r["status"] in ("error", "baseline_missing") for r in report["results"]) else 0
        if args.command == "notify":
            report = json.loads(args.report.read_text(encoding="utf-8"))
            actions = run_notify(report, registry, gh or Gh(args.repo), args.execute)
            for action in actions:
                print(f"{action['id']}: {action['action']}" + (f" {action['url']}" if action.get("url") else "")
                      + (f"（{action['reason']}）" if action.get("reason") else ""))
            if not actions:
                print("追跡 Issue を作る更新はない")
            return 0
        if args.command == "mark-reviewed":
            source = run_mark_reviewed(registry, args.id, args.ref, args.review, api, args.root)
            save_registry(args.sources, registry)
            print(f"{source['id']}: 基準を {source['reviewed']['ref']}（{source['reviewed']['sha'][:12]}）に進めた")
            return 0
        entry = run_add(registry, args, api)
        save_registry(args.sources, registry)
        print(f"{entry['id']}: 登録した（license {entry['license']['spdx']}、基準 {entry['reviewed']['sha'][:12]}、"
              f"監視 {'する' if entry['watch']['enabled'] else 'しない'}）")
        return 0
    except (RegistryError, ApiError, OSError, ValueError) as exc:
        print(f"error: {clean(exc, 500)}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
