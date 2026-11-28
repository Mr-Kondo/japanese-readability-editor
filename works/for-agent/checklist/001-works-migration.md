現在地: 文書の移動、移動先の索引、リンクと旧パスの書き換えは完了。未確認: テスト、リンク検査、整形検査、最終確認。
次の項目: 検証（テスト、旧パスの残存検査、リンク検査、整形検査）。
未解決の指摘: evals/opq-run・opq2-run・opq3-run の run.json に記録された adr_sha256 が、現在の ADR（移動の前後で同じ内容）のハッシュと一致しない。移動前から存在する問題で、移動では変えていない。

# チェックリスト: works/ への移行

使うモデル: 実装 Haiku 5.5、検査 audit（Haiku 5.5）、設計判断 Sonnet 5.5、最終確認 advisor（Opus 5.5）、外部レビュー Codex・Antigravity。

承認条件: ユーザーがこのチェックリストを承認し、下の全項目を確認したこと。

## 移動

- [ ] ADR 6件と index.md を `works/for-agent/design-document/` の番号付きフォルダへ移す
- [ ] 設計・要求・計画の文書 9件を、移動表どおりに `works/for-agent/` へ移す
- [ ] `adr/`、`reports/`、`research_notes/` を、空になったことを確認して削除する
- [ ] `opq-analysis-adr.md` と `opq-reeval-adr.md` のバイト同一を `shasum -a 256` で確認する
- [ ] `evals/opq-run`、`opq2-run`、`opq3-run` の runner の ADR パスを新パスへ変える（その他の行は変えない）
- [ ] run.json などに旧パス文字列が残っていないか確認する（書き換えない）

## 参照の書き換え

- [ ] 旧ファイル名への参照（リンクと本文のパス言及）を、README・AGENTS・docs・evals の説明文書・skills・tests・tools で書き換える
- [ ] 移した文書の中の相対リンクを、新しい階層で解決するよう直す（バイト同一の2件は除く）
- [ ] `works/for-agent/design-document/index.md` に番号付きフォルダ一覧を追加し、ADR のリンクを直す
- [ ] `docs/development.md` の reports/research_notes の言及を works/ へ直す
- [ ] 触らない行（`evals/token-usage/inputs/xlong.md`、`docs/upstream/reviews/`、`docs/release-notes/`、`docs/feedback.md`）は変えていないことを確認する

## 新規作成

- [ ] `works/README.md`（英語。先頭に日本語の案内）
- [ ] `works/for-human/README.md`（日本語）
- [ ] `works/for-agent/requirement-definition-document/index.md`
- [ ] `works/for-agent/implementation-plan/index.md`
- [ ] `requirements-document/` は作らない（空になるため）

## 検証

- [ ] `perl -e 'alarm 180; exec @ARGV' python3 -m unittest discover -s tests` が通る
- [ ] `grep -rn "adr/"` の結果が、works/ 内の新パスと触らない行を除いて0件
- [ ] 旧ファイル名（reports/、research_notes/、docs/design.md ほか）の残りが、触らない行を除いて0件
- [ ] Markdown の相対リンクの壊れ数を、移動前（HEAD の展開）と移動後で比べる
- [ ] `prettier --check` と `markdownlint-cli2` を works/ 配下の新規・移動ファイルで実行する（バイト同一の2件は整形しない）
- [ ] 最終確認: advisor（Opus 5.5）に統合された diff を見せる

## 作業ログ

