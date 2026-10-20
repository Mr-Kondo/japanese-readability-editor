# 他のモデル・エージェント・Gemini の確認(Issue 87、2026-10-21)

[Issue 87](https://github.com/Mr-Kondo/japanese-readability-editor/issues/87) の未確認だった範囲のうち、手元で確かめられたものの記録です。**1環境につき1〜2回の動作確認で、統計ではありません。** 版は v0.18.0 の Skill を、隔離した一時ディレクトリ(利用者の設定やインストール済みの Skill を使わない)に置いて流しました。

## Haiku 5.5(`claude -p`、ファイルを直す依頼 B、短・中・長を各5回、旧 v0.17.1 と新 v0.18.0 を交互に)

| 項目 | v0.17.1 | v0.18.0 |
|---|---|---|
| `compare_rewrite.py` を実行した回 | 12/15 | 15/15 |
| 入力側トークン(平均、15回) | 307,256 | 307,799(+0.2%) |
| 費用(USD、平均) | 0.0136〜0.0172 | 0.0139〜0.0171 |

- **Haiku 5.5 は、旧版でも 8 割の回でスクリプトを実行した。** そのため、必ず実行させる変更で、トークンはほぼ増えなかった(Sonnet 5.5 は +29%、Opus 5.5 は旧版でも毎回実行)。以前測った Haiku 4.5 は実行しなかったので、世代で挙動が違う。
- 1回の入力側が約30万トークンで、Sonnet 5.5(約15万)の約2倍。Haiku 5.5 のほうが、ターン数(API 呼び出し)が多い。
- 意味保存は、Haiku 5.5 では測っていない。記録: [evals/token-usage/runs-haiku-5-5/](../../evals/token-usage/runs-haiku-5-5/)。

## Codex(CLI 0.155.1、モデルは設定ファイルを使わない既定)

`CODEX_HOME` を空の一時ディレクトリにして(認証だけをコピー)、`.agents/skills/` に Skill を置いたプロジェクトで `codex exec` を流した。

- **Skill は読み込まれた。** 依頼に Skill 名を書くと、`SKILL.md` と参照ファイルを `cat` で読んだ(5コマンド、入力 227,943 トークン、うち 180,864 はキャッシュ)。
- B で、書き換える前の文章を `/private/tmp/` へ保存し、`python3` で書き換えた。**`compare_rewrite.py` は実行せず、`diff -u` で比べた。** v0.18.0 の本文の「必ず」を、読んだが守らなかった(1回)。保存先の削除は行った。
- 「版と実行環境を確かめて」と頼むと、`skill_info.py --model GPT-6` を実行した。アプリは `codex`、版は `0.163.0`(`CODEX_THREAD_ID` と `CODEX_VERSION` から)と判定した。**`codex --version` の 0.155.1 とは違う**(アプリ側が持つ版を指しているとみられ、CLI 単体の版ではない)。モデル名は、エージェントが `GPT-6` と書いた(環境から分からず、エージェントの自己申告に頼る。実際のモデル名は記録していない)。
- JSON の保存先 `~/.agents/skill-env/` は、既定のサンドボックス(`workspace-write`)の書き込み範囲の外なので、エージェントは `/private/tmp/skill-env/` に保存した。

## OpenCode(v2.1.0)

`XDG_CONFIG_HOME` を一時ディレクトリにして(設定ファイルだけをコピー)、プロジェクトの `.agents/skills/` に Skill を置いて `opencode run --auto` を流した。

- **`.agents/skills/` の Skill は読み込まれた。** `skill` ツールで読み、参照ファイル2つを読んだ。
- B で、書き換える前の文章を一時ディレクトリへ保存し、`measure.py --locate` を実行し、本文を編集し、`compare_rewrite.py` を実行して(引数の確認を含めて3回)、保存先を削除した。**v0.18.0 の手順に従った。**
- シェルのツールが最初から見えず、`execute` / `search` のツールでシェルを探すのに、3回の API 呼び出しを使った(このエージェントの挙動で、Skill とは無関係)。
- 注意: 隔離しないで流すと、`~/.config/opencode/skills/` に入っている**古い版**(`VERSION` がなく、v0.17.0 より前)が優先して読み込まれた。利用者の環境の更新が、動作に影響する。

## Hermes Agent(v0.21.6)

`HERMES_HOME` を一時ディレクトリにして(設定・認証をコピー)、`skills/` に Skill を置いて `hermes -z --yolo` を流した。モデルは設定のローカルの qwen3 27B。

- **Skill は、コンテナ内の `/root/.hermes/skills/` に置かれ、読み込まれた。** ただし、端末のツールは Docker コンテナの中で動き、ホストのファイルが見えない(`doc.md` が見つからず、質問を繰り返して終わらなかった)。**ファイルではなく、文章を依頼に貼ると動いた**(8回の API 呼び出し、入力 25,033 + キャッシュ 131,826、出力 8,623 トークン)。
- B で、書き換える前の文章を `/tmp/jre-edit/before.md` へ保存した。最終の応答は、「`compare_rewrite.py` の照合で…確認済み」と書いたうえで本文を返した。**照合を実行したと報告したが、私は個々のコマンドを最後まで確かめていない**(途中までは `before.md` の保存と `--help` の確認を見た)。
- **応答の頭に、照合の報告を書いた。** 「照合の結果は表示しない」(v0.19.1 で足した)に反する。ローカルのモデルでは、出力の指示を守りきれない。

## Gemini Apps(Gem)と Gemini CLI

- **Gem の指示の文字数の上限は、公式の資料に書かれていない。** Gemini Apps ヘルプの「Gems」関連のページ(2件)を確かめたが、指示欄の上限の記載はない(ファイルの上限だけ)。第三者の記事に「約4,000字」とあるが、根拠がない。貼付用の指示は 33,188 字で、入るかは、Gem の編集画面で確かめるしかない。
- **Gems は Skills に移行する。** Google の Workspace 管理者向けの案内([About the transition from Gems to skills](https://knowledge.workspace.google.com/p/gems-migration))によると、Gemini アプリでは Skills の展開が 2026-10-13 に始まり、2026-11-17 に Gems が設定へ移り、残りの Gems は下書きの Skills に自動で移行する。business / enterprise は 2027-03-01 以降、education は 2027-06-01 以降まで Gems を使える。Skills は、オープンな Markdown 形式の `SKILL.md` を使う。フォルダやzipの取り込みができるかは、ページに書かれていない。サイズの上限も書かれていない。
- これから Gemini Apps に入れるなら、貼付用の指示(Gem)より、`SKILL.md` をそのまま使う Skills が自然な入口になる可能性がある。**未確認**(Skills への取り込み方法と、`references/` や `scripts/` の扱いは確かめていない)。
- Gemini CLI は、この Mac に入っていないので、確かめていない。`skill_info.py` の Gemini CLI の判定(`GEMINI_CLI`)は未確認のまま。
