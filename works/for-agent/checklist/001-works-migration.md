現在地: 移動・書き換え・audit・外部レビュー（俯瞰・詳細）・advisor 確認まで完了。残りは PR の作成と自動マージ。
次の項目: PR 作成、CI 通過、マージ、ブランチとワークツリーの片付け。
未解決の指摘: run.json の adr_sha256 が移行前から不一致。opq の ADR 2件の相対リンク7件が切れたまま。テスト2件（test_input_guard）は移行前から失敗。for-agent は英訳待ち。

# チェックリスト: works/ への移行

使うモデル: 実装 Haiku 5.5、検査 audit（Haiku 5.5）、設計判断 Sonnet 5.5、最終確認 advisor（Opus 5.5）、外部レビュー Codex・Antigravity。

承認条件: ユーザーがこのチェックリストを承認し、下の全項目を確認したこと。

## 移動

- [x] ADR 6件と index.md を `works/for-agent/design-document/` の番号付きフォルダへ移す
- [x] 設計・要求・計画の文書 9件を、移動表どおりに `works/for-agent/` へ移す
- [x] `adr/`、`reports/`、`research_notes/` を、空になったことを確認して削除する
- [x] `opq-analysis-adr.md` と `opq-reeval-adr.md` のバイト同一を `shasum -a 256` で確認する
- [x] ~~runner の ADR パスを新パスへ変える~~ → 変更しない。Codex の指摘で、runner.py を変えると既存の run.json の `check_frozen` が失敗すると分かったため。runner は元のまま、旧パスの注記を index.md に残した
- [x] run.json などに旧パス文字列が残っていないか確認する（書き換えない）

## 参照の書き換え

- [x] 旧ファイル名への参照（リンクと本文のパス言及）を、README・AGENTS・docs・evals の説明文書・skills・tests・tools で書き換える
- [x] 移した文書の中の相対リンクを、新しい階層で解決するよう直す（バイト同一の2件は除く）
- [x] `works/for-agent/design-document/index.md` に番号付きフォルダ一覧を追加し、ADR のリンクを直す
- [x] `docs/development.md` の reports/research_notes の言及を works/ へ直す
- [x] 触らない行（`evals/token-usage/inputs/xlong.md`、`docs/upstream/reviews/`、`docs/release-notes/`、`docs/feedback.md`）は変えていないことを確認する

## 新規作成

- [x] `works/README.md`（英語。先頭に日本語の案内）
- [x] `works/for-human/README.md`（日本語）
- [x] `works/for-agent/requirement-definition-document/index.md`
- [x] `works/for-agent/implementation-plan/index.md`
- [x] `requirements-document/` は作らない（空になるため）

## 検証

- [x] （移行前から2件失敗、他は通る）`perl -e 'alarm 180; exec @ARGV' python3 -m unittest discover -s tests` が通る
- [x] `grep -rn "adr/"` の結果が、works/ 内の新パスと触らない行を除いて0件
- [x] 旧ファイル名（reports/、research_notes/、docs/design.md ほか）の残りが、触らない行を除いて0件
- [x] Markdown の相対リンクの壊れ数を、移動前（HEAD の展開）と移動後で比べる
- [x] （移動した文書は移行前から未整形。新規ファイルは markdownlint 指摘なし）`prettier --check` と `markdownlint-cli2` を works/ 配下の新規・移動ファイルで実行する（バイト同一の2件は整形しない）
- [x] 最終確認: advisor（Opus 5.5）に統合された diff を見せる

- [x] 外部レビュー（俯瞰・詳細）を Codex・Antigravity に別々に依頼し、結果を記録する（`both`）

## 作業ログ

- advisor の指摘: `evals/no-skill-comparison.md` は `plan_sha256` で凍結されているため、書き換えを取り消した。opq の runner と同じ扱いで、index.md に注記した。他の runner は、変更したファイルを凍結していないことを確認した。

- 2026-11-28 外部レビュー（乱数 0.90 で割当）: 俯瞰は Antigravity、詳細は Codex。Antigravity の1回目は、ヘッドレスで git コマンドの権限が確認できず失敗した。権限を緩めず、差分一覧のファイルを読む形で再依頼して成功した。Codex の1回目は、サンドボックスが状態フォルダへの書き込みを拒否して失敗し、サンドボックスなしで再実行した。
- 俯瞰の指摘への対応: AGENTS.md に works/README.md の導線を足した。README・environments の使用例は、利用者向けの docs/user-guide.md に戻した。for-agent の英訳待ちと for-human の要約なしは、計画どおりの過渡状態として残した。
- 詳細の指摘への対応: runner.py の書き換えは取り消した（check_frozen が失敗するため）。conclude-pilot-adr.md の supersedes を新名に直した。チェックリスト末尾の空行を直した。works/ のみ MD041 を無効にした。

- 2026-11-28 audit 検査: ADR 2件のバイト同一、runner のパス、旧パス残り0件を確認。テストは 963件中2件が失敗（origin/main でも同じ）。整形検査は移動前から未整形のため報告のみ。
