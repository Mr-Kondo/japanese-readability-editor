#!/usr/bin/env python3
"""国語表記の規則データ(data/*.json)を検証する。読み取り専用。ネットワークを使わない。

    validate_kokugo_rules.py [--data-dir DIR] [--json]

検査する内容。
  - 規則 ID の形式と重複、必須項目の不足、適用設定(general-tech / public-explanation / official)の抜けと不正な区分
  - 出典の欠落、出典 ID の参照切れ、節の欠落、PDF の出典のページ(形式と、PDF のページ数の範囲)
  - 出典の記録(正式名称、発出主体、種別、告示・改定日、公式 URL、確認日、サイズと SHA-256)
  - error の根拠: スキル独自の判断(skill-policy)や、内閣告示・内閣訓令でない出典だけの規則は error にできない
  - 検出の定義(正規表現のコンパイル、候補の置換テンプレートの参照、曖昧な語の理由、省略形が全形の部分列か)
  - 修正例と保持例を、検査エンジンに実際に通した結果(修正例は検出され、保持例は確認対象にならない)
  - 常用漢字表のデータ(2136字、字種の重複なし、音訓あり)と、規則が主張する『表にない音訓』が表と食い違わないこと
  - 異字同訓のデータ(133項目、番号の連続)
  - 使われていない出典がないこと

終了コード: 0=問題なし, 1=問題あり, 2=データを読めない(ファイルがない、JSON が壊れている)。
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kokugo_engine as engine  # noqa: E402

RULE_ID_RE = re.compile(r"^KOKUGO-[A-Z]+-\d{3}$")
SOURCE_ID_RE = re.compile(r"^[A-Z0-9]+(?:-[A-Z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PDF_PAGES_RE = re.compile(r"^PDF (?:pp?\.\d+(?:-\d+)?(?:, \d+(?:-\d+)?)*|全\d+ページ)$")
TEMPLATE_REF_RE = re.compile(r"\\g<([A-Za-z_][A-Za-z0-9_]*)>")
FAMILIES = ("kanji", "kana", "okurigana", "gairai", "numeral", "punctuation", "expression", "ijidokun", "consistency", "reference")
SOURCE_KINDS = ("内閣告示", "内閣訓令", "建議", "報告", "答申", "通知")
BINDING_KINDS = ("内閣告示", "内閣訓令")  # error の根拠にできる種別
SOURCE_ROLES = ("implemented", "reference-only")
VERIFICATIONS = ("bytes-fetched-and-read", "summary-only")
PROFILE_BASES = ("source", "skill-policy")
OFFICIAL_HOST = "https://www.bunka.go.jp/"
EXPECTED_JOYO_COUNT = 2136
EXPECTED_IJIDOKUN_COUNT = 133
DETECT_REQUIRED_LISTS = ("conditions", "exceptions", "protected")
RULE_REQUIRED_TEXT = ("title", "summary", "machine_detectable", "needs_context_scope")
# 構造検査をすり抜けた不備で、検査エンジンが失敗するときの例外。検証エラーとして報告する
ENGINE_DATA_ERRORS = (KeyError, TypeError, ValueError, IndexError, AttributeError, re.error)


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def error(self, where: str, message: str) -> None:
        self.errors.append(f"{where}: {message}")

    def warn(self, where: str, message: str) -> None:
        self.warnings.append(f"{where}: {message}")

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class Context:
    """検証の間、各関数が共有する入力。"""

    report: Report
    sources: Dict[str, dict]
    ruleset: Optional[engine.RuleSet]
    joyo: engine.Joyo
    ijidokun: dict


def is_date(value: object) -> bool:
    if not isinstance(value, str) or not DATE_RE.match(value):
        return False
    try:
        datetime.date.fromisoformat(value)
    except ValueError:
        return False
    return True


def non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def parse_pdf_pages(text: str, page_count: int) -> Optional[List[int]]:
    """'PDF pp.4-5' などの表記を、ページ番号の一覧にする。形式が不正なら None。"""
    if not PDF_PAGES_RE.match(text):
        return None
    if text.startswith("PDF 全"):
        return [page_count]
    pages: List[int] = []
    for part in text.split(".", 1)[1].split(","):
        part = part.strip()
        if "-" in part:
            low, high = (int(x) for x in part.split("-"))
            if low > high:
                return None
            pages += [low, high]
        else:
            pages.append(int(part))
    return pages


# --- 出典の記録 -------------------------------------------------------------


def validate_retrieved_file(item: dict, report: Report, where: str) -> None:
    if not isinstance(item.get("url"), str) or not item["url"].startswith("https://"):
        report.error(where, "url must be https")
    if item.get("format") not in ("pdf", "html"):
        report.error(where, "format must be 'pdf' or 'html'")
    if not isinstance(item.get("size"), int) or item["size"] <= 0:
        report.error(where, "size must be a positive integer")
    if not isinstance(item.get("sha256"), str) or not SHA256_RE.match(item["sha256"]):
        report.error(where, "sha256 must be 64 lowercase hex digits")
    if item.get("format") == "pdf" and (not isinstance(item.get("pages"), int) or item["pages"] <= 0):
        report.error(where, "pdf files must record the page count")
    if "last_modified" in item and not is_date(item["last_modified"]):
        report.error(where, "last_modified must be a date")


def validate_source_record(source: dict, report: Report, where: str) -> None:
    for key in ("title", "designation", "issuer", "nature", "scope", "currentness"):
        if not non_empty_text(source.get(key)):
            report.error(where, f"missing '{key}'")
    if source.get("kind") not in SOURCE_KINDS:
        report.error(where, f"kind must be one of {SOURCE_KINDS}")
    if source.get("role") not in SOURCE_ROLES:
        report.error(where, f"role must be one of {SOURCE_ROLES}")
    if source.get("verification") not in VERIFICATIONS:
        report.error(where, f"verification must be one of {VERIFICATIONS}")
    for key in ("issued_on", "verified_on"):
        if not is_date(source.get(key)):
            report.error(where, f"'{key}' must be a date (YYYY-MM-DD)")
    url = source.get("url")
    if not isinstance(url, str) or not url.startswith(OFFICIAL_HOST):
        report.error(where, f"url must be an official URL starting with {OFFICIAL_HOST}")
    files = source.get("retrieved_files")
    if not isinstance(files, list) or not files:
        report.error(where, "retrieved_files must record at least one file (URL, size, SHA-256)")
        return
    for number, item in enumerate(files):
        validate_retrieved_file(item, report, f"{where}.retrieved_files[{number}]")


def validate_usage_terms(registry: dict, report: Report) -> None:
    terms = registry.get("usage_terms") or {}
    for key in ("url", "name", "verification", "note"):
        if not non_empty_text(terms.get(key)):
            report.error("sources.usage_terms", f"missing '{key}' (the terms under which the data may be reused must be recorded)")


def validate_sources(registry: dict, report: Report) -> Dict[str, dict]:
    by_id: Dict[str, dict] = {}
    if registry.get("schema_version") != engine.SCHEMA_VERSION:
        report.error("sources", f"schema_version must be {engine.SCHEMA_VERSION}")
    if not is_date(registry.get("verified_on")):
        report.error("sources", "verified_on must be a date (YYYY-MM-DD)")
    validate_usage_terms(registry, report)
    sources = registry.get("sources")
    if not isinstance(sources, list) or not sources:
        report.error("sources", "'sources' must be a non-empty list")
        return by_id
    for index, source in enumerate(sources):
        sid = source.get("id") if isinstance(source, dict) else None
        where = f"sources[{sid or index}]"
        if not isinstance(sid, str) or not SOURCE_ID_RE.match(sid):
            report.error(where, "invalid or missing id")
        elif sid in by_id:
            report.error(where, "duplicate source id")
        else:
            by_id[sid] = source
            validate_source_record(source, report, where)
    return by_id


def first_pdf_pages(source: dict) -> Optional[int]:
    for item in source.get("retrieved_files", []):
        if item.get("format") == "pdf":
            return item.get("pages")
    return None


# --- 規則 -------------------------------------------------------------------


def is_subsequence_with_hiragana(small: str, big: str) -> bool:
    index = 0
    for ch in big:
        if index < len(small) and small[index] == ch:
            index += 1
        elif not ("ぁ" <= ch <= "ゖ"):
            return False
    return index == len(small)


def unescape_literal(pattern: str) -> str:
    return re.sub(r"\\(.)", r"\1", pattern)


def validate_entry(entry: dict, detection: dict, ctx: Context, where: str) -> None:
    report, joyo = ctx.report, ctx.joyo
    pattern = entry.get("pattern")
    if not non_empty_text(pattern):
        report.error(where, "missing pattern")
        return
    try:
        regex = re.compile(pattern, re.M)
    except re.error as exc:
        report.error(where, f"invalid regular expression: {exc}")
        return
    if regex.search(""):
        report.error(where, "pattern must not match the empty string")
    candidates = entry.get("candidates", [])
    if not isinstance(candidates, list) or not all(isinstance(c, str) for c in candidates):
        report.error(where, "candidates must be a list of strings")
        return
    for template in candidates:
        for name in TEMPLATE_REF_RE.findall(template):
            if name not in regex.groupindex:
                report.error(where, f"candidate {template!r} refers to group '{name}' that the pattern does not define")
    if entry.get("ambiguous") and not non_empty_text(entry.get("ambiguity")):
        report.error(where, "an ambiguous entry must say why in 'ambiguity'")
    if detection.get("omission_check"):
        literal = unescape_literal(pattern)
        if len(candidates) != 1 or not is_subsequence_with_hiragana(candidates[0], literal):
            report.error(where, f"candidate {candidates!r} must be the pattern {literal!r} with only hiragana removed")
    for check in entry.get("joyo_check", []):
        ch, prefix = check.get("char"), check.get("kun_prefix")
        if ch not in joyo.chars:
            report.error(where, f"joyo_check: '{ch}' is not in the Joyo kanji table")
            continue
        clash = [r for r in joyo.readings[ch] if "\u3041" <= r[0] <= "\u3096" and r.startswith(prefix)]
        if clash:
            report.error(where, f"joyo_check: the table lists the kun reading {clash} for '{ch}', so '{prefix}…' is not outside the table")


def validate_pattern_entries(detection: dict, ctx: Context, where: str) -> None:
    entries = detection.get("entries")
    if not isinstance(entries, list) or not entries:
        ctx.report.error(where, "patterns detection needs a non-empty 'entries' list")
        return
    if "noun_context" in detection and not non_empty_text(detection["noun_context"].get("followers")):
        ctx.report.error(where, "noun_context.followers must be a non-empty string")
    for index, entry in enumerate(entries):
        validate_entry(entry, detection, ctx, f"{where}.entries[{index}]")


def validate_consistency_groups(detection: dict, ctx: Context, where: str) -> None:
    groups = detection.get("groups")
    if not isinstance(groups, list) or not groups:
        ctx.report.error(where, "consistency detection needs a non-empty 'groups' list")
        return
    seen: Set[object] = set()
    for group in groups:
        gwhere = f"{where}.groups[{group.get('id')}]"
        if group.get("id") in seen:
            ctx.report.error(gwhere, "duplicate group id")
        seen.add(group.get("id"))
        forms = group.get("forms", [])
        labels = [form.get("label") for form in forms]
        if len(forms) < 2 or len(set(labels)) != len(labels):
            ctx.report.error(gwhere, "a group needs at least two forms with distinct labels")
        for form in forms:
            try:
                re.compile(form["pattern"], re.M)
            except (re.error, KeyError) as exc:
                ctx.report.error(gwhere, f"invalid form pattern: {exc}")


def validate_detection(rule: dict, ctx: Context, where: str) -> None:
    detection = rule.get("detection")
    if not isinstance(detection, dict):
        ctx.report.error(where, "a detect rule needs a 'detection' object")
        return
    kind = detection.get("kind")
    if kind not in engine.DETECTION_KINDS:
        ctx.report.error(where, f"detection.kind must be one of {engine.DETECTION_KINDS}")
        return
    if detection.get("dedupe") not in (None, "first_per_text"):
        ctx.report.error(where, "detection.dedupe must be absent or 'first_per_text'")
    if kind == "patterns":
        validate_pattern_entries(detection, ctx, f"{where}.detection")
    elif kind == "consistency":
        validate_consistency_groups(detection, ctx, f"{where}.detection")
    elif kind == "ijidokun":
        ids = detection.get("entry_ids")
        known = {entry["id"] for entry in ctx.ijidokun.get("entries", [])}
        if not isinstance(ids, list) or not ids or not all(i in known for i in ids):
            ctx.report.error(where, "detection.entry_ids must list existing 異字同訓 entry ids")


def validate_profile_mapping(rule: dict, name: str, mapping: dict, binding_sources: bool, report: Report, where: str) -> None:
    category = mapping.get("category")
    if category not in engine.CATEGORIES or category == "excluded":
        report.error(where, f"category must be one of error / recommendation / needs_context / accepted_variant, got {category!r}")
    if mapping.get("basis") not in PROFILE_BASES:
        report.error(where, f"basis must be one of {PROFILE_BASES}")
    if not non_empty_text(mapping.get("note")):
        report.error(where, "missing note")
    if category == "error":
        if rule.get("provenance") == "skill-policy":
            report.error(where, "a skill-policy rule cannot produce 'error' (the skill's own judgment is not an official rule)")
        if not binding_sources:
            report.error(where, "'error' needs a cabinet notice or cabinet directive among the cited sources")
        if mapping.get("basis") != "source":
            report.error(where, "'error' must be based on the source text (basis: source)")
    if rule.get("provenance") == "skill-policy" and mapping.get("basis") != "skill-policy":
        report.error(where, "a skill-policy rule must mark every profile basis as skill-policy")


def validate_profiles(rule: dict, binding_sources: bool, ctx: Context, where: str) -> None:
    profiles = rule.get("profiles")
    if not isinstance(profiles, dict) or set(profiles) != set(engine.PROFILES):
        ctx.report.error(where, f"profiles must define exactly {list(engine.PROFILES)}")
        return
    for name, mapping in profiles.items():
        validate_profile_mapping(rule, name, mapping, binding_sources, ctx.report, f"{where}.profiles[{name}]")


def validate_source_pages(ref: dict, source: dict, report: Report, where: str) -> None:
    page_count = first_pdf_pages(source)
    if page_count is None:
        return
    text = ref.get("pages")
    if not non_empty_text(text):
        report.error(where, f"{ref['source_id']} is a PDF source: record the pages (e.g. 'PDF pp.4-5')")
        return
    numbers = parse_pdf_pages(text, page_count)
    if numbers is None:
        report.error(where, f"pages {text!r} is not in the form 'PDF p.N', 'PDF pp.N-M', 'PDF p.N, M' or 'PDF 全Nページ'")
    elif any(n < 1 or n > page_count for n in numbers):
        report.error(where, f"pages {text!r} is outside the PDF ({page_count} pages)")


def validate_rule_sources(rule: dict, ctx: Context, where: str) -> bool:
    """出典を検査し、error の根拠になる出典(内閣告示・内閣訓令)を含むかを返す。"""
    cited = rule.get("sources")
    if not isinstance(cited, list) or not cited:
        ctx.report.error(where, "a rule must cite at least one source (rules without a source are not allowed)")
        return False
    binding = False
    only_reference = True
    for number, ref in enumerate(cited):
        swhere = f"{where}.sources[{number}]"
        source = ctx.sources.get(ref.get("source_id"))
        if source is None:
            ctx.report.error(swhere, f"unknown source_id {ref.get('source_id')!r} (dangling reference)")
            continue
        if not non_empty_text(ref.get("locator")):
            ctx.report.error(swhere, "missing locator (section / item)")
        binding = binding or source["kind"] in BINDING_KINDS
        only_reference = only_reference and source["role"] != "implemented"
        validate_source_pages(ref, source, ctx.report, swhere)
    if rule.get("automation") == "detect" and only_reference:
        ctx.report.error(where, "a detect rule cannot rest only on reference-only sources")
    return binding


def validate_fix_example(rule: dict, example: dict, ruleset: engine.RuleSet, report: Report, where: str) -> bool:
    """修正例の before が検出され、after が確認対象にならないこと。before が確認対象になるかを返す。"""
    profile = example.get("profile")
    if profile not in engine.PROFILES or not non_empty_text(example.get("before")) or not non_empty_text(example.get("after")):
        report.error(where, "needs profile, before and after")
        return False
    before = engine.check_text(example["before"], profile, ruleset, only_rules=[rule["id"]])
    after = engine.check_text(example["after"], profile, ruleset, only_rules=[rule["id"]])
    triggered = [f for f in before if f["category"] != "excluded"]
    if not triggered:
        report.error(where, f"the 'before' text is not detected by this rule under {profile}: {example['before']!r}")
    leftovers = [f for f in after if f["category"] in engine.FLAG_CATEGORIES]
    if leftovers:
        report.error(where, f"the 'after' text still gets a {leftovers[0]['category']} under {profile}: {example['after']!r}")
    return any(f["category"] in engine.FLAG_CATEGORIES for f in triggered)


def validate_keep_example(rule: dict, example: dict, ruleset: engine.RuleSet, report: Report, where: str) -> None:
    profiles = example.get("profiles")
    if not isinstance(profiles, list) or not profiles or not set(profiles) <= set(engine.PROFILES) or not non_empty_text(example.get("text")):
        report.error(where, "needs a text and a non-empty list of valid profiles")
        return
    if not non_empty_text(example.get("reason")):
        report.error(where, "needs a reason (why this text must stay as it is)")
    for profile in profiles:
        flagged = [f for f in engine.check_text(example["text"], profile, ruleset, only_rules=[rule["id"]]) if f["category"] in engine.FLAG_CATEGORIES]
        if flagged:
            report.error(where, f"this text must not be flagged under {profile}, but got {flagged[0]['category']}: {example['text']!r}")


def run_examples(rule: dict, ctx: Context, where: str) -> None:
    examples = rule.get("examples")
    if not isinstance(examples, dict) or not examples.get("fix") or not examples.get("keep"):
        ctx.report.error(where, "a detect rule needs both fix examples and keep examples (修正例と保持例)")
        return
    flag_possible = any(rule["profiles"][p]["category"] in engine.FLAG_CATEGORIES for p in engine.PROFILES)
    shown_flag = False
    for number, example in enumerate(examples["fix"]):
        shown_flag = validate_fix_example(rule, example, ctx.ruleset, ctx.report, f"{where}.examples.fix[{number}]") or shown_flag
    if flag_possible and not shown_flag:
        ctx.report.error(f"{where}.examples.fix", "no fix example is flagged (error / recommendation / needs_context) by this rule")
    for number, example in enumerate(examples["keep"]):
        validate_keep_example(rule, example, ctx.ruleset, ctx.report, f"{where}.examples.keep[{number}]")


def validate_rule_fields(rule: dict, report: Report, where: str) -> None:
    if rule.get("family") not in FAMILIES:
        report.error(where, f"family must be one of {FAMILIES}")
    if rule.get("provenance") not in engine.PROVENANCES:
        report.error(where, f"provenance must be one of {engine.PROVENANCES}")
    if rule.get("automation") not in engine.AUTOMATIONS:
        report.error(where, f"automation must be one of {engine.AUTOMATIONS}")
    for key in RULE_REQUIRED_TEXT:
        if not non_empty_text(rule.get(key)):
            report.error(where, f"missing '{key}'")
    skill_decisions = rule.get("skill_decisions")
    if not isinstance(skill_decisions, list) or not skill_decisions or not all(non_empty_text(x) for x in skill_decisions):
        report.error(where, "skill_decisions must list which parts are this skill's own judgment (公式資料の規定と区別するため)")
    protected = rule.get("protected")
    if not isinstance(protected, list) or not set(protected) <= set(engine.PROTECTED_KINDS):
        report.error(where, f"protected must be a list drawn from {engine.PROTECTED_KINDS}")


def validate_reference_rule(rule: dict, report: Report, where: str) -> None:
    for key in ("reference_when", "not_checked"):
        if not non_empty_text(rule.get(key)):
            report.error(where, f"a reference-only rule needs '{key}'")
    for key in ("profiles", "detection", "examples"):
        if key in rule:
            report.error(where, f"a reference-only rule must not define '{key}' (it would look like an automatic check)")


def validate_detect_rule(rule: dict, binding: bool, ctx: Context, where: str) -> None:
    for key in DETECT_REQUIRED_LISTS:
        value = rule.get(key)
        if not isinstance(value, list) or (key != "protected" and not value) or not all(non_empty_text(x) for x in value):
            ctx.report.error(where, f"'{key}' must be a non-empty list of strings (適用条件・例外と許容形・保護対象)")
    validate_profiles(rule, binding, ctx, where)
    validate_detection(rule, ctx, where)


def validate_rule(rule: dict, ctx: Context, where: str) -> Set[str]:
    """規則1件を検証し、引用した出典 ID を返す。構造に問題があるときは、エンジンに通す例を実行しない。"""
    errors_before = len(ctx.report.errors)
    validate_rule_fields(rule, ctx.report, where)
    binding = validate_rule_sources(rule, ctx, where)
    cited = {ref.get("source_id") for ref in rule.get("sources", [])} if isinstance(rule.get("sources"), list) else set()
    if rule.get("automation") == "reference-only":
        validate_reference_rule(rule, ctx.report, where)
        return cited
    validate_detect_rule(rule, binding, ctx, where)
    compiled = ctx.ruleset is not None and any(r.id == rule["id"] for r in ctx.ruleset.rules)
    if compiled and len(ctx.report.errors) == errors_before:
        try:
            run_examples(rule, ctx, where)
        except ENGINE_DATA_ERRORS as exc:
            ctx.report.error(where, f"the checking engine failed on this rule's examples: {type(exc).__name__}: {exc}")
    return cited


def validate_rules_header(doc: dict, report: Report) -> None:
    if doc.get("schema_version") != engine.SCHEMA_VERSION:
        report.error("rules", f"schema_version must be {engine.SCHEMA_VERSION}")
    if not is_date(doc.get("rules_version")):
        report.error("rules", "rules_version must be a date (YYYY-MM-DD)")
    if set(doc.get("profiles", {})) != set(engine.PROFILES):
        report.error("rules", f"top-level profiles must define exactly {list(engine.PROFILES)}")
    else:
        for name, info in doc["profiles"].items():
            if not non_empty_text(info.get("label")) or not non_empty_text(info.get("description")):
                report.error(f"rules.profiles[{name}]", "needs label and description")
    if set(doc.get("categories", {})) != set(engine.CATEGORIES):
        report.error("rules", f"top-level categories must define exactly {list(engine.CATEGORIES)}")


def validate_rules(doc: dict, ctx: Context) -> None:
    validate_rules_header(doc, ctx.report)
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        ctx.report.error("rules", "'rules' must be a non-empty list")
        return
    seen: Set[str] = set()
    cited_sources: Set[str] = set()
    for index, rule in enumerate(rules):
        rid = rule.get("id") if isinstance(rule, dict) else None
        where = f"rules[{rid or index}]"
        if not isinstance(rid, str) or not RULE_ID_RE.match(rid):
            ctx.report.error(where, "id must look like KOKUGO-FAMILY-001")
        elif rid in seen:
            ctx.report.error(where, "duplicate rule id")
        else:
            seen.add(rid)
            cited_sources |= validate_rule(rule, ctx, where)
    for sid in ctx.sources:
        if sid not in cited_sources:
            ctx.report.error(f"sources[{sid}]", "not cited by any rule (remove it or cite it)")


# --- 派生データ -------------------------------------------------------------


def validate_joyo(joyo_doc: dict, sources: Dict[str, dict], report: Report) -> None:
    chars, readings = joyo_doc.get("chars", ""), joyo_doc.get("readings", {})
    if joyo_doc.get("count") != EXPECTED_JOYO_COUNT or len(chars) != EXPECTED_JOYO_COUNT:
        report.error("joyo-kanji", f"must hold exactly {EXPECTED_JOYO_COUNT} characters (count={joyo_doc.get('count')}, chars={len(chars)})")
    if len(set(chars)) != len(chars):
        report.error("joyo-kanji", "duplicate characters")
    if set(chars) != set(readings):
        report.error("joyo-kanji", "chars and readings do not cover the same characters")
    empty = [ch for ch in chars if not readings.get(ch)]
    if empty:
        report.error("joyo-kanji", f"characters without any reading: {''.join(empty[:10])}")
    not_kanji = [ch for ch in chars if not engine.is_ideograph(ch)]
    if not_kanji:
        report.error("joyo-kanji", f"non-ideograph characters: {''.join(not_kanji[:10])}")
    check_derived(joyo_doc, "NAIKAKU-JOYO-2010", sources, report)


def validate_ijidokun(data: dict, sources: Dict[str, dict], report: Report) -> None:
    entries = data.get("entries", [])
    if data.get("count") != EXPECTED_IJIDOKUN_COUNT or len(entries) != EXPECTED_IJIDOKUN_COUNT:
        report.error("ijidokun", f"must hold exactly {EXPECTED_IJIDOKUN_COUNT} entries")
    if [entry.get("id") for entry in entries] != list(range(1, len(entries) + 1)):
        report.error("ijidokun", "entry ids must run 1, 2, 3, … without gaps")
    pages = first_pdf_pages(sources.get("BUNKA-IJIDOKUN-2014", {})) or 0
    for entry in entries:
        if not entry.get("variants") or not non_empty_text(entry.get("reading")):
            report.error(f"ijidokun[{entry.get('id')}]", "needs a reading and at least one variant")
        if not isinstance(entry.get("page"), int) or not 1 <= entry["page"] <= pages:
            report.error(f"ijidokun[{entry.get('id')}]", "page is outside the PDF")
    check_derived(data, "BUNKA-IJIDOKUN-2014", sources, report)


def check_derived(data: dict, source_id: str, sources: Dict[str, dict], report: Report) -> None:
    """派生データが、記録した公式ファイルの SHA-256 と結び付いていること。"""
    source = sources.get(source_id)
    if data.get("source_id") != source_id or source is None:
        report.error(source_id, f"derived data must name source_id {source_id}, and the registry must have it")
        return
    recorded = next((f for f in source["retrieved_files"] if f.get("format") == "pdf"), None)
    derived = data.get("derived_from", {})
    if recorded is None or derived.get("sha256") != recorded["sha256"]:
        report.error(source_id, "derived_from.sha256 does not match the recorded official file (the data is not tied to the recorded source)")


# --- 入口 -------------------------------------------------------------------


def validate_all(data_dir: Optional[Path] = None) -> Report:
    base = Path(data_dir) if data_dir else engine.DATA_DIR
    report = Report()
    docs: Dict[str, dict] = {}
    for name in (engine.RULES_FILE, engine.SOURCES_FILE, engine.JOYO_FILE, engine.IJIDOKUN_FILE):
        docs[name] = engine.read_json(base / name)  # 読めなければ RulesError(終了コード 2)
    sources = validate_sources(docs[engine.SOURCES_FILE], report)
    validate_joyo(docs[engine.JOYO_FILE], sources, report)
    validate_ijidokun(docs[engine.IJIDOKUN_FILE], sources, report)
    try:
        ruleset: Optional[engine.RuleSet] = engine.load_rules(base)
    except (engine.RulesError, KeyError, TypeError, ValueError, AttributeError) as exc:
        report.error("rules", f"cannot compile the rules: {type(exc).__name__}: {exc}")
        ruleset = None
    joyo_doc = docs[engine.JOYO_FILE]
    joyo = ruleset.joyo if ruleset else engine.Joyo(frozenset(joyo_doc.get("chars", "")), joyo_doc.get("readings", {}), 0)
    validate_rules(docs[engine.RULES_FILE], Context(report, sources, ruleset, joyo, docs[engine.IJIDOKUN_FILE]))
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="国語表記の規則データを検証する(読み取り専用、ネットワークなし)。",
                                     epilog="終了コード: 0=問題なし, 1=問題あり, 2=データを読めない。")
    parser.add_argument("--data-dir", type=Path, default=None, metavar="DIR", help="規則データのディレクトリ(既定は skill の data/)")
    parser.add_argument("--json", action="store_true", help="結果を JSON で出力する")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = validate_all(args.data_dir)
    except engine.RulesError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"ok": report.ok, "errors": report.errors, "warnings": report.warnings}, ensure_ascii=False, indent=2))
    else:
        for message in report.errors:
            print(f"ERROR: {message}")
        for message in report.warnings:
            print(f"WARN: {message}")
        print("OK: kokugo rules are valid" if report.ok else f"FAILED: {len(report.errors)} error(s)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
