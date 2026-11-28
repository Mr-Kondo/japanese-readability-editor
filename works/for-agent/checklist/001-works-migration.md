現在地: 移動・書き換え・新規作成・audit検査は完了。残りは外部レビュー（俯瞰・詳細）と advisor の最終確認。
次の項目: Codex・Antigravity への俯瞰・詳細レビュー依頼（割当は乱数）。
未解決の指摘: run.json の adr_sha256 が移行前から現在のどの ADR とも一致しない。opq の ADR 2件は本文不変のため相対リンク7件が壊れたまま。テスト2件（test_input_guard）は移行前から失敗。for-agent は英訳待ち。

# チェックリスト: works/ への移行

使うモデル: 実装 Haiku 5.5、検査 audit（Haiku 5.5）、設計判断 Sonnet 5.5、最終確認 advisor（Opus 5.5）、外部レビュー Codex・Antigravity。

承認条件: ユーザーがこのチェックリストを承認し、下の全項目を確認したこと。

## 移動

- [x] ADR 6件と index.md を `works/for-agent/design-document/` の番号付きフォルダへ移す
- [x] 設計・要求・計画の文書 9件を、移動表どおりに `works/for-agent/` へ移す
- [x] `adr/`、`reports/`、`research_notes/` を、空になったことを確認して削除する
- [x] `opq-analysis-adr.md` と `opq-reeval-adr.md` のバイト同一を `shasum -a 256` で確認する
- [x] `evals/opq-run`、`opq2-run`、`opq3-run` の runner の ADR パスを新パスへ変える（その他の行は変えない）
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

- [ ] `perl -e 'alarm 180; exec @ARGV' python3 -m unittest discover -s tests` が通る
- [x] `grep -rn "adr/"` の結果が、works/ 内の新パスと触らない行を除いて0件
- [x] 旧ファイル名（reports/、research_notes/、docs/design.md ほか）の残りが、触らない行を除いて0件
- [x] Markdown の相対リンクの壊れ数を、移動前（HEAD の展開）と移動後で比べる
- [ ] `prettier --check` と `markdownlint-cli2` を works/ 配下の新規・移動ファイルで実行する（バイト同一の2件は整形しない）
- [ ] 最終確認: advisor（Opus 5.5）に統合された diff を見せる

- [ ] 外部レビュー（俯瞰・詳細）を Codex・Antigravity に別々に依頼し、結果を記録する（`both`）

## 作業ログ

- 2026-11-28 audit 検査: ADR 2件のバイト同一、runner のパス、旧パス残り0件を確認。テストは 963件中2件が失敗（origin/main でも同じ）。整形検査は移動前から未整形のため報告のみ。

