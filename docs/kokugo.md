# 国語の表記・用法の検査

文化庁が公開する国語の表記・用法の基準(内閣告示、内閣訓令、建議など)に基づく規則を、文章へ当てる機能です。規則は、出典と適用条件を持つデータとして Skill に入っています。検査は `check_kokugo.py` が行い、読み取り専用で、ネットワークを使いません。

この機能は、読みやすさの改善(構成、論理、文の長さ)を置き換えるものではありません。表記の修正より先に、構成と論理を確認します。

## 資料の性格を区別する

文化庁の資料は、すべてが同じ強さの規則ではありません。性格に応じて、判定の強さを変えています。

| 性格 | 資料 | 判定の強さ |
|---|---|---|
| 内閣告示 | 常用漢字表、現代仮名遣い、送り仮名の付け方、外来語の表記、ローマ字のつづり方 | 一般の社会生活の目安・よりどころ。専門分野や個々人の表記には及ばない。明確な条件を満たすときだけ `error` |
| 内閣訓令 | 公用文における漢字使用等について | 各行政機関の公用文が対象。`official` でだけ強く扱う |
| 建議・報告・答申 | 公用文作成の考え方、「異字同訓」の漢字の使い分け例、敬語の指針 | 手引・参考。`recommendation` か `needs_context` まで |
| この skill の運用判断 | 区分の割り当て、混在の確認、文の長さの目安 | 公式資料の規定と区別する |

文の長さの目安(30〜45字、46字以上を候補、段落は200字以上)は、この skill の運用上の目安です。文化庁の基準ではありません。「公用文作成の考え方」の解説は、一文の長さを「適当な長さは一概に決められないが、50〜60字ほどになってきたら読みにくくなっていないか意識するとよい」と述べるにとどまります。

採用した資料、確認日、ハッシュは [references/kokugo-sources.md](../skill/japanese-readability-editor/references/kokugo-sources.md) にあります。

## 適用設定

モード A・B・C とは独立した設定です。`--profile` で指定します。

| 設定 | 用途 | 動作 |
|---|---|---|
| `general-tech`(既定) | 技術・業務文書 | 明確な誤りを確認し、専門用語・組織の表記・許容形を尊重する |
| `public-explanation` | 一般向けの解説・案内・広報 | 読み手に応じた表記を検討する。説明不足は、原文に根拠がなければ指摘にとどめる |
| `official` | 公用文基準が明示された文書 | 公用文固有の表記・用語の運用も確認する |

指定がなければ `general-tech` です。文体が堅いという理由だけで `official` にはしません。組織の用語集や表記指定があれば、先に確認します。公用文への準拠指定と競合するときは、黙って片方を適用せず、競合を示します。

## 判定区分

| 区分 | 意味 |
|---|---|
| `error` | 適用条件と修正根拠が明確な誤り |
| `recommendation` | 選択した基準では推奨されるが、一般的な誤りとは限らない |
| `accepted_variant` | 許容される表記 |
| `needs_context` | 意味・品詞・文脈の確認が必要 |
| `excluded` | 保護対象など、適用しない箇所 |

許容形や適用範囲外の表記を、誤りとして報告しません。文脈に依存する候補を、確定した誤りとして扱いません。常用漢字は字種だけを照合し、音訓は登録した語だけを確かめます。異字同訓は、読みや世論調査の多数派では決めず、常に要確認にとどめます。

表記をどれに合わせるかは、次の順です。

1. 明示された表記基準と、組織の用語集を確認する。
2. 指定がなければ、適用設定に従う。
3. 複数の表記が許容される場合にだけ、文書内の統一を判断材料にする。
4. 多数派であることを理由に、明確な誤りを広げない。

## 実行する

Skill のディレクトリで実行します。Windows では `python3` ではなく `python` の場合があります。

```bash
python3 scripts/check_kokugo.py document.md --profile general-tech
python3 scripts/check_kokugo.py document.md --profile official --json
python3 scripts/check_kokugo.py docs/ --profile public-explanation --glossary glossary.txt
python3 scripts/check_kokugo.py --list-rules
python3 scripts/validate_kokugo_rules.py
```

| オプション | 内容 |
|---|---|
| `--profile` | `general-tech`(既定)、`public-explanation`、`official` |
| `--json` | JSON で出力する。`accepted_variant` と `excluded` も全件を含む |
| `--glossary FILE` | 組織の用語集(複数指定可)。形式は下の「用語集」 |
| `--fail-on` | 終了コード 1 にする水準。`error`(既定)、`recommendation`、`needs_context`、`never` |
| `--all` | テキスト出力でも `accepted_variant` と `excluded` を表示する |
| `--format` | `auto`(拡張子で判断)、`markdown`、`plain` |
| `--data-dir` | 規則データのディレクトリ(既定は Skill の `data/`) |
| `--list-rules` | 規則の一覧(ID、自動判定の有無、設定ごとの区分) |

## 終了コード

| コード | 意味 |
|---|---|
| 0 | 検査を終え、`--fail-on` で指定した水準以上の指摘がない |
| 1 | 検査を終え、指定した水準以上の指摘がある(既定は `error` があるとき) |
| 2 | 引数、入力ファイル、用語集、規則データの不備で、検査を完了できなかった |

`recommendation` と `needs_context` は、既定では終了コードを変えません。`validate_kokugo_rules.py` は、0=問題なし、1=問題あり、2=データを読めない、です。

## 出力

JSON の形式は固定しています(`schema_version: 1`)。キーの追加や削除は、`schema_version` を上げて行います。

| 階層 | キー |
|---|---|
| 最上位 | `schema_version`, `tool`, `profile`, `rules_version`, `fail_on`, `exit_code`, `files`, `summary`, `coverage` |
| `files[]` | `file`, `sha256`(入力のバイト列), `markdown`, `findings`, `counts` |
| `findings[]` | `rule_id`, `category`, `line`, `column`, `end_line`, `end_column`, `offset`, `length`, `text`, `candidates`, `title`, `reason`, `reason_code`, `source_ids`, `provenance`, `detail` |
| `coverage` | `profile`, `tokenizer`, `rules_checked`, `rules_reference_only`, `not_checked`, `limits`, `glossary`, `disclaimer` |

- 位置の `offset` は、BOM を除き、改行を LF にそろえた後の文字数です。`line` と `column` は 1 から数えます。
- `candidates` は修正の候補です。本文は書き換えません。`needs_context` の候補は、示さないことがあります(異字同訓など)。
- `provenance` は、規則が公式資料の規定そのもの(`primary-source`)か、資料の例示を広げたもの(`primary-source-derived`)か、この skill の運用判断(`skill-policy`)かを示します。
- `detail.count` は、同じ表記を最初の1か所にまとめたときの回数です(表外漢字、異字同訓)。
- 同じ入力、規則、設定からは、同じ出力(順序を含む)が得られます。実行日時や環境の値は入りません。

## 保護対象と用語集

次の箇所は、規則に当てはまる表記があっても適用せず、`excluded` として示します。

- YAML frontmatter
- fenced code block、インラインコード
- URL とリンク先(日本語のパスを含む)
- ブロッククォート(引用)
- HTML コメント、HTML タグ
- `<!-- kokugo-ignore-start -->` から `<!-- kokugo-ignore-end -->` までの範囲
- 用語集の `protect:` に書いた語

固有名詞・専門用語は、自動では識別できません。用語集で指定します。

```text
# 組織の用語集(UTF-8、1行に1語。# から始まる行はコメント)
protect: 髙橋            この語に重なる箇所には規則を適用しない
protect: Kubernetes
use: サーバ              組織が指定する表記
```

接頭辞のない行は `protect:` として扱います。`use:` の表記が、適用設定の推奨と食い違うときは、黙って片方を適用せず、`needs_context`(`reason_code: glossary:use-conflict`)として食い違いを示します。

## 検査していないもの、限界

出力の `coverage` に、検査したものと、していないものを示します。『指摘なし』は『規則に違反していない』ことを意味しません。

- 敬語(敬語の指針)、ローマ字のつづり方、字体の適否は検査しません。参照先を整理しただけです(`KOKUGO-REF-001` から `003`)。
- 数字・符号は、『○か所』『○か月』、全角・半角数字の混在、読点の混在、句点のピリオドだけです。
- 異字同訓は、133項目のうち選んだ16項目の漢字の形を要確認として示すだけです。
- 規則に登録した語・表記だけを検査します。登録していない語は未検査です。
- 形態素解析を使いません(`tokenizer: none`)。品詞や用法が決まらない語(『きわめて』『はじめて』『申し込み、』など)は、確定した指摘にせず `needs_context` に下げます。形態素解析を使えば精度は上がりえますが、環境によって出力が変わるため、初期実装では使っていません。
- 名詞か動詞の連用形かは、直後が『が』『を』『の』のときだけ名詞と確定します。
- 意味の保存、日本語の正しさ全体、構成や論理の適否は保証しません。

## 規則データ

| ファイル | 内容 |
|---|---|
| `data/kokugo-rules.json` | 規則。ID、内容、適用設定ごとの区分、適用条件、例外と許容形、保護対象、出典(資料 ID、節、PDF のページ)、修正例と保持例、機械検出できる範囲、文脈判断が必要な範囲、`provenance`、`skill_decisions` |
| `data/kokugo-sources.json` | 資料の記録。正式名称、発出主体、種別、告示・発出日、公式 URL、確認日、取得したファイルのサイズと SHA-256 |
| `data/joyo-kanji.json` | 常用漢字表の字種(2136字)と音訓。公式の PDF から機械的に取り出した派生データ |
| `data/ijidokun.json` | 「異字同訓」の漢字の使い分け例の133項目。公式の PDF から機械的に取り出した派生データ |

`scripts/validate_kokugo_rules.py` は、次を検査します。

- ID の重複、参照切れ、必須項目の不足、不正な適用設定・区分
- 出典のない規則、PDF の出典のページの欠落・範囲外
- `error` の根拠(内閣告示・内閣訓令を挙げない規則や、この skill の運用判断の規則は `error` にできない)
- 正規表現と候補のテンプレート、曖昧な語の理由、省略形が全形の部分列であること
- 修正例と保持例を検査エンジンに通した結果
- 常用漢字表が2136字であること、規則が主張する『表にない音訓』が表と食い違わないこと
- 使われていない出典がないこと

## 規則を更新する

規則データ(`data/kokugo-rules.json`)と資料の記録(`data/kokugo-sources.json`)を変えたら、規則の一覧(`references/kokugo-notation.md`)と出典(`references/kokugo-sources.md`)を、次のコマンドで作り直します。この2つの文書は手で書き換えません。

```bash
python3 tools/render_kokugo_docs.py
python3 tools/render_kokugo_docs.py --check
```

公式資料の更新を確かめる処理は、日常の検査から分けています。ネットワークを使うのは、リポジトリの `tools/update_kokugo_sources.py` だけです。Skill の外にあり、配布物には入りません。

```bash
python3 tools/update_kokugo_sources.py verify
```

記録した URL を取得し、サイズと SHA-256 を照合します。不一致の資料は、公式側で変わった可能性があります。規則の根拠(節・ページ)を読み直してから、記録と規則データを更新します。

常用漢字表と異字同訓のデータを作り直すときは、`pypdf` が要ります。システムの Python へは入れず、仮想環境を使います。

```bash
python3 -m venv .venv-sources
.venv-sources/bin/pip install pypdf
.venv-sources/bin/python tools/update_kokugo_sources.py extract-joyo 常用漢字表.pdf
.venv-sources/bin/python tools/update_kokugo_sources.py extract-ijidokun ijidokun_140221.pdf
```

抽出した件数が公式の件数(字種 2136、異字同訓 133項目)と一致しないときは、データを書き出さずに失敗します。

## 検証とテストをまとめて実行する

```bash
python3 tools/check_all.py
```

Skill の検証、規則データの検証、生成した文書の最新確認、全テストを順に実行します。ネットワークは使いません。1つでも失敗すれば終了コード 1 です。テストだけを実行するときは、`python3 -m unittest discover -s tests -v` です。

テストの期待値は、公式資料の例示・許容・適用範囲と、保存要件から決めています(`tests/kokugo_sources_data.py`)。変更してはいけない反例(許容形、慣用の重ね言葉、保護対象、動詞の連用形など)を、修正例と同数以上含みます。意味保存のテストは、用意したケースでの確認であり、すべての自然言語入力に対する保証ではありません。

## モード C の確認

モード C は、改行と空行の挿入だけを行います。国語の規則を理由に、文言・句読点・語順は変えません。表記上の問題を見つけても、本文は変えず、報告するだけです。

```bash
python3 scripts/verify_preservation.py --strict before.md after.md
```

既定の `verify_preservation.py` は、空白全般を無視します。文と文のあいだの空白を消しても、タブを空白に置き換えても、既存の改行を消しても、合格してしまいます。`--strict` は、改行以外のすべての文字(半角・全角スペース、タブ、不可分スペースを含む)が同一で、改行が減っていないときだけ 0 を返します。

## モード B の照合の限界

モード B では、書き換えの後に `compare_rewrite.py` で意味の変化候補を確認します。数値、単位、条件(限定・残余)、例外の削除、否定の増減、断定の強さは、用意したケースで挙がることを確かめています(`tests/test_kokugo_modes.py`)。次は、現在の照合では挙がりません。人が元の文と見比べます。

- 漢字の名詞だけの主体の入れ替え(利用者→管理者)
- 因果関係の入れ替え
- 近接する2文で打ち消し合う否定の増減

表記の修正で、同じ語の表記違いが `terms` のポインタとして挙がることがあります(サーバ→サーバー。SudachiPy を使わないとき)。判定ではありません。
