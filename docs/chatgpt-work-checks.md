# ChatGPT Work の実機確認

## Skill の取り込みと呼び出し

Plus プランのアカウントで、次を確認しました(2026-09-29)。

- ZIP を取り込めた。`name` と `description` は、全文が保たれた。
- `@japanese-readability-editor` で呼び出せた。
- ChatGPT が `agents/openai.yaml` を自動生成した。`allow_implicit_invocation` は `true` だが、実際に自動で使われる頻度は低かった(次の「暗黙起動の実測」)。
- 取り込み直後の `openai.yaml` は、`assets/icon.svg` を参照していたが、ZIP には含まれず、アイコンが壊れた画像として表示された。
- その後、ChatGPT が `assets/icon.svg` を追加し、`openai.yaml` の短い説明文を書き換え、アイコンが表示されるようになった。`SKILL.md` の `name` と `description` は変わらなかった。

## SudachiPy の導入

2026-10-06 に、Plus プランのアカウントで確かめました。Work モードで、既定のモデル(GPT-6 Luna、Medium)を使いました。

- コマンドは、既定ではネットワークを使えません。そのまま `pip install` を実行すると、`No matching distribution found for sudachipy` で失敗しました。設定の「Work network access」がオンでも、同じでした。
- ネットワークを使える権限でコマンドを実行すると、入りました。その後の照合では、`tokenizer: sudachi (sudachidict_small)` と出ました。承認の画面は出ませんでした。
- 最初の版の指示(「入れてよい」)では、ChatGPT は入れようとせず、`regex` の結果を返しました。そこで、「入れて、照合をやり直す」に改め、ネットワークを使える権限で実行することを書き足しました。
- 入れた SudachiPy は、実行環境の領域(`/opt/codex/runtimes/` の下)に入り、次の会話でも残りました。同じ権限で削除しようとすると、承認の審査で拒否されました。
- 改めた指示だけで、SudachiPy のない状態から入れるかは、確かめられていません。確認に使った環境には、すでに入っていたためです。

## 同じ名前の Skill の置き換え

置き換えの後は、ファイル一覧から、ChatGPT が追加した `assets/icon.svg` が消えました。画面上部のアイコンは、表示されたままでした。
