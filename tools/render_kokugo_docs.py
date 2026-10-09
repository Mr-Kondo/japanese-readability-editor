#!/usr/bin/env python3
"""references/kokugo-sources.md と references/kokugo-notation.md を、規則データから生成する。

    python3 tools/render_kokugo_docs.py           # 2つの文書を書き換える
    python3 tools/render_kokugo_docs.py --check   # 最新か確かめる(古ければ終了コード 1)

この2つの文書は、data/kokugo-sources.json と data/kokugo-rules.json の内容を表にしたものである。
手で書き換えず、データを変えたらこのツールで作り直す。tests/test_render_kokugo_docs.py が、最新であることを確かめる。
ネットワークは使わない。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

sys.dont_write_bytecode = True

SKILL_DIR = Path(__file__).resolve().parent.parent / "skill" / "japanese-readability-editor"
SOURCES_JSON = SKILL_DIR / "data" / "kokugo-sources.json"
RULES_JSON = SKILL_DIR / "data" / "kokugo-rules.json"
SOURCES_MD = SKILL_DIR / "references" / "kokugo-sources.md"
NOTATION_MD = SKILL_DIR / "references" / "kokugo-notation.md"


PROFILE_NAMES = ("general-tech", "public-explanation", "official")
CATEGORY_MARKS = {"error": "**error**", "recommendation": "recommendation", "needs_context": "needs_context", "accepted_variant": "accepted_variant"}
FAMILY_TITLES = [
    ("kanji", "漢字の使い方", [
        "字種(表外漢字)と音訓(表外音訓)は別に扱う。常用漢字表の字種だけを確認して、音訓まで確認済みとしない。この skill が音訓を確かめるのは、規則に登録した語だけである。",
        "固有名詞(人名・地名)と専門用語・特殊用語は、常用漢字表と内閣訓令の対象外である。機械では識別できないので、表外漢字は error にせず、要確認にとどめる。",
        "公用文では、副詞・連体詞は原則として漢字、接続詞は原則として仮名、補助的な用法は仮名で書く(内閣訓令 別紙1(2))。広く一般に向けた解説・広報等では、漢字を用いることになっている語も、仮名で書いたり振り仮名を使ったりしてよい(考え方 本文 Ⅰ-1)。",
        "品詞が決まらない語(動詞の連用形+『て』になりうる語など)は、形態素解析を使わないので、確定した指摘にせず要確認に下げる。",
    ]),
    ("kana", "仮名遣い(現代仮名遣い)", [
        "適用するのは現代文のうち口語体の文章である。原文の仮名遣いによる必要のあるもの、固有名詞などでこれによりがたいものは除かれる(前書き)。",
        "『ぢ』『づ』で書くことも認められている語(いなづま、きづな など)は、許容形である。誤りとして報告しない。例示にない語(『少しづつ』など)は、告示の例示から断定せず、要確認にする。",
    ]),
    ("okurigana", "送り仮名の付け方", [
        "本則・例外・許容を区別する。許容は、本則と並んで慣用として行われ、これによってよい形であり、誤りではない(見方及び使い方 三)。",
        "公用文は、原則として通則1〜6の本則・例外、通則7、付表の語による。許容を適用してよいのは通則2・4・6である(内閣訓令 別紙2)。ただし、読み間違えるおそれのない複合の名詞186語は、送り仮名を省くものとする。動詞は本則に従う。",
        "広く一般に向けた解説・広報等では、送り仮名を省かずに書くことができる(考え方 本文 Ⅰ-2)。",
        "名詞か動詞の連用形かは形態素解析なしには決まらない。この skill は、直後が『が』『を』『の』のときだけ名詞と確定し、それ以外は要確認にする。",
    ]),
    ("gairai", "外来語の表記", [
        "『外来語の表記』は、語形にゆれのあるものについて、語形をどちらかに決めようとはしていない。慣用が定まっているものはそれによる。分野によって異なる慣用が定まっている場合は、それぞれの慣用によって差し支えない(留意事項その1)。",
        "語末の長音符号は、告示が『慣用に応じて省くことができる』とし、考え方が『長音符号を用いて書くのが原則』とする。記述が異なるので、適用設定で区分を分けた(IT 分野の『サーバ』は general-tech では許容形)。",
        "固有名詞(人名、会社名、商品名)は、告示の対象外である。",
    ]),
    ("numeral", "数字の使い方", ["検査するのは『○か所』『○か月』だけである。そのほかの数字の用法は未検査(KOKUGO-REF-004)。"]),
    ("punctuation", "符号の使い方", ["検査するのは、句点にピリオドを使う書き方だけである。『，』と『、』の混在は、許容される表記の混在として KOKUGO-CONSIST-001 で扱う。"]),
    ("expression", "表現", [
        "考え方の表現に関する推奨は、一概に誤りとは言えないものを含む。recommendation にとどめ、error にしない。",
        "『まず最初に』『従来から』『返事を返す』『排気ガス』『被害を被る』は、考え方が慣用や強調として一概に誤りとも言えないとする例なので、検出しない。",
    ]),
    ("ijidokun", "異字同訓", [
        "『異字同訓』の使い分け例は『一つの参考』であり、異なる使い分けを否定する趣旨ではなく、仮名で表記することも妨げない(前書き3)。常に要確認とし、正しい漢字の候補は示さない。",
        "読みだけで使い分けを決めない。国語に関する世論調査の多数派・少数派だけで、正誤を決めない。語義と文脈で決める。",
        "133項目のうち、技術文書や案内文で紛らわしさが問題になりやすい16項目だけを検査する。残りは未検査である。",
    ]),
    ("consistency", "許容される複数表記の混在", [
        "この規則は、この skill の運用判断である。多数派かどうかは、許容される表記のあいだで選ぶときの判断材料にとどめ、明確な誤りを広げる理由にしない。",
        "明示された表記基準と組織の用語集を先に確認する。用語集が表記を指定していれば、その表記を候補に示す。",
    ]),
    ("reference", "参照のみ(自動判定しない)", ["初期実装では、参照先の整理にとどめる。ここに挙げた項目の適否は、検査していない。"]),
]


def render_sources_md(reg: dict) -> str:
    role_labels = {"implemented": "規則の根拠として使っている", "reference-only": "参照先として記録するだけ(自動判定しない)"}
    verification_labels = {"bytes-fetched-and-read": "公式サイトから原本のバイト列を取得し、本文を読んで確認した", "summary-only": "要約でのみ確認した"}
    lines: List[str] = []
    emit = lines.append
    emit("# 国語の表記・用法の出典")
    emit("")
    emit("この skill の国語の規則は、文化庁が公開する次の公式資料に基づく。規則の中身は `data/kokugo-rules.json` にあり、各規則が根拠として挙げる資料 ID と節・ページは、この文書の ID に対応する。")
    emit("")
    emit(f"確認日は {reg['verified_on']} である。この日に、入口の公式ページから各資料へたどり、原本(PDF と HTML)を取得して本文を読んだ。検索結果の要約だけでは規則を実装していない。")
    emit("")
    emit("## 公式資料の規定と、この skill の運用判断を区別する")
    emit("")
    emit("- 公式資料の規定: 規則データの `provenance` が `primary-source`(資料の規定そのもの)か `primary-source-derived`(資料の例示や原則を、この skill が活用形や条件へ広げたもの)の部分。")
    emit("- この skill の運用判断: `provenance` が `skill-policy` の規則と、各規則の `skill_decisions` に書いた部分。どの区分(error、recommendation など)にするか、品詞が決まらない語を要確認に下げるか、といった判断を含む。")
    emit("- 文の長さ(30〜45字の目安、46字以上、段落は200字以上)や、20字未満の文が3文以上続く箇所は、この skill の運用上の目安であり、文化庁の基準ではない。")
    emit("")
    emit("## 資料の性格")
    emit("")
    emit("| 種別 | 資料 | 性格 |")
    emit("|---|---|---|")
    emit("| 内閣告示 | 常用漢字表、現代仮名遣い、送り仮名の付け方、外来語の表記、ローマ字のつづり方 | 一般の社会生活における目安・よりどころ。科学・技術・芸術等の専門分野や個々人の表記には及ばない(各告示の前書き) |")
    emit("| 内閣訓令 | 公用文における漢字使用等について | 各行政機関が作成する公用文を対象にする。固有名詞は対象外で、専門用語・特殊用語では従わなくてもよい(別紙3) |")
    emit("| 建議 | 公用文作成の考え方 | 政府内の公用文作成の手引。告示・訓令そのものではなく、その運用の考え方と推奨 |")
    emit("| 報告・答申 | 「異字同訓」の漢字の使い分け例、敬語の指針 | 一つの参考。異なる使い分けを否定しない |")
    emit("| 通知 | 「公用文作成の考え方」の周知について | 周知の依頼。規則を新たに定めるものではない |")
    emit("")
    emit("## 資料一覧")
    emit("")
    emit("| ID | 正式名称 | 発出主体 | 種別 | 告示・発出日 | この skill での役割 |")
    emit("|---|---|---|---|---|---|")
    for source in reg["sources"]:
        emit(f"| `{source['id']}` | {source['title']}({source['designation']}) | {source['issuer']} | {source['kind']} | {source['issued_on']} | {role_labels[source['role']]} |")
    emit("")
    emit("## 利用条件と出典の表示")
    emit("")
    terms = reg["usage_terms"]
    emit(f"文化庁のサイトのコンテンツは、[{terms['name']}]({terms['url']})に従って利用する。出典を記載すれば、編集・加工して利用できる(商用利用を含む)。加工した場合は、加工したことを記載する。")
    emit("")
    emit("- 出典: 文化庁ホームページ(上の各資料の公式 URL)。")
    emit("- 加工: `data/joyo-kanji.json` と `data/ijidokun.json` は、公式の PDF から字種・音訓・項目を機械的に取り出した派生データである。`data/kokugo-rules.json` の規則は、公式資料を読んでこの skill が作成した。いずれも文化庁が作成したものではなく、文化庁が内容を保証するものでもない。")
    emit(f"- 規約の確認: {terms['note']}")
    emit("")
    emit("## 各資料の詳細")
    for source in reg["sources"]:
        emit("")
        emit(f"### `{source['id']}` {source['title']}")
        emit("")
        emit(f"- 正式名称: {source['title']}({source['designation']})")
        emit(f"- 発出主体: {source['issuer']}")
        emit(f"- 資料の種別: {source['kind']}")
        emit(f"- 告示・発出日: {source['issued_on']}")
        emit(f"- 公式 URL: <{source['url']}>")
        emit(f"- 確認日: {source['verified_on']}({verification_labels[source['verification']]})")
        emit(f"- 性格: {source['nature']}")
        emit(f"- 適用範囲: {source['scope']}")
        emit(f"- 現行であることの確認: {source['currentness']}")
        emit("")
        emit("取得したファイル(再確認用)。PDF の出典ページは、この表の最初の PDF のページ番号で示す。")
        emit("")
        emit("| 形式 | URL | サイズ(バイト) | ページ数 | 最終更新(サーバー表示) | SHA-256 |")
        emit("|---|---|---|---|---|---|")
        for item in source["retrieved_files"]:
            emit(f"| {item['format']} | <{item['url']}> | {item['size']} | {item.get('pages', '-')} | {item.get('last_modified', '-')} | `{item['sha256']}` |")
    emit("")
    emit("## 再確認の方法")
    emit("")
    emit("公式資料が改定されていないかは、次のコマンドで確かめる。ネットワークを使うので、日常の検査(`check_kokugo.py`)とは別に、規則を更新するときだけ実行する。リポジトリの `tools/` にあり、配布物には入らない。")
    emit("")
    emit("```bash")
    emit("python3 tools/update_kokugo_sources.py verify")
    emit("```")
    emit("")
    emit("SHA-256 が記録と一致しない資料は、公式側で内容が変わった可能性がある。規則の根拠(節・ページ)を読み直してから、`data/kokugo-sources.json` と規則データを更新する。HTML のページは、サイトの見た目の更新でも変わるので、不一致は本文を読んで判断する。")
    emit("")
    emit("## 取得できなかった資料")
    emit("")
    emit("- 「法令における漢字使用等について」(内閣法制局長官決定)。「公用文作成の考え方」と内閣訓令から参照されているが、原資料は取得していない。この skill は法令の表記を検査しない。")
    emit("- 「表外漢字字体表」(平成12年国語審議会答申)と「常用漢字表の字体・字形に関する指針」(平成28年文化審議会国語分科会報告)。取得しておらず、字体の検査は行わない。")
    emit("- 文部科学省ウェブサイト利用規約のページは、証明書の検証に失敗して直接取得できなかった。要約でのみ確認した。")
    return "\n".join(lines) + "\n"


def render_notation_md(rules: List[dict]) -> str:
    def cell(rule, profile):
        mapping = rule["profiles"][profile]
        mark = CATEGORY_MARKS[mapping["category"]]
        return mark if mapping["basis"] == "source" else mark + "※"
    def sources_cell(rule):
        refs = []
        for s in rule["sources"]:
            pages = f" ({s['pages']})" if s.get("pages") else ""
            refs.append(f"`{s['source_id']}` {s['locator']}{pages}")
        return "<br>".join(refs)
    lines: List[str] = []
    emit = lines.append
    emit("# 国語の表記・用法の規則")
    emit("")
    emit("`data/kokugo-rules.json` の規則を、分野ごとに一覧にする。この表は規則データから生成した。規則の中身(適用条件、例外と許容形、保護対象、修正例と保持例、機械検出できる範囲、文脈判断が必要な範囲)は、規則データを読む。出典の詳細は [kokugo-sources.md](kokugo-sources.md) にある。")
    emit("")
    emit("適用設定の選び方と判定区分の意味は [kokugo-policy.md](kokugo-policy.md)、`official` の運用は [kokugo-official.md](kokugo-official.md) にある。")
    emit("")
    emit("表の見方:")
    emit("")
    emit("- 区分は、適用設定(general-tech、public-explanation、official)ごとに、規則データが決めている。`accepted_variant` は誤りではない。`error` は太字で示す。")
    emit("- 区分の末尾の `※` は、その区分がこの skill の運用判断であり、公式資料の規定ではないことを示す(規則データの `basis: skill-policy`)。")
    emit("- 規則 ID の末尾が示す分野は、ID の2番目の語である(KANJI、KANA、OKURI、GAIRAI、NUM、PUNCT、EXPR、IJIDOKUN、CONSIST、REF)。")
    emit("- 『出典』の資料 ID は [kokugo-sources.md](kokugo-sources.md)。PDF の出典はページを添える。")
    emit("")
    for family, title, notes in FAMILY_TITLES:
        group = [candidate for candidate in rules if candidate["family"] == family]
        if not group:
            continue
        emit(f"## {title}")
        emit("")
        for n in notes:
            emit(f"- {n}")
        emit("")
        if family == "reference":
            emit("| ID | 内容 | 参照するとき | 未検査の範囲 | 出典 |")
            emit("|---|---|---|---|---|")
            for rule in group:
                emit(f"| `{rule['id']}` | {rule['title']} | {rule['reference_when']} | {rule['not_checked']} | {sources_cell(rule)} |")
        else:
            emit("| ID | 内容 | general-tech | public-explanation | official | 出典 |")
            emit("|---|---|---|---|---|---|")
            for rule in group:
                prov = {"primary-source": "", "primary-source-derived": "", "skill-policy": " (運用判断)"}[rule["provenance"]]
                emit(f"| `{rule['id']}` | {rule['title']}{prov} | {cell(rule, 'general-tech')} | {cell(rule, 'public-explanation')} | {cell(rule, 'official')} | {sources_cell(rule)} |")
        emit("")
    emit("## 規則の読み方")
    emit("")
    emit("各規則の `provenance` は、規則のどこまでが公式資料の規定かを示す。")
    emit("")
    emit("- `primary-source`: 資料の規定そのもの。検出する語や形が、資料に書かれている。")
    emit("- `primary-source-derived`: 資料の例示や原則を、この skill が活用形や条件へ広げたもの。広げた部分は各規則の `skill_decisions` に書いてある。")
    emit("- `skill-policy`: この skill の運用判断。公式資料が定めていない確認を、判断材料として示す。error にはならない。")
    emit("")
    emit("`error` を出せるのは、内閣告示または内閣訓令を根拠に挙げる規則だけである(`validate_kokugo_rules.py` が検査する)。建議・報告・答申(考え方、異字同訓、敬語の指針)と、この skill の運用判断は、recommendation か needs_context までにとどまる。")
    return "\n".join(lines) + "\n"


def render_all() -> dict:
    registry = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
    rules = json.loads(RULES_JSON.read_text(encoding="utf-8"))["rules"]
    return {SOURCES_MD: render_sources_md(registry), NOTATION_MD: render_notation_md(rules)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="kokugo-sources.md と kokugo-notation.md を規則データから生成する。")
    parser.add_argument("--check", action="store_true", help="書き換えずに、最新かどうかだけ確かめる(古ければ終了コード 1)")
    args = parser.parse_args(argv)
    stale = []
    for path, text in render_all().items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        stale.append(path)
        if not args.check:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path}")
    if args.check:
        for path in stale:
            print(f"out of date: {path} (run: python3 tools/render_kokugo_docs.py)")
        if not stale:
            print("kokugo documents are up to date")
    return 1 if (args.check and stale) else 0


if __name__ == "__main__":
    sys.exit(main())
