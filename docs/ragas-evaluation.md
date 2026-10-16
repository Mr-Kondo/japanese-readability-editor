# Ragas による自動評価（任意・開発用）

Issue #45。`tools/ragas_readability.py` は、推敲候補を原文と照合して Ragas で採点する開発用CLIです。既存の標準ライブラリだけの手動・表層検証は変えません。Ragas は評価基盤であり、日本語の推敲品質を検証済みの指標ではありません。**人手確認済みの日本語ケースで評価器の有効性を調べるまで、採用する指標は確定していません。**

## 導入

Ragas は任意の依存です。スキルの配布物、通常のオフライン処理、CI には含めません。専用の仮想環境に入れます。

```bash
python3 -m venv .venv-ragas
.venv-ragas/bin/python -m pip install -r tools/requirements-ragas.txt -c tools/ragas-constraints.txt
.venv-ragas/bin/python tools/ragas_readability.py check
```

`check` は通信せず、Ragas・固定版・Claude CLI の有無と、Ragas を import できるかを調べます。

### 固定した版

| 項目 | 内容 |
|---|---|
| `ragas` | 0.4.3（PyPI の最新、Apache-2.0、Python 3.9 以上） |
| `langchain-community` | **0.3.31 に固定**。0.4.2 だと `import ragas` が `ModuleNotFoundError: langchain_community.chat_models.vertexai` で失敗する（依存を最新で解決すると起こる） |
| 解決版の記録 | `tools/ragas-constraints.txt`（約90パッケージ） |
| 動作を確認した環境 | Linux、Python 3.13.16。macOS は未検証 |

依存は `langchain`、`openai`、`datasets` など多く、必須化しない判断の根拠です。

### 使う API と使わない API

Ragas 0.4.3 の公式 docs は、同じページに旧APIと現行APIが混在しています。現行のものだけを使います。

| 使う（現行） | 使わない（旧） |
|---|---|
| `ragas.metrics.collections.FactualCorrectness`、`await metric.ascore(response=, reference=)` | `SingleTurnSample`、`single_turn_ascore` |
| `ragas.metrics.DiscreteMetric`（項目別rubric、日本語プロンプトを自作） | `AspectCritic`。`ragas.metrics` からの import は非推奨で、警告が案内する `collections` 側にも 0.4.3 には存在しない |

## 実行

```bash
# 準備のみ。本文は送信せず、送信範囲と呼出し数の上限を表示して plan.json に保存する
.venv-ragas/bin/python tools/ragas_readability.py score --input evals/ragas-calibration/artificial-cases.json --out-dir /tmp/jre-ragas
# Claude CLI へ送信して採点する
.venv-ragas/bin/python tools/ragas_readability.py score --input evals/ragas-calibration/artificial-cases.json --out-dir /tmp/jre-ragas-run --execute
```

- 入力は `review_readability.py` と同じ cases JSON（モードBのみ）です。ID・入力ハッシュ・原文／候補／依頼／文脈／対象読者の検査を再利用します。
- `--execute` を付けない限り、どこにも送信しません。**`--execute` は依頼・資料・原文・候補・対象読者を Claude CLI へ送信し、利用枠を消費します。**
- 評価器 LLM は、既存の `evaluate_readability.py` と同じ Claude CLI（sonnet / medium、ツールなし）をアダプタで接続します。API キーは不要です。アダプタは JSON スキーマの指示をプロンプト末尾に付け、逐次実行し、同一プロンプトは再利用します。Ragas 本来の構造化出力経路（instructor）は通りません。
- 出力先は新規ディレクトリのみで、上書きしません。終了コードは `0=完了`、`1=採点に失敗あり`、`2=入力・環境・保存エラー`。

## 採点の内容

| 区分 | 内容 | 状態 |
|---|---|---|
| FactualCorrectness（precision／recall） | response＝候補、reference＝原文。原文との整合であり、世界の事実の真偽ではない | 候補。校正前 |
| 日本語rubric（`--metrics rubric`） | 否定・条件・主体・義務の強さ・数値・原文にない具体化・不要な変更・論旨と語り口を、観点ごとに `pass/fail/uncertain` と引用付きの理由で判定する。観点の組は `--profile`（`core`、`gov-org`、`tech`、`essay`、`all`）で選ぶ | 暫定。校正後に確定する |
| 読みやすさ（`--metrics readability`） | 意味保持と分けて `better/same/worse/uncertain`。短文や低い漢字率だけを高評価にしない | 暫定 |
| Faithfulness | 未実装。precision との重複と費用を比べ、不要なら採用しない | 校正後に判断 |
| jReadability | 未確認。学習者向けの補助候補で、用途・辞書・利用条件を確認してから採否を決める | 未着手 |
| 保護対象（コード・API・数値・URL・モードC） | 既存の機械検査を使う。LLM採点で代替しない | 既存 |
| 実理解 | 既存の人手理解問題を使う。モデルのQA正答を人の理解度として報告しない | 既存 |
| 検索用指標、参照文なしの BLEU/ROUGE/SARI、埋込み類似度のみの合否 | 主要指標に採用しない | 方針 |

### FactualCorrectness の扱い

- **主張抽出は `atomicity=high`、`coverage=high` を既定にします。** Ragas の既定は `low/low` で、`coverage=low` の例は細部を意図的に落とします（docs の例では「food critic」が落ちる）。条件・例外の脱落を見たい本用途では不利と考えた**仮説**です。設定間の差は校正で測ります。
- precision は候補の主張のうち原文に支持される割合、recall は Ragas の式では `TP/(TP+FN)` で、TP は**候補の主張**のうち原文に支持されるものの数です。「原文の主張のうち候補が支持する割合」ではありません。後者は `reference_claims.coverage` として別に保存します。F1 だけで報告しません。
- 主張を1件も抽出できないと、Ragas は NLI を呼ばず**黙って 0.0 を返します**。本ツールはこれを `no_claims`（値なし）として分け、0点にしません。
- 主張・判定は LLM 呼出しのログから再構成し、再計算した値が Ragas の値と一致するか（`consistent`）を記録します。一致しなければ警告します。
- 候補にあり原文で支持されない主張（追加・矛盾）と、原文にあり候補で支持されない主張（欠落）を、理由付きで保存します。
- Ragas の主張抽出・NLI のプロンプトは英語の指示と英語の例です。日本語への適合は未検証で、プロンプトを日本語へ翻訳しても適合したことにはなりません。

## 記録されるもの

出力先に `tasks.json`（入力）、`plan.json`、`ragas-run.json`、`ragas-run.md`、`raw/`（呼出しごとの生応答）を保存します。

- 設定: Ragas とその依存の版、Python、OS、Claude CLI の版とフラグ、主張抽出設定、rubric の版とハッシュ、使った観点。温度・乱数種は CLI から指定できないため「不明」と記録します。
- 呼出しごと: プロンプトのハッシュ、モデル識別子、生応答のファイル、再利用の有無、所要時間、費用（定価換算）、失敗。CLI は `claude-sonnet-5-5` と `claude-haiku-5-5` の両方を報告することがあり、そのまま記録します。
- ケースごと: 主張数、支持／不支持の主張、観点別の値と理由、失敗。
- 失敗・主張なし・判断不能は、0点や合格に変換しません。`ragas-run.md` は値の記録で、合否や総合点ではありません。

## 校正の状況

`evals/ragas-calibration/` に、評価器の動作確認用の**人工ケース13件**とその期待ラベルがあります（無変更の対照、正当な言い換え、数値変更、例外の脱落、否定の反転、必須→推奨、部分否定→全否定、頻度・時制、原文にない確定表現、時期の入れ替え）。

- ラベルは**構成によるもので、人の確認前**です（`confirmed_by` が空）。人手確認済みとして扱いません。
- 元はデジタル庁文書群の**調整用側の出典だけ**です。最終評価用の出典は使っていません（#45 の「校正用と未使用検証用を元文書単位で分ける」）。
- 人工例の成績は、実運用の見逃し率や誤警告率ではありません。実際のモデル出力での成績とは分けて報告します。

## #45 の進捗

| 作業 | 状態 |
|---|---|
| 安定版・API・Python互換性・ライセンスの確認と版の固定 | 完了（Linux/Python 3.13。macOS 未検証） |
| 既存のJSON/ID/ハッシュの再利用と対応の検証 | 完了（`read_tasks` を再利用） |
| 任意依存の小さな実行手段、送信範囲の説明 | 完了 |
| 日本語のinstruction・主張抽出・推論・採点例の確認 | rubric は日本語で作成。Ragas 既定プロンプトは英語のままで未検証 |
| 引用・人物の台詞・著者の評価の扱い、原文の誤り訂正の分離 | rubric の指示に「訂正は理由に書き他の観点と混ぜない」を入れた。引用・台詞の扱いは未実装 |
| 人手確認済み校正ケース | 人工13件を用意（人の確認前）。実出力・人手確認済みは未着手 |
| 各文書群で人手判定と照合（見逃し・誤警告・判断不能・失敗） | 未実施。人手判定が必要 |
| 元文書単位で校正用と未使用検証用を分離 | 校正ケースは調整用側のみ。検証用の分離方針は #40 の分割に従う |
| 公式スコアと独自rubricの分離保存、設定・モデル・費用・時間の記録 | 実装済み。費用は CLI の生応答にある定価換算の値を呼出しごとに記録（取得できなければ「不明」で、0 にしない） |
| 既存LLM評価との比較、最小構成の選択 | 未実施 |
| 群別rubricの記録 | `--profile` の暫定版。校正後に確定する |
| 接続・入力不整合・タイムアウトの検証（実API／モックの区別） | 偽LLMでのテストを実装。実接続（Ragas＋Claude CLI）の結果は未記載（スモーク実行中） |
| 採用／補助／見送りの文書化、#44 の主要／補助指標の確定 | 未実施（校正が前提） |
