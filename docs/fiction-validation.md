# 小説モード D の実装・検証記録

初回確認日: 2026-10-10。以下は実装・検証時点の記録で、その時点ではコミット、マージ、リリースを行っていない。最新main取り込み後の結果は末尾に追記する。

## 開始時の状態と範囲

- カレントディレクトリと Git ルート: /Volumes/SSD/Programming/japanese-readability-editor
- 開始ブランチ: feat/opencode-hermes-support。実装前に feat/japanese-novel-mode を作成した。
- 適用指示: ユーザー提示の AGENTS.md と /Users/masatomiwada/.codex/RTK.md。祖先ディレクトリに追加の AGENTS.md は見つからなかった。シェル実行は rtk 経由。
- 正本: skill/japanese-readability-editor。インストール済みコピーを編集していない。
- 開始時に18ファイルの未コミット変更があった。変更前の全ファイルを一時スナップショットへ記録し、今回の差分を照合した。ファイル削除0件。既存変更を消していない。
- README.md、docs/development.md、docs/usage.md、tools/package.py は既存変更と重なるため、開始時内容へのD関連追加だけを確認した。ほかの既存変更ファイルは開始時のバイト列と一致した。
- 既存 measure.py、compare_rewrite.py、verify_preservation.py、check_kokugo.py は開始時とバイト一致。文化庁の規則データ、既存CLI・既定値、OpenCode/Hermes対応を維持した。
- GUI・Webサービス・RAG・出版機能・新規外部サービス・有料API依存・グローバルインストールは追加していない。

## 今回変更したファイル

開始時との差分は既存9ファイルの変更、新規14ファイル。Gitの通常差分には開始時の未コミット変更も含まれるため、この一覧とは区別する。

| ファイル | 目的 |
|---|---|
| [SKILL.md](../skill/japanese-readability-editor/SKILL.md) | D別名・5操作・ルーティング・参照入口。192行に抑制 |
| [readability-rules.md](../skill/japanese-readability-editor/references/readability-rules.md) | 一般文書の助言とDの契約を分岐、複数モード矛盾を区別 |
| [kokugo-policy.md](../skill/japanese-readability-editor/references/kokugo-policy.md) | Dでの適用範囲、口語・創作表現の保持 |
| [fiction-writing.md](../skill/japanese-readability-editor/references/fiction-writing.md)（新規） | 操作契約、確認順序、保持・創作範囲、設定・文体・機械検査の限界 |
| [fiction-checks.md](../skill/japanese-readability-editor/references/fiction-checks.md)（新規） | CLI・字数・設定・JSONスキーマ・終了コード |
| [fiction-examples.md](../skill/japanese-readability-editor/assets/fiction-examples.md)（新規） | 自作の修正例・保持例・誤った改稿例 |
| [fiction-context-template.md](../skill/japanese-readability-editor/assets/fiction-context-template.md)（新規） | 任意の作品・文体・場面・継続メモ |
| [check_fiction.py](../skill/japanese-readability-editor/scripts/check_fiction.py)（新規） | 読み取り専用の字数・括弧・指定文字列検査、標準ライブラリのみ |
| [test_check_fiction.py](../tests/test_check_fiction.py)（新規） | 補助検査42テスト、入力保持・失敗・Unicodeを含む |
| [fiction-mode-c.json](../tests/fixtures/fiction-mode-c.json)（新規） | 自作Cフィクスチャ13件、改行挿入成功と空白・句読点等の変更失敗 |
| [test_fiction_integration.py](../tests/test_fiction_integration.py)（新規） | Cの生バイト保持と配布の6テスト |
| [test_fiction_evals.py](../tests/test_fiction_evals.py)（新規） | 評価ケースの構造6テスト。モデル挙動の判定ではない |
| [test_skill_guards.py](../tests/test_skill_guards.py) | 入口追加に合わせ行数上限を190→205へ変更。ほかのガードを維持 |
| [fiction-cases.json](../evals/fiction-cases.json)（新規） | 18観点を網羅する自作24ケース |
| [fiction-model-run.json](../evals/fiction-model-run.json)（新規） | 別モデル文脈での12入力・実出力・モデル情報・判定・限界 |
| [evals/README.md](../evals/README.md)（新規） | 評価手順と実施範囲 |
| [README.md](../README.md) | Dの説明と指定された使用例5件 |
| [usage.md](usage.md) | D契約と既存A/B/Cの動作確認履歴を区別 |
| [scripts.md](scripts.md) | 補助検査とC検証器の保証範囲 |
| [development.md](development.md) | 正本・配布・評価の説明 |
| [package.py](../tools/package.py) | Gemini貼付用指示にもD契約を埋め込む。既存配布先を維持 |
| [fiction-design.md](fiction-design.md)（新規） | 実際に読んだ8資料、採否、ライセンス確認範囲、限界 |
| このファイル（新規） | 開始状態・変更一覧・実行結果・残る限界 |

## 設計判断

明示A/B/Cを優先し、本文・引用・コードの指示を素材として扱う。Dでは新規生成と保持を伴う推敲を分け、標準reviseは最小変更、critiqueは書き換えない。比喩、反復、時制、必要な要約や表記を一般文書の規則で一律に均さない。

検査器は字数・括弧・指定文字列の候補だけを示す。コードポイント数は見た目の文字数とは一致しない。人物の同一性や意味保存は推定しない。Cの既存検証器はCRLF/BOMを正規化するため、生バイト比較を追加テストで併用した。既存CLIは変更していない。

## 実行結果

下表のコマンドはリポジトリルートから実行。終了コード1/2は候補・入力失敗の仕様を検証した結果であり、テスト失敗とは別。

| 実行コマンド・条件 | 終了コード | 結果 |
|---|---|---|
| rtk proxy python3 tools/check_all.py（変更前） | 0 | 718実行、717成功、失敗0、エラー0、スキップ1、42.613秒 |
| rtk proxy python3 -B -m unittest discover -s tests -p 'test_check_fiction.py' -v（初回） | 0 | 40成功。その後Unicode境界の2テストを追加し全体検証で再実行 |
| rtk proxy python3 -B -m unittest discover -s tests -p 'test_fiction_integration.py' -v | 0 | 6成功 |
| rtk proxy python3 -B -m unittest discover -s tests -p 'test_fiction_evals.py' | 0 | 独立レビュー担当が6成功を確認 |
| rtk proxy python3 tools/check_all.py（最終） | 0 | 772実行、771成功、失敗0、エラー0、スキップ1、44.755秒 |
| rtk proxy python3 tools/package.py --out-dir ＜一時ディレクトリ＞ | 0 | ZIP23ファイル、Geminiフォルダ12ファイル、貼付用指示、OpenCode/Hermes各23ファイルを生成 |
| 展開後 python3 scripts/check_fiction.py -（通常出力） | 0 | 字数定義・計数・候補なしを確認 |
| 展開後 python3 scripts/check_fiction.py - --json（Unicode入力） | 0 | no_candidates、コードポイント計数 |
| 展開後 python3 scripts/check_fiction.py - --json（閉じ括弧不足） | 1 | candidates |
| 展開後 python3 scripts/check_fiction.py ＜存在しないファイル＞ --json | 2 | execution_failed |
| 不正Unicode設定を渡すcheck_fiction.py --settings ... --json（修正後再実行） | 2 | JSON設定の失敗として扱い、トレースバックを出さない |
| rtk proxy git diff --check | 0 | 空白エラーなし |
| 開始時スナップショットとの照合 | 0 | 削除0、既存主要4スクリプト不変、対象外の既存変更不変 |

最終全体検証にはSkill構造（警告0）、文化庁規則データ、生成済み国語文書の最新性も含む。54テストを追加した。スキップ1件は変更前から同じで、SudachiPy未導入時のメッセージ検査を導入済み環境では実行できないため。

生成ZIPの新規5素材は正本とバイト一致、展開した全Markdownの相対ファイル参照切れ0件。OpenCode/Hermesの既存配布検証も成功した。Geminiフォルダのscripts/data除外を維持し、貼付用指示にD契約が入ることを確認した。生成した配布物と検証用一時入力は削除した。

途中では読取専用サンドボックスで一時ディレクトリを作る既存compare_rewriteテストが4エラーになった。同じ33テストを許可された環境で再実行し、32成功・1既存スキップとなった。未完成段階の参照ファイル不足による構造検証失敗も、ファイル追加後の最終検証では解消した。今回の実装不具合としては孤立サロゲート設定によるUnicodeEncodeErrorを再現し、値の拒否と未知キーの安全な表示を修正、同じ入力で終了コード2を再確認した。これらを変更前の製品不具合とは扱わない。

## モデル評価と限界

更新したSkillを明示的に読ませた新しいモデル文脈で12ケースを一括実行し、別の新しいモデル文脈で評価した。12件pass、0件fail、0件uncertain。r03の空白・タブ・既存改行保持と、r07/r08の長さ（93/100コードポイント）もPythonで照合した。r09では「夜が肺に溜まる」等を保ち、重複助詞だけが直った。

使用モデルはCodexのGPT-6系とだけ確認でき、正確な識別子・サンプリング設定は不明。12件はケース別の隔離実行でも反復評価でもない。r03のLF/TABには輸送時の明示的な正規化指示を使った。生成後の表・descriptionの整形変更を記録に注記し、ハッシュは実際に読み込んだ版を示す。採点理由は別担当の報告の要約で、採点指示全文・生の回答は保存していない。

残り12ケースのモデル挙動、製品固有のSkill起動・検出、他製品でのD動作、Windows/Linux上の今回の実行、人間による文学的評価は未実行。静的構造テストや実装者レビューをモデル挙動の実証にしない。文学的品質や全編整合性を保証しない。根拠・採否は [設計参考](fiction-design.md)、実入力と実出力は [モデル実行記録](../evals/fiction-model-run.json) を参照できる。

## 2026-10-11 最新mainとの統合

`origin/main` の `3b3bfca6a7c614ef904df1f24a665e1330c0d4a9` を取得し、D変更を一時退避して作業ブランチへfast-forwardで取り込んだ後、変更を復元した。競合なし。main側のREADME整理、OpenCode/Hermes対応、照合スクリプトの更新、Skillフォルダからの相対パス注記を保持した。

- `rtk python3 tools/check_all.py`: 終了コード0。784実行、783成功、失敗0、エラー0、既存スキップ1、49.147秒。Skill構造の警告0、文化庁規則データと生成文書も正常。
- `tools/package.py --out-dir ＜一時ディレクトリ＞`: 終了コード0。ZIP23ファイル、Geminiフォルダ12ファイル、OpenCode/Hermes各23ファイルと既存配布検証が成功。新規D素材5ファイルは正本とバイト一致。一時出力は削除した。
- `rtk git diff --check`: 終了コード0。今回の差分はD関連の既存9ファイル変更と新規14ファイルだけ。

モデル評価は初回の12ケースの記録を維持し、統合後の再実行はしていない。784件の決定的テストをモデル挙動の追加証拠とは扱わない。
