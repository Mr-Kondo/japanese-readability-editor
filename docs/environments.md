# 環境別の対応

各環境での Skill の扱いと、環境ごとの注意をまとめます。インストールのコマンドは、[インストール](installation.md)にあります。

仕様の確認日は 2026-09-29 です。各製品の仕様は変わりやすく、確認日以降に変わる可能性があります。このため、公式資料で確認できた範囲だけを書き、確認できなかった項目は「未確認」としています。

## 対応表

`Native Agent Skill` は、その環境が Agent Skills 形式(`SKILL.md` を含むフォルダ)を直接扱えるかを表します。表の path は、各製品が Skill を探す場所です。インストーラが置く場所は、[インストール](installation.md#配置先)にあります。

| Environment | Native Agent Skill | Workspace path | User/global path | ZIP upload | Notes |
|---|---|---|---|---|---|
| ChatGPT Work | あり。Plus プランのアカウントで、アップロードと呼び出しを確認した(2026-09-29)※1 | 未確認 | 未確認 | 可。Plugins → Skills → Add → Upload from your computer。ZIP を取り込めた | `@skill-name` で呼べる(確認済み)。暗黙起動は不安定([ChatGPT Work](#chatgpt-work))。取り込み時に、ChatGPT が `agents/openai.yaml` を自動生成する ※1 |
| Codex | あり | `.agents/skills/`(カレントから repo root まで探索) | `$HOME/.agents/skills/` | 不要 | `$CODEX_HOME/skills` は旧仕様。管理者向けに `/etc/codex/skills` もある。変更は自動検出、出なければ再起動。symlink 可 |
| Claude Cowork | あり | 非対応(アップロード方式) | 非対応 | 可。Customize → Skills。ZIP の最上位にフォルダ | コード実行の有効化が必要。プランの記載は公式ページ間で異なる。`description` に200字の上限があるという記載あり |
| Claude Code | あり | `.claude/skills/` | `~/.claude/skills/` | 不要 | `.agents/skills` は読まない。未知の frontmatter は無視される。symlink 可 |
| GitHub Copilot | あり(cloud agent、code review、CLI、app、VS Code / JetBrains の agent mode) | `.agents/skills/`、`.github/skills/`、`.claude/skills/` | `~/.agents/skills/`、`~/.copilot/skills/` | 不要 | 利用できるプランは未確認 |
| Gemini Apps | あり(Skills。Gems は 2026-11 以降 Skills へ移行) | 非対応 | 非対応(アカウントに保存) | `SKILL.md` またはフォルダをアップロード。ZIP の可否は未確認 | `scripts/` の扱いは未確認。生成物は [Gemini Apps](#gemini-apps) |
| Gemini CLI | あり | `.agents/skills/`、`.gemini/skills/` | `~/.agents/skills/`、`~/.gemini/skills/` | 不要 | 同じ階層では `.agents/skills` が優先。`/skills list` で確認 |
| Antigravity IDE | あり | `.agents/skills/`(旧 `.agent/skills/` も互換) | `~/.gemini/config/skills/`(旧 `~/.gemini/antigravity/skills/`) | 不要 | `/<skill-name>` で呼べる |
| Antigravity CLI | あり | `.agents/skills/` | `~/.gemini/antigravity-cli/skills/` | 不要 | `~/.agents/skills` は自動では読まれないとする記述あり(Codelab)。未確認 |

※1 2026-09-29 に、Plus プランのアカウントで、実際に確認しました。

二次資料では、対象は Business / Enterprise / Healthcare / Edu とされていました。Free / Plus / Pro は対象外という記述もありました。今回の確認とは一致しません。

OpenAI ヘルプセンターの記事は、自動取得できませんでした。提供状況は、プラン、workspace の設定、リリース状況によって変わります。管理者による有効化が必要な場合もあります。利用前に、各自の画面で確認してください。

### 未確認の項目

次の項目は、公式資料で確認できていません。

- ChatGPT Work のプラン条件と、管理者の設定(Plus プランでの動作は確認済み)
- Gemini Apps の `scripts/` の扱いと、ZIP の可否
- Copilot のプラン条件
- Antigravity の `~/.agents/skills`

## ChatGPT Work

ChatGPT のワークスペースに Skill をアップロードする方式です。`dist/japanese-readability-editor.zip` を使います。

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. ChatGPT の Plugins → Skills を開き、Add → Upload from your computer で、ZIP を選びます。

アップロードできるのは、`.zip`、`.skill`、`SKILL.md` で、最大サイズは1ファイルあたり25MBです。

SudachiPy は、Skill の指示で、エージェントが実行中に入れます(「[SudachiPy を入れる](installation.md#sudachipy-を入れる任意)」)。

Skill 機能がプラン、workspace の設定、管理者の許可に依存する点に注意してください。Enterprise と Edu では、管理者が有効化するまで表示されない場合があります。アップロード画面の名称と手順は、変わる可能性があります。

Plus プランのアカウントで、取り込み、呼び出し、SudachiPy の導入、置き換えを確かめました。記録は、[ChatGPT Work の実機確認](chatgpt-work-checks.md)にあります。

### 暗黙起動の実測

`@` で指定しない場合に、Skill が自動で使われるかを調べました(2026-09-30)。使うべき依頼6件のうち、使われたのは1件でした。その依頼も、3回測り直すと、3回とも使われませんでした。`description` を変えても、増えませんでした。

暗黙起動は、この条件では不安定でした。確実に使うには、`@japanese-readability-editor` で指定してください。

測定の条件、結果、限界は、[ChatGPT Work の暗黙起動の実測](chatgpt-implicit-invocation.md)にあります。

## Codex

Codex は `.agents/skills/` を、カレントディレクトリから repo root まで順にたどって探します。ユーザー全体の配置先は `$HOME/.agents/skills/` です。

従来の `${CODEX_HOME:-~/.codex}/skills/` は、現行の公式ドキュメントに記載がありません。旧仕様として非推奨になったと報告されています。

このリポジトリは、現行の `$HOME/.agents/skills/` を使います。旧版の Codex を使う場合は、手動で `$CODEX_HOME/skills/` へコピーしてください。

## Claude Cowork

Claude のアプリ(Cowork を含む)には、ZIP をアップロードします。ChatGPT Work と同じ ZIP を再利用します。

1. ZIP を用意します。最新の Release からダウンロードするか、`python3 tools/package.py` で作ります。
2. Customize → Skills から、`dist/japanese-readability-editor.zip` を追加します。

ZIP は、Skill のフォルダが最上位にある構造です。コード実行の有効化が必要です。Claude Code の `~/.claude/skills/` は、Cowork のセッションでは読み込まれません。

この Skill の `description` は、Claude のヘルプ記事にある「200字以内」の記載に合わせて、200字以内に収めています。Agent Skills の仕様と Claude API の文書は、1024字までを許しています。

### モデルを選ぶ

Claude のアプリでは、Sonnet 以上のモデルを選んでください。Haiku 4.5 では、Skill の規則が守られない回がありました。

2026-10-07 に、Pro プランのアカウントで、v0.3.0 を確かめました。ブラウザの claude.ai のチャットで、252字の1段落を処理させました。依頼の1行目には、`/japanese-readability-editor` とモードを書きました。Cowork では、確かめていません。

| モデル | モード C(1回) | モード B(2回) |
|---|---|---|
| Haiku 4.5(Extended) | 文言は変わらなかった。頼んでいない「区切った理由」が付いた | 2回とも、常体を敬体に変え、「ログファイル」を「ログ」にした。1回目は Skill を読み込まず、「呼び出し元に」も消えた |
| Sonnet 5.5(Medium) | 文言は変わらなかった | 2回とも、常体のまま、用語と条件を保った。言い切りを変えた1回は、その旨を返答に書いた |

Haiku 4.5 の2回目は、Skill を読み込んだうえで、「敬体に統一」と書いて文体を変えました。Skill を読み込んでも、規則が守られるとは限りません。

## Claude Code

Claude Code は `.agents/skills/` を読みません。配置先は、プロジェクトでは `.claude/skills/`、ユーザー全体では `~/.claude/skills/` です。Codex などと同じプロジェクトで使う場合は、`--target all` で両方に配置します。複製を避けたい場合は、`--link` でシンボリックリンクを作れます。

### プラグインとして入れる

Claude Code のプラグインとしても、入れられます。

```text
/plugin marketplace add Mr-Kondo/japanese-readability-editor
/plugin install japanese-readability-editor@japanese-readability-editor
```

プラグインの Skill は、プラグイン名を前に付けて呼びます。たとえば、`/japanese-readability-editor:japanese-readability-editor` です。

定義ファイル(`.claude-plugin/`)は、`skill/` を指すだけです。Skill は複製していません。`version` を設定していないので、更新はコミットに追従します。更新の手順は、「[更新する](installation.md#更新する)」にあります。

プラグインの定義は、`claude plugin validate` で検証しました。

プラグインのインストールと更新は、マーケットプレースの追加を含めて、`claude plugin` のコマンドで確かめました。確認日は 2026-10-05、Claude Code は 2.1.285 です。手元の設定に影響しないよう、一時的な設定ディレクトリ(`CLAUDE_CONFIG_DIR`)を使いました。対話画面の `/plugin` での操作は、検証していません。

## GitHub Copilot

Copilot は、次の場所から Skill を読みます。

- プロジェクト: `.agents/skills/`、`.github/skills/`、`.claude/skills/`
- 個人: `~/.agents/skills/`、`~/.copilot/skills/`

この repo は共通配置の `.agents/skills/` を使い、`.github/skills/` へは複製しません。

Copilot には、Skill のほかに指示ファイルがあります。今回の用途は、常に適用するルールではなく、必要なときに読み込む手順なので、Agent Skill を使います。

| 仕組み | 置き場所 | 適用のされ方 |
|---|---|---|
| Agent Skills | `.agents/skills/<name>/SKILL.md` など | 関連するときに読み込まれる。詳細な手順向き |
| リポジトリ全体の指示 | `.github/copilot-instructions.md` | 常に適用される。プロジェクト全体の方針向き |
| パス別の指示 | `.github/instructions/*.instructions.md` | `applyTo` に合うファイルを扱うときに適用される |
| エージェント向けの指示 | `AGENTS.md`(`CLAUDE.md`、`GEMINI.md` も) | エージェントが参照する。ディレクトリ木で最も近いものが優先される |

## Gemini Apps

Gemini CLI とは別の製品です。

Gemini Apps では、Gems が 2026-11-17 から Skills に移行します。これは個人の Google アカウントの日程です。Workspace の business / enterprise は 2027-03、education は 2027-06です。

Skills は、`SKILL.md` またはそれを含むフォルダをアップロードして作れます。公式資料が挙げるファイルの種類は、テキスト、PDF、画像です。`scripts/` にある `.py` を扱えるかは、記載がありません。

このため、`tools/package.py` は、共通 Skill から次の2つを生成します。どちらも共通 Skill から機械的に作る出力で、別実装ではありません。

| 生成物 | 使い方 |
|---|---|
| `dist/gemini-apps/japanese-readability-editor/` | `scripts/` を除いたコピー。Skills へフォルダごとアップロードする |
| `dist/gemini-apps-instructions.md` | Gem の指示、または Custom Instructions に貼り付ける |

指示文は、Part 1(`SKILL.md` の本文)と Part 2(詳細ルール)からなります。文字数の上限で貼れない場合は、Part 2 を省いてください。上限は公式資料で確認できていません。Gemini Apps では `scripts/` を実行できないので、計測と検証は Agent が手作業で近似します。

## Gemini CLI

`.agents/skills/` は `.gemini/skills/` の別名で、同じ階層では優先されます。適用順は、ワークスペース、ユーザー、拡張機能、組み込みの順です。確認と管理には、次の機能を使えます。

- 対話中: `/skills list`、`/skills reload`、`/skills enable <name>`、`/skills disable <name>`、`/skills link <path>`
- 端末: `gemini skills list`

Skill が有効になるときは、名前と参照するディレクトリを示す確認画面が出ます。

## Antigravity IDE

ワークスペースは `.agents/skills/` です。旧称の `.agent/skills/` は互換のために読まれますが、新しい `.agents/skills/` を優先します。グローバルは `~/.gemini/config/skills/` で、旧配置の `~/.gemini/antigravity/skills/` も互換のために読まれます。

## Antigravity CLI

ワークスペースは、IDE と同じ `.agents/skills/` です。グローバルは `~/.gemini/antigravity-cli/skills/` で、IDE とは異なります。IDE と CLI の両方に入れる場合は `--target antigravity` を使います。

## 参照した公式資料

- [Agent Skills specification](https://agentskills.io/specification)
- [Codex / ChatGPT: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code: Extend Claude with skills](https://code.claude.com/docs/en/skills)
- [Claude: Agent Skills overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Claude Help Center: How to create custom skills](https://support.claude.com/en/articles/12512198-how-to-create-custom-skills)
- [GitHub Docs: About agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)
- [GitHub Docs: Custom instructions](https://docs.github.com/en/copilot/how-tos/configure-custom-instructions/add-repository-instructions)
- [GitHub Docs: Copilot CLI の agent skills](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills)
- [Gemini CLI: Agent Skills](https://geminicli.com/docs/cli/skills/)
- [Antigravity: Agent Skills](https://antigravity.google/docs/skills)
- [Gemini Apps Help: The transition from Gems to skills](https://support.google.com/gemini/answer/18560919?hl=en)
