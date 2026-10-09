"""国語の表記・用法の規則を文書に当てる検査エンジン。読み取り専用。

check_kokugo.py(検査)と validate_kokugo_rules.py(規則データの検証)が使う。単独では実行しない。
ネットワーク通信、ファイルの書き込み、外部コマンドの実行は行わない。形態素解析も使わない。

規則と根拠は data/kokugo-rules.json に、資料の記録は data/kokugo-sources.json に、
常用漢字表の字種と音訓は data/joyo-kanji.json に、「異字同訓」の項目は data/ijidokun.json にある。
区分(category)は、適用設定(profile)ごとに規則データが決める。このモジュールは区分を決めず、
次の場合に限って、区分を『要確認(needs_context)』または『適用しない(excluded)』へ下げる。

  - 規則の語が、品詞や用法を機械では決められないと規則データが記した語(ambiguous)であるとき
  - 名詞の用法を確かめる規則(noun_context)で、直後の文字から名詞と確定できないとき
  - 該当箇所が保護対象(コード、URL、引用、frontmatter、除外指定、用語集の語)に重なるとき
  - 該当箇所が、用語集の表記指定(use:)と衝突するとき
"""

from __future__ import annotations

import bisect
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

sys.dont_write_bytecode = True

SCHEMA_VERSION = 1
PROFILES = ("general-tech", "public-explanation", "official")
DEFAULT_PROFILE = "general-tech"
CATEGORIES = ("error", "recommendation", "needs_context", "accepted_variant", "excluded")
FLAG_CATEGORIES = ("error", "recommendation", "needs_context")  # 利用者に確認を求める区分(重い順)
DETECTION_KINDS = ("patterns", "joyo_outside", "ijidokun", "consistency")
PROVENANCES = ("primary-source", "primary-source-derived", "skill-policy")
AUTOMATIONS = ("detect", "reference-only")
PROTECTED_KINDS = ("code", "url", "quote", "frontmatter", "proper_noun", "technical_term")
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RULES_FILE = "kokugo-rules.json"
SOURCES_FILE = "kokugo-sources.json"
JOYO_FILE = "joyo-kanji.json"
IJIDOKUN_FILE = "ijidokun.json"

IGNORE_START = re.compile(r"<!--\s*kokugo-ignore-start\s*-->")
IGNORE_END = re.compile(r"<!--\s*kokugo-ignore-end\s*-->")
FENCE_RE = re.compile(r"^[ ]{0,3}(`{3,}|~{3,})")
QUOTE_LINE_RE = re.compile(r"^[ ]{0,3}>")
FRONTMATTER_CLOSE = ("---", "...")
INLINE_CODE_RE = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)", re.S)
LINK_DEST_RE = re.compile(r"\]\((?P<dest>[^)\s]*)(?:\s+\"[^\"]*\")?\)")
URL_RE = re.compile(r"(?:https?|ftp)://[^\s<>\"'`\)\]）」』、。，．]+")  # 日本語のパス(/wiki/申し込み)も URL に含める
HTML_TAG_RE = re.compile(r"</?[A-Za-z][^>\n]*>")
REF_DEF_RE = re.compile(r"^[ ]{0,3}\[[^\]\n]+\]:[ \t]*(?P<dest>\S+)", re.M)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.S)

PROTECTION_LABELS = {
    "frontmatter": "frontmatter", "fenced_code": "コードブロック", "inline_code": "インラインコード", "url": "URL・リンク先",
    "quote": "引用(ブロッククォート)", "html_comment": "HTML コメント", "html": "HTML タグ", "ignore_region": "除外指定(kokugo-ignore)",
}

DISCLAIMER = ("この結果は表記上の機械検査であり、意味の保存、日本語の正しさ全体、構成や論理の適否を保証しない。"
              "指摘は見直しの起点であり、命令ではない。")
LIMITS = (
    "形態素解析を使わない。品詞や用法が決まらない語は、確定した指摘にせず『要確認(needs_context)』に下げる。",
    "常用漢字表は字種(2136字)だけを照合する。音訓は、規則に登録した語についてだけ確かめる。",
    "異字同訓は、選んだ項目の漢字の形を『要確認』として示すだけで、正誤を決めない。",
    "固有名詞・専門用語を自動では識別しない。--glossary の protect: または kokugo-ignore で指定する。",
    "規則に登録していない語・表記は検査していない。『指摘なし』は『規則に違反していない』ことを意味しない。",
)
NOT_CHECKED = (
    "敬語(敬語の指針)の適否",
    "ローマ字のつづり方の適否",
    "字体(通用字体、表外漢字字体表)の適否",
    "数字・符号の用法のうち、規則に登録していない項目",
    "文体、構成、論理、文の長さ(別の診断で扱う)",
)


class RulesError(Exception):
    """規則データを読めない、または使えない。"""


# --- データの読み込み -----------------------------------------------------------


def read_json(path: Path) -> dict:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError) as exc:
        raise RulesError(f"cannot read {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise RulesError(f"invalid JSON in {path}: {exc}") from exc


@dataclass
class Joyo:
    chars: frozenset
    readings: Dict[str, List[str]]
    count: int


@dataclass
class CompiledRule:
    data: dict
    entries: List[Tuple[dict, "re.Pattern[str]"]] = field(default_factory=list)
    groups: List[dict] = field(default_factory=list)
    ijidokun_regex: Optional["re.Pattern[str]"] = None
    ijidokun_forms: Dict[str, dict] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return self.data["id"]

    @property
    def kind(self) -> Optional[str]:
        return (self.data.get("detection") or {}).get("kind")


@dataclass
class RuleSet:
    doc: dict
    joyo: Joyo
    ijidokun: dict
    rules: List[CompiledRule]

    @property
    def version(self) -> str:
        return self.doc.get("rules_version", "")


def compile_pattern(pattern: str, where: str) -> "re.Pattern[str]":
    try:
        return re.compile(pattern, re.M)
    except re.error as exc:
        raise RulesError(f"{where}: invalid regular expression {pattern!r}: {exc}") from exc


def compile_rule(rule: dict, joyo: Joyo, ijidokun: dict) -> CompiledRule:
    compiled = CompiledRule(data=rule)
    detection = rule.get("detection")
    if rule.get("automation") != "detect" or not detection:
        return compiled
    kind = detection.get("kind")
    where = rule.get("id", "?")
    if kind == "patterns":
        for index, entry in enumerate(detection.get("entries", [])):
            compiled.entries.append((entry, compile_pattern(entry["pattern"], f"{where} entries[{index}]")))
    elif kind == "consistency":
        for group in detection.get("groups", []):
            forms = [(form, compile_pattern(form["pattern"], f"{where} group {group.get('id')}")) for form in group["forms"]]
            compiled.groups.append({"group": group, "forms": forms})
    elif kind == "ijidokun":
        by_id = {entry["id"]: entry for entry in ijidokun.get("entries", [])}
        forms: Dict[str, dict] = {}
        for entry_id in detection.get("entry_ids", []):
            entry = by_id.get(entry_id)
            if entry is None:
                raise RulesError(f"{where}: ijidokun entry {entry_id} not found")
            for variant in entry["variants"]:
                for form in variant["forms"]:
                    forms.setdefault(form, {"entry": entry, "variant": variant})
        compiled.ijidokun_forms = forms
        if forms:
            ordered = sorted(forms, key=lambda f: (-len(f), f))
            compiled.ijidokun_regex = re.compile("|".join(re.escape(f) for f in ordered))
    return compiled


def load_rules(data_dir: Optional[Path] = None) -> RuleSet:
    base = Path(data_dir) if data_dir else DATA_DIR
    doc = read_json(base / RULES_FILE)
    joyo_doc = read_json(base / JOYO_FILE)
    ijidokun = read_json(base / IJIDOKUN_FILE)
    for key in ("schema_version", "rules"):
        if key not in doc:
            raise RulesError(f"{RULES_FILE}: missing '{key}'")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise RulesError(f"{RULES_FILE}: unsupported schema_version {doc['schema_version']} (expected {SCHEMA_VERSION})")
    joyo = Joyo(frozenset(joyo_doc["chars"]), joyo_doc["readings"], joyo_doc["count"])
    rules = [compile_rule(rule, joyo, ijidokun) for rule in doc["rules"]]
    return RuleSet(doc, joyo, ijidokun, rules)


# --- 用語集 -----------------------------------------------------------------


@dataclass
class Glossary:
    """組織の用語集。protect: は適用しない語(固有名詞・専門用語)、use: は組織が指定する表記。"""

    protect: List[str] = field(default_factory=list)
    use: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"protect": len(self.protect), "use": len(self.use)}


def parse_glossary(text: str) -> Glossary:
    glossary = Glossary()
    for raw in text.lstrip("﻿").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("use:"):
            term = line[4:].strip()
            target = glossary.use
        elif line.startswith("protect:"):
            term = line[8:].strip()
            target = glossary.protect
        else:
            term, target = line, glossary.protect
        if term and term not in target:
            target.append(term)
    return glossary


def merge_glossaries(glossaries: Iterable[Glossary]) -> Glossary:
    merged = Glossary()
    for glossary in glossaries:
        for term in glossary.protect:
            if term not in merged.protect:
                merged.protect.append(term)
        for term in glossary.use:
            if term not in merged.use:
                merged.use.append(term)
    return merged


def find_all(text: str, term: str) -> Iterable[Tuple[int, int]]:
    start = text.find(term)
    while start != -1:
        yield start, start + len(term)
        start = text.find(term, start + 1)


# --- 保護対象 ---------------------------------------------------------------


class Protection:
    """文字ごとに、保護対象の種類(なければ None)を持つ。位置は元の文章のままで、文章は書き換えない。"""

    def __init__(self, length: int) -> None:
        self.kinds: List[Optional[str]] = [None] * length

    def mark(self, start: int, end: int, kind: str) -> None:
        for index in range(max(start, 0), min(end, len(self.kinds))):
            if self.kinds[index] is None:
                self.kinds[index] = kind

    def first(self, start: int, end: int) -> Optional[str]:
        for kind in self.kinds[start:end]:
            if kind:
                return kind
        return None


def line_spans(text: str) -> List[Tuple[int, int]]:
    """各行の (開始, 終了=改行の位置) を返す。"""
    spans = []
    start = 0
    for line in text.split("\n"):
        spans.append((start, start + len(line)))
        start += len(line) + 1
    return spans


def protect_markdown_blocks(text: str, protection: Protection) -> None:
    lines = line_spans(text)
    count = len(lines)
    index = 0
    if count and text[lines[0][0]:lines[0][1]].strip() == "---":
        for close in range(1, count):
            if text[lines[close][0]:lines[close][1]].strip() in FRONTMATTER_CLOSE:
                protection.mark(0, min(lines[close][1] + 1, len(text)), "frontmatter")
                index = close + 1
                break
    fence: Optional[str] = None
    fence_start = 0
    while index < count:
        start, end = lines[index]
        line = text[start:end]
        if fence is not None:
            closing = re.match(r"^[ ]{0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}[ \t]*$", line)
            if closing:
                protection.mark(fence_start, min(end + 1, len(text)), "fenced_code")
                fence = None
            index += 1
            continue
        opener = FENCE_RE.match(line)
        if opener:
            fence, fence_start = opener.group(1), start
            index += 1
            continue
        if QUOTE_LINE_RE.match(line):
            protection.mark(start, min(end + 1, len(text)), "quote")
        index += 1
    if fence is not None:  # 閉じられていない fence は、文末まで保護する
        protection.mark(fence_start, len(text), "fenced_code")


def protect_comments_and_ignore_regions(text: str, protection: Protection) -> None:
    for match in HTML_COMMENT_RE.finditer(text):
        protection.mark(match.start(), match.end(), "html_comment")
    position = 0
    while True:
        opener = IGNORE_START.search(text, position)
        if not opener:
            break
        closer = IGNORE_END.search(text, opener.end())
        end = closer.start() if closer else len(text)
        protection.mark(opener.end(), end, "ignore_region")
        position = closer.end() if closer else len(text)
        if position >= len(text):
            break


def masked_copy(text: str, protection: Protection) -> str:
    """保護済みの文字を \x00 に置き換えた写しを返す(長さは変えない)。コードブロックの中の記号が、外の文章と対にならないようにする。"""
    return "".join("\x00" if kind else ch for ch, kind in zip(text, protection.kinds))


def protect_inline(text: str, protection: Protection) -> None:
    """インラインコード、リンク先、URL、HTML タグを保護する。段落(空行まで)ごとにコードの範囲を探す。"""
    masked = masked_copy(text, protection)
    offset = 0
    for chunk in re.split(r"(\n[ \t]*\n)", masked):
        for match in INLINE_CODE_RE.finditer(chunk):
            protection.mark(offset + match.start(), offset + match.end(), "inline_code")
        offset += len(chunk)
    masked = masked_copy(text, protection)
    for match in LINK_DEST_RE.finditer(masked):
        protection.mark(match.start("dest"), match.end("dest"), "url")
    for match in REF_DEF_RE.finditer(masked):
        protection.mark(match.start("dest"), match.end("dest"), "url")
    protect_urls(masked, protection)
    for match in HTML_TAG_RE.finditer(masked):
        protection.mark(match.start(), match.end(), "html")


def protect_urls(text: str, protection: Protection) -> None:
    for match in URL_RE.finditer(text):
        end = match.end()
        while end > match.start() and text[end - 1] in ".,;:)'":
            end -= 1
        protection.mark(match.start(), end, "url")


def build_protection(text: str, markdown: bool, glossary: Optional[Glossary] = None) -> Protection:
    protection = Protection(len(text))
    if markdown:
        protect_markdown_blocks(text, protection)
        protect_comments_and_ignore_regions(text, protection)
        protect_inline(text, protection)
    else:
        protect_urls(text, protection)
    if glossary:
        for term in glossary.protect:
            for start, end in find_all(text, term):
                protection.mark(start, end, f"glossary:{term}")
    return protection


# --- 位置 -------------------------------------------------------------------


class LineIndex:
    def __init__(self, text: str) -> None:
        self.starts = [0] + [i + 1 for i, ch in enumerate(text) if ch == "\n"]

    def locate(self, offset: int) -> Tuple[int, int]:
        line = bisect.bisect_right(self.starts, offset)
        return line, offset - self.starts[line - 1] + 1


# --- 検出 -------------------------------------------------------------------


@dataclass
class Hit:
    rule: CompiledRule
    start: int
    end: int
    text: str
    candidates: List[str] = field(default_factory=list)
    entry: Optional[dict] = None
    detail: dict = field(default_factory=dict)
    noun_state: Optional[str] = None  # 'noun' | 'compound' | 'verb-possible'


def is_ideograph(ch: str) -> bool:
    code = ord(ch)
    return 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0x20000 <= code <= 0x323AF or 0xF900 <= code <= 0xFAFF


def is_katakana(ch: str) -> bool:
    return "ァ" <= ch <= "ヺ"


def drop_overlaps(hits: List[Hit]) -> List[Hit]:
    """同じ規則の中で重なる該当箇所は、先に始まるもの、同じなら長いものを残す。"""
    kept: List[Hit] = []
    for hit in sorted(hits, key=lambda h: (h.start, -(h.end - h.start))):
        if kept and hit.start < kept[-1].end:
            continue
        kept.append(hit)
    return kept


def detect_patterns(rule: CompiledRule, text: str) -> List[Hit]:
    noun_context = rule.data["detection"].get("noun_context")
    hits: List[Hit] = []
    for entry, regex in rule.entries:
        for match in regex.finditer(text):
            if match.end() == match.start():
                continue
            candidates = [match.expand(template) for template in entry.get("candidates", [])]
            hit = Hit(rule, match.start(), match.end(), match.group(0), candidates, entry)
            if noun_context:
                following = text[match.end()] if match.end() < len(text) else ""
                if following and following in noun_context["followers"]:
                    hit.noun_state = "noun"
                elif following and (is_ideograph(following) or is_katakana(following)):
                    hit.noun_state = "compound"
                else:
                    hit.noun_state = "verb-possible"
            hits.append(hit)
    return drop_overlaps(hits)


def detect_joyo_outside(rule: CompiledRule, text: str, joyo: Joyo) -> List[Hit]:
    ignore = set(rule.data["detection"].get("ignore_chars", ""))
    hits: List[Hit] = []
    index = 0
    while index < len(text):
        ch = text[index]
        if is_ideograph(ch) and ch not in joyo.chars and ch not in ignore:
            end = index + 1
            while end < len(text) and is_ideograph(text[end]) and text[end] not in joyo.chars and text[end] not in ignore:
                end += 1
            hits.append(Hit(rule, index, end, text[index:end]))
            index = end
        else:
            index += 1
    return hits


def detect_ijidokun(rule: CompiledRule, text: str) -> List[Hit]:
    if rule.ijidokun_regex is None:
        return []
    hits = []
    for match in rule.ijidokun_regex.finditer(text):
        info = rule.ijidokun_forms[match.group(0)]
        entry = info["entry"]
        alternatives = ["・".join(variant["forms"]) for variant in entry["variants"]]
        note = (f"異字同訓『{entry['reading']}』の使い分け例: {'／'.join(alternatives)}"
                f"(出典 PDF p.{entry['page']}、項目{entry['id']:03d})。語義と文脈で決まる。")
        hits.append(Hit(rule, match.start(), match.end(), match.group(0), [], {"note": note},
                        {"ijidokun_id": entry["id"], "reading": entry["reading"], "alternatives": alternatives,
                         "page": entry["page"], "gloss": info["variant"]["gloss"]}))
    return hits


def detect(rule: CompiledRule, text: str, ruleset: RuleSet) -> List[Hit]:
    kind = rule.kind
    if kind == "patterns":
        return detect_patterns(rule, text)
    if kind == "joyo_outside":
        return detect_joyo_outside(rule, text, ruleset.joyo)
    if kind == "ijidokun":
        return detect_ijidokun(rule, text)
    return []


# --- 分類 -------------------------------------------------------------------


@dataclass
class CheckContext:
    """1つの文章の検査で共有する、変わらない入力。"""

    profile: str
    protection: Protection
    lines: LineIndex
    glossary: Optional[Glossary]
    use_spans: List[Tuple[int, int, str]]


@dataclass
class Verdict:
    category: str
    reason: str
    reason_code: str = "rule"

    @property
    def confirmed(self) -> bool:
        return self.category in ("error", "recommendation")

    def require_confirmation(self, reason_code: str, note: str) -> None:
        """確定した指摘を、要確認に下げる。理由に note を足す。"""
        self.category, self.reason_code = "needs_context", reason_code
        self.reason = f"{self.reason} {note}"


def source_ids_of(rule: dict) -> List[str]:
    ids: List[str] = []
    for source in rule.get("sources", []):
        if source["source_id"] not in ids:
            ids.append(source["source_id"])
    return ids


def protection_label(kind: str) -> str:
    if kind.startswith("glossary:"):
        return f"用語集(protect: {kind[len('glossary:'):]})"
    return PROTECTION_LABELS.get(kind, kind)


def noun_context_note(hit: Hit, noun_context: dict) -> Tuple[str, str]:
    if hit.noun_state == "compound":
        return "compound-word", noun_context.get("compound_reason", "")
    return "verb-form-possible", noun_context.get("otherwise_reason", "")


def glossary_conflict_note(term: str) -> str:
    return (f"【衝突】組織の用語集(use:)は『{term}』を指定している。"
            "適用設定の推奨と食い違うため、どちらに従うかを確かめる(黙って片方を適用しない)。")


def classify(hit: Hit, ctx: CheckContext) -> Verdict:
    """規則データが決めた区分を出発点に、確定できない理由があれば要確認へ、保護対象なら適用しないへ下げる。"""
    rule = hit.rule.data
    entry = hit.entry or {}
    mapping = rule["profiles"][ctx.profile]
    verdict = Verdict(mapping["category"], mapping["note"] + (f" {entry['note']}" if entry.get("note") else ""))

    if verdict.confirmed and entry.get("ambiguous"):
        verdict.require_confirmation("ambiguous", f"【要確認】{entry.get('ambiguity', '')}")
    noun_context = (rule.get("detection") or {}).get("noun_context")
    if noun_context and verdict.confirmed and hit.noun_state != "noun":
        code, why = noun_context_note(hit, noun_context)
        verdict.require_confirmation(code, f"【要確認】{why}")
    if verdict.confirmed:
        conflict = next((term for start, end, term in ctx.use_spans if start < hit.end and hit.start < end), None)
        if conflict:
            verdict.require_confirmation("glossary:use-conflict", glossary_conflict_note(conflict))

    protected_kind = ctx.protection.first(hit.start, hit.end)
    if protected_kind:
        return Verdict("excluded", f"保護対象({protection_label(protected_kind)})のため適用しない。", f"protected:{protected_kind}")
    return verdict


def build_finding(rule: dict, lines: LineIndex, span: Tuple[int, int], text: str, candidates: List[str],
                  verdict: Verdict, detail: dict) -> dict:
    """指摘の辞書を作る。出力の形式(キーと順序)は、ここだけで決める。"""
    start, end = span
    line, column = lines.locate(start)
    end_line, end_column = lines.locate(end)
    return {
        "rule_id": rule["id"], "category": verdict.category,
        "line": line, "column": column, "end_line": end_line, "end_column": end_column,
        "offset": start, "length": end - start, "text": text,
        "candidates": candidates, "title": rule["title"],
        "reason": verdict.reason, "reason_code": verdict.reason_code,
        "source_ids": source_ids_of(rule), "provenance": rule["provenance"], "detail": detail,
    }


def apply_dedupe(findings: List[dict], rule_dedupe: Dict[str, str]) -> List[dict]:
    """dedupe 指定の規則は、同じ表記を最初の1か所だけ残し、回数を detail.count に添える。"""
    counts: Dict[Tuple[str, str], int] = {}
    for finding in findings:
        if rule_dedupe.get(finding["rule_id"]) == "first_per_text" and finding["category"] != "excluded":
            key = (finding["rule_id"], finding["text"])
            counts[key] = counts.get(key, 0) + 1
    seen: Set[Tuple[str, str]] = set()
    kept: List[dict] = []
    for finding in findings:
        if rule_dedupe.get(finding["rule_id"]) == "first_per_text" and finding["category"] != "excluded":
            key = (finding["rule_id"], finding["text"])
            if key in seen:
                continue
            seen.add(key)
            finding["detail"] = dict(finding["detail"], count=counts[key])
        kept.append(finding)
    return kept


# --- 混在(許容される複数表記) ------------------------------------------------------

Occurrences = List[Tuple[int, int, str]]  # (開始, 終了, 該当した文字列)


def form_occurrences(forms: list, text: str, protection: Protection, flagged_spans: List[Tuple[int, int]]) -> List[Tuple[str, Occurrences]]:
    """各表記の出現箇所を返す。保護対象と、ほかの規則が既に指摘している箇所は、重ねて数えない。"""
    result = []
    for form, regex in forms:
        found = [(m.start(), m.end(), m.group(0)) for m in regex.finditer(text)
                 if m.end() > m.start() and not protection.first(m.start(), m.end())
                 and not any(m.start() < a_end and a_start < m.end() for a_start, a_end in flagged_spans)]
        result.append((form["label"], found))
    return result


def choose_majority(present: List[Tuple[str, Occurrences]], order: List[str], use_terms: Set[str]) -> Tuple[str, Optional[str]]:
    """(候補として示す表記, 用語集が指定した表記)。用語集の指定があれば、多数派より先に採る。"""
    preferred = next((label for label, found in present
                      if label in use_terms or any(matched in use_terms for _, _, matched in found)), None)
    majority = preferred or max(present, key=lambda item: (len(item[1]), -order.index(item[0])))[0]
    return majority, preferred


def mixture_reason(note: str, group: dict, counts: Dict[str, int], preferred: Optional[str]) -> str:
    reason = f"{note} 『{group['label']}』が混在している({', '.join(f'{k}: {v}件' for k, v in counts.items())})。"
    if preferred:
        reason += f"組織の用語集(use:)は『{preferred}』を指定している。"
    else:
        reason += "回数の多い表記は判断材料の一つにとどめ、明示された基準・用語集があればそれに従う。"
    if group.get("note"):
        reason += f" {group['note']}"
    return reason


def consistency_findings(rule: CompiledRule, text: str, ctx: CheckContext, flagged_spans: List[Tuple[int, int]]) -> List[dict]:
    mapping = rule.data["profiles"][ctx.profile]
    use_terms = set(ctx.glossary.use) if ctx.glossary else set()
    findings: List[dict] = []
    for compiled in rule.groups:
        group = compiled["group"]
        occurrences = form_occurrences(compiled["forms"], text, ctx.protection, flagged_spans)
        present = [(label, found) for label, found in occurrences if found]
        if len(present) < 2:
            continue
        counts = {label: len(found) for label, found in present}
        majority, preferred = choose_majority(present, [label for label, _ in occurrences], use_terms)
        verdict = Verdict(mapping["category"], mixture_reason(mapping["note"], group, counts, preferred), "glossary:use" if preferred else "rule")
        for label, found in present:
            if label != majority:
                start, end, matched = found[0]
                findings.append(build_finding(rule.data, ctx.lines, (start, end), matched, [majority], verdict,
                                              {"group": group["id"], "counts": counts}))
    return findings


# --- 検査 -------------------------------------------------------------------


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def check_text(text: str, profile: str = DEFAULT_PROFILE, ruleset: Optional[RuleSet] = None, markdown: bool = True,
               glossary: Optional[Glossary] = None, only_rules: Optional[Sequence[str]] = None) -> List[dict]:
    """文章を検査し、指摘の一覧を返す。同じ入力・規則・設定からは、同じ一覧(順序を含む)を返す。"""
    if profile not in PROFILES:
        raise ValueError(f"unknown profile: {profile}")
    ruleset = ruleset or load_rules()
    text = normalize_newlines(text)
    ctx = CheckContext(profile, build_protection(text, markdown, glossary), LineIndex(text), glossary,
                       [(s, e, term) for term in (glossary.use if glossary else []) for s, e in find_all(text, term)])
    dedupe = {r.id: r.data["detection"].get("dedupe") for r in ruleset.rules if r.data.get("detection")}
    selected = [r for r in ruleset.rules if r.data.get("automation") == "detect" and (only_rules is None or r.id in only_rules)]
    findings = [build_finding(hit.rule.data, ctx.lines, (hit.start, hit.end), hit.text, hit.candidates, classify(hit, ctx), dict(hit.detail))
                for rule in selected if rule.kind != "consistency" for hit in detect(rule, text, ruleset)]
    findings.sort(key=finding_order)
    findings = apply_dedupe(findings, dedupe)
    flagged_spans = [(f["offset"], f["offset"] + f["length"]) for f in findings if f["category"] in FLAG_CATEGORIES]
    for rule in selected:
        if rule.kind == "consistency":
            findings.extend(consistency_findings(rule, text, ctx, flagged_spans))
    findings.sort(key=finding_order)
    return findings


def finding_order(finding: dict) -> Tuple[int, str, int]:
    return finding["offset"], finding["rule_id"], finding["length"]


def count_categories(findings: Iterable[dict]) -> Dict[str, int]:
    counts = {category: 0 for category in CATEGORIES}
    for finding in findings:
        counts[finding["category"]] += 1
    return counts


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def coverage(ruleset: RuleSet, profile: str, glossary: Optional[Glossary]) -> dict:
    """検査したものと、していないものを、規則データから作る。未確認の項目を検査済みとして示さない。"""
    detect_rules = [r.data for r in ruleset.rules if r.data.get("automation") == "detect"]
    reference_rules = [r.data for r in ruleset.rules if r.data.get("automation") != "detect"]
    return {
        "profile": profile,
        "tokenizer": "none",
        "rules_checked": [{"id": r["id"], "title": r["title"], "family": r["family"], "provenance": r["provenance"],
                           "category_in_profile": r["profiles"][profile]["category"]} for r in detect_rules],
        "rules_reference_only": [{"id": r["id"], "title": r["title"], "not_checked": r["not_checked"]} for r in reference_rules],
        "not_checked": list(NOT_CHECKED),
        "limits": list(LIMITS),
        "glossary": glossary.to_dict() if glossary else None,
        "disclaimer": DISCLAIMER,
    }
