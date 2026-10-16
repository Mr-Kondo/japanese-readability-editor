# 公開文書による評価データ整備の計画

Issue #38 の確定事項です。公開された実文書で、意味を保った読みやすさの改善と、不必要に変更しない判断を調べます。公開文書は正解ラベル付きデータではありません。既存の人工例に追加する予備評価であり、効果は未測定です。

## 文書群と優先順

| 優先 | 文書群 | Issue | 状態 |
|---|---|---|---|
| P0 | デジタル庁（手順・責任・要件） | #40、[文書群の手順](public-documents-digital-agency.md) | 原本取得済み。候補11件・採用0件（人の確認待ち） |
| P0 | Python日本語文書 | #41 | 未着手 |
| P0 | Kubernetes日本語文書 | #42 | 未着手 |
| P0 | 青空文庫の随筆（補助群） | #39 | 未着手 |
| P1 | IPAのOSS・OSPO資料 | #43 | 未着手 |
| P1 | 評価結果に基づくスキル改良 | #44 | 本データの整備後 |
| P0 | Ragas等の自動指標の校正 | #45 | 別計画 |

青空文庫は文学・歴史的文体の補助群です。業務・技術文書の結果と混ぜて集計しません。大量収集や新しい評価基盤より、文脈、保持要件、理解問題の人手確認を優先します。

## 共通の決定事項

### 1. 台帳で追跡する

出典・抜粋・保持要件・理解問題・分割は、文書群ごとではなく一つの台帳 `evals/public-documents/manifest.json` に記録します。形式の検査は `tools/validate_public_corpus.py` が行います（標準ライブラリのみ、通信・書き込みなし）。

| 単位 | 必須の記録 |
|---|---|
| 出典（`sources[]`） | `group`、`title`、`provider`、`url`、`version`（版・コミット）、`format`、`retrieved_on`、原ファイルの `raw_sha256`、`lineage_id`（旧版・別形式・対訳があるとき同じ値） |
| 利用条件（`license`） | 本文（`body`）と書誌情報（`bibliographic`）を分け、それぞれ `name`、`url`、`checked_on`、`redistribution`。本文には `attribution` と `modification_notice` |
| 抜粋（`excerpts[]`） | `source_id`、`locator`（抜粋範囲）、`correspondence`（原本との対応の確認者・確認日）、`text`、`text_sha256`、`transform_history`、`status`、`split` |
| 保持要件（`preserve[]`） | `kind`、抜粋内の `quote`、`allowed_changes`、`confirmed_by`、`reason` |
| 理解問題（`questions[]`） | `comprehension_readability.py` と同じ項目。検証は同ツールの規則を再利用 |

- 原本（PDF・Word・HTML）はリポジトリへ置きません。取得元と SHA-256 で特定します。可変URLの内容だけで版を特定せず、`version` に版・コミット・取得時点を残します。
- 台帳へ本文を入れてよいのは、出典の本文条件が `redistribution: allowed` のときだけです。検証ツールは、それ以外の出典の本文を拒否します。
- Word（docx）は `tools/extract_docx_text.py` で段落・表の順に取り出せる（標準ライブラリのみ。自動番号は復元しない）。抜粋範囲 `locator` はその識別子（P<連番>）で書く。
- `transform_history` は、原本のハッシュから抜粋の `text_sha256` までの変換を一段ずつ記録します（抽出、ルビ・注記の処理、範囲の切り出し等）。最初の入力が `raw_sha256`、各段の入力が直前の出力、最後の出力が `text_sha256` と一致しなければ拒否します。原本は上書きしません。
- 利用条件は、データの条件です。リポジトリのコード用ライセンス（`LICENSE`）で置き換えません。本文と書誌情報の条件、第三者の引用・図表も分けます。第三者の内容を含む抜粋は採用しません（`third_party_content: none`）。
- 帰属・加工表示は採用文書ごとに `attribution` と `modification_notice` へ書きます。推敲文を出典元の公式文書として提示しません。

### 2. 抜粋を選ぶ

- 文書群ごとに最初は10抜粋程度、複数の独立した原本から選びます。この件数は運用上の出発点で、統計的十分性の根拠ではありません。
- 結果を見る前に、候補（`candidate`）を台帳へ記録します。採用（`adopted`）と除外（`excluded`、理由必須）の数と理由を残します。生成結果を見てから都合のよい抜粋だけを選びません。
- 自己完結しない抜粋、前後の文脈に依存する抜粋、抽出で見出し・表・脚注・注記を失った抜粋は、修復するか除外します。
- 変更不要の対照例（`role: no_change_control`、理由 `no_change_reason`）を各群に含めます。原文をそのまま返すことを失敗扱いにしません。

### 3. 元文書単位で分割する

- 調整用（`tuning`）と最終評価用（`final`）は原本単位で分けます。同じ `lineage_id` の章・抜粋・別形式・旧版・対訳は同じ側に置きます。同一本文のハッシュが両側にあれば拒否します。
- 分割は、モデルの出力を見る前に決めて台帳へ固定します。可能なら著者・系列の偏りも抑えます（検証ツールは検査しません。人が確認します）。
- 調整に使った抜粋は、スキル改良後の最終評価に使いません（#44）。

### 4. 原文を唯一の正解にしない

保持すべき主張・条件・例外・主体・数値・文の働きを `preserve` に書き、許容する変更を `allowed_changes` に書きます。人が原文と照合した確認者と理由を残します。確認者のいない保持要件は採用済みの抜粋に置けません。LLMの判定は補助であり、保持要件や理解問題の正解にしません。

### 5. 評価を分ける

| 区分 | 内容 | 使うツール |
|---|---|---|
| 自動検査 | 数値・URL・コード・否定・条件等の差。意味保持の合格にはしない | `review_readability.py auto`、`compare_readability.py auto` |
| 人手評価 | 意味保持、読みやすさ、引用付きの定性指摘 | `compare_readability.py` |
| 理解問題 | 一候補だけを読んで答える | `comprehension_readability.py` |
| LLM判定（補助） | `--judge` の評点・理由。人手判定との照合に使う | `feedback_readability.py calibrate` |

主観評点と実理解を合算した総合点は作りません。未実施・失敗・判断不能・欠測は合格にせず、文書群別に残します。

### 6. 実行条件を記録する

各ケースの `request`、`audience`、`provenance.model`、`provenance.skill_version` を記録します。生成設定（温度等）は `provenance` に追記します。割付は準備ツールが保存する `organizer.json` が持ちます。公開文書は学習データに含まれた可能性があり、不明として扱います。社内文書での効果を保証しません。

## 既存ツールとの接続

新しい評価基盤は作らず、既存の入力形式に合わせます。実際の入力検査から分かった制約です。

| 制約 | 帰結 |
|---|---|
| `compare_readability.py`・`statistics_readability.py` は `document_id` を独立文書の単位として数え、同じ `document_id` は同じ向きで割り付ける | `document_id` は**原本（`source_id`）**にする。同じ原本の複数抜粋を独立文書にしない。#44 が確認を求めた点は、この設定で原本単位の集約になる |
| `comprehension_readability.py` は `document_id` の重複を拒否する（一人に同じ原稿を一度だけ配る） | `document_id` は**抜粋ID**にし、1回の配布に含める抜粋は**1原本につき1つまで**にする。同じ原本の別抜粋は別の配布に回す |
| 理解問題の集計は記述値で、区間推定はない | 理解問題から効果推定や信頼区間を作らない（#44 の注意と同じ） |
| 匿名比較・理解問題はモードB専用 | 小説（モードD）や現代語化を、Bとして採点しない（#39 の境界） |
| 確認記録は `compare_readability.py prepare` の `organizer.json` から作る | 回帰ケース化（`feedback_readability.py`）は匿名比較を実施した後 |

`validate_public_corpus.py` は、これらを `--cases` で検査します。

## 手順

1. 出典を台帳へ `planned` で登録する。取得後に `collected` へ変え、版・取得日・`raw_sha256`・利用条件を記録する。
2. 抜粋を `candidate` で登録し、原本と照合して `adopted` / `excluded` にする。保持要件と理解問題を人が確認する。
3. 台帳を検査する。

   ```bash
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json
   # candidate を採用するまでに残る不備（人の確認）を一覧する
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --readiness
   ```

4. 既存CLI用の `cases` JSON を作る。`original` は台帳の `text` をそのまま使う。実行前に台帳との一致と分割を検査する。

   ```bash
   # 比較・統計: document_id は原本
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --cases cases.json --split tuning
   # 理解問題: document_id は抜粋ID
   python3 tools/validate_public_corpus.py --manifest evals/public-documents/manifest.json --cases comprehension.json --split tuning --document-id-by excerpt
   ```

5. 以降は[文章評価ツール](human-evaluation.md)の手順に従う。

検証ツールの終了コードは `0=合格`、`1=台帳または cases に不備`、`2=入力を読めない`。検査するのは形式と整合性だけです。保持要件の意味、利用条件の解釈、抜粋と原本の一致、理解問題の正解は人が確認します。

## 対象外

社内実務での効果の保証、自律的なスキル更新、学習済みでないことの証明、改良率の事前断定。NTTの非営利・継承条件付き資料、他媒体利用の案内があるPostgreSQL日本語版、BCCWJは初回対象に含めません。必要になった時点で条件を別途確認します。

## 現在の状態

- 共通の台帳形式、検証ツール、docx 抽出器、文書群手順（デジタル庁）を用意した。
- デジタル庁（#40）は原本5文書を取得し、候補11件・除外6件を台帳に記録した。保持要件・理解問題は草案で、**人の確認と採用は0件**。詳細は[文書群の手順](public-documents-digital-agency.md#状態2026-10-16-時点)。
- Python（#41）、Kubernetes（#42）、青空文庫（#39）、IPA（#43）は未着手。各Issueで出典と固有の保持要件を台帳に追加する。
- 生成・評価・自動指標（#45）は未実施。効果は未測定。
