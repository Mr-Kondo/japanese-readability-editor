# 照合コマンドの実行記録（Issue #100）

## 変更

`tools/evaluate_readability.py --skill-dir` の生成は、Claude Code の
`--output-format stream-json --verbose` を使う。採点と、Skillを入れない従来の呼び出しはJSONのままとする。
`invoke()` の既存の返却項目を残し、生成結果に次を追加した。

- `tool_calls`: tool_use ID、ツール名、入力、対応するtool_result、結果の詳細、成否。
- `compare_rewrite_status`: `success` / `failed` / `unconfirmed`。

単純なPython経由または直接の `compare_rewrite.py` 実行で、2つの入力を伴うコマンドと
対応する成功結果があれば `success`、失敗結果があれば `failed` とする。
複数回実行したときは、成功が一度でもあれば集約値を `success` とし、個々の失敗も残す。
呼び出しや結果がない、コマンド名が本文にあるだけ、ソースの表示、`--help`だけ、
複合シェルやラッパー、完了していないバックグラウンド処理は `unconfirmed` とする。
`unconfirmed` は未実行の断定ではない。

生のstdout/stderrと依頼文のハッシュも従来どおり保存する。
タイムアウト時には取得できた部分出力も保存し、最終resultがない生成を完了扱いしない。
旧JSONへの新しい成否の後付けや、既存の意味保存の合否条件の変更は行わない。

## 実環境の確認

2026-10-27 JST、macOS、Claude Code 2.1.308、`claude-sonnet-5-5`、medium。
隔離した一時プロジェクトにv0.21.2のSkillをコピーして、以下を別々のBash呼び出しで実行した。

| 実行 | 実際の結果 | 記録した照合状態 |
|---|---|---|
| SkillのSKILL.md同士を比較（`--json --tokenizer regex`） | 比較結果を返して成功 | `success` |
| 存在しない2つのファイルを比較 | `cannot read`、終了コード2 | `failed` |
| `--help`のみ | 用法表示に成功 | `unconfirmed` |

1セッションの定価換算費用は **$0.0658283**。
生記録は公開しない `feedback/claude-resume-20261027/issue-100/live-direct.json`、抽出結果は同じ場所の
`live-direct-summary.json` に保存した。保存済みstreamを最終実装で再抽出して照合できる。
この確認は記録方式の検証であり、実際の推敲の品質や照合後の修正を評価するものではない。

最初の評価器経由の試行は、環境変数 `ANTHROPIC_BASE_URL` がローカルの
`http://127.0.0.1:8080` を指しており、`model_not_found`（404）で失敗した。
RTK経由の最小呼び出しは成功し、評価器の検証プロセスだけ
`env -u ANTHROPIC_BASE_URL` としても成功した。全体の設定は変更していない。
認証・接続成功は確認したが、アカウントの残り利用量の数値は取得していない。

続くA/B比較では、`~/.claude/settings.json` も同じローカルURLを指定するため、
採点では環境変数の除去だけでは足りないことを確認した。3条件の採点用一時フォルダに
同一の公式APIのURL設定を置いて成功した。詳細は[A/B比較の記録](compare-wording-2026-10-27.md)を参照。

## 検証と限界

対応する結果のID照合、失敗、結果欠落、名前への言及、help、ソース表示、複合シェル、
バックグラウンド処理、重複イベント、最終result欠落、タイムアウトの部分出力をテストした。
従来の呼び出し元と、生成・採点結果の読み取りとの互換性は全体テストで確認する。

`success` は照合コマンドの実行成功であり、入力が正しい原文・最終稿だったこと、
指摘を検討したこと、意味が保存されたことまでは証明しない。
複合シェルなどは成功していても未確認になりうるため、比較時は未確認件数も併記し、
必要なら生記録を個別に確認する。旧来の `num_turns` は回数として残すが、
照合実行の直接証拠として扱わない。

## 参考

- [Issue #100](https://github.com/Mr-Kondo/japanese-readability-editor/issues/100)
- [Issue #101](https://github.com/Mr-Kondo/japanese-readability-editor/issues/101)
- [Claude Code: Run Claude Code programmatically](https://code.claude.com/docs/en/headless)
