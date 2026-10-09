#!/usr/bin/env python3
"""国語表記の規則データの元になる、文化庁の公式資料を取得・照合・抽出する。ネットワークを使う。

    python3 tools/update_kokugo_sources.py verify
    python3 tools/update_kokugo_sources.py extract-joyo PDF [--out PATH]
    python3 tools/update_kokugo_sources.py extract-ijidokun PDF [--out PATH]

日常の検査(skill/japanese-readability-editor/scripts/check_kokugo.py)は、ネットワークを使わない。
規則を更新するときにだけ、このツールで公式資料を取り直す。このツールは skill の外にあるので、
配布物(ZIP)には入らない。

  verify            data/kokugo-sources.json に記録した URL を取得し、サイズと SHA-256 が記録と
                    一致するかを確かめる。一致しない資料は、公式側で内容が変わった可能性がある。
                    規則の根拠(節・ページ)を読み直してから、記録を更新する。終了コード 0=すべて一致、
                    1=不一致または取得の失敗がある。
  extract-joyo      常用漢字表の PDF から、字種(2136字)と音訓を取り出して data/joyo-kanji.json を作る。
  extract-ijidokun  「異字同訓」の漢字の使い分け例の PDF から、133項目を取り出して data/ijidokun.json を作る。

extract-* には pypdf が要る。システムの Python へは入れず、仮想環境を使う。

    python3 -m venv .venv-sources && .venv-sources/bin/pip install pypdf
    .venv-sources/bin/python tools/update_kokugo_sources.py extract-joyo 常用漢字表.pdf

PDF から取り出した文字列の並びは、PDF ライブラリの版で変わりうる。そのため、抽出した件数が公式の
件数(字種 2136、異字同訓 133項目)と一致しなければ、データを書き出さずに失敗する。
"""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import re
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "skill" / "japanese-readability-editor" / "data"
SOURCES_FILE = DATA_DIR / "kokugo-sources.json"
JOYO_FILE = DATA_DIR / "joyo-kanji.json"
IJIDOKUN_FILE = DATA_DIR / "ijidokun.json"

EXPECTED_JOYO_COUNT = 2136
EXPECTED_IJIDOKUN_COUNT = 133
JOYO_SOURCE_ID = "NAIKAKU-JOYO-2010"
IJIDOKUN_SOURCE_ID = "BUNKA-IJIDOKUN-2014"
USER_AGENT = "japanese-readability-editor-source-check"

# 常用漢字表の本表のページを見分ける印。PDF の各ページ末に、InDesign の書き出し名が入っている。
JOYO_BODY_MARKER = "03初_改定常用漢字表_本表"
JOYO_ROW_RE = re.compile(r"^[ \t　]{0,2}(\S)\t")
KANA_FIELD_RE = re.compile(r"^[　 ]{0,2}([ぁ-ゖァ-ヶー]+)[　 ]*$")
IJIDOKUN_HEAD_RE = re.compile(r"^(\S+) ([０-９]{3})$")
IJIDOKUN_VARIANT_RE = re.compile(r"^【(.+?)】(.*)$")
FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

Pages = Sequence[Tuple[int, str]]


class ExtractionError(Exception):
    """抽出した件数が公式の件数と合わないなど、データを書き出してはならない状態。"""


def sha256_of(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_cjk_ideograph(ch: str) -> bool:
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x2FA1F


# --- 抽出 -------------------------------------------------------------------


def parse_joyo_pages(pages: Pages) -> Tuple[List[str], Dict[str, List[str]]]:
    """常用漢字表の本表のページから、(字種の一覧, 字種ごとの音訓) を返す。

    行の先頭にある漢字を字種とみなす。音訓は、その字種の行に続く行から、かな(字音は片仮名、
    字訓は平仮名)だけの欄を拾う。1字下げの音訓(特別なもの)も含める。
    """
    chars: List[str] = []
    readings: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for _, text in pages:
        if JOYO_BODY_MARKER not in text:
            continue
        for line in text.split("\n"):
            head = JOYO_ROW_RE.match(line)
            starts_row = bool(head) and is_cjk_ideograph(head.group(1))
            if starts_row:
                current = head.group(1)
                if current in readings:
                    raise ExtractionError(f"字種が重複した: {current}")
                chars.append(current)
                readings[current] = []
            if current is None:
                continue
            fields = line.split("\t")
            for field in fields[1:] if starts_row else fields:
                match = KANA_FIELD_RE.match(field)
                if match:
                    readings[current].append(match.group(1))
                    break
    return chars, readings


def parse_ijidokun_pages(pages: Pages) -> List[dict]:
    """「異字同訓」の本表から、項目の一覧を返す。項目の番号は 1 から連続していなければならない。

    各項目は、見出しの読み、PDF のページ、使い分けの候補(漢字の形と、語義の最初の1行)を持つ。
    漢字の形に付いた注記の印(*)は取り除く。
    """
    entries: List[dict] = []
    current: Optional[dict] = None
    for page, text in pages:
        for raw in text.split("\n"):
            line = raw.strip()
            head = IJIDOKUN_HEAD_RE.match(line)
            if head:
                number = int(head.group(2).translate(FULLWIDTH_DIGITS))
                if number == len(entries) + 1:
                    current = {"id": number, "reading": head.group(1), "page": page, "variants": []}
                    entries.append(current)
                    continue
            if current is None:
                continue
            variant = IJIDOKUN_VARIANT_RE.match(line)
            if variant and current["page"] <= page <= current["page"] + 1:
                forms = [form.replace("*", "") for form in variant.group(1).split("・")]
                current["variants"].append({"forms": forms, "gloss": variant.group(2).strip()})
    return entries


def extract_pdf_pages(path: Path) -> List[Tuple[int, str]]:
    """PDF の各ページの文字列を、(ページ番号, 文字列) の一覧で返す。pypdf が要る。"""
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise ExtractionError(
            "pypdf is required for extract-*. Install it into a virtual environment, not the system Python: "
            "python3 -m venv .venv-sources && .venv-sources/bin/pip install pypdf"
        ) from exc
    reader = PdfReader(str(path))
    return [(number, page.extract_text() or "") for number, page in enumerate(reader.pages, start=1)]


def pypdf_version() -> str:
    try:
        import pypdf

        return f"pypdf {pypdf.__version__}"
    except ImportError:
        return "pypdf (not installed)"


# --- 書き出し -----------------------------------------------------------------


def render_joyo(chars: List[str], readings: Dict[str, List[str]], source: dict, pdf_bytes: bytes) -> str:
    """読みやすい差分になるよう、字種ごとに1行で書く。"""
    header = {
        "schema_version": 1,
        "source_id": JOYO_SOURCE_ID,
        "derived_from": {"url": source["retrieved_files"][0]["url"], "sha256": sha256_of(pdf_bytes), "size": len(pdf_bytes)},
        "extraction": {
            "script": "tools/update_kokugo_sources.py extract-joyo",
            "library": pypdf_version(),
            "note": "常用漢字表の本表を機械的に取り出した派生データ。文化庁が作成したものではない。出典の記載と加工の注記は kokugo-sources.md を参照",
        },
        "count": len(chars),
    }
    lines = ["{"]
    for key, value in header.items():
        lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
    lines.append(f'  "chars": {json.dumps("".join(chars), ensure_ascii=False)},')
    lines.append('  "readings": {')
    body = [f"    {json.dumps(ch, ensure_ascii=False)}: {json.dumps(readings[ch], ensure_ascii=False)}" for ch in chars]
    lines.append(",\n".join(body))
    lines.append("  }")
    lines.append("}")
    return "\n".join(lines) + "\n"


def render_ijidokun(entries: List[dict], source: dict, pdf_bytes: bytes) -> str:
    header = {
        "schema_version": 1,
        "source_id": IJIDOKUN_SOURCE_ID,
        "derived_from": {"url": source["retrieved_files"][0]["url"], "sha256": sha256_of(pdf_bytes), "size": len(pdf_bytes)},
        "extraction": {
            "script": "tools/update_kokugo_sources.py extract-ijidokun",
            "library": pypdf_version(),
            "note": "「異字同訓」の漢字の使い分け例の本表を機械的に取り出した派生データ。語義は各項目の最初の1行だけ。文化庁が作成したものではない",
        },
        "count": len(entries),
    }
    lines = ["{"]
    for key, value in header.items():
        lines.append(f"  {json.dumps(key)}: {json.dumps(value, ensure_ascii=False)},")
    lines.append('  "entries": [')
    lines.append(",\n".join("    " + json.dumps(entry, ensure_ascii=False) for entry in entries))
    lines.append("  ]")
    lines.append("}")
    return "\n".join(lines) + "\n"


# --- 照合 -------------------------------------------------------------------


def fetch_bytes(url: str, timeout: float = 60.0) -> Tuple[int, bytes]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (https の公式 URL だけ)
        return response.status, response.read()


def verify_sources(registry: dict, fetch: Callable[[str], Tuple[int, bytes]] = fetch_bytes) -> List[dict]:
    """記録した各ファイルを取得し、サイズと SHA-256 を照合する。fetch は差し替えられる。"""
    results: List[dict] = []
    for source in registry.get("sources", []):
        for item in source.get("retrieved_files", []):
            record = {"source_id": source["id"], "url": item["url"], "expected_sha256": item["sha256"],
                      "expected_size": item["size"], "ok": False, "note": ""}
            try:
                status, body = fetch(item["url"])
            except (OSError, ValueError, http.client.HTTPException) as exc:  # 通信の失敗は、1件の失敗として記録して続ける(URLError は OSError)
                record["note"] = f"fetch failed: {exc}"
                results.append(record)
                continue
            record["status"] = status
            record["size"] = len(body)
            record["sha256"] = sha256_of(body)
            if status != 200:
                record["note"] = f"HTTP {status}"
            elif record["sha256"] != item["sha256"]:
                record["note"] = "content changed since it was recorded; re-read the cited sections before updating"
            else:
                record["ok"] = True
            results.append(record)
    return results


# --- CLI --------------------------------------------------------------------


def load_registry(path: Path = SOURCES_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def find_source(registry: dict, source_id: str) -> dict:
    for source in registry["sources"]:
        if source["id"] == source_id:
            return source
    raise ExtractionError(f"source not found in the registry: {source_id}")


def run_verify(args: argparse.Namespace) -> int:
    registry = load_registry(args.sources)
    results = verify_sources(registry, lambda url: fetch_bytes(url, args.timeout))
    failed = [r for r in results if not r["ok"]]
    for r in results:
        mark = "OK  " if r["ok"] else "FAIL"
        print(f"{mark} {r['source_id']}  {r['url']}" + (f"  ({r['note']})" if r["note"] else ""))
    print(f"{len(results) - len(failed)}/{len(results)} files match the recorded SHA-256")
    return 1 if failed else 0


@dataclass(frozen=True)
class ExtractSpec:
    """1種類のデータ(常用漢字表、異字同訓)を PDF から作る手順。"""

    source_id: str
    build: Callable[[Pages, bytes, dict], str]  # (ページ, PDF のバイト列, 資料の記録) から、書き出す JSON を作る
    default_out: Path


def build_joyo_text(pages: Pages, pdf_bytes: bytes, source: dict) -> str:
    chars, readings = parse_joyo_pages(pages)
    if len(chars) != EXPECTED_JOYO_COUNT or len(set(chars)) != EXPECTED_JOYO_COUNT:
        raise ExtractionError(f"expected {EXPECTED_JOYO_COUNT} distinct characters, found {len(chars)} ({len(set(chars))} distinct)")
    empty = [ch for ch in chars if not readings[ch]]
    if empty:
        raise ExtractionError(f"characters without any reading: {''.join(empty)}")
    return render_joyo(chars, readings, source, pdf_bytes)


def build_ijidokun_text(pages: Pages, pdf_bytes: bytes, source: dict) -> str:
    entries = parse_ijidokun_pages(pages)
    if len(entries) != EXPECTED_IJIDOKUN_COUNT:
        raise ExtractionError(f"expected {EXPECTED_IJIDOKUN_COUNT} entries, found {len(entries)}")
    if any(not entry["variants"] for entry in entries):
        raise ExtractionError("an entry without any variant was found")
    return render_ijidokun(entries, source, pdf_bytes)


JOYO_SPEC = ExtractSpec(JOYO_SOURCE_ID, build_joyo_text, JOYO_FILE)
IJIDOKUN_SPEC = ExtractSpec(IJIDOKUN_SOURCE_ID, build_ijidokun_text, IJIDOKUN_FILE)


def run_extract(args: argparse.Namespace, spec: ExtractSpec) -> int:
    source = find_source(load_registry(args.sources), spec.source_id)
    pdf_bytes = Path(args.pdf).read_bytes()
    recorded = source["retrieved_files"][0]["sha256"]
    if sha256_of(pdf_bytes) != recorded:
        print(f"warning: {args.pdf} differs from the recorded file (SHA-256 {recorded[:12]}…); "
              "the extracted data will be tied to the file you gave", file=sys.stderr)
    text = spec.build(extract_pdf_pages(Path(args.pdf)), pdf_bytes, source)
    out = Path(args.out) if args.out else spec.default_out
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="文化庁の公式資料を取得・照合・抽出する(ネットワークを使う)。")
    parser.add_argument("--sources", type=Path, default=SOURCES_FILE, help="資料の記録(既定は data/kokugo-sources.json)")
    commands = parser.add_subparsers(dest="command", required=True)

    verify = commands.add_parser("verify", help="記録した URL を取得し、SHA-256 を照合する")
    verify.add_argument("--timeout", type=float, default=60.0)
    verify.set_defaults(handler=run_verify)

    joyo = commands.add_parser("extract-joyo", help="常用漢字表の PDF から data/joyo-kanji.json を作る")
    joyo.add_argument("pdf")
    joyo.add_argument("--out", default=None)
    joyo.set_defaults(handler=lambda a: run_extract(a, JOYO_SPEC))

    ijidokun = commands.add_parser("extract-ijidokun", help="「異字同訓」の PDF から data/ijidokun.json を作る")
    ijidokun.add_argument("pdf")
    ijidokun.add_argument("--out", default=None)
    ijidokun.set_defaults(handler=lambda a: run_extract(a, IJIDOKUN_SPEC))
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.handler(args)
    except (ExtractionError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
