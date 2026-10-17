# 利用者のフィードバックを改良に使う

この Skill の結果に問題を見つけた利用者が、その事例を報告し、メンテナーが規則・例の改良に使うための手順です。通信による自動収集はしません。利用者が自分で内容を確かめ、ファイルとして送ります。判定の確定と `skill/` への反映は、メンテナーが人手で行います。

- 利用者向け: [報告する](#報告する利用者向け)
- メンテナー向け: [受け取って改良につなぐ](#受け取って改良につなぐメンテナー向け)
- 効果と限界: [効果の根拠と限界](#効果の根拠と限界)

## 報告する(利用者向け)

### 1. 票を作る

スクリプトを実行できる環境では、Skill の `scripts/make_feedback.py` で票(JSON)を出せます。書き込みも送信もしません。出力を自分でファイルに保存します。

```bash
python3 scripts/make_feedback.py --original before.md --result after.md \
  --type strength_changed --quote "必ず" --mode B --consent-storage > feedback.json
```

- `--original` は Skill に渡す前の文章、`--result` は Skill が返した文章のファイルです。
- `--quote` は問題の箇所です。結果から、そのまま写します(情報が抜けた場合は原文から)。
- `--type` は次のどれかです。`--help` にも載っています。

| `--type` | 問題の内容 |
|---|---|
| `added_content` | 原文にない主体・条件・完了状態・事実を足した |
| `strength_changed` | 必須・推奨・断定・推量などの言い切りの強さが変わった |
| `number_or_negation` | 数値・単位・範囲・否定の数が変わった |
| `meaning_lost` | 情報・条件・例外が抜けた |
| `over_editing` | 直さなくてよい箇所まで書き換えた |
| `unneeded_change` | 変更が不要な文章を変えた |
| `unnatural` | 不自然、または読みにくくなった |
| `other` | 上のどれでもない |

任意の項目: `--mode`(A/B/C/D)、`--severity`(major/minor)、`--comment`(何が問題か、読者への影響)、`--request`(Skill に出した依頼文)、`--skill-version`、`--model`、`--origin`(実際の出力は `model_output`、作った例は `artificial`)。

票の例は [feedback-example.json](feedback-example.json) にあります。人工の文章で、実際の失敗ではありません。

### 2. 同意の意味

| 指定 | 意味 |
|---|---|
| `--consent-storage`(必須) | メンテナーが非公開で保管し、スキル改良の検討に使うことに同意する |
| `--consent-ai`(任意) | 改良案の下書きのために、AI サービス(Claude)へ送ることに同意する。送るのは、メンテナーが確認して書いた引用・根拠・保つこと・禁止だけで、原文と結果の全文は送らない。付けなければ送られない |
| `--consent-publish`(任意) | 匿名化したうえで、公開の回帰ケースや例に使うことに同意する。付けなければ公開されない |

保管は原則として非公開です。保管期間は受領から12か月で、その後は原本を削除します。削除を依頼すると、30日以内に原本・派生物・バックアップを削除し、完了を知らせます。ただし、同意を得て公開済みのものは、リポジトリの履歴から完全には消せない場合があります。

### 3. 送る前に確かめる

- 氏名、連絡先、社内固有の名称、顧客や取引の情報、秘密の数値が入っていないか、`feedback.json` を開いて確かめます。入っていれば、伏せ字にするか、問題の箇所を含む短い範囲に絞ります。
- スクリプトは、メールアドレス・URL・電話番号らしい文字列があれば警告します。これは目安で、機密がないことの保証ではありません。
- 引用は、問題の箇所を含む最小の範囲にします。

### 4. 送る

- **機密を含みうる文書: メール(非公開)で送ります。** 宛先はメンテナーから個別に伝えられます。メールは端末間で暗号化されないので、機密の度合いが高いものは送らないでください。
- **公開してよい内容(機密でなく、伏せ字済み): GitHub Issue に添付してもかまいません。** Issue は公開されます。誤って機密を貼った場合は、すぐにコメントを削除し、メールで連絡してください。

送付後に、判定の結果や改良の反映を約束するものではありません。メンテナーが確認し、同じ種類の失敗が複数の文書・複数の人から確認できた場合に、規則・例の修正を検討します。

## 受け取って改良につなぐ(メンテナー向け)

### 保管

内容そのものを、リポジトリの作業ツリーの外に置きます。暗号化した領域(macOS では FileVault に加えて、暗号化したディスクイメージか暗号化ボリューム)に `feedback-inbox/<送付者ID>/` を作り、届いた票を入れます。メールの添付は移したら受信箱から削除します。ツールは、git の作業ツリーの中にある入力と出力先を拒否します。`.gitignore` に `/feedback-inbox/` もあります。

送付者ID(`[A-Za-z0-9_-]` の40文字まで)は、メンテナーが付けるフォルダ名です。票の自己申告は使いません。同じ人の複数の票は同じフォルダに入れます。

### 手順

```bash
# 取り置き: final 用の文書は、調整に使わない。document_id を一覧にして、受領時に照合する
python3 tools/feedback_loop.py fingerprint final-document.md   # 出力の document_id を JSON 配列 reserved.json に集める

# 1. 受領と検証(通信なし)。出力先は新規フォルダ
python3 tools/feedback_loop.py intake --inbox feedback-inbox --out-dir work/intake --reserved-ids reserved.json
```

`work/intake/` に次が出ます(どれも、作業ツリーの外に置きます)。

| ファイル | 内容 |
|---|---|
| `findings.json` | 検証を通した指摘。送付文を含む。状態は `reported`(利用者の報告で、確認済みではない) |
| `ledger.json` | 本文を含まない台帳(指摘ID、ハッシュ、送付者、同意など)。台帳として残すのはこれだけにする |
| `decisions.json` | 確認記録の雛形。全指摘が `unresolved`、確認者・根拠は空 |
| `rejected.json` | 拒否した票のファイル名と理由(本文は含めない) |

2. **確認(人手)。** `decisions.json` を、原文・結果に照らして埋めます。`confirmed_problem`(問題を確認)、`no_problem`、`unresolved` のどれかを付け、確定した判定には `confirmer`、`reason`、`quote`(結果か原文にそのまま出る引用)が必要です。`confirmed_problem` には、保つべきこと(`preserve`)、禁止すること(`forbid`)、関連規則(`rule_ids`)が必要です。`split` は、調整に使う `tuning` か、最終評価に取り置く `final` です。同じ原本の別の抜粋が複数ある場合は、`source_document` に同じ名前を書いて、1つの文書としてまとめます(空なら原文のハッシュで数えます)。利用者の主張だけで確定しません。確認者・根拠は自動で入りません。

```bash
# 3. 集約と回帰ケース化(通信なし)
python3 tools/feedback_loop.py triage --findings work/intake/findings.json --decisions work/intake/decisions.json --out-dir work/triage

# 4. 改良案の下書き。既定では何も送らず、送る範囲と量を表示して止まる
python3 tools/feedback_loop.py propose --findings work/intake/findings.json --decisions work/intake/decisions.json --clusters work/triage/clusters.json
# 内容を確かめたら、--out-dir と --execute を付けて再実行する(AI 処理に同意した票だけを Claude CLI へ送る)
python3 tools/feedback_loop.py propose ... --out-dir work/propose --execute
```

`triage` は、確認済みで `tuning` の指摘を、失敗の種類と関連規則ごとに、**独立文書数**と**送付者数**で数えます。独立文書は、原文の空白を除いたハッシュで数えます。同じ原本の複数の票、同じ人の再送は重ねません。閾値は、独立3文書以上かつ2人以上の送付者です(暫定。`--min-documents` と `--min-submitters` で変える)。満たすと「規則修正の提案ができる」とし、満たさなければ「経過観察」です。確認済みの指摘は、閾値に満たなくても `regression-cases.json`(既存の `evaluate_readability.py` の形式。モード A/B)に入ります。

`propose` は `skill/` を書き換えません。下書きは `proposals/` に、LLM の下書きである旨を付けて出ます。非公開の送付文に基づくため、公開しません。PR や Issue には、匿名化した人工例に置き換えて書きます。

```bash
# 5. 規則を直したあと、修正前後を同条件で評価し、失敗の種類別に並べる(evaluate_readability.py は、実行時の skill/ の内容で動く。修正前は元のコミットで実行する)
python3 tools/evaluate_readability.py --suite work/triage/regression-cases.json --out-dir work/before --execute   # 修正前のスキルで
python3 tools/evaluate_readability.py --suite work/triage/regression-cases.json --out-dir work/after  --execute   # 修正後のスキルで
python3 tools/feedback_loop.py verify --cases work/triage/regression-cases.json --before work/before/run.json --after work/after/run.json --out-dir work/verify
```

`verify` は、`fixed`、`regressed`、`still_fail`、`still_pass`、`uncertain_or_missing` を種類別に出します。悪化・判断保留・欠測があれば `HOLD` で、改善で相殺しません。`NO_REGRESSION_ON_TUNING_CASES` は、調整に使ったケースで悪化がなかっただけで、改善の確証ではありません。最終評価は、取り置いた `final` の文書で、別に行います(#44)。

### 公開してよいもの

非公開の送付文は、`--consent-publish` のある票でも、匿名化して人工例に直してから公開します。リポジトリに置いてよいのは、`ledger.json`(本文を含まない)と、匿名化・同意済みの例だけです。

## 効果の根拠と限界

この仕組みが改良につながる保証はありません。調べた範囲と、設計への反映は次のとおりです。

| 懸念 | 根拠・意見 | 設計への反映 |
|---|---|---|
| 利用者の評価・報告は、一部に偏り、無作為ではない | 実務の記事は、評価する利用者は無作為の標本ではなく、評価が極端に良いか悪いものに偏ると指摘する([解説](https://barkingiguana.com/writing/building-a-feedback-loop-from-users-to-model-improvement/))。失敗の事例を含めた方が、改良した Skill が選ばれたという報告もある([arXiv:2608.02636](https://arxiv.org/abs/2608.02636)) | 失敗率・改善率を出さない。`no_problem` の確認済みケースを対照に入れる |
| 検証での改善が、別の評価では出ないことがある | 同論文は、検証・テスト・頑健性の評価で、選ばれる改良が一致しないことがあるとする | 調整用(`tuning`)と最終評価用(`final`)を分け、`final` を調整に使わない |
| スキルの変更は人が承認する | 提案を差分で出し、人が承認してから反映する運用の例がある([Speakeasy](https://www.speakeasy.com/docs/ai-control-plane/distribute/skills/improving-skills-with-agent-feedback.md)) | `skill/` を自動で書き換えない。提案は下書きとして出す |
| 同系統モデルの判定・下書きは盲点を共有する | 判定者が自分や同じ系統の出力を好む傾向が報告されている([arXiv:2502.01534](https://arxiv.org/abs/2502.01534)) | LLM の下書きと判定は補助。確認は人が行い、新規の規則より既存規則の統合・明確化を優先させる |

### 外部の意見と反映

設計の確認として、Codex と Antigravity に同じ依頼(効果の観点、安全性の観点、優先順位つきで10項目まで)を出しました。どちらも読み取り専用で、リポジトリのファイルは変更していません。意見は参考であり、採否はメンテナーが決めます。

| 意見 | 出所 | 反映 |
|---|---|---|
| 失敗票だけでは改善率を測れない。原本単位で未使用の final を固定し、旧新版を伏せて比べる | Codex | 本仕組みは改良案の根拠を集める段階で、効果の測定は #44 の最終評価で行う。`final` の指摘は集約・提案・回帰ケースに使わない |
| LLM への送信は、確認者の要約・最小の引用に絞る。出力は信頼しない | Codex、Antigravity | `propose` が送るのは、確認者が書いた引用・根拠・保つこと・禁止だけ。資料はタグで区切り、命令として扱わない指示を付ける。下書きは確認済みの判定として扱わない |
| JSON は、型・未知のキー・深さ・件数・総容量を制限し、工程間をハッシュでつなぐ | Codex、Antigravity | 未知のキーと制御文字を拒否、深いネストは拒否(クラッシュしない)、ファイル数1000・総容量100MBの上限、`findings_sha256` で工程をつなぐ |
| 同じ原本の別の抜粋を、別の文書として数えない。原本IDが要る | Codex、Antigravity(自信なしと注記) | `source_document` でメンテナーがまとめられる。原文の重複検査は未実装(限界に記載) |
| 票に依頼文を持たせ、「変更不要」「許容できる言い換え」の対照を付ける | Codex、Antigravity | 票に `request` を追加。`no_problem` の確認済みケースを対照に入れ、`verify` が対照の判定の悪化も見る |
| 調整用の `final` 文書が票として届くと、最終評価が汚染される | Antigravity | `fingerprint` と `--reserved-ids` で、取り置いた文書の票を受領時に拒否する |
| 規則を足すより、既存規則の統合・削除を優先する | Codex、Antigravity | 下書きの指示に、統合・明確化を優先することを入れた。規則数の上限は設けていない(未実装) |
| 3文書×2人の閾値は、提案を出す順位づけに限る | Codex | 閾値は規則修正の提案を出す目安に限り、効果の根拠にしない。送付が10票ほどたまったら見直す |

### 限界

- 閾値(3文書・2人)は暫定で、送付が10票ほどたまったら実際の分布を見て見直します。
- 少数の送付者では、個人の好みを規則に固定するおそれがあります。確認で「好み」と「意味保持の問題」を分けます。
- 同一原本の部分抜粋を、別の文書として申告された場合は、ハッシュでは見分けられません(原文の重複検査は未実装)。
- メールと GitHub Issue をまたぐ同一人物は、送付者IDでまとめる運用に頼ります。
- 非公開の送付文の一部を LLM に送るのは、`--consent-ai` のある票だけです。確認者の引用・根拠にも、機密が残りうる点は同じです。機密の度合いが高いものは `--consent-ai` を付けず、メンテナーも引用を伏せてから送ってください。
- 効果(未知の文書での意味保持・可読性の改善)は、この仕組みでは測りません。回帰ケースでの悪化がないことと、最終評価での改善は別です(#44)。
